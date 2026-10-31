---
status: accepted
date: 2026-10-04
decision-makers: the human, who chose the list in the brief of run 20261004-121127-fix-w1-leaks
consulted: harness maintainers
informed: all package owners
---

# A role session runs only the harness commands listed for it

## Context and Problem Statement
ADR-0010 made every command that changes a run, and `abort`, refuse a session with `HARNESS_ROLE` set. `poll` and
`watch` were declared reads, though each gates units, rewrites `state.json` and stops sessions, so a role session's
`harness poll` steered its run (02/F23 of the audit of 2026-10-04). A declaration per command is a list of what to
refuse, and every command added later is allowed until somebody remembers it.

## Decision Drivers
* A role session does not steer its run, whatever a command is declared to do to a run.
* A command added later refuses a role session until it is listed.

## Considered Options
* A list of the commands a role session may run (`cli.ROLE_COMMANDS`)
* Declare poll and watch as changing commands

## Decision Outcome
Chosen option: the list. It holds what a role session or one of its hooks runs today, each with where it is told to:
`gate` (only `--preview`, the stop hook), `validate`, `docs-check`, `map`, `version-check`, `audit`, `loop` (only
`validate`), `wiki-lint`, `skill-usage` and `steps`. With `HARNESS_ROLE` set every other command answers
`role_session` and changes nothing. `RUN_COMMANDS` keeps "reads" and "changes" for the aborted-run rule of ADR-0010.

### Consequences
* Good, because poll, watch and any command added later refuse a role session.
* Bad, because a role that needs another command waits for a change of the list.

### Confirmation
`packages/harness/tests/test_abort.py`, `test_a_role_session_runs_only_the_commands_listed_for_it`; the probe
`role_poll.py` prints `behaves as promised (exit 0)`.

## More Information
Amends `docs/decisions/0010-a-run-ends-with-integrate-or-abort.md`: the sentence "with `HARNESS_ROLE` set, every
changing command and `abort` refuse (`role_session`), save the gate preview its stop hook asks for" becomes the list.
