---
name: checkpoint
description: Save progress to disk so a restart resumes at the last finished step. Use after each unit, before long commands and before stopping.
user-invocable: false
allowed-tools: Read Write Edit
---
# Checkpoint

Paths come from the SessionStart context (`prompt`, `progress`, `result`, `output directory`).

- `progress.md`: rewrite the whole file with three sections: "Done" (numbered, each with its output path), "Next" (the exact next step), "Open" (questions carried forward).
- `result.json`: rewrite the whole file following `schemas/stage-result.schema.json`; `status: partial` until the stage is finished, then `complete`; list every file under `output/` in `outputs`, with its path as seen from your stage directory (`output/notes.md`). Code on your branch is listed with kind `code` and its path in the repository.
- `tasks.json` (writer only): flip `passes` to `true` and fill `evidence` for a finished task; change nothing else in the file.

A hook validates every JSON file of the run: an invalid Write is denied before it happens, an invalid Edit is only reported after it happened and you must rewrite the file. Always rewrite `result.json` with Write; never append to it or edit it in place. Never write outside your stage directory except `escalations/`.
