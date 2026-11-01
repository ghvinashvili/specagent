---
title: No one-agent mode; a project's work runs as the multi-role pipeline
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-11-01
audience: [main]
sources: []
decided: 2026-11-01
by: owner
review: 2027-11-01
why: a measured run of one agent doing every role in turn on one task, against the multi-role pipeline on the same work, found it a quarter cheaper per task but 2.5 times slower and weaker in review, so the owner cancelled the mode in the template
decision_status: decided
would_change_if: the owner names a one-agent run again
---
# No one-agent mode; a project's work runs as the multi-role pipeline

**Rule.** The template offers no one-agent mode, in which one session plays planner, critic, builder and verifier
in turn. A project's work runs as the multi-role pipeline: separate `claude --bg` sessions per role, a separate
critic beside the planner and a separate verifier per commit.

**Why.** On 2026-11-01 one agent built the same kind of tasks a multi-role run built. It cost about a quarter less
per task but took 2.5 times longer, and its own critique found 2.3 plan defects per task against 5-8 by a separate
critic; two major defects passed it (the project's measurement record, named in the owner statement of 2026-11-01).

**How to apply.**
- No brief, config example or README section of the template offers a one-agent run.
- The cache and compaction rules (the vault page cache-and-compaction) serve the multi-role pipeline and stay.
- A one-agent measurement already made stays as its project's record; it is not a mode to reuse.

Related: [[project-work-runs-through-the-pipeline-skill]].
