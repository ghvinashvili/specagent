---
title: The template is English only
type: decision
status: draft
updated: 2026-10-29
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: a script outside the Latin blocks costs about twice the tokens for every agent that reads it, and the template copies its text into every project
would_change_if: a script outside the Latin blocks costs no more tokens than English for the models a pipeline runs
decision_status: decided
scope: global
tags:
  - decision
---
# The template is English only

`harness validate` reports a letter of a refused block in a file git tracks or is about to track; a project whose product text is
in another script narrows it with `english_only:`; a summary is English, one page, `<name>.summary.md`; the attack stage writes
`output/summary.md`; the original design record is in the owner's vault.

## Record and source
- [ADR-0030 The template is English only](../../docs/decisions/0030-the-template-is-english-only.md)
