---
name: escalate
description: Ask the human in escalations/<NNN>.json and stop. Use when material conflicts or is missing, a tool fails twice or the brief is silent.
user-invocable: false
allowed-tools: Read Write Bash(ls *)
---
# Escalate

1. Next id: `ls $HARNESS_RUN_DIR/escalations`, take the highest `NNN` and add one; start at `001`. If `$HARNESS_BLIND` is `1` you cannot read or write that directory: write the same JSON as `escalation.json` in your stage directory (`$HARNESS_STAGE_DIR`) with `"id": "000"`; `harness poll` assigns the number and files it.
2. Write `escalations/<NNN>.json` following `schemas/escalation.schema.json`: `stage`, `shard` (from `$HARNESS_SHARD`, when set), `question` (one sentence), `context` (where you saw it, with paths and quotes), `options` (two to four, each with its consequence), `recommendation` (or null), `blocking: true`, `status: "open"`, `answer: null`.
3. Rewrite `result.json` with `status: "escalated"` and the question in `open_questions`.
4. Rewrite `progress.md` so that the step after the answer is explicit.
5. Stop. Do not continue on a guess; the manager resumes you with the answer as your next message.

The Stop hook lets you stop when an escalation with `status: open` exists for your stage, or when `result.json` is valid and final (`complete`, `escalated` or `failed`); a `partial` result does not let you stop.
