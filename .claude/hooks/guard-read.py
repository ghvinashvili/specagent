"""PreToolUse(Read) of a pipeline role session (wired by the roles' settings, the skill's example/*-settings.json; D10,
owner 2026-10-30): a file over 20,000 bytes is read by range. A Read with neither `offset` nor `limit` (nor `pages`, a
PDF's range) of a larger file is refused with the way to read it: `grep -n` for the lines, then a Read of those lines.
What a session reads stays in its context and is re-read by every later call, so one whole read of a large file costs
its size times the calls that follow it. A missing file, a folder and an image are let through: Read reports the first
itself, and the others have no lines to cut. The project's own settings do not wire this hook: the owner's sessions
read as they like. A hook that cannot decide refuses the call (exit 2).
"""

import json
import os
import sys
from pathlib import Path

LIMIT = 20_000  # bytes; a larger file is read by range
IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}  # Read shows these as images; no offset or limit applies
REASON = "read by range: grep -n first, then offset and limit"


def main() -> int:
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input") or {}
    if data.get("tool_name") != "Read" or any(tool_input.get(k) is not None for k in ("offset", "limit", "pages")):
        return 0
    path = Path(os.path.expanduser(str(tool_input.get("file_path") or "")))
    if not path.is_absolute():
        path = Path(data.get("cwd") or os.getcwd()) / path
    if path.suffix.lower() in IMAGES or not path.is_file() or path.stat().st_size <= LIMIT:
        return 0
    out = {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": REASON}
    print(json.dumps({"hookSpecificOutput": out}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - a guard that cannot decide refuses the call (exit 2 blocks it)
        print(f"guard-read: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
