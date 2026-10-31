#!/usr/bin/env python3
"""PreToolUse(Bash): keep test output out of the context. A pytest command is rewritten through `updatedInput`: the full
output goes to a file, the session sees the failures, the summary lines and the file's path, and the exit code is kept,
because the verifier records it as evidence. Every other command passes unchanged.

A short output (60 lines or fewer) is shown whole: cutting it saved nothing and, seen live, hid the one line that named
the cause of a collection error. The file is written where the session can read it: a role session reads only its
working directories, so its file goes to the `logs/` directory of its stage; any other session gets a temporary file.

A pytest command is every form the repository counts as one (packages/harness/tests/test_steps.py): `pytest`,
`python -m pytest` and `uv run` before either, with uv's options, leading assignments or `env`, and one `cd <dir> &&`
before it. The command stands in the wrapper on a line of its own, so a `#` comment ends at its line and the exit code
is the command's. A helper: when it cannot read its input it lets the call through unchanged (exit 0; exit 2 would
block every Bash call)."""

import json
import re
import sys

TEST = re.compile(
    r"^\s*(cd\s+[^\s;&|<>()`$]+\s*&&\s*)?"  # one `cd <dir> &&` in front
    r"(env\s+)?([A-Za-z_][A-Za-z0-9_]*=[^\s;&|<>()`$]*\s+)*"  # env and leading assignments
    r"(uv\s+run\s+(--?[\w-]+(=[^\s;&|<>]+|\s+(?!-)[^\s;&|<>]+)?\s+)*)?"  # uv run and its options
    r"((\S*/)?python3?(\.\d+)?\s+-m\s+)?(\S*/)?pytest\b[^;&|<>]*$"
)
WRAP = (
    'f=$(mktemp "${HARNESS_STAGE_DIR:-/nonexistent}/logs/test-XXXXXX" 2>/dev/null) || f=$(mktemp); '
    '( {cmd}\n) > "$f" 2>&1; rc=$?; '
    'if [ "$(wc -l < "$f")" -le 60 ]; then cat "$f"; else '
    'grep -A 12 -E \'(FAILED|ERROR|Error|error:)\' "$f" | head -150; tail -n 5 "$f"; fi; '
    'echo "full output: $f (exit $rc)"; exit $rc'
)


def main() -> int:
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input") or {}
    command = tool_input.get("command", "")
    if data.get("tool_name") != "Bash" or not TEST.match(command):
        return 0
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "updatedInput": {**tool_input, "command": WRAP.replace("{cmd}", command)},
                }
            }
        )
    )  # the whole input object is replaced
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a helper fails open: the command runs unchanged
        sys.exit(0)
