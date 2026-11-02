"""timeout(1) where the system has none (macOS ships no `timeout`; Homebrew's coreutils name theirs `gtimeout`):

  python3 -I ops/timeout.py [-k <grace>] <limit> <command> [<arg> ...]

<limit> and <grace> are seconds, or a number followed by s, m, h or d, as timeout(1) reads them (a grace of 0 is no
kill). The command runs in a process group of its own; past <limit> the group gets SIGTERM, and with -k SIGKILL <grace>
later. The exit is then 124, as timeout(1)'s; otherwise it is the command's, 128 + the signal's number when a signal
ended it, 127 when the command is not found. A SIGTERM, SIGINT, SIGHUP or SIGQUIT this wrapper gets goes on to the
command's group (Ctrl-C on a script that runs it), and the exit is 128 + that signal's number. The scripts that need a time limit (ops/par-tests.sh, evals/nightly.sh) run `timeout` where it exists and
this file where it does not.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys

UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
USAGE = "usage: timeout.py [-k <grace>] <limit> <command> [<arg> ...]"


def seconds(text: str) -> float:
    """`3600`, `0.5`, `10m`: the duration in seconds; ValueError for anything else."""
    unit = UNITS.get(text[-1:], 0)
    value = float(text[:-1] if unit else text)
    if value < 0:
        raise ValueError(text)
    return value * (unit or 1)


FORWARDED = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT)


def stop(proc: subprocess.Popen, sig: int) -> None:
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        pass


def finish(proc: subprocess.Popen, grace: float | None) -> None:
    """Wait for the stopped command; with a grace, SIGKILL its group when the grace runs out."""
    try:
        proc.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        stop(proc, signal.SIGKILL)
        proc.wait()


def parse(argv: list[str]) -> tuple[float | None, float, list[str]] | None:
    """(grace, limit, command), or None for a wrong call. A grace of 0 is no kill, as timeout(1) reads it."""
    grace = None
    try:
        if argv[:1] == ["-k"]:
            grace, argv = seconds(argv[1]), argv[2:]
        limit, command = seconds(argv[0]), argv[1:]
    except (IndexError, ValueError):
        return None
    return (grace or None), limit, command


def main(argv: list[str]) -> int:
    parsed = parse(argv)
    if parsed is None or not parsed[2]:
        print(USAGE, file=sys.stderr)
        return 125
    grace, limit, command = parsed
    try:
        proc = subprocess.Popen(command, start_new_session=True)
    except FileNotFoundError:
        print(f"timeout.py: {command[0]}: command not found", file=sys.stderr)
        return 127
    except OSError as exc:
        print(f"timeout.py: {command[0]}: {exc}", file=sys.stderr)
        return 126
    received: list[int] = []

    def forward(sig: int, _frame: object) -> None:
        """A signal to this wrapper (Ctrl-C, a kill) goes to the command's group, which has a session of its own."""
        received.append(sig)
        stop(proc, sig)

    for sig in FORWARDED:
        signal.signal(sig, forward)
    try:
        code = proc.wait(timeout=limit or None)  # 0 is no limit, as timeout(1) reads it
    except subprocess.TimeoutExpired:
        stop(proc, signal.SIGTERM)
        finish(proc, grace)
        return 124
    if received:
        return 128 + received[0]
    return code if code >= 0 else 128 - code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
