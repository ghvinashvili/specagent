# `wait_for_log.py` — the verifier's waiter
```
python3 -I scripts/wait_for_log.py FILE LINES [--first TEXT]... [--once]
```
Exits when FILE has more than LINES lines (the verifier on build-log.md; anyone waiting for an answer line).

`--once`: one check, no polling; it prints its line and exits 0 when FILE has more lines now, 3 when not (2 is a usage
error), the form a role's `work_check` takes.

`--first TEXT`, repeatable: it also exits when line 1 of FILE equals one of the texts. The planner waits so on
`critique.md`, whose line 1 the critic sets in place, which adds no line.
