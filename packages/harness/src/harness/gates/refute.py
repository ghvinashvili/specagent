"""harness/gates/refute.py — the gate of the critic's stage in a research run: one entry per claim file."""

from __future__ import annotations

from pathlib import Path

from .critique import critique_checks


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    return critique_checks(run_dir, stage_dir)
