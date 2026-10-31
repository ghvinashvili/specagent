---
title: The record monitor answers no request
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: every answer to a request changes a worktree or the sandbox, and the manager's guards cover only the commands the manager runs
would_change_if: the guards come to cover the monitor's own commands, and a run shows requests waiting on the manager long enough to cost a role's session
decision_status: decided
scope: global
tags:
  - decision
---
# The record monitor answers no request

`monitor_records.py watch <run-dir>` reads the run's records, finds the request lines (`SANDBOX:`, `COPY-REQUEST:`,
`CHECKOUT-REQUEST:` and `FF-REQUEST:`), the claims, the `VERDICT:` lines and the `Merged:` lines, and wakes the
manager; it answers no request itself. The manager does what a request asks, answers it with
`monitor_records.py answer <run-dir> <request-id> <text>` (`--refuse` for a refusal) and re-arms the monitor with the
same `watch` command. Every answer changes a worktree or the sandbox, and the manager's four guards cover only the
commands the manager runs (manager spec 5.5, need 4).

## Record and source
- [The record monitor](../../.claude/skills/running-specagent-pipelines/scripts/docs/monitor_records.md)
- [The manager runs without the sandbox, with four guards](the-manager-runs-without-the-sandbox.md)
