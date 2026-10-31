Decision (owner, 2026-10-29): the code graph is generated, layered and refreshed by git hooks.
bash ops/graph.sh builds it and exports one index line per top folder and package under wiki/graph/; neither output is committed.
The hooks in .githooks/ refresh it after every commit, merge and checkout; the harness's own git runs no hook.
The record is ADR-0029.
