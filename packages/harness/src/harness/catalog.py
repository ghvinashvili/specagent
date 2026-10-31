"""Role-type catalog and repository self-checks: parse .claude/agents/*.md frontmatter, validate, write
docs/generated/role-types.md; `harness validate` and `harness docs-check` for CI and the manager."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import jsonschema
import yaml

from . import access, extensions, plans, rounds, stagemap
from .gates import spec as spec_gate
from .gates import steps
from .gitcall import GIT

MANAGER_ONLY_TOOLS = {"Workflow", "SendMessage", "ListAgents"}
# Hook events of the hooks reference; `harness validate` rejects any other key under settings.hooks.
HOOK_EVENTS = {
    "SessionStart",
    "Setup",
    "UserPromptSubmit",
    "UserPromptExpansion",
    "PreToolUse",
    "PermissionRequest",
    "PermissionDenied",
    "PostToolUse",
    "PostToolUseFailure",
    "PostToolBatch",
    "Notification",
    "MessageDisplay",
    "SubagentStart",
    "SubagentStop",
    "TaskCreated",
    "TaskCompleted",
    "Stop",
    "StopFailure",
    "TeammateIdle",
    "InstructionsLoaded",
    "ConfigChange",
    "CwdChanged",
    "DirectoryAdded",
    "FileChanged",
    "WorktreeCreate",
    "WorktreeRemove",
    "PreCompact",
    "PostCompact",
    "PreModelSwitch",
    "PostModelSwitch",
    "Elicitation",
    "ElicitationResult",
    "SessionEnd",
}
SKIP_PARTS = {".git", ".venv", "node_modules", "__pycache__", "results", "cache", "worktrees"}
LINK = re.compile(r"\[[^\]]*\]\(([^)\s#]+)(?:#[^)]*)?\)")
FENCE = re.compile(r" {0,3}(`{3,}|~{3,})(.*)")  # match: a line that opens or closes a fenced code block
CODE_SPAN = re.compile(r"(`+)(.+?)\1")  # an inline code span: a run of backticks, text, the same run
INDEX_MAX_BYTES = 12_000  # one line per item; 12 KB as the vault's ops/split_large.py counts (TARGET = 12_000)
KEPT_README = ("docs", "template", "README.md")  # a project's copy of the template's README (ops/new-project.py)
SUMMARY_FOLDERS = ("wiki/decisions", "docs/runbooks")  # spec A5: a page here without its <name>.summary.md is a warning
SPEC_WRITER = "spec-writer"
# A spec is about one page, under 8,000 bytes (the spec-writer's rule); a longer one is a warning of docs-check
SPEC_MAX_BYTES = 8_000
# What the planner writes and a spec never holds (spec 005, requirement 5): none is among what a spec-writer returns
# ("data-model" and "data" + a line break + "model" are the same section as "data model")
PLANNERS = re.compile(r"\b(?:data[\s-]+models?|interfaces?|tests?)\b", re.IGNORECASE)
NOT_A_SPECS = "a data model, interfaces and tests are the planner's, not a spec's"
# The three blocks of 8.3.11 (U+10A0-U+10FF, U+1C90-U+1CBF, U+2D00-U+2D2F), built from their code points
# so that this file holds no letter of a refused block (ADR-0030); listed files are English
GEORGIAN: re.Pattern[str] = re.compile(
    "[" + "".join(f"{chr(lo)}-{chr(hi)}" for lo, hi in ((0x10A0, 0x10FF), (0x1C90, 0x1CBF), (0x2D00, 0x2D2F))) + "]"
)
LETTER = ": a letter of a refused block (U+10A0-U+10FF, U+1C90-U+1CBF, U+2D00-U+2D2F); tracked files are English only"


def load_types(root: Path) -> dict[str, dict]:
    types = {}
    for path in sorted((root / ".claude" / "agents").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            raise SystemExit(f"{path}: missing frontmatter")
        fm = yaml.safe_load(text.split("---", 2)[1])
        if fm.get("name") != path.stem:
            raise SystemExit(f"{path}: name {fm.get('name')!r} must equal the file name {path.stem!r}")
        types[path.stem] = fm
    return types


def _returns(text: str) -> str | None:
    """The `## Returns` section of an agent file or a contract (its heading to the next `## `), or None."""
    head = "\n## Returns\n"
    return text.split(head, 1)[1].split("\n## ", 1)[0] if head in text else None


def spec_writer_problems(root: Path) -> list[str]:
    """Requirement 5 of spec 005: a spec-writer returns the skeleton (intent, requirements, limits, done, out of scope),
    so the `## Returns` of its agent file and of its contract, and the sections its stage's gate requires, name no data
    model, interface or test; those are the planner's. One problem per place and per word. A file without a
    `## Returns` section is a problem too, so that the check never reads nothing."""
    problems: list[str] = []
    places: list[tuple[str, str]] = []
    for rel in (f".claude/agents/{SPEC_WRITER}.md", f"docs/roles/types/{SPEC_WRITER}.md"):
        path = root / rel
        if not path.is_file():  # a missing contract is a problem of validate_types
            continue
        section = _returns(path.read_text(encoding="utf-8"))
        if section is None:
            problems.append(f"{SPEC_WRITER}: {rel} has no `## Returns` section")
        else:
            places.append((f"{rel} `## Returns`", section))
    places.append(("the spec stage's gate (gates/spec.py `REQUIRED`)", "\n".join(spec_gate.REQUIRED)))
    for where, text in places:
        named: dict[str, str] = {}  # each word once per place, as it was first written
        for match in PLANNERS.finditer(text):
            word = " ".join(match.group(0).split())  # a line break inside "data model" reads as one space
            named.setdefault(word.lower(), word)
        for word in named.values():
            problems.append(f"{SPEC_WRITER}: {where} names {word!r}; {NOT_A_SPECS}")
    return problems


def validate_types(root: Path) -> list[str]:
    schema = json.loads((root / "schemas" / "role-type.schema.json").read_text(encoding="utf-8"))
    problems = []
    for name, fm in load_types(root).items():
        for err in jsonschema.Draft7Validator(schema).iter_errors(fm):
            problems.append(f"{name}: {err.message}")
        tools = {t.strip().split("(")[0] for t in str(fm.get("tools", "")).split(",")}
        if name != "manager" and tools & MANAGER_ONLY_TOOLS:
            problems.append(f"{name}: tools {sorted(tools & MANAGER_ONLY_TOOLS)} are manager-only")
        wrong = access.model_problem(access.load_policy(root), fm.get("model"))
        if wrong:
            problems.append(f"{name}: {wrong}")
        if name != "manager" and "memory" in fm:
            problems.append(f"{name}: role types have no `memory` field (docs/architecture/memory.md)")
        if not (root / "docs" / "roles" / "types" / f"{name}.md").exists():
            problems.append(f"{name}: missing contract docs/roles/types/{name}.md")
        if name == SPEC_WRITER:
            problems += spec_writer_problems(root)
    return problems


def write_catalog(root: Path) -> dict:
    problems = validate_types(root)
    if problems:
        return {"ok": False, "problems": problems}
    out = root / "docs" / "generated" / "role-types.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_catalog(root), encoding="utf-8")
    return {"ok": True, "written": str(out), "types": list(load_types(root))}


def render_catalog(root: Path) -> str:
    """The text of docs/generated/role-types.md for the agent files as they are now."""
    rows = [
        "# Role types (generated by `harness catalog`; do not edit)",
        "",
        "| type | model | effort | tools | description |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, fm in load_types(root).items():
        rows.append(f"| `{name}` | {fm['model']} | {fm['effort']} | {fm['tools']} | {fm['description']} |")
    return "\n".join(rows) + "\n"


def _listed(root: Path) -> list[str] | None:
    """The files under root that git tracks or is about to track; an ignored file (a local one, or an empty stub that
    the sandbox mounts) is not listed (B11). None outside a work tree or without git."""
    try:
        res = subprocess.run(
            [*GIT, "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if res.returncode != 0:
        return None
    return sorted({rel for rel in res.stdout.decode("utf-8", "surrogateescape").split("\0") if rel})


def _files(root: Path, suffix: str):
    listed = _listed(root)
    found = root.rglob(f"*{suffix}") if listed is None else (root / rel for rel in listed if rel.endswith(suffix))
    for p in found:
        rel = p.relative_to(root)
        if p.is_file() and not (SKIP_PARTS & set(rel.parts)):
            yield p, rel


def json_problems(root: Path) -> list[str]:
    """Every listed JSON file parses."""
    problems = []
    for p, rel in _files(root, ".json"):
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            problems.append(f"{rel}: not valid JSON ({exc})")
    return problems


def table_problems(root: Path) -> list[str]:
    """docs/roles/stages.yaml and every docs/roles/pipelines/*.yaml: the schema, the order, the loops, need-to-know,
    the role types, the gates and the routes."""
    problems = []
    stages_schema = json.loads((root / "schemas" / "stages.schema.json").read_text(encoding="utf-8"))
    types = load_types(root)
    tables = [root / "docs" / "roles" / "stages.yaml", *sorted((root / "docs" / "roles" / "pipelines").glob("*.yaml"))]
    for path in tables:  # the default table and every named pipeline follow one schema
        table, rel = yaml.safe_load(path.read_text(encoding="utf-8")), path.relative_to(root)
        shape = [f"{rel}: {err.message}" for err in jsonschema.Draft7Validator(stages_schema).iter_errors(table)]
        problems += shape or [f"{rel}: {msg}" for msg in stagemap.order_problems(table["stages"])]  # ids and order
        problems += [] if shape else [f"{rel}: {msg}" for msg in rounds.loop_problems(table)]  # loops (ADR-0024)
        problems += [f"{rel}: {msg}" for msg in access.check_table(access.load_policy(root), table)]  # need-to-know
        for row in table.get("stages", []):
            if row.get("role_type") not in types:
                problems.append(f"{rel}: stage {row.get('id')}: unknown role type {row.get('role_type')!r}")
            elif row.get("mode") == "print" and row.get("json_schema"):
                # the result of a print stage comes back through this tool; an agent file's `tools` is a whitelist
                listed = (access.tools_flag(root, row["role_type"]) or "").split(",")
                if "StructuredOutput" not in listed:
                    problems.append(
                        f"{rel}: stage {row.get('id')}: print stage with json_schema, but "
                        f".claude/agents/{row['role_type']}.md does not list the StructuredOutput tool"
                    )
            if (
                row.get("gate") != row.get("id")
                or not (root / "packages" / "harness" / "src" / "harness" / "gates" / f"{row.get('gate')}.py").exists()
            ):
                problems.append(
                    f"{rel}: stage {row.get('id')}: the gate is named after the stage and harness/gates/{row.get('id')}.py must exist"
                )
            if row.get("permission_mode") == "auto" and str(row.get("model", "")).startswith("haiku"):
                problems.append(f"{rel}: stage {row.get('id')}: auto mode does not support Haiku models")
        for label, target in (table.get("routes") or {}).get("labels", {}).items():
            if target != "escalate" and not (root / "docs" / "roles" / "pipelines" / f"{target}.yaml").exists():
                problems.append(f"{rel}: route {label!r} names a missing pipeline {target!r}")
    return problems


def english_only_problems(root: Path) -> list[str]:
    """No letter of a refused block in a listed file (ADR-0030), one problem per file at its first line with one. A project
    whose product text is in another script narrows the check with `english_only:` (path prefixes) in
    docs/template/variables.yaml; `[]` checks no file."""
    listed = _listed(root)
    if listed is None:  # outside a work tree or without git: every file under the root
        found = (p.relative_to(root) for p in root.rglob("*"))
        listed = sorted(rel.as_posix() for rel in found if not (SKIP_PARTS & set(rel.parts)))
    variables = root / "docs" / "template" / "variables.yaml"
    spec = (yaml.safe_load(variables.read_text(encoding="utf-8")) or {}) if variables.is_file() else {}
    if "english_only" in spec:
        listed = [rel for rel in listed if rel.startswith(tuple(spec["english_only"] or ()))]
    problems = []
    for rel in listed:
        path = root / rel
        if path.is_symlink() or not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").split("\n")
        except UnicodeDecodeError:
            continue
        first = next((n for n, line in enumerate(lines, 1) if GEORGIAN.search(line)), 0)
        if first:
            problems.append(f"{rel}:{first}{LETTER}")
    return problems


def validate_repository(root: Path) -> dict:
    """`harness validate`: no spec-writer type returns a data model, interfaces or tests (spec_writer_problems);
    every JSON file that git tracks or is about to track parses (an ignored one is not read);
    every schemas/*.schema.json is a valid draft-07 schema;
    docs/roles/stages.yaml and every docs/roles/pipelines/*.yaml match schemas/stages.schema.json and name existing
    role types and gate modules (a gate is named after its stage; no `auto` stage on a Haiku model; routes name pipelines;
    a stage id is used once and `depends_on` names stages of the table, once each and without a cycle);
    every skill's frontmatter name equals its directory; every hook event in .claude/settings.json is a known
    event; `Agent` is denied and never allowed; every stage's inputs fit docs/roles/need-to-know.yaml; every plugin and
    MCP server is the one a human accepted in docs/roles/extensions.yaml; no listed file holds a letter of a refused block
    (ADR-0030). Returns {"ok": bool, "problems": [...]}."""
    problems = validate_types(root)
    problems += json_problems(root)
    for p in sorted((root / "schemas").glob("*.schema.json")):
        try:
            jsonschema.Draft7Validator.check_schema(json.loads(p.read_text(encoding="utf-8")))
        except (jsonschema.SchemaError, json.JSONDecodeError) as exc:
            problems.append(f"schemas/{p.name}: {str(exc)[:200]}")
    problems += table_problems(root)
    for skill in sorted((root / ".claude" / "skills").glob("*/SKILL.md")):
        fm = yaml.safe_load(skill.read_text(encoding="utf-8").split("---", 2)[1]) or {}
        if fm.get("name") != skill.parent.name:
            problems.append(
                f"{skill.relative_to(root)}: name {fm.get('name')!r} must equal the directory {skill.parent.name!r}"
            )
    settings = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    problems += [
        f".claude/settings.json: unknown hook event {event!r}"
        for event in settings.get("hooks", {})
        if event not in HOOK_EVENTS
    ]
    perms = settings.get("permissions", {})
    if "Agent" in perms.get("allow", []) or "Agent" not in perms.get("deny", []):
        problems.append(".claude/settings.json: `Agent` must be in permissions.deny and never in permissions.allow")
    problems += [f"extensions: {msg}" for msg in extensions.check(root)["problems"]]  # docs/roles/extensions.yaml
    problems += [f"step rules: {msg}" for msg in steps.problems(root)]  # .claude/agents/*.md, Working method
    problems += english_only_problems(root)
    return {"ok": not problems, "problems": problems}


def prose(text: str) -> str:
    """Markdown without its fenced code blocks and inline code spans: links there are text, as lychee reads them
    without --include-verbatim."""
    kept, fence = [], ""
    for line in text.split("\n"):
        mark = FENCE.match(line)
        if fence:  # inside a block, only a run of the same character at least as long, then blanks, closes it
            if mark and mark.group(1)[0] == fence[0] and len(mark.group(1)) >= len(fence) and not mark.group(2).strip():
                fence = ""
        elif mark:  # an unclosed fence runs to the end of the text
            fence = mark.group(1)
        else:
            kept.append(CODE_SPAN.sub("", line))
    return "\n".join(kept)


def listed(root: Path, rel: str, llms: str) -> bool:
    """Whether docs/<rel> is listed: in docs/llms.txt, in its folder's README.md that docs/llms.txt links, or, inside
    docs/exec-plans/active/<plan>/ or docs/exec-plans/done/<plan>/, by the link to <plan>/00-index.md in the README.md of
    that folder (docs/llms.txt links it)."""
    if f"({rel})" in llms:  # L1
        return True
    folder, _, name = rel.rpartition("/")
    readme = root / "docs" / folder / "README.md"
    by_readme = bool(folder) and name != "README.md" and f"({folder}/README.md)" in llms  # L2, one level only
    if by_readme and readme.is_file() and f"({name})" in readme.read_text(encoding="utf-8"):
        return True
    parts = rel.split("/")
    if len(parts) < 4 or parts[0] != "exec-plans" or parts[1] not in ("active", "done"):
        return False
    plans = root / "docs" / "exec-plans" / parts[1] / "README.md"
    if f"(exec-plans/{parts[1]}/README.md)" not in llms:
        return False
    return plans.is_file() and f"({parts[2]}/00-index.md)" in plans.read_text(encoding="utf-8")  # L3


def summary_warnings(root: Path) -> list[str]:
    """Each page under SUMMARY_FOLDERS without <name>.summary.md beside it; README.md, index.md and summaries are no pages."""
    warnings = []
    for folder in (root / rel for rel in SUMMARY_FOLDERS):
        for page in folder.rglob("*.md") if folder.is_dir() else []:
            if page.name in ("README.md", "index.md") or page.name.endswith(".summary.md"):
                continue
            if not (page.parent / f"{page.stem}.summary.md").is_file():
                warnings.append(f"{page.relative_to(root).as_posix()}: no summary {page.stem}.summary.md beside it")
    return sorted(warnings)


def spec_size_warnings(root: Path) -> list[str]:
    """Each specs/*/spec.md that is not under SPEC_MAX_BYTES bytes (bytes, as the spec-writer's rule counts them)."""
    warnings = []
    for spec in sorted((root / "specs").glob("*/spec.md")):
        size = spec.stat().st_size if spec.is_file() else 0
        if size >= SPEC_MAX_BYTES:
            rel = spec.relative_to(root).as_posix()
            warnings.append(
                f"{rel}: {size} bytes; a spec stays under {SPEC_MAX_BYTES}, "
                "and a longer one is a sign the brief asked for the plan"
            )
    return warnings


def _documents(root: Path) -> list[Path]:
    """Every document under docs/: generated ones are compared on their own; handoffs are a session's notes, not
    documents, and not committed."""
    found = (root / "docs").rglob("*.md")
    return sorted(p for p in found if not {"generated", "handoff"} & set(p.relative_to(root).parts))


def index_problems(root: Path) -> list[str]:
    """docs/llms.txt and each README.md or index.md under docs/ that is larger than INDEX_MAX_BYTES; the copy of the
    template's README that a project keeps (KEPT_README) is a document, not an index."""
    named = (p for p in _documents(root) if p.name in ("README.md", "index.md"))
    indexes = [p for p in named if p.relative_to(root).parts != KEPT_README]
    problems = []
    for path in [root / "docs" / "llms.txt", *indexes]:
        size = len(path.read_bytes()) if path.is_file() else 0
        if size > INDEX_MAX_BYTES:
            rel = path.relative_to(root).as_posix()
            problems.append(f"{rel}: {size} bytes; an index stays at most {INDEX_MAX_BYTES}")
    return problems


def docs_check(root: Path) -> dict:
    """`harness docs-check` (ADR-0026): every document under docs/ is listed in docs/llms.txt or in a folder index it
    links (`listed`; a `.summary.md` summary needs no line), relative links outside code resolve,
    docs/generated/role-types.md and every map under docs/generated/maps/ match what their sources produce now, every
    index stays at most INDEX_MAX_BYTES, and plan-lint passes. A page under SUMMARY_FOLDERS without its summary and a
    specs/*/spec.md that is not under SPEC_MAX_BYTES bytes are warnings, sorted by path, which never change `ok`."""
    problems = []
    llms = (root / "docs" / "llms.txt").read_text(encoding="utf-8")
    docs = _documents(root)
    for p in docs:
        rel = p.relative_to(root / "docs").as_posix()
        if p.name != "adr-template.md" and not p.name.endswith(".summary.md") and not listed(root, rel, llms):
            problems.append(f"docs/llms.txt: {rel} is not listed")
    for p in docs + [root / "CLAUDE.md", root / "AGENTS.md", root / "ARCHITECTURE.md", root / "README.md"]:
        if not p.exists():
            continue
        for target in LINK.findall(prose(p.read_text(encoding="utf-8"))):
            if "://" in target or target.startswith("mailto:"):
                continue
            if not (p.parent / target).resolve().exists():
                problems.append(f"{p.relative_to(root)}: broken link {target}")
    generated = root / "docs" / "generated" / "role-types.md"  # compared by content: git does not keep file times
    if not generated.exists() or generated.read_text(encoding="utf-8") != render_catalog(root):
        problems.append("docs/generated/role-types.md does not match .claude/agents/*.md; run `harness catalog`")
    problems += stagemap.docs_problems(root)
    problems += index_problems(root)
    problems += [f"plan-lint: {problem}" for problem in plans.plan_lint(root)["problems"]]
    warnings = sorted([*summary_warnings(root), *spec_size_warnings(root)])
    return {"ok": not problems, "problems": problems, "warnings": warnings}
