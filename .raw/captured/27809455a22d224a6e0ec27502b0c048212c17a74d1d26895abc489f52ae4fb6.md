---
title: One score per run, by script
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-30
audience: [all]
decided: 2026-10-30
by: owner
why: every hand-over costs a hand-off note and a start-up of 32-33k tokens plus the re-reading of the same files; the owner folds one pair of roles at a time and keeps what wins, so each run is measured the same way first
would_change_if: a hand count of a run's findings per task that differs from the script's numbers
decision_status: decided
scope: global
tags:
  - decision
---
# One score per run, by script

Every run of the SpecAgent pipeline is scored by `scripts/manager/score_run.py <run-dir>`, which prints one line and
three tables from the run folder's records and the sessions' transcripts: the findings per task by kind (C, A, R, V,
the `(plan)` V ids and the ones the critic missed, the builders' B ids), the sessions, hand-overs, cap orders and idle
restarts per role with the first-call context and the cache-read share, the cost per task and per role, the request
lines with the minutes to their answer, and the lesson classes repeated. The rules are the same for every run and are
written in the manager scripts' README; the count of rejected findings per task comes with the run's Task 6. The
first score, of the manager-build run of 2026-10-29, is the baseline every fold is compared with.

## Record and source
- [score_run.py in the manager scripts' README](../../.claude/skills/running-specagent-pipelines/scripts/manager/README.md)
- [The pipeline-fold design, Decided 1](../../docs/design-docs/pipeline-fold.md)
- Task 1 of the pipeline-fold run, commit 84a5dad, with the fixes of V1-V4 (aae090e) and of R1-R3 and R5
