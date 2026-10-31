---
name: resume-stage
description: Resume a unit under its session id. Use when harness poll prints resume, rework or recheck, or an escalation is answered.
argument-hint: "[run-id] [stage] [escalation-id]"
allowed-tools: Bash(uv run harness resume *) Bash(uv run harness escalations *) Bash(claude agents *) Read
---
# Resume a stage

1. `uv run harness escalations --run $0 --stage $1` lists the stage's escalations and their status.
2. `uv run harness resume --run $0 --stage $1` resumes the unit under its newest known session id (the manifest's, or the copy an earlier resume recorded); add `--shard N` for one shard of a sharded stage. Add `--escalation $2` to deliver that answer verbatim; add `--message "<text>"` only for an instruction the human dictated, verbatim. If it prints `config_changed`, stop and tell the human.
2a. For a `rework` or `recheck` action: `uv run harness resume --run $0 --stage $1 --rework`, without `--message`: the harness delivers the findings from `rework.md`, or the instruction to check again after it rebuilt the stage's inputs and Material. A plain resume of such a unit is refused with `in_rework`; `round_moving` means run `uv run harness poll --run $0` first; `max_runs` means the loop is over: tell the human.
3. The CLI chooses `claude respawn <job-id>` when there is nothing to deliver and the old row is still listed as `stopped` or `failed`, `claude --resume <session-id> --bg "<message>"` otherwise, and `claude -p --resume <session-id> …` for a `mode: print` unit (run to completion; the output is processed like a first run); you do not choose. Pass the `message` that `harness poll` printed for the unit (the failing gate checks, or the failed print run's error) unless the human dictated another.
4. Update HANDOFF.md with the `handoff` skill and report to the human in one line.

When the answer says `continued as a copy <id>`, Claude Code started a copy under a new session id; the CLI already recorded it in `state.json` and `poll` follows it. The CLI refuses a resume above `max_attempts`; then you ask the human instead of retrying.
