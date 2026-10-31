# `audit_read_first.py` — the "Read first" audit
```
python3 -I scripts/audit_read_first.py <run-dir> [--today YYYY-MM-DD] [--json]
```
Flags the items of lessons.md's "Read first" section to review: a marker word (`HOLD`, `RESTATED`, superseded,
withdrawn, no longer), done work (every `Task N`, `M<n>`, `O<n>` it names is done by build-log.md), a similar item
(word ratio over 0.6) and age (over 7 days). Prints the flagged items, then a proposed compacted section with the
flagged items marked `[flag: …]` and nothing reworded. A flag is a reason to review, not to drop: the done flag also
marks standing rules that name a done task. It never edits. Exit 1 without the section, 2 without lessons.md.
