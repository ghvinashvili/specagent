# The pipeline's economy: the rules, their defaults and their measurement

Date: 2026-10-30. Status: ordered by the owner with its build (facts:18-28). Base `ce9d7af`. `S/` =
`.claude/skills/running-specagent-pipelines/`; `facts:N` = line N of `_inputs/facts.md` in the run folder
`runs/pipeline-economy-2026-10-30/`.

## Intent
Every later run costs less with no drop in quality: the obsidian-ingest run cost $43.01 against a $15-25 estimate
(F1-F4). Each rule sets a default with its saving and its quality guard; `score_run.py` prints one economy row per
run, which proves the effect against the last run of the same shape.

## Facts
- F1. The measured run: 40 pages, 5 units, $43.01: builder 14 sessions, 495 calls, average context 127k, $21.03;
  verifier 9 sessions, 333 calls, 102k, $21.98; estimate $15-25 by feel (facts:3-5). Per session $1.50 and $2.44.
- F2. Orders: builder 4 `cap` at 205k-219k mid-unit, 3 `unit end` at 181k-197k just after `Task N: done`, before
  its own note; verifier 1 `cap` (206k), 1 `unit end` (155k); each order starts a copy: 9 (facts:6-9).
- F3. The builder's context: plugin documents read many times, JSON answers printed whole, the 660-line driver
  re-read each session; about 13k per page (facts:10-12).
- F4. The verifier replayed every unit and re-ran every check; V1, V4, V5 (design holes) came at Units 1 and 4-5,
  V2, V3 at Unit 1, none from a replay, none escaped to the merge gate (facts:13-14). Units: 5 pages and the driver,
  9, 9, 9, 8 (`_inputs/ingest-verify-summary.md:16-34`).
- F5. Skill: a hand-over anywhere in 140-180k moves cost under 7%, 120k costs more, "Do not tune the cap"
  (`S/references/context-and-cost.md:9-10`); startup 81k -> 50k saves about 15% of a run (:13); a hand-over costs
  1-1.5 USD (`S/references/choosing-roles-and-skills.md:27`).

## Rules

**R1. A session hands over by itself at its unit's end; the unit-end order waits a grace.**
- Default: `S/example/handoff-rule.md`, first line under `## When`: "Hand over yourself: at the unit's end write the
  note at once, in the same turn as the unit's done line; the watcher's order, and the copy it starts, is the
  exception, not the way." Watcher field `unit_end_grace` = 600 s (`S/example/agents.json`, `S/scripts/watch_agents.py`
  :1082 and its page; >= 0, 0 = today): the order
  waits until the new line 1 is that old; a note before then starts the fresh session as usual. Why 600 s: 5 rounds
  of `interval`, half of `handoff_wait`. `cap` 200000, `handoff_at` 150000, `handoff_wait` 1200 stay (facts:15-16):
  no gain within 140-180k (F5); a lower `handoff_at` adds orders and leaves F2's race.
- Saving: F2's 4 unit-end orders and copies -> 0, up to $4-6 at F5's price [NEEDS CLARIFICATION: a copy's cost is
  unmeasured; the economy row settles it].
- Guard: a session busy past the grace gets the order; the cap order is unchanged.
- Check: `uv run pytest -q S/scripts/tests/test_watch_agents.py -k grace` -> passed (new line 1 at 180k, a note at
  300 s: no order; no note by 600 s: one; grace 0: one at once); `grep -c '"unit_end_grace": 600'
  S/example/agents.json` and `grep -c 'exception, not the way' S/example/handoff-rule.md` -> 1 each.

**R2. A repeat's unit is sized to end under `handoff_at`.**
- Default: `S/references/context-and-cost.md`, the unit-size rule: k = floor((handoff_at - start) / per-item), from
  the last measured run of the shape; start = a unit's end context minus its items x per-item. Ingest: 9 -
  ceil((197k - 150k) / 13k) = 5 pages, not 9 [NEEDS CLARIFICATION: if 197k ended the 8-page unit, 4; the order rule
  corrects it]. `S/example/launch.md` Size line: "Size: <n> tasks, or <n> items in units of <k> (the unit-size
  rule); …". `S/example/common.md` "Context": "A repeat's unit size is your brief's; when an order to hand over
  reaches you in a unit, write `Unit size: <k> -> <k-1>` in your record and note; later units take the smaller size."
- Saving: F2's 4 mid-unit cap stops (each a stop, a copy and a restarted unit) -> 0; up to $4-6.
- Guard: each unit is checked as before (R3); 40 pages take 8 units, not 5.
- Check: `grep -c 'unit-size rule' S/example/launch.md S/references/context-and-cost.md` -> 1 each; `grep -c
  'Unit size: <k> -> <k-1>' S/example/common.md` -> 1.

**R3. The verifier checks new code and fixes per commit, a repeat in pairs, the full gate once.**
- Default: `S/example/verifier-assignment.md`, a line `Repeat units: <units, or none>` and a step after step 1:
  "Repeat units go in pairs: after the second one's done line, read both diffs, run the checks once at the later
  commit and write a `## Task N — <sha>` section for each; an odd last unit goes alone. A unit that changes the
  driver and every `V<n>: fixed` commit go alone. Replay a driver in a clone once per driver, at its first
  unit. A run of repeats runs the full suites once, at the end." Plan runs keep their milestones.
- Saving: Units 2-5 (F4) take 2 passes, not 4: about 2 of 9 sessions at $2.44, $5 of $43.01 (F1); 5 replays -> 1.
- Guard: repeat-unit findings (F4: V4, V5) come at the pair's later commit, before the merge; escaped stays 0.
- Check: on `S/example/verifier-assignment.md`, `grep -c 'Repeat units'` -> 2 or more, `grep -c 'once per driver'`
  -> 1.

**R4. A facts pack replaces reading a tool's documentation.**
- Default: the manager writes `_inputs/<topic>.md` before the launch (a few KB: each tool fact the run needs, with
  its source line); the briefs name it. `S/example/common.md` "Context": "Read the facts pack `_inputs/<topic>.md`
  your brief names at your start; open a tool's documentation only for a fact it lacks, by line ranges, once; read a
  JSON answer through a filter (`python3 -c`), never whole." Also `S/example/first-pass-rules.md` rule 4 (the start
  list), `S/SKILL.md` "## Briefs" (11,876 of 12,000 bytes, a test) and `S/references/context-and-cost.md` (why: F3).
- Saving: F3's re-reads; F5's startup lever (81k -> 50k, about 15% of a run).
- Guard: each pack fact carries its source (first-pass rule 1 holds); escaped stays 0; `first call` shows the start.
- Check: `grep -l '_inputs/<topic>.md' S/example/common.md S/example/first-pass-rules.md S/SKILL.md
  S/references/context-and-cost.md | wc -l` -> 4; `uv run pytest -q S/scripts/tests/test_skill_md.py` -> passed.

**R5. A launch's estimate comes from a measurement.**
- Default: `S/example/launch.md`: "Estimate: <n> roles, <k> fresh sessions per unit, <n>-<m> sessions; from
  `~/vault/context/measurements/<date>-<run>.md` (the last run of the same shape): $<a>-$<b> per session;
  $<low>-$<high> per unit, $<total> for the run". `S/scripts/manager/preflight.py` `ESTIMATE` (:48-53) adds
  ("measurement page", `measurements/\S+\.md`) and ("cost per session", `\$\d[\d.]*(?:-\$?\d[\d.]*)? per session`);
  `S/references/preflight-and-capacity.md:32-34` names both.
- Saving: none by itself; the owner's yes rests on a measured price, not a guess $18-28 short (F1). Guard: the
  line's other checks stay.
- Check: `uv run pytest -q S/scripts/tests/test_preflight.py -k measurement` -> passed: a launch file without the page
  fails (`Estimate: names no measurement page`), one with it passes, the example asks for both.

**R6. The model class follows the work; effort is never lowered.**
- Default: the rule stands in `S/references/choosing-roles-and-skills.md:24-26`, unchanged. `S/SKILL.md:19` drops
  `builder, ` from its fixed judgment list (the owner: the class by the work, facts:20-21) and keeps "Effort max for
  every role"; the `Model rule:` line of `S/example/launch.md` stays.
- Saving: [NEEDS CLARIFICATION: the classes' prices are the manager's, in no file]; read as cost per unit.
- Guard: escaped stays 0 per shape; a shape that lets one escape goes back to the judgment class.
- Check: on `S/SKILL.md`, `grep -c 'fixer, critic, builder'` -> 0, `grep -c 'fixer, critic, verifier, judge'` and
  `grep -c 'Effort max for every role'` -> 1 each; `git diff ce9d7af -- S/references/choosing-roles-and-skills.md` ->
  empty.

**R7. The night tick commits the renewal.**
- Default: `ops/night-tick.sh`: after `--refresh` exits 0, on `main`, when `git status --porcelain --
  wiki/meta/ledgers wiki/log.md wiki/hot.md` lists a change, `git commit -m "chore(wiki): renew the due sources
  (night tick)" -- <those paths>` (other staged changes stay out); on another branch or
  a failed commit, the log line `renewal not committed: <reason>`, and the fire goes on. `docs/loops/README.md:95`
  says so.
- Saving: no cost; no manual step, no dirty checkout that blocks a merge touching `wiki/log.md` (facts:31-32).
- Guard: the commit holds only those paths.
- Check: `uv run pytest -q packages/harness/tests/test_night_tick.py -k renewal` -> passed (on `main`: one commit,
  that message, only those paths, a staged other file left out; on a branch: no commit, the log line).

**R8. A finding's cause may be `(brief)`.**
- Default: `S/scripts/check_formats.py:61` `CAUSE` and `S/scripts/findings_report.py:34` `CAUSES` accept `brief`;
  `S/example/verifier-assignment.md`'s heading pattern and `S/scripts/docs/check_formats.md` add `(brief)` for a run
  without a planner. `S/SKILL.md` stays (its pipeline has a planner).
- Saving: none; such findings pass the format check (facts:33-34). Guard: the other causes read as before.
- Check: `uv run pytest -q S/scripts/tests/test_check_formats.py S/scripts/tests/test_findings_report.py -k brief`
  -> passed.

**R9. A lint answer without its counts is an error.**
- Default: `ops/obsidian-ingest.py:650`: an answer without `summary.category_counts` stops with a message naming it.
- Saving: none; it closes a silent pass (facts:35). Guard: plugin 3.0.1's answers pass as today.
- Check: `uv run pytest -q ops/tests/test_obsidian_ingest.py -k lint_answer` -> passed, not skipped (`core`
  replaced: `{}` and `{"summary": {}}` stop, `{"summary": {"category_counts": {}}}` passes); `grep -c
  'category_counts", {})' ops/obsidian-ingest.py` -> 0.

**R10. The supersede loop is a recorded to-check, not a fix.**
- Default: `docs/architecture/knowledge.md`, after the `--supersede` lines (:27-33): "To check (plugin): after a
  revert and `--supersede` two sources name each other in `supersedes`; the plugin checks only the id's form, so a
  tool that walks the chain must stop at an id it has seen."
- Saving, guard: none; the item is kept (facts:36-37). Check: `grep -c 'To check (plugin)'
  docs/architecture/knowledge.md` -> 1.

## Measurement
`S/scripts/manager/score_run.py <run-dir> --prefix <run>/` prints after its tables one row (`--json`: `economy`):
`| units | cost per unit | sessions per unit | copies per unit | findings per unit | escaped |`
- units: the score's numbered tasks; cost, sessions: its totals; copies: the `cap <agent> N tokens` and `unit end
  <agent> N tokens` lines of `_watch.log`; findings: C + A + R + V; escaped: the M, J and O ids of
  `findings_report.py` (past the verifier, the merge gate included); a missing source prints `n/a`.
- Baseline, the ingest run (F1-F4): 5 | $8.60 | 4.6 | 1.8 | 1.0 | 0. Expected next: copies 0 (R1, R2), cost per
  unit lower, escaped 0; a fall in findings per unit is explained on the measurement page.
- `S/references/measuring.md` "After every run": the row goes on the run's measurement page beside the last run
  of the shape; `S/scripts/manager/README.md` (11,988 of 12,000 bytes, a test): one sentence.
- Check: `uv run pytest -q S/scripts/tests/test_score_run.py -k economy` -> passed (one `cap` and one `unit end`
  line: copies 2).

## Out of scope
- The watcher's numbers (R1); startup packs (off: `S/references/context-and-cost.md:16-20`); model names and
  prices; `usage_report.py`; plan runs' checks.
- The plugin's supersede loop (R10); 45c2fcd's squash, the B13 lesson, the diagrams page's claims
  (`_inputs/ingest-verify-summary.md:53-61`): the main session's.
- A measuring run: the first run after the merge (grantsdaily) is read by the economy row.
