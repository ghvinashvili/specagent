# Assignment: builder (lane A)
Wait for the plan with `python3 /run/_wait_for_log.py /run/plan-log.md 2`; it exits when the index is written.
Before each task, wait with `python3   /run/_wait_for_task.py /run/build-log-b.md 4` (it re-arms on its own).
Wait for your task with `python3 <run-dir>/_wait_for_ready.py <run-dir>/build-log-a.md <lines you have seen>`.
Commit with `git commit -m "<message>" -- <paths>`.

Quote a file name with one backtick (`) on each side.

Wait for the critic in the background with `python3 <run-dir>/_wait_for_log.py
<run-dir>/critique.md <lines>` (one waiter per file).

A finding line looks like this (its backticks are text):
```text
B1: sent to plan-fixer — `python3 <run-dir>/_wait_for_log.py <run-dir>/verify.md <lines>` hangs

B2: fixed in code — the waiter's path
```
