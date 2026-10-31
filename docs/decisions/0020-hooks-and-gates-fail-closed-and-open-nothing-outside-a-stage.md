---
status: accepted
date: 2026-10-04
decision-makers: the human, who approved the brief of run 20261004-121127-fix-w1-leaks (items 1.17 a, d, e)
consulted: harness maintainers
informed: all package owners
---

# Hooks and gates fail closed, read the main checkout, and open nothing outside a stage

## Context and Problem Statement
Hooks and gates run outside the sandbox with the user's full access (sandboxing.md:11 and :38-43 in
`context/fix-20261004/claude-code-facts.md`). The audit of 2026-10-04 found a read gate that opened locations outside
its bases (03/F06) and a gate that followed a link out of the stage (03/F32), both telling the session what they found;
a stop hook that took a session's checkout for the main checkout (03/F30); guards that a working directory, a `~`, a
`..`, a wrapper or a second spelling went around (04/F1 to F7); and hooks that let a call through when they crashed
(a traceback is exit 1, which Claude Code treats as a non-blocking error, hooks.md:840).

## Decision Drivers
* A guard that cannot decide refuses; a helper that cannot decide gets out of the way; a hook that cannot block does
  what its event allows (hooks.md:852-892).
* The rules a hook applies are not the ones a session may be changing.
* Nothing a gate or a hook reads outside the stage comes back to the session.

## Considered Options
* Fail closed per event, the main checkout for rules, paths resolved and confined
* Leave each hook as it was and rely on the sandbox

## Decision Outcome
Chosen option: the first.
* The PreToolUse guards (guard-checkout, guard-bash, guard-inbox, validate-json) and config-audit exit 2 on any
  exception; permission-request answers no on any failure in a role session, reading `HARNESS_RUN_DIR` before its
  input; stop-gate lets the stop through on its own crash and logs it; compact-output and skill-audit let the call
  through unchanged.
* A hook takes rules, schemas, runs and the harness from the main checkout: `CLAUDE_PROJECT_DIR`, mapped to the main
  checkout when it is a checkout under `.claude/worktrees/`; where the session stands is the input's `cwd`, resolved
  and compared as a path.
* The guards read a command as the shell does (`.claude/hooks/shellwords.py`): simple commands, quotes, line
  continuations, and the wrappers `env`, `sudo`, `exec`, `bash -c` and the rest taken off, since Claude Code takes off
  only some before it matches a rule (permissions.md:237-245).
* A gate reads a file of a stage only when it is no link and lies inside the stage directory (`_common.stage_file`),
  the read gate opens no location outside its bases and no path the stage's type may not read, and the stop hook does
  not read a `result.json` that is a link. The stop hook counts its holds in `<run>/logs/stop-gate/`, where the session
  cannot write, and lets a session stop on an open escalation of its stage only.

### Consequences
* Good, because a guard's hole is no longer a matter of spelling, and a crash refuses instead of allowing.
* Bad, because a hook probe of a branch runs from a checkout outside `.claude/worktrees/`: inside one, the hook takes
  the main checkout's rules, as it should.

### Confirmation
`packages/harness/tests/test_guards.py`, `test_hooks.py`, `test_layout.py`, `test_gates.py`; the probes of areas 03
and 04 of the audit print no defect.

## More Information
Amended by [ADR-0025](0025-a-guard-refuses-the-plain-spellings-and-the-boundary-holds-the-rest.md): a guard refuses the plain spellings of a command; what a command builds at run time is held by the sandbox and the write gate, and the gates open no path the project's settings close.
