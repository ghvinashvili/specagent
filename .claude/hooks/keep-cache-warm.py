#!/usr/bin/env python3
"""A role session's prompt cache stays warm by rule, not by the role's care (owner, 2026-11-01).

The prompt cache lives 5 minutes from a session's last call; a wait past that rewrites the whole context (a run of
2026-11-01: a verifier wrapped the shipped 3.5-minute waiter in its own loop and sat 8 and 14 minutes, rewriting about
60k tokens each time; a plan fixer held one foreground command for 10 minutes). Two hooks of a role's settings:

  python3 keep-cache-warm.py pretool
      PreToolUse(Bash): refuses a foreground command that may hold the turn past 210 s: a `timeout` over 210000 ms,
      a `timeout N` or `sleep N` over 210 s in the command, or a loop around a waiter (`wait_for_*`). In the
      background (`run_in_background`) everything passes. Exit 2 with the reason on stderr refuses the call.

  python3 keep-cache-warm.py stop RECORD FINAL [--wait S] [--max-minutes M]
      Stop: while line 1 of RECORD does not start with FINAL, the session's turn end waits S seconds (default 200,
      so the next call comes within 3.5 minutes of the last) and then continues the session with a short keep-alive,
      for at most M minutes (default 60, the break-even: a touch of a 150k context costs about $0.04, a rewrite about
      $0.75, so 19 touches pay one rewrite) counted from the first turn end of the stretch; then the turn ends. A
      final record, a missing record or a stretch past M lets the turn end at once.

Stdin is the hook's JSON input. The stretch's start is kept in $TMPDIR/specagent-keep-warm-<session_id>.json.
"""

import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

LIMIT = 210  # seconds a foreground call may hold the turn: the 5-minute cache with room for the next call
TIMEOUT = re.compile(r"(?:^|[;&|(\s])timeout\s+(?:-\S+\s+(?:\d+[smhd]?\s+)?)*(\d+(?:\.\d+)?)([smhd]?)\b")
SLEEP = re.compile(r"(?:^|[;&|(\s])sleep\s+(\d+(?:\.\d+)?)([smhd]?)\b")
LOOP = re.compile(r"\b(?:for|while|until)\b[\s\S]*wait_for_\w+")
UNIT = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}
KEEP_ALIVE = (
    "Keep-alive for the prompt cache (your record is not final): if no notification arrived and your waiter's output "
    "did not change, run nothing and end your turn with one word; otherwise do what your assignment says."
)


def seconds(found: re.Match) -> float:
    return float(found.group(1)) * UNIT[found.group(2)]


def pretool(data: dict) -> int:
    """0 lets the call run; 2 refuses it with the reason on stderr."""
    tool = data.get("tool_input") or {}
    if data.get("tool_name") != "Bash" or tool.get("run_in_background") is True:
        return 0
    command = str(tool.get("command", ""))
    why = None
    timeout = tool.get("timeout")
    if isinstance(timeout, (int, float)) and timeout > LIMIT * 1000:
        why = f"a foreground timeout of {timeout / 1000:g} s"
    for pattern, name in ((TIMEOUT, "timeout"), (SLEEP, "sleep")):
        for found in pattern.finditer(command):
            if seconds(found) > LIMIT:
                why = why or f"`{name} {found.group(1)}{found.group(2)}`"
    if LOOP.search(command):
        why = why or "a loop around a waiter (the waiters return within 3.5 minutes by design: run one again yourself)"
    if why is None:
        return 0
    print(
        f"Refused: {why} would hold the turn past {LIMIT} s, and the prompt cache expires 5 minutes after the last "
        "call. Run a long command with run_in_background and check on it, or wait with the run's waiter, which "
        "returns within 3.5 minutes.",
        file=sys.stderr,
    )
    return 2


def stop(data: dict, record: Path, final: str, wait: float, max_minutes: float) -> int:
    """0 with no output lets the turn end; 0 with a block decision continues the session after `wait` seconds."""
    try:
        line = record.read_text(encoding="utf-8").splitlines()[0] if record.is_file() else final
    except (OSError, UnicodeDecodeError, IndexError):
        line = final
    session = re.sub(r"[^\w-]", "", str(data.get("session_id", ""))) or "unknown"
    state = Path(tempfile.gettempdir()) / f"specagent-keep-warm-{session}.json"
    if line.startswith(final):
        state.unlink(missing_ok=True)
        return 0
    now = time.time()
    try:
        start = float(json.loads(state.read_text(encoding="utf-8"))["start"]) if data.get("stop_hook_active") else now
    except (OSError, ValueError, KeyError, TypeError):
        start = now
    if now - start >= max_minutes * 60:
        state.unlink(missing_ok=True)
        return 0  # past the break-even: a rewrite later costs less than more touches
    state.write_text(json.dumps({"start": start}), encoding="utf-8")
    time.sleep(wait)
    print(json.dumps({"decision": "block", "reason": KEEP_ALIVE}))
    return 0


def main(argv: list[str]) -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        data = {}
    data = data if isinstance(data, dict) else {}
    if argv[:1] == ["pretool"]:
        return pretool(data)
    if argv[:1] == ["stop"] and len(argv) >= 3:
        wait = float(argv[argv.index("--wait") + 1]) if "--wait" in argv else 200.0
        most = float(argv[argv.index("--max-minutes") + 1]) if "--max-minutes" in argv else 60.0
        return stop(data, Path(os.path.expanduser(argv[1])), argv[2], wait, most)
    print("usage: keep-cache-warm.py pretool | stop RECORD FINAL [--wait S] [--max-minutes M]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
