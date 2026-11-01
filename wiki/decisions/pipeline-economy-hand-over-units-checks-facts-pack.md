---
title: "Pipeline economy: hand over by itself, size the units, check in pairs, write a facts pack"
type: decision
status: draft
updated: 2026-11-01
created: 2026-10-30
audience: [all]
decided: 2026-10-30
by: owner
why: the obsidian-ingest run of 2026-10-30 cost $43.01 against an estimate of $15-25; orders started 9 copies of its sessions (builder 4 at the cap mid-unit and 3 at a unit's end, verifier 2), the builder's context grew about 13k tokens a page, and the verifier replayed every unit; the owner ordered every later run to cost less with no drop in quality
would_change_if: the economy row of the first run after the merge shows copies per unit above 0 or escaped above 0; then the rule that failed is revised against that row
decision_status: decided
scope: global
tags:
  - decision
---
# Pipeline economy: hand over by itself, size the units, check in pairs, write a facts pack

Superseded in part (2026-11-01): the TTL is 5m for every role and a session compacts instead of handing over by itself; see [decisions/session-compaction-and-the-lane-pack-in-the-prompt-cache.md](session-compaction-and-the-lane-pack-in-the-prompt-cache.md).

Four rules of the SpecAgent pipeline cut the copies and the re-reading that made the obsidian-ingest run of
2026-10-30 cost $43.01 against an estimate of $15-25 (40 pages in 5 units, 9 sessions started by orders), and one row
of `score_run.py` shows after every run whether they worked. A copy is the fresh session an order of the watcher starts
in place of the session it stopped.

- **A session hands over by itself at its unit's end.** `example/handoff-rule.md` tells it to write its note at once,
  in the same turn as the unit's done line; the watcher's order, and the copy it starts, is the exception. The
  watcher's `unit_end_grace` (600 s; `0` is the old behavior; a config without the key takes 600) holds the unit-end
  order until the new line 1 of the record is that old, so a note written within the grace starts the fresh session as
  usual and no order comes. A session still busy past the grace gets the order; the cap order, `cap` 200000,
  `handoff_at` 150000 and `handoff_wait` 1200 are unchanged, because a hand-over anywhere in 140-180k moves the cost by
  under 7%.
- **A repeat's unit is sized to end under `handoff_at`.** k = floor((handoff_at - start) / per-item), from the last
  measured run of the shape, with start = a unit's end context minus its items x per-item. Ingest, at 13k tokens a
  page and 197k at the end of a 9-page unit: start 80k, k = 5 pages, not 9 (4 if that unit had 8). The Size line of
  `example/launch.md` carries k. A builder that still gets an order to hand over inside a unit writes
  `Unit size: <k> -> <k-1>` in its record and note, and the later units take the smaller size. Smaller units are more
  units (40 pages: 8, not 5), each checked as before.
- **The verifier checks what is new per commit, what repeats in pairs, and a replay once.** `Repeat units:` in
  `example/verifier-assignment.md` names the repeats. Two repeat units get one pass at the later commit and a section
  each; an odd last unit goes alone; a unit that changes the driver and every `V<n>: fixed` commit go alone; a driver is
  replayed in a clone once per driver, at its first unit; a run of repeats runs the full suites once, at its end. A plan
  run keeps its milestones.
- **A facts pack replaces reading a tool's documentation.** The manager writes `_inputs/<topic>.md` before the launch
  (a few KB: each tool fact the run needs, with its source line) and the briefs name it. A session reads the pack at its
  start, opens a tool's documentation only for a fact the pack lacks, by line ranges, once, and reads a JSON answer
  through a filter, never whole. Rule 1 of `example/first-pass-rules.md` holds: each fact keeps its source. The pack and
  a hand-over note are sized so a fresh session starts under about 60k tokens; a builder of this run that read its
  whole note, its brief and the spec's sections was near 150k before its first edit.
- **One row per run.** `score_run.py <run-dir>` ends its output with `| units | cost per unit | sessions per unit |
  copies per unit | findings per unit | escaped |` (`--json`: `economy`). Copies are the `cap` and `unit end` lines of
  `_watch.log`, else of `_control/watch.out`; escaped are the M, J and O ids of `findings_report.py`, the findings that
  got past the verifier; a cell is `n/a` for a missing source, a partial cost or no unit. The ingest run's row is
  `5 | $8.60 | 4.6 | 1.8 | 1.0 | 0`; the next run is expected to show copies 0, a lower cost per unit and escaped 0,
  and a fall in findings per unit is explained on its measurement page.

Quality is guarded, not traded: every unit is still checked (a pair's findings come at its later commit, before the
merge), each pack fact carries its source, and escaped is the number that must stay 0. The cost of one copy is not
measured; the row settles it.

## Record and source
- [The spec, R1-R4 and the Measurement](../../specs/003-pipeline-economy/spec.md)
- The skill's files, `.claude/skills/running-specagent-pipelines/`: `example/handoff-rule.md:10`,
  `example/agents.json:24`, `scripts/watch_agents.py:228,589,1095-1122`, `scripts/docs/watch_agents.md:69-72`,
  `references/context-and-cost.md:9-27`, `example/launch.md:11`, `example/common.md:120-124`,
  `example/verifier-assignment.md:5,32-35`, `example/first-pass-rules.md:22`, `SKILL.md:73`,
  `scripts/manager/score_run.py:312`, `references/measuring.md:61-64`
- Unit 1 of the pipeline-economy run: commit 02179f6 (the unit-end grace) and the unit's second commit (the other rules
  and the economy row)
