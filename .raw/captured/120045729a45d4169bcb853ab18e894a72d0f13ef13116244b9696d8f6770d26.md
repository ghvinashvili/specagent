---
title: The learning layer is a later run
type: decision
status: draft
updated: 2026-10-29
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: a layer that learns from runs needs measured runs, and this run's evals and run report give the first
would_change_if: the owner moves it into an earlier run
decision_status: decided
scope: global
tags:
  - decision
---
# The learning layer is a later run

ECC's learning layer (its instinct model) is not part of release 1.4.0; it comes after the spec of the manager chat
(`docs/roles/MANAGER.md`), as the first priority of the run after it, and starts from the pipeline evals and
`harness pipeline-report`.

## Record and source
- The owner's decision in the template-core run (no file).
