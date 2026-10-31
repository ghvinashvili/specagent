# Hand-over rule: planner, critic, builders, verifier (owner, 2026-10-09; cap 200k since 2026-10-29 01:50 UTC, 300k from 2026-10-26 to then)

Each session does one unit of work and then hands over to a fresh session, so that its context stays small: every
step re-reads the whole conversation. The owner's cap is **200k tokens per call** (measured 2026-10-26 on 269 sessions: 300k cost 15-25% more per task, hand-overs included). The owner's watcher reads your
context size from the transcript; when it passes the cap it stops you and resumes you once with the order to hand
over. The plan, `lessons.md`, the build logs, `verify.md`, `critique.md`, `critique-response.md`, `plan-log.md` and
git are the record; your note carries only what your session knows and those files do not.

## When
- Hand over yourself: at the unit's end write the note at once, in the same turn as the unit's done line; the
  watcher's order, and the copy it starts, is the exception, not the way.
- Planner: when a task file is written and committed, its line is in `plan-log.md`, and every finding that was
  waiting is answered in `critique-response.md`. One task per session: do not start the next one. Line 1 of
  `critique-response.md` keeps saying `STATUS: writing Task N` for the task the next session will write.
- Critic: when you have finished one unit, the coverage round of one plan task (its findings are in `critique.md`, the
  STATUS line is updated), and you have checked the answers that were waiting.
- Builder: when a task is committed and logged (`Task N: done — <sha>`) and the findings you were fixing are
  answered in your build log. Never in the middle of a task, and do not start the next one.
- Verifier: when you have finished verifying one built commit (its section in `verify.md` is written and every
  finding filed) or one milestone's full run. Re-checking a fix does not end a session; do it in the session you are in.
- Any role, when the watcher resumes you with the order to hand over: save what you have at a point where nothing is
  half done (finish the step, not the task), then hand over.

## How
1. Overwrite `<run-dir>/handoff-<role>.md` (`<role>` is planner, critic, builder-a, builder-b or verifier), in English,
   at most 40 lines, in one Write call from what you know (do not re-read the files to write it):
   - Line 1, exactly: `HANDOFF <role> after Task <N> — <YYYY-MM-DD HH:MM>`. A new line 1 is what starts the next
     session, so write this file last, once, after everything else is saved and committed.
   - State: the last unit finished, its commit, and anything half done (there should be none).
   - Next unit: which task or commit, with the facts it needs copied in (paths, names, values, the ids waiting).
   - Open threads: ids still waiting for an answer (C, A, V, B) and from whom; messages that were held.
   - Working knowledge that is not in `lessons.md` or your assignment: commands that work here, traps you hit and
     how you got past them, facts you verified that the next unit needs (path:line).
   - Read first: at most 5 files or line ranges the next session needs for its first step.
   Leave out anything the files above already say.
2. End your turn. Start no waiter and no new work. The owner's watcher stops this session and starts a fresh one
   with the same name, which reads your assignment, `lessons.md`'s "Read first", the logs and, last, your note, and
   continues.
