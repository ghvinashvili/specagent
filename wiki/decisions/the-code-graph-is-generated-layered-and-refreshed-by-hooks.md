---
title: The code graph is generated, layered and refreshed by git hooks
type: decision
status: draft
updated: 2026-10-29
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: an agent reads one layer's index of the graph instead of scanning the code, and a graph rebuilt by hand falls behind it
would_change_if: graphify's own hooks cover merges and export the layered wiki/graph/, or a measured run shows the incremental update holding a commit up longer than a minute
decision_status: decided
scope: global
tags:
  - decision
---
# The code graph is generated, layered and refreshed by git hooks

`bash ops/graph.sh` builds the graph with graphify and exports it in layers under `wiki/graph/`, one index line per top
folder and package; neither `graphify-out/` nor `wiki/graph/` is committed. The hooks in `.githooks/` (`post-commit`,
`post-merge`, `post-checkout`) run `bash ops/graph.sh --quick` after people's and agents' own git commands, skip it when
graphify is missing or `GRAPH_SKIP=1`, and never fail the git command; the harness's own git runs no hook.

## Record and source
- [ADR-0029 A checkout sets up its hooks, sandbox and graph](../../docs/decisions/0029-a-checkout-sets-up-its-hooks-sandbox-and-graph.md)
