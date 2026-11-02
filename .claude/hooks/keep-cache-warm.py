#!/usr/bin/env python3
"""A role session's prompt cache stays warm by rule, not by the role's care (owner, 2026-11-01).

The prompt cache lives 5 minutes from a session's last call; a wait past that rewrites the whole context (a run of
2026-11-01: a verifier wrapped the shipped 3.5-minute waiter in its own loop and sat 8 and 14 minutes, rewriting about
60k tokens each time; a plan fixer held one foreground command for 10 minutes). Two hooks of a role's settings:

  python3 keep-cache-warm.py pretool
      PreToolUse(Bash): refuses a foreground command that may hold the turn past 210 s: a `timeout` over 210000 ms,
      a `timeout N` (after any options and their values: `timeout -s KILL N`) or `sleep N` over 210 s in the command
      (also inside the quotes of `bash -c '…'` and after `eval`), or a loop around a waiter (`wait_for_*`, in the
      loop's condition or body). The text of a quoted string is data, so a commit message or an `echo` that holds
      "for … do" or `sleep 600` passes. Two things in quotes are shell: a `-c` or `eval` argument, and a `$(…)` or
      backtick pair, in double quotes too (`out="$(timeout 900 …)"` is refused). A quoted string inside a pair is data
      again, and so is a heredoc body inside one (`git commit -m "$(cat <<'EOF' … EOF)"` passes). A waiter's name
      counts wherever it stands after the loop's keyword, a path in quotes too. A quote or a pair that never closes
      is ordinary text. In the background (`run_in_background`) everything passes. Exit 2 with the reason on stderr
      refuses the call. Two false positives are left: a heredoc body outside a pair, and unquoted prose that holds a
      `for`, a `do` and a waiter's name.

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
from functools import cache
from pathlib import Path

LIMIT = 210  # seconds a foreground call may hold the turn: the 5-minute cache with room for the next call
# where a command word may start: the line's start, a separator, a quote (`bash -c 'sleep 600'`), a substitution
START = r"""(?:^|[;&|('"`\s])"""
# an option of `timeout` may carry a value that is no option (`-s KILL`, `-k 10`): the duration follows the last option
TIMEOUT = re.compile(START + r"timeout\s+(?:-\S+\s+(?:[^-\s]\S*\s+)?)*(\d+(?:\.\d+)?)([smhd]?)\b")
SLEEP = re.compile(START + r"sleep\s+(\d+(?:\.\d+)?)([smhd]?)\b")
# a loop is a for, while or until with its `do` somewhere after it (the word "for" in prose is no loop)
LOOP = re.compile(r"\b(?:for|while|until)\b(?=[\s\S]*\bdo\b)")
WAITER = re.compile(r"wait_for_\w+")
# the text of a quoted string is data (a commit message, an `echo`), so it is not read as shell, except a string that
# follows `sh -c`, `bash -lc` or `eval` (that one is shell, and its own quoted strings are data again) and a `$(…)` or
# backtick pair, which is shell in double quotes too (its own quoted strings and heredoc bodies are data again)
SHELL_ARG = re.compile(r"(?:\b(?:ba|da|z|k|c|tc)?sh\b(?:\s+-\S+)*\s+-\w*c|\beval)\s+$")
# a heredoc's operator with its delimiter: `<<EOF`, `<<'EOF'`, `<<"EOF"`; after `<<-` the delimiter's line may start
# with tabs
HEREDOC = re.compile(r"""<<(-?)[ \t]*(?:'([^'\n]+)'|"([^"\n]+)"|([A-Za-z_]\w*))""")
Span = tuple[int, int]  # the start and the stop of a run of text in the command
UNIT = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}
KEEP_ALIVE = (
    "Keep-alive for the prompt cache (your record is not final): if no notification arrived and your waiter's output "
    "did not change, run nothing and end your turn with one word; otherwise do what your assignment says."
)


def seconds(found: re.Match) -> float:
    return float(found.group(1)) * UNIT[found.group(2)]


def terminator(text: str, start: int, dash: str, word: str) -> int:
    """Where the heredoc body that starts at `start` ends: the end of its delimiter line, or the end of the text."""
    tabs = "\t*" if dash else ""
    line = re.compile(rf"^{tabs}{re.escape(word)}$", re.MULTILINE).search(text, start)
    return line.end() if line else len(text)


def scan(text: str, i: int, end: str) -> tuple[int, list[Span]]:
    """Walk shell text from i to its end: `end` (the `)` or the backtick that closes a pair), or the text's own end when
    `end` is empty. Returns where it stopped, with the spans on the way that are data: a quoted string, and a heredoc
    body inside a pair. A string after `sh -c` or `eval` and a `$(…)` or backtick pair are shell."""
    spans: list[Span] = []
    depth = 0  # plain parentheses open inside the pair
    heredocs: list[tuple[str, str]] = []  # (dash, delimiter) of the heredocs whose bodies start after this line
    while i < len(text):
        char = text[i]
        if char == "\\":  # an escaped character opens and closes nothing
            i += 2
        elif char == end and not depth:
            return i, spans
        elif char in "'\"" or char == "`" or text.startswith("$(", i):
            found = quoted(text, i) if char in "'\"" else pair(text, i)
            if found is None:  # a quote or a pair that never closes is ordinary text
                i += 1
                continue
            stop, parts = found
            if char in "'\"" and SHELL_ARG.search(text[max(0, i - 80) : i]):  # a `-c` body or an `eval` argument
                parts = tuple((a + i + 1, b + i + 1) for a, b in scan(text[i + 1 : stop - 1], 0, "")[1])
            spans += parts
            i = stop
        elif char in "()":
            depth += 1 if char == "(" else -1
            i += 1
        elif char == "<" and end and text[i - 1 : i] != "<" and (op := HEREDOC.match(text, i)):  # not a `<<<`
            heredocs.append((op.group(1), op.group(2) or op.group(3) or op.group(4)))
            i = op.end()
        elif char == "\n" and heredocs:  # the bodies of the heredocs of the line that ends here
            start = i + 1
            for dash, word in heredocs:
                i = terminator(text, start, dash, word)
                spans.append((start, i))
                start = i + 1
            heredocs = []
        else:
            i += 1
    return i, spans


@cache
def quoted(text: str, i: int) -> tuple[int, tuple[Span, ...]] | None:
    """The quoted string that opens at text[i]: the index after its closing quote and the spans of its text that are
    data, or None when it never closes. In double quotes a `$(…)` or backtick pair is shell: only the quoted strings
    and the heredoc bodies inside it are data."""
    if text[i] == "'":
        stop = text.find("'", i + 1)
        return None if stop < 0 else (stop + 1, ((i + 1, stop),))
    spans: list[Span] = []
    data = j = i + 1  # the data run that is not yet in spans starts at `data`
    while j < len(text):
        if text[j] == '"':
            return j + 1, (*spans, (data, j))
        if text[j] == "\\":
            j += 2
        elif (text[j] == "`" or text.startswith("$(", j)) and (found := pair(text, j)):
            spans += [(data, j), *found[1]]
            data = j = found[0]
        else:
            j += 1
    return None


@cache
def pair(text: str, i: int) -> tuple[int, tuple[Span, ...]] | None:
    """The `$(…)` or backtick pair that opens at text[i]: the index after its closer and the spans of data inside it,
    or None when it never closes."""
    closer = "`" if text[i] == "`" else ")"
    stop, spans = scan(text, i + (1 if closer == "`" else 2), closer)
    return (stop + 1, tuple(spans)) if stop < len(text) else None


def shell_text(command: str) -> str:
    """The command with the text of its quoted strings blanked out, as long as before so the places still line up."""
    out = list(command)
    for start, stop in scan(command, 0, "")[1]:
        out[start:stop] = " " * (stop - start)
    return "".join(out)


def pretool(data: dict) -> int:
    """0 lets the call run; 2 refuses it with the reason on stderr."""
    tool = data.get("tool_input") or {}
    if data.get("tool_name") != "Bash" or tool.get("run_in_background") is True:
        return 0
    command = str(tool.get("command", ""))
    shell = shell_text(command)
    why = None
    timeout = tool.get("timeout")
    if isinstance(timeout, (int, float)) and timeout > LIMIT * 1000:
        why = f"a foreground timeout of {timeout / 1000:g} s"
    for pattern, name in ((TIMEOUT, "timeout"), (SLEEP, "sleep")):
        for found in pattern.finditer(shell):
            if seconds(found) > LIMIT:
                why = why or f"`{name} {found.group(1)}{found.group(2)}`"
    # the waiter's name is looked for in the whole command, since a path in quotes is still the waiter
    if any(WAITER.search(command, loop.end()) for loop in LOOP.finditer(shell)):
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
