# The pipeline's economy (spec 003): summary for the owner

- Goal: runs cheaper than the ingest run ($43.01, estimated $15-25) and no drop in quality; every rule has a check.
- R1: a session hands over by itself at its unit's end; the unit-end order waits 600 s (`unit_end_grace`) for its note.
- R2: a repeat's unit is sized from the last run's context per item to end under handoff_at: ingest 5 pages, not 9.
- R3: the verifier checks new code and fixes per commit, repeats in pairs, one replay per driver, the full suites once.
- R4: the manager writes a facts pack `_inputs/<topic>.md`; documentation only for a missing fact; JSON via filters.
- R5: a launch's Estimate names a measurement page and a cost per session; preflight fails a launch without them.
- R6: the model class follows the work, effort never lowered; SKILL.md drops the builder from its judgment list.
- R7: the night tick commits the renewed ledgers, log and hot cache on main only, with a fixed message.
- R8: a finding's cause may be `(brief)`, for a run without a planner.
- R9: an ingest lint answer without its counts stops with an error instead of passing as clean.
- R10: the supersede loop (two sources naming each other) is a to-check in `docs/architecture/knowledge.md`, not a fix.
- Savings: R1 and R2 up to $4-6 each (4 orders each, at $1-1.5 a hand-over); R3 about $5 of $43.01; R4 the startup
  lever (about 15% of a run). R5 and R7-R10 price the launch or close gaps; R6's saving is unpriced (below).
- Unchanged: cap 200k, handoff_at 150k, handoff_wait 1200 s (no gain within 140-180k); model names and prices.
- Measurement: `score_run.py` prints a row per run: units; cost, sessions, copies, findings per unit; escaped
  (past the verifier). Ingest: 5 | $8.60 | 4.6 | 1.8 | 1.0 | 0. Next: copies 0, cost lower, escaped 0.
- Open, each decided by the safer option until the row settles it: a copy's own cost (R1, R2); which ingest unit
  ended at 197k (5 pages per unit; 4 if it was the 8-page one); the model classes' prices, in no file (R6).
