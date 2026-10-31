"""The rule "stable first, unique last" (spec 005, requirement 7b) holds in every live text that tells a fresh session what to
read: the brief, the hand-over rule, `lessons.md`'s "Read first" and the facts pack are the same at every start of a role and
come first; the hand-over note is unique to one session and comes last (V3 found six places that gave the note first)."""

import ast
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / ".claude" / "skills" / "running-specagent-pipelines"
SUFFIXES = {".md", ".json", ".svg", ".txt"}
# records say what was true when they were written: the finished plans, the ADRs, the pinned references, the changelogs
RECORDS = ("docs/exec-plans/done/", "docs/decisions/", "docs/references/")

# "its note, `lessons.md`'s "Read first"", "brief, note · Read first": the note, then the section, in one sentence or one
# element (a window never runs across `> <`, so the title of the next element is no continuation of a label)
NOTE_FIRST = re.compile(r"\b[Nn]otes?\b(?:(?!\.\s|;|>\s*<)[\s\S]){0,120}?\bRead first\b")
# `{run}/handoff-builder.md` is a note; `{run}/_handoff-rule.md` is the rule, the same for every session
NOTE_PATH = re.compile(r"/handoff-(?!rule)[\w-]+\.md")


def live_texts() -> list[Path]:
    paths = [ROOT / name for name in ("README.md", "CLAUDE.md", "AGENTS.md", "ARCHITECTURE.md")]
    paths += (ROOT / ".claude" / "agents").glob("*.md")
    paths += (ROOT / "docs").rglob("*")
    paths += (p for p in SKILL.rglob("*") if "tests" not in p.relative_to(SKILL).parts)
    return sorted(
        p
        for p in paths
        if p.is_file()
        and p.suffix in SUFFIXES
        and p.name != "CHANGELOG.md"
        and not p.relative_to(ROOT).as_posix().startswith(RECORDS)
    )


def launch_texts() -> dict[str, str]:
    """What a watcher says to a fresh session: the shipped config's texts and the built-in ones of watch_agents.py."""
    shipped = json.loads((SKILL / "example" / "agents.json").read_text(encoding="utf-8"))["fresh"]
    tree = ast.parse((SKILL / "scripts" / "watch_agents.py").read_text(encoding="utf-8"))
    built_in = next(
        node.value
        for node in tree.body
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "FRESH" for t in node.targets)
    )
    return {
        **{f"agents.json {role}": text for role, text in shipped.items()},
        **{f"watch_agents.py {role}": text for role, text in ast.literal_eval(built_in).items()},
    }


def test_no_live_text_gives_the_note_before_read_first():
    found = []
    for path in live_texts():
        text = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
        found += [f"{path.relative_to(ROOT)}: ...{m.group(0)[-100:]}" for m in NOTE_FIRST.finditer(text)]
    assert found == []


@pytest.mark.parametrize("name", sorted(launch_texts()))
def test_a_launch_text_names_the_note_after_lessons(name):
    text = launch_texts()[name]
    note = NOTE_PATH.search(text)
    if note and "lessons.md" in text:  # a milestone text names no note, the critic's and judge's no lessons.md
        assert text.index("lessons.md") < note.start(), text
