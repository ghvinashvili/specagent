# `check_formats.py` — the format check of a run folder
```
python3 -I scripts/check_formats.py <run-dir> [--repo <checkout>] [--state <monitor.json>] [--json]
```
The lines the waiters and the watcher parse. Errors (exit 1): a record file whose line 1 is not `STATUS: …`; a finding
heading used twice (`#### V29, round 2` reuses V29); an answer line for an id no file defines; an id answered twice in
critique-response.md (`critique-response.md:<line>: <id> answered twice`; the first answer stands); an answer written
as a list item in critique-response.md; a `#### V<n>` without its `(code)`, `(plan)`, `(spec)` or `(brief)` cause
(`(brief)`: a run without a planner, the fix is in a brief or a rule); a `Task N: done —
<sha>` line whose sha is not a commit of the checkout (`--repo`, default the `cwd` of the agent whose `status` is
that log, in `_control/_agents.json`, then `_agents.json`, then `_agents-active.json`); a hand-over note whose line 1
is not `HANDOFF <role> after Task <N> — <YYYY-MM-DD HH:MM>`; a request line open past the bound `_common.md` names
(`Request-line bound: <m> minutes`, default 15; the age from `--state`, else the file's mtime) or an answer line that
closes none; a `Merged:` line of `lessons.md` without a hex sha or whose sha the merged-into checkout lacks or, when
every lane worktree is gone, the `--repo` repository lacks; a waiter
that counts the Merged marker with `grep -c`; a ticked duty in `_control/duties.md` without its UTC time. Open request
lines are listed under `open` by kind. Information (exit 0): the open ids per kind and the done tasks, `open: … | done
tasks: <n> | errors: <n>`. It reads every `build-log*.md` of the run folder; `B<n>: sent to planner` and `B<n>: sent
to plan-fixer` both define a B id.
