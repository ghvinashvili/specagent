"""harness/gates/investigate.py — the researcher's stage in a research run, per shard: located statements and a finished task."""

from __future__ import annotations

import json
from pathlib import Path

from ._common import check, stage_file
from .research import content_checks, findings_checks  # noqa: F401  (content_checks: the researcher's, here too)


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    path = stage_file(stage_dir, "tasks.json")  # None for a link out of the stage directory
    tasks = json.loads(path.read_text(encoding="utf-8"))["tasks"] if path else []
    return [
        *findings_checks(stage_dir),
        check(
            "every task of the shard passes with evidence",
            bool(tasks) and all(t["passes"] and t.get("evidence") for t in tasks),
        ),
    ]
