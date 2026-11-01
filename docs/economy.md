# Time and money

Where SpecAgent saves time and money, what its quality costs, and the runs that measured it. The README's
[How it saves time](../README.md#how-it-saves-time) and [Where it saves money](../README.md#where-it-saves-money) are
the short form; every number here names its source. The measurement pages are in a private vault and are cited by
name.

## How it saves time

**Each role starts as soon as its input is ready.** A waiter script polls once a minute and wakes its session, so
waiting costs no tokens; nothing starts on speculation: a builder waits for its task's coverage round ([scripts]).

**Nothing waits for you.** You say yes once, before the run, to the launch table
([decision](../wiki/decisions/the-launch-table-and-one-yes.md)); `AskUserQuestion` is denied, a dispute after round
three is decided by rule, and a doubtful item is held and logged ([why](WHY.md#nothing-waits-for-the-owner)). What a
stop for a human costs was measured: in pipeline-fold, two stops that waited for the owner took about 2 h 10 min of
wall time (`2026-10-30-pipeline-fold`).

**Work runs side by side.** Planner lanes take a task with a `Task N: started by <role>` line, two builders work on
disjoint files, and the verifier checks each commit while the next is built ([skill]). pipeline-fold ran two
builders, a critic, a plan fixer, a verifier and a judge as 103 sessions (`2026-10-30-pipeline-fold`).

**Fixes land at once, in place.** The builder fixes a `V<n>` with one commit as soon as it is filed: the ingest run's
fixes for V4 and V5 came 16 and 12 minutes after the unit commits before them (`1108d9b` 20:13Z, `e09a2c5` 20:29Z;
`d9e79e5` 20:37Z, `ce9d7af` 20:49Z; `git log ce9d7af`), with no stage end and no human dispatch between.

**No human restarts a session.** The watcher (`watch_agents.py`) hands a session over at the end of its unit or at the
cap and revives a stopped one ([scripts]): in the ingest run, 4 of the builder's 14 sessions were handed over at the
cap (`2026-10-30-obsidian-ingest`).

On 2026-10-30 the template's own build ran 8 tasks in 2 h 22 min and the ingest 5 units in 2 h 15 min (the table
below).

## Where it saves money

**Compaction, with a hand-over as the backstop.** Since 2026-11-01 a session compacts near 197k and keeps its lane's
pack in the system prompt (README "The cache and the context"); before, it did one unit and handed over, or at 200k
([hand-over rule][handoff]). Every call re-reads the whole conversation, so a read costs its size times the calls that
follow it: a session starts at 27k tokens (10k from the shared cache) and reaches 81k after ten calls, 84% of the growth
tool results ([cost]). Without the cap, calls grew to 500-740k tokens, three times the cost of a fresh session
(2026-10-15), and no cap costs twice as much; a 300k cap cost 15-25% more per task than 200k, measured over 269 sessions
(2026-10-26) ([cost], [hand-over rule][handoff]).
<!-- after the economy merge: hand-over 150k, facts pack (specs/003) -->

**A fresh session reads a note of facts, not the history.** The note is at most 40 lines; a note that only pointed at
the files made a session rebuild 35k tokens of state ([cost]), and the eval case `pipeline-handoff-carries-facts`
checks that a note holds facts ([evals]).

**Reading is on need.** The index first, one page by its link, a long page by ranges (`ops/outline.py`), never a
folder scan (`CLAUDE.md`); pages under 12 KB, plan tasks under 1,500 lines ([decision][small]). A start of 50k instead
of 81k saves about 15% of a run ([cost]).

**The cache carries the prefix.** `score_run.py` printed `cache-read 98%` for fold-task6 and for pipeline-fold, 98% to
99% per role (the two runs' pages); the eval case `cache-share-reader` checks that a stage's second session finds its
prompt cached ([evals]). An hour-long cache at max effort would have saved 14% on both measured sessions (ADR-0016),
and a startup pack (`make_pack.py`) raised the start from 30.7k to 42.4k tokens, so packs were off until 2026-11-01, when one frozen pack per lane went
into the system prompt, where it survives a compaction ([cost]). Since
2026-10-31 the cache is measured in dollars, not tokens, and its time to live is set per role (the last measurement
below).

**Mechanical work runs on the cheaper class.** Work that code or a verifier checks runs in the mechanical model class,
judgment in the judgment class, set per role in a settings file no role reads ([skill]); a run names its models only
in the launch table's message ([decision](../wiki/decisions/the-spec-writers-model-is-a-dated-exception.md)); the
ingest run's builder ran in the mechanical class (the table below).

## What quality costs

The cost of quality is a second session per unit and the records on disk. The verifier took $10.10 of fold-task6's
$35.57 (builder $23.27, plan fixer $2.19) and $21.98 of the ingest run's $43.01 (builder $21.03); in the ingest run
the builder made 495 calls over 14 sessions (average context 127k) and the verifier 333 over 9 (102k)
(`2026-10-30-template-surface`, `2026-10-30-obsidian-ingest`). The ingest run was estimated at $15-25 with a budget of
$40 and cost $43.01; its page names the two causes: the builder's cap hand-overs from reading the plugin's documents
and whole JSON answers, and the verifier's replay of every unit in a clone. Each run is scored the same way by
`score_run.py`: findings per task by kind, sessions and hand-overs per role, cost per task and per role
([decision][score]).

## The measurements

After every run the main session measures the run and itself from the records and transcripts, with the scripts of
[measuring] in their order (`check_formats.py`, `findings_report.py`, `usage_report.py`, `startup_report.py`,
`measure_manager.py`, `score_run.py`), and writes every number, with the command that produced it, into the private
vault's `context/measurements/<date>-<run>.md`, committed before any page or summary cites it: the pages this page
names are such pages.

### Two measured runs of 2026-10-30

What a real run of this system costs and takes: the two runs that the README's table shows, from
`2026-10-30-template-surface` and `2026-10-30-obsidian-ingest`:

| Run | Roles | Units | Sessions | Findings, all fixed | Cost | Wall clock |
| --- | --- | --- | --- | --- | --- | --- |
| fold-task6: the template's own build | builder, verifier, the plan fixer on demand | 8 tasks | 15 | 14 V | $35.57 | 15:09-17:31Z |
| obsidian-ingest: 40 decision pages through the plugin | builder (mechanical class), verifier | 5 | 23 | 5 V | $43.01 | 18:44-20:59Z |

A third run of the same day, pipeline-fold (`2026-10-30-pipeline-fold`), had a plan of 7 tasks, of which its sessions
built 5 (Task 1 was built before the launch, Task 6 not built), with two builders, a critic, a plan fixer, a verifier
and a judge: 103 sessions, $277.40; its critic filed 43 C findings and 20 A attack tests, its verifier 12 V findings.

[A subagent vs a SpecAgent role session](comparison.md) reads these numbers against the subagent model.

### The cache in dollars, 2026-10-31

A cache is cheap per token and still most of a bill, so `usage_report.py` and `score_run.py` print cache reads, cache
writes and output as dollars beside the token counts (one usage per message id), and the economy row of `score_run.py`
has a "cache write $ per unit" column after "cost per unit" ([measuring]). The measurement of 2026-10-31 is from the
transcripts of the readme run and the consolidation run, counted with one usage per message id; its method and commands
are on the private vault's page `context/measurements/2026-10-31-cache-ttl.md`:

- The readme writer's $129.61 is cache reads 31%, cache writes 29% and output 40%.
- A fresh session's first call reads at least the 20,452 tokens of the shared prefix and writes about 14k.
- At 5m instead of 1h a cache write costs 37.5% less, so the saving is at most 37.5% of a role's write dollars, less the
  rewrites after gaps of 5 to 60 minutes:

| Session | Net at 5m instead of 1h | Gaps of 5 to 60 minutes | Calls |
| --- | --- | --- | --- |
| readme writer | +$13.49 | 1 | 1,697 |
| consolidation builder | +$3.07 | 0 | 659 |
| readme verifier | +$2.79 | 13 | 1,265 |
| consolidation verifier | +$2.99 | 4 | 633 |

So in a SpecAgent role session launched with the skill's example settings ([launch]), the `env` sets
`CLAUDE_CODE_PROMPT_CACHE_TTL`: `5m` for every role since 2026-11-01, the waiters returning within 3.5 minutes (the
1-hour TTL cost $59.51 more in writes against $26.91 saved on one run); the harness's stage types keep the hour that
`docs/roles/need-to-know.yaml` sets (ADR-0016). A launch prompt names what is byte-identical across a role's sessions
first (the brief, the hand-over rule, the "Read first" section of `lessons.md`, the facts pack) and the hand-over note
last, because a cached prefix is only as long as what is identical ([cost]); `make_pack.py --no-note` leaves the note
out of a pack. Packs stay off until a run measures one in dollars.

[cost]: ../.claude/skills/running-specagent-pipelines/references/context-and-cost.md
[launch]: ../.claude/skills/running-specagent-pipelines/references/launch.md
[evals]: ../evals/README.md
[measuring]: ../.claude/skills/running-specagent-pipelines/references/measuring.md
[handoff]: ../.claude/skills/running-specagent-pipelines/example/handoff-rule.md
[score]: ../wiki/decisions/one-score-per-run-by-script.md
[scripts]: ../.claude/skills/running-specagent-pipelines/scripts/README.md
[skill]: ../.claude/skills/running-specagent-pipelines/SKILL.md
[small]: ../wiki/decisions/what-an-agent-reads-is-small-and-layered.md
