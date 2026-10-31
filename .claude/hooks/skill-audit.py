#!/usr/bin/env python3
"""PreToolUse(Skill) and UserPromptExpansion: one line per skill use. PreToolUse fires when Claude calls the Skill tool;
UserPromptExpansion fires when `/name` is typed (by a human, or in a `-p` prompt). Skills preloaded through an agent's
`skills` field pass through neither. Role sessions log to their stage, every other session to <runs root>/_audit/."""

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
        log = Path(run_dir) / "stages" / stage / os.environ.get("HARNESS_SHARD", "") / "logs" / "skills.jsonl"
    else:
        root = main_checkout(Path(os.environ["CLAUDE_PROJECT_DIR"]).resolve())
        log = runs_root(root) / "_audit" / "skills.jsonl"
    record = {
        "at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "session_id": data.get("session_id"),
        "role": os.environ.get("HARNESS_ROLE", "manager"),
        "event": data.get("hook_event_name"),
    }
    if data.get("hook_event_name") == "UserPromptExpansion":
        if data.get("expansion_type") != "slash_command":
            return 0
        record.update({"via": "typed", "skill": data.get("command_name"), "source": data.get("command_source")})
    else:
        record.update(
            {"via": "model", "tool_input": data.get("tool_input")}
        )  # stored as is: the reference does not list the Skill tool's input fields
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a helper fails open: exit 2 would block every Skill call and expansion
        sys.exit(0)
