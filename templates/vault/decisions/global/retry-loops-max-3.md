---
title: Every automatic retry or revise loop stops after 3 rounds; then decide by rule or escalate
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [all]
sources: []
decided: 2026-10-05
by: owner
review: 2027-10-31
why: the owner fears endless cycles burning the usage limit
decision_status: decided
would_change_if: never
---
# Retry loops: at most 3

**Rule.** Any automatic loop (judge `revise` → rewrite, article gate correction rounds, finding ↔ fix rounds) has a hard cap of 3 iterations. State the cap whenever a loop is proposed or built. After the cap: in an unattended pipeline the dispute is decided by rule (the spec and recorded owner decisions win, otherwise the safer option) and doubtful items are held and logged; in interactive work, stop and tell the owner. Never design an unbounded loop.

**Why.** The owner fears endless cycles burning the usage limit. A cap turns an open-ended cycle into a decision: by rule when nobody is there, by the owner when someone is.

**How to apply.**
- Put the cap in the loop's brief or code, and say it when the loop is proposed.
- Article pipelines: quality and SEO gates loop at most 3 rounds, then the best version is published and the gate is flagged for tuning (the owner, 2026-10-09); a fact gate never publishes an unconfirmed fact.
- Since 2026-10-22 an article that fails a gate stays `held` and is logged, waiting for no human; that rule gives no round count.
