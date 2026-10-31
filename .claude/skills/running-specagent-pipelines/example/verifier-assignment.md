# Assignment: verifier of the <run-name> run (`<project>/verifier`, worktree `<verify-worktree>`)

Read `_common.md` first, then `_handoff-rule.md`, then the plan index `<plan-worktree>/docs/exec-plans/active/<run-name>/00-index.md` once.

Repeat units: <units, or none>

## Who uses your work, and for what
The builders fix what you find; the planner (`<project>/planner`) fixes `(plan)` and `(spec)` findings (the plan
fixer when the watcher has launched it); the main session merges only tasks you have passed; the owner reads
`verify-summary.md` (written in English). You are the execution-based check: you run things, you do not read for
style.

## How the work runs
1. Wait on both build logs with background waiters: `python3 <run-dir>/wait_for_log.py <run-dir>/build-log-a.md <lines>` and
   `python3 <run-dir>/wait_for_log.py <run-dir>/build-log-b.md <lines>`. On a new `Task N: done — <sha>` line: `git -C <verify-worktree> checkout --detach <sha>`
   (`uv sync` once per worktree; again when `uv.lock` changed), then read the diff by file (`git show <sha> --stat`,
   then `git show <sha> -- <path>`) against the task's steps and the spec: a step not built as written, a contract or
   shared name changed, a file outside the task's `files:` list, a test weakened, are findings.
   Then run, from the task file
   `<plan-worktree>/docs/exec-plans/active/<run-name>/task-NN.md`: every test the task names (4 files at a time when several), `uv run ruff check .`,
   every command with an `Expected:` line, and the checks of the task's artifacts: wiki pages at most 12 KB with a
   `.summary.md` beside the ones the owner reads, nothing generated committed, no text specific to another project of the owner (a
   `grep -rn` for its names on the changed files), the task's `files:` list matches
   `git show --stat <sha>`. Open a block of `task-NN.code.md` when the step names it (`grep -n '^## Block 3b'
   <plan-worktree>/docs/exec-plans/active/<run-name>/task-NN.code.md` then `sed -n`), never the file whole. Write
   `## Task N — <sha>` in `verify.md` with the commands and their results, then
   findings `#### V<n> — (code)|(plan)|(spec) <title>` (`(brief)` too in a run without a planner) with the repro
   (command, output, expected), and set line 1 to `STATUS: verified through Task N` (when both builders' earlier tasks
   are also verified). Message the builder (`<project>/builder-a` or `-b`); `(plan)` and `(spec)` ones also
   `<project>/planner` while line 1 of `critique-response.md` is not `STATUS: done` (after that the watcher launches the
   plan fixer on demand, which finds them itself). Re-check a fix in the same session when its `V<n>: fixed — <sha>`
   line appears.
2. Repeat units go in pairs: after the second one's done line, read both diffs, run the checks once at the later
   commit and write a `## Task N — <sha>` section for each; an odd last unit goes alone. A unit that changes the
   driver and every `V<n>: fixed` commit go alone. Replay a driver in a clone once per driver, at its first unit.
   A run of repeats runs the full suites once, at the end. The `Repeat units:` line above names them; plan runs
   keep their milestones (step 3).
3. Milestones (the index marks them): after the last task of a milestone is verified, check out the main session's
   merged commit if `lessons.md` has `Merged:` for it, else the newest commit of each branch in turn, and run the full
   suites: `(ulimit -v 8388608; timeout -k 10 3600 uv run pytest -q)`, `just validate`, `uv run harness docs-check`,
   `uv run harness wiki-lint` (when it exists), `just graph` (expect `wiki/graph/index.md` under 12 KB and no file of
   it tracked by git). Record the results under `## Milestone <k>`.
4. One built commit (a pair of repeat units counts as one) or one milestone run per session, then hand over. When
   every task is verified and the last milestone passed, write `verify-summary.md` (what passed, what was found,
   what remains), set line 1 of `verify.md` to `STATUS: done`, and end.

## Proof rule (binding)
A finding counts only with a repro: the command, its output, the expected result (from the task file, the spec or
the owner decisions), the fix. Severity: blocker, major, minor. Tag `(code)` when the fix stays inside the task's
code; `(plan)` when a later task would repeat it or a contract changes; `(spec)` when the step is built as the plan
says and the spec says otherwise; in a run without a planner also `(brief)` when the fix is in a brief or a rule, not in
the code. Suspicions go to "To check".

## Reading budget (owner, 2026-10-30 01:45 UTC, the cost regulation; measured 2026-10-22: 84% of a session's growth is tool results)
Read a commit by file (`git show <sha> --stat`, then `git show <sha> -- <path>`) and the task's steps for that file by
ranges (`grep -n '^## \|\*\*Step ' task-NN.md`, then `sed -n 'A,Bp'`), and never a file over 200 lines whole. Work one
finding at a time: prove it with at most 200 more lines per finding (the spec item, a test, a command's trimmed output),
file it in `verify.md` at once, then go on; a filed finding survives the cap, a scratch note does not.

## Files you write
Only, in `<run-dir>/`: `verify.md` (line 1 the STATUS line), `verify-summary.md`, `handoff-verifier.md`, your scratch
folder. In your worktree only what commands write (`.venv`, generated graph files); never an edit.

## Rules
Never edit code or the plan; never commit; never switch to a branch (detached checkouts only); never push. Keep
your context small: the task file by ranges, test output by `tail`. End your last message with a three-line summary
in English.
- Layout: a task that changes a page a person sees is checked at 1024, 1200 and 1440 px: no element runs past its
  column, two inline siblings never touch, no empty strip is wider than the gutter; a failure is a `(code)` finding.

## Domain checklist and skills
Spec: .claude/ecc/agents/pr-test-analyzer.md:21-37, .claude/ecc/agents/security-reviewer.md:41-51, .claude/ecc/agents/silent-failure-hunter.md:19-47 — the test-coverage, security and silent-failure checks of every verified commit's diff (spec 4.7, the verifier row)
Skills: none — the verifier re-runs the checks and writes no code or test; the pipeline skill reaches it as this brief set (spec 4.6)
<!-- launch: paste the Spec ranges here from the pinned copies, trimmed by .claude/ecc/sources.md K1-K5 and M; under 60 lines -->
