"""harness/gates/synthesize.py — the synthesizer stage gate in a research run."""

from __future__ import annotations

from pathlib import Path

from .verdict import synthesis_checks, synthesis_content


def content_checks(repo: Path, run_dir: Path, stage_dir: Path, events: list[dict] | None) -> list[dict]:
    """Part 3 of specs/001-chat-depth on briefing.md: every input is named, both sides of every clash are named."""
    return synthesis_content(run_dir, stage_dir, "briefing.md")


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    return synthesis_checks(run_dir, stage_dir, "briefing.md")
