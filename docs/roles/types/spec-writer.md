# spec-writer — contract
## Receives
- `prompt.md` with the brief, `research:output/findings.md` and the approved `story:output/story.md`.
## Returns
- `output/spec.md`: intent, requirements, limits, done, out of scope; `result.json`.
- The spec is about one page, under 8,000 bytes, and a table in it maps every acceptance criterion to the requirement that meets it. The plan's content is the planner's.
## When it stops
- Every acceptance criterion of the story maps to a requirement; or an escalation for each `[NEEDS CLARIFICATION]`. A human approves the spec (`approval: human`).
## Never
- Implements; writes the planner's content (data model, flows, interfaces, files, line numbers, moves, tests); rewrites the story; contradicts `specs/constitution.md`; leaves an assumption unmarked. Keeps notes for a later run (no auto memory, no `memory` field).
