---
title: A project's work runs through the pipeline skill, never harness stages by default
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [main]
sources: []
decided: 2026-10-31
by: owner
review: 2027-10-31
why: a project's manager chat read the map line that named the harness first and ran a day's work stage by stage, the planner alone and the critic waiting
decision_status: decided
would_change_if: the owner names the harness's stage runner for a project's runs
---
# A project's work runs through the pipeline skill, never harness stages by default

**Rule.** A project's work runs as a SpecAgent pipeline run: the manager chat starts every role as a `claude --bg`
session through the skill `running-specagent-pipelines`, from one `_launch.md` table and one yes, the planner and the
critic in parallel. The harness's stage runner (`harness run`, `harness launch`, `docs/roles/stages.yaml`) serves only
a harness run the owner has named for that work.

**Why.** The owner chose the chat-agent pipeline over folding it into one loop (2026-10-29) and expects its parallel
form. On 2026-10-31 a project's manager chat followed the first map line of `CLAUDE.md` ("a manager session launches
role sessions stage by stage") and `docs/roles/MANAGER.md`, started an audit as a `read` stage and the plan as a `plan`
stage, sequential by `depends_on`, with no critic beside the planner; the owner had not asked for that form and ordered
that no manager chat misses this again.

**How to apply.**
- A manager chat's first reading is `docs/roles/manager-chat.md` and the skill's `SKILL.md`, before any launch.
- An audit or a research step is no reason for a harness stage: brief it as a role of the pipeline run, or ask.
- `CLAUDE.md` names the skill first and marks the harness commands as a harness run's only; `ops/tests/test_pipeline_choice.py`
  keeps the sentences in the template and in every project that copies the files (template 6c8b2c4).
- When the owner names a harness run, the harness's manager page applies to that run alone.
- A sequential form the owner did not ask for is stopped the moment it is seen and reported, not explained away.
