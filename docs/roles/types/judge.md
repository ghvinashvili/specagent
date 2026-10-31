# judge — contract
## Receives
- `prompt.md` with the verifier's report and the critic's critique paths; in the default and fix tables also the plan and the change as `changes.patch`, without a checkout.
## Returns
- Structured output matching `schemas/stage-result.schema.json` with `verdict.decision` in accept, revise, replan, reject and `verdict.reasons`, each naming its source as `<stage>#<n>` or a line of `changes.patch`. `revise` sends the work back to the writer; `replan` and `reject` stop the run for the human.
## When it stops
- The single `-p` invocation ends with valid structured output (the launcher writes `result.json`).
## Never
- Opens the branch or runs anything; gathers new evidence; launches anything; returns prose instead of JSON; keeps notes for a later run (no auto memory, no `memory` field).
