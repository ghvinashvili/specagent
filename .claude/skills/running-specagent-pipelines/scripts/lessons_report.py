#!/usr/bin/env python3
"""Whether a lesson lowers the error it was written for (owner, 2026-11-02; vault measure-the-effect-of-every-improvement).

  python3 lessons_report.py <run-dir> [<run-dir> ...] [--transcript FILE]... [--json]

A lesson is an item of the run's `lessons.md` (a `- ` or `N. ` line and its indented continuation) in its section:
"Read first", "Known error classes" (carried from earlier runs and the vault) or "Lessons from this run". Its sources are
the finding ids its text names (`(C34, C39)`, `B1`). A finding of `critique.md`, `verify.md`, `verify-kb.md` or
`judge.md` names the lesson it breaks with `Lesson: lessons.md:<line>`, or cites a lessons.md line as its
`Checklist:` item; either line may fall anywhere in the item. Such a finding that is not one of the item's sources is a
recurrence: the rule was broken again. A lesson with a recurrence was broken twice and is flagged to become code
(vault a-rule-broken-twice-becomes-code). Units are the `Task N: done` lines of the build logs.

Markdown to stdout: per run its units, the lessons per section, each cited lesson with its sources, recurrences and
recurrences per 10 units, the lessons to make code, and the carried classes' recurrences per 10 units, which is the
measured effect of what earlier runs and the vault carried in; with several runs, one row per lesson text across them,
so a lesson carried into the template or the vault is followed run by run. `--transcript` (a session's .jsonl, e.g. the
main session's) adds the vault pages it read. A lesson no finding cites is listed as unmeasured, never as working.
Read-only.
"""

import argparse
import json
import pathlib
import re
import sys

sys.dont_write_bytecode = True  # `python3 -I` ignores PYTHONDONTWRITEBYTECODE; the skill folder stays clean
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_formats as cf

REVIEWS = ("critique.md", "verify.md", "verify-kb.md", "judge.md")
SECTIONS = (("Read first", "read first"), ("Known error classes", "carried"), ("Lessons from this run", "this run"))
ITEM = re.compile(r"^(?:- |\d+\. )")
IDENT = re.compile(r"\b(?:BK|VK|[CARBVMOJP])\d+\b")
CITE = re.compile(r"^(?:Checklist|Lesson):\s*`?(?:\S*/)?lessons\.md:(\d+)", re.MULTILINE)
DONE = re.compile(r"(?:- )?Task (\d+): done\b")
VAULT_READ = re.compile(r"/vault/(\S+?\.md)")


def lessons(text: str) -> list[dict]:
    """The items of lessons.md: first line, last line, section and source ids."""
    items: list[dict] = []
    section = None
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("#"):
            section = next((key for head, key in SECTIONS if head.lower() in line.lower()), None)
            continue
        if section and ITEM.match(line):
            items.append({"line": n, "end": n, "section": section, "text": line})
        elif section and items and items[-1]["end"] == n - 1 and line.startswith((" ", "\t")) and line.strip():
            items[-1]["end"], items[-1]["text"] = n, items[-1]["text"] + " " + line.strip()
    for item in items:
        item["sources"] = sorted(set(IDENT.findall(item["text"])))
    return items


def units(run: pathlib.Path) -> int:
    """The tasks done in the run's build logs, each once."""
    done = set()
    for path in sorted(run.glob("build-log*.md")):
        done |= set(DONE.findall(cf.read(path)))
    return len(done)


def citations(run: pathlib.Path) -> list[tuple[str, int]]:
    """Each finding's cited lessons.md lines, `(id, line)`, a reused heading once."""
    out, seen = [], set()
    for name in REVIEWS:
        for ident, _, body in cf.sections(cf.read(run / name)):
            for line in CITE.findall(body):
                if (ident, int(line)) not in seen:
                    seen.add((ident, int(line)))
                    out.append((ident, int(line)))
    return out


def report_run(run: pathlib.Path) -> dict:
    items, cited, count = lessons(cf.read(run / "lessons.md")), citations(run), units(run)
    for item in items:
        hits = sorted({i for i, line in cited if item["line"] <= line <= item["end"]})
        item["cited_by"] = hits
        item["recurrences"] = [i for i in hits if i not in item["sources"]]
        item["per_10_units"] = round(10 * len(item["recurrences"]) / count, 2) if count else None
        item["make_code"] = bool(item["recurrences"])
    carried = [i for i in items if i["section"] == "carried"]
    again = sum(len(i["recurrences"]) for i in carried)
    return {
        "run": str(run),
        "units": count,
        "lessons": {key: sum(i["section"] == key for i in items) for _, key in SECTIONS},
        "items": items,
        "make_code": [i["line"] for i in items if i["make_code"]],
        "unmeasured": [i["line"] for i in items if not i["cited_by"]],
        "carried": {
            "classes": len(carried),
            "recurrences": again,
            "per_10_units": round(10 * again / count, 2) if count else None,
        },
    }


def vault_reads(paths: list[pathlib.Path]) -> dict[str, int]:
    """The vault pages a session read with the Read tool, each with its count."""
    pages: dict[str, int] = {}
    for path in paths:
        for raw in cf.read(path).splitlines():
            try:
                d = json.loads(raw)
            except ValueError:
                continue
            content = d.get("message", {}).get("content") if isinstance(d, dict) else None
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Read":
                    found = VAULT_READ.search(str(block.get("input", {}).get("file_path", "")))
                    if found:
                        pages[found.group(1)] = pages.get(found.group(1), 0) + 1
    return dict(sorted(pages.items()))


def key(text: str) -> str:
    """A lesson's text for matching across runs: its words, lower case, the source ids left out."""
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", IDENT.sub("", ITEM.sub("", text)).lower()).split())[:80]


def markdown(runs: list[dict], pages: dict[str, int]) -> str:
    out = []
    for r in runs:
        out += [
            f"## {r['run']}",
            "",
            f"units: {r['units']}; lessons: " + ", ".join(f"{k} {v}" for k, v in r["lessons"].items()),
        ]
        out += [
            "",
            "| lessons.md line | section | sources | recurrences | per 10 units |",
            "| ---: | --- | --- | --- | ---: |",
        ]
        for i in (i for i in r["items"] if i["cited_by"]):
            again = ", ".join(i["recurrences"]) or "0"
            out.append(
                f"| {i['line']} | {i['section']} | {', '.join(i['sources']) or '-'} | {again} | {i['per_10_units']} |"
            )
        c = r["carried"]
        out += [
            "",
            f"make code (broken twice): {', '.join(f'lessons.md:{n}' for n in r['make_code']) or 'none'}",
            (
                f"carried classes (earlier runs and the vault): {c['classes']}, broken again {c['recurrences']} times, "
                f"{c['per_10_units']} per 10 units"
            ),
            f"unmeasured (no finding names them): {len(r['unmeasured'])} of {len(r['items'])}",
            "",
        ]
    if len(runs) > 1:
        rows: dict[str, list[str]] = {}
        for n, r in enumerate(runs):
            for i in r["items"]:
                rows.setdefault(key(i["text"]), ["-"] * len(runs))[n] = f"{len(i['recurrences'])}/{r['units']}"
        out += [
            "## Across runs (recurrences / units)",
            "",
            "| lesson | " + " | ".join(f"run {n + 1}" for n in range(len(runs))) + " |",
        ]
        out += ["| --- |" + " ---: |" * len(runs)]
        out += [f"| {k[:60]} | " + " | ".join(v) + " |" for k, v in rows.items() if sum(x != "-" for x in v) > 1]
        out.append("")
    if pages:
        out += ["## Vault pages read", ""] + [f"- {p}: {n}" for p, n in pages.items()] + [""]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(prog="lessons_report.py", description=__doc__.splitlines()[0])
    ap.add_argument("runs", nargs="+", type=pathlib.Path, metavar="RUN")
    ap.add_argument("--transcript", action="append", type=pathlib.Path, default=[], metavar="FILE")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    for run in a.runs:
        if not (run / "lessons.md").is_file():
            print(f"lessons_report.py: no lessons.md in {run}", file=sys.stderr)
            return 2
    runs, pages = [report_run(run) for run in a.runs], vault_reads(a.transcript)
    print(json.dumps({"runs": runs, "vault_reads": pages}, indent=1) if a.json else markdown(runs, pages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
