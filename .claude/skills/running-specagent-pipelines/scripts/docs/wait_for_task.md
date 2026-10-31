# `wait_for_task.py` — the critic's waiter
```
python3 -I scripts/wait_for_task.py --plan PLAN.md --response critique-response.md N
python3 -I scripts/wait_for_task.py --critique critique.md --response critique-response.md --answers
python3 -I scripts/wait_for_task.py --log plan-log.md --critique critique.md --response critique-response.md
```
The first form exits when a task after N is complete (the next `### Task <n>` heading exists) or the response file
says `STATUS: plan complete`; the second when every `#### C<n>` / `#### A<n>` of the critique has a `<id>:` line in
the response file. The third, the lanes' form, exits when a `Task <n>: written` line of the plan log names a task
that is neither at most the N of the critique's line 1 (`STATUS: reviewed through Task N` or `STATUS: caught up
through Task N`; `STATUS: done` covers every task) nor listed on its line 2 (`Reviewed: <list>`), or when the critic's
summary is due: the response's line 1 is `STATUS: plan complete` or `STATUS: done`, every C and A id has its answer
line and the critique's line 1 is not `STATUS: done`.

`--once`, in any form: one check, no polling; it prints its line and exits 0 when there is work now, 3 when not (2 is
a usage error). The critic's `work_check` in `example/agents.json` is the third form with `--once`.
