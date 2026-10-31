---
title: A run is collected only after its record is checked as saved
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: what the collector deletes is gone, so it first proves that the run's records, lessons, done commits and Deferred items reached the main branch, the skill or the tracker
would_change_if: a collected run whose lesson, done commit or Deferred item turned out lost, or a check that refused a run whose record was saved
decision_status: decided
scope: global
tags:
  - decision
---
# A run is collected only after its record is checked as saved

Before it deletes anything, `collect_run.py` checks the run's record: the final record lines; each lesson of the run
marked `(skill: <sha>)` with that commit in the main branch, or `(skill: none)` (a script cannot judge whether a
lesson's meaning reached the skill, so the manager marks each lesson and the collector checks the marks); every build
log's done commit and each `--final` commit in the main branch; every Deferred item of the plan, read outside fenced
code, in a tracker row; and nothing unsaved in what goes. A failed check refuses the run and names what is missing
(manager spec 5.9.4 and 8.2.13; tracker TD-010).

## Record and source
- [The collector](../../.claude/skills/running-specagent-pipelines/scripts/docs/collect_run.md)
- [The collector's yes, then the standing rule](collector-yes-then-standing-rule.md)
