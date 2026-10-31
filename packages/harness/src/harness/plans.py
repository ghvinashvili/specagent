"""Plans as part folders (spec A4, ADR-0026): `harness plan-lint` checks each folder under
docs/exec-plans/active/ against the task order of its 00-index.md, and each task's `task-NN.code.md` against the blocks
its steps name (the plan split, docs/design-docs/pipeline-fold.md, Decided 4)."""

from __future__ import annotations

import re
from pathlib import Path

MAX_TASK_LINES = 1500  # owner, 2026-10-28 (spec A4, B5): a longer task is split, or its growth goes to Deferred
TASK_FILE = re.compile(r"task-(\d{2,})\.md")  # fullmatch on a file name
CODE_FILE = re.compile(r"task-(\d{2,})\.code\.md")  # fullmatch on a file name: a task's blocks, with no line limit
ROW = re.compile(r"\|\s*(\d+)\s*\|")  # match at the start of a line inside the task order section
HEADING = re.compile(r"# Task (\d+)(?: |$)")  # match on the first line of a task file
BLOCK_HEADING = re.compile(r"^## Block ([0-9]+[a-z]?)\s*$", re.MULTILINE)  # a block of a code file: `## Block 3b`
BLOCK_REF = re.compile(r"\bBlock ([0-9]+[a-z]?)\b")  # a step naming a block, in prose or inside a short fence
FENCE = re.compile(r" {0,3}(`{3,}|~{3,})(.*)")  # match: a line that opens or closes a code fence, as catalog.FENCE


def count_lines(text: str) -> int:
    """Lines as `wc -l` counts them, plus a last line without a newline: only a newline ends a line."""
    return text.count("\n") + (1 if text and not text.endswith("\n") else 0)


def task_numbers(index_text: str) -> list[int]:
    """The numbers of the rows of the `## Task order` table, in order and with repeats; [] without the section."""
    numbers, inside = [], False
    for line in index_text.split("\n"):  # never splitlines(): it splits at U+2028 and form feeds
        if line.startswith(("## ", "# ")):
            inside = line.rstrip() == "## Task order"
        elif inside and (row := ROW.match(line)):
            numbers.append(int(row.group(1)))
    return numbers


def block_ids(code_text: str) -> list[str]:
    """The ids of a code file's `## Block <id>` headings, in order and with repeats. A line inside a fenced code block is
    code, not a heading; fences are read as catalog.prose reads them (CommonMark), which this module cannot import since
    catalog imports it: only a bare run of the opening character, at least as long, closes a fence, and an unclosed
    fence runs to the end of the file."""
    ids, fence = [], ""
    for line in code_text.split("\n"):  # never splitlines(): it splits at U+2028 and form feeds
        mark = FENCE.match(line)
        if fence:
            if mark and mark.group(1)[0] == fence[0] and len(mark.group(1)) >= len(fence) and not mark.group(2).strip():
                fence = ""
        elif mark:
            fence = mark.group(1)
        elif heading := BLOCK_HEADING.match(line):
            ids.append(heading.group(1))
    return ids


def _task_problems(folder: Path, name: str, number: int, order: set[int]) -> list[str]:
    """The heading, length and order problems of one task file, in that order."""
    plan, text = folder.name, (folder / name).read_text(encoding="utf-8")
    heading = HEADING.match(text.split("\n", 1)[0])
    problems = []
    if not heading or int(heading.group(1)) != number:
        problems.append(f"{plan}/{name}: the first line must be '# Task {number} — <title>'")
    lines = count_lines(text)
    if lines > MAX_TASK_LINES:
        problems.append(f"{plan}/{name}: {lines} lines, more than {MAX_TASK_LINES}")
    if number not in order:
        problems.append(f"{plan}/{name}: not in the task order of 00-index.md")
    return problems


def code_problems(folder: Path, name: str, number: int, tasks: dict[str, int]) -> list[str]:
    """Rules 1-4 of the plan split for task `number`: `name` is its `task-NN.code.md`, which may be missing (then it
    defines no block), and `tasks` maps the folder's task files to their numbers. A code file without its task file has
    that problem alone; else a block the steps name and no heading defines, a heading twice and a heading no step names
    are one problem each per block id, in that order."""
    plan, code, steps = folder.name, folder / name, f"task-{number:02d}.md"
    if steps not in tasks:
        return [f"{plan}/{name}: no {steps} beside it"] if code.is_file() else []
    defined = block_ids(code.read_text(encoding="utf-8")) if code.is_file() else []
    named = dict.fromkeys(BLOCK_REF.findall((folder / steps).read_text(encoding="utf-8")))  # a fence counts (rule 5)
    problems = [f"{plan}/{steps}: names Block {b}, not in {name}" for b in named if b not in defined]
    problems += [f"{plan}/{name}: Block {b} twice" for b in dict.fromkeys(defined) if defined.count(b) > 1]
    problems += [f"{plan}/{name}: Block {b} is named by no step" for b in dict.fromkeys(defined) if b not in named]
    return problems


def _lint_folder(folder: Path) -> tuple[dict, list[str]]:
    """One plan folder against its index: the plan's entry and its problems, in the order of ADR-0026's contract, then
    the code files' problems when the folder holds one."""
    plan, files = folder.name, sorted(p.name for p in folder.iterdir() if p.is_file())
    tasks = {name: int(m.group(1)) for name in files if (m := TASK_FILE.fullmatch(name))}
    codes = {name: int(m.group(1)) for name in files if (m := CODE_FILE.fullmatch(name))}
    blocks = sum(len(block_ids((folder / name).read_text(encoding="utf-8"))) for name in codes)
    index = folder / "00-index.md"
    if not index.is_file():
        return {"plan": plan, "tasks": 0, "written": len(tasks), "blocks": blocks}, [f"{plan}: no 00-index.md"]
    numbers = task_numbers(index.read_text(encoding="utf-8"))
    order = dict.fromkeys(numbers)  # the distinct numbers, in the order of their first row
    entry = {"plan": plan, "tasks": len(order), "written": len(tasks), "blocks": blocks}
    if not numbers:
        return entry, [f"{plan}/00-index.md: no task order (a '## Task order' table with rows '| N | ...')"]
    problems = [f"{plan}/00-index.md: Task {n} appears twice in the task order" for n in order if numbers.count(n) > 1]
    problems += [
        f"{plan}/task-{n:02d}.md: named in 00-index.md but missing" for n in order if f"task-{n:02d}.md" not in tasks
    ]
    for name, number in tasks.items():
        problems += _task_problems(folder, name, number, set(order))
    if codes:  # rule 2's scope: a folder that holds a code file; an older plan names blocks without one
        names = {n: f"task-{n:02d}.code.md" for n in tasks.values()} | {n: name for name, n in codes.items()}
        for n in sorted(names):
            problems += code_problems(folder, names[n], n, tasks)
    return entry, problems


def plan_lint(root: Path) -> dict:
    """`harness plan-lint`: every plan folder under docs/exec-plans/active/ against its index (spec A4).
    Returns {"ok": bool, "plans": [{"plan", "tasks", "written", "blocks"}], "problems": [...]}."""
    active = root / "docs" / "exec-plans" / "active"
    entries, problems = [], []
    if active.is_dir():  # files directly in active/ (its README, single-file plans, plan-mode drafts) are not linted
        for folder in sorted(p for p in active.iterdir() if p.is_dir() and not p.name.startswith(".")):
            entry, found = _lint_folder(folder)
            entries.append(entry)
            problems += found
    return {"ok": not problems, "plans": entries, "problems": problems}
