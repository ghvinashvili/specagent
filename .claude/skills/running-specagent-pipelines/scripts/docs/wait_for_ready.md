# `wait_for_ready.py` — the builder's waiter
```
python3 -I scripts/wait_for_ready.py --critique critique.md --response critique-response.md [--index 00-index.md --lane a] N [--once]
```
Exits when Task N is ready to build: the critique's line 1 is `STATUS: caught up through Task M` or `STATUS: reviewed
through Task M` with M >= N (or `STATUS: done`), and every C and A id filed under the shared sections or under Tasks
1..N has an answer line. With `--index <00-index.md> --lane <a|b>` only the ids of the lane's own tasks up to N in
the index's build order (the rows with that builder of the index's task table, found by its header cells Task, builder
and depends_on as `duty_list.py` finds it) and of Task N's `depends_on` tasks (a range `1-4` is each of its tasks)
count, with the shared sections: the other lane's open ids never hold this one (a project's run of 2026-11-02: a
builder waited 107 minutes on them). The two flags go together.

An index that is missing, holds no task table or has no Task N in the lane stops the waiter at its first call, with exit
2 and the reason on stderr, because a gate that read nothing would release the task (V15 of the verifier: a missing
file, a `planner` column and a `1-4` cell each released Task N while ids it waits for were open). The waiter holds a
copy of the reader of `duty_list.py` (`CODE_SPAN`, `SEPARATOR`, `RANGE`, `numbers`, `cells`, `task_table`) because it
runs alone from the run folder, where only the waiters are copied; `test_waiters.py` holds the copy to the original,
character for character.

Without `--once` it polls every 30 s and returns within 3.5 minutes: exit 0 with work, else exit 3 with its line and
"Run the same command again now: a call within 5 min keeps the prompt cache warm", and the role runs it again
(owner, 2026-11-01; until then it polled once a minute for up to 8 hours and exited 1 at the end).

`--once`: one check, no polling; it prints its line and exits 0 when Task N is ready now, 3 when not (2 is a usage
error or an index it cannot use), the form a role's `work_check` takes.
