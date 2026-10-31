---
title: Finished plans live in docs/exec-plans/done
type: decision
status: draft
updated: 2026-10-31
created: 2026-10-31
audience: [all]
decided: 2026-10-30
by: owner
why: the owner wanted the plans in progress and the plans of merged runs apart, so that a reader of docs/exec-plans/active/ finds only what is still being written
would_change_if: plan-lint is to check finished plans too, or the template stops keeping the plans of its own runs
decision_status: decided
scope: project
tags:
  - decision
---
# Finished plans live in docs/exec-plans/done

A plan whose run is merged moves from `docs/exec-plans/active/<plan>/` to `docs/exec-plans/done/<plan>/` (`git mv`, so the
history stays). `done/README.md` lists each finished plan by the link to its `00-index.md`, as `active/README.md` does for the
plans in progress; `docs/llms.txt` links both READMEs, and the check that decides whether a file of a plan folder is listed
(`catalog.listed`, rule L3) reads the README of the folder the plan is in. The plan text is not rewritten: only the paths that
name the moved folders change. `harness plan-lint` reads `active/` only, and `wiki/plans` still links `active/`. The first two
plans moved are `manager-build` and `pipeline-fold`. A new project gets `pipeline-fold`; `manager-build` stays in the `omit:`
list of `docs/template/variables.yaml` under its new path.

## Record and source
- [Spec 004 consolidation, item S4](../../specs/004-consolidation/spec.md)
- [The form of a plan folder](../../docs/exec-plans/active/README.md)
- [Finished plans](../../docs/exec-plans/done/README.md)
- [The plan file is split: steps in one file, blocks in another](plan-steps-and-blocks-in-two-files.md): the form of a plan folder, which this decision does not change
