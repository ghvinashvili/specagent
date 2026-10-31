---
title: ECC content is pinned, never its mechanism
type: decision
status: draft
updated: 2026-10-29
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: ECC's rules, skills and agent texts are useful as text, and its installer, hooks and agent mechanics would bring a second harness into the template
would_change_if: the template takes a plugin mechanism that keeps ECC's updates without its runtime
decision_status: decided
scope: global
tags:
  - decision
---
# ECC content is pinned, never its mechanism

The template keeps copies of chosen ECC files at one pinned commit with their licence and checksums, the rules under
`.claude/rules/ecc/`, the skills under `.claude/skills/`, the agent texts as brief material in
a folder of the documentation (never `.claude/agents/`); a re-pin follows the sources page. Revised for the place of the ECC texts on 2026-10-30: [ECC texts live under .claude/ecc](ecc-texts-live-under-claude-ecc.md).

## Record and source
- [ECC sources](../../.claude/ecc/sources.md)
- [ECC texts live under .claude/ecc](ecc-texts-live-under-claude-ecc.md): the place of the agent texts and of the pages about the pin, which this decision revises
