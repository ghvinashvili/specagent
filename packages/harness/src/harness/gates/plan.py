"""harness/gates/plan.py — the planner stage gate: a plan a writer can carry out without guessing."""

from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema

from .. import state
from ._common import OPEN_MARKER, check, has_sections, result, sections, stage_file, text

REQUIRED = [
    "goal",
    "requirements",
    "phase -1",
    "current state",
    "decisions",
    "approach",
    "trial",
    "reference output",
    "risks",
    "out of scope",
]
ITEM = re.compile(r"^([-*]|\d+[.)])\s+\S")
NOTHING_TO_RUN = re.compile(r"^\W*nothing to run\b", re.IGNORECASE)
PATCH_FILE = re.compile(r"(?m)^\+\+\+ b/(\S+)")
PASTE_LINES = 150  # fenced code a plan may hold whatever its length: shapes, signatures, excerpts
PASTE_SHARE = 0.4  # beyond that, the share of the plan that may be fenced code


def _body(found: dict[str, str], name: str) -> str:
    """The text under a heading and under the headings below it, up to the next heading that starts another section
    of the plan (`sections` cuts at every heading, and a section of a plan has sub-headings)."""
    out, inside = [], False
    for heading, body in found.items():
        if heading.startswith(name):
            inside = True
        elif inside and any(heading.startswith(other) for other in REQUIRED):
            break
        if inside:
            out.append(body)
    return "\n".join(out)


def questions(stage_dir: Path) -> list[str]:
    """The questions a reader left, as the planner received them: one per line of `input/**/questions.md`."""
    lines: list[str] = []
    inp = stage_dir / "input"
    for path in sorted(inp.rglob("questions.md")) if inp.is_dir() else []:
        rows = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()]
        rows = [ln for ln in rows if ln and not ln.startswith("#")]
        items = [ln for ln in rows if ITEM.match(ln)]  # a list, when the reader wrote one; else every line
        lines += items or [ln for ln in rows if ln.strip(" .").lower() != "none"]
    return lines


def _fenced(md: str) -> int:
    """The lines of a text that stand inside code fences."""
    inside, n = False, 0
    for line in md.splitlines():
        if line.lstrip().startswith("```"):
            inside = not inside
        elif inside:
            n += 1
    return n


def pasted(plan: str) -> str:
    """Why the plan reads as the code of the work and not as its specification, or an empty string. A plan is read
    by the human who approves it and by the verifier; the implementation the planner tried is delivered beside it
    as `output/trial/trial.patch`, where the writer finds it. Seen live: a planner that believed the writer would
    get the plan alone pasted its whole module and test file, 876 of 1,224 lines. The reference output is not
    counted: an exact result is what that section is for."""
    code = _fenced(plan) - _fenced(_body(sections(plan), "reference output"))
    lines = len(plan.splitlines())
    if code > PASTE_LINES and code > PASTE_SHARE * lines:
        return f"{code} of {lines} lines are fenced code; specify the work, the code is in output/trial/trial.patch"
    return ""


def depth_checks(stage_dir: Path, plan: str) -> list[dict]:
    """A plan is exact when its author has built and run the design once, and decided what the reader left open.
    These checks look for the traces of that: a decision per question, the trial's change and its commands, and
    every file the trial changed named in the plan. A plan whose design cannot be run says so in its first words
    under Trial (`nothing to run: <why>`); the human who approves the plan sees that line."""
    found = sections(plan)
    asked = questions(stage_dir)
    decided = _body(found, "decisions")
    open_ = [f"Q{n}" for n in range(1, len(asked) + 1) if not re.search(rf"\bQ{n}\b", decided)]
    trial = _body(found, "trial").strip()
    if NOTHING_TO_RUN.match(trial):
        return [
            check("every question of the reader is decided under Decisions", not open_, ", ".join(open_[:8])),
            check("the design was tried before the plan was written", True, "the plan says: " + trial.splitlines()[0]),
        ]
    patch = text(stage_dir, "output/trial/trial.patch")
    ran = [e for e in result(stage_dir).get("evidence", []) if e.get("command") and "exit_code" in e]
    changed = sorted(set(PATCH_FILE.findall(patch)))
    unnamed = [f for f in changed if f not in plan and str(Path(f).parent) + "/" not in plan]
    how = "" if patch.strip() and ran else "output/trial/trial.patch and evidence entries with command and exit_code"
    return [
        check("every question of the reader is decided under Decisions", not open_, ", ".join(open_[:8])),
        check("the design was tried before the plan was written", bool(patch.strip() and ran), how),
        check("every file the trial changed is named in the plan", not unnamed, ", ".join(unnamed[:6])),
    ]


def tasks_checks(root: Path, stage_dir: Path) -> tuple[list[dict], list[dict]]:
    """Checks on tasks.json that every stage with a task list shares, and the tasks themselves."""
    path = stage_file(stage_dir, "tasks.json")  # None for a link: a gate opens nothing outside the stage
    if path is None:
        misplaced = (stage_dir / "output" / "tasks.json").is_file()
        hint = (
            f"found output/tasks.json; the task list belongs beside result.json: {stage_dir / 'tasks.json'}"
            if misplaced
            else ""
        )
        return [check("tasks.json exists", False, hint)], []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        jsonschema.validate(doc, state.schema(root, "tasks"))
    except (json.JSONDecodeError, jsonschema.ValidationError) as exc:
        return [check("tasks.json is valid against tasks.schema.json", False, str(exc))], []
    tasks = doc["tasks"]
    ids = [t["id"] for t in tasks]
    unknown = sorted({d for t in tasks for d in t.get("depends_on", [])} - set(ids))
    graph = {t["id"]: set(t.get("depends_on", [])) & set(ids) for t in tasks}
    done: set[str] = set()
    while True:  # a task is removed once everything it depends on is removed; what remains is a cycle
        free = {i for i, deps in graph.items() if i not in done and deps <= done}
        if not free:
            break
        done |= free
    return [
        check("tasks.json is valid against tasks.schema.json", True),
        check("task ids are unique", len(ids) == len(set(ids))),
        check("every task has at least one step", all(t["steps"] for t in tasks)),
        check("every depends_on names an existing task", not unknown, ", ".join(unknown)),
        check("the dependency graph has no cycle", len(done) == len(graph), ", ".join(sorted(set(graph) - done))),
    ], tasks


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    plan = text(stage_dir, "output/plan.md")
    missing = has_sections(plan, REQUIRED)
    task_checks, tasks = tasks_checks(root, stage_dir)
    placeholders = [t["id"] for t in tasks if re.search(r"\bTBD\b|\bTODO\b", t["description"] + " ".join(t["steps"]))]
    return [
        check("plan.md exists", bool(plan)),
        check("plan.md has the required sections", not missing, "missing: " + ", ".join(missing)),
        check("no [NEEDS CLARIFICATION: ...] marker is left", not OPEN_MARKER.search(plan)),
        check("the plan specifies the work instead of pasting its code", not pasted(plan), pasted(plan)),
        *depth_checks(stage_dir, plan),
        *task_checks,
        check("at least one task", bool(tasks)),
        check("no task is a placeholder", not placeholders, ", ".join(placeholders)),
        check("no task is marked done by the planner", not any(t["passes"] for t in tasks)),
    ]
