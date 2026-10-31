---
status: accepted
date: 2026-10-28
decision-makers: the owner, in the spec of the template-core run (items A4 and A5)
consulted: the template-core run's planner, critic and plan fixer
informed: every project created from this template
---

# Plans in parts and layered document indexes

## Context and Problem Statement
`docs/llms.txt` was one flat index: 107 lines and 10,921 bytes at commit d4811e1, 5,422 of them the list of decision
records. A plan was one file: the run-loop plan (development records, outside the repository since 2026-10-29) had 2,201 lines. In an earlier project of the owner,
one task of 5,197 plan lines took 4.5 hours and 11 planner sessions (item B5 of the owner's spec of the template-core
run). A session pays on every call for everything it has read, so an index or a plan that is read whole costs on every
step after it. How are the indexes and the plans laid out so that an agent reads only what it needs?

## Decision Drivers
* Load on need: an agent reads an index, then the one document it needs.
* One line per item in every index, and an index at most 12,000 bytes.
* A task file is what a builder reads whole: at most 1,500 lines.
* A check by code, not by review: a missing line or a long task fails a command.

## Considered Options
* One flat `docs/llms.txt` and one file per plan, as before
* Layered indexes (`docs/llms.txt` → a folder's `README.md` → the document) and plans as folders of `00-index.md` plus
  `task-NN.md`, checked by plan-lint
* An index generated from the tree, as `ops/build_indexes.py` in the owner's vault generates one

## Decision Outcome
Chosen option: the layered indexes and the plans in parts, because they keep the hand-written sentence per document,
halve `docs/llms.txt` and give a builder one task file to read, and every rule is checked by `harness docs-check`.
* A document under `docs/` is listed when `docs/llms.txt` links it (L1); when `docs/llms.txt` links its folder's
  `README.md` and that README links it (L2, one level only: a README listed by another README lists nothing); or, for
  a file inside `docs/exec-plans/active/<plan>/`, when `docs/exec-plans/active/README.md`, itself linked from
  `docs/llms.txt`, links `<plan>/00-index.md` (L3). A path in backticks lists nothing.
* A `<name>.<language>.md` summary beside a page needs no line; docs-check warns, and never fails, for a page under
  `wiki/decisions/` or `docs/runbooks/` without one.
* Links inside fenced code blocks and inline code are text, as lychee reads Markdown without `--include-verbatim`.
* `docs/llms.txt` and every `README.md` or `index.md` under `docs/` stay at most 12,000 bytes.
* plan-lint: each folder under `docs/exec-plans/active/` is a plan whose `00-index.md` has a `## Task order` table; the
  row `| N |` names `task-NN.md`. Every named task exists, starts with `# Task N`, and has at most 1,500 lines counted
  at newlines; no task file is outside the order, and no number appears twice. Files directly in
  `docs/exec-plans/active/` (single-file plans, plan-mode drafts) are not linted. docs-check runs plan-lint too.
* The decision records are listed in `docs/decisions/README.md`, which `docs/llms.txt` links.

### Consequences
* Good, because `docs/llms.txt` halves (6,072 bytes after the move) and a builder reads one task file, not a whole plan.
* Good, because a plan's task count is fixed when its order is written: growth goes to a task's Deferred list.
* Bad, because a new document needs its line in the right index, and docs-check has more rules to know.

### Confirmation
`packages/harness/tests/test_plan_lint.py` and `packages/harness/tests/test_docs_layers.py`; `uv run harness
docs-check` and `uv run harness plan-lint` in CI's documentation check and in every writer's checks.

## Pros and Cons of the Options

### One flat `docs/llms.txt` and one file per plan
* Good, because one file holds every line, and nothing needs a rule of where a line goes.
* Bad, because every agent that opens the index pays for all of it, and the list of decision records alone is half.
* Bad, because a plan of thousands of lines is read whole by every session that works on one of its tasks.

### Layered indexes and plans in parts
* Good, because each index stays small and keeps one written sentence per document.
* Good, because plan-lint and docs-check hold the structure by code.
* Bad, because a writer must know which index lists a new document.

### An index generated from the tree
* Good, because no line is ever missing.
* Bad, because it needs a category file, and the hand-written sentence per document is lost.

## More Information
The layers, the indexes, the plans in parts and the summaries are described in
[the documentation layers](../architecture/documentation.md). The source is the owner's spec of the template-core run,
in the template's development records (outside the repository since 2026-10-29), which projects do not receive. The owner's vault decision
`plan-whole-research-first-one-document` (outside this repository) plans the whole thing first, from researched
sources, as one plan; its addendum of 2026-10-28 keeps that one plan on disk as ordered part files with an index, the
task count fixed when the task order is written.

* Amended on 2026-10-29 by [ADR-0030](0030-the-template-is-english-only.md): a summary is `<name>.summary.md`, in English.
