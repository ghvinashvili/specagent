#!/usr/bin/env python3
"""Audit of lessons.md's "Read first" section: the items to review before the section is compacted.

  python3 audit_read_first.py <run-dir> [--today YYYY-MM-DD] [--json]

The section runs from the first `## Read first…` heading of <run-dir>/lessons.md to the next `## ` heading; an item
is a line `<n>. ` at column 0 and the lines after it up to the next item (blank lines at its end are not its own).
An item is flagged for:
- a marker word: `HOLD` and `RESTATED` in capitals (a lowercase `hold` or `restated` is prose), `superseded`,
  `withdrawn` and `no longer` in any case;
- done work: every `Task N`, `M<n>` and `O<n>` it names is done by build-log.md (`Task N: done — <sha>`, as a list
  item too, as check_formats.py reads it; `M<n>: fixed …`, `O<n>: fixed …`). An item that names open work as well is
  not flagged; a name in a code span is an example (`--under "Task 22"`), no work the item names;
- a similar item: difflib.SequenceMatcher's ratio of the two items' words (lowercase, split at whitespace, autojunk
  off) over 0.6. Words, not characters: from 200 characters autojunk drops every character that occurs in more than
  1% of the text, the common letters of prose; two near-identical live items (item 2 of two earlier runs) score
  0.66 on characters, 0.92 on words, two different ones 0.02 and 0.08;
- age: the newest date it names that is not after --today (else the heading's date) is over 7 days back.
Markdown to stdout: one row per flagged item and the share flagged, then the proposed compacted section: the heading,
the preamble and the unflagged items verbatim, then the flagged items verbatim with `[flag: …]` after their number.
Numbers are kept, as items cite each other by number ("after items 10-12"). Read-only: it never edits a file.
Exit 1 when lessons.md has no `## Read first` section, 2 when the file is missing.
"""

import argparse
import datetime
import difflib
import itertools
import json
import pathlib
import re
import sys

sys.dont_write_bytecode = True  # `python3 -I` ignores PYTHONDONTWRITEBYTECODE; the skill folder stays clean
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_formats as cf

SECTION = re.compile(r"^## Read first\b")
ITEM = re.compile(r"^(\d+)\.\s")
MARKERS = (
    ("HOLD", re.compile(r"\bHOLD\b")),
    ("RESTATED", re.compile(r"\bRESTATED\b")),
    ("superseded", re.compile(r"\bsuperseded\b", re.IGNORECASE)),
    ("withdrawn", re.compile(r"\bwithdrawn\b", re.IGNORECASE)),
    ("no longer", re.compile(r"\bno\s+longer\b", re.IGNORECASE)),
)
REF = re.compile(r"\bTask (\d+)\b|" + cf.LESSON_ID.pattern)
FIXED = re.compile(r"^(?:- )?([MO])(\d+): fixed\b", re.MULTILINE)
CODE_SPAN = re.compile(r"`[^`]*`")
DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
SIMILAR = 0.6
MAX_AGE = 7  # days
FLAGGED_LINE = "Flagged (drop, merge or keep each after review; text verbatim, numbers kept):"


def newest_date(text: str, today: datetime.date) -> datetime.date | None:
    dates = []
    for m in DATE.finditer(text):
        try:
            d = datetime.date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if d <= today:
            dates.append(d)
    return max(dates) if dates else None


def done_work(log: str) -> dict[str, int]:
    """`Task N`, `M<n>`, `O<n>` -> the first build-log.md line that finishes it."""
    done: dict[str, int] = {}
    for m in cf.DONE.finditer(log):
        done.setdefault(f"Task {m.group(1)}", cf.line_of(log, m.start()))
    for m in FIXED.finditer(log):
        done.setdefault(m.group(1) + m.group(2), cf.line_of(log, m.start()))
    return done


def named(text: str) -> list[str]:
    """The `Task N`, `M<n>` and `O<n>` an item names outside code spans, in order, once each."""
    refs: list[str] = []
    for m in REF.finditer(CODE_SPAN.sub(" ", text)):
        ref = f"Task {m.group(1)}" if m.group(1) else m.group(2) + m.group(3)
        if ref not in refs:
            refs.append(ref)
    return refs


def audit(text: str, log: str, today: datetime.date) -> dict | None:
    lines = text.split("\n")
    start = next((k for k, line in enumerate(lines) if SECTION.match(line)), None)
    if start is None:
        return None
    end = next((k for k in range(start + 1, len(lines)) if lines[k].startswith("## ")), len(lines))
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    heading = lines[start]
    heading_date = newest_date(heading, today)
    firsts = [k for k in range(start + 1, end) if ITEM.match(lines[k])]
    done = done_work(log)

    items = []
    for a, b in zip(firsts, firsts[1:] + [end]):
        while b > a + 1 and not lines[b - 1].strip():
            b -= 1
        body = "\n".join(lines[a:b])
        date, date_from = newest_date(body, today), "item"
        if date is None:
            date, date_from = heading_date, "heading" if heading_date else None
        refs = named(body)
        item = {
            "n": int(ITEM.match(lines[a]).group(1)),
            "start": a + 1,
            "end": b,
            "lines": b - a,
            "chars": len(body),
            "date": date.isoformat() if date else None,
            "date_from": date_from,
            "age": (today - date).days if date else None,
            "words": [word for word, pattern in MARKERS if pattern.search(body)],
            "done": [{"ref": r, "line": done[r]} for r in refs] if refs and all(r in done for r in refs) else [],
            "similar": [],
            "text": lines[a:b],
        }
        items.append(item)

    pairs = []
    words = [ITEM.sub("", "\n".join(i["text"]), count=1).lower().split() for i in items]
    for x, y in itertools.combinations(range(len(items)), 2):
        sm = difflib.SequenceMatcher(None, words[x], words[y], autojunk=False)
        if sm.real_quick_ratio() > SIMILAR and sm.quick_ratio() > SIMILAR and sm.ratio() > SIMILAR:
            ratio = round(sm.ratio(), 2)
            pairs.append({"items": [items[x]["n"], items[y]["n"]], "ratio": ratio})
            items[x]["similar"].append({"item": items[y]["n"], "ratio": ratio})
            items[y]["similar"].append({"item": items[x]["n"], "ratio": ratio})

    for i in items:
        flags = list(i["words"])
        if i["done"]:
            flags.append("done: " + ", ".join(f"{d['ref']} (build-log.md:{d['line']})" for d in i["done"]))
        flags += [f"similar to {s['item']} ({s['ratio']:.2f})" for s in sorted(i["similar"], key=lambda s: s["item"])]
        if i["age"] is not None and i["age"] > MAX_AGE:
            flags.append(f"old: {i['date']}{' (heading)' if i['date_from'] == 'heading' else ''}, {i['age']} days")
        i["flags"] = flags

    def size(chosen: list[dict]) -> dict:
        return {
            "items": len(chosen),
            "lines": sum(i["lines"] for i in chosen),
            "chars": sum(i["chars"] for i in chosen),
        }

    return {
        "today": today.isoformat(),
        "section": {
            "heading": heading,
            "start": start + 1,
            "end": end,
            "date": heading_date.isoformat() if heading_date else None,
        },
        "preamble": lines[start + 1 : firsts[0] if firsts else end],
        "items": items,
        "pairs": pairs,
        "total": size(items),
        "flagged": size([i for i in items if i["flags"]]),
    }


def proposal(result: dict) -> list[str]:
    """The heading, the preamble and the unflagged items verbatim, then the flagged items with their flags."""
    out = [result["section"]["heading"]] + result["preamble"]
    while len(out) > 1 and not out[-1].strip():
        out.pop()
    for i in result["items"]:
        if not i["flags"]:
            out += i["text"]
    flagged = [i for i in result["items"] if i["flags"]]
    if flagged:
        out += ["", FLAGGED_LINE]
    for i in flagged:
        m = ITEM.match(i["text"][0])
        first = i["text"][0]
        out += [m.group(0) + "[flag: " + "; ".join(i["flags"]) + "] " + first[m.end() :]] + i["text"][1:]
    return out


def markdown(result: dict, name: str) -> str:
    s, total, flagged = result["section"], result["total"], result["flagged"]
    cutoff = datetime.date.fromisoformat(result["today"]) - datetime.timedelta(days=MAX_AGE)
    out = [
        f"# Read-first audit: {name}",
        "",
        (
            f"lessons.md:{s['start']}-{s['end']}, `{s['heading']}`: {total['items']} items, {total['lines']} item "
            f"lines, {total['chars']:,} characters."
        ),
        f"Today {result['today']}; old: an item whose newest date is over {MAX_AGE} days back (before {cutoff}).",
        "",
    ]
    rows = []
    for i in result["items"]:
        if i["flags"]:
            lines = str(i["start"]) if i["start"] == i["end"] else f"{i['start']}-{i['end']}"
            first = re.sub(r"[`|]", "", ITEM.sub("", i["text"][0], count=1))
            first = first if len(first) <= 60 else first[:60].rstrip() + "…"
            rows.append(f"| {i['n']} | {lines} | {'; '.join(i['flags'])} | {first} |")
    out += ["| item | lines | flags | first words |", "|---|---|---|---|"] + rows if rows else ["No item is flagged."]
    out += [
        "",
        (
            f"Flagged: {flagged['items']} of {total['items']} items, {flagged['lines']} of {total['lines']} item "
            f"lines, {flagged['chars']:,} of {total['chars']:,} characters."
        ),
    ]
    pairs = ", ".join(f"{p['items'][0]} and {p['items'][1]} ({p['ratio']:.2f})" for p in result["pairs"])
    out.append(f"Similar pairs (word ratio over {SIMILAR}): {pairs or 'none'}.")
    body = proposal(result)
    longest = max((len(run) for line in body for run in re.findall(r"`+", line)), default=0)
    fence = "`" * max(3, longest + 1)
    out += (
        [
            "",
            '## Proposed compacted "Read first"',
            (
                "The heading, the preamble and the unflagged items verbatim, then the flagged items verbatim with their "
                "flags; item numbers kept (items cite each other by number). Review each flagged item: drop, merge or "
                "keep. This script edits nothing."
            ),
            "",
            fence + "text",
        ]
        + body
        + [fence]
    )
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument(
        "--today",
        type=datetime.date.fromisoformat,
        default=datetime.datetime.now().astimezone().date(),
        help="the date the age is counted from (default: today)",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    run = pathlib.Path(args.run_dir)
    lessons = run / "lessons.md"
    if not lessons.is_file():
        print(f"{lessons}: no such file", file=sys.stderr)
        return 2
    result = audit(cf.read(lessons), cf.read(run / "build-log.md"), args.today)
    if result is None:
        print(f"{lessons}: no `## Read first` section", file=sys.stderr)
        return 1
    if args.json:
        items = [{k: v for k, v in i.items() if k != "text"} for i in result["items"]]
        print(
            json.dumps(
                {"lessons": str(lessons), **{k: v for k, v in result.items() if k != "preamble"}, "items": items},
                indent=1,
                ensure_ascii=False,
            )
        )
    else:
        sys.stdout.write(markdown(result, run.resolve().name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
