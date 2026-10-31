---
status: accepted
date: 2026-10-04
decision-makers: the human, who chose the code over a changed text in the brief of run 20261004-121127-fix-w1-leaks
consulted: harness maintainers
informed: all package owners
---

# The write gate runs a branch's tests in a sandbox, without the gating process's environment

## Context and Problem Statement
The write gate runs the whole suite on a checkout of a writer's branch (`docs/roles/RUNS.md`, `checks.json`), inside
`harness poll`, which the manager starts outside Claude Code's sandbox. The suite includes every test and conftest.py
the writer committed: the audit of 2026-10-04 (03/F21) showed a branch's conftest.py writing outside the checkout and
reading a variable of the gating process. ADR-0010 denies role sessions every command that runs outside the sandbox
because such a command "runs code a writer can change in its own checkout"; the gate did exactly that.

## Decision Drivers
* Code a role session wrote runs where a role session's own commands run, never with the manager's access.
* The template promises Linux, macOS and Windows through WSL2 (ADR-0009).
* No suite runs unsandboxed without anybody knowing, as no role session starts without its sandbox (ADR-0013).

## Considered Options
* Run the suite in a sandbox of its own, with a fixed environment
* Say in the decisions that a writer's tests run unsandboxed when its stage is gated
* Run the suite inside a role session

## Decision Outcome
Chosen option: a sandbox of its own (`packages/harness/src/harness/gates/_sandbox.py`). On Linux and WSL2 bubblewrap
(the copy `ops/machine-setup.py` provides where the system's is held back), on macOS Seatbelt (`sandbox-exec`), as
Claude Code's own sandbox does. What the suite sees: the system read-only, no network, a private `/tmp`, no home
directory but the toolchain paths of `docs/roles/need-to-know.yaml` (`toolchain`), the git configuration and the
gating interpreter's environment, read-only; the repository's `.git` read-only; the uv cache and the branch's checkout
writable. Its environment is fixed (`PATH`, `HOME`, `LANG`, `TMPDIR`, `NO_COLOR`, `UV_OFFLINE`); no variable of the
gating process reaches it. uv builds the checkout's environment from its cache, offline. Where no sandbox starts (no
bubblewrap or Seatbelt, a namespace refused, another platform) the suite is not run and the check fails with the
reason. `state.claude_version` answers `unknown` where no `claude` is, as in the sandbox.

### Consequences
* Good, because a writer's tests reach nothing a writer's session cannot reach, and the manager's variables stay out.
* Good, because measured on the planner's trial (run 20261004-121127-fix-w1-leaks): the whole suite ran in the
  sandbox, offline, in 19.5 seconds (562 passed, 8 skipped).
* Bad, because a test that needs the network or a file of the home directory outside the toolchain fails in the gate
  as it would in a role session.
* Bad, because the macOS path has not run on macOS; its command and profile are tested with the platform stood in for.

### Confirmation
`packages/harness/tests/test_gate_sandbox.py`; the probe `p21_gate_runs_branch_code.py`, run by the manager outside
the sandbox after integration, prints `ok: the branch's code did not run in the gate's process`.

## More Information
`docs/roles/RUNS.md` says where the suite runs. ADR-0010 stays as it is.
