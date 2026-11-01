# Hand-over rule: planner, critic, builders, verifier (owner, 2026-10-09; compaction instead of hand-over since 2026-11-01)

A session works unit after unit and compacts itself near 197k (`--autocompact 235000`), keeping its system prompt (this
lane's frozen pack) and a summary of the conversation; it does not hand over after a unit. **The owner's watcher orders
a hand-over only past `handoff_at` (250k tokens per call) or `cap` (260k), and the manager for a model change or a
stuck session.** Because a compaction keeps only the main points, write the facts your next step needs into your record
file as you go (your log, `critique.md`, `verify.md`, `critique-response.md`, `plan-log.md`). The plan, `lessons.md`,
those records and git are the record; a note carries only what your session knows and those files do not.

## When
- Only on an order: the watcher's (`handoff`, `unit-end`) or the manager's (`--order`), or for a long wait as
  `_common.md` "Waiting" says (your agent has a `work_check`). Never else write a `HANDOFF` line 1: a new line 1 starts
  the next session.
- On the order: save what you have at a point where nothing is half done (finish the step, not the task), then write
  the note as below.
- Between units: write your done line and the facts the next unit needs into your record, then start the next unit in
  the same session.

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
   with the same name and the same pack in its system prompt, which reads the lines of `lessons.md` dated after the
   pack and, last, your note, and continues.
