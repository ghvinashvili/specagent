---
title: The control plane is a later run
type: decision
status: draft
updated: 2026-10-29
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: a control plane over runs needs the run loop and the pipeline skill settled, and both changed in this run
would_change_if: the owner moves it into an earlier run
decision_status: decided
scope: global
tags:
  - decision
---
# The control plane is a later run

ECC's control plane is not part of release 1.4.0; the main session starts and watches a run's sessions with the pipeline
skill's waiters and watcher; it is a later run, after the spec of the manager chat.

## Record and source
- The owner's decision in the template-core run (no file).
