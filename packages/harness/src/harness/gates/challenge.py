"""harness/gates/challenge.py — the gate of the critic's stage in a learning run: every proposal answered."""

from __future__ import annotations

from pathlib import Path

from ._common import check, text
from .critique import critique_checks


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    doc = text(stage_dir, "output/critique.md")
    proposals = sorted(p.stem for p in (run_dir / "stages" / "analyze" / "output" / "proposals").glob("*.md"))
    unanswered = [p for p in proposals if f"{p}.md" not in doc]
    return [
        *critique_checks(run_dir, stage_dir),
        check("every proposal has an entry", not unanswered, ", ".join(unanswered)),
    ]
