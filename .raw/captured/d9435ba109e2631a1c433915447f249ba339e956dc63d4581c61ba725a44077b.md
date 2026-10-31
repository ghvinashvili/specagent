---
title: "The critic reviews the plan only; the verifier reads the code"
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-30
audience: [all]
decided: 2026-10-30
by: owner
why: every built commit of the manager-build run was read by two sessions, the critic (8 R findings over Tasks 1-10) and the verifier (7 V findings, two of which the critic had missed), and each diff review was a session of its own, with a start-up of 32-33k tokens and the re-reading of the same files; the verifier already holds the commit in a clean worktree, so one reader per commit keeps the independent eyes and drops the second read
would_change_if: the measurement run (Task 6 of the pipeline-fold run) loses quality against the manager-build run, with a new V the original run did not have or a rebuild; this pair is then unfolded and measured again
decision_status: decided
scope: global
tags:
  - decision
---

# The critic reviews the plan only; the verifier reads the code

The SpecAgent pipeline gives each built commit one reader. The critic keeps its coverage round: one per plan task,
before the build, filed as C findings and A attack tests in `critique.md`. It loses the diff review and never opens a
checkout's code. The verifier, which already checks the commit out in its own clean worktree, takes over what the diff
review did: before it re-runs the checks, it reads the diff by file (`git show <sha> --stat`, then
`git show <sha> -- <path>`) against the task's steps and the spec. A step not built as written, a changed contract or
shared name, a file outside the task's `files:` list and a weakened test are findings.

Every finding on a commit is a V id with one of three causes: `(code)` when the fix stays inside the task's code,
`(plan)` when a later task would repeat the mistake or a contract changes, and `(spec)` when the step is built as the
plan says and the spec says otherwise. `(plan)` and `(spec)` findings also go to the planner while line 1 of
`critique-response.md` is not `STATUS: done`; after that the watcher launches the plan fixer on demand, which collects
the open ids itself (`open_ids.py --cause plan` drops only the `(code)` ones). R ids are retired for new runs: no brief
files, waits for or answers one. The scripts still read them, so old runs parse and report (`findings_report.py` keeps
its R column).

One critic by default: its work halves, and the second critic of the manager-build run was added for the diff
reviews. A second one (`critic-b`, even tasks, ids from 500) runs only when `_agents.json` names it, for a run whose
planner lanes outpace one critic. The planner's last wait reads line 1 of `critique.md`, which the critic sets in
place: `wait_for_log.py --first` exits on that line as well as on a new one.

## Record and source
- [Pipeline fold, Decided 3](../../docs/design-docs/pipeline-fold.md)
- [The critic's brief](../../.claude/skills/running-specagent-pipelines/example/critic-assignment.md)
- [The verifier's brief](../../.claude/skills/running-specagent-pipelines/example/verifier-assignment.md)
- Task 5 of the pipeline-fold run
