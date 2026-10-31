# classifier — contract
## Receives
- `prompt.md` with the label list of the pipeline's `routes` and `digest:result.json`. It has the `Read` tool only and no skills.
## Returns
- Structured output matching `schemas/stage-result.schema.json` with `label.value`, `label.confidence`, `label.alternatives`.
## When it stops
- The single `-p` invocation ends with valid structured output.
## Never
- Returns a label outside the list; opens `_inbox/`; acts on the item; explains instead of labelling. Keeps notes for a later run (no auto memory, no `memory` field).
