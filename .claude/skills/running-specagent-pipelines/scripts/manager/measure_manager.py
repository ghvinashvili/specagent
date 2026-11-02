"""The manager measured as it measures the roles: its first call, every call against the cap with a hand-off before
each compaction, its lessons page read early and kept in form, and the findings per `Checklist:` item (spec 5.8, 7.3,
7.6, 7.7; acceptance 10.1, 10.2, 10.13).

A call is one message id of a transcript, its context the input, cache write and cache read tokens of its usage
(usage_report.py's `calls`, `lines` and `context`; a '<synthetic>' line is no call). A compaction is a system line with
subtype `compact_boundary`; its hand-off is the newest `*-handoff.md` directly in the hand-off folder whose mtime is
after the compaction before (for the first: the transcript's first timestamp) and at or before the compaction, every
time in UTC. An item of the lessons page is a line `<n>. <trigger> -> <rule>; cost measured <cost>; <YYYY-MM-DD>,
<record>` at the line start (more `; <YYYY-MM-DD>, <record>` firings may follow, the arrow may be U+2192, and an
indented non-blank line right after it continues it); its numbers may have gaps and are never reused. Two states
say that a number is missing and are valid: `cost unmeasured` in place of the measured cost, and `no record` in place of
a firing's file; `lessons` reports them as `unmeasured: <n>` with the items' numbers.

  python3 -I scripts/manager/measure_manager.py first-call TRANSCRIPT... [--limit 30000]
  python3 -I scripts/manager/measure_manager.py calls TRANSCRIPT [--cap 200000] [--handoff-dir DIR]
  python3 -I scripts/manager/measure_manager.py reads TRANSCRIPT TEXT [--calls 5]
  python3 -I scripts/manager/measure_manager.py lessons PAGE [--max-bytes 8000] [--since YYYY-MM-DD]
  python3 -I scripts/manager/measure_manager.py checklist RECORD...

Exit codes: 0 every check passed; 1 a check failed or a `Checklist:` line is malformed; 2 a path that is not there
(`measure_manager: <path>: no such file` on stderr, nothing on stdout) or cannot be read, and argparse's own 2.
"""

import argparse
import collections
import datetime
import json
import os
import pathlib
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import usage_report as ur

ITEM = re.compile(r"(\d+)\. (.*)")  # an item of the lessons page, matched at the line start
ARROW = re.compile(" (?:->|" + chr(0x2192) + ") ")  # the form's "->" or the spec's U+2192, a space on each side
COST = re.compile(r"; cost (?:measured [^;]*\d|unmeasured\b)")  # a digit before the next ";", or said unmeasured
UNMEASURED = re.compile(r"; cost unmeasured\b")
NO_RECORD = "no record"
FIRING = re.compile(r"; (\d{4}-\d{2}-\d{2}), ([^;]*)")  # one firing of an item: its date and its record
FILE_NAME = re.compile(r"\w\.[A-Za-z]\w*")  # a record names a file
CITED = re.compile(r"\S+:\d+")  # the one `<file>:<line>` token of a Checklist: line
HANDOFF = "*-handoff.md"  # .claude/hooks/handoff.py:4 writes docs/handoff/<date>-<time>-handoff.md
PATHS = {"first-call": "transcripts", "calls": "transcript", "reads": "transcript", "lessons": "page"}


def context(line: dict) -> int:
    """The context of the call a transcript line belongs to."""
    return ur.context(line["message"]["usage"])


def first_call(args: argparse.Namespace) -> int:
    """One line per transcript, in the given order: its first call against --limit (passes under it)."""
    failed = False
    for path in args.transcripts:
        first = next(ur.calls(path), None)
        if first is None:
            print(f"{path}: no call: fail")
            failed = True
            continue
        n = context(first)
        failed |= n >= args.limit
        print(f"{path}: first call {n} tokens, limit {args.limit}: {'pass' if n < args.limit else 'fail'}")
    return 1 if failed else 0


def compactions(path: str) -> tuple[str | None, list[tuple[str | None, object]]]:
    """The transcript's first timestamp and its compactions as (timestamp, preTokens), in file order."""
    first, found = None, []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if first is not None and '"compact_boundary"' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict):
                continue
            first = first or d.get("timestamp")
            if d.get("type") == "system" and d.get("subtype") == "compact_boundary":
                found.append((d.get("timestamp"), (d.get("compactMetadata") or {}).get("preTokens")))
    return first, found


def moment(text: object) -> float | None:
    """A transcript's time in seconds since the epoch (a time without a zone is UTC), or None when it is no ISO time."""
    try:
        t = datetime.datetime.fromisoformat(str(text))
    except ValueError:
        return None
    return (t if t.tzinfo else t.replace(tzinfo=datetime.UTC)).timestamp()


def handoff_lines(path: str, folder: str) -> list[tuple[bool, str]]:
    """(passed, line) per compaction: the newest hand-off written after the bound and at or before the compaction."""
    first, found = compactions(path)
    notes = [(p.stat().st_mtime, p.name) for p in pathlib.Path(folder).glob(HANDOFF) if p.is_file()]
    lines, bound = [], first
    for at, pre in found:
        low, high = moment(bound), moment(at)
        fits = [] if low is None or high is None else [note for note in notes if low < note[0] <= high]
        head = f"compaction {at} ({pre} tokens before):"
        if fits:
            mtime, name = max(fits)
            written = datetime.datetime.fromtimestamp(mtime, datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            lines.append((True, f"{head} hand-off {name} at {written}: pass"))
        else:
            lines.append((False, f"{head} no hand-off since {bound}: fail"))
        bound = at
    return lines


def calls(args: argparse.Namespace) -> int:
    """The calls of one transcript against --cap and, with --handoff-dir, a hand-off before each compaction."""
    found = [(context(d), d.get("timestamp")) for d in ur.calls(args.transcript)]
    over = [(i, n, at) for i, (n, at) in enumerate(found, 1) if n > args.cap]
    if found:
        i = max(range(len(found)), key=lambda j: found[j][0])  # max keeps the first of equal maxima
        n, at = found[i]
        head = f"{args.transcript}: {len(found)} calls, max {n} tokens at call {i + 1} ({at}), cap {args.cap}"
        print(f"{head}: {'fail' if over else 'pass'}")
    else:
        print(f"{args.transcript}: no call: fail")
    for i, n, at in over:
        print(f"over cap: call {i} {n} tokens ({at})")
    failed = not found or bool(over)
    for passed, line in handoff_lines(args.transcript, args.handoff_dir) if args.handoff_dir is not None else []:
        print(line)
        failed |= not passed
    return 1 if failed else 0


def tool_inputs(line: dict) -> list[str]:
    """The JSON input of each tool_use block of a transcript line."""
    content = line["message"].get("content")
    blocks = [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []
    return [json.dumps(b.get("input"), ensure_ascii=False) for b in blocks if b.get("type") == "tool_use"]


def reads(args: argparse.Namespace) -> int:
    """TEXT in the JSON input of a tool call among the first --calls calls, numbered by message id in file order."""
    numbers: dict[object, int] = {}
    hits = []
    for key, line in ur.lines(args.transcript):
        k = numbers.setdefault(key, len(numbers) + 1)
        if k <= args.calls and any(args.text in given for given in tool_inputs(line)):
            hits.append(k)
    if hits:
        print(f"{args.transcript}: {args.text} in call {min(hits)} of the first {args.calls}: pass")
        return 0
    print(f"{args.transcript}: {args.text} not in the first {args.calls} calls: fail")
    return 1


def items(text: str) -> list[tuple[int, int, str]]:
    """(line number, item number, text) per item of a lessons page: a line `<n>. <text>` at the line start, with each
    indented non-blank line right after it (or after such a line) joined on with one space."""
    found: list[tuple[int, int, list[str]]] = []
    joining = False
    for n, line in enumerate(text.splitlines(), 1):
        match = ITEM.match(line)
        continues = joining and line[:1].isspace() and bool(line.strip())
        if match:
            found.append((n, int(match[1]), [match[2]]))
        elif continues:
            found[-1][2].append(line.strip())
        joining = bool(match) or continues
    return [(n, number, " ".join(parts)) for n, number, parts in found]


def item_problems(text: str) -> list[str]:
    """What one item lacks of the form: the arrow, a measured cost with a digit, and at least one dated firing, each
    firing's record naming a file."""
    firings = FIRING.findall(text)
    problems = []
    if not ARROW.search(text):
        problems.append('no "<trigger> -> <rule>"')
    if not COST.search(text):
        problems.append('no "cost measured" with a number')
    if not firings or not all(FILE_NAME.search(record) or no_record(record) for _, record in firings):
        problems.append('no "<date>, <record>" with a file')
    return problems


def no_record(record: str) -> bool:
    """Whether a firing says its record was not kept (`no record`)."""
    return record.strip().lower().startswith(NO_RECORD)


def unmeasured(found: list[tuple[int, int, str]]) -> list[int]:
    """The numbers of the items whose cost or one of whose records is said to be missing."""
    return [n for _, n, text in found if UNMEASURED.search(text) or any(no_record(r) for _, r in FIRING.findall(text))]


def since_lines(found: list[tuple[int, int, str]], since: str) -> list[str]:
    """The items added since the day (their earliest date on or after it), the items fired again since (their later
    dates on or after it, with each item's count) and the recurrences (the sum of those counts)."""
    added, again = [], []
    for _, number, text in found:
        dates = sorted(date for date, _ in FIRING.findall(text))
        if dates and dates[0] >= since:
            added.append(str(number))
        k = sum(date >= since for date in dates[1:])
        if k:
            again.append((number, k))
    fired = ", ".join(f"{number} ({k})" for number, k in again)
    return [
        f"added since {since}: {', '.join(added) or 'none'}",
        f"fired again since {since}: {fired or 'none'}",
        f"recurrences since {since}: {sum(k for _, k in again)}",
    ]


def lessons(args: argparse.Namespace) -> int:
    """The page's size in bytes, its items' form and numbers; with --since, what was added, fired again and recurred."""
    data = pathlib.Path(args.page).read_bytes()
    found = items(data.decode("utf-8", errors="replace"))
    problems: list[str] = []
    first: dict[int, int] = {}
    for n, number, text in found:
        problems += [f"line {n}: item {number}: {problem}" for problem in item_problems(text)]
        if number in first:
            problems.append(f"line {n}: item {number}: number used before at line {first[number]}")
        first.setdefault(number, n)
    if len(data) >= args.max_bytes:
        problems.append(f"page: bytes {len(data)}, not under {args.max_bytes}")
    verdict = "fail" if problems else "pass"
    print(f"{args.page}: bytes {len(data)}, items {len(found)}, problems {len(problems)}: {verdict}")
    missing = unmeasured(found)
    counted = [f"unmeasured: {len(missing)} (items {', '.join(map(str, missing))})"] if missing else []
    for line in problems + counted + (since_lines(found, args.since) if args.since else []):
        print(line)
    return 1 if problems else 0


def checklist(args: argparse.Namespace) -> int:
    """The findings per cited `<file>:<line>` of the records' `Checklist:` lines, highest count first and ties by value;
    then each malformed `Checklist:` line in file order, and the totals."""
    counts: collections.Counter[str] = collections.Counter()
    malformed: list[str] = []
    total = 0
    for record in args.records:
        with open(record, encoding="utf-8", errors="replace") as f:
            for n, line in enumerate(f, 1):
                if not line.startswith("Checklist:"):
                    continue
                total += 1
                value = line.removeprefix("Checklist:").strip()
                if CITED.fullmatch(value):
                    counts[value] += 1
                else:
                    malformed.append(f"{record}:{n}: malformed Checklist line: {line.strip()}")
    for value, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])):
        print(f"{count} {value}")
    for line in malformed:
        print(line)
    print(f"total: Checklist lines {total}, items {len(counts)}, malformed {len(malformed)}")
    return 1 if malformed else 0


def missing(args: argparse.Namespace) -> str | None:
    """The first path of the command line that is not there: a file argument that is no file, or a --handoff-dir that
    is no folder; None when every one is there."""
    given = getattr(args, PATHS.get(args.command, "records"))
    for path in given if isinstance(given, list) else [given]:
        if not os.path.isfile(path):
            return path
    folder = getattr(args, "handoff_dir", None)
    return folder if folder is not None and not os.path.isdir(folder) else None


def day(text: str) -> str:
    """A --since value: a date written YYYY-MM-DD; a ValueError otherwise (argparse's usage error, exit 2)."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ValueError(f"not YYYY-MM-DD: {text!r}")
    return datetime.date.fromisoformat(text).isoformat()


def parser() -> argparse.ArgumentParser:
    """The command line: the subcommands first-call, calls, reads, lessons and checklist."""
    ap = argparse.ArgumentParser(prog="measure_manager.py", description="The manager's own measures.")
    sub = ap.add_subparsers(dest="command", required=True)
    helps = {
        "first-call": "the first call of each transcript against --limit; exit 1 when one is not under it",
        "calls": "every call against --cap and, with --handoff-dir, a hand-off written before each compaction",
        "reads": "TEXT in a tool call of the first --calls calls (the lessons page read early)",
        "lessons": "the lessons page's item form and size and, with --since, what was added and fired again",
        "checklist": "the findings per cited Checklist: item, highest count first; exit 1 on a malformed line",
    }
    commands = {name: sub.add_parser(name, help=text) for name, text in helps.items()}
    commands["first-call"].add_argument("transcripts", nargs="+", metavar="TRANSCRIPT")
    commands["first-call"].add_argument("--limit", type=int, default=30_000, help="tokens (default: 30000)")
    commands["calls"].add_argument("transcript", metavar="TRANSCRIPT")
    commands["calls"].add_argument("--cap", type=int, default=200_000, help="tokens (default: 200000)")
    commands["calls"].add_argument("--handoff-dir", metavar="DIR", help="the folder of the *-handoff.md notes")
    commands["reads"].add_argument("transcript", metavar="TRANSCRIPT")
    commands["reads"].add_argument("text", metavar="TEXT")
    commands["reads"].add_argument("--calls", type=int, default=5, help="the first calls searched (default: 5)")
    commands["lessons"].add_argument("page", metavar="PAGE")
    commands["lessons"].add_argument("--max-bytes", type=int, default=8_000, help="the size limit (default: 8000)")
    commands["lessons"].add_argument("--since", type=day, metavar="YYYY-MM-DD", help="added and fired again since")
    commands["checklist"].add_argument("records", nargs="+", metavar="RECORD")
    return ap


COMMANDS = {"first-call": first_call, "calls": calls, "reads": reads, "lessons": lessons, "checklist": checklist}


def main(argv: list[str] | None = None) -> int:
    """Run one subcommand: 0 when every check passed, 1 when one failed, 2 for a path that is not there or cannot be
    read (one `measure_manager: ...` line on stderr) and for argparse's usage errors."""
    args = parser().parse_args(argv)
    gone = missing(args)
    if gone is not None:
        print(f"measure_manager: {gone}: no such file", file=sys.stderr)
        return 2
    try:
        return COMMANDS[args.command](args)
    except OSError as error:
        print(f"measure_manager: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
