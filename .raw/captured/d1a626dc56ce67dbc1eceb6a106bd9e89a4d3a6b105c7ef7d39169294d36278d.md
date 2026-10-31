---
title: A graph over the vault is measured before it is built
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: the vault held 169 KB of pages when the question was asked, which its index and outline tool may serve without a graph
would_change_if: a measurement that shows queries the vault's `INDEX.md` and `outline.py` answer late or wrong and a graph answers better
decision_status: decided
scope: global
tags:
  - decision
---
# A graph over the vault is measured before it is built

No graph over the owner's vault is built in the manager-build run. The main session first measures what the vault's
queries cost and miss with its `INDEX.md` and `ops/outline.py`, then decides whether a graph pays (tracker TD-015);
the template's code graph of the repository (`bash ops/graph.sh`) is unchanged. This is the owner's answer to question
12 of the manager spec, "measure, then decide" (2026-10-29; spec 7.5).

## Record and source
- [The code graph](the-code-graph-is-generated-layered-and-refreshed-by-hooks.md)
- [The shared knowledge base](the-shared-knowledge-base.md)
