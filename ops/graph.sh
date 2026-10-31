#!/usr/bin/env bash
# The code graph (spec A3), the body of `just graph`; the git hooks in .githooks/ run it with --quick.
set -euo pipefail

case "${1:-}" in
"") ;;
--quick)
  # After a commit, merge or checkout: nothing to do without graphify or with GRAPH_SKIP=1; the build's output is
  # discarded, a failure is one line on stderr, and the git command never fails (bash ignores set -e inside a
  # condition, so the build runs as a process of its own).
  if [ "${GRAPH_SKIP:-}" = 1 ] || ! command -v graphify >/dev/null 2>&1; then
    exit 0
  fi
  bash "$0" >/dev/null 2>&1 || echo "graph: the code graph was not refreshed (exit $?); bash ops/graph.sh shows why" >&2
  exit 0
  ;;
*)
  echo "usage: bash ops/graph.sh [--quick]" >&2
  exit 2
  ;;
esac

cd "$(dirname "$0")/.."
export GRAPHIFY_OUT=graphify-out # graphify's output folder (graphify/paths.py), whatever the caller set
if ! command -v graphify >/dev/null 2>&1; then
  echo "graph: graphify is not installed (the PyPI package graphifyy): uv tool install graphifyy==0.9.64, then run bash ops/graph.sh again" >&2
  exit 3
fi

graphify update .
graphify export wiki
# The earlier build goes whole, its split folders included, so ops/split_large.py never skips an article.
rm -rf wiki/graph
mkdir -p wiki
mv graphify-out/wiki wiki/graph
python3 -I ops/graph_index.py wiki/graph
