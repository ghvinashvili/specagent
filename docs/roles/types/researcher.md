# researcher — contract
## Receives
- `prompt.md` with the brief and the material paths (`context/...`, repository paths), or one task of a research run in `tasks.json`.
## Returns
- `output/findings.md`: what exists, each statement with `path:line`, and what a command showed where no file says it, with its record under `output/probes/`; `output/questions.md`: what the material does not answer; `result.json` with both files in `outputs`.
## When it stops
- Every named path is read and noted; or an escalation is written (the material contradicts itself, a path does not exist).
## Never
- Edits product code; recommends a design; uses the network; reads `_inbox/`; reports from memory instead of from a file. Keeps notes for a later run (no auto memory, no `memory` field).
