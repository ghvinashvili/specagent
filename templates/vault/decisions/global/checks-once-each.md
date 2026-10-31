---
title: Every check runs once, by one role; full suites only at milestones; heavy runs take a machine lock
type: decision
scope: global
kind: lesson
template: yes
status: verified
updated: 2026-10-31
audience: [planner, builder, verifier]
sources: []
decided: 2026-10-16
by: owner
proof: [context/measurements/2026-10-25-checks-once.md]
why: "a site build dragged on because of repeated tests: builder and verifier each ran the full suite and the gate on every task, queued on one lock"
decision_status: decided
would_change_if: never; nothing is dropped, only repetitions
---
# Checks once each

**Rule.** Every check runs once, by one role. The builder runs the task's own tests and one gate at the end of the task; the verifier runs the same tests in its clean copy plus its own probes. Full suites (the complete test suite, check-all, a page-speed audit on every page, a live full cycle) run only at milestones and at the end, in the background. No run lasts longer than 15 minutes between milestones, and every lock has a timeout.

**Why.** A site build dragged on because of repeated tests: the builder and the verifier each ran the full suite and the gate on every task, queued on one lock. Nothing is dropped, only repetitions, so quality does not fall. The same builder and verifier running heavy runs together had also frozen a machine.

**How to apply.**
- Name this rule in the builder and verifier briefs from the start.
- Run test files four at a time, slowest first, not one after another: four kernel test files took 157 s in a row and 63 s at once, the same assertions passing. At most four at once per role; a test that fails only beside others shares state and is a code finding.
- Run tests on the same database engine as production, never on a lighter one to save time: offered speed against the risk of missing database-specific faults, the owner chose no errors.
- Heavy runs (browser checks, full runs) take one machine lock with a timeout, so the builder and the verifier never run them together.
- A step that runs two or more test files uses the parallel runner of the project, and reads its one-line-per-run log before any output.
