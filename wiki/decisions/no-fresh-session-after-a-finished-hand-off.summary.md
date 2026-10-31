Decision (owner, 2026-10-30): a hand-off note starts a fresh session only when the role's work_check says work waits.
Exit 0 launches; exit 3 logs idle, and the watcher re-checks the role every round and launches once the check passes.
Any other exit, or a check that cannot run, launches; a note that answers the watcher's own hand-over order launches unchecked.
The example gives the critic wait_for_task.py --log ... --once and the plan fixer open_ids.py --cause plan; builders and verifier none.
