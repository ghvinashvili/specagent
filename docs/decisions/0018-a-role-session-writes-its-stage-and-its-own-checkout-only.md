---
status: accepted
date: 2026-10-04
decision-makers: the human, who approved the brief of run 20261004-121127-fix-w1-leaks (wave 1 of the audit's fixes)
consulted: harness maintainers
informed: all package owners
---

# A role session writes its stage and its own checkout only, and takes no configuration or instruction from a checkout it does not own

## Context and Problem Statement
The audit of 2026-10-04 found that every role session could write the shared checkout and every unit's checkout
(01/F16: the launcher repeated the project's `./.claude/worktrees` write path for every type), rewrite its own input
copies, which the gates trust (01/F17), and write the run's JSON files through the shell (04/F7). Claude Code's file
tools do not follow the sandbox (sandboxing.md:42 in `context/fix-20261004/claude-code-facts.md`), a sandboxed
command saw the messaging token and socket of its session (item 1.9), a session that enters a checkout loads the
configuration and the `CLAUDE.md` files it finds there (worktrees.md:43), and the planner of the fix measured that a
sandboxed command may still write `.claude/rules/`, `.claude/CLAUDE.md` and `.claude/agent-memory/` of its own checkout.

## Decision Drivers
* A type that does not change the repository writes nothing of it; a type that does writes its own checkout only.
* Every limit binds the shell (the sandbox) and the Edit and Write tools (permission rules) alike.
* A deny rule decides before any prompt: the hook scripts a fix run opens stay open to the tools of its own checkout.
* A reviewer judges the work and takes no instruction from it.

## Considered Options
* Limits in the settings the launcher builds for each session (`access.stage_settings`, `access.write_limits`)
* Limits in `.claude/settings.json`, the same for every session

## Decision Outcome
Chosen option: the settings the launcher builds, because what a session may write depends on its type and its checkout.
* No write path inside the repository is repeated from the project's `sandbox.filesystem.allowWrite`.
* A type without a checkout gets `Edit(//<repo>/**)` and `denyWrite` of the repository.
* A type with a checkout gets an `Edit(...)` deny rule and a `denyWrite` entry for every entry of the main checkout
  but `.claude` and `.git`, of its `.claude/` but `worktrees`, and of `.claude/worktrees/` but its own (the rest of the
  main checkout its shell sees only as the throwaway layer the sandbox lays over the home folder, as the planner
  measured); in its own checkout an `Edit(...)` deny rule for every part of `.claude/` Claude Code loads, without
  `hooks` when the brief says `- Hooks: open` and the checkout is its own work, and `denyWrite` of its own `.claude/`
  and `.mcp.json`. With the protected paths of the sandbox, no component of an approved hook-script path can be
  swapped for a link (item 1.18; the planner measured `.claude` and `.claude/hooks` refusing a rename with EBUSY).
* Every session: `Edit` deny and `denyWrite` of its `input/` and of `gate.json` and `checks.json`; `denyWrite` of
  `result.json`, `tasks.json`, `escalation.json` and the run's `escalations/`, which it writes with the Write tool.
* Read deny rules are also written as absolute `//` paths of the main checkout and of every checkout under it.
* `sandbox.credentials.envVars` unsets `CLAUDE_CODE_MESSAGING_TOKEN` and `CLAUDE_CODE_MESSAGING_SOCKET` for every
  sandboxed command; a sandboxed command cannot open a Unix socket (measured: `socket(AF_UNIX)` refused with EPERM).
* A reviewing session (a checkout that is not its own work) excludes every `CLAUDE.md`, `AGENTS.md` and
  `CLAUDE.local.md` of its checkout (`claudeMdExcludes`).
* The launcher copies only regular files whose real place is inside the producing stage (01/F14), refuses a table
  input whose path leaves it (01/F13), writes every input copy read-only with its sha256 in `<run>/_access/`, and the
  gate takes an input `checks.json` only with that sha256 (01/F17).

### Consequences
* Good, because the holes 01/F13, F14, F16, F17 and 04/F7 close in the settings and in the gate, each with a test.
* Bad, because the main checkout's entries are named as they are at launch; an entry made later is closed by
  guard-checkout and by Claude Code's worktree isolation, not by a deny rule.
* Bad, because `credentials.envVars` and `**` in `claudeMdExcludes` are taken from the repository's design notes
  (the design record in the owner's vault, `context/design-record/DESIGN-NOTES/`; was `design/DESIGN-NOTES.md`), not from the facts file: the live checks after integration confirm them.

### Confirmation
`packages/harness/tests/test_access.py`, `packages/harness/tests/test_gates.py`; the live checks of the plan of run
20261004-121127-fix-w1-leaks (`p26_write_access.py`, `p28_input_copies_writable.py`, the messaging token and socket).
