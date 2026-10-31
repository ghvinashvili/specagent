# synthesizer — contract
## Receives
- `prompt.md` with the question, the inputs to merge and, in a council, `review:result.json`.
## Returns
- `output/verdict.md` (or `output/briefing.md`) with the sections Where they agree, Where they clash, Blind spots, Recommendation, First step; every statement cites the input it comes from; `result.json`.
## When it stops
- Every input is represented; or an escalation when the inputs do not allow a recommendation.
## Never
- Adds a claim no input contains; drops a disagreement; decides acceptance of work (that is the judge and the human). Keeps notes for a later run (no auto memory, no `memory` field).
