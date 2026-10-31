#!/usr/bin/env python3
"""Deterministic grader: exit 0 when a hand-over note carries its session's facts instead of pointing at files.

`pipeline_note.py <note> <facts.json>`, where facts.json is {"role", "task", "facts": [...]}. Line 1 must be
`HANDOFF <role> after Task <task> — <YYYY-MM-DD HH:MM>`, the note has at most 40 lines, and every fact appears in
it as written (error class 7: a hand-over note that points at files instead of carrying the facts). Prints one
problem per line. See evals/README.md.
"""

import json
import re
import sys
from pathlib import Path

MAX_LINES = 40
STAMP = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}"


def problems(note: str, facts: dict) -> list[str]:
    role, task, lines = facts["role"], facts["task"], note.splitlines()
    line_1 = f"HANDOFF {re.escape(str(role))} after Task {re.escape(str(task))} — {STAMP}"
    out = []
    if not re.fullmatch(line_1, lines[0] if lines else ""):
        out.append(f'line 1 is not "HANDOFF {role} after Task {task} — <YYYY-MM-DD HH:MM>"')
    if len(lines) > MAX_LINES:
        out.append(f"{len(lines)} lines, over {MAX_LINES}")
    return out + [f'the fact "{fact}" is not carried' for fact in facts["facts"] if fact not in note]


def main() -> int:
    note = Path(sys.argv[1]).read_text(encoding="utf-8")
    found = problems(note, json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")))
    if found:
        print("\n".join(found))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
