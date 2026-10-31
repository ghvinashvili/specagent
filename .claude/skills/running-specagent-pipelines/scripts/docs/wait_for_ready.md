# `wait_for_ready.py` — the builder's waiter
```
python3 -I scripts/wait_for_ready.py --critique critique.md --response critique-response.md N [--once]
```
Exits when Task N is ready to build: the critique's line 1 is `STATUS: caught up through Task M` or `STATUS: reviewed
through Task M` with M >= N (or `STATUS: done`), and every C and A id filed under the shared sections or under Tasks
1..N has an answer line.

`--once`: one check, no polling; it prints its line and exits 0 when Task N is ready now, 3 when not (2 is a usage
error), the form a role's `work_check` takes.
