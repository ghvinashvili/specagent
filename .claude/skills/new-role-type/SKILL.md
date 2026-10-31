---
name: new-role-type
description: Create a role type from templates/role-type.md, validate it and regenerate the catalog. Use only when a human asks for a new type.
disable-model-invocation: true
argument-hint: "[type-name]"
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/new_type.py *) Bash(uv run harness catalog *) Read Edit Write
---
# New role type

1. `python3 ${CLAUDE_SKILL_DIR}/scripts/new_type.py $0` copies the template to `.claude/agents/$0.md` with `name: $0`.
2. Fill `description` with the three sentences the template asks for, then `model`, `effort` and `tools` (never `Agent`).
3. Give every numbered step of the Working method its rule at the step's end, `<!-- check: ... -->` in the language of `packages/harness/src/harness/gates/steps.py` (read:, ran:, wrote:, output:, when:, trust:); once `docs/roles/need-to-know.yaml` gives the type a `steps` mode, `uv run harness validate` names a step without one.
4. Write the contract `docs/roles/types/$0.md` with the sections Receives, Returns, When it stops, Never.
5. `uv run harness catalog` validates every type against `schemas/role-type.schema.json` and regenerates `docs/generated/role-types.md`.
6. Add the type to `docs/roles/stages.yaml` only when the human named the stage it serves.
