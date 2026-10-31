---
name: loop-tick
description: Run one tick of a loop from docs/loops/<name>.yaml. Use when a schedule, the night tick or the human asks to advance a loop.
argument-hint: "[loop-name]"
allowed-tools: Bash(uv run harness loop *) Read
---
# Tick a loop

Argument: `$0` = loop name (the file `docs/loops/$0.yaml`).

1. `uv run harness loop tick --name $0` prints one JSON object. Act on its `action` and on nothing else:
   - `wait`: the loop's last run is still active. Handle that run like any other (poll, resume, escalations, approvals). Start nothing.
   - `launch`: a run was created from the loop's goal with the loop's pipeline. Launch its first stage with the run-stage skill and continue as docs/roles/MANAGER.md describes.
   - `prompt`: read the printed `file` and do exactly what it says in this turn.
   - `external`: the loop runs in CI; there is nothing to do here.
   - `exit`: the episode ended for the printed `rule` (success, failure, max_iterations, max_minutes, max_usd, no_progress, disabled, not_ready). Report the rule and the detail to the human in one line. For every rule except success, tell the human that the schedule should stop until someone looks.
2. Never change a loop file, its limits or its state file. A human edits `docs/loops/` in a pull request.
3. If a run exists, update its HANDOFF.md with the handoff skill.
