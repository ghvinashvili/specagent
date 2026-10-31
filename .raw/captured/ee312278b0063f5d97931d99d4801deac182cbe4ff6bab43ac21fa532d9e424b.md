---
title: "The plan file is split: steps in one file, blocks in another"
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-30
audience: [all]
decided: 2026-10-30
by: owner
why: task files of 53-118 KB held 61% of their lines in code fences, so every hand-over re-read pasted blocks its unit did not need and a critic session reached the cap with no section written; a steps file about 40% of that size is read whole, and a block only when a step names it
would_change_if: the measurement run (Task 6 of the pipeline-fold run) loses quality against the manager-build run, with a new V the original run did not have or a rebuild; this pair is then unfolded and measured again
decision_status: decided
scope: global
tags:
  - decision
---

# The plan file is split: steps in one file, blocks in another

A task of a plan folder keeps its steps in `task-NN.md`: the goal, departures, contracts, interfaces, the steps with
their `Expected:` lines, the deferred list and the verified list. Every fenced block longer than 10 lines goes to
`task-NN.code.md` beside it, under a heading `## Block <id>` whose id is the step number and a letter (`1a`, `3b`), and
the step names its block (`Block 3b`) instead of pasting it. `harness plan-lint` (`packages/harness/src/harness/plans.py`)
checks the pair: a code file needs its task file; once a folder holds a code file, every block a step names is defined
there; a block is defined once and named by a step. The code file counts against no line limit; the steps file keeps
its 1,500 lines.

Tests stay written in full by the planner: the builder cannot bend a test to its code, and the critic attacks the test
before any code exists. Texts (changelog entries, decision pages, documentation prose) change hands: the planner gives
the facts the text must state and the test that pins them, and the builder writes the prose. The owner left that part
to the design's author on 2026-10-30: the test, not the author, holds the quality, and long texts stop being read twice.

The reading rules follow: the critic reads `task-NN.md` whole and every test block of `task-NN.code.md` in full, other
blocks only when a finding needs them; the builder and the verifier open a block when a step names it (`grep -n` for its
heading, then `sed -n`), never the code file whole.

## Record and source
- [Pipeline fold, Decided 4](../../docs/design-docs/pipeline-fold.md)
- [The form of a plan folder](../../docs/exec-plans/active/README.md)
- Task 3 of the pipeline-fold run
