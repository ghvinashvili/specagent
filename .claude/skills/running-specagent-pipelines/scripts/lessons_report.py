#!/usr/bin/env python3
"""Whether a lesson lowers the error it was written for (owner, 2026-11-02; vault measure-the-effect-of-every-improvement).

  python3 lessons_report.py <run-dir> [<run-dir> ...] [--repo DIR] [--projects DIR] [--transcript FILE]... [--json]

A lesson is an item of the run's `lessons.md` (a `- ` or `N. ` line and its indented continuation) in its section:
"Read first", "Known error classes" (carried from earlier runs and the vault) or "Lessons from this run". Its sources are
the finding ids its text names (`(C34, C39)`, `B1`). Finding ids restart in every run, so only an item of "Lessons from
this run" has sources among this run's findings; an id named by an item of the two other sections is an earlier run's
finding. A finding of `critique.md`, `verify.md`, `verify-kb.md` or `judge.md` names the lesson it breaks with
`Lesson: lessons.md:<line>`, or cites a lessons.md line as its `Checklist:` item; either line may fall anywhere in the
item. Such a finding that is not one of the item's own sources is a recurrence: the rule was broken again. A lesson
with a recurrence was broken twice and is flagged to become code (vault a-rule-broken-twice-becomes-code). Units are
the `Task N: done` lines of the build logs.

Held split (v2): a recurrence counts only when the session that made the error held the lesson. The error is the commit
of the finding's `## Task N — <sha>` heading; its session is the commit's `Role-Session: <id>` trailer, else the one
session of the run's registry (`_control/registry.json`, `session_ids`) whose transcript (`--projects`, first to last
timestamp) spans the commit's time (`--repo`). A session held a lesson of "Read first" or "Known error classes" (there
from the run's start: the pack, the start-up read) and one dated `added <ISO>` before the session's first timestamp (a
new session reads the dated lessons); it did not hold a lesson added after its start. A recurrence whose session or
lesson date is unknown still counts, and is listed as such.

Markdown to stdout: per run its units, the lessons per section, each cited lesson with its sources, recurrences and
recurrences per 10 units, the lessons to make code, and the carried classes' recurrences per 10 units, which is the
measured effect of what earlier runs and the vault carried in; with several runs, one row per lesson text across them,
so a lesson carried into the template or the vault is followed run by run. `--transcript` (a session's .jsonl, e.g. the
main session's) adds the vault pages it read. A lesson no finding cites is listed as unmeasured, never as working.
Read-only.
"""

import argparse
import datetime
import json
import pathlib
import re
import subprocess
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
ADDED = re.compile(r"\badded (\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?Z?)?)")
TASK_SHA = re.compile(r"^## .*?\b([0-9a-f]{7,40})\b")
TRAILER = re.compile(r"^Role-Session:\s*([0-9a-f-]{8,})", re.MULTILINE)
PROJECTS = pathlib.Path.home() / ".claude" / "projects"
BUILT = re.compile(r"(?:Task \d+: (?:done|committed)|\b[A-Z]{1,2}\d+: fixed)\W+([0-9a-f]{7,40})\b")
SAME_START = datetime.timedelta(seconds=60)  # copies of one session start within a second of each other


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
        added = ADDED.search(item["text"])
        item["added"] = added.group(1) if added else None
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


def when(iso: str | None) -> datetime.datetime | None:
    """An ISO time (a date alone is its midnight UTC), or None."""
    if not iso:
        return None
    try:
        t = datetime.datetime.fromisoformat(iso)
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=datetime.UTC)


def finding_commits(run: pathlib.Path) -> dict[str, str]:
    """Each finding's commit: the sha of the `## Task N — <sha>` heading it stands under."""
    out: dict[str, str] = {}
    for name in REVIEWS:
        sha = None
        for line in cf.read(run / name).splitlines():
            head = TASK_SHA.match(line)
            if head or line.startswith("## "):
                sha = head.group(1) if head else None
            found = cf.HEADING.match(line)
            if found and sha:
                out.setdefault(found.group(1) + found.group(2), sha)
    return out


def roles_of(run: pathlib.Path) -> dict[str, list[str]]:
    """Each registered role's session ids (`_control/registry.json`)."""
    try:
        roles = json.loads(cf.read(run / "_control" / "registry.json") or "{}").get("roles", {})
    except ValueError:
        roles = {}
    return {name: list(row.get("session_ids") or []) for name, row in roles.items()}


def builders(run: pathlib.Path) -> dict[str, str]:
    """Each built commit's lane suffix: `builder-a` from a `Task N: done|committed — <sha>` or `V<n>: fixed — <sha>` line
    of build-log-a.md, `builder` from build-log.md."""
    out = {}
    for path in sorted(run.glob("build-log*.md")):
        lane = "builder" + path.stem.removeprefix("build-log")
        for sha in BUILT.findall(cf.read(path)):
            out[sha] = lane
    return out


def windows(run: pathlib.Path, projects: pathlib.Path) -> dict[str, tuple[datetime.datetime, datetime.datetime]]:
    """Each registered session's first and last transcript timestamp."""
    out = {}
    for sid in {s for ids in roles_of(run).values() for s in ids}:
        stamps = []
        for path in projects.glob(f"*/{sid}.jsonl"):
            for raw in cf.read(path).splitlines():
                stamp = re.search(r'"timestamp":\s*"([^"]+)"', raw)
                t = when(stamp.group(1)) if stamp else None
                if t:
                    stamps.append(t)
        if stamps:
            out[sid] = (min(stamps), max(stamps))
    return out


def commit_session(repo: pathlib.Path | None, sha: str, spans: dict) -> str | None:
    """The session that made a commit: its `Role-Session:` trailer, else the one session of `spans` (the sessions of the
    role that built it, where the build log names it) whose span holds the commit's time; several such sessions only
    when they share their start (copies of one session)."""
    if repo is None:
        return None
    done = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%cI%n%B", sha], capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        return None
    stamp, _, body = done.stdout.partition("\n")
    trailer = TRAILER.search(body)
    if trailer:
        return trailer.group(1)
    t = when(stamp.strip())
    inside = [sid for sid, (first, last) in spans.items() if t and first <= t <= last]
    # a resumed copy carries its original's history, so copies alive at once share the first timestamp, and the lessons
    starts = [spans[sid][0] for sid in inside]
    return inside[0] if inside and max(starts) - min(starts) <= SAME_START else None


def own_spans(run: pathlib.Path, sha: str, spans: dict) -> dict:
    """The spans of the sessions of the role whose build log names the commit; all spans when none does."""
    lane = next((lane for built, lane in builders(run).items() if built.startswith(sha) or sha.startswith(built)), None)
    ids = {s for name, sids in roles_of(run).items() if lane and name.rsplit("/", 1)[-1] == lane for s in sids}
    return {sid: span for sid, span in spans.items() if sid in ids} if ids else spans


def held(item: dict, sid: str | None, spans: dict) -> bool | None:
    """Whether the session held the lesson when it worked: True, False, or None when unknown."""
    if item["section"] in ("read first", "carried"):
        return True
    added, span = when(item["added"]), spans.get(sid) if sid else None
    if added is None or span is None:
        return None
    return added <= span[0]


def report_run(run: pathlib.Path, repo: pathlib.Path | None = None, projects: pathlib.Path = PROJECTS) -> dict:
    items, cited, count = lessons(cf.read(run / "lessons.md")), citations(run), units(run)
    commits, spans = finding_commits(run), windows(run, projects) if repo else {}
    sessions = {i: commit_session(repo, sha, own_spans(run, sha, spans)) for i, sha in commits.items()}
    for item in items:
        hits = sorted({i for i, line in cited if item["line"] <= line <= item["end"]})
        item["cited_by"] = hits
        # finding ids restart per run: only a lesson written in this run names this run's findings as its sources
        own = item["sources"] if item["section"] == "this run" else []
        again = [i for i in hits if i not in own]
        state = {i: held(item, sessions.get(i), spans) for i in again}
        item["not_held"] = [i for i in again if state[i] is False]  # added after the erring session started
        item["held_unknown"] = [i for i in again if state[i] is None]
        item["recurrences"] = [i for i in again if state[i] is not False]
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
            "| lessons.md line | section | sources | recurrences | per 10 units | not held | held unknown |",
            "| ---: | --- | --- | --- | ---: | --- | --- |",
        ]
        for i in (i for i in r["items"] if i["cited_by"]):
            again = ", ".join(i["recurrences"]) or "0"
            out.append(
                f"| {i['line']} | {i['section']} | {', '.join(i['sources']) or '-'} | {again} | {i['per_10_units']} "
                f"| {', '.join(i['not_held']) or '-'} | {', '.join(i['held_unknown']) or '-'} |"
            )
        c = r["carried"]
        out += [
            "",
            (
                f"make code (broken twice: its first break is its source, or an earlier run for a carried class; "
                f"then one or more recurrences): {', '.join(f'lessons.md:{n}' for n in r['make_code']) or 'none'}"
            ),
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
    ap.add_argument("--repo", type=pathlib.Path, help="the git checkout of the run's commits (the held split)")
    ap.add_argument("--projects", type=pathlib.Path, default=PROJECTS, help="Claude Code's transcripts folder")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    for run in a.runs:
        if not (run / "lessons.md").is_file():
            print(f"lessons_report.py: no lessons.md in {run}", file=sys.stderr)
            return 2
    runs, pages = [report_run(run, a.repo, a.projects) for run in a.runs], vault_reads(a.transcript)
    print(json.dumps({"runs": runs, "vault_reads": pages}, indent=1) if a.json else markdown(runs, pages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
