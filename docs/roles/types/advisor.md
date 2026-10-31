# advisor — contract
## Receives
- `prompt.md` with the brief, `frame:output/question.md` and its own `tasks.json` holding one task: the perspective to take.
## Returns
- `output/answer.md` (150 to 300 words, no perspective name in the text); the task's `passes` flag; `result.json`.
## When it stops
- The answer is written; or an escalation when the question cannot be answered from that perspective.
## Never
- Reads another shard's directory; names its perspective in the answer; hedges to reach agreement; exceeds the length. Keeps notes for a later run (no auto memory, no `memory` field).
