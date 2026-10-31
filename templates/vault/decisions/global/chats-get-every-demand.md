---
title: A role chat gets every demand a subagent would, 1:1, plus the cache; success is quality, speed and economy together
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [main, planner]
sources: []
decided: 2026-10-02
by: owner
review: 2027-10-31
why: chats exist to reach at least subagent quality; a cheaper but shallower result is no win
decision_status: decided
would_change_if: never
---
# Chats get every demand

**Rule.** Every role chat receives what a subagent of the same kind would for the same job: the same assignment
demands, material, tools and permission to run code, the same effort. The one intended difference is the cache: the
material the job needs (documents, sources, earlier outputs) is placed in a stable system prompt and read from cache.

**Why.** Chats exist to reach at least subagent quality; a cheaper but shallower result is no win. Success is quality,
speed and economy together.

**How to apply.**
- Before any comparison, lay the full text each side receives side by side (agent definition with type contract, gate,
  `prompt.md`, pack versus the subagent's whole prompt) and confirm every demand of one side is in the other, or launch
  the subagent from the same definition. Comparing the assignments alone is not enough.
- Read the session's current effort from its transcript immediately before launch and give the chat the same.

Related: [[no-pointless-tests]].
