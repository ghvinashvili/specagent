# The pipeline-fold run — measured 2026-10-30 14:4x UTC

Run folder: `agent-system-run/pipeline-fold-2026-10-30`. Spec: `docs/design-docs/pipeline-fold.md` (Decided 1-6); plan
`docs/exec-plans/active/pipeline-fold/` (seven tasks; Task 6, the measurement run, not built). Branch head 58c253d
(lane a, lane b and the plan branch merged; on `main` since 14:3x UTC). Launched 05:20Z (plan-fixer, critic, builder,
verifier; the owner's yes "gaushvi yvela taskze"), lane b 05:38Z ("ki daamate"), M1 07:19 UTC (b797afc), M2 11:01 UTC
(58c253d), watcher stopped 11:03 UTC, judge 13:26-14:23 UTC (the owner's yes "Ki" at 13:25). Task 1 was built by the
main session before the launch (84a5dad); the pipeline built Tasks 2-5 and 7. This run used the pre-fold watcher
(v3) and roles: it is the fold's build, not its measurement (that is Task 6).

## Score line (`score_run.py --prefix fold/ --since 2026-10-30`)
`score pipeline-fold-2026-10-30: tasks 7, findings C 43 A 20 R 13 V 12 (plan 2, missed 2), sessions 103 (cap 25, idle 11), cost $277.40, cache-read 98%`
Full result: `2026-10-30-pipeline-fold.score.json`. Baseline (manager-build, 2026-10-29): `tasks 11, C 32 A 13 R 8 V 9
(plan 5, missed 3), sessions 210 (cap 56, idle 3), $674.50`. Per built task: 17 sessions and $46 here against 19 and
$61 there; the two runs differ in plan, roles and lanes, so the pair is context, not the before/after of Task 6.
`cap` and `fresh` come from `_watch.log`, written after the run by joining `_control/watch.out` and
`_control/watch-judge.out` (judge J5: the start line now tees to it, 9db1a1a); `idle` counts sessions with no record line.

## Sessions and cost
| role | sessions | fresh | cap | idle | first call | cache read | cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| builder (lane a) | 15 | 5 | 5 | 1 | 32,488 | 98% | 41.27 |
| builder-b | 9 | 4 | 3 | 2 | 32,515 | 99% | 33.60 |
| critic | 26 | 16 | 3 | 1 | 32,438 | 98% | 74.13 |
| plan-fixer | 29 | 13 | 12 | 4 | 73,620 | 98% | 73.97 |
| verifier | 19 | 9 | 2 | 3 | 32,490 | 98% | 37.91 |
| judge | 5 | 4 | 0 | 0 | 31,915 | 98% | 16.01 |

`fresh` is the watcher's launches after a hand-over note, `cap` its hand-over orders at the context cap (25: the
fixer 12, the builders 8, the critic 3, the verifier 2).

Budget $250, spent $277.40 (111%); the judge was launched at 104% with the owner's yes. Sessions counted by the main
session as fresh sessions launched on an idle hand-over (every id closed, nothing to take): verifier 9, critic 16,
plan-fixer 13, 38 of 103; the watcher kept launching them until it was stopped at 11:03 (main-duties D42). This is
the waste Decided 5 removes (Task 2, built this run, not yet running). Each brief reload or order by the watcher was
one `--resume` copy session, counted here. The fixer: 29 sessions for 71 ids (C 43, A 20, B 6, plan-V 2), 13 of them
idle, about 4.4 ids per working session; one session (09:19-09:41) answered nothing at the cap until a reading-budget
section was added to its brief. The judge: one verdict in 5 sessions (4 hand-overs, 57 minutes).

## Findings (per task; cost by unit lines)
| task | C | A | R | V | V plan | missed | B | cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 0 | 5 | 5 | 1 | 1 | 0 | 22.55 |
| 2 | 6 | 7 | 2 | 1 | 1 | 1 | 2 | 2.65 |
| 3 | 5 | 2 | 0 | 2 | 0 | 0 | 2 | 0.00 |
| 4 | 8 | 4 | 3 | 3 | 0 | 0 | 1 | 11.17 |
| 5 | 5 | 2 | 2 | 1 | 0 | 0 | 2 | 12.01 |
| 6 | 7 | 2 | 0 | 0 | 0 | 0 | 0 | 0.12 |
| 7 | 9 | 3 | 1 | 0 | 0 | 0 | 1 | 0.12 |
| none | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 228.27 |

$228 of $277 sits in `none`: sessions that wrote no `Task N:` unit line (fixers, critics' coverage rounds, idle
sessions) are not attributed; the attribution rule is V5 / Review Focus 5, carried by Task 6 Step 0. Repeated lesson
classes (`Checklist:` citations): lessons.md:40 (C11, C12, C34, C41, C43), :41 (C8, C15, C23, C39), :60 (C1), :80
(C13), :39 (C14), :59 (C24), :11 (C37), :111 (R13). Judge J1: `score_run.py` counts a citation anywhere in a
section body, `measure_manager.py` only a line starting `Checklist:`; one rule is the fix.

## Merges and requests
19 `Merged:` lines in lessons.md: plan->a and plan->b after each fixer batch (22 markers in 12 lines), b->a five
times, a+b three times; the last, b->a at 58c253d (10:47 UTC), is M2's head. Two conflicts, both in wiki/index.md and
wiki/log.md (both lanes append): both sides kept. 4 CHECKOUT-REQUEST lines answered in 1-2 minutes; 4 detaches ahead
of a request (logged as "Main session: detached … ahead of a request"); no COPY-REQUEST, FF-REQUEST or SANDBOX line.
Two owner-dependent stops: the judge's yes (asked 11:1x, given 13:25) and `claude stop` of a session the classifier
refuses the main session (one retry succeeded after the owner's "Shen gaushvi").

## Lessons recorded this run (lessons.md "Lessons from this run": 34 lines)
By the main session: two lanes (files disjoint, `Merged:` lines before a dependent task); Task 6 is not a lane's
task; fixers answer one id at a time with a reading budget; a generator writes a record file only when it is missing
(make_run.py rewrote lessons.md at 09:43; 12 role lines restored from transcripts, 3 with approximate times). By the
roles: 12 lines (lessons.md:81-92), among them the fence-indentation class again (R13).

## The judge (fold/judge, 13:26-14:23 UTC; `judge.md`)
`VERDICT: release with conditions`; one major, four minors, "To check" empty, 63 lines "Checked and fine".
- J3 (major, plan): with two plan fixers the watcher splits queues by task parity and the brief by builder lane, so
  one fixer is relaunched over ids it may not answer. Fix before any run launches a second fixer: the brief's Lanes
  section by parity, one fixer owning the shared ids and B lines (or `open_ids.py --no-shared`), `fixer-b-log.md`, one
  test. One fixer (the default) is unaffected; the merge was not held.
- J4 (minor, plan): `<vault>/decisions/global/manager-lessons.md` did not exist — created 14:4x UTC from the form.
- J5 (minor, plan): no start line wrote `<run>/_watch.log`, so `fresh` and `cap` were `n/a`; the start lines in
  SKILL.md and example/README.md now tee to it (9db1a1a); this run's log was joined by hand and the score above
  re-read.
- J1 (minor, code): score_run's own `Checklist:` pattern (above) — one rule with measure_manager since ef16012.
  J2 (minor, plan): the plan's summary page still said six tasks by the main session with the full suites at every
  task — fixed on `main` 7cf7c43. J3: fixed on `main` 7b525fb (the brief by parity, `open_ids.py --no-shared`,
  `demand.shared`). After the owner's order of 15:0x (sessions close without them): the watcher stops final
  sessions, `final_stop_minutes` (9499e13; decision sessions-close-by-the-watcher).
- Not findings: D10 is not done while the spec orders the work "After D9 and D10" (the owner's 05:20Z yes covered the
  build; Task 6 states its order against D10); `docs/quality/SECURITY.md:25` lacks two hosts the example settings allow.

## What this run says for Task 6 and D10
- Fresh sessions on idle hand-overs were 37% of the sessions: Decided 5's `work_check` is the biggest single cut.
- The fixer's hand-overs are the next: 29 sessions for 71 ids. Decided 2 (the planner answers, the fixer on demand)
  targets exactly this queue.
- Judge hand-overs (4 of 5 sessions) and reload copies are costs the baseline did not separate; with `_watch.log`
  the score shows 25 cap orders, half of them the fixer's.
- The two owner-dependent stops cost about 2h10m of wall time; a standing yes for the judge inside an approved run
  and a `Bash(claude stop *)` permission rule remove them (proposed to the owner 13:2x, not decided).
