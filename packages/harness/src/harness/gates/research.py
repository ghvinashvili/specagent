"""harness/gates/research.py — the researcher stage gate: every statement carries its location."""

from __future__ import annotations

from pathlib import Path

from ._common import LOCATOR, check, locators, prompt_files, statements, text

READ_DEFAULT_LINES = 2000  # what a Read without `limit` returns at most (the Read tool's description)


def findings_checks(stage_dir: Path) -> list[dict]:
    """Shared by research and investigate."""
    doc = text(stage_dir, "output/findings.md")
    lines = statements(doc)
    bare = [s[:70] for s in lines if not LOCATOR.search(s)]
    return [
        check("findings.md exists", bool(doc)),
        check("findings.md states something", bool(lines)),
        check("every statement has a `path:line` locator", not bare, "; ".join(bare[:3])),
        check("questions.md exists", (stage_dir / "output" / "questions.md").is_file()),
    ]


def _same(cited: str, opened: str) -> bool:
    """A cited path and an opened one name the same file: equal, or one is the other's tail after a `/`."""
    return cited == opened or opened.endswith("/" + cited) or cited.endswith("/" + opened)


def _covers(read: dict, first: int, last: int) -> bool:
    """The lines a Read returned: what its result shows (startLine, numLines), else what it asked (offset, limit)."""
    start = read.get("start") or read.get("offset") or 1
    count = read.get("lines") or read.get("limit") or READ_DEFAULT_LINES
    return start <= first and last <= start + count - 1


def content_checks(repo: Path, run_dir: Path, stage_dir: Path, events: list[dict] | None) -> list[dict]:
    """Part 3 of specs/001-chat-depth (method step 7, "re-open every cited location"): every line findings.md cites
    falls inside a Read of the session, offset and limit counted, or its file was in the prompt. Without a
    transcript there is nothing to compare; the check `the session's transcript was found` says so."""
    if events is None:
        return []
    given = prompt_files(stage_dir)
    reads = [e for e in events if e["tool"] == "Read" and e["ok"]]
    unread = [
        f"`{path}:{first}`"
        for path, first, last in locators(text(stage_dir, "output/findings.md"))
        if not any(_same(path, g) for g in given)
        and not any(_same(path, r["file"]) and _covers(r, first, last) for r in reads)
    ]
    return [check("every cited line was read in the session", not unread, "; ".join(unread[:3]))]


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    return findings_checks(stage_dir)
