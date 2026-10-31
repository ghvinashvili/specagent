---
title: The manager is the pipeline skill's main session
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: the owner talks to one chat; the skill's main session already launches, watches, merges and measures the roles, and no page described it beside the harness's manager
would_change_if: the harness's manager runs SpecAgent pipelines with the same duties, or the owner chooses one design for both
decision_status: decided
scope: global
tags:
  - decision
---
# The manager is the pipeline skill's main session

The template held two manager designs: the harness's manager of `docs/roles/MANAGER.md`, a session started with
`claude --agent manager` that runs the stage table with `harness assign`, `harness launch` and `harness poll`, and the
main session that runs the pipeline skill, which launches the roles as background sessions, watches them, merges their
branches and measures them. On 2026-10-29 at 17:03 UTC the owner chose answer (a) to question 1 of the manager spec:
the manager that goes forward is the skill's main session, and the harness's manager stays for harness runs. Answer
(b), the harness's manager with the chat pipelines as one of its pipelines, was not taken; the skill's main session is
the design that ran, with measured results.

The template ships `docs/roles/manager-chat.md`, the chat manager's page: its four guards in place of the sandbox, its
duties before, during and after a run, how it measures itself, its recovery and its lessons page. `docs/llms.txt`
lists it under `## Roles`; `docs/roles/MANAGER.md` is unchanged.

## Record and source
- [The manager in chat](../../docs/roles/manager-chat.md)
- [Manager specification](../../docs/roles/MANAGER.md)
- [Pipelines run as SpecAgent sessions from a template skill](pipelines-run-as-specagent-sessions-from-a-template-skill.md)
