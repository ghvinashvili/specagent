# story-writer — contract
## Receives
- `prompt.md` with the brief and `research:output/findings.md`.
## Returns
- `output/story.md`: the story, numbered acceptance criteria in checkable form, edge cases, out of scope, open questions; `result.json`.
## When it stops
- The story is written and every criterion can be checked by a test or an inspection; or an escalation for a requirement the brief leaves open. A human approves the story (`approval: human`).
## Never
- Chooses a technical solution; names files to change; adds a requirement the brief does not contain. Keeps notes for a later run (no auto memory, no `memory` field).
