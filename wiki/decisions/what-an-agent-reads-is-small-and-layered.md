---
title: What an agent reads is small and layered
type: decision
status: draft
updated: 2026-10-29
created: 2026-10-28
audience: [all]
decided: 2026-10-28
by: owner
why: every step of a session re-reads its whole context, so a file read whole that the step does not need is paid for on every later step
would_change_if: a measured run in which agents that read whole files finish with fewer tokens than agents that read indexes and ranges
decision_status: decided
scope: global
tags:
  - decision
---
# What an agent reads is small and layered

A plan is a folder, an index and task files of at most 1,500 lines (`harness plan-lint`); a document folder has an index
of one line per page; a page stays under 12 KB; a large file is read by its sections through `ops/outline.py`.

## Record and source
- [ADR-0026 Plans in parts and layered document indexes](../../docs/decisions/0026-plans-in-parts-and-layered-document-indexes.md)
