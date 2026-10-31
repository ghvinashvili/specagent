# Active plans

A plan in progress is a folder `<plan>/`: `00-index.md` (goal, constraints, the task order table with one row
`| N | ...` per task) and one `task-NN.md` per task, at most 1,500 lines each. `uv run harness plan-lint`, which
`harness docs-check` also runs, checks that every task the order names exists, starts with `# Task N`, is not longer,
and that no task file is outside the order. Each plan folder gets one line in this file, under a `## Plans` heading the first plan adds, linking its `00-index.md`; its task
files, their code files and its `.summary.md` summary need no line of their own. Plan-mode drafts land here as single
files through `plansDirectory` (`.claude/settings.json`) and are not linted. Move a finished plan to `../done/` and give it its line in `../done/README.md`.

A task may keep its long blocks in a second file: every fenced block longer than 10 lines goes to `task-NN.code.md`
beside `task-NN.md`, under a heading `## Block <id>` whose id is the step number and a letter (`## Block 3b`), and the
step names it in its text as `Block 3b`. Plan-lint checks the pair. A code file without its `task-NN.md` is a problem,
its only one. In a folder that holds a code file, a block that a task file names and its code file does not define is
a problem, once per id, also when that code file was never written; a folder with no code file is linted as before. A
block heading twice in one code file is a problem. A block heading that no step names is a problem, so a code file
carries nothing the steps do not use. A code file has no line limit while its steps file keeps the 1,500 lines, and a
reference inside a fence of the steps file counts like one in prose.
