#!/usr/bin/env python3
"""StopFailure: the turn ended on an API error instead of a normal stop. Claude Code ignores this hook's output and exit
code, so the hook only records the error: `harness poll` (limits.py) and the analyst read the log."""

import datetime as dt
import json
import os
import sys
from pathlib import Path


def main_checkout(path: Path) -> Path:
    """The main checkout of a checkout under `.claude/worktrees/`, as stop-gate.py maps it; else the path itself."""
    return path.parents[2] if path.parent.name == "worktrees" and path.parents[1].name == ".claude" else path


def runs_root(root: Path) -> Path:
    """harness.state.runs_root without the harness package: ../runs when that folder carries .harness-runs,
    otherwise ../<repo>-runs (packages/harness/tests/test_layout.py holds the two to one rule)."""
    shared = root.parent / "runs"
    return shared if (shared / ".harness-runs").is_file() else root.parent / f"{root.name}-runs"


def main() -> int:
    data = json.load(sys.stdin)
    run_dir, stage = os.environ.get("HARNESS_RUN_DIR"), os.environ.get("HARNESS_STAGE")
    if run_dir and stage:
        log = Path(run_dir) / "stages" / stage / os.environ.get("HARNESS_SHARD", "") / "logs" / "stop-failure.jsonl"
    else:
        root = main_checkout(Path(os.environ["CLAUDE_PROJECT_DIR"]).resolve())
        log = runs_root(root) / "_audit" / "stop-failure.jsonl"
    record = {
        "at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "session_id": data.get("session_id"),
        "error": data.get("error"),
        "error_details": data.get("error_details"),
        "last_assistant_message": (data.get("last_assistant_message") or "")[:500],
    }
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
