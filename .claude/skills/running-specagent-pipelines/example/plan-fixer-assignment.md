# Assignment: plan fixer of the <run-name> run (`<project>/plan-fixer`)

Read `_common.md` first, then `_first-pass-rules.md`, `_handoff-rule.md` and the "Read first" section of
`lessons.md`, then the plan index `<plan-worktree>/docs/exec-plans/active/<run-name>/00-index.md` once.

## Why you are launched (owner, 2026-10-30)
The planner answers the open ids of its own tasks after each part it writes. The watcher launches you only when the
open ids of your parity reach `demand.queue` (6) or the oldest is `demand.wait_minutes` (45) old, in `_agents.json`,
and stops you when none is open.

## Lanes (owner, 2026-10-29 03:10 UTC, "add a plan fixer"; judge J3 of the pipeline-fold run, 2026-10-30)
Two plan fixers may answer in parallel (optional), split by task parity, the split the watcher's queue uses (`demand.parity` in `_agents.json`: `odd` owns the ids filed under Tasks 1, 3, 5… in `critique.md` and `verify.md`, `even` those under Tasks 2, 4, 6…). The fixer of the odd tasks also owns the shared ids: those under `## Index` or any section whose heading is not a task's, and every `B<n>: sent to plan-fixer` line of the build logs. The fixer of the even tasks is `<project>/plan-fixer-b` (`status` `fixer-b-log.md`, `demand.shared` `false`, a `fresh.plan-fixer-b` text, its note `handoff-plan-fixer-b.md`): it collects with `--parity even --no-shared`, never answers a shared id or one of the odd tasks, and ends on `STATUS: done` when only such ids are open. If an id of the other parity is unanswered for an hour, message the other fixer, do not take it. Shared files: append your answer lines to `critique-response.md` and your lesson lines to `lessons.md` with Bash (`printf '%s\n' "C<n>: applied — …" >> <file>`), never with Edit or Write, so two appends cannot overwrite each other. `00-index.md`: you may edit any proven cell; the other fixer edits only the rows of its own tasks; both re-read the file right before an edit and commit it alone with a pathspec at once; on `index.lock` wait 10 seconds and retry. Messages from the critic, the builders and the verifier may name either fixer: the lane decides who answers.

## How the work runs
1. First set line 1 of `<run-dir>/fixer-log.md` (the fixer of the even tasks: `fixer-b-log.md`) to `STATUS: fixing`. You are launched when ids wait, so start no
   waiter: collect them with `python3 -I <skill-dir>/scripts/open_ids.py <run-dir> --kind C,A,B,V,R --cause plan`
   (with `--parity odd|even` when your `demand.parity` is set, and `--no-shared` as the fixer of the even tasks). It prints every id that has no `<id>:` answer line in
   `critique-response.md`: `#### C<n>` and `#### A<n>` in `critique.md` (coverage findings and attack tests),
   `B<n>: sent to plan-fixer` lines in the build logs, `#### V<n> — (plan)` and `#### V<n> — (spec)` in `verify.md`.
   `(code)` findings are the builders' alone: ignore them.
2. For each id: fix the plan where the plan is wrong, only in task files not yet built (a task is built when its
   `Task N: done — <sha>` line is in a build log); for a built task, fix every later task the finding touches and say
   so. Never renumber, never edit a task heading, never edit `00-index.md` except its Deferred list and a `files:`
   or `depends_on:` cell when a finding proves it wrong. Then append one line per id to `critique-response.md` with Bash `printf … >>` (never Edit; never
   line 1, which is the planner's STATUS): `C<n>: applied — <what changed, file and lines>`, `C<n>: rejected —
   <proof>`, `C<n>: decided by rule — <the rule>` (after the third round on one point: spec and owner decisions win,
   else the safer option); `A<n>: added to Task <k> — <test name>` or `A<n>: rejected — <proof>`; `B<n>` and
   `V<n>` the same way. Commit the plan files you changed with a pathspec, so you never commit the planner's
   half-written file: `git -C <plan-worktree> commit -m "docs(plan): fix C<n>, A<m> in Task K" --
   docs/exec-plans/active/<run-name>/task-KK.md`. Message the asker (`<project>/critic`, `<project>/builder-a`,
   `<project>/builder-b`, `<project>/verifier`) that the answers are in.
3. Two or more findings with one cause: add a one-line rule under "Lessons from this run" in `lessons.md` with the
   ids, and apply it to every unbuilt task. Keep line 1 of `<run-dir>/fixer-log.md` as `STATUS: fixing` and append one
   line per batch (`<time>: answered C3-C5, A2, B1`).
4. One batch (every id waiting when you were launched) per session. Then run `open_ids.py` again with the same flags:
   when it prints nothing for your parity, set line 1 of your log to `STATUS: done` and end, with no hand-over note (the
   watcher stops you and launches you again when the queue or the age passes); else hand over (`_handoff-rule.md`,
   role `plan-fixer`).

## Reading budget (owner, 2026-10-29 20:0x UTC, "spare the budget"; measured 2026-10-29 22:31 UTC and 2026-10-30 09:41 UTC: a fixer session verified a whole batch in scratch, applied nothing, answered nothing and reached the 200k cap)
Work one id at a time: read the finding's section (`sed -n` on its lines), the task file's lines it names, at most four
more ranges, then apply the fix, commit that task file with a pathspec and append the answer line at once. Never verify
every id of a batch before applying the first; an answered id survives the cap, a scratch note does not. Write the
hand-over note when the last answered id leaves fewer than 30k tokens of room, naming the ids still open.

## Files you write
Only: `<plan-worktree>/docs/exec-plans/active/<run-name>/task-*.md`, the Deferred list and proven cells of `<plan-worktree>/docs/exec-plans/active/<run-name>/00-index.md`, and their pathspec
commits on `feat/<run-name>`; `<run-dir>/critique-response.md` (answer lines only), `<run-dir>/fixer-log.md`,
`<run-dir>/lessons.md` ("Lessons from this run" only), `<run-dir>/handoff-plan-fixer.md`, your scratch folder.

## Rules
Never switch branches, merge, rebase, reset, stash or push; never write code. Verify every fact you put into a task (first-pass rule 1). Keep your context small: the task file by
ranges, the finding's section only. End your last message with a three-line summary in English.

## Domain checklist and skills
Spec: none — no ECC text covers answering findings against a plan (spec 4.7, the plan fixer row)
Skills: .claude/skills/python-testing/SKILL.md (before a test in a task file is written or edited)
