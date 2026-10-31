---
status: accepted
date: 2026-09-25
decision-makers: platform team
consulted: harness maintainers
informed: all package owners
---

# Run state lives in JSON files on disk; transcripts are not state

## Context and Problem Statement
A run must continue after a session hits a limit, crashes or is restarted, and a new manager session must be able to take over. Transcripts are in an internal format that changes between versions and are deleted after `cleanupPeriodDays`.

## Decision Drivers
* Stable, schema-validated state
* Takeover by any session or human without the previous context

## Considered Options
* Transcripts as the source of truth
* The manager's own context as the source of truth
* JSON files in a run directory beside the repository (`../<repo>-runs/<run-id>/`) validated against `schemas/`

## Decision Outcome
Chosen option: JSON files, because they are validated, diffable and independent of Claude Code's internals; `claude agents --json` is the only runtime interface read. The directory sits outside the checkout because a background session works in its own worktree and may not write into the shared checkout, while a write outside the working directory is allowed.

### Consequences
* Good, because every transition is on disk before and after the action.
* Bad, because the role session must checkpoint explicitly (enforced by the Stop hook).

### Confirmation
`validate-json.py` hook (an invalid Write is denied before it happens, an invalid Edit is reported after); `stop-gate.py` (schema plus a final status); `harness poll` re-derives status from `claude agents --json`; `config_fingerprint` in `state.json` is checked by every launch and resume.

## More Information
`~/.claude/jobs/<id>/state.json` is documented as not a stable interface and is never read.
Amended by [ADR-0021](0021-one-writer-at-a-time-for-run-and-loop-state.md): every writer of a state file holds its one lock and writes through a temporary file of its own.
