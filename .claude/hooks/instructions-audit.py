#!/usr/bin/env python3
"""InstructionsLoaded hook: record which instruction file loaded, and why (audit of the instruction layers)."""

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
    run_dir = os.environ.get("HARNESS_RUN_DIR")
    stage = os.environ.get("HARNESS_STAGE")
    if run_dir and stage:
        log = (
            Path(run_dir) / "stages" / stage / os.environ.get("HARNESS_SHARD", "") / "logs" / "instructions.jsonl"
        )  # per shard
    else:
        root = main_checkout(Path(os.environ["CLAUDE_PROJECT_DIR"]).resolve())
        log = runs_root(root) / "_audit" / "instructions.jsonl"  # the runs root, outside the repository
    log.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "session_id": data.get("session_id"),
        "file_path": data.get("file_path"),
        "memory_type": data.get("memory_type"),
        "load_reason": data.get("load_reason"),
        "trigger_file_path": data.get("trigger_file_path"),
    }
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
