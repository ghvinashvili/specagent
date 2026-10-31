"""harness/gates/story.py — the story-writer stage gate: checkable criteria and stated limits."""

from __future__ import annotations

import re
from pathlib import Path

from ._common import check, has_sections, sections, text

REQUIRED = ["story", "acceptance criteria", "edge cases", "out of scope", "open questions"]


def criteria(story: str) -> list[str]:
    """The numbers of the acceptance criteria, as written in story.md."""
    body = next((b for h, b in sections(story).items() if h.startswith("acceptance criteria")), "")
    return re.findall(r"(?m)^\s*(\d+)[.)]\s+\S", body)


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    story = text(stage_dir, "output/story.md")
    missing = has_sections(story, REQUIRED)
    numbers = criteria(story)
    return [
        check("story.md exists", bool(story)),
        check("story.md has the required sections", not missing, "missing: " + ", ".join(missing)),
        check("the acceptance criteria are numbered", bool(numbers)),
        check("the criteria are numbered 1..n without gaps", numbers == [str(i) for i in range(1, len(numbers) + 1)]),
    ]
