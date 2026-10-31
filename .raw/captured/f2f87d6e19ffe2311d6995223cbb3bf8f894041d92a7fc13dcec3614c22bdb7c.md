---
title: ECC text reaches a brief by line range
type: decision
status: draft
updated: 2026-10-29
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: the same pinned words in every run let the findings per checklist item compare runs; a rewrite in each brief's own words drifts from run to run
would_change_if: the pasted ranges cost more context than the findings they bring are worth, or a re-pin moves the line numbers so often that the citations break
decision_status: decided
scope: global
tags:
  - decision
---
# ECC text reaches a brief by line range

A role's brief names the pinned ECC copies it borrows from in one line, `Spec: <pinned copy>:<a>-<b>[, ...] — <why>`,
or `Spec: none — <why>`; at launch the manager pastes those lines word for word into the run folder's brief, trimmed by
the drop rules K1-K5 and M of the sources page, under 60 lines in all. Every critic and verifier finding
cites its item as `Checklist: <file>:<line>`. This replaces the rule that a brief rewrites the copy in its own words
(manager spec, question 9, answer (a)). Revised for the place of the ECC texts on 2026-10-30: [ECC texts live under .claude/ecc](ecc-texts-live-under-claude-ecc.md).

## Record and source
- [Choosing roles and skills](../../.claude/skills/running-specagent-pipelines/references/choosing-roles-and-skills.md)
- [ECC sources](../../.claude/ecc/sources.md)
- [ECC texts live under .claude/ecc](ecc-texts-live-under-claude-ecc.md): the folder of the pinned copies, which this decision revises
