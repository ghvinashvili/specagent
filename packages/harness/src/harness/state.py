"""Validated reads and writes of the run directory's files (<runs root>/<run-id>/, outside the
repository). Nothing else in the package writes state directly."""

from __future__ import annotations

import contextlib
import copy
import datetime as dt
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from collections.abc import Iterator, Mapping
from pathlib import Path

import jsonschema
import yaml

from .gitcall import GIT

SCHEMAS: dict[str, dict] = {}
# What shapes a role session: team and local settings, MCP servers, agent files, skills, hooks, rules, and the
# plugins the settings enable from the internal marketplace (`plugins/`). Frozen for the life of a run.
FROZEN = [
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".mcp.json",
    ".claude/agents",
    ".claude/skills",
    ".claude/hooks",
    ".claude/rules",
    "plugins",
    "docs/roles/auto-mode.json",
]  # the classifier environment `auto` stages receive through --settings
FINGERPRINT_SKIP = {
    "results",
    "__pycache__",
}  # generated under plugins/ (plugin eval results, bytecode); never part of the configuration
# Keywords dropped from the API copy of a schema (platform structured-outputs, "JSON Schema limitations"): the numeric
# and string-length constraints, `maxItems` and `uniqueItems` are listed there as unsupported and answered with a 400.
# `pattern` is supported with limits (no backreferences, lookarounds or `\b`; only "simple {n,m} cases"); the page does
# not say which counts are simple, so the copy drops `pattern` as well and the full schema checks it locally.
# `$schema`, `$id` and `title` are in neither list; they describe the document, not the data, and are dropped too.
API_UNSUPPORTED = {
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minLength",
    "maxLength",
    "pattern",
    "maxItems",
    "uniqueItems",
    "$schema",
    "$id",
    "title",
}
API_FORMATS = {"date-time", "time", "date", "duration", "email", "hostname", "uri", "ipv4", "ipv6", "uuid"}


def now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


# An escalation is `<NNN>.json`. Nothing else in the directory is one: the Bash sandbox leaves an empty, read-only
# `.mcp.json` in every directory a session may write to (seen live), and `*.json` would match it.
ESCALATION = "[0-9][0-9][0-9].json"


RUNS_MARKER = ".harness-runs"  # a `runs/` folder beside the checkout holds its runs when it carries this file


def runs_root(root: Path, create: bool = True) -> Path:
    """Run state lives outside the repository: a background session may not write into the main checkout, and a
    write outside the working directory is not subject to worktree isolation. A folder `runs/` beside the checkout
    holds it when the folder carries the marker `.harness-runs`: a container that keeps a project, its runs and its
    experiments together. Otherwise <parent>/<repo>-runs. A folder merely named `runs` is not taken: it may belong
    to something else. Seven hooks and ops/night-tick.sh repeat this rule (tests/test_layout.py holds them to it)."""
    shared = root.parent / "runs"
    d = shared if (shared / RUNS_MARKER).is_file() else root.parent / f"{root.name}-runs"
    if create:  # a command that only looks (harness doctor) leaves no folder behind
        d.mkdir(parents=True, exist_ok=True)
    return d


def _checkout(path: Path) -> bool:
    try:
        return (path / ".git").exists()
    except OSError:  # a folder this user may not read is no checkout of theirs
        return False


def init_runs_root(root: Path) -> dict:
    """Make ../runs/ the runs root of the checkout at `root` (`harness runs-root --init`). The marked folder is the
    runs root of every checkout beside it, so a parent that holds another checkout (a shared folder such as ~/Desktop)
    is refused: its projects would mix their runs and lose sight of their active ones. A runs/ folder without the
    marker belongs to something else and is not taken."""
    others = sorted(p.name for p in root.parent.iterdir() if p != root and _checkout(p))
    if others:
        hint = "move the checkout into a folder of its own (its container) and run --init there"
        return {"ok": False, "status": "shared_parent", "checkouts": others, "hint": hint}
    shared = root.parent / "runs"
    if shared.exists() and not (shared / RUNS_MARKER).is_file():
        return {"ok": False, "status": "not_a_runs_root", "folder": str(shared)}
    shared.mkdir(exist_ok=True)
    (shared / RUNS_MARKER).write_text(
        f"runs of the checkout {root.name} beside this folder (harness state.runs_root)\n", encoding="utf-8"
    )
    return {"ok": True}


def schema(root: Path, name: str) -> dict:
    if name not in SCHEMAS:
        SCHEMAS[name] = json.loads((root / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))
    return SCHEMAS[name]


def api_schema(doc: dict) -> dict:
    """The copy of a schema that goes to `--json-schema`: every keyword the API does not accept is dropped.
    Local validation (hooks, gates, state.save) keeps the full schema."""

    def strip(node):
        if isinstance(node, dict):
            out = {}
            for key, value in node.items():
                if (
                    key in API_UNSUPPORTED
                    or (key == "minItems" and value not in (0, 1))
                    or (key == "format" and value not in API_FORMATS)
                ):
                    continue
                out[key] = strip(value)
            return out
        if isinstance(node, list):
            return [strip(item) for item in node]
        return node

    return strip(copy.deepcopy(doc))


def config_fingerprint(root: Path) -> str:
    """sha256 over the FROZEN files; recorded by `harness run`, checked by every launch and resume."""
    digest = hashlib.sha256()
    for rel in FROZEN:
        path = root / rel
        files = (
            sorted(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else ([path] if path.exists() else [])
        )
        for f in files:
            if FINGERPRINT_SKIP & set(f.relative_to(root).parts):
                continue
            digest.update(str(f.relative_to(root)).encode("utf-8") + b"\0" + f.read_bytes() + b"\0")
    return digest.hexdigest()


def claude_version() -> str:
    try:  # the write gate runs a branch's tests in a sandbox, where no `claude` is (docs/decisions/0017)
        res = subprocess.run(["claude", "--version"], capture_output=True, text=True, check=False)
    except OSError:
        return "unknown"
    return (res.stdout.strip().splitlines() or ["unknown"])[0] if res.returncode == 0 else "unknown"


def harness_env(run_dir: Path, stage_id: str, role_type: str, mode: str, shard: int | None = None) -> dict[str, str]:
    """The variables the hooks and the stop gate of a role session read. They travel twice: in the process
    environment of the launching command (session_env), and in the `env` block of the `--settings` JSON
    (launch.session_flags). A background session keeps its `--settings` when the supervisor restarts its process;
    the launching shell's environment is not among the things the agent view page lists as carried over.
    Auto memory is off for role sessions: it is per repository and shared across worktrees, so it would carry
    Claude-written notes from one run into the next, while a role session must start from its agent file and the
    brief alone."""
    env = {
        "HARNESS_RUN_DIR": str(run_dir),
        "HARNESS_STAGE": stage_id,
        "HARNESS_ROLE": role_type,
        "HARNESS_MODE": mode,
        # the interpreter this harness runs in: the stop hook asks the stage's gate through it (`gate --preview`),
        # whatever PATH the session's process has
        "HARNESS_PYTHON": sys.executable,
        "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
        # plain output from every command: colour codes are tokens the session pays for and reads nothing from
        "NO_COLOR": "1",
        "PY_COLORS": "0",
        # A background session is started by Claude Code's background service and inherits the environment the
        # service was started in, not the launching command's (seen live: every `uv run` of a verifier warned about
        # the VIRTUAL_ENV of the shell that had started the service an hour earlier). uv ignores an empty value.
        "VIRTUAL_ENV": "",
    }
    if shard:
        env["HARNESS_SHARD"] = f"{shard:02d}"
    return env


def own_environ(environ: dict[str, str] | None = None) -> dict[str, str]:
    """The launcher's environment without its own Python environment and without the variables of any role session.
    `uv run harness ...` puts the main checkout's
    `.venv` into VIRTUAL_ENV and in front of PATH. A session that works in a worktree must not inherit either: uv
    warns on every command there, and a tool the worktree's environment lacks would be taken from the main
    checkout's (seen live: pytest of the main checkout ran against a worktree and could not import the package)."""
    env = {k: v for k, v in (os.environ if environ is None else environ).items() if not k.startswith("HARNESS_")}
    venv = env.pop("VIRTUAL_ENV", None)
    if venv:
        own = str(Path(venv) / "bin")
        env["PATH"] = os.pathsep.join(p for p in env.get("PATH", "").split(os.pathsep) if p != own)
    return env


def session_env(run_dir: Path, stage_id: str, role_type: str, mode: str, shard: int | None = None) -> dict[str, str]:
    """The process environment of the command that starts a role session: launch, resume and an eval trial all call
    this one function, so the hooks and the stop gate see the same variables everywhere.

    A background session gets none of the harness variables this way. Its variables are in the `env` block of its
    settings (launch.session_flags), and the command that starts it may also start Claude Code's background service,
    which keeps the environment it was started in and hands it to every later background session: seen live, a
    manager started in the background an hour later was taken by the hooks for the reader of the first run."""
    flags = {
        "CLAUDE_CODE_FORCE_SESSION_PERSISTENCE": "1",  # a session started from inside a session is still saved
        "CLAUDE_CODE_SYNC_PLUGIN_INSTALL": "1",  # -p only: enabled plugins install before the first query
    }
    if mode == "bg":
        return {**own_environ(), **flags}
    return {**own_environ(), **harness_env(run_dir, stage_id, role_type, mode, shard), **flags}


def load(root: Path, path: Path, schema_name: str) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema(root, schema_name), format_checker=jsonschema.FormatChecker())
    return doc


def _essence(st: dict) -> dict:
    """What a change of a run is measured by (`changed_at`): its statuses, gates, approvals, attempts and escalations,
    not the time it was last looked at (`updated_at`, `last_poll`, which every poll writes)."""

    def unit(u: dict) -> list:
        return [u["status"], u["gate"], u["attempts"], u.get("approval")]

    return {
        "status": st["status"],
        "stages": {
            sid: [unit(ss), {k: unit(u) for k, u in sorted(ss.get("shards", {}).items())}]
            for sid, ss in st["stages"].items()
        },
        "escalations": sorted((e["id"], e["status"]) for e in st["escalations"]),
    }


def save(root: Path, path: Path, doc: dict, schema_name: str) -> None:
    """Validate, then write atomically (temp file + rename) so a crash never leaves half a file. A run state gets
    `changed_at` when what matters in it differs from the file it replaces (docs/decisions/0010)."""
    if schema_name == "run-state":
        old = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
        if old is None or _essence(old) != _essence(doc):
            doc["changed_at"] = now()
        else:  # a run from before `changed_at` keeps the time of its last write, not of this poll
            doc["changed_at"] = old.get("changed_at") or old["updated_at"]
    jsonschema.validate(doc, schema(root, schema_name), format_checker=jsonschema.FormatChecker())
    write_atomic(path, json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def write_atomic(path: Path, text: str) -> None:
    """Write a file whole or not at all: a temporary file of this write's own beside it (the process id and a random
    part in its name), then a rename, the only step that touches the file. Writers that run at once never share a
    temporary file, and a reader meets the old file or the new one (ADR-0021)."""
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("x", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


@contextlib.contextmanager
def locked(path: Path) -> Iterator[None]:
    """Hold the one lock of a state file, an exclusive flock on `<file>.lock` beside it (ADR-0021). Every writer of a
    run's state.json, its logs/notified.json and a loop's state.json holds it around its read, change and write, and
    never while a session or a gate runs. The kernel drops the lock when its holder's process ends, so a lock left by
    a process that died stops no later writer; the lock file that stays behind holds nothing."""
    lock = path.with_name(path.name + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        yield


def table_path(root: Path, pipeline: str = "default") -> Path:
    """The stage table of a run: docs/roles/stages.yaml, or docs/roles/pipelines/<name>.yaml for a named pipeline."""
    roles = root / "docs" / "roles"
    return roles / "stages.yaml" if pipeline == "default" else roles / "pipelines" / f"{pipeline}.yaml"


def load_table(root: Path, pipeline: str = "default") -> dict:
    table = yaml.safe_load(table_path(root, pipeline).read_text(encoding="utf-8"))
    jsonschema.validate(table, schema(root, "stages"))
    return table


EFFORTS = ("low", "medium", "high", "xhigh", "max")
FAMILIES = ("haiku", "sonnet", "opus")  # weakest first; a model name is read as its family by a part of it
FIXED_TYPES = ("classifier", "quarantine-reader")  # a small fixed job: their rows keep a cheap model in every table
# max_minutes of a stage whose effort rises above the table's: unmeasured; the first real run (harness cache-report)
# corrects them. They make fewer false `timeout` notices: poll never stops a stage (poll.py:244-247).
MINUTES_FACTOR = {"xhigh": 2, "max": 3}


def family(model: object) -> str | None:
    """`opus`, `sonnet` or `haiku` by a part of the name; Fable counts as Opus, since the policy's models list has no
    Fable (seen on 2026-10-02 in continued sessions, a fault fixed the same day); None for anything else."""
    name = str(model or "").lower()
    if "fable" in name:
        return "opus"
    return next((f for f in FAMILIES if f in name), None)


def resolve_model_effort(environ: Mapping[str, str] | None) -> dict:
    """The model and the effort of the session that runs `harness run` (the manager's), read once at run creation:
    its id from CLAUDE_CODE_SESSION_ID, its transcript by launch.transcript_of, the model of its last response and the
    effort of its last line that has one (transcript.model_and_effort). {"inherited": False, "reason": ...} when the
    variable is missing (a terminal, a loop, a test), the transcript is not found or names neither."""
    if environ is None:
        return {"inherited": False, "reason": "no session environment was given to create_run"}
    session = environ.get("CLAUDE_CODE_SESSION_ID")
    if not session:
        return {"inherited": False, "reason": "CLAUDE_CODE_SESSION_ID is not set: harness run ran outside a session"}
    from . import launch, transcript  # launch imports this module

    path = launch.transcript_of(session)
    if path is None:
        return {"inherited": False, "reason": f"no transcript of session {session}", "session_id": session}
    found = transcript.model_and_effort(path)
    if not family(found["model"]) or found["effort"] not in EFFORTS:
        why = f"the transcript of session {session} names model {found['model']!r} and effort {found['effort']!r}"
        return {"inherited": False, "reason": why, "session_id": session}
    return {"inherited": True, "session_id": session, "model": found["model"], "effort": found["effort"]}


def choose_stage(row: dict, session: dict, flag: str | None) -> dict:
    """The model, effort and max_minutes of one stage: the table's values as they are, or the effort an `--effort`
    flag gives the stage for this run (docs/decisions/0024). The session that runs `harness run` is recorded in the
    manifest and changes nothing: two runs made from an Opus/max session on 2026-10-04 ran every stage at max and
    used the week's limit. An effort above the table's multiplies max_minutes (MINUTES_FACTOR). `source` says where
    each value came from; `floor` keeps the table's."""
    floor = {"model": row["model"], "effort": row["effort"], "max_minutes": row["max_minutes"]}
    effort, source = row["effort"], {"model": "table", "effort": "table"}
    if flag:
        effort, source["effort"] = flag, "flag"
    raised = EFFORTS.index(effort) > EFFORTS.index(row["effort"])
    factor = MINUTES_FACTOR.get(effort, 1) if raised else 1
    source["max_minutes"] = "effort" if factor > 1 else "table"
    return {
        "model": row["model"],
        "effort": effort,
        "max_minutes": row["max_minutes"] * factor,
        "source": source,
        "floor": floor,
    }


def head_commit(root: Path) -> str | None:
    """HEAD of the checkout at run creation: the commit a stage without a checkout of its own is gated at."""
    res = subprocess.run([*GIT, "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return res.stdout.strip() if res.returncode == 0 else None


def create_run(
    root: Path,
    slug: str,
    brief: Path,
    context_paths: list[str] | None = None,
    pipeline: str = "default",
    effort: dict[str, str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict:
    """Create <runs root>/<run-id>/ with manifest.json (session ids pre-generated) and state.json.
    `brief` is the confirmed brief, normally <runs root>/_briefs/<slug>.md; it is copied into the run directory.
    `pipeline` names the stage table; the manifest records it, so launch and resume read the same table.
    `effort` sets the effort of named stages for this run (stage id: level): the table gives the default for ordinary
    work, and a hard run raises the stages whose output decides. Measured on one reader stage, max found every fact
    and five contradictions where high missed one fact and wrote half the quotes, at four times the price.
    `environ` is the environment of the session that runs `harness run` (the CLI passes os.environ): its model and
    effort are recorded under `session` and change no stage (choose_stage)."""
    table = load_table(root, pipeline)
    effort = dict(effort or {})
    ids = [r["id"] for r in table["stages"]]
    wrong = [f"{s}={e}" for s, e in effort.items() if s not in ids or e not in EFFORTS]
    if wrong:
        return {"ok": False, "status": "bad_effort", "given": wrong, "stages": ids, "levels": list(EFFORTS)}
    from . import access  # the policy fixes the steps mode of every stage for the life of the run

    policy = access.load_policy(root)
    session = resolve_model_effort(environ)
    run_id = dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S") + "-" + slug
    run_dir = runs_root(root) / run_id
    for sub in ("stages", "escalations", "locks", "logs"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy(brief, run_dir / "brief.md")
    stages = [_manifest_stage(row, session, effort.get(row["id"]), policy) for row in table["stages"]]
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": now(),
        "created_by": "manager",
        "brief_path": f"{run_id}/brief.md",
        "context_paths": list(context_paths or []),
        "claude_version": claude_version(),
        "pipeline": pipeline,
        "session": session,
        **({"base_commit": head} if (head := head_commit(root)) else {}),
        **({"loop": table["loop"]} if table.get("loop") else {}),
        "stages": stages,
        "limits": {
            "max_minutes_per_stage": max(s["max_minutes"] for s in stages),
            "max_attempts_per_stage": max(r["max_attempts"] for r in table["stages"]),
            "max_budget_usd_print": max(r.get("max_budget_usd", 0) for r in table["stages"]),
        },
    }
    save(root, run_dir / "manifest.json", manifest, "run-manifest")
    st = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "created",
        "updated_at": now(),
        "current_stage": None,
        "config_fingerprint": config_fingerprint(root),
        "stages": {
            s["id"]: {
                "status": "pending",
                "attempts": 0,
                "session_ids": [],
                "gate": "pending",
                "approval": "pending" if s["approval"] == "human" else "not_required",
            }
            for s in stages
        },
        "escalations": [],
        "loop": {"rounds": {}, "history": []},
    }
    save(root, run_dir / "state.json", st, "run-state")
    return {"ok": True, "run_id": run_id, "run_dir": str(run_dir), "session": session}


def _manifest_stage(row: dict, session: dict, flag: str | None, policy: dict) -> dict:
    """One stage of the manifest: the row's fixed fields, the chosen model, effort and max_minutes with their
    source, and the steps mode of its type as need-to-know.yaml has it now (warn when it names none)."""
    from . import access

    shards = row.get("max_shards", 1) if row.get("parallel") == "per_task" else 1  # one fixed session id per shard
    chosen = choose_stage(row, session, flag)
    entry = {
        "id": row["id"],
        "role_type": row["role_type"],
        "mode": row["mode"],
        "depends_on": row.get("depends_on", []),
        "shards": shards,
        "session_ids": [str(uuid.uuid4()) for _ in range(shards)],
        "model": chosen["model"],
        "effort": chosen["effort"],
        "permission_mode": row["permission_mode"],
        "gate": row["gate"],
        "approval": row["approval"],
        "max_minutes": chosen["max_minutes"],
        "max_attempts": row["max_attempts"],
        "source": chosen["source"],
        "floor": chosen["floor"],
        "steps": access.steps_mode(policy, row["role_type"]) or "warn",
    }
    if "max_budget_usd" in row:
        entry["max_budget_usd"] = row["max_budget_usd"]
    if "returns_to" in row:  # a reviewer that sends its findings back (harness/rounds.py)
        entry["returns_to"] = row["returns_to"]
    return entry


def refuse_aborted(root: Path, run_id: str) -> dict | None:
    """The refusal of a command that would change an aborted run (docs/decisions/0010); None for any other run."""
    path = runs_root(root) / run_id / "state.json"
    st = load(root, path, "run-state") if path.is_file() else {}
    if st.get("status") != "aborted":
        return None
    why = "an aborted run is a record: nothing changes it; the work goes on in a new run (`harness run`)"
    return {"ok": False, "status": "run_aborted", "run_id": run_id, "aborted": st["aborted"], "why": why}


def check_frozen(root: Path, st: dict) -> dict | None:
    """A launch or resume is refused when a FROZEN file changed since `harness run` (or the last `refreeze`)."""
    current = config_fingerprint(root)
    if current == st["config_fingerprint"]:
        return None
    return {
        "ok": False,
        "status": "config_changed",
        "recorded": st["config_fingerprint"],
        "current": current,
        "hint": "a frozen file changed during the run; a human accepts the change with `harness refreeze --run <run-id>`",
    }


def refreeze(root: Path, run_id: str) -> dict:
    path = runs_root(root) / run_id / "state.json"
    with locked(path):  # read, change and write under the file's one lock (ADR-0021)
        refused = refuse_aborted(root, run_id)
        if refused:
            return refused
        st = load(root, path, "run-state")
        st["config_fingerprint"], st["refrozen_at"], st["updated_at"] = config_fingerprint(root), now(), now()
        save(root, path, st, "run-state")
    return {"ok": True, "run_id": run_id, "config_fingerprint": st["config_fingerprint"]}


def approve(root: Path, run_id: str, stage: str, decision: str) -> dict:
    path = runs_root(root) / run_id / "state.json"
    with locked(path):  # read, change and write under the file's one lock (ADR-0021)
        refused = refuse_aborted(root, run_id)
        if refused:
            return refused
        st = load(root, path, "run-state")
        st["stages"][stage]["approval"] = decision
        if st.get("loop", {}).get("stop", {}).get("stage") == stage:  # the human answered the loop's stop
            del st["loop"]["stop"]
        st["updated_at"] = now()
        save(root, path, st, "run-state")
    return {"ok": True, "stage": stage, "approval": decision}


def list_escalations(root: Path, run_id: str, stage: str | None) -> dict:
    run_dir = runs_root(root) / run_id
    items = []
    for path in sorted((run_dir / "escalations").glob(ESCALATION)):
        esc = load(root, path, "escalation")
        if stage is None or esc["stage"] == stage:
            items.append(
                {
                    "id": esc["id"],
                    "stage": esc["stage"],
                    "shard": esc.get("shard"),
                    "status": esc["status"],
                    "question": esc["question"],
                }
            )
    return {"ok": True, "escalations": items}


def output_file(run_dir: Path, stage_dir: Path, rel: str) -> Path | None:
    """The file an `outputs` entry of result.json names, or None when there is no such file in the stage directory.
    The path is written relative to the stage directory (`output/notes.md`), the directory that holds result.json.
    The run-relative form (`stages/read/output/notes.md`) is accepted as well: both name the same file and a session
    that wrote the longer one has not done anything wrong. A path that leaves the stage directory names nothing."""
    home = stage_dir.resolve()
    for base in (stage_dir, run_dir):
        p = (base / rel).resolve()
        if p.is_file() and p.is_relative_to(home):
            return p
    return None


def _next_launch(run_dir: Path, run_id: str, stage_id: str) -> str:
    """The next step of a run whose next stage is ready: its launch, and before it the assignment when none is stored."""
    launch = f"`harness launch --run {run_id} --stage {stage_id}`"
    if (run_dir / "assignments" / f"{stage_id}.md").is_file():
        return launch
    return (
        f"Write the assignment of `{stage_id}` as you would write the prompt of a subagent for the job "
        f"(`templates/stage-assignment.md`), `harness assign --run {run_id} --stage {stage_id}`, then {launch}"
    )


def gate_warnings(stage_dir: Path, label: str) -> list[str]:
    """The failing advisory checks of a unit's gate.json (steps mode warn): `- <unit>: <check> — <detail>`."""
    path = stage_dir / "gate.json"
    try:
        advisory = json.loads(path.read_text(encoding="utf-8")).get("advisory", []) if path.is_file() else []
    except json.JSONDecodeError:
        return []
    return [
        f"- {label}: {c['name']}" + (f" — {c['detail']}" if c.get("detail") else "")
        for c in advisory
        if not c["passed"]
    ]


def write_handoff(root: Path, run_id: str) -> dict:
    """Render HANDOFF.md in the section order of templates/handoff.md from manifest, state, results and
    escalations. Every line comes from a file; nothing is summarised from a session's memory. A unit in a loop
    (harness/rounds.py) counts its attempts within its round and waits for its `--rework` resume, not for a human."""
    from . import launch, rounds  # both import this module

    run_dir = runs_root(root) / run_id
    manifest = load(root, run_dir / "manifest.json", "run-manifest")
    st = load(root, run_dir / "state.json", "run-state")
    rows, produced, waiting, warnings = [], [], [], []
    for stage in manifest["stages"]:
        ss = st["stages"][stage["id"]]
        units = sorted(ss["shards"].items()) if ss.get("shards") else [("", ss)]
        for shard, u in units:
            label = stage["id"] + (f"/{shard}" if shard else "")
            rows.append(
                f"| {label} | {u['status']} | {u['gate']} | {ss['approval']} | {(u['session_ids'] or ['—'])[-1]} | {u['attempts']} |"
            )
            warnings += gate_warnings(run_dir / "stages" / stage["id"] / shard, label)
            result = run_dir / "stages" / stage["id"] / shard / "result.json"
            if result.exists():
                doc = json.loads(result.read_text(encoding="utf-8"))
                for o in doc.get("outputs", []):
                    found = output_file(run_dir, result.parent, o["path"])
                    shown = found.relative_to(run_dir.resolve()).as_posix() if found else o["path"]
                    produced.append(f"- {label}: `{shown}` ({o['kind']})")
            if u.get("last_error"):
                waiting.append(
                    f"- {label}: the print run failed at {u['last_error']['at']} (exit {u['last_error']['exit_code']}); `stages/{label}/logs/print.json`"
                )
            if launch.round_attempts(u) >= stage["max_attempts"] and u["status"] not in (
                "done",
                "skipped",
                *rounds.LOOPING,
            ):
                waiting.append(
                    f"- {label}: {u['attempts']} attempts used, status {u['status']}: resume with a message, refreeze, or `harness abort --run {run_id} --reason ...`"
                )
        if ss["status"] == "done" and ss["approval"] == "pending":
            waiting.append(
                f"- approval of `{stage['id']}`: `harness approve --run {run_id} --stage {stage['id']} --decision approved|rejected`"
            )
    loop = st.get("loop") or {}
    if loop.get("stop"):
        stop = loop["stop"]
        waiting.append(
            f"- the loop stopped at `{stop['stage']}`: {stop['action']} ({stop.get('detail', '')}); "
            f"`harness approve --run {run_id} --stage {stop['stage']} --decision approved` goes on with the work as it is, "
            f"`harness abort --run {run_id} --reason ...` ends the run"
        )
    history = [f"- round {h['round'] + 1}: `{h['from']}` sent {h['items']} finding(s) back to `{h['to']}` ({h['at']})"
               for h in loop.get("history", [])]  # fmt: skip
    for path in sorted((run_dir / "escalations").glob(ESCALATION)):
        esc = load(root, path, "escalation")
        if esc["status"] == "open":
            waiting.append(
                f"- escalation {esc['id']} ({esc['stage']}): open `{path.relative_to(run_dir)}`, fill `answer`, set `status: answered`"
            )
    done = {
        s["id"]
        for s in manifest["stages"]
        if st["stages"][s["id"]]["status"] == "done" and st["stages"][s["id"]]["approval"] != "pending"
    }
    launchable = [
        s["id"]
        for s in manifest["stages"]
        if st["stages"][s["id"]]["status"] == "pending" and set(s["depends_on"]) <= done
    ]
    again = rounds.pending(run_dir, manifest, st)  # a unit a loop sent back whose turn it is
    next_steps = (
        ["Answer the items above, then `harness poll`."]
        if waiting
        else [f"`uv run harness resume --run {run_id} --stage {again[0]['stage']} --rework`"]
        if again
        else [_next_launch(run_dir, run_id, launchable[0])]
        if launchable
        else ["Nothing: the run is finished or every unit is working."]
    )
    cost = st.get("cost", {}).get("print_total_usd", 0.0)
    text = "\n".join(
        [
            f"# HANDOFF — {run_id} ({st['updated_at']})",
            "",
            "## Where the run stands",
            f"- Status: {st['status']}; current stage: {st.get('current_stage')}",
            "",
            "| stage | status | gate | approval | session id | attempts |",
            "| --- | --- | --- | --- | --- | --- |",
            *rows,
            "",
            "## Rounds",
            *(history or ["- none"]),
            "",
            "## What was produced",
            *(produced or ["- nothing yet"]),
            "",
            "## Gate warnings",
            *(warnings or ["- none"]),
            "",
            "## Waiting on a human",
            *(waiting or ["- nothing"]),
            "",
            "## Next steps",
            *(f"{i}. {s}" for i, s in enumerate(next_steps, 1)),
            "",
            "## Costs and limits",
            f"- Print stages total: {cost:.2f} USD; bg sessions: see OpenTelemetry `cost.usage` by `agent.name`",
            "",
        ]
    )
    (run_dir / "HANDOFF.md").write_text(text, encoding="utf-8")
    return {"ok": True, "written": str(run_dir / "HANDOFF.md"), "waiting": len(waiting)}
