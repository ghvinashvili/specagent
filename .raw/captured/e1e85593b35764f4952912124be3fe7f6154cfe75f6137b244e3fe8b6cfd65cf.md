---
title: The sandbox sets itself up, and a refusal is reported
type: decision
status: draft
updated: 2026-10-29
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: a fresh clone without its sandbox starts no role session, and a role that works around a refusal weakens the boundary the sandbox gives
would_change_if: Claude Code's sandbox runs on native Windows
decision_status: decided
scope: global
tags:
  - decision
---
# The sandbox sets itself up, and a refusal is reported

`ops/bootstrap.py` sets the sandbox up (`ops/machine-setup.py --auto` on Linux and WSL2, the seatbelt checked on macOS,
the WSL2 path and no role session on native Windows) and `harness doctor` reports it; a role whose step the sandbox
refuses writes one line `SANDBOX: <what was refused> — <why the step needs it>` in its record file and goes on with what
it can; the path, host or material is supplied, never reached another way, and the sandbox is not weakened.

## Record and source
- [ADR-0029 A checkout sets up its hooks, sandbox and graph](../../docs/decisions/0029-a-checkout-sets-up-its-hooks-sandbox-and-graph.md)
