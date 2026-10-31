---
title: No tests that settle no decision; think from the evidence, fix everything known, launch once
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [all]
sources: []
decided: 2026-10-02
by: owner
review: 2027-10-31
why: live comparison runs cost about $49 in one day for what a side-by-side comparison of inputs shows for nothing
decision_status: decided
would_change_if: never
---
# No pointless tests

**Rule.** Before proposing any test or run, name the decision it settles and why existing data cannot settle it; by default design the solution instead. Check parity of prompts, inputs, packs, tools and effort by laying them side by side, not by running both sides. Pytest and deterministic scripts that call no model are not live runs.

**Why.** Live comparison runs cost about $49 in one day for what a side-by-side comparison of inputs shows for nothing, and the owner refused twice to spend tokens on testing. Failed tests give the owner nothing, and fixing one problem per run makes them watch tests instead of receiving a finished result. The cases are in the source notes.

**How to apply.**
- Launch once: think everything through, turn every known problem into a code gate, present the complete list once and ask for one go.
- Quality checks belong inside the production pipeline, not in separate lab runs.
- Existing results first: before a new sweep or run, look for results already computed (grid outputs, research documents, caches), answer from them and compute only what they do not cover.
- Measure the gain before building it: on real data, in the units the owner works in, report the number, then give a verdict, not a menu, including how narrow the benefit is and what it does not fix.

Related: [[retry-loops-max-3]], [[do-what-was-asked-then-the-root-cause]].
