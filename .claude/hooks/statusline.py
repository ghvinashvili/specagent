#!/usr/bin/env python3
"""Status line of the manager's terminal: the human's own status line, then one row with the role sessions that are
running or waiting for the human right now. A session that finished, stopped or failed is not listed, and when
nothing runs there is no row. The row is read from the runs' state.json files, which `harness watch` and
`harness poll` keep current, so nothing is started here. The human's own script still runs (it may do more than
print), with the same input: `~/.claude/statusline.sh`, or the command in HARNESS_STATUSLINE_BASE. The size of the
conversation is recorded for the handoff hook (handoff.py)."""

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

try:  # the size of the conversation, which the handoff hook reads
    from handoff import record_context
except ImportError:  # pragma: no cover - the hook file is part of the template
    record_context = None

MARK = {"launched": "▶", "working": "▶", "checkpointed": "▶", "blocked": "⏸"}
FRESH_HOURS = 12  # an open question of a run nobody touched for longer than this is not shown


def own_line(raw: str) -> str:
    cmd = os.path.expanduser(os.environ.get("HARNESS_STATUSLINE_BASE") or "~/.claude/statusline.sh")
    if not Path(cmd).is_file():
        return ""
    try:
        return subprocess.run([cmd], input=raw, capture_output=True, text=True, timeout=4, check=False).stdout.rstrip(
            "\n"
        )
    except (OSError, subprocess.SubprocessError):
        return ""


def minutes(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        return f" {int((dt.datetime.now(dt.UTC) - dt.datetime.fromisoformat(iso)).total_seconds() // 60)}m"
    except ValueError:
        return ""


def fresh(iso: str | None) -> bool:
    try:
        return (dt.datetime.now(dt.UTC) - dt.datetime.fromisoformat(iso)).total_seconds() < FRESH_HOURS * 3600
    except (TypeError, ValueError):
        return False


def main_checkout(path: Path) -> Path:
    """The main checkout of a checkout under `.claude/worktrees/`, as stop-gate.py maps it; else the path itself."""
    return path.parents[2] if path.parent.name == "worktrees" and path.parents[1].name == ".claude" else path


def runs_root(root: Path) -> Path:
    """harness.state.runs_root without the harness package: ../runs when that folder carries .harness-runs,
    otherwise ../<repo>-runs (packages/harness/tests/test_layout.py holds the two to one rule)."""
    shared = root.parent / "runs"
    return shared if (shared / ".harness-runs").is_file() else root.parent / f"{root.name}-runs"


def role_row(project: Path) -> str:
    cells = []
    for path in sorted(runs_root(project).glob("*/state.json"))[-30:]:
        try:
            st = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if st.get("status") not in ("running", "waiting_human", "paused"):
            continue
        for stage, ss in st.get("stages", {}).items():
            units = sorted(ss["shards"].items()) if ss.get("shards") else [("", ss)]
            for shard, u in units:
                if u.get("status") in MARK:
                    label = stage + (f"/{shard}" if shard else "")
                    cells.append(f"{MARK[u['status']]} {label} {u['status']}{minutes(u.get('started_at'))}")
        waiting = sum(1 for e in st.get("escalations", []) if e.get("status") == "open")
        if waiting and fresh(st.get("updated_at")):
            cells.append(f"? {waiting} question{'s' if waiting > 1 else ''}")
    return "chats: " + " · ".join(cells) if cells else ""


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except ValueError:
        data = {}
    project = main_checkout(
        Path((data.get("workspace") or {}).get("project_dir") or os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()
    )
    lines = [own_line(raw)]
    if not os.environ.get("HARNESS_RUN_DIR"):  # a role session has no terminal to show this in
        lines.append(role_row(project))
        if record_context:
            record_context(data)
    print("\n".join(line for line in lines if line))
    return 0


if __name__ == "__main__":
    sys.exit(main())
