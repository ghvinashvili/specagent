# Measuring the pipeline
Read-only scripts for the main session (usage and options on each script's page under `scripts/docs/`, indexed in
`scripts/README.md`); none runs a model, and they may run while the pipeline works.
- Records: `scripts/check_formats.py <run-dir>` before trusting a run's numbers and after a brief changes. The waiters
  and the watcher parse those lines; a reused id, an answer to an undefined id or a done line with a wrong sha answers
  or opens nothing, silently. Exit 1 lists the errors.
- Gates: `scripts/findings_report.py <run-dir>` counts the findings per kind, cause, severity and task; its escape
  table names the stage that caught each defect, and `J + O` is what got past the critic, the builder and the
  verifier. Measured 2026-10-26 on three earlier runs: 13 of 519 (the judge's), 0 of 491, 6 of 242 (the owner's,
  after the build); the critic caught 71–78% of all, the verifier 12–19%.
- Cost: `scripts/usage_report.py --prefix <run>/ --since <date>` per agent, and `scripts/startup_report.py --prefix
  <run>/ --since <date>` for the start-up cost, the context of a session's first write. Measured 2026-10-26 over the
  sessions since 2026-10-22: the median start-up was 113–137k per pipeline, and 1,026 of 1,064 fresh sessions started
  over 60k; the costliest reached the cap before their first write. A resumed session's transcript repeats the one it
  resumes, and usage figures from before 2026-10-26 counted those calls twice.
- Budget: the watcher's `budget` (3,000 calls or 40,000,000 output tokens per session by default, counted over the whole transcript: a session now
  lives through its compactions and its waiter calls, about 17 an hour) returns with exit 3
  when a session passes it, so a runaway session is seen; at the check of 2026-10-26 the busiest live session had made
  109 calls.
- Lessons: `scripts/audit_read_first.py <run-dir>` before compacting lessons.md's "Read first": it flags marker
  words, done work, near-duplicates and items over 7 days old, to review, not to drop, and prints a compacted section
  with the flags marked. It never edits.
- Replay: `scripts/replay_cases.py <run-dir> --repo <checkout> --out <dir> --try` turns findings into eval cases (the
  finding's command at the commit before the fix, and at the fix). A finding replays only when its record holds a
  read-only command and that command's literal output: of an earlier run's 99 V findings, 2 became cases and 1 replays.
- Disk: background jobs keep a `tmp` folder under `~/.claude/jobs/<id>/` after they end; an earlier run's filled
  about 90 GB, and 58 GB were freed on 2026-10-25. `scripts/clean_jobs_tmp.py` lists the `tmp` folders of finished
  jobs and removes them with `--apply` (the one script here that deletes).

### The owner's surface
- `scripts/manager/surface.py <run-dir>` renders the run's state in fixed phrases with the numbers inserted (answer
  11a): one line for the run (its cost from `scripts/usage_report.py` against the `$` amount of the `Budget:` line of
  `_launch.md`), one per role of the registry its config names (state, unit and how long on it, context, cost, what it
  waits for, the record path), the newest reading of `_control/usage.json` with the next reset, the hand-over orders
  past the cap, the free disk and the open alarms of `_control/monitor.json`. The registry is the `registry` field of
  `--config` (default `_control/_agents.json`), else `_control/registry.json`, as the watcher reads it.
- The manager spends no tokens on it: its status answer is two or three short lines, "now: …, next: …", whose
  figures it copies from the output as printed (no figure of its own), the whole output only when the owner asks for
  the costs; it keeps `_control/surface.txt` fresh with `--out` and `--every 120` in the background, re-armed on each
  exit.
- Phrases: `example/surface-phrases.en.json` holds the English words; the owner's own file keeps every key and
  every `{field}`, lives outside the template and is passed with `--phrases`; `--check-phrases FILE` checks it.
- A role's cost is the watcher's figure in the registry; the run's cost is the total row of `scripts/usage_report.py`
  for the run's prefix, which also counts the manager's helpers, so the roles need not add up to the run.

### After every run, in this order
The main session measures the run and itself before any page or summary cites a number (spec 5.6). The scripts are
the ones above, run in this order:
1. `scripts/check_formats.py <run-dir>`: no number of the run is trusted while it lists an error.
2. `scripts/findings_report.py <run-dir>`: the findings per kind and the escape table.
3. `scripts/usage_report.py --prefix <run>/ --since <date>`: calls, cost and the dollars of the cache reads, cache
   writes and output per role (the cache is measured in money, not tokens), once the date of its price table is
   checked against the provider's prices of the day.
4. `scripts/startup_report.py --prefix <run>/ --since <date> --threshold 60000`: the first-write context per session.
5. The manager itself, from its own transcript (`~/.claude/projects/<project>/<session id>.jsonl`), with
   `scripts/manager/measure_manager.py`: `first-call <transcript>...` (under 30,000 tokens, on three starts in a row),
   `calls <transcript> --handoff-dir <container>/docs/handoff` (no call over 200,000 tokens, and a hand-off written
   before each compaction), `reads <transcript> decisions/global/manager-lessons.md` (the lessons page read in one of
   the first five calls) and `lessons <vault>/decisions/global/manager-lessons.md --since <the run's first day>` (the
   items added, the items fired again with their counts, the recurrences).
6. `scripts/manager/measure_manager.py checklist <run>/critique.md <run>/verify.md`: the findings per `Checklist:`
   item, highest first; an item that two findings cite is a shared cause, promoted by hand to a rule (spec 7.6).
7. `scripts/manager/score_run.py <run-dir> --prefix <run>/ --since <date>`: the last row of its output is the economy
   row (`| units | cost per unit | cache write $ per unit | sessions per unit | copies per unit | findings per unit | escaped |`;
   `--json`: `economy`); the role table above it splits each role's cost into its cache read, cache write and output
   dollars. The row goes on the run's measurement page beside the last run of the same shape: the ingest run (40
   pages) is `5 | $8.60 | 4.6 | 1.8 | 1.0 | 0` (taken before the cache write column). After the economy run expect
   copies 0, a lower cost per unit and escaped 0; a fall in findings per unit is explained on that page. A cell is
   `n/a` when its source is missing (the transcripts for the cost and the cache write, `_watch.log` or
   `_control/watch.out` for the copies).
8. Every number, with the command that produced it, goes into `<vault>/context/measurements/<date>-<run>.md`, committed
   before the owner's summary or any page cites it; `ops/check_pages.py` runs in the vault after every commit and
   prints 0 problems.
9. A page that cites an owner statement was written after it: compare the statement's first commit
   (`git log --format=%ct -- context/owner-statements/<date>.md`, its last line) with the commit that adds the citation
   (`git log -S 'owner-statements/<date>.md' --format=%ct -- <page>`, its last line), not with the page's first commit.
10. A rule this run proves right is proposed with this measurement page as its proof (or the record of the found
    mistake); it enters `decisions/global/` on the owner's yes (`docs/roles/manager-chat.md`, `## After a run`, step 4).
