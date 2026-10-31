Decision (owner, 2026-10-29): a run is collected only after its record is checked as saved.
collect_run.py checks the final record lines, each lesson's (skill: <sha>) or (skill: none) mark, the done commits.
Every --final commit must be in the main branch, and every Deferred item of the plan in a tracker row.
A failed check refuses the run and names what is missing; nothing unsaved is deleted.
