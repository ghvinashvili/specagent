---
title: Bootstrap runs eleven steps in order
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: two steps were added after ADR-0029 listed them, and the texts that name bootstrap's work fell behind its docstring
would_change_if: a step added to or removed from `ops/bootstrap.py`, which changes this page, the template README and `ops/new-project.py`'s docstring together
decision_status: decided
scope: global
tags:
  - decision
---
# Bootstrap runs eleven steps in order

`ops/bootstrap.py` runs eleven steps in this order, each skipped when it is done: uv; the workspace; `just`; the git
hooks; the plugins; the language servers; the sandbox; the first code graph; graphify's skill; the user-level pipeline
skill, a link to the checkout's; `harness doctor`. Its docstring describes each step, and the template README and the
docstring of `ops/new-project.py` name all eleven, which `ops/tests/test_bootstrap_steps.py` checks. This page
supersedes ADR-0029 :38-40, which stays as history: its list ends at the first code graph, and the manager-build run's
Task 9 added graphify's skill and the pipeline skill's link (items 9 and 10).

## Record and source
- [ADR-0029](../../docs/decisions/0029-a-checkout-sets-up-its-hooks-sandbox-and-graph.md)
- [ADR-0009 A checkout sets itself up](../../docs/decisions/0009-a-checkout-sets-itself-up.md)
- [The template's README, renamed to docs/template/PROJECTS.md on 2026-10-31](../../docs/template/PROJECTS.md)
