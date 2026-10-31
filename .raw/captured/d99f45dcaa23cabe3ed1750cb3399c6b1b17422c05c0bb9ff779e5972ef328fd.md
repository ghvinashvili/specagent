---
title: The collector deletes on the owner's yes for three runs, then by a standing rule
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: a deletion cannot be undone, so the owner approves the exact list until three runs have shown that the list is right
would_change_if: a run in which the collector's list held something the owner would have kept, which brings the yes back
decision_status: decided
scope: global
tags:
  - decision
---
# The collector deletes on the owner's yes for three runs, then by a standing rule

`collect_run.py` lists a finished run's leftovers (its worktrees and branches, `scratch/`, the sessions' job outputs
and result copies) in a dry run that prints the list's digest. For the first three runs it deletes only on the owner's
yes for that exact list, `--apply --yes <digest>`; once its history file holds three runs applied with a yes,
`--apply` alone deletes by the standing rule, and the owner reads `collected.md` in the run folder afterwards. This is
the owner's answer to question 4 of the manager spec, "4 (a) for three runs, then (b)" (2026-10-29; spec 5.9.4).

## Record and source
- [The collector](../../.claude/skills/running-specagent-pipelines/scripts/docs/collect_run.md)
- [A run is collected only after its record is checked as saved](collector-save-check.md)
