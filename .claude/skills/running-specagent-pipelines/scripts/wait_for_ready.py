#!/usr/bin/env python3
"""Builder's waiter: exit 0 when Task N is ready to build.
Polls every 30 s and returns within 3.5 min (exit 3 and the line to run it again), so the caller's next call
comes within the prompt cache's 5 minutes (owner, 2026-11-01); a wait known to be longer than about an hour ends the
session instead, and the watcher relaunches it on work.

  python3 wait_for_ready.py --critique critique.md --response critique-response.md N
Ready: the critique's first line is 'STATUS: caught up through Task M' or 'STATUS: reviewed through Task M' with M >= N
(or 'STATUS: done'), and every '#### C<n>' / '#### A<n>' id filed under the shared sections or under Tasks 1..N has a
'<id>:' answer line in the response file. Sections are '##' or '###' headings; 'Task <n>' headings mark a task, any
other heading counts as shared.
  --index 00-index.md --lane a: only the ids of the lane's own tasks up to N in the index's build order (the rows with
that builder of the index's task table, read by its header as duty_list.py reads it) and of Task N's `depends_on`
tasks (a range `1-4` is each of its tasks) count, with the shared sections: the other lane's open ids never hold this
one (a project's run of 2026-11-02: 107 idle minutes). Without them every task 1..N counts. An index that is missing,
holds no task table or has no Task N in the lane stops the waiter at its first call, exit 2 and the reason on stderr,
because a gate that read nothing would release the task.
  --once: one check, no polling; prints its line and exits 0 when Task N is ready now, 3 when not.
"""

import argparse
import pathlib
import re
import sys
import time
from typing import NoReturn

ap = argparse.ArgumentParser()
ap.add_argument("--critique", required=True)
ap.add_argument("--response", required=True)
ap.add_argument("task", type=int)
ap.add_argument("--once", action="store_true")
ap.add_argument("--index", help="the plan's 00-index.md: its `## Task order` table gives each task's builder")
ap.add_argument("--lane", help="this builder's lane (`a`, `b`): with --index, only its build order counts")
args = ap.parse_args()
if bool(args.index) != bool(args.lane):
    ap.error("--index and --lane go together")


def text(path):
    p = pathlib.Path(path)
    return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""


# The index reader of duty_list.py, copied because this script runs alone from the run folder (SKILL.md: the waiters are
# copied there); test_waiters.py holds the copy to the original, character for character, so the waiter and the duty
# list read an index alike.
CODE_SPAN = re.compile(r"`[^`\n]*`")
SEPARATOR = re.compile(r"^\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|?\s*$")
RANGE = re.compile(r"(\d+)(?:\s*[-–]\s*(\d+))?")


def numbers(cell: str) -> list[int]:
    """The task numbers of a depends_on cell, sorted, each once; code spans skipped, `1-4` read as 1, 2, 3, 4."""
    found: set[int] = set()
    for match in RANGE.finditer(CODE_SPAN.sub(" ", cell)):
        low = int(match.group(1))
        found.update(range(low, int(match.group(2) or low) + 1))
    return sorted(found)


def cells(row: str) -> list[str]:
    """The cells of a table row, split on `|` outside code spans (a backticked `a|b` stays in one cell)."""
    masked = CODE_SPAN.sub(lambda m: m.group().replace("|", "\0"), row.strip())
    parts = masked.split("|")
    if masked.startswith("|"):
        parts = parts[1:]
    if masked.endswith("|") and parts:
        parts = parts[:-1]
    return [part.replace("\0", "|").strip() for part in parts]


def task_table(lines: list[str]) -> tuple[list[tuple[int, int, str, str]], range] | None:
    """The first table whose header has a cell starting `task`, a cell `builder` and a cell starting `depends_on`
    (case ignored): its rows as (line, task, builder, depends_on cell) and its line numbers; None without one."""
    for i in range(len(lines) - 1):
        if not lines[i].lstrip().startswith("|") or not SEPARATOR.match(lines[i + 1]):
            continue
        head = [cell.lower() for cell in cells(lines[i])]
        task = next((k for k, cell in enumerate(head) if cell.startswith("task")), None)
        builder = head.index("builder") if "builder" in head else None
        depends = next((k for k, cell in enumerate(head) if cell.startswith("depends_on")), None)
        if task is None or builder is None or depends is None:
            continue
        end, rows = i + 2, []
        while end < len(lines) and lines[end].lstrip().startswith("|"):
            row = cells(lines[end])
            number = re.search(r"\d+", row[task]) if len(row) > max(task, builder, depends) else None
            if number:
                rows.append((end + 1, int(number.group()), row[builder].strip("`"), row[depends]))
            end += 1
        return rows, range(i + 1, end + 1)
    return None


def fail(reason) -> NoReturn:
    """Stop with exit 2 and the reason on stderr: a gate that cannot read its index must not release the task."""
    print(f"wait_for_ready: {reason}", file=sys.stderr)
    sys.exit(2)


def rows(index):
    """The index's task table as (task, builder, depends_on tasks), in the table's order, read as the duty list reads
    it (by the header's Task, builder and depends_on cells; a range `1-4` in depends_on is each of its tasks)."""
    path = pathlib.Path(index)
    if not path.is_file():
        fail(f"--index {index}: no such file")
    table = task_table(path.read_text(encoding="utf-8", errors="ignore").splitlines())
    if table is None:
        fail(f"{index}: no task table with Task, builder and depends_on columns")
    return [
        (task, builder.lower().removeprefix("builder").strip(" :"), set(numbers(cell)))
        for _, task, builder, cell in table[0]
    ]


def counted(n):
    """The tasks whose ids hold Task N: the lane's tasks up to N in build order and N's depends_on; else 1..N."""
    if not args.index:
        return set(range(1, n + 1))
    order = rows(args.index)
    lane = [task for task, builder, _ in order if builder == args.lane.lower()]
    if n not in lane:
        builders = ", ".join(sorted({builder for _, builder, _ in order}))
        fail(f"{args.index}: Task {n} is not a task of lane {args.lane} (the builders of its task table: {builders})")
    return set(lane[: lane.index(n) + 1]) | next(deps for task, _, deps in order if task == n)


def state(n):
    critique, response = text(args.critique), text(args.response)
    first = critique.splitlines()[0] if critique else ""
    m = re.match(r"STATUS: (?:caught up|reviewed) through Task (\d+)", first)
    reviewed = 10**6 if first.startswith("STATUS: done") else (int(m.group(1)) if m else 0)
    if reviewed < n or not response:
        return f'not ready: critic says "{first or "no critique yet"}"', False
    section, needed, tasks = 0, set(), counted(n)
    for line in critique.splitlines():
        if not line.startswith("####"):
            h = re.match(r"#{2,3} (.+)", line)
            if h:
                t = re.match(r"Task (\d+)", h.group(1).strip())
                section = int(t.group(1)) if t else 0
        i = re.match(r"#### ([CA]\d+)\b", line)
        if i and (section == 0 or section in tasks):
            needed.add(i.group(1))
    missing = sorted(needed - set(re.findall(r"^([CA]\d+):", response, re.MULTILINE)), key=lambda s: (s[0], int(s[1:])))
    return (f"Task {n} ready" if not missing else f"not ready: unanswered {', '.join(missing[:15])}"), not missing


# an index that cannot be used stops the waiter at its first call, not when the critic has caught up
if args.index:
    counted(args.task)
deadline = time.monotonic() + 210
while True:
    message, ready = state(args.task)
    if ready or args.once:
        print(message)
        sys.exit(0 if ready else 3)
    if time.monotonic() + 30 > deadline:
        break
    time.sleep(30)
print(f"{message}. Run the same command again now: a call within 5 min keeps the prompt cache warm")
sys.exit(3)
