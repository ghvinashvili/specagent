# pipeline-fold: summary for the owner

The owner cancelled the measurement on 2026-10-30: the fold stands on `main` unmeasured, and the yes asked for at the
end of this page is no longer needed.

What gets built: fewer hand-overs in the SpecAgent pipeline, measured. A run score script (one line per run: findings,
sessions, cap hand-overs, idle restarts, cost, requests, cache ratio); a watcher that starts a fresh session only when
the role's own check says work waits; the plan file split into steps and blocks, with the texts' prose moved to the
builder behind a facts list and a test; the planner answering its own findings after each part, the plan fixer
launched only when the queue passes 6 ids or 45 minutes; the critic on the plan only, the verifier reading each
commit's diff; one critic by default.

Order: seven tasks, each with its tests first. Task 1 (the score) by the main session; Tasks 2-5 and 7 by two builder
lanes in a pipeline run with a plan fixer answering the findings (the owner's yes of 2026-10-30 05:20Z, before D10),
into `main` after M2 and the judge (owner, 2026-10-30 07:38 UTC); Task 6, the measurement run, after D10 (the spec's
"After D9 and D10"). The score first (its baseline on the manager-build run), then the watcher rule, the plan split,
the planner and fixer, the critic and verifier, the manager-build judge's conditions (Task 7), then the measurement.

How it is checked: each task's own tests and `ruff` at its end; the skill's suite, the harness suite, docs-check,
plan-lint and validate at M1 and M2; the measurement run rebuilds Task 10 of the manager-build run with the folded pipeline on a scratch branch and compares
its score with the original; the fold is kept only when cost fell and quality held. The plain one-agent session on the
same task is cancelled (owner, 2026-11-01): the template offers no one-agent mode.

What you do: say yes to the measurement run (five sessions), once.
