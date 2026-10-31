---
title: The spec writer writes the skeleton, the planner the flesh
type: decision
status: draft
updated: 2026-10-31
created: 2026-10-31
audience: [all]
decided: 2026-10-31
by: owner
why: a spec that lists data, interfaces and tests is a plan written on the spec model, which is meant for the short document; the plan is the planner's, in the judgment class
would_change_if: a measured run shows that a one-page spec leaves the planner guessing at intent, or the owner orders another split of the two
decision_status: decided
scope: project
tags:
  - decision
---
# The spec writer writes the skeleton, the planner the flesh

A spec is about one page, under 8,000 bytes: intent, requirements, limits, what counts as done and what is out of scope, each
acceptance criterion mapped to a requirement. It names no data model, interfaces, signatures, file lists, line numbers, moves or
tests; those are the plan, and the plan is the planner's: data, flows, interfaces, and tasks with files, commands and tests. The
spec writer is never used as a planner, and a spec longer than a page is a sign the brief asked for the plan. In the
`software-factory` pipeline the spec stage feeds the plan stage, and no stage and no brief template asks the spec writer for
plan content. A check keeps it so: the role catalogue and `harness validate` refuse a spec-writer type whose output sections
include a data model, interfaces or tests, and `harness docs-check` warns about a spec file that is not under 8,000 bytes.

The model map follows the work. The spec writer runs on the owner's spec model, a dated exception named only in the launch
table's message; the planner, critic, verifier and judge run in the judgment class; the builder runs in the mechanical class; the
effort is never lowered. A role's class is set in a settings file no role reads, so no brief, flag or text names a model. The
rule is the owner's vault page `decisions/global/models-per-role.md`.

The lessons loop gets a third step: a finding is recorded where it was made, a cause shared by two or more findings becomes a
rule, and a rule broken a second time becomes a check in code (a hook, a watcher or monitor script, a `check_formats.py` or
`harness validate` rule, a test). The pipeline skill's "Briefs" section and the example `lessons.md` say so. The rule is the
owner's vault page `decisions/global/a-rule-broken-twice-becomes-code.md`.

## Record and source
- [Spec 005](../../specs/005-spec-writer-rule/spec.md): requirements 1-6
- [The spec writer's model is a dated exception](the-spec-writers-model-is-a-dated-exception.md): where the spec model is named
- [The pipeline skill](../../.claude/skills/running-specagent-pipelines/SKILL.md): the model map and "Briefs"
