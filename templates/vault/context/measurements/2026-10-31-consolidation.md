# Measurement: the consolidation run (2026-10-30 – 2026-10-31 10:1xZ)

What: `specs/004-consolidation` (S1-S10: the template is named SpecAgent, nothing personal, plugin skills, ECC in
`.claude/ecc/` with a catalogue, plans to `docs/exec-plans/done/`, decisions, the project README to `docs/template/PROJECTS.md`,
"chat agent" to SpecAgent, README/llms.txt/CHANGELOG, the version bump) written by a spec-writer, built by a builder in 10
units, checked by a verifier; merged into template main as b053d37 on 2026-10-31 and pushed.
Run folder `~/Desktop/aftpro/runs/consolidation-2026-10-30/`.

## The run
`score consolidation-2026-10-30: tasks 10, findings V 10 (plan 0, missed 0), rejected 0, sessions 42 (idle 8), cost $122.14, cache-read 96%`
(spec-writer 9 sessions $48.54; builder 17 sessions, 659 calls, average context 133k, $28.70; verifier 13+1 sessions,
677 calls, $44.90). Economy row: `| 10 | $12.21 | 4.2 | 1.2 | 1.0 | 0 |` = units 10, cost per unit $12.21, sessions per
unit 4.2, copies per unit 1.2, findings per unit 1.0, escaped to the gate 0. Raw: `2026-10-31-consolidation.score.json`.
Not counted: the SpecAgent desktop sessions of 03:54-05:2xZ (the CLI was on an account at its weekly limit; they ran in the
desktop app, outside `usage_report.py`'s records).
Estimate in `_launch.md`: 7-8 sessions, budget $20, for 3 build units. The spec grew to S1-S10 (10 units) after the launch;
the budget line was not raised and the manager did not stop at $20: an overrun of 6x, unrecorded until this page.

## What it shows
- Against the economy run (7.3 sessions and $15.93 per unit) the new defaults hold: 4.2 sessions and $12.21 per unit;
  the ingest row was 4.6 and $8.60. The spec-writer is the expensive role: $48.54 for one spec in 9 sessions.
- Quality: 10 V findings in 10 units, all closed (8 fixed, 1 by striking a spec clause, V8 by MAIN's ruling); 0 escaped;
  the final gates at b053d37: 1899 passed + the map test, every lint green.
- The manager's misses: a `(spec)` finding for MAIN (V8) waited 3 hours (07:14-10:04Z), because the records monitor wakes on
  request lines and commits, not on a question to MAIN; the verifier's final line `STATUS: verified …` did not match the
  watcher's `STATUS: done`, so the watcher relaunched a finished verifier 3 times; a duplicate manager (the desktop copy of
  the chat) answered a SANDBOX line (manager-lessons 14).
