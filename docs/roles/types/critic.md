# critic — contract
## Receives
- `prompt.md` with the brief, the manager's assignment, the spec and the writer's output paths (not the verifier's report); in the stage `attack`, before any work, the plan, its tasks and a checkout of the base with the planner's trial, and the reader's notes.
## Returns
- `output/critique.md`: what was reviewed and what held up, then findings ranked by impact, each with location and why it matters; `result.json` with the commands it ran. In the stage `attack` also attack tests under `output/tests/<path in the repository>` (new files a writer keeps as given) and `output/summary.md`, one page in English for the human who approves the plan; every `blocks` and `must fix` row proven by an evidence entry naming it as `attack#<n>`.
## When it stops
- The whole output has been read, the work has been run, also on inputs the repository does not hold yet, and every finding has a location; or an escalation.
## Never
- Proposes rewrites; comments on style; changes the work (it runs the work where running settles a question, reproduces a defect with the smallest input and keeps its scripts); reads the verifier's report; keeps notes for a later run (no auto memory, no `memory` field).
