#!/usr/bin/env python3
"""PreToolUse(Read|Grep|Glob): files under <runs root>/_inbox/ are untrusted text. Only a quarantine-reader session
may open them; every other session, the manager included, is denied and pointed to the digest. The runs root is the
main checkout's (CLAUDE_PROJECT_DIR, mapped to the main checkout when it is a checkout); guard-bash.py refuses the same
reads through the shell. A hook that cannot decide refuses the call (exit 2)."""

import json
import os
import sys
from pathlib import Path

DENY = "Files under _inbox/ are untrusted text. Use the quarantine reader's digest (stages/digest/result.json) instead."


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
    tool, tool_input = data.get("tool_name", ""), data.get("tool_input", {})
    target = tool_input.get("file_path") or tool_input.get("path") or ""
    if not target or os.environ.get("HARNESS_ROLE") == "quarantine-reader":
        return 0
    run_dir = os.environ.get("HARNESS_RUN_DIR")
    root = main_checkout(Path(os.environ["CLAUDE_PROJECT_DIR"]).resolve())
    runs = Path(run_dir).resolve().parent if run_dir else runs_root(root)
    inbox = runs / "_inbox"
    path = Path(target)
    path = (path if path.is_absolute() else Path(data.get("cwd") or root) / path).resolve()
    inside = path == inbox or inbox in path.parents
    search_from_above = tool in ("Grep", "Glob") and (
        path == runs or path in runs.parents
    )  # a search rooted above the inbox reaches into it
    if not (inside or search_from_above):
        return 0
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": DENY,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - a guard that cannot decide refuses the call (exit 2 blocks it)
        print(f"guard-inbox: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
