#!/usr/bin/env python3
"""PermissionRequest hook: a role session has nobody who can answer a permission prompt. A background session would
wait on the prompt until a human attaches to it; here the request is denied at once, with a message that tells the
session how to go on. Outside a harness run (the manager, a human's own session) the hook decides nothing.

One request is answered yes (ADR-0015): an Edit or a Write of a hook script under `.claude/hooks/` of the session's
own checkout, in a run whose brief says `- Hooks: open`, by a type whose checkout is its own work (a writer's branch,
a planner's trial), in a session started in the main checkout, on a path with no `..` and no link in it. Claude Code
asks before every edit under `.claude/`. Every session runs the main checkout's hooks (`$CLAUDE_PROJECT_DIR`), so a
changed script runs nowhere before the run is integrated, after its review and the human. The rest of `.claude/` stays
refused: a session that enters a checkout reads its settings, skills, agents and commands from there."""

import json
import os
import re
import sys
from pathlib import Path

MESSAGE = (
    "Nobody can approve a permission prompt in a role session, so this call is denied. "
    "Write files with the Write or Edit tool, never through the shell. Keep each Bash call to one plain command: "
    "no shell variables, loops, braces, command or process substitution, here-documents or redirections. "
    "Search with the Grep and Glob tools. If the task cannot be done without this call, write an escalation with "
    "the escalate skill and stop."
)
EDITS = {"Edit", "Write", "MultiEdit"}
HOOKS_OPEN = re.compile(r"^\s*-\s*Hooks:\s*open\s*$", re.MULTILINE)  # as harness.gates._common.hooks_open


def hook_edit(data: dict) -> bool:
    """An edit of a hook script in the session's own checkout, in a run that opens the hooks."""
    name, run_dir = os.environ.get("HARNESS_WORKTREE"), os.environ.get("HARNESS_RUN_DIR", "")
    if data.get("tool_name") not in EDITS or not name or os.environ.get("HARNESS_OWN_CHECKOUT") != "1":
        return False
    brief = Path(run_dir) / "brief.md"
    if not brief.is_file() or not HOOKS_OPEN.search(brief.read_text(encoding="utf-8")):
        return False
    # The session's hooks run from CLAUDE_PROJECT_DIR. Only a session started in the main checkout may change the
    # hook scripts of its own checkout: they are not the ones that govern it.
    started = os.environ.get("CLAUDE_PROJECT_DIR")
    if not started or "/.claude/worktrees/" in f"{Path(started).resolve()}/":
        return False
    hooks = Path(started).resolve() / ".claude" / "worktrees" / name / ".claude" / "hooks"
    raw, cwd = (data.get("tool_input") or {}).get("file_path") or "", str(data.get("cwd") or "")
    if not raw or ".." in Path(raw).parts or not (os.path.isabs(raw) or os.path.isabs(cwd)):
        return False  # `..` after a link would leave the folder the text names
    target = Path(os.path.normpath(os.path.join(cwd, raw)))
    if hooks not in target.parents:
        return False
    # Judged on real files only: no symbolic link from the checkout down to the file, and no file with a second hard
    # link, either of which could be the main checkout's file under another name.
    below = [p for p in [target, *target.parents] if hooks in p.parents or p == hooks]
    links = [*below, hooks.parent, hooks.parent.parent]
    if any(p.is_symlink() for p in links) or (target.exists() and target.stat().st_nlink != 1):
        return False
    return hooks.resolve() in target.resolve().parents


def main() -> int:
    if not os.environ.get("HARNESS_RUN_DIR"):  # read before stdin: outside a run the hook decides nothing
        return 0
    try:  # PermissionRequest ignores exit 2: every failure is answered with the deny (docs/decisions/0020)
        data = json.load(sys.stdin)
        allowed = isinstance(data, dict) and hook_edit(data)
    except Exception:  # noqa: BLE001 - a hook that fails leaves a background session waiting on the prompt: no
        allowed = False
    decision = {"behavior": "allow"} if allowed else {"behavior": "deny", "message": MESSAGE}
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": decision}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
