---
title: The managing session owns the structure; mechanical steps are scripts; the owner reads outputs and decides
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [main]
sources: []
decided: 2026-10-04
by: owner
review: 2027-10-31
why: the owner wants to read outputs and decide, not spot structural problems by reading along; a manager that spends tokens on mechanical work defeats the economy
decision_status: decided
would_change_if: never
---
# Manager owns the structure

**Rule.** The managing session owns material, routing, assignments, gates, procedure and turning each mistake into a
check, without asking the owner about structural details. Success means the owner never has to spot a structural
problem; the manager or its gates catch it first. The owner gets outputs (verdicts, results, costs) and real decisions
only, each with a recommendation, in plain words about what changes for them.

**Why.** The owner wants to read outputs and decide, not spot structural problems by reading along; a manager that
spends tokens on mechanical work defeats the economy.

**How to apply.**
- *Not unilateral.* A manager acting on its own and doing everything may damage things (the owner's words are in
  `context/owner-statements/2026-10-04.md`): a structural fix follows a written procedure, is carried out by separate
  agents (a run) with the owner's approval, and reaches the owner as one approved package, design first, not piece by
  piece. The manager notices, records and proposes; it never patches the template ad hoc.
- *Scripts, not manager tokens.* A step decidable from files alone (cutting material, choosing a stage's pieces,
  budgets, ordering, waiting, watching) is a deterministic script in the harness with tests; the manager writes only
  what a script cannot know. Explain the method to the owner instead of proving it with live runs.
- *Material by script.* Material is indexed and chosen by script per session (a writer gets only its own tasks' parts,
  a reviewer the work's version, never the base; the shared part first so the cache stays shared), and gates turn each
  mistake into a check (e.g. launch refuses an assignment changed after its preview).
- *Priority.* When the usage limit allows, refine the managing session first: if it cannot manage well, nothing will go
  well.

Related: [[owner-questions-and-status]], [[no-pointless-tests]], [[template-carries-what-user-relies-on]].
