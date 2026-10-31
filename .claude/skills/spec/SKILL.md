---
name: spec
description: Start a feature spec under specs/<NNN-feature>/ from the templates and constitution gates. Use when the human asks for a new spec.
disable-model-invocation: true
argument-hint: "[feature-name]"
allowed-tools: Bash(ls specs *) Read Write
---
# Spec

1. Next number: highest `NNN` under `specs/` plus one; directory `specs/NNN-$0/`.
2. Copy `templates/spec/spec.md`, `plan.md`, `tasks.md` into it; create `contracts/`.
3. Fill `spec.md` from the human's words only; every guess becomes `[NEEDS CLARIFICATION: ...]`.
4. Leave `plan.md` and `tasks.md` as templates; the planner fills them in a run.
