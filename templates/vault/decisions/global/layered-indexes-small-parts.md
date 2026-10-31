---
title: Big files are split by topic into titled parts; indexes are layered by category, so no agent reads a whole file or a whole index
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [all]
sources: []
decided: 2026-10-25
by: owner
review: 2027-10-31
why: the vault's raw files reach 862 KB (STRUCTURE.md); an agent that must read a whole file or a whole index to find one fact pays for all of it
decision_status: decided
would_change_if: never; only the thresholds may move
---
# Layered indexes, small parts

**Rule.** A large text file is split by topic at its own headings into parts, each titled by what it holds. Finding
goes down short steps: a top index of categories (10–15 lines), an index per category (one line per file), an index
per file listing its parts with their original line ranges (split again into its main sections when long), then the
part. An agent reads a few dozen lines at each step and opens only the part it needs. This holds for the vault and
for any project's knowledge folders.

**Why.** The vault's raw files reached 862 KB (STRUCTURE.md); an agent that must read a whole file or a whole index to
find one fact pays for all of it.

**How to apply.**
- Cut large files with `ops/split_large.py` into titled parts of at most 12 KB (the first run cut the files over
  24 KB); build the layered indexes with `ops/build_indexes.py`.
- Index memory folders over 40 files by topic (`ops/memory-topics.json`).
- Do not split files that live sessions edit (exec plans, specs, runbooks in a project repository): moving them breaks
  the line citations in plans, critiques and logs, the repository's docs check (every file under `docs/` is listed in
  `docs/llms.txt`), and the branches' merges.
- For such a file, `ops/outline.py <file>` prints its top layer with current line ranges; `--under "<heading>"`
  (repeatable) goes down a layer, `--show "<heading>"` prints one section numbered in a single call, `--grep` finds a
  heading; then only that range is read.

Related: [[keep-context-small]].
