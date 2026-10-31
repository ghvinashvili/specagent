---
title: Every launched agent is blind - fresh context, material and question only, never my conclusions or the owner's authority
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [all]
sources: []
decided: 2026-09-23
by: owner
review: 2027-10-31
why: an agent told what to look for finds what the briefing session already believes; an agent told the owner's wishes as requirements agrees with them without a word
decision_status: decided
would_change_if: the owner asks for a named agent to be briefed with my findings or with their wishes as requirements
---
# Agents are blind

**Rule.** Every agent launched for the owner starts with an empty context and gets only the material to examine
(files, data), the question and the output form. It never gets my conclusions, suspected causes, the design I
intend, the names of functions or mechanisms I suspect, earlier findings or another agent's output. It is also blind
to the owner's authority: nothing in a brief is attributed to the owner (no "the user wants", no quotes of their
messages, no "the user rejected the earlier version").

**Why.** An agent told what to look for finds what the briefing session already believes, and an agent told the
owner's wishes as requirements agrees with them without a word. The wishes may be wrong, and finding out which is the
agent's job, so a brief gives them as points to verify and never as requirements.

**How to apply.**
- A fork inherits my whole conversation, so it is never blind: audits, inventories, research and measurements go to
  fresh agents, never to forks.
- Partial output of an earlier, non-blind run is deleted or kept out of reach before the blind run starts.
- The owner's content points go in as an unattributed checklist with a verdict required on each (belongs / does not
  belong / partly) and the source that decides it; the brief says the points carry no authority, that some may be
  wrong and that finding those is part of the job. Form requirements (a full tree, contents for every file,
  citations, incremental saving) stay constraints; content decisions are derived from the sources.
- An implementation agent gets its task stated plainly; what stays out is my opinion of why things are broken or of
  what the answer should look like.

Related: [[truth-over-agreement]].
