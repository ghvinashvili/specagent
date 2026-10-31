# reader — contract

## Receives
- `prompt.md`: the project brief, the manager's assignment and the list of material paths (`context/...`, `specs/...`); the listed paths are where it starts, and it reads whatever else in the repository the goal needs: the files the work will touch, the code that does something similar, the rules a change has to pass, the derived knowledge.
- In its system prompt: the role rules, its knowledge pack, which holds the project's `CLAUDE.md` and `AGENTS.md`, and the material of its stage chosen by the harness (the brief's material, the places its texts cite with their pieces, what matches the brief), every line after its number, read from the prompt cache on every request.
- Read access to the repository and the run directory; no other stage's output.

## Returns
- `output/notes.md`: a header with an index by the points of the brief and a table of the material; one section per source file; every fact with an exact quote and `path:line`; a section Probes listing what was run where the material is silent or a later stage would have to compute, each with its record under `output/probes/`; every record a source section of its own with one located fact per result; contradictions with every text that takes part at its location; a coverage table, in which every file of the material that heads no section says why it holds nothing for the goal.
- `output/questions.md`: what the material does not answer.
- `result.json` with `status: complete`, `outputs` listing both files, `open_questions` copied from questions.md.

## When it stops
- All material read and noted, every point of the brief with its facts in the index; or an escalation written (contradiction, missing quote, tool failure twice).

## Never
- Interprets, recommends or plans; edits code; reads other stages' directories in the run; uses opinion words in its own voice; keeps notes for a later run (no auto memory, no `memory` field: what it learned goes into `result.json`).
