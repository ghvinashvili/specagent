# `task_lint.py` — a task file checked before it is handed on
The content of each task; `uv run harness plan-lint` checks the plan folder's form (the index, the headings, the
size) and runs in docs-check.
```
python3 -I scripts/task_lint.py <task-NN.md | plan-dir>... [--repo DIR]
```
Per task file (a plan folder gives every `task-NN.md`; a `task-NN.code.md` is read with its task): a `Step 0` whose
`Expected:` line holds a number, the tests collected at the task's base; every command, a fenced shell block (`bash`,
`sh`, `shell`, `console`, `zsh`) or a `Run:` line, followed by an `Expected:` line before the next command or step; and
every fenced `python` block passing `ruff check` and `ruff format --check`, run from the repository (`--repo`, else the
plan's git checkout) so its own rules apply, when it has a ruff configuration (`ruff.toml`, `.ruff.toml` or
`[tool.ruff` in `pyproject.toml`). A block is checked as a fragment, since it is often the lines to add to a file and
uses that file's names and imports: dedented, without the rules that need the whole file (F401, F811, F821, E402,
I001); a block that does not parse alone, or holds only expressions that are no calls (one entry of a set), is counted
as `unchecked fragment <n>`, never refused. A block of another language is counted as `unchecked <lang> <n>`, never
passed. A fence closes on a line of the same character, at least as long as the opening, with nothing else on it
(CommonMark), so a block of four backticks quotes a block of three.
Prints `<file>:<line>: <problem>` per problem and `task_lint: <n> files, <m> problems`; exit 0 with none, 1 with
one, 2 when a path is not there or ruff does not run (it cannot start, or ends with an exit other than 0 and 1): its
error goes to stderr and nothing to stdout, since no edit of a task fixes a tool that does not run. The planner runs it before `Task N: written`, the plan fixer before each commit
(a project's run of 2026-11-02: tasks without the Step 0 count and the Expected lines, C34 … C63; quoted tests that failed
ruff, lessons.md "Lessons from this run").
