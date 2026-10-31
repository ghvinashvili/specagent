---
title: Decisions and pages are written with the work
type: decision
status: draft
updated: 2026-10-29
created: 2026-10-28
audience: [all]
decided: 2026-10-28
by: owner
why: knowledge written after the work is written late or never, and the commit that changes the code is the moment its author knows why
would_change_if: a measured run in which pages written with the work are wrong more often than pages the librarian compiles later
decision_status: decided
scope: global
tags:
  - decision
---
# Decisions and pages are written with the work

A task that changes code writes its pages in the same commit, or its plan says why it needs none.

## The rule
- The commit of a task whose work changes code adds or changes a page under `wiki/`, `docs/runbooks/` or
  `docs/decisions/`, or the planner gave the task `"docs": "none — <reason>"` in its `tasks.json`: `docs: none —`
  and a reason.
- An index, a log, a `README.md` or a `.summary.md` summary is no page. Tests, configuration, schemas, scripts and CI
  files are code; an instruction file or a plan task file is neither.
- A decision has a page of its own here, in `wiki/decisions/`. A changed decision is a new page: the old one gets
  `decision_status: revised` and `revised_by` naming the new one.

## How it is held
- The write gate fails a branch with code and no page unless every task of the shard has the planner's
  `docs: none — <reason>`; a `docs` the writer adds to its own copy counts for nothing (`pages_problem` and
  `planned_tasks` in `packages/harness/src/harness/gates/write.py`).
- A builder writes its pages as `draft`. `harness integrate` marks them `verified` once every verdict of the run is
  `accept` (`accepted` in `packages/harness/src/harness/work.py`); only a `verified` page reaches a knowledge pack.
- `harness wiki-lint` checks the fields of a decision page and resolves its `revised_by`
  (`packages/harness/src/harness/wiki.py`).

## Record and source
- ADR-0027: `docs/decisions/0027-pages-are-written-with-the-work.md`.
- The owner's spec of the template-core run, items A1 and A2.
