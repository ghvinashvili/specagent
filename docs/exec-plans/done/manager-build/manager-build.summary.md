# manager-build: summary for the owner

What gets built: the manager of SpecAgent from the spec of 2026-10-29 (sections 3-10): a measured catalogue and the rules
for choosing roles, skills and ECC texts; a watcher that reloads briefs, keeps a registry, requires an `ACK` line for
every order and hands over at a unit's end; a monitor for the request lines and the claims, with the duty list; the
owner's STATUS surface by script; a pre-flight for every launch (settings simulated, formats, disk, usage, timeouts, the
five-hour window); the garbage collector that checks before it deletes; the forms of the manager-lessons page and the
learning records, and the manager's own start-up measurement; the evals for the lesson classes of 2026-10-29 with CI; the
tracker rows closed; release 1.5.0.

Order: eleven tasks, four planner lanes writing them at once, two builders on disjoint files (A: catalogue, pre-flight,
surface, forms, tracker, release; B: watcher, monitor, collector, evals, the scripts README), one verifier, a judge at
the end with your yes. Milestones after Tasks 1-4, after 5-10, after 11.

How it is checked: tests written in the plan and run red first; the verifier re-runs every task and the acceptance
checks of spec section 10; the full suites at the milestones; no letter of a refused block, no model named, nothing generated
committed.

What you do once: the owner's phrase file for the surface (outside the template), the manager-lessons page in your
vault from the form, the yes for the judge, the yes for the collector's first three runs.

Tasks written (one line each, added by the planner of the task):
- Task 1 (builder A, no dependency, milestone M1): the catalogue and the brief forms. `scripts/manager/catalogue.py`
  measures every agent file, contract, example brief, skill (whole and by its description line) and pinned ECC text in
  bytes and tokens, checks a role's start-up prefix against the 10k and 13k bounds and checks every brief's domain
  section; the selection rules of spec 4 become one reference page of the skill; the plan fixer and the translator
  become role types. Every example brief ends with a `Spec:` line (the ECC lines pasted at launch, under 60) and a
  `Skills:` line, every critic and verifier finding cites `Checklist: <file>:<line>`, and no text of the skill names a
  model: it moves into each role's settings file. TD-006 closed. 67 new tests (51 catalogue, 12 role types, 4 brief
  forms; 201 in the skill's suite), the catalogue's 19 wrong versions and the forms' 5 run red once. Checks 10.9 (the
  `Skills:` lines), 10.15 (in part), 10.17.
- Task 2 (builder B, no dependency, milestone M1): the watcher, version 3. A changed brief no longer stops it: the
  sessions whose texts name the brief are stopped and resumed with a reload order. Each agent's session is found by the
  id recorded at its launch (a rename or a namesake cannot take its place; two live copies stop the watcher). Every
  order ends with an Order line and waits for an `ACK <msg_id>` line in the role's record file, resent by stop and
  resume at most twice; past 150k tokens a session is told to hand over only when its unit ends. The registry
  `_control/registry.json` keeps each role's state, lane, settings, sessions, cost and open orders, so a restarted
  watcher loses nothing; the manager gives its orders with `--order`. 35 new tests against a fake `claude` (181 in the
  skill's suite), every wrong version run red once. Checks 10.5 (first clause), 10.8 (first two clauses), 10.15, 10.20.
- Task 3 (builder B, after Task 2, milestone M1): the record monitor `monitor_records.py` (`watch`, `once`, `answer`,
  `report`, `status`) watches the request lines of the record files, raises the alarm when a task is claimed twice within
  one interval and says whether it is still armed; the duty list `duty_list.py` (`extract` from the plan index, `tick`);
  `check_formats.py` also checks requests against their time bound, a sha on every `Merged:` line, no bare `grep -c`
  waiter and the duty ticks. 46 tests (7 duty list, 8 added to the 14 kept for `check_formats.py`, 17 monitor), every
  wrong version run red once. Checks 10.7, 10.8 (third clause), 10.10, 10.11, 10.19.
- Task 4 (builder A, no dependency, after Task 1 in its lane, milestone M1): the pre-flight
  `scripts/manager/preflight.py` (`check`, `timeout`, `polls`, `clock`). `check` runs before a launch and checks
  the config and every settings file under `_control/`, no model outside the settings files, the blind deny rules, no
  deny on or above a path a role writes, a sandbox probe through `sim_bwrap.py`, each worktree, the waiters, the
  formats, the monitor's armed state, the disk, the usage reading against the five-hour and weekly limits, and the
  `_launch.md` table that you answer once, with one `Yes:` line per role (answer 6a). `timeout` sums a suite's
  timeout from its cases (175 minutes for the two suites today); `polls` and `clock` find `sleep` loops and times not
  taken from the clock in a run's record. `example/common.md` gains the ACK rule, the clock rule, two more request
  lines with their answers and the 15-minute bound. 36 new tests (237 in the skill's suite), 26 wrong versions run
  red once. Checks 10.12, 10.15 (the deny and model part), 10.16, 10.19, 10.20.
- Task 5 (builder D, after Tasks 1 and 2 through the merges `a->d` and `b->d`, milestone M2): the owner's surface
  `scripts/manager/surface.py` renders one line for the run (its cost, the total of `usage_report.py`, against the
  `Budget:` line of `_launch.md`), one per role from the watcher's registry (state, unit and how long on it, context,
  cost, what it waits for, the record path), the usage reading with the next reset, the hand-over orders, the free disk
  and the monitor's alarms, each a fixed phrase with the numbers inserted (answer 11a). The manager quotes it whole when
  you ask for the status, and `--every 120 --out` keeps `_control/surface.txt` fresh. The template ships the English
  phrases (`example/surface-phrases.en.json`); your own phrase file keeps the same keys and `{fields}`, stays
  outside the template and is passed with `--phrases` (`--check-phrases` checks it). One decision page. 28 new tests
  (174 in the skill's suite at ff3354a), 41 wrong versions run once, 40 red (the 41st is equivalent). Checks 10.6 and
  10.18.
- Task 6 (builder C, no dependency, milestone M2): the garbage collector `scripts/collect_run.py`. After a run it lists
  every deletion with what it loses (the run's worktrees and branches, `scratch/`, the job folders of its sessions, the
  copies you name) and removes nothing unless the save check passes: final records, every lesson marked
  `(skill: <sha>)` or `(skill: none)` with the commit merged, every done commit of the build logs in `main`, every
  Deferred item of the plan in the tracker, no unsaved work, no session still running. You say yes to the exact list
  (`--apply --yes <digest>`) for three runs; then the standing rule runs it and you read `collected.md` (answer 4). 17
  new tests (163 in the skill's suite at f70e84c), 41 wrong versions run once, all red. Checks 10.14.
- Task 7 (builder D, no dependency, after Task 5 in its lane, milestone M2): the manager's self-measurement
  `scripts/manager/measure_manager.py` (`first-call`, `calls`, `reads`, `lessons`, `checklist`): its first call against
  30,000 tokens on three starts and for both profiles (answer 5), every call against the 200,000 cap with a hand-off
  written before each compaction, the lessons page read in one of its first five calls, the page's form, size and
  recurrences, and the findings per `Checklist:` item. The vault form gains `forms/manager-lessons.md` (you copy it once
  to your vault's `decisions/global/manager-lessons.md`, a section per project: answer 3a) and
  `forms/learning-record.md`; `references/measuring.md` gets the order after every run; `docs/roles/manager-chat.md`
  describes the manager: the skill's main session (1a), no sandbox and four guards (2a), its duties by phase, its
  recovery and the collector's steps; four decision pages. 16 new tests (162 in the skill's suite at f70e84c), 34
  wrong versions of the script and 7 of the documents run red once. Checks 10.1, 10.2, 10.13; 10.3 and 10.4 over your
  vault at the run's end.
- Task 8 (builder C, no dependency, before Task 9 in its lane, milestone M2): evals and CI. Every lesson class of
  2026-10-29 gets a guard that runs on every push. Four code cases, with four checks in `evals/graders/pipeline_plan.py`,
  cover a `timeout` shorter than the suite's minutes, a sandbox deny on an ancestor of a written path, a hand-over note
  with pointers instead of facts, and a waiter not run as its brief gives it. The critic's baseline now holds the
  spelling a session wrote (graders are written from recorded outputs). A lint stops `harness eval` before any trial
  when a case names a stage or file that is gone, and the stale `access-probe-critic` is removed. The llm grader loads
  only local settings and refuses a grade that is not in English (TD-011). CI runs the tests and the gate
  (`harness eval --suite regression --baseline --threshold 1.0`, 19 cases, no session, no API key) on every push. The
  session cases run on your machine with `bash evals/nightly.sh` (threshold 1.0, timeout 125 min, cost cap $20 against
  a worst case of $18). 38 new tests; 63 wrong versions run red once. Once: add a cron line for `bash evals/nightly.sh`
  if you want it nightly.
- Task 9 (builder C, no dependency, after Tasks 6 and 8 in its lane, milestone M2): the tracker sweep. Bootstrap installs
  graphify's skill for Claude Code (`graphify install --platform claude`, TD-007; graphify adds its own four-line block
  to your `~/.claude/CLAUDE.md`). Where there is no user-level pipeline skill yet, bootstrap makes
  `~/.claude/skills/running-specagent-pipelines` a link to the checkout's. An existing link or copy is kept, and a copy
  is named in the log with the command that replaces it. `ops/new-project.py --container` makes `docs/handoff/` as
  `ops/container.py` does. The harness's module map moves to a page of its own, so `docs/architecture/harness.md` is
  11,241 bytes, under 12 KB (TD-009). TD-001 is closed as found implemented and TD-012 as found aligned, each pinned by
  tests. `just` in bootstrap is shown working and left unchanged. 9 new tests, 2 changed; 9 fail before the change, and
  23 wrong versions run once, all red. Check 10.19 for the bootstrap step. Deferred: graphify's project hook,
  `CLAUDE_CONFIG_DIR`, the harness's quality score (the release review's) and three modules missing from the map.
- Task 10 (builder B, after Tasks 1, 2, 3, 6 and 8 through the merges `a->b` and `c->b`, milestone M2): the skill's
  `scripts/README.md` (19,156 bytes at f70e84c, over the 12 KB rule: TD-008) becomes an index under 12,000 bytes; each
  script's section moves unchanged to its own page `scripts/docs/<stem>.md` (17 pages), built and compared by a check
  script so nothing is retyped. `usage_report.py` takes the list prices of 2026-10-29 from the official pricing page
  (its Sonnet and Haiku rows held older models' prices) and the Fable family, and prints the prices' date and page on
  its first line; the `total` line, whose figure your surface quotes, keeps its form and is pinned by a test (check
  10.18). 6 new tests; 16 wrong doc trees and 24 wrong versions of the script run red once. Haiku 5.5's prices for
  prompts over 100,000 tokens, fast mode and US-only inference are deferred.
- Task 11 (builder A, after every lane's merge, milestone M3): release 1.5.0, a MIGRATIONS entry a project's sync run
  takes as its brief; `harness validate` refuses all three blocks; the tracker holds every Deferred item;
  `SKILL.md` names the other lanes' tools; 13 decision pages; 16 new tests, the full suite once. Deferred: the vault
  test's one-block pattern (TD-020).
