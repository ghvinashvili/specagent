#!/bin/bash
# Runs one test command over test files or directories 4 at a time (owner's order, 2026-10-25; measured in an earlier
# project of the owner: four slow test files 157 s one after another, 63 s at once, the same tests and assertions
# passing, at least 13.5 GB of memory left free).
# Usage, from the folder the test command runs in:
#   bash ops/par-tests.sh <out prefix> "<test command>" <path> [<path> ...]
# <test command> is one argument, a program and its options (such as "uv run pytest -q"); each run is
# "<test command> <path>" under timeout -k 10 3600. Each path is relative to that folder; list the slowest first.
# Each run's output goes to <out prefix>-<n>.txt and one line per run to <out prefix>.log: "<n>: exit <code> in <s> s:
# <path>"; the last line is "done: <failed> failed of <total> in <s> s". Exit 1 if any run failed. PAR_JOBS=<n> changes
# the 4. Where the system has no timeout(1) (macOS), Homebrew's gtimeout, or ops/timeout.py, runs each command.
set -u
[ $# -ge 3 ] || { echo "usage: par-tests.sh <out prefix> \"<test command>\" <path> [<path> ...]"; exit 2; }
P=$1; C=$2; shift 2
LIMIT=$(command -v timeout || command -v gtimeout || true)
LIMIT_PY="$(cd "$(dirname "$0")" && pwd)/timeout.py"
export P C LIMIT LIMIT_PY
: > "$P.log"
t0=$SECONDS
n=$#
i=0
for f in "$@"; do i=$((i + 1)); echo "$i $f"; done | xargs -P "${PAR_JOBS:-4}" -L 1 bash -c '
  t=$SECONDS
  if [ -n "$LIMIT" ]; then "$LIMIT" -k 10 3600 $C "$1"; else python3 -I "$LIMIT_PY" -k 10 3600 $C "$1"; fi \
    > "$P-$0.txt" 2>&1
  echo "$0: exit $? in $((SECONDS - t)) s: $1" >> "$P.log"'
failed=$(grep -c -v ': exit 0 in ' "$P.log")
echo "done: $failed failed of $n in $((SECONDS - t0)) s" >> "$P.log"
[ "$failed" -eq 0 ]
