"""PreToolUse(Write, Edit) of a pipeline role session (wired by the roles' settings, the skill's example/*-settings.json;
D10, owner 2026-10-30): a run's record is appended to, never cut. A record is known by its name: build-log*.md,
fixer-log*.md, verify.md, critique.md, critique-response.md, plan-log.md, lessons.md, judge.md. Its head may change:
line 1, the STATUS line, and line 2 where a brief keeps a field there (judge.md's `VERDICT:`, critique.md's
`Reviewed:`). A Write keeps every other old line, in order, as the start of the lines below its own head; an Edit
changes the head only, or keeps its `old_string` inside its `new_string` (lines are added, never removed). A new file
is free. The project's own settings do not wire this hook. A hook that cannot decide refuses the call (exit 2).
"""

import fnmatch
import json
import os
import sys
from pathlib import Path

RECORDS = ("build-log*.md", "fixer-log*.md", "verify.md", "critique.md", "critique-response.md", "plan-log.md",
           "lessons.md", "judge.md")  # fmt: skip
SECOND = {"judge.md": "VERDICT:", "critique.md": "Reviewed:"}  # a field on line 2 that changes as line 1 does
REASON = "append-only record: change line 1 (the STATUS line) or add lines; never remove or rewrite one"


def head(name: str, lines: list[str]) -> int:
    """How many lines of the record's head may change: line 1, and line 2 when it holds the record's field."""
    return 2 if len(lines) > 1 and name in SECOND and lines[1].startswith(SECOND[name]) else 1


def kept(name: str, old: str, tool: str, tool_input: dict) -> bool:
    """Whether the call keeps every line of the record below its head."""
    lines = old.splitlines()
    if tool == "Write":
        new = str(tool_input.get("content") or "").splitlines()
        body = lines[head(name, lines) :]
        return new[head(name, new) :][: len(body)] == body
    find, put = str(tool_input.get("old_string") or ""), str(tool_input.get("new_string") or "")
    top = "\n".join(lines[: head(name, lines)])
    return (find in top and old.count(find) == top.count(find)) or find in put


def main() -> int:
    data = json.load(sys.stdin)
    tool, tool_input = data.get("tool_name"), data.get("tool_input") or {}
    path = Path(os.path.expanduser(str(tool_input.get("file_path") or "")))
    if not path.is_absolute():
        path = Path(data.get("cwd") or os.getcwd()) / path
    if tool not in ("Write", "Edit") or not any(fnmatch.fnmatchcase(path.name, p) for p in RECORDS):
        return 0
    if not path.is_file() or kept(path.name, path.read_text(encoding="utf-8"), tool, tool_input):
        return 0
    out = {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": REASON}
    print(json.dumps({"hookSpecificOutput": out}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - a guard that cannot decide refuses the call (exit 2 blocks it)
        print(f"guard-records: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
