"""What every session loads stays small (D10.e): the description line of each agent and skill, which Claude Code lists
at every start, and the project CLAUDE.md, a map plus the rules a session must follow; the explanations it carried
live in the pages they belong to, linked from the map."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
LISTED = sorted([*(REPO / ".claude" / "agents").glob("*.md"), *(REPO / ".claude" / "skills").glob("*/SKILL.md")])
DESCRIPTION_BYTES = 150  # the `description:` line with its newline, as catalogue.py counts a skill's description
CLAUDE_MD_LINES, CLAUDE_MD_BYTES = 60, 4_000


def description_bytes(text: str) -> int | None:
    """Bytes of the frontmatter's `description:` line with its newline; None when the text has no closed frontmatter,
    no description, or a description that does not sit on that one line (a `>` or `|` block hides its length)."""
    parts = text.split("---", 2)  # the frontmatter as harness validate reads it
    if not text.startswith("---\n") or len(parts) < 3:
        return None
    description = (yaml.safe_load(parts[1]) or {}).get("description")
    line = next((line for line in parts[1].splitlines() if line.startswith("description:")), "")
    if not isinstance(description, str) or not description or description not in line:
        return None
    return len(line.encode("utf-8")) + 1


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("---\nname: k\ndescription: " + "d" * 136 + "\n---\nbody\n", 150),
        ("---\nname: k\ndescription: " + "d" * 137 + "\n---\nbody\n", 151),
        ("---\nname: k\ndescription: " + "—" * 45 + "d\n---\n", 150),  # 46 characters, 136 bytes
        ('---\nname: k\ndescription: "Does x. Use when: y."\n---\n', 36),
        ("---\nname: k\ndescription: >\n  folded over\n  two lines\n---\n", None),
        ("---\nname: k\n---\ndescription: in the body\n", None),
        ("description: no frontmatter\n", None),
        ("---\nname: k\ndescription: never closed\n", None),
    ],
    ids=["at-150", "at-151", "multibyte", "quoted", "folded", "none", "no-frontmatter", "unclosed"],
)
def test_the_description_is_measured_in_bytes_on_its_one_line(text: str, expected: int | None):
    assert description_bytes(text) == expected


def test_the_listing_holds_the_agents_and_the_skills():
    assert {p.parent.name for p in LISTED if p.name != "SKILL.md"} == {"agents"}
    assert any(p.name == "SKILL.md" for p in LISTED)


@pytest.mark.parametrize("path", LISTED, ids=lambda p: p.relative_to(REPO).as_posix())
def test_each_agent_and_skill_description_is_one_line_of_at_most_150_bytes(path: Path):
    size = description_bytes(path.read_text(encoding="utf-8"))
    assert size is not None and size <= DESCRIPTION_BYTES, f"{size} bytes"


def test_claude_md_is_a_map_of_at_most_60_lines_and_4000_bytes():
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    lines, size = len(text.splitlines()), len(text.encode("utf-8"))
    assert lines <= CLAUDE_MD_LINES and size <= CLAUDE_MD_BYTES, f"CLAUDE.md: {lines} lines, {size} bytes"


def test_what_settings_and_hooks_enforce_is_a_page_of_its_own_that_the_map_links():
    """A page of its own, as the module map (TD-009): harness.md is near the 12,000 bytes every architecture page keeps
    (test_doc_rules.py), and the rules move whole."""
    claude = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    page = (REPO / "docs" / "architecture" / "harness-enforcement.md").read_text(encoding="utf-8")
    assert "](docs/architecture/harness-enforcement.md)" in claude
    assert page.startswith("# What settings and hooks enforce\n")
    assert "- No subagents: the `Agent` tool is denied." in page
    assert "the `Agent` tool is denied" not in claude
