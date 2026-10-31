# comparator — contract
## Receives
- `prompt.md` with the question or rubric and the candidates' directory; candidates are known by shard number only.
## Returns
- Structured output matching `schemas/stage-result.schema.json` with `ranking.order`, `ranking.strongest`, `ranking.blind_spots`, `ranking.missed_by_all`.
## When it stops
- The single `-p` invocation ends with valid structured output (the launcher writes `result.json`).
## Never
- Asks who wrote a candidate; scores candidates one by one instead of comparing; edits a candidate; returns prose instead of JSON. Keeps notes for a later run (no auto memory, no `memory` field).
