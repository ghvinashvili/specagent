# Rules for getting it right the first time (owner, 2026-10-09; carried into this run 2026-10-28)

These apply to the planner and the builders, in addition to your assignment.

1. Facts come from installed code and official pages, not from memory, because a remembered flag or version may be
   wrong and everything built on it is redone. Before you write (planner) or use (builder)
   any library, module, function, option, config key, command, CLI flag or version, confirm it: in the checkout
   (`pyproject.toml`, `uv.lock`, `packages/harness`, `.claude/`, `justfile`), in the installed tool's own `--help`
   (graphify 0.9.64 at `~/.local/bin/graphify`, `claude --help`, `just --list`), in the Python 3.12 documentation, on
   the library's PyPI page or official documentation, or on Claude Code's documentation pages. Planner: end each task
   with a short "Verified" list, one line per fact with its file:line, command or URL, so the critic can re-check each
   fact. Builder: when the installed code or the official page contradicts the plan, send the planner the proof instead
   of guessing, since a guess repeats the error in the next task.
2. Before you call a task finished, go through `lessons.md` ("Known error classes" and "Lessons from this run") and
   make sure the task handles every item that applies, because each item is an error an earlier run already paid for: the
   planner in the task's steps and tests, the builder in the code and its tests.
3. When you answer findings (the planner the critic's, the builder the verifier's) and two or more share
   a cause, add that cause as a one-line rule under "Lessons from this run" in `lessons.md`, with the finding ids, and
   apply it to every later task, so the cause is not found again (step 2 of the ladder in the pipeline skill's `SKILL.md`, "Briefs"). Grep `lessons.md`
   for today's date before each task for lines added since you read it.
4. Read late and narrow. Open a file only when the step you are on needs it, by line ranges (`sed -n`, `grep -n`,
   `cut -c1-300`, `head`), never whole: what you read stays in the context and is re-read by every later call of the
   session, so a read costs its size times the calls that follow it (measured 2026-10-22: 84% of a session's growth is
   tool results). At the start of a session read your assignment, this file, `_handoff-rule.md`, the facts pack
   `_inputs/<topic>.md` your brief names, lessons.md's "Read first" section and, last, your note; nothing else until a
   step asks for it. The note carries the state.
