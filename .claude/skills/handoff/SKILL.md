---
name: handoff
description: Rewrite the run's HANDOFF.md from state.json, results and escalations. Use after every launch, gate, escalation or approval.
argument-hint: "[run-id]"
allowed-tools: Bash(uv run harness handoff *) Read
---
# Handoff

Run `uv run harness handoff --run $0`. It renders `templates/handoff.md` from `manifest.json`, `state.json`, every `result.json` and every escalation, and writes `HANDOFF.md` in the run directory (`<runs root>/$0/`). Read the result and correct wording only; every fact must come from those files.
