#!/usr/bin/env python3
"""Notification: forward what Claude Code announces (permission prompt, idle prompt, a background session that needs
input or finished, a usage-limit continuation that did not happen) to the operator's command in HARNESS_NOTIFY_CMD.
A Notification hook cannot block or change anything; this one only forwards and logs."""

import datetime as dt
import json
import os
import shlex
import subprocess
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
    role = os.environ.get("HARNESS_ROLE", "manager")
    line = f"[{role}] {data.get('notification_type')}: {data.get('title') or ''} {data.get('message') or ''}".strip()
    command, sent = os.environ.get("HARNESS_NOTIFY_CMD"), False
    if command:
        try:
            sent = (
                subprocess.run(
                    shlex.split(command), input=line + "\n", text=True, capture_output=True, timeout=8, check=False
                ).returncode
                == 0
            )
        except (OSError, subprocess.TimeoutExpired):
            sent = False
    root = main_checkout(Path(os.environ["CLAUDE_PROJECT_DIR"]).resolve())
    log = runs_root(root) / "_audit" / "notify.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                    "kind": data.get("notification_type"),
                    "session_id": data.get("session_id"),
                    "line": line,
                    "sent": sent,
                }
            )
            + "\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
