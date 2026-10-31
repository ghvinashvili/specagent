#!/usr/bin/env python3
"""Waiter: exit when a file has more lines than the given count (the verifier on build-log.md; anyone waiting for an answer line).

Usage: python3 _wait_for_log.py FILE LINES [--first TEXT]... [--once]   Polls once a minute; gives up after 8 hours.
  --first TEXT, repeatable: exit also when line 1 equals one of the texts (a line set in place adds no line).
  --once: one check, no polling; prints its line and exits 0 when the file has more lines now, 3 when not.
"""

import argparse
import pathlib
import sys
import time

ap = argparse.ArgumentParser()
ap.add_argument("file")
ap.add_argument("lines", type=int)
ap.add_argument("--once", action="store_true")
ap.add_argument("--first", action="append", default=[], metavar="TEXT")
args = ap.parse_args()
path, seen = pathlib.Path(args.file), args.lines


def check():
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines() if path.exists() else []
    if len(lines) > seen:
        return f"{len(lines)} lines now (was {seen}); first line: {lines[0] if lines else ''}", True
    if lines and lines[0].strip() in args.first:
        return f"first line is now: {lines[0]}", True
    return f"{len(lines)} lines, waiting for more than {seen}", False


for _ in range(480):
    message, found = check()
    if found or args.once:
        print(message)
        sys.exit(0 if found else 3)
    time.sleep(60)
print("timeout after 8 hours")
sys.exit(1)
