# writer — contract
## Receives
- `prompt.md` with the brief, the manager's assignment, the plan, the patch of the planner's trial when there is one (a reference to start from; the plan wins where they differ, and the test files it adds are kept as given), the critic's findings and attack tests when a critic attacked the plan, the reader's notes to look facts up in and `tasks.json`: every task of the plan, or in a wave this shard's dependency-closed part (every `depends_on` is inside the file or was finished in an earlier stage), so nothing waits on another shard's branch.
## Returns
- Code or documents on its worktree branch, committed with Conventional Commits; the pages of its tasks under `wiki/`, `docs/runbooks/` or `docs/decisions/` in the same commits as the code, a new or changed wiki page as `draft` (`.claude/rules/wiki.md`), unless the planner gave the task `"docs": "none — <reason>"` (a `docs` the writer adds to its own `tasks.json` counts for nothing); `tasks.json` with `passes` flipped for finished tasks and `evidence` filled; `report.md` beside it (the commits, a claim per task with its command and exit code, the state at the end, the decisions the plan did not make, what was noticed and left), which the verifier checks statement by statement; `result.json` naming the branch.
## When it stops
- Every task passes its steps and tests, in dependency order, the given tests pass as given, and a test of every new behaviour was seen to fail when the behaviour is broken; or an escalation. Resumed with findings of a round, it answers each under `Round <n>` in `report.md`.
## Never
- Edits or deletes tests to pass, or changes a given test; touches tasks outside its file; pushes; changes the plan; keeps notes for a later run (no auto memory, no `memory` field).
