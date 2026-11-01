# `wait_for_log.py` — the verifier's waiter
```
python3 -I scripts/wait_for_log.py FILE LINES [--first TEXT]... [--once]
```
Exits when FILE has more than LINES lines (the verifier on build-log.md; anyone waiting for an answer line).

Without `--once` it polls every 30 s and returns within 3.5 minutes: exit 0 with work, else exit 3 with its line and
"Run the same command again now: a call within 5 min keeps the prompt cache warm", and the role runs it again
(owner, 2026-11-01; until then it polled once a minute for up to 8 hours and exited 1 at the end).

`--once`: one check, no polling; it prints its line and exits 0 when FILE has more lines now, 3 when not (2 is a usage
error), the form a role's `work_check` takes.

`--first TEXT`, repeatable: it also exits when line 1 of FILE equals one of the texts. The planner waits so on
`critique.md`, whose line 1 the critic sets in place, which adds no line.
