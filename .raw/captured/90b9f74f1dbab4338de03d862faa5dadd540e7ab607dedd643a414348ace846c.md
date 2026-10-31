---
title: The owner's vault is read on need
type: decision
status: draft
updated: 2026-10-29
created: 2026-10-28
audience: [all]
decided: 2026-10-28
by: owner
why: the vault holds rules and records of every project, and a session that read it whole would fill its context with what its task does not need
would_change_if: the vault gets a search a session can ask for one rule
decision_status: decided
scope: global
tags:
  - decision
---
# The owner's vault is read on need

`CLAUDE.md` names the vault (`vault_path` of `docs/template/variables.yaml`); a session opens its `INDEX.md` only when a
step needs an owner rule, follows only the links it needs and reads a long page by ranges; the vault is read-only to
every role, and where a vault page and a brief differ the brief wins and the difference is logged.

## Record and source
- [CLAUDE.md](../../CLAUDE.md), the section "The owner's vault"
