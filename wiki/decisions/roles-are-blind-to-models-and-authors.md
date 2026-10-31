---
title: Roles are blind to models and authors
type: decision
status: draft
updated: 2026-10-29
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: a reviewer who knows or guesses which model wrote the work judges the model instead of the work
would_change_if: a measured run shows the same findings on the same work whether or not the reviewer knows its author
decision_status: decided
scope: global
tags:
  - decision
---
# Roles are blind to models and authors

No role is told which model another runs on, and none tries to find out; every role runs sandboxed, and its settings
deny the transcripts, the run's `_control/`, the checkout's `docs/handoff/`, `/proc`, `ps`, `pgrep` and
`claude agents|logs|attach` to its tools, and its sandbox denies the same folders to its shell; a finding or a message
never names a model; the harness keeps `blind: true` and `repo_deny` for its role types.

## Record and source
- [The pipeline skill's example README](../../.claude/skills/running-specagent-pipelines/example/README.md)
