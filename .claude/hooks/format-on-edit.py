#!/usr/bin/env python3
"""PostToolUse(Edit|Write) hook: ruff formats the Python file Claude changed.
The project is CLAUDE_PROJECT_DIR, else the hook input's cwd (a `cd` moves the session's cwd, not the project). Only an
existing `.py` file inside the project is formatted, by this checkout's `.venv/bin/ruff`, else its main checkout's,
with `--force-exclude`, so the exclusions of pyproject.toml hold. With neither ruff the hook does nothing: it never runs
uv, which would create `.venv` and sync it. When ruff cannot format the file, Claude reads why; the edit stands."""

import json
import os
import subprocess
import sys
from pathlib import Path


def main_checkout(path: Path) -> Path:
    """The main checkout of a checkout under `.claude/worktrees/`, as stop-gate.py maps it; else the path itself."""
    return path.parents[2] if path.parent.name == "worktrees" and path.parents[1].name == ".claude" else path


def ruff_of(root: Path) -> Path | None:
    """The checkout's own ruff, else its main checkout's; None when neither has one."""
    found = (base / ".venv" / "bin" / "ruff" for base in (root, main_checkout(root)))
    return next((ruff for ruff in found if ruff.is_file()), None)


def main() -> int:
    data = json.load(sys.stdin)
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".").resolve()
    raw = (data.get("tool_input") or {}).get("file_path")
    if not raw:
        return 0
    path = (Path(data.get("cwd") or root) / raw).resolve()
    if path.suffix != ".py" or not path.is_file() or not path.is_relative_to(root):
        return 0
    ruff = ruff_of(root)
    if ruff is None:
        return 0
    cmd = [str(ruff), "format", "--force-exclude", str(path)]
    res = subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        first = next(iter((res.stderr or res.stdout).splitlines()), "")
        context = f"format-on-edit: ruff could not format {path.relative_to(root).as_posix()}: {first}"
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": context}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - a non-blocking error (exit 1): the edit stands
        print(f"format-on-edit: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
