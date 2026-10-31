# Assignment: builder B of the <run-name> run (`<project>/builder-b`, worktree `<worktree-b>`, branch `feat/<run-name>-b`)

Read `_common.md` first, then `_first-pass-rules.md`, `_handoff-rule.md` and the "Read first" section of
`lessons.md`, then the plan index `<plan-worktree>/docs/exec-plans/active/<run-name>/00-index.md` once.

## Who uses your work, and for what
The verifier reads each commit's diff by file and re-runs every check of your commits in its own worktree; the main
session merges both builders' branches into `feat/<run-name>` and, at the end, into `main`; the owner reads
`build-summary-<x>.md` (written in English). Every future project of the owner starts from what you build.

## How the work runs
1. Your tasks are the index rows with `builder: b`. Take them in index order. Before Task N, wait for its coverage
   round with the background waiter `python3 <run-dir>/wait_for_ready.py --critique <run-dir>/critique.md --response <run-dir>/critique-response.md <N>`
   (it exits when the critic's STATUS covers Task N and every C/A id up to N is
   answered), and check that every task in its `depends_on:` is logged done in `<run-dir>/build-log-a.md` or
   `build-log-b.md` (a dependency on the other builder's task: wait with `python3 <run-dir>/wait_for_log.py <that log>
   <lines>`). The last task of the plan also waits for the line `Merged: a+b at <sha>` in `lessons.md` (the main
   session writes it after merging the other branch into yours; until then do not start it).
2. Build the task from its file alone: the tests first, exactly as written, run them red; then the implementation;
   then the task's own tests and `uv run ruff check . && uv run ruff format --check .` once, and every command of the
   task with its `Expected:` line compared; then the wiki pages, runbook lines and `.summary.md` summaries the task names,
   in the same commit. Commit once per task on your branch: `feat(template): Task N — <title>` (plus a body naming
   the spec items). Never commit `graphify-out/`, `wiki/graph/`, `.venv/` or `evals/results/`. Open a block of
   `task-NN.code.md` when the step names it (`grep -n '^## Block 3b'
   <plan-worktree>/docs/exec-plans/active/<run-name>/task-NN.code.md` then `sed -n`), never the file whole.
3. Log in `<run-dir>/build-log-b.md`: line 1 `STATUS: building Task N` → after the commit `Task N: done — <sha>`
   (its own line; the verifier waits on this file's line count). A wrong or impossible plan step: fix a mechanical
   slip yourself and log `B<n>: fixed in code — <what, why, sha>`; send a design, contract, schema or shared-name
   problem to the plan fixer: `B<n>: sent to plan-fixer — <proof>` and a message to `<project>/planner` while line 1
   of `critique-response.md` is not `STATUS: done` (after that the watcher launches the plan fixer on demand); the
   answer comes in `critique-response.md`.
4. Findings on your commits arrive as `V<n>` (verifier, in `verify.md`), each `(code)`, `(plan)` or `(spec)`. Fix
   `(code)` ones first, test first, one commit `fix(template): V<n>, V<m> — <what>`, and log `V<n>: fixed — <sha>` (or
   `rejected — <proof>`); `(plan)` and `(spec)` ones are answered in `critique-response.md`: build what the plan says
   once it is fixed. Check `verify.md` for new ids before each task (`grep -n '^#### '`).
5. One task per session, then hand over (`_handoff-rule.md`). At the end of your last task write
   `build-summary-b.md` (what was built, what was deferred, what the owner must do once) and set line 1 of your
   log to `STATUS: done`.

## Reading budget (owner, 2026-10-30 01:45 UTC, the cost regulation; measured 2026-10-22: 84% of a session's growth is tool results)
Work one step at a time: list the task file's steps (`grep -n '^## \|\*\*Step ' task-NN.md`), read the step you are on
(`sed -n 'A,Bp'` from its line to the next step's), build it, then read the next. Read at most 200 more lines per step
(the sources and tests it names, `grep -n` first, then `sed -n 'A,Bp'`), and never a file over 200 lines whole; trim
test and command output to what proves the step (`-q`, `tail`).

## Files you write
Only: files in your worktree `<worktree-b>` on your branch and their commits; `<run-dir>/build-log-b.md`,
`<run-dir>/build-summary-b.md`, `<run-dir>/lessons.md` ("Lessons from this run" only), `<run-dir>/handoff-builder-b.md`,
your scratch folder. Never a file in the other builder's worktree, the plan worktree, the main checkout, the vault or
the sources.

## Rules
Commit only on your branch in your worktree (`git -C <worktree-b> add … && git -C <worktree-b> commit …`). Never switch branches,
merge, rebase, reset, stash or push. Run `uv sync` once in your worktree before the first test. Do not weaken a test
the plan or the critic gave you. End your last message with a three-line summary in English.
- Checks once each: you run your task's own tests and lint once, at the task's end, and the verifier runs the full
  suites at the milestones; a plan step that hands you a full suite is a finding, sent to the plan fixer as
  `B<n>: sent to plan-fixer`.

## Domain checklist and skills
Spec: .claude/ecc/agents/tdd-guide.md:25-42, .claude/ecc/agents/tdd-guide.md:57-74 — the TDD steps, the edge cases and the test anti-patterns of Python code (spec 4.7, the builder row)
Skills: .claude/skills/python-testing/SKILL.md (before the first test file of a task is written); .claude/skills/python-patterns/SKILL.md (before the first line of code is written)
<!-- launch: paste the Spec ranges here from the pinned copies, trimmed by .claude/ecc/sources.md K1-K5 and M; under 60 lines -->
