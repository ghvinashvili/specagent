---
status: accepted
date: 2026-10-09
decision-makers: the human, who approved the brief and the plan of run 20261009-022929-fix-w1-revise (the revise of wave 1)
consulted: harness maintainers; a critic that attacked the plan and its trial before the work
informed: all package owners
---

# A guard refuses the plain spellings of a command; the sandbox and the write gate hold the rest

## Context and Problem Statement
ADR-0020 has the guards (guard-bash, guard-checkout) read a command the way the shell does and refuse the holes 04/F1
to F7 whatever their spelling. Wave 1's critic and verifier found new spellings in every round: a `#` inside a word, a
variable, a `cd` option, a brace, `${PWD%/*/*/*}`, `CDPATH`, a function, a pipe into `sh`, `eval`, `xargs` (R1 to R5 of
run 20261009-022929-fix-w1-revise). A guard that reads a command's text cannot keep that promise: bash is a language.
Measured in a role session's sandbox on Claude Code 2.1.289 (the plan of that run): after EnterWorktree every read of
the main checkout, of the runs root and of the inbox found nothing; every whole-tree `git add` or `git commit` that ran
died on the sandbox's mask of `.env.example`; every shell write of a run file was refused; the other spellings were
refused by Claude Code's permission prompt, its worktree isolation or a guard. Where does the boundary of a role
session stand, and what do the documents promise?

## Decision Drivers
* A protection stands where nothing can go around it: the sandbox, the file's permissions, the gate at merge.
* A document, a docstring and a changelog line say only what a test or a measurement shows.

## Considered Options
* Read more of the shell in the guards
* Hold the boundary by construction, and keep the guards as early refusals of the plain spellings

## Decision Outcome
Chosen option: the second, because the first was tried for a whole wave and lost a round to every new spelling.
* What a role session's shell may read and write is its sandbox's: the read block (`blockReadsOutsideWorkingDirectories`)
  with working directories that are never the repository, the run root or the inbox, and the `denyWrite` entries and
  `Edit(...)` deny rules of `access.write_limits` (ADR-0018), held by `packages/harness/tests/test_boundary_settings.py`.
* What a commit may contain is judged by the write gate on its effect: `_common.closed_to` refuses a branch that changes
  a path its author could not read, by its type's row or by the project's settings (`access.unreadable`,
  `access.settings_closed`), whatever command made it.
* guard-bash and guard-checkout refuse the plain spellings: the command reader (`.claude/hooks/shellwords.py`) takes `#`
  as part of a word, and guard-checkout resolves the folder a Glob pattern names. Their docstrings say so.
* The read gate, its probe check and the locator check open no path the project's settings close and nothing outside
  the stage and the repository, and answer the same whether such a path exists or not (amends ADR-0020 on the gates).
* Every input copy is written read-only and indexed with its sha256 in `<run>/_access/`, the change patch of a unit that
  reviews code work included, on its launch, a recheck and a resume (ADR-0018, unchanged).

### Consequences
* Good, because each case of R1 to R5 but the two limits below is held by a layer no spelling goes around, with a test
  or a measurement.
* Bad, because the sandbox's hold is Claude Code's behaviour, measured on 2.1.289: the live checks of the plan repeat the
  measurement after integration.
* Bad, because two limits stay, which the human accepted with the plan of run 20261009-022929-fix-w1-revise, in its
  words:
  1. "Before a session has entered its checkout (a reviewer whose checkout the launcher prepared, or any session right
     after a resume), its sandbox still reads the main checkout: a spelling the guards do not read reaches the base
     there. Measured on Claude Code 2.1.289: the session's sandbox lists the main checkout among the readable paths
     until EnterWorktree, and hides it after."
  2. "Until the manager applies the `.claude/settings.json` change of this plan, the manager's own shell reads
     `<runs root>/_inbox/` through a spelling guard-bash does not read."

### Confirmation
`packages/harness/tests/test_plain_spellings.py`, `test_boundary_settings.py`, `test_closed_paths.py`,
`test_held_repairs.py`, `test_input_copies.py` and `test_documents.py`; the table of the cases of R1 to R5 in the plan of
run 20261009-022929-fix-w1-revise, and its live checks.

## More Information
Amends [ADR-0020](0020-hooks-and-gates-fail-closed-and-open-nothing-outside-a-stage.md) on what the guards read and on
what the gates open; keeps [ADR-0018](0018-a-role-session-writes-its-stage-and-its-own-checkout-only.md) as it is.
