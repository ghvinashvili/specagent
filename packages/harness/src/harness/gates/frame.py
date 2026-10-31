"""harness/gates/frame.py — the framing stage gate (council, research): one question, two to seven independent tasks."""

from __future__ import annotations

from pathlib import Path

from ._common import check, text
from .plan import tasks_checks


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    task_checks, tasks = tasks_checks(root, stage_dir)
    dependent = [t["id"] for t in tasks if t.get("depends_on")]
    return [
        check("question.md exists", bool(text(stage_dir, "output/question.md").strip())),
        *task_checks,
        check("two to seven tasks", 2 <= len(tasks) <= 7, str(len(tasks))),
        check("the tasks are independent", not dependent, ", ".join(dependent)),
    ]
