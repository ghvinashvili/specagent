---
title: Code cases gate every push, session cases run nightly
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: a lesson class comes back unseen unless a case fails at push time, and a session case costs money and needs a key that GitHub Actions does not hold
would_change_if: a regression that the gate passed and a nightly session case caught first, or nightly runs that cost more than the cap
decision_status: decided
scope: global
tags:
  - decision
---
# Code cases gate every push, session cases run nightly

`.github/workflows/ci.yml` runs `uv run harness eval --suite regression --baseline --threshold 1.0` on every push and
pull request: the fourteen code cases (`session: false`, graded by the thirteen checks of
`evals/graders/pipeline_plan.py`) and every session case's code graders on its recorded baseline, with no session and
no key. The session cases run nightly on the owner's machine (`evals/nightly.sh`), at threshold 1.0, under a cost cap
that counts each started case at its worst; `evals.yml` keeps `instruction-version` and `plugin-evals`, and its
session job is gone. Each lesson class of 2026-10-29 has its guard: `pipeline-job-timeouts` (the wrapper timeout),
`pipeline-handoff-pointers` (a hand-over note with pointers instead of facts), `pipeline-ancestor-deny` (a sandbox deny
on an ancestor), the critic case's recorded baseline (the grader regex) and the lint that fails a suite naming a stage
that no longer exists (the stale case); `pipeline-waiters` checks the waiters (acceptance check 10.19).
`access-probe-critic` is removed, not ported, since its `critique` stage is gone (tracker TD-017). Graders are written
from recorded outputs (`evals/README.md`); the llm grader runs with `--setting-sources local` and refuses dimensions
that are not in English (TD-011).

This page supersedes these lines of ADR-0028, which stay as history: :17 and :104 (the probe left for later), :40 and
:52 (ten code cases, graded by `--no-sessions`), :45 (nine checks), :47 (standard library only: the job-timeouts check
imports `harness.evals`), :70 (the full suite at threshold 0.9, run by the main session) and :78 (the gate named as
`--no-sessions`).

## Record and source
- Task 8 of the manager-build run, commit baf3590: its Departures 2-5 and the four cases above
- [ADR-0028 Pipeline evals](../../docs/decisions/0028-pipeline-evals.md)
- [The evals](../../evals/README.md)
