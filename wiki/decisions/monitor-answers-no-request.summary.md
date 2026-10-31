Decision (owner, 2026-10-29): the record monitor answers no request.
monitor_records.py finds the request lines, claims, verdicts and Merged: lines and wakes the manager.
The manager does what a request asks and answers with monitor_records.py answer, then re-arms the monitor.
Every answer changes a worktree or the sandbox, and the manager's guards cover only the manager's own commands.
