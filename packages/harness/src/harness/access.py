"""harness/access.py — what a role session may receive, read and write (docs/roles/need-to-know.yaml).

A role session's working directories are the repository checkout it runs in and its own stage directory.
The run root (manifest, state, other stages, logs) is not among them, so the session cannot read it:
`permissions.blockReadsOutsideWorkingDirectories` in .claude/settings.json makes the file tools refuse every path
outside the working directories, and with the sandbox on, shell commands lose the same paths. What a stage may
use from an earlier stage is copied by the launcher into `<stage dir>/input/`. What a session may write is its stage
directory without its inputs, and its own checkout without the configuration Claude Code loads from it
(docs/decisions/0018-a-role-session-writes-its-stage-and-its-own-checkout-only.md).

This module decides; launch.py, resume.py and poll.py call it:
  check_inputs        a stage's `inputs` against its type's row, before anything is launched
  materialize_inputs  build `<stage dir>/input/` from the declared inputs
  working_dirs        the directories passed with --add-dir
  stage_settings      read and write deny rules, excluded instruction files, plugins and skills for --settings
  skill_settings      the skills a type may call without a prompt, and the ones hidden from it
  tools_flag          the built-in tools of the type, for --tools
  env_extra           HARNESS_STAGE_DIR, HARNESS_BLIND and the prompt cache lifetime
  file_escalations    turn a blind session's `escalation.json` into `<run>/escalations/<NNN>.json`
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import posixpath
import re
import shutil
import stat
from pathlib import Path, PurePosixPath

import yaml

POLICY_PATH = "docs/roles/need-to-know.yaml"
SHARD = re.compile(r"^[0-9]{2}$")


class AccessError(Exception):
    """A stage asks for an input its role type may not receive, or its type has no row. Raised before launch."""


def load_policy(root: Path) -> dict:
    policy = yaml.safe_load((root / POLICY_PATH).read_text(encoding="utf-8"))
    if policy.get("schema_version") != 1:
        raise AccessError(f"{POLICY_PATH}: unsupported schema_version")
    return policy


def type_row(policy: dict, role_type: str) -> dict:
    """The type's row with the defaults filled in."""
    if role_type not in policy["types"]:
        raise AccessError(f"role type {role_type!r} has no row in {POLICY_PATH}; a type without a row is not launched")
    d = policy["defaults"]
    row = {
        **{
            k: d[k]
            for k in ("dirs", "blind", "brief_drop", "cache_ttl", "plugins", "mcp_servers", "pack_files", "repo_deny")
        },
        "bundled_skills": d.get("bundled_skills", False),
        "plugin_skills": [],
        "skills": [],
        "changes_repository": False,
        "trial_checkout": False,
        "alias": {},
        "repo_deny_extra": [],
        **policy["types"][role_type],
    }
    if row["blind"]:  # what names the types, the stages and how the flow judges the work (ADR-0015)
        row["repo_deny"] = [*row["repo_deny"], *d["blind_deny"]]
    return row


SETTINGS_FILES = (".claude/settings.json", ".claude/settings.local.json")
READ_RULE = re.compile(r"^Read\((.+)\)$")


def unreadable(row: dict, root: Path | None = None) -> list[str]:
    """The repository paths a session of the type may not read, as globs from the repository root: its row's
    `repo_deny` (type_row adds `blind_deny` for a blind type) and `repo_deny_extra`, then, given the root, the paths the
    project's settings close to every session (settings_closed). The one list every reader of closed paths takes:
    the launcher's material, the write gate's scope check, the read gate and the locator check (docs/decisions/0025)."""
    return [*row["repo_deny"], *row.get("repo_deny_extra", []), *(settings_closed(root) if root else [])]


def settings_closed(root: Path) -> list[str]:
    """The repository paths the project's own settings close to every session: the `Read(...)` deny rules and the
    `sandbox.filesystem.denyRead` entries of .claude/settings.json and .claude/settings.local.json (`.env`, secrets,
    keys). Each is given as a glob from the repository root, below a closed folder and at any depth too: a deny rule of
    one folder holds at any depth (Claude Code docs, permissions.md:394-397; measured in the template's fix of 2026-10-04), and the sandbox
    shows a closed folder empty. A rule for a path outside the repository adds nothing, and so does a settings file that
    is missing, a link, unreadable or no JSON object."""
    found: list[str] = []
    for rel in SETTINGS_FILES:
        doc = _settings(root / rel)
        rules = [m.group(1) for r in _listed(doc, "permissions", "deny") if (m := READ_RULE.match(r))]
        for base in (_repo_pattern(root, p) for p in [*rules, *_listed(doc, "sandbox", "filesystem", "denyRead")]):
            found += [base, f"{base}/*", f"*/{base}", f"*/{base}/*"] if base else []
    return sorted(set(found))


def _settings(path: Path) -> dict:
    """A settings file as a JSON object; {} for one that is missing, a link, unreadable or anything else."""
    try:
        doc = json.loads(path.read_text(encoding="utf-8")) if path.is_file() and not path.is_symlink() else {}
    except (OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _listed(doc: object, *keys: str) -> list[str]:
    """The strings of the list at `keys` in a JSON document; [] where anything on the way has another shape."""
    for key in keys:
        doc = doc.get(key) if isinstance(doc, dict) else None
    return [x for x in doc if isinstance(x, str)] if isinstance(doc, list) else []


def _repo_pattern(root: Path, path: str) -> str | None:
    """The path of a settings rule as a glob from the repository root, without `./`, `**/` and a trailing `/**`; None
    for a path outside the repository and for the root itself. `//` starts an absolute path, `~/` the home folder, a
    single `/` the project's root (the settings source) and anything else the root as well (a session starts there).
    A `..` is resolved first: `../runs/_inbox` names the inbox beside the checkout, no path of the repository."""
    top = root.resolve().as_posix()
    if path.startswith("//"):
        full = path[1:]
    elif path.startswith("~/"):
        full = Path.home().as_posix() + path[1:]
    else:
        full = f"{top}/{path.removeprefix('/').removeprefix('./')}"
    full = posixpath.normpath(full)
    if not full.startswith(top + "/"):
        return None
    rel = full[len(top) + 1 :].removeprefix("**/").removesuffix("/**").rstrip("/")
    return rel or None


def check_inputs(policy: dict, stages: dict[str, dict], row: dict) -> None:
    """Refuse a stage whose `inputs` exceed what its type may receive. `stages` maps stage id -> stage table row."""
    t = type_row(policy, row["role_type"])
    for item in row["inputs"]:
        if ":" not in item:
            if item not in t["may_receive"]:
                raise AccessError(f"stage {row['id']}: type {row['role_type']} may not receive {item!r}")
            continue
        dep, rel = item.split(":", 1)
        if dep not in stages:
            raise AccessError(f"stage {row['id']}: input {item!r} names an unknown stage")
        if PurePosixPath(rel).is_absolute() or ".." in PurePosixPath(rel).parts:  # the run root, another stage
            raise AccessError(f"stage {row['id']}: input {item!r} leaves the directory of stage {dep}")
        producer = stages[dep]["role_type"]
        if producer not in t["outputs_of"]:
            raise AccessError(
                f"stage {row['id']}: type {row['role_type']} may not receive output of {producer} ({item!r})"
            )


def model_problem(policy: dict, model: object) -> str | None:
    """What is wrong with a model name, or None. A role session runs only on a model the policy lists (`models`)."""
    allowed = policy["defaults"].get("models")
    if allowed and str(model) not in allowed:
        return f"model {model!r} is not one of {', '.join(allowed)} ({POLICY_PATH}, `models`)"
    return None


STEPS_MODES = ("warn", "enforce")


def steps_mode(policy: dict, role_type: str) -> str | None:
    """How the gates hold a type to the checks of specs/001-chat-depth: `warn` records a failing check, `enforce`
    fails the stage. The type's row `steps`, else `defaults.steps`; None while neither is set (not switched on)."""
    mode = (policy["types"].get(role_type) or {}).get("steps") or policy["defaults"].get("steps")
    if mode is not None and mode not in STEPS_MODES:
        raise AccessError(f"{POLICY_PATH}: steps of {role_type} is {mode!r}, not one of {', '.join(STEPS_MODES)}")
    return mode


def check_table(policy: dict, table: dict) -> list[str]:
    """Every stage of a stage table against the policy; used by `harness validate`."""
    stages = {s["id"]: s for s in table["stages"]}
    problems = []
    for s in table["stages"]:
        try:
            check_inputs(policy, stages, s)
        except AccessError as e:
            problems.append(str(e))
        wrong = model_problem(policy, s.get("model"))
        if wrong:
            problems.append(f"stage {s['id']}: {wrong}")
    return problems


ASSIGNMENT = "assignment.md"  # the name of the copy under `input/`; the manager's own text is `assignments/<stage>.md`


def assignment_path(run_dir: Path, stage_id: str) -> Path:
    """Where the manager's assignment for a stage lives: beside the brief, outside every stage directory, so that
    a session reads the copy made for its type and never the text itself. The shards of a stage share it."""
    return run_dir / "assignments" / f"{stage_id}.md"


def brief_for(policy: dict, role_type: str, brief_text: str) -> str:
    """The brief without the lines the type may not see (for a reviewing type: the budget and approvals line)."""
    drop = [re.compile(p) for p in type_row(policy, role_type)["brief_drop"]]
    if not drop:
        return brief_text
    kept = [ln for ln in brief_text.splitlines() if not any(p.match(ln) for p in drop)]
    return "\n".join(kept).rstrip("\n") + "\n"


def _skipped(rel: str, never_copy: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(Path(rel).name, pat) for pat in never_copy)


def put_copy(dst: Path, data: bytes) -> str:
    """Write one input copy, read-only for the role (its settings also deny writes under input/), in place of a file or
    a link already there: an earlier copy is read-only, and a write would follow a link. Returns its sha256."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.unlink(missing_ok=True)
    dst.write_bytes(data)
    dst.chmod(stat.S_IRUSR | stat.S_IRGRP)
    return hashlib.sha256(data).hexdigest()


def _copy(src: Path, dst: Path) -> str:
    """Copy one file byte for byte, read-only for the role. Returns its sha256."""
    return put_copy(dst, src.read_bytes())


def unit_record(run_dir: Path, stage_dir: Path, kind: str) -> Path:
    """The launcher's record of a unit under `<run>/_access/`, which no role session can read or write:
    `<stage>[-NN].inputs.json`, the index of its input copies, or `<stage>[-NN].work.json`, the work it reviews."""
    return run_dir / "_access" / f"{'-'.join(stage_dir.relative_to(run_dir / 'stages').parts)}.{kind}.json"


def write_index(run_dir: Path, stage_dir: Path, index: list[dict]) -> Path:
    """Write the index of a unit's input copies (unit_record): every copy by its name under input/, its source and its
    sha256, which the gate compares a copy with (gates._common.as_copied)."""
    path = unit_record(run_dir, stage_dir, "inputs")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _within(path: Path, home: Path) -> bool:
    """Whether a path is no link and lies inside `home` once every link on its way is resolved. The launcher runs
    outside the sandbox: a link a session left in its output would make it copy a file the session may not read."""
    try:
        return not path.is_symlink() and path.resolve().is_relative_to(home.resolve())
    except OSError:
        return False


def _sources(run_dir: Path, dep: str, rel: str) -> list[tuple[str, Path]]:
    """Where an input `<dep>:<rel>` lives: the stage directory, or each shard directory of a sharded stage."""
    base = run_dir / "stages" / dep
    found = [("", base / rel)] if (base / rel).exists() else []
    for sh in sorted(p for p in base.iterdir() if p.is_dir() and SHARD.match(p.name)) if base.exists() else []:
        if (sh / rel).exists():
            found.append((sh.name, sh / rel))
    return found


def materialize_inputs(policy: dict, stages: dict[str, dict], run_dir: Path, row: dict, stage_dir: Path) -> list[dict]:
    """Build `<stage dir>/input/` from the stage's declared inputs: byte-for-byte copies under neutral names.

    A named file is copied as named. A named directory is copied without the files in `never_copy`: another
    session's result, progress, prompt, gate verdict and logs. A shard of an earlier stage appears under its
    shard number, never under a session id. Only regular files are copied whose real place is inside the producing
    stage's directory: a link in a directory is left out, and a named file that is a link refuses the launch. The
    index, with the sha256 of every copy, is written to `<run>/_access/`, which no role can read.
    """
    check_inputs(policy, stages, row)
    t = type_row(policy, row["role_type"])
    inp = stage_dir / "input"
    _fresh(inp)
    brief = brief_for(policy, row["role_type"], (run_dir / "brief.md").read_text(encoding="utf-8"))
    index: list[dict] = [
        {"source": str(run_dir / "brief.md"), "as": "brief.md", "dropped_lines": t["brief_drop"],
         "sha256": put_copy(inp / "brief.md", brief.encode("utf-8"))}
    ]  # fmt: skip
    given = assignment_path(run_dir, row["id"])
    if given.is_file():  # the manager's assignment, without the lines the type may not see, like the brief
        text = brief_for(policy, row["role_type"], given.read_text(encoding="utf-8"))
        sha = put_copy(inp / ASSIGNMENT, text.encode("utf-8"))
        index.append({"source": str(given), "as": ASSIGNMENT, "dropped_lines": t["brief_drop"], "sha256": sha})
    for item in row["inputs"]:
        if ":" in item:  # brief is above; context and spec are read in the repository
            index += _copy_input(policy, stages, run_dir, row, inp, item)
    write_index(run_dir, stage_dir, index)
    return index


def _fresh(inp: Path) -> None:
    """An empty `input/` for a unit: the read-only copies of an earlier launch are made writable and removed first."""
    if inp.exists():
        for p in inp.rglob("*"):
            if p.is_file():
                p.chmod(stat.S_IRUSR | stat.S_IWUSR)
        shutil.rmtree(inp)
    inp.mkdir(parents=True)


def _copy_input(policy: dict, stages: dict[str, dict], run_dir: Path, row: dict, inp: Path, item: str) -> list[dict]:
    """The copies of one declared input `<dep>:<rel>` under its alias and shard, with their index entries: a named file
    as named, a named directory without the files in `never_copy`. Raises AccessError for an input that does not exist,
    and for a named file that is a link or leads out of the producing stage."""
    t = type_row(policy, row["role_type"])
    never = policy["defaults"]["never_copy"]
    dep, rel = item.split(":", 1)
    alias = t["alias"].get(stages[dep]["role_type"], dep)
    home = run_dir / "stages" / dep
    sources = _sources(run_dir, dep, rel)
    if not sources:
        raise AccessError(f"stage {row['id']}: input {item!r} does not exist under {home}")
    out: list[dict] = []
    for shard, src in sources:
        prefix = f"{alias}/{shard}" if shard else alias
        if src.is_dir():
            for f in sorted(p for p in src.rglob("*") if p.is_file() and _within(p, home)):
                r = f.relative_to(src).as_posix()
                if not _skipped(r, never):
                    out.append({"source": str(f), "as": f"{prefix}/{r}", "sha256": _copy(f, inp / prefix / r)})
        elif _within(src, home):
            out.append(
                {"source": str(src), "as": f"{prefix}/{src.name}", "sha256": _copy(src, inp / prefix / src.name)}
            )
        else:
            raise AccessError(f"stage {row['id']}: input {item!r} is a link, or leads out of stage {dep}")
    return out


def working_dirs(policy: dict, run_dir: Path, row: dict, stage_dir: Path) -> list[str]:
    """Directories passed with --add-dir. Never the run root, except for a type whose row says `runs`."""
    where = {
        "stage": stage_dir,
        "escalations": run_dir / "escalations",
        "inbox": run_dir.parent / "_inbox",
        "runs": run_dir.parent,
    }
    dirs = []
    for key in type_row(policy, row["role_type"])["dirs"]:
        where[key].mkdir(parents=True, exist_ok=True)
        dirs.append(str(where[key]))
    return dirs


# Entries of a run directory (docs/roles/RUNS.md) that may not exist yet when a stage starts.
RUN_ENTRIES = (
    "manifest.json",
    "state.json",
    "brief.md",
    "HANDOFF.md",
    "assignments",
    "escalations",
    "locks",
    "logs",
    "_access",
)


def _manifest_stage_ids(run_dir: Path) -> set[str]:
    manifest = run_dir / "manifest.json"
    if not manifest.is_file():
        return set()
    return {s["id"] for s in json.loads(manifest.read_text(encoding="utf-8")).get("stages", [])}


def _abs(p: Path) -> str:
    return "//" + str(p.resolve()).lstrip("/")


def agent_front(root: Path, role_type: str) -> dict:
    """Frontmatter of the type's agent file, `.claude/agents/<type>.md`."""
    text = (root / ".claude" / "agents" / f"{role_type}.md").read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    return yaml.safe_load(text[4:].split("\n---\n", 1)[0]) or {}


def _names(value: object) -> list[str]:
    """A frontmatter list written as a YAML list or as one comma-separated string."""
    if not value:
        return []
    items = value.split(",") if isinstance(value, str) else list(value)
    return [str(i).strip() for i in items if str(i).strip()]


def skill_settings(root: Path, policy: dict, role_type: str) -> dict:
    """Skills of a role session. The skills the agent file lists are pre-approved: a skill with `allowed-tools`
    needs an approval, and a role session has nobody to give one (the call is denied in a print session and blocks
    a background one). Every other project skill is hidden from the session, and the bundled skills are off unless
    the type's row keeps them: a role does not see the manager's procedures, and its listing stays short.
    A skill of a plugin the type keeps is pre-approved when the row names it in `plugin_skills` (`<plugin>:<skill>`):
    seen live, a writer asked for the commit skill of the conventions plugin and the call was denied.
    The type's row may list `skills:` of its own, the project skills a domain needs (the ECC ones, `.claude/ecc/README.md`);
    they join the agent file's list."""
    mine = _names(agent_front(root, role_type).get("skills"))
    mine += [n for n in _names(type_row(policy, role_type)["skills"]) if n not in mine]  # the row's own, e.g. ECC's
    skills_dir = root / ".claude" / "skills"
    project = sorted(p.parent.name for p in skills_dir.glob("*/SKILL.md")) if skills_dir.is_dir() else []
    workflows = root / ".claude" / "workflows"  # listed beside the skills; a role session has no Workflow tool
    project += sorted(p.stem for p in workflows.glob("*.js")) if workflows.is_dir() else []
    out: dict = {
        "permissions": {"allow": [f"Skill({name})" for name in [*mine, *type_row(policy, role_type)["plugin_skills"]]]},
        "skillOverrides": {name: "off" for name in project if name not in mine},
    }
    if not type_row(policy, role_type)["bundled_skills"]:
        out["disableBundledSkills"] = True
    return out


def tools_flag(root: Path, role_type: str) -> str | None:
    """The built-in tools the type's agent file lists, for `--tools`. On Linux and macOS a session that has Bash
    gets no Glob and Grep unless they are named when the session starts; naming the list makes the session's tools
    exactly what the agent file says. MCP tools are not built-in tools and are left to --mcp-config. A list without a
    built-in tool, an empty one included, gives "": `--tools ""` starts a session with no built-in tool, where no flag
    would give it every one. None only for an agent file without a `tools` key."""
    front = agent_front(root, role_type)
    if "tools" not in front:
        return None
    return ",".join(n for n in _names(front["tools"]) if not n.startswith("mcp__"))


def writes_files(root: Path, role_type: str) -> bool:
    """Whether a session of the type can write a file: False only for a type whose agent file lists tools, none of
    them Write or Bash. A type without an agent file counts as writing, and so does one whose agent file has no `tools`
    key (its session gets every tool). The gate asks every type that writes to account for its material
    (gates.common_checks), and the launcher gives only such a type pieces it chooses by script
    (launch.stage_material)."""
    try:
        tools = tools_flag(root, role_type)
    except OSError:
        return True
    return tools is None or bool({"Write", "Bash"} & set(tools.split(",")))


# What Claude Code loads from a checkout a session enters (its settings, agents, skills, commands, rules, hooks, memory):
# no role session writes it, in its own checkout or in another (docs/decisions/0018).
CHECKOUT_CONFIG = ("CLAUDE.md", "agent-memory", "agents", "commands", "hooks", "launch.json", "loop.md",
                   "output-styles", "routines", "rules", "scheduled_tasks.json", "settings.json", "settings.local.json",
                   "skills", "workflows")  # fmt: skip
# The files of a stage directory no shell command writes: the harness writes the last two, and the session writes the
# others with the Write or Edit tool, where the schema check runs.
RUN_FILES = ("result.json", "tasks.json", "escalation.json", "gate.json", "checks.json")
HARNESS_FILES = ("gate.json", "checks.json")
MESSAGING = ("CLAUDE_CODE_MESSAGING_TOKEN", "CLAUDE_CODE_MESSAGING_SOCKET")  # unset for every sandboxed command
INSTRUCTIONS = ("CLAUDE.md", "AGENTS.md", "CLAUDE.local.md")


def own_work(policy: dict, role_type: str) -> bool:
    """Whether the checkout a session of the type enters is its own work (a writer's branch, a planner's trial), not
    the work it reviews."""
    t = type_row(policy, role_type)
    return bool(t["changes_repository"] or t["trial_checkout"])


def write_limits(
    policy: dict, run_dir: Path, row: dict, stage_dir: Path, root: Path | None, checkout: str | None
) -> tuple[list[str], list[str]]:
    """What a role session may not write: `Edit(...)` deny rules, which bind the Edit and Write tools (they do not
    follow the sandbox), and the paths its sandboxed commands may not write (`sandbox.filesystem.denyWrite`).

    Its inputs and the files of its stage the harness writes, for both; the other run files and the escalations,
    for the shell. A type that works in no checkout writes nothing of the repository. A type with a checkout writes
    that checkout only: every other entry of the main checkout, of its `.claude/` and of `.claude/worktrees/` is named,
    for both (`.git` is left out: a commit writes there; the shell's list holds also where the project's own
    `allowWrite` merges into the session's sandbox), and in its own checkout the configuration Claude Code loads, part
    by part, without `.claude/hooks/` when the brief opens the hook scripts to a type whose checkout is its own work."""
    from .gates._common import hooks_open  # the gates import this module

    edit = [f"Edit({_abs(stage_dir / 'input')}/**)", *[f"Edit({_abs(stage_dir / n)})" for n in HARNESS_FILES]]
    deny = [str(stage_dir / "input"), *[str(stage_dir / n) for n in RUN_FILES]]
    if "escalations" in type_row(policy, row["role_type"])["dirs"]:
        deny.append(str(run_dir / "escalations"))
    if root is None:
        return edit, deny
    main = root.resolve()
    if checkout is None:
        return [*edit, f"Edit({_abs(main)}/**)"], [*deny, str(main)]
    own = main / ".claude" / "worktrees" / checkout
    keep = {main: {".claude", ".git"}, main / ".claude": {"worktrees"}, main / ".claude" / "worktrees": {checkout}}
    for parent, kept in keep.items():
        for p in sorted(parent.iterdir()) if parent.is_dir() else []:
            if p.name not in kept:
                edit.append(f"Edit({_abs(p)}/**)" if p.is_dir() else f"Edit({_abs(p)})")
                deny.append(str(p))
    opened = own_work(policy, row["role_type"]) and hooks_open(run_dir)
    names = set(CHECKOUT_CONFIG) | (
        {p.name for p in (own / ".claude").iterdir()} if (own / ".claude").is_dir() else set()
    )
    for name in sorted(names - {"worktrees", *(["hooks"] if opened else [])}):
        edit += [f"Edit({_abs(own / '.claude' / name)})", f"Edit({_abs(own / '.claude' / name)}/**)"]
    edit.append(f"Edit({_abs(own / '.mcp.json')})")
    return edit, [*deny, str(own / ".claude"), str(own / ".mcp.json")]


def stage_settings(
    policy: dict, run_dir: Path, row: dict, stage_dir: Path, root: Path | None = None, checkout: str | None = None
) -> dict:
    """Settings merged into the `--settings` JSON of a role session. `checkout` names the unit's own checkout under
    `.claude/worktrees/` (launch.worktree_of), None for a unit that has none.

    Deny rules are checked before allow rules. Repository paths are written relative to the session's directory and,
    with the root known, as absolute `//` paths of the main checkout and of every checkout under it: a `./` rule is
    read from the current directory, which follows the session into its checkout. Two layers close the rest of the
    run: the read block (nothing outside the working directories), and deny rules that name every other entry of the
    run, including the ones that do not exist yet. What the session may not write is `write_limits`.
    """
    t = type_row(policy, row["role_type"])
    d = policy["defaults"]
    deny: list[str] = []
    for pat in unreadable(t):  # the row's; the project's settings close their own paths to every session themselves
        deny += [f"Read(./{pat})", f"Read(./.claude/worktrees/*/{pat})"]
        if root:
            deny += [f"Read({_abs(root)}/{pat})", f"Read({_abs(root)}/.claude/worktrees/*/{pat})"]
    deny += [f"Read({pat})" for pat in d["home_deny"]]
    if "runs" not in t["dirs"]:  # everything in the run except what the row opens
        own = stage_dir.resolve()
        opened = {Path(p).resolve() for p in working_dirs(policy, run_dir, row, stage_dir)}
        # What exists now, plus what the layout says will exist: a directory another session creates later
        # (the next stage, the escalations of a builder) must already be closed when this session starts.
        entries = {p.name for p in run_dir.iterdir()} | set(RUN_ENTRIES)
        stage_ids = {p.name for p in (run_dir / "stages").iterdir()} | _manifest_stage_ids(run_dir)
        for name in sorted(entries - {"stages"}):
            p = run_dir / name
            if p.resolve() not in opened:
                deny.append(
                    f"Read({_abs(p)})" if p.is_file() or (not p.exists() and "." in name) else f"Read({_abs(p)}/**)"
                )
        for sid in sorted(stage_ids):
            s = run_dir / "stages" / sid
            if s.resolve() == own:
                continue
            if s.resolve() in own.parents:  # our stage is a shard: close the sibling shards only
                deny += [
                    f"Read({_abs(x)}/**)" if x.is_dir() else f"Read({_abs(x)})"
                    for x in sorted(s.iterdir())
                    if x.resolve() != own
                ]
            else:
                deny.append(f"Read({_abs(s)}/**)")
    skills = skill_settings(root, policy, row["role_type"]) if root else {"permissions": {"allow": []}}
    deny += _unsandboxed(root)
    edit, no_write = write_limits(policy, run_dir, row, stage_dir, root, checkout)
    deny += edit
    excluded = [str(Path(p).expanduser()) for p in d["user_instructions"]]
    if root:  # the project's own instruction files, in the main checkout and in every worktree copy of it
        for rel in d.get("project_instructions", []):
            excluded += [str(root.resolve() / rel), str(root.resolve() / ".claude" / "worktrees" / "*" / rel)]
    if root and checkout and not own_work(policy, row["role_type"]):  # a reviewer takes no instruction from the work
        excluded += [str(root.resolve() / ".claude" / "worktrees" / checkout / "**" / n) for n in INSTRUCTIONS]
    return {
        # file tools refuse every path outside the session's working directories; Claude Code keeps its own files
        # (skills, plugins, rules, agents) readable
        "permissions": {
            "allow": skills["permissions"]["allow"],
            "deny": deny,
            "blockReadsOutsideWorkingDirectories": True,
        },
        # A role session loads neither the user's instruction files nor the project's root map: its rules and
        # its pack are in its system prompt (pack.supplement), where every session of the type reads them from
        # the cache. A CLAUDE.md inside a package still loads when the session opens a file there.
        "claudeMdExcludes": excluded,
        # no snapshot of `git status` in the first message: it differs from session to session, a reviewing type
        # has no use for the list of changed files, and a type that commits has its git rules in its agent file
        "includeGitInstructions": False,
        # A sandboxed command that reaches for a host outside `sandbox.network.allowedDomains` is refused at once.
        # Without this Claude Code asks whether to allow the connection, and a background session waits for an
        # answer nobody gives (seen live: `uv run` asking for releases.astral.sh). The key is honoured from
        # --settings and from user settings, not from the project file.
        "sandbox": _sandbox(root, d.get("toolchain") or {}, no_write),
        "enabledPlugins": {name: name in t["plugins"] for name in d["project_plugins"]},
        **{k: v for k, v in skills.items() if k != "permissions"},
        # the lifetime of the session's prompt cache and no auto memory, as settings: a background session keeps its
        # --settings across a restart of its process
        "promptCacheTtl": t["cache_ttl"],
        "autoMemoryEnabled": False,
        # the checkout a session enters brings its own project settings: none of them may switch the hooks off
        "disableAllHooks": False,
    }


def _toolchain(paths: dict) -> dict:
    """The `sandbox.filesystem` block that re-opens the toolchain paths of the policy for sandboxed commands. They
    travel in --settings: while the read block is on, entries of the repository's own settings do not count."""
    read = [str(Path(p).expanduser()) for p in paths.get("read", []) if Path(p).expanduser().exists()]
    write = [str(Path(p).expanduser()) for p in paths.get("write", []) if Path(p).expanduser().exists()]
    if not read and not write:
        return {}
    return {"filesystem": {**({"allowRead": read} if read else {}), **({"allowWrite": write} if write else {})}}


def _unsandboxed(root: Path | None) -> list[str]:
    """Bash rules that deny a role session every command the project runs outside the sandbox
    (`sandbox.excludedCommands`, which Claude Code merges across the settings a session loads; a role session starts
    in the main checkout with `--setting-sources project,local`). Such a command runs code a writer can change in its
    own checkout (`uv run harness`, `python3 ops/`), so the sandbox would be left by way of it; a permission rule is
    Claude Code's and no code in the checkout changes it. Hooks call the harness without the Bash tool and keep
    working (docs/decisions/0010). An empty file (white space only) is no settings: in a role's sandbox a write-denied
    file that does not exist is mounted empty and read-only (seen 2026-10-29, `.claude/settings.local.json`). A broken
    file still raises: what it runs outside the sandbox cannot be known."""
    patterns: list[str] = []
    for name in ("settings.json", "settings.local.json"):
        source = root / ".claude" / name if root else None
        text = source.read_text(encoding="utf-8") if source and source.is_file() else ""
        if text.strip():
            patterns += json.loads(text).get("sandbox", {}).get("excludedCommands", [])
    return [f"Bash({pattern})" for pattern in dict.fromkeys(patterns)]


def _sandbox(root: Path | None, toolchain: dict, deny_write: list[str] | None = None) -> dict:
    """The `sandbox` block of a role session's --settings.

    A host outside the allowlist is refused at once: without `strictAllowlist` Claude Code asks whether to allow the
    connection, and a background session waits for an answer nobody gives (seen live: `uv run` asking for
    releases.astral.sh). The key is honoured from --settings and user settings only, and once it is on, the hosts and
    the write paths of the repository's own `.claude/settings.json` no longer count (seen live: pypi.org refused
    although the project file lists it). So the launcher repeats them here; the project file stays the one place
    where they are edited. A write path inside the repository is not repeated: `./.claude/worktrees` would open every
    unit's checkout to every role session, and a session's own checkout is its working directory, writable without one.

    A role session starts only inside the sandbox (`failIfUnavailable`): without it Claude Code runs the session's
    commands unsandboxed and nobody sees its warning (seen 2026-10-03, socat missing). The launcher asks first
    (harness/doctor.py `sandbox_problem`), so a missing sandbox is named before a session is spent. `deny_write` is
    what its commands may not write (write_limits), and the messaging token and socket of the session are unset for
    every sandboxed command (`credentials.envVars`); a sandboxed command cannot open a Unix socket either."""
    block: dict = {"failIfUnavailable": True, "network": {"strictAllowlist": True}, **_toolchain(toolchain)}
    block["credentials"] = {"envVars": [{"name": name, "mode": "deny"} for name in MESSAGING]}
    if deny_write:
        block.setdefault("filesystem", {})["denyWrite"] = list(dict.fromkeys(deny_write))
    project = root / ".claude" / "settings.json" if root else None
    if root and project and project.is_file():
        own = json.loads(project.read_text(encoding="utf-8")).get("sandbox", {})
        hosts = own.get("network", {}).get("allowedDomains", [])
        if hosts:
            block["network"]["allowedDomains"] = list(hosts)
        main = root.resolve()
        writes = [
            (root / p).resolve() if p.startswith(".") else Path(p).expanduser()
            for p in own.get("filesystem", {}).get("allowWrite", [])
        ]
        writes = [str(w) for w in writes if w != main and main not in w.parents]
        if writes:
            fs = block.setdefault("filesystem", {})
            fs["allowWrite"] = [*fs.get("allowWrite", []), *[w for w in writes if w not in fs.get("allowWrite", [])]]
    return block


def mcp_config(root: Path, policy: dict, row: dict) -> dict | None:
    """The MCP servers of a role session: the entries of the repository's .mcp.json its type's row names, and no
    other. The launcher passes them with --mcp-config beside --strict-mcp-config, so the tool set of a type is fixed
    and the same in every session of that type. A type whose agent file has a `tools` list also names the server's
    tools there."""
    wanted = type_row(policy, row["role_type"])["mcp_servers"]
    if not wanted:
        return None
    defined = json.loads((root / ".mcp.json").read_text(encoding="utf-8")).get("mcpServers", {})
    missing = [name for name in wanted if name not in defined]
    if missing:
        raise AccessError(f"type {row['role_type']}: MCP server {', '.join(missing)} is not defined in .mcp.json")
    return {"mcpServers": {name: defined[name] for name in wanted}}


def env_extra(policy: dict, row: dict, stage_dir: Path) -> dict[str, str]:
    """Variables a role session gets on top of state.session_env."""
    t = type_row(policy, row["role_type"])
    env = {
        "HARNESS_STAGE_DIR": str(stage_dir),
        "CLAUDE_CODE_PROMPT_CACHE_TTL": t["cache_ttl"],
        # Compact where Claude Code compacts on its own (100: the window less its reserve), not where the human's
        # sessions do: a CLAUDE_AUTOCOMPACT_PCT_OVERRIDE of the human's settings reaches a background session through
        # the environment of the background service. The material stays in the system prompt after a compaction.
        "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "100",
    }
    if t["blind"]:
        env["HARNESS_BLIND"] = "1"
    if t["changes_repository"] or t["trial_checkout"]:  # the checkout HARNESS_WORKTREE names is its own work, not
        env["HARNESS_OWN_CHECKOUT"] = "1"  # work it reviews (permission-request.py, ADR-0015)
    for var, spec in (policy.get("agent_env_dirs") or {}).items():  # plugin state the session must not share
        env[var] = str(_agent_env_dir(stage_dir, var, spec))  # another stage's directory is closed already
    return env


def _agent_env_dir(stage_dir: Path, var: str, spec: dict | None) -> Path:
    """The session's own directory for one `agent_env_dirs` variable, `<stage dir>/plugin-data/<VAR>`, its seed files
    written once each: the variable is an identifier outside the harness's own names, a seed path is relative and
    stays inside the directory, and every part of it is opened by file descriptor with O_NOFOLLOW, so no symbolic link
    is followed, not one planted between a check and the write (the directory is the session's to write)."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", var) or var.startswith("HARNESS_"):
        raise AccessError(f"{POLICY_PATH}: agent_env_dirs: {var!r} is no variable name of a plugin")
    base, own = stage_dir / "plugin-data", stage_dir / "plugin-data" / var
    if base.is_symlink() or own.is_symlink() or stage_dir.resolve() not in own.resolve().parents:
        raise AccessError(f"{POLICY_PATH}: agent_env_dirs: {var}: the directory leaves the stage or is a symbolic link")
    own.mkdir(parents=True, exist_ok=True)
    for rel, text in ((spec or {}).get("files") or {}).items():
        parts = str(rel).split("/")
        if not rel or str(rel).startswith("/") or ".." in parts or "" in parts:
            raise AccessError(f"{POLICY_PATH}: agent_env_dirs: {var}: {rel!r} is no relative path")
        _seed(own, parts, str(text), f"{POLICY_PATH}: agent_env_dirs: {var}: {rel!r}")
    return own


def _seed(own: Path, parts: list[str], text: str, what: str) -> None:
    """One seed file, written once, every directory on its path opened by descriptor without following a link."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        fd = os.open(own, flags)
    except OSError as exc:
        raise AccessError(f"{what}: {own} is no directory ({exc.strerror})") from exc
    try:
        for part in parts[:-1]:
            try:
                nxt = os.open(part, flags, dir_fd=fd)
            except FileNotFoundError:
                os.mkdir(part, 0o700, dir_fd=fd)
                nxt = os.open(part, flags, dir_fd=fd)
            except OSError as exc:  # a link or a file where a directory should be
                raise AccessError(f"{what}: {part} crosses a symbolic link or a file ({exc.strerror})") from exc
            os.close(fd)
            fd = nxt
        try:
            out = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        except FileExistsError:
            return  # written once: a file the session changed is kept
        with os.fdopen(out, "w", encoding="utf-8") as f:
            f.write(text)
    finally:
        os.close(fd)


def pack_files(policy: dict, role_type: str) -> list[str]:
    return list(type_row(policy, role_type)["pack_files"])


def file_escalations(run_dir: Path) -> list[str]:
    """Move every `stages/<stage>[/<NN>]/escalation.json` a blind session wrote to `<run>/escalations/<NNN>.json`.

    The session cannot see the shared directory, so it does not know the next number; the launcher assigns it.
    Returns the ids filed. Called by poll before it reads the escalations. A file that is a link is not filed: poll
    runs outside the sandbox, and the escalations are read by other sessions. An empty file is no escalation: the
    sandbox leaves one, read-only, where a denyWrite rule names a run file that does not exist yet (its mount point);
    a file that does not parse is left for the next poll, never a reason for this one to stop.
    """
    esc_dir = run_dir / "escalations"
    esc_dir.mkdir(exist_ok=True)
    filed = []
    for path in sorted((run_dir / "stages").glob("*/escalation.json")) + sorted(
        (run_dir / "stages").glob("*/[0-9][0-9]/escalation.json")
    ):
        if not _within(path, path.parent):
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(doc, dict):
            continue
        taken = [int(p.stem) for p in esc_dir.glob("[0-9][0-9][0-9].json")]
        doc["id"] = f"{max(taken, default=0) + 1:03d}"
        (esc_dir / f"{doc['id']}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
        path.unlink()
        filed.append(doc["id"])
    return filed
