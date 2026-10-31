# `open_ids.py` — the open finding ids of a run folder
```
python3 -I scripts/open_ids.py <run-dir> [--kind C,A,B,V,R] [--cause plan] [--parity odd|even] [--no-shared] [--task N]
```
Prints the open ids, one per line: an id is open as `check_formats.ids()` reads the run folder (no answer line yet; a
B id only when it was sent to the planner or the plan fixer). The kinds print in the order of `--kind` (default
`C,A,B,V,R`), each kind's ids in reading order. An id's task is the `##` or `###` heading above its `#### <id>` line
when that heading starts `Task <n>` (`## Task 2 (diff)`, `## Task 2 — abc1234`); any other heading, or none (a build
log's B line), makes the id shared, and an id's first heading wins. Read-only.

| Flag | Keeps |
|---|---|
| `--kind C,A` | these kinds only, printed in this order; each entry one or two capital letters, no spaces |
| `--cause plan` | every id but a V or R whose heading names `(code)`: those are the builders', not the plan fixer's |
| `--parity odd` or `--parity even` | the ids of the tasks of that parity and every shared id |
| `--no-shared` | every id but the shared ones (the index's, a non-task section's, a build log's B line): the second plan fixer's collection, which the fixer of the odd tasks owns otherwise (judge J3 of the pipeline-fold run) |
| `--task N` | task N's ids only, no shared one |

Exit 0 when it printed an id (work waits), 3 when none (nothing to take), 2 on a usage error (a `--kind` entry that
is not one or two capital letters: `C, A`, `c,a`) or a run folder that does not exist, so a broken check never reads
as "nothing waits"; the watcher takes any code but 0 and 3 as a failed check and launches. The plan fixer's
`work_check` in `example/agents.json` is `open_ids.py {run} --kind C,A,B,V,R --cause plan`.
