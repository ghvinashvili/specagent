---
title: The planner answers its own findings; the fixer is launched on demand
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-30
audience: [all]
decided: 2026-10-30
by: owner
why: every hand-over costs a hand-off note and a start-up of 32-33k tokens plus the re-reading of the same files; in the manager-build run of 2026-10-29 the plan fixer restarted five times between 01:51 and 03:31 with one finding to answer, and plan findings per task fell from 3-5 to 1 as lessons.md filled, so the queue the fixer was made for no longer forms in a mature run
would_change_if: the measurement run loses quality (a new V the original run did not have, or a rebuild); then this pair is unfolded and measured again
decision_status: decided
scope: global
tags:
  - decision
---
# The planner answers its own findings; the fixer is launched on demand

The planner of the SpecAgent pipeline answers the open C, A, B, `(plan)` V and `(plan)` R ids of its own tasks after
every part it writes (a `Task N: part <k>` or `Task N: written — <sha>` line), before the next part: it runs
`open_ids.py <run-dir> --kind C,A,B,V,R --cause plan`, fixes the unbuilt task file (the code of a built task is the
truth), appends its answer lines to `critique-response.md` and messages the asker. A part is the checkpoint because a
task is written in parts over hours; answering at a task's end would leave findings open for hours.

The plan fixer stays a role (`example/plan-fixer-assignment.md`), but the manager does not launch it at the start.
Its agent entry has `on_demand` and a `demand` object; the watcher launches it only when its open ids reach
`demand.queue` (default 6) or the oldest is `demand.wait_minutes` (default 45) old, stops it when its queue is empty,
and never revives it. These are the spec's `fixer_queue` and `fixer_wait_minutes`, kept per agent so two fixers by
parity keep their own. A new project, whose `lessons.md` is thin, sees the fixer early; a mature one may not see it at
all. With it, a `work_check` that exits 3 on a hand-over note now stops the session for every role.

## Record and source
- [The watcher's page, "on demand"](../../.claude/skills/running-specagent-pipelines/scripts/docs/watch_agents.md)
- [The pipeline-fold design, Decided 2](../../docs/design-docs/pipeline-fold.md)
- Task 4 of the pipeline-fold run, with the fix of R6 (the session stopped at a `work_check` exit 3)
