#!/usr/bin/env python3
"""PreToolUse(Write) hook: a warning when Claude writes a new source file that no test names (AGENTS.md, Testing).
A source file has a suffix of the pinned rules' paths (Python, C++, TypeScript, JavaScript). A new one is held to the
check under `packages/<package>/src/` (its tests in `packages/<package>/tests`) or as `ops/<name>.py` (in `ops/tests`).
A test names it by its file name (`test_<name>`, `<name>_test`, `<name>.test`, `<name>.spec`) or by `<name>` as a whole
word in its text. The project is CLAUDE_PROJECT_DIR, else the hook input's cwd. The hook only gives Claude context:
it never decides on the write."""

import json
import os
import re
import sys
from pathlib import Path

SOURCE = {".py", ".cpp", ".cc", ".cxx", ".hpp", ".hh", ".h", ".ts", ".tsx", ".js", ".jsx"}


def tests_folder(rel: Path) -> Path | None:
    """The tests folder of a new source file at `rel` from the project, or None when the file is not held to the check."""
    parts = rel.parts
    if len(parts) >= 4 and parts[0] == "packages" and parts[2] == "src":
        return Path("packages", parts[1], "tests")
    if len(parts) == 2 and parts[0] == "ops" and rel.suffix == ".py":
        return Path("ops", "tests")
    return None


def named(folder: Path, stem: str) -> bool:
    """A source file under `folder`, at any depth, is a test of `stem` by its name, or names `stem` in its text."""
    names = {f"test_{stem}", f"{stem}_test", f"{stem}.test", f"{stem}.spec"}
    word = re.compile(rf"(?<![\w-]){re.escape(stem)}(?![\w-])")
    files = [p for p in folder.rglob("*") if p.suffix in SOURCE and p.is_file()]
    if any(p.name[: -len(p.suffix)] in names for p in files):
        return True
    return any(word.search(p.read_text(encoding="utf-8", errors="replace")) for p in files)


def main() -> int:
    data = json.load(sys.stdin)
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".").resolve()
    raw = (data.get("tool_input") or {}).get("file_path")
    if not raw:
        return 0
    path = (Path(data.get("cwd") or root) / raw).resolve()
    if path.suffix not in SOURCE or path.name == "__init__.py" or path.exists() or not path.is_relative_to(root):
        return 0
    folder = tests_folder(path.relative_to(root))
    if folder is None or named(root / folder, path.stem):
        return 0
    context = f"test-alongside: no test under {folder.as_posix()} names {path.stem}; write one that does"
    out = {"hookEventName": "PreToolUse", "additionalContext": context + " (AGENTS.md, Testing)"}
    print(json.dumps({"hookSpecificOutput": out}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - a non-blocking error (exit 1): the write goes ahead
        print(f"test-alongside: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
