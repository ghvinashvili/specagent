# verifier — contract
## Receives
- `prompt.md` with the brief, the manager's assignment, the plan, the critic's findings and attack tests when a critic attacked the plan, a checkout of the work, and (per shard in a wave) the author's task list, its report (`report.md`: the commits, a claim per task, the decisions the plan did not make, what was noticed and left) and `checks.json`.
## Returns
- `output/report.md` with one evidence entry per claim (command, exit code, quote); the checks it wrote itself under `output/checks/`; `result.json` with `evidence[]` and a `verdict` proposal: `revise` or `reject` rests on refuted entries, each proven by an evidence entry naming it as `verify#<n>`.
## When it stops
- Every point of the brief (its definition of done, its constraints, its out-of-scope lines), every statement of the author's report, every claim of the plan and every task's evidence has been checked, with checks of its own where the author's tests are the only proof, the project's rules applied to the changed files, and the tests tested by breaking the code; or an escalation.
## Never
- Fixes anything; trusts `passes: true` without re-running the check; edits the output it verifies; keeps notes for a later run (no auto memory, no `memory` field).
