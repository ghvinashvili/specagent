# Lessons: read "Read first" once at your start (planner and builders; the critic and verifier grep it on need)

The lessons loop has three steps: a finding is recorded where it was made; a cause shared by two or more findings
becomes a one-line rule under "Lessons from this run"; a rule broken a second time becomes a check in code (a hook, a
script the watcher or the records monitor runs, a `check_formats.py` or `harness validate` rule, a test), so that
holding it no longer depends on a session reading it.

## Read first (main session, 2026-10-28)
1. Reading rule. `lessons.md` once per session, this section only; the record files (`critique.md`,
   `critique-response.md`, `build-log-a.md`, `build-log-b.md`, `verify.md`, `plan-log.md`, the `handoff-*.md` notes)
   never whole: `head -1` for the STATUS line, `grep -n '^#### '` or `grep -n '^Task '` for ids and sections,
   `sed -n 'A,Bp'` for the one section you need, `tail -n 40` for the newest entries. The plan: the index once, then
   only the task file you work on. The spec: by section (`grep -n '^## \|^### \|^[A-B][0-9]*\. ' <spec>` then ranges).
2. Task size: at most 1,500 lines per task file, one checkable result each; the task count is fixed when the index is
   written; a task that grows gets a Deferred line, never a new task number.
3. Two builders, disjoint files. The index gives every task `builder: a|b`, `depends_on:` and `files:`; two tasks of
   different builders never list the same file. Shared files that both need are edited by one builder and the other
   depends on that task. The merge is the main session's: it merges both branches into `feat/<run-name>` after the
   verifier passes the tasks and writes `Merged: a+b at <sha>` here; the last task starts only after that line.
4. Shell: no top-level `cd`; paths literal or `"${W:?}/x"`; long jobs inside `(ulimit -v 8388608; …)`; `timeout -k 10`.
   Each worktree needs its own `uv sync` once (the `.venv` is per worktree).
5. The vault `<vault>` is read-only and read on need: open `INDEX.md` only when a step needs an owner rule, follow
   one link, read by ranges with `python3 <vault>/ops/outline.py <file>`. Where a vault page and your brief differ,
   the brief wins; log the difference in your log file.
6. Scratch: `<run-dir>/scratch/<role>/` with Write and Edit. Never a heredoc or `cp` under /tmp.
7. Two plan roles: `<project>/planner` writes new tasks only; `<project>/plan-fixer` answers every C, A, B, `(plan)` R
   and V id and edits unbuilt task files. Messages about findings go to the fixer (and to the builder for `(code)`).
   The code of a built task is the truth: its plan text is not rewritten; later tasks are.
8. Copy tasks stay thin (owner, 2026-10-29: "it is already written in an earlier project; it is moved, not
   rewritten"). A task whose work is moving existing files is a table source → destination, the rename and
   generalisation rules (project paths → variables, project names out), the one test or command that proves the copy
   works, and the wiki line; never a description of the content and never a rewrite. The planner's time goes to the
   genuinely new tasks.
9. Planner lanes (optional; owner, 2026-10-29): planners write in parallel from the fixed index. The claim line
   `Task N: started by <role>` in `plan-log.md` is the lock: a claimed task is skipped. Contracts between lanes come
   from the index's cells and the copied sources; a name a not-yet-written task must honour goes under "Contracts" in
   the task file and to the plan fixer by message. The critic's line 1 stays monotonic ("through N" = all tasks <= N
   reviewed), line 2 `Reviewed:` lists the rest; builders wait on line 1 as before. The plan fixer answers every lane.
   A claim line is never voided by a later lane list. The lane list says who may claim what is unclaimed; an existing
   `started by` line wins, whoever wrote it and whenever the lanes changed. A planner whose task is claimed sets
   `STATUS: done` and may hand its verified facts to the claim holder in `scratch/<role>/`.

## Known error classes (from earlier runs; check each task against them)
- A path or line cited in a plan or finding that does not exist at the base commit.
- A command in a plan without an `Expected:` line, or an `Expected:` that the command cannot produce.
- A test that cannot fail (asserts a constant) or always fails (fixture missing).
- A step that edits a file another builder's task also edits.
- A dependency added without `uv.lock` changing, or a tool named without its installed version checked.
- A control file (`_*`) edited by an agent; a plan task renumbered or a heading written ahead.
- A hand-over note that points at files instead of carrying the facts.
- A `.summary.md` summary missing for a page the owner reads; a wiki page over 12 KB; a flat index over 12 KB.
- A generated artifact committed (`graphify-out/`, `wiki/graph/`, `.venv`, `evals/results/`).
- A role settings file that leaves `~/.claude/.credentials.json` readable (J6 of the manager-build judge; the
  pre-flight's `blind` check refuses it).

## Lessons from this run
(planner and builders add one-line rules here, with the finding ids)
