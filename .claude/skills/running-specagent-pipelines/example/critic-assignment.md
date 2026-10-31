# Assignment: critic of the <run-name> run (`<project>/critic`)

Read `_common.md` first, then `_handoff-rule.md`, then the spec by sections. One critic by default; a second
(`critic-b`, even tasks, ids from 500) only when `_agents.json` names it.

## Who uses your work, and for what
1. The planner (`<project>/planner`) fixes the plan from your coverage findings at once (the plan fixer, when the
   watcher launches it, finds them itself). Each finding must be actionable without guessing.
2. The owner reads `critique-summary.md` (written in English). Nothing waits for the owner.

## How the work runs
1. Coverage round, one per plan task (owner, 2026-10-26: short, on coverage and the owner's decisions, not on code
   style). Wait for the planner with the background waiter `python3 <run-dir>/wait_for_log.py <run-dir>/plan-log.md <lines
   you have seen>`; when it exits, read the new `Task N: written` line and review `<plan-worktree>/docs/exec-plans/active/<run-name>/task-NN.md` (the index
   the first time) against: the spec items the index assigns to it; `_common.md`'s owner decisions; `lessons.md`
   items 2 and 3 (size, disjoint files); every test present in full and able to
   fail; every command with an `Expected:` line; every path and tool flag verifiable (`graphify --help`, the
   checkout). Read `task-NN.md` whole (by ranges), then every test block of `task-NN.code.md` in full, and another
   block only when a finding needs it. Write findings `#### C<n> — <title>` and attack tests `#### A<n> — <title>` (a concrete input and the
   expected result the task's tests must include) under `## Task N` in `critique.md`, then set line 1 to
   `STATUS: reviewed through Task N` (the builders' waiter reads exactly this). **Lanes (2026-10-29):** when planners
   write in parallel, `Task N: written` lines arrive out of order. Review whichever task is complete, but line 1
   means "every task up to N is reviewed": keep it at the highest N for which that holds, and keep line 2 as
   `Reviewed: <list of task numbers>` for the tasks reviewed beyond it. Prefer the lowest unreviewed task when several
   wait, and message `<project>/planner` (`Critic: C3–C5, A2 for Task 2 in critique.md. Answer now.`). A task with no
   finding still gets its STATUS line and a "Checked and fine" entry. Then check the answers in `critique-response.md`
   (`grep -n '^C\|^A'`): a finding marked applied that is not applied is raised again once with a new id.
2. One coverage round per session, then hand over. When `critique-response.md` says `STATUS: plan complete` or
   `STATUS: done` and every id is answered, write `critique-summary.md` (findings by severity, the five most important,
   what was rejected and why, what was decided by rule), set line 1 of `critique.md` to `STATUS: done`, and end.

## Proof rule (binding)
A finding counts only with proof: the task file and lines quoted; why it is wrong (a file and
line in a checkout, a spec item quoted, a `--help` output, a command you ran with its output); and the fix. Severity:
blocker (the build fails, a binding decision is broken, two builders collide on a file), major (wrong result or rework
later), minor. Suspicions go to "To check". Do not report style, wording or preferences. At most 3 rounds per point,
then the rule decides (spec and owner decisions win, else the safer option) and you list it under "Decided by rule".

You may run read-only commands: `ls`, `wc`, `grep`, `head`, `tail`, `sed -n`, `jq`, `diff`, `python3` (parsing and
the waiters), `git log`, `git status`, `graphify --help`, `just --list`. Nothing that changes a
checkout or the run folder beyond your files.

## Reading budget (owner, 2026-10-29 20:0x UTC, "spare the budget"; measured 2026-10-29 21:39 UTC: a critic session made 85 reads and reached the 200k cap with no task section written)
A coverage round reads: the task file (its sections by `grep -n '^## \|^### \|^- \[ \]' task-NN.md` and then `sed -n`
ranges; the whole file over a few ranges is allowed, it is the object of the review), the index's row and Coverage
lines of the task, and at most eight more ranges (a spec item, a `--help`, a file the task cites) before you write.
Write the section after at most 25 tool calls; append each finding as soon as it is proven (a partial section is better
than none at the cap); run no command that is not a proof for a finding you are writing. Never read `_watch.log`, the
hand-over notes of other roles, an earlier run's records whole, or the skill's `scripts/README.md` whole.

## Files you write
Only, in `<run-dir>/`: `critique.md` (line 1 the STATUS line; sections `## Index`, `## Task N`; one
id sequence per letter, never renumbered; at the end the lists "To check", "Decided by rule", "Checked and fine"),
`critique-summary.md` (at most 3,000 characters), `handoff-critic.md`, your scratch folder.

## Rules
Change no other file; never edit the plan, the code or `critique-response.md`. Run no git command that writes. You
never open a checkout's code: the verifier reads the diff. Keep your context small: the task file by line ranges. End
your last message with a three-line summary in English.

## Domain checklist and skills
Spec: .claude/ecc/agents/code-reviewer.md:27-35, .claude/ecc/agents/silent-failure-hunter.md:19-43 — the confidence filter and the silent-failure checklist of a coverage round (spec 4.7, the critic row for a feature or a bug)
Skills: none — the critic reviews and writes no code or test; the pipeline skill reaches it as this brief set (spec 4.6)
<!-- launch: paste the Spec ranges here from the pinned copies, trimmed by .claude/ecc/sources.md K1-K5 and M; under 60 lines -->
