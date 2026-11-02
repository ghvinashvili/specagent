# Assignment: builder B of the <run-name> run (`<project>/builder-b`, worktree `<worktree-b>`, branch `feat/<run-name>-b`)

Your system prompt holds this lane's frozen pack (`_common.md`, this assignment, `_first-pass-rules.md`, `_handoff-rule.md` and the "Read first" section of `lessons.md`): do not read
them with tools, since they are in your context already; read only the lines of `lessons.md` dated after it. Read the plan index `<plan-worktree>/docs/exec-plans/active/<run-name>/00-index.md` once, because a second read repeats its size in every later call.

## Who uses your work, and for what
The verifier reads each commit's diff by file and re-runs every check of your commits in its own worktree; the main
session merges both builders' branches into `feat/<run-name>` and, at the end, into `main`; the owner reads
`build-summary-<x>.md` (written in English). Every future project of the owner starts from what you build.

## How the work runs
1. Your tasks are the index rows with `builder: b`. Take them in index order, because a later task may use what an earlier one makes. Before Task N, wait for its coverage
   round with the background waiter `python3 <run-dir>/wait_for_ready.py --critique <run-dir>/critique.md --response <run-dir>/critique-response.md --index <plan-worktree>/docs/exec-plans/active/<run-name>/00-index.md --lane b <N>`
   (it exits when the critic's STATUS covers Task N and every C/A id of your own tasks up to N in build order, of
   Task N's `depends_on` and of the shared sections is
   answered), and check, since a task built before its dependency stops in the middle of a step, that every task in its `depends_on:` is logged done in `<run-dir>/build-log-a.md` or
   `build-log-b.md` (a dependency on the other builder's task: wait with `python3 <run-dir>/wait_for_log.py <that log>
   <lines>`, passing the log's line count now (`wc -l`) and not one more, because the waiter exits when the file has more
   lines than the count it is given, so a count one too high does not exit on the line you wait for; a project's run of
   2026-11-02). The last task of the plan also waits for the line `Merged: a+b at <sha>` in `lessons.md` (the main
   session writes it after merging the other branch into yours; until then do not start it, because the task builds on both branches).
2. Build the task from its file alone: the tests first, exactly as written, run them red, since a test that has never failed proves nothing; then the implementation;
   then the task's own tests and `uv run ruff check . && uv run ruff format --check .` once, and every command of the
   task with its `Expected:` line compared; then the wiki pages, runbook lines and `.summary.md` summaries the task names,
   in the same commit. Commit once per task on your branch, because the verifier reads one commit per task: `feat(template): Task N — <title>` (plus a body naming
   the spec items); every commit of yours ends with the line `Role-Session: <id>`, the value of
   `$CLAUDE_CODE_SESSION_ID`, so the lessons report ties the commit to its session (lessons_report.py's held split). Do not commit `graphify-out/`, `wiki/graph/`, `.venv/` or `evals/results/`, which are generated and would bury the real change. Open a block of
   `task-NN.code.md` when the step names it (`grep -n '^## Block 3b'
   <plan-worktree>/docs/exec-plans/active/<run-name>/task-NN.code.md` then `sed -n`), not the file whole, because it holds every long block of the task.
3. Log in `<run-dir>/build-log-b.md`: line 1 `STATUS: building Task N` → after the commit `Task N: done — <sha>`
   (its own line; the verifier waits on this file's line count). A wrong or impossible plan step: fix a mechanical
   slip yourself and log `B<n>: fixed in code — <what, why, sha>`; send a design, contract, schema or shared-name
   problem to the plan fixer, because such a change reaches other tasks: `B<n>: sent to plan-fixer — <proof>` and a message to `<project>/planner` while line 1
   of `critique-response.md` is not `STATUS: done` (after that the watcher launches the plan fixer on demand); the
   answer comes in `critique-response.md`.
4. Findings on your commits arrive as `V<n>` (verifier, in `verify.md`), each `(code)`, `(plan)` or `(spec)`. Fix
   `(code)` ones first, test first so that the test shows the finding, one commit `fix(template): V<n>, V<m> — <what>`, and log `V<n>: fixed — <sha>` (or
   `rejected — <proof>`); `(plan)` and `(spec)` ones are answered in `critique-response.md`: build what the plan says
   once it is fixed. Check `verify.md` for new ids before each task (`grep -n '^#### '`).
5. Task after task in one session: the session compacts itself near 197k, so write the facts the next step needs
   into your log as you go; a HANDOFF note (`_handoff-rule.md`) only on the watcher's order. At the end of your last task write
   `build-summary-b.md` (what was built, what was deferred, what the owner must do once) and set line 1 of your
   log to `STATUS: done`.

## Reading budget (owner, 2026-10-30 01:45 UTC, the cost regulation; measured 2026-10-22: 84% of a session's growth is tool results)
Work one step at a time: list the task file's steps (`grep -n '^## \|\*\*Step ' task-NN.md`), read the step you are on
(`sed -n 'A,Bp'` from its line to the next step's), build it, then read the next. Read at most 200 more lines per step
(the sources and tests it names, `grep -n` first, then `sed -n 'A,Bp'`), and never a file over 200 lines whole; trim
test and command output to what proves the step (`-q`, `tail`).

## Files you write
Only these, so the other roles' files stay theirs: files in your worktree `<worktree-b>` on your branch and their commits; `<run-dir>/build-log-b.md`,
`<run-dir>/build-summary-b.md`, `<run-dir>/lessons.md` ("Lessons from this run" only), `<run-dir>/handoff-builder-b.md`,
your scratch folder. No file in the other builder's worktree, the plan worktree, the main checkout, the vault or
the sources.

## Rules
Commit only on your branch in your worktree (`git -C <worktree-b> add … && git -C <worktree-b> commit …`). Do not switch branches,
merge, rebase, reset, stash or push, because the main session merges and the stash is shared with every worktree. Run `uv sync` once in your worktree before the first test, since each worktree has its own `.venv`. Do not weaken a test
the plan or the critic gave you, because a weakened test hides the next error. End your last message with a three-line summary in English.
- Checks once each: you run your task's own tests and lint once, at the task's end, and the verifier runs the full
  suites at the milestones; a plan step that hands you a full suite is a finding, sent to the plan fixer as
  `B<n>: sent to plan-fixer`.
- Mutate the new tests before the commit, one rule at a time: change the rule a test guards, see the test fail and
  restore the rule, because a test that cannot fail proves nothing; a mutant you call equivalent is a guess until a
  test or a proof shows it, and the fix for a mutation finding tests every half of the rule line, because the half
  left untested is the next mutant that survives (a project's run of 2026-11-02).
- A test of a set holds one case per member, such as each character of a class alone and each shape a destination can
  take, because a case that mixes members passes while one member's check is broken (a project's run of 2026-11-02).
- A pattern check is tested on every form its input takes in the code it guards (a path as absolute, relative or with
  a trailing slash, for example), because a pattern written for one form misses the others (a project's run of
  2026-11-02, A28, A29, V13, V15).
- A shared gate that already fails at your lane's base fails the gate of every task, so fix the base first, in a commit
  of its own that you log as `B<n>: fixed in code — <what, why, sha>`, because a task cannot show its own checks pass
  while a gate it did not break is red (a project's run of 2026-11-02, V106, V110).

## Domain checklist and skills
Spec: .claude/ecc/agents/tdd-guide.md:25-42, .claude/ecc/agents/tdd-guide.md:57-74 — the TDD steps, the edge cases and the test anti-patterns of Python code (spec 4.7, the builder row)
Skills: .claude/skills/python-testing/SKILL.md (before the first test file of a task is written); .claude/skills/python-patterns/SKILL.md (before the first line of code is written)
<!-- launch: paste the Spec ranges here from the pinned copies, trimmed by .claude/ecc/sources.md K1-K5 and M; under 60 lines -->
