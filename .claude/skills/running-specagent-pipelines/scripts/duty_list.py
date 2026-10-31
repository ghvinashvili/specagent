"""The duty list of a run (spec 5.1.2): every merge, request point and the judge's approval, read from the plan.

  python3 -I duty_list.py extract <plan-dir> [--out FILE]
  python3 -I duty_list.py tick <duty-file> <D-id> <evidence>

`extract` reads `<plan-dir>/00-index.md` and the `task-NN.md` files and gives the duties in this order: the merges of
the task table (a dependency in another builder's lane gives `Merged: <y>-><x>`, one per other lane; a `Merged: <m>` in
the depends_on cell replaces them, each marker over the tasks of its own lane), the backticked `Merged:` markers of the
index's prose that the table does not place, the `Request point: <KIND>` lines of the task files outside fenced code
(once per kind per task), and last the judge's approval. Without `--out` it prints the duty lines; with `--out` it
creates the duty file, or appends only the duties the file lacks (compared without their `<name>.md:<line>` sources,
which move between extractions) under a dated `Extracted` line. `tick` marks a duty done with its UTC time and evidence.
`monitor_records.py` imports `DUTY`, `MERGE`, `JUDGE`, `numbers`, `norm`, `parse_duties` and `tick`, and ticks the
merges itself; the point and prose duties are ticked by hand. Standard library only.
"""

import argparse
import datetime
import os
import pathlib
import re
import sys

DUTY = re.compile(
    r"^- \[(?P<mark>[ x])\] (?:(?P<when>(?:\d{4}-\d{2}-\d{2} )?\d{2}:\d{2} UTC)(?: \((?P<evidence>[^)]*)\))? )?"
    r"D(?P<n>\d+) (?P<text>.+)$"
)
MERGE = re.compile(
    r"^Merged: (?P<marker>\S+) — blocks Task (?P<task>\d+) \(builder (?P<lane>[\w-]+)\) — "
    r"due when Tasks? (?P<after>[\d, -]+) done — (?P<source>\S+)$"
)
JUDGE = "judge approval — blocks the judge — due when every record's STATUS is final"
HEADER = "# Duty list (spec 5.1.2): each duty is ticked with its date -u time when done; the monitor ticks the merges."
CODE_SPAN = re.compile(r"`[^`\n]*`")
SEPARATOR = re.compile(r"^\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|?\s*$")
RANGE = re.compile(r"(\d+)(?:\s*[-–]\s*(\d+))?")
MARKER = re.compile(r"Merged: (\S+)")
POINT = re.compile(r"^Request point: (COPY-REQUEST|CHECKOUT-REQUEST|FF-REQUEST)\b")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
SOURCE = re.compile(r"\S+\.md:\d+")
TASK_FILE = re.compile(r"task-(\d+)\.md")


def clock(now: datetime.datetime | None = None) -> str:
    """`YYYY-MM-DD HH:MM UTC` of `now` (default: the current time)."""
    return (now or datetime.datetime.now(datetime.UTC)).astimezone(datetime.UTC).strftime("%Y-%m-%d %H:%M UTC")


def norm(marker: str) -> str:
    """A marker with `→` read as `->`: `b→a` -> `b->a`."""
    return marker.replace("→", "->")


def numbers(cell: str) -> list[int]:
    """The task numbers of a depends_on cell, sorted, each once; code spans skipped, `1-4` read as 1, 2, 3, 4."""
    found: set[int] = set()
    for match in RANGE.finditer(CODE_SPAN.sub(" ", cell)):
        low = int(match.group(1))
        found.update(range(low, int(match.group(2) or low) + 1))
    return sorted(found)


def span(nums: list[int]) -> str:
    """`Task 2`, `Tasks 2, 3, 6, 8`; a run of three or more as a range: `Tasks 1-3, 5, 6`."""
    runs: list[list[int]] = []
    for n in nums:
        if runs and n == runs[-1][-1] + 1:
            runs[-1].append(n)
        else:
            runs.append([n])
    parts = [f"{run[0]}-{run[-1]}" if len(run) >= 3 else ", ".join(map(str, run)) for run in runs]
    return ("Task " if len(nums) == 1 else "Tasks ") + ", ".join(parts)


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


def kept(marker: str, nums: list[int], lane: dict[int, str]) -> list[int]:
    """The tasks a merge waits for: a `<y>-><x>` marker whose y is a builder of the table keeps y's tasks (all of them
    when none is y's); any other marker (`a+b+c+d`, `main->plan`) keeps them all (critic C12)."""
    first, arrow, _ = norm(marker).partition("->")
    if arrow and first in lane.values():
        return [n for n in nums if lane.get(n) == first] or nums
    return nums


def table_merges(rows: list[tuple[int, int, str, str]]) -> list[str]:
    """The merge duties of the task table, in row order: the cell's markers in cell order (over every lower task when
    the cell has no number), else one implied `<y>-><x>` per other lane in the order of its first number."""
    lane = {task: builder for _, task, builder, _ in rows}
    duties = []
    for line, task, builder, cell in rows:
        nums = numbers(cell)
        markers = [m.group(1) for code in CODE_SPAN.finditer(cell) if (m := MARKER.match(code.group()[1:-1]))]
        if markers and not nums:
            nums = list(range(1, task))
        if not markers:
            others = dict.fromkeys(lane[n] for n in nums if lane.get(n, builder) != builder)
            markers = [f"{other}->{builder}" for other in others]
        for marker in markers:
            after = span(kept(marker, nums, lane))
            duties.append(
                f"Merged: {marker} — blocks Task {task} (builder {builder}) — due when {after} done"
                f" — 00-index.md:{line}"
            )
    return duties


def prose_markers(lines: list[str], table: range, placed: set[str]) -> list[str]:
    """The backticked `Merged: <m> …` of the index outside the task table whose marker the table does not place,
    once per marker (`→` read as `->`); the text keeps the marker as first written."""
    duties, seen = [], set(placed)
    for number, line in enumerate(lines, 1):
        if number in table:
            continue
        for code in CODE_SPAN.finditer(line):
            match = MARKER.match(code.group()[1:-1])
            if match and norm(match.group(1)) not in seen:
                seen.add(norm(match.group(1)))
                duties.append(
                    f"Merged: {match.group(1)} — blocks: see 00-index.md:{number}"
                    " (a marker the task table does not place)"
                )
    return duties


def unfenced(text: str) -> list[tuple[int, str]]:
    """(line number, line) of each line outside fenced code (CommonMark: a fence of three or more backticks or tildes
    indented at most three spaces closes on a line of that character alone, at least as long)."""
    found, fence = [], ""
    for number, line in enumerate(text.splitlines(), 1):
        if fence:
            bare = line.strip()
            if len(line) - len(line.lstrip(" ")) <= 3 and len(bare) >= len(fence) and set(bare) == {fence[0]}:
                fence = ""
        elif match := FENCE.match(line):
            fence = match.group(1)
        else:
            found.append((number, line))
    return found


def points(plan: pathlib.Path, lane: dict[int, str]) -> list[str]:
    """The `Request point: <KIND>` lines of the task files (sorted by name), outside fenced code, at a line start,
    once per kind per task: a mention in prose or a test's fixture is no point (departure 4)."""
    duties = []
    for path in sorted(plan.glob("task-*.md")):
        found = TASK_FILE.fullmatch(path.name)
        if not found:
            continue
        task, kinds = int(found.group(1)), {}
        for number, line in unfenced(path.read_text(encoding="utf-8")):
            match = POINT.match(line)
            if match and match.group(1) not in kinds:
                kinds[match.group(1)] = number
        builder = lane.get(task, "-")
        duties += [
            f"{kind} point — blocks Task {task} (builder {builder}) — {path.name}:{n}" for kind, n in kinds.items()
        ]
    return duties


def extract(plan: pathlib.Path) -> list[str]:
    """The duty texts of a plan folder; ValueError(<the stderr text>) without a task table."""
    index = plan / "00-index.md"
    lines = index.read_text(encoding="utf-8").splitlines() if index.is_file() else []
    table = task_table(lines)
    if table is None:
        raise ValueError(f"{index}: no task table with Task, builder and depends_on columns")
    rows, table_lines = table
    merges = table_merges(rows)
    placed = {norm(text.split(" — ", 1)[0].removeprefix("Merged: ")) for text in merges}
    lane = {task: builder for _, task, builder, _ in rows}
    return merges + prose_markers(lines, table_lines, placed) + points(plan, lane) + [JUDGE]


def parse_duties(text: str) -> list[dict]:
    """The DUTY lines of a duty file, hand-written ones too: {"n", "done", "when", "evidence", "text", "line"} each."""
    return [
        {
            "n": int(match["n"]),
            "done": match["mark"] == "x",
            "when": match["when"],
            "evidence": match["evidence"],
            "text": match["text"],
            "line": number,
        }
        for number, line in enumerate(text.splitlines(), 1)
        if (match := DUTY.match(line))
    ]


def key(text: str) -> str:
    """A duty's text without its `<name>.md:<line>` sources, which move between extractions."""
    return SOURCE.sub("", text).strip()


def merge_into(existing: str, texts: list[str], when: str, source: str) -> tuple[str, int]:
    """`existing` with the duties of `texts` whose key it lacks appended under an `Extracted` line, numbered after its
    highest D, and their count; `existing` unchanged when none is new. An empty `existing` starts with HEADER."""
    duties = parse_duties(existing)
    keys, last, new = {key(duty["text"]) for duty in duties}, max((duty["n"] for duty in duties), default=0), []
    for text in texts:
        if key(text) not in keys:
            keys.add(key(text))
            new.append(f"- [ ] D{last + len(new) + 1} {text}\n")
    if not new:
        return existing, 0
    head = existing if existing.strip() else f"{HEADER}\n\n"
    head += "" if head.endswith("\n") else "\n"
    return f"{head}Extracted {when} from {source}: {len(new)} new duties.\n{''.join(new)}", len(new)


def tick(text: str, n: int, evidence: str, when: str) -> str:
    """`text` with duty D<n> as `- [x] <when> (<evidence>) D<n> <text>`; a parenthesis or line break in the evidence
    becomes a bracket or a space, so the line still parses. KeyError("no D<n>"); ValueError when ticked already."""
    lines = text.splitlines(keepends=True)
    evidence = " ".join(evidence.replace("(", "[").replace(")", "]").split())
    for duty in parse_duties(text):
        if duty["n"] != n:
            continue
        if duty["done"]:
            raise ValueError(f"D{n} is ticked already ({duty['when'] or 'no time'})")
        end = "\n" if lines[duty["line"] - 1].endswith("\n") else ""
        lines[duty["line"] - 1] = f"- [x] {when} ({evidence}) D{n} {duty['text']}{end}"
        return "".join(lines)
    raise KeyError(f"no D{n}")


def write(path: pathlib.Path, text: str) -> None:
    """Write `text` whole: the folder made, a temporary file beside `path`, then os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def run_extract(plan: pathlib.Path, out: pathlib.Path | None) -> int:
    """The `extract` command: print the duty lines, or create or extend the duty file."""
    try:
        texts = extract(plan)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    if out is None:
        print("\n".join(f"- [ ] D{k} {text}" for k, text in enumerate(texts, 1)))
        return 0
    existing = out.read_text(encoding="utf-8") if out.is_file() else ""
    text, new = merge_into(existing, texts, clock(), str(plan / "00-index.md"))
    if new:
        write(out, text)
    print(f"{out}: {new} new duties")
    return 0


def run_tick(path: pathlib.Path, duty: str, evidence: str) -> int:
    """The `tick` command: one duty ticked with the current UTC time."""
    found = re.fullmatch(r"D?(\d+)", duty)
    if not path.is_file():
        print(f"{path}: no such duty file", file=sys.stderr)
        return 2
    try:
        if not found:
            raise KeyError(f"no {duty}")
        write(path, tick(path.read_text(encoding="utf-8"), int(found.group(1)), evidence, clock()))
    except (KeyError, ValueError) as e:
        print(f"{path}: {e.args[0]}", file=sys.stderr)
        return 2
    print(f"ticked D{int(found.group(1))}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The duty list of a run: extract it from the plan, or tick one duty.")
    commands = parser.add_subparsers(dest="command", required=True)
    extract_cmd = commands.add_parser("extract", help="the duties of a plan folder")
    extract_cmd.add_argument("plan", type=pathlib.Path, help="the folder of 00-index.md and the task-NN.md files")
    extract_cmd.add_argument("--out", type=pathlib.Path, help="the duty file: created, or given only its new duties")
    tick_cmd = commands.add_parser("tick", help="mark one duty done with its UTC time and evidence")
    tick_cmd.add_argument("file", type=pathlib.Path, help="the duty file")
    tick_cmd.add_argument("duty", help="D<n>")
    tick_cmd.add_argument("evidence", help="what proves it done, e.g. `lessons.md:4, abc1234`")
    args = parser.parse_args(argv)
    if args.command == "extract":
        return run_extract(args.plan, args.out)
    return run_tick(args.file, args.duty, args.evidence)


if __name__ == "__main__":
    sys.exit(main())
