---
title: Roles and sessions keep their names until the owner names them
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: the skill, the spec and the template already say roles and sessions, and a rename would touch every file before the owner has chosen a name
would_change_if: the owner names the pipeline's agents
decision_status: decided
scope: global
tags:
  - decision
---
# Roles and sessions keep their names until the owner names them

A pipeline's agents are called roles, and one run of a role a session, as the pipeline skill and the manager spec say.
The owner dropped their earlier name (2026-10-29); until the owner gives another, these words stay and no
file is renamed, and the template keeps its own name. This is the owner's answer (a) to
question 7 of the manager spec, "(a) until the owner names it" (2026-10-29). Revised for the template's name on
2026-10-30: [The template is named SpecAgent](the-template-is-named-specagent.md).

## Record and source
- [The pipeline skill](../../.claude/skills/running-specagent-pipelines/SKILL.md)
- [Pipelines run as SpecAgent sessions from a template skill](pipelines-run-as-specagent-sessions-from-a-template-skill.md)
