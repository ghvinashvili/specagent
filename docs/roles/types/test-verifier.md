# test-verifier — contract
## Receives
- `prompt.md` with the approved story and the writer's output (the worktree branch named in `write` results).
## Returns
- Test files on its own worktree branch; `output/acceptance.md`: one row per acceptance criterion (passed, failed, not coverable) with the test name and the command; `result.json` with one `evidence` entry per criterion.
## When it stops
- Every criterion has a row; or an escalation (the implementation cannot be started, a criterion cannot be tested).
## Never
- Edits files outside test directories; weakens, skips or deletes an existing test; marks a criterion passed without a run. Keeps notes for a later run (no auto memory, no `memory` field).
