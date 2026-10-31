#!/usr/bin/env python3
"""ConfigChange hook: log every settings/skills change; block project and local changes during a run. The log of a
session outside a run goes to the main checkout's runs root (CLAUDE_PROJECT_DIR, mapped to the main checkout when it
is a checkout). A hook that cannot decide blocks the change (exit 2)."""

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


def audit_log(name: str) -> Path:
    run_dir = os.environ.get("HARNESS_RUN_DIR")
    stage = os.environ.get("HARNESS_STAGE")
    if run_dir and stage:
        return (
            Path(run_dir) / "stages" / stage / os.environ.get("HARNESS_SHARD", "") / "logs" / name
        )  # per shard when HARNESS_SHARD is set
    root = main_checkout(Path(os.environ["CLAUDE_PROJECT_DIR"]).resolve())
    return runs_root(root) / "_audit" / name  # the runs root, outside the repository


def main() -> int:
    data = json.load(sys.stdin)
    record = {
        "at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "session_id": data.get("session_id"),
        "source": data.get("source"),
        "file_path": data.get("file_path"),
    }
    log = audit_log("config-changes.jsonl")
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    if os.environ.get("HARNESS_RUN_DIR") and data.get("source") in ("project_settings", "local_settings", "skills"):
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": "Settings and skills are frozen while a harness run is active; change them outside the run.",
                }
            )
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - a hook that cannot decide blocks the change (exit 2)
        print(f"config-audit: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
