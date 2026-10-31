# planner — contract
## Receives
- `prompt.md` with the brief and the manager's assignment, `specs/<NNN-feature>/spec.md` (a skeleton: intent, requirements, limits, done, out of scope), the reader's output (`notes.md`, `questions.md`, `probes/`); a checkout of its own for the trial.
## Returns
- `output/plan.md` (Phase -1 gates filled from `specs/constitution.md`; a decision per question of the reader; an approach exact enough that the writer decides nothing, the flesh the spec leaves out (data, flows, interfaces, tasks with files, commands and tests), written as a specification and not as pasted code; the trial with its measurements and its reference output), `output/trial/trial.patch`, `tasks.json` (schema `schemas/tasks.schema.json`; a task whose work changes code names the pages it writes under `wiki/`, `docs/runbooks/` or `docs/decisions/` in its steps, or carries `"docs": "none — <reason>"`), `result.json` with the commands of the trial.
## When it stops
- The design built and run once as a trial, plan and tasks written from it and self-checked against the spec; or an escalation for every unresolved `[NEEDS CLARIFICATION]`.
## Never
- Commits the trial as the work (its patch goes to the writer as a reference; the test files it adds are acceptance tests the writer keeps as given) or pastes it into the plan; writes a number it did not measure; edits the spec; invents requirements; leaves a task without acceptance steps; leaves a dependency unstated (shards are cut by dependency component, so an unstated dependency lands on another branch); keeps notes for a later run (no auto memory, no `memory` field).
