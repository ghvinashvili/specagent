"""harness/gates/read.py — the reader stage gate.

The notes are what every later session reads instead of the material, so the gate checks the one thing a model cannot
be trusted to check about itself: that a quote stands where the notes say it stands. An entry is a list item in a
source section; it carries its location as inline code, `path:line`, and its quote in double quotes. The record of a
probe is a source too: what a command showed is written fact by fact, each quoted from the record, and not as one
line of summary. A contradiction gives the texts that disagree, each at its place.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from ._common import LOCATOR, check, closed_paths, file_lines, inside, is_closed, sections, stage_file
from ._common import text as stage_text

OWN = ("header", "contradictions", "coverage", "probes")  # sections of the notes that are not a source
# A heading is one of them when the name is not the start of a path: `Probes` is, `probes/p1.txt` is a source.
OWN_HEADING = re.compile(rf"`?({'|'.join(OWN)})\b(?![/.\w-])")
PROBE_FILE = re.compile(r"`(?:output/)?(probes/[^`\s]+)`")  # the record of a probe, named in its entry
ITEM = re.compile(r"^([-*]|\d+[.)])\s+\S")
QUOTE = re.compile(r'"([^"]{8,})"|“([^”]{8,})”')
MARK = re.compile(r'Quote:\s*["“]')  # where the quote of an entry begins
OPINION = re.compile(r"\b(probably|seems|I think)\b")
SPAN = re.compile(r"`([^`\s]+):(\d+)(?:-(\d+))?`")


def entries(body: str) -> list[str]:
    """List items with their indented continuation lines, each as one string."""
    out: list[str] = []
    for line in body.splitlines():
        if ITEM.match(line.strip()) and not line.startswith((" ", "\t")):
            out.append(line.strip())
        elif out and line.strip() and line.startswith((" ", "\t")):
            out[-1] += " " + line.strip()
    return out


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parts(entry: str) -> tuple[str | None, re.Match | None]:
    """The quote of an entry and its location. After the word `Quote:` the quote runs from the opening double quote
    to the last double quote before the location, so a quote may contain double quotes itself, as quoted code does,
    and a quoted word in the fact before it is not mistaken for the quote. An entry without the word falls back to
    its first quoted passage."""
    mark = MARK.search(entry)
    if not mark:
        q = QUOTE.search(entry)
        return ((q.group(1) or q.group(2)) if q else None), SPAN.search(entry)
    location = SPAN.search(entry, mark.end())
    body = entry[mark.end() : location.start() if location else len(entry)]
    close = max(body.rfind('"'), body.rfind("”"))
    return (body[:close] if close > 0 else None), location


def own_voice(text: str) -> str:
    """The notes without their quotes: what the reader says in its own words."""
    lines = []
    for line in text.splitlines():
        quote, _ = parts(line) if MARK.search(line) else (None, None)
        lines.append(line.replace(quote, "") if quote else line)
    return QUOTE.sub("", "\n".join(lines))


def own(heading: str, name: str | None = None) -> bool:
    """Whether a heading is one of the notes' own sections (`name`: that one), and not a source."""
    m = OWN_HEADING.match(heading)
    return bool(m) and (name is None or m.group(1) == name)


def opened(base: Path, rel: str, closed: list[str] | tuple = ()) -> list[str] | None:
    """The lines of `base / rel`, or None when the path leaves the base (an absolute path, `..`, a link out of it) or
    names a path the stage's type may not read (`closed`: closed_paths, its row and the project's settings, also inside
    a checkout under `.claude/worktrees/`, as the session's Read deny rules name it): the gate runs outside the sandbox,
    and what it finds there would reach the session in a check's detail (docs/decisions/0020, 0025)."""
    if PurePosixPath(rel).is_absolute():
        return None
    at = inside(base, rel)
    if at is None or is_closed(at, closed):
        return None
    return file_lines(base / rel)


def window(m: re.Match, bases: list[Path], closed: list[str] | tuple = ()) -> tuple[str | None, str | None]:
    """The text at a location, with two lines of slack on each side, and what is wrong with the location. Both are
    None for a location outside the bases (a URL, a file that is not on disk, a path the system refuses to look up, a
    path that leaves every base or is closed to the stage's type): it is not opened here."""
    lines = next((found for b in bases if (found := opened(b, m.group(1), closed)) is not None), None)
    if lines is None:
        return None, None
    first, last = int(m.group(2)), int(m.group(3) or m.group(2))
    if first < 1 or last > len(lines):
        return None, f"{m.group(0)}: the file has {len(lines)} lines"
    return _norm(" ".join(lines[max(0, first - 3) : last + 2])), None


def misplaced(entry: str, bases: list[Path], closed: list[str] | tuple = ()) -> str | None:
    """Why the entry's quote is not at its stated location, or None."""
    quote, m = parts(entry)
    if not m:
        return None
    text, wrong = window(m, bases, closed)
    if wrong or text is None or not quote:
        return wrong
    return None if _norm(quote) in text else f"{m.group(0)}: the quote is not at that place"


def probe_problems(stage_dir: Path, body: str | None) -> list[str]:
    """What is wrong with the section Probes. A probe is a command the reader ran because the material does not say
    how something behaves; its entry names the file under `output/probes/` that holds what was run and what came
    back. A section without entries says `none` and why. A record is looked for in output/ only: a path that leaves it
    (`..`, a link) is no record, whether a file stands there or not (docs/decisions/0025)."""
    if body is None:
        return ["the notes have no section Probes"]
    items = entries(body)
    if not items:
        return [] if re.search(r"\bnone\b", body, re.IGNORECASE) else ["Probes has neither an entry nor `none`"]
    bad = []
    for e in items:
        named = PROBE_FILE.findall(e)
        if not named:
            bad.append(f"{e[:50]}: no file under output/probes/ is named")
        bad += [f"{rel}: no such file" for rel in named if stage_file(stage_dir / "output", rel) is None]
    return bad


def unsectioned(body: str | None, sources: dict[str, str]) -> list[str]:
    """Probes whose record is not a source of the notes. What a command showed is written fact by fact in a section
    headed by the record's path, each item quoted from the record at its line; an entry under Probes alone is a
    summary nobody can check. One record with its section is enough for an entry that names several files (the
    script, the input, the output)."""
    bad: dict[str, None] = {}  # several probes may share one record: it is named once
    for e in entries(body or ""):
        named = PROBE_FILE.findall(e)
        if named and not any(rel.lower() in h for rel in named for h in sources):
            bad[f"{named[-1]}: no section of the notes is headed by this record"] = None
    return list(bad)


def _two_texts(found: list[set[str] | None]) -> bool:
    """Whether two of the locations hold two different quoted texts. `None` is a location that cannot be opened
    here (a URL); it counts as holding a text of its own."""
    for a, x in enumerate(found):
        for y in found[a + 1 :]:
            if x is None or y is None:
                if x is None and y is None or x or y:
                    return True
            elif any(p not in q and q not in p for p in x for q in y):
                return True
    return False


def unsupported(body: str | None, bases: list[Path], closed: list[str] | tuple = ()) -> list[str]:
    """Contradictions that do not show two texts at their places. An item names every text that takes part with its
    location; two of them must stand where the item says, and they must be two texts, not one text located twice.
    The order is free (quote then location, or location then quote), and a quote may hold double quotes."""
    bad = []
    for e in entries(body or ""):
        marks = [i for i, ch in enumerate(e) if ch in '"“”']
        # every stretch between two double quotes: one of them is the quote, whatever quotes it holds itself
        quoted = {q for a, i in enumerate(marks) for j in marks[a + 1 :] if len(q := _norm(e[i + 1 : j])) >= 8}
        found: list[set[str] | None] = []
        for m in SPAN.finditer(e):
            text, wrong = window(m, bases, closed)
            if wrong:
                bad.append(wrong)
            else:
                found.append(None if text is None else {q for q in quoted if q in text})
        if not _two_texts(found):
            bad.append(f"{e[:50]}: fewer than two texts stand at a stated location")
    return bad


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    text = stage_text(stage_dir, "output/notes.md")  # "" for a link out of the stage directory
    found = sections(text)
    bases = [root, stage_dir, stage_dir / "input", stage_dir / "output"]
    closed = closed_paths(root, run_dir, stage_dir)
    sources = {h: body for h, body in found.items() if not own(h) and entries(body)}
    items = [e for body in sources.values() for e in entries(body)]
    bare = [e[:60] for e in items if not LOCATOR.search(e) and "http" not in e]
    wrong = [w for w in (misplaced(e, bases, closed) for e in items) if w]
    unquoted = own_voice(text)
    listed = next((b for h, b in found.items() if own(h, "probes")), None)
    probes = probe_problems(stage_dir, listed)
    loose = unsectioned(listed, sources)
    clash = unsupported(next((b for h, b in found.items() if own(h, "contradictions")), None), bases, closed)
    return [
        check("notes.md has a section per source with at least one entry", bool(sources)),
        check("every entry carries its location as `path:line`", bool(items) and not bare, "; ".join(bare[:3])),
        check("every quote stands at its stated location", bool(items) and not wrong, "; ".join(wrong[:3])),
        check(
            "the notes have the sections Contradictions and Coverage",
            all(any(own(h, n) for h in found) for n in ("contradictions", "coverage")),
        ),
        check("every contradiction shows two texts at their places", not clash, "; ".join(clash[:3])),
        check("every probe has its record under output/probes/", not probes, "; ".join(probes[:3])),
        check("every probe record is a source section of the notes", not loose, "; ".join(loose[:3])),
        check("no opinion words in the reader's own voice", not OPINION.search(unquoted)),
        check("questions.md exists", (stage_dir / "output" / "questions.md").exists()),
    ]
