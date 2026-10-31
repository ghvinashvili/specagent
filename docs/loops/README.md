# Loop layer

A loop is a declared, repeatable way to start work. It is a layer above the harness: the manager's instruction
names no goal, rubric, limit or schedule. One loop is one file, `docs/loops/<name>.yaml` (schema
`schemas/loop.schema.json`), and one state file outside the repository,
`<runs root>/_loops/<name>/state.json` (schema `schemas/loop-state.schema.json`).
A human changes a loop in a pull request; no session edits these files.

## Parts of a loop

| Part | Field | Enforced by |
| --- | --- | --- |
| Goal | `goal.statement`, `goal.done_when` | rendered into the brief of every iteration by `harness loop tick`; read from disk each time, never from a session's memory |
| Rubric | `rubric` | `evals/rubrics/<name>.md`, read by the checking stage of the loop's pipeline |
| Action | `action.kind`: `pipeline`, `command`, `prompt` or `ci` | a run of `docs/roles/pipelines/<name>.yaml`; a deterministic command; a prompt file run in the manager session; a GitHub workflow |
| Verifier | the gates of the pipeline, or the command's exit code | `harness gate`; the maker and the checker are different sessions |
| Exit rule | `exit.success`, `exit.failure`, `exit.check` | `harness loop tick` reads the last run's `state.json` and gate verdicts; for a `prompt` loop it checks `exit.check` at every tick (see Prompt loops) |
| Hard stops | `stops.max_iterations`, `stops.max_minutes`, `stops.max_usd`, `stops.no_progress_after` | `harness loop tick`, before anything starts; for a `prompt` loop too |
| State | `_loops/<name>/state.json` | written only by `harness loop`, one tick of a loop at a time: a tick holds the loop state's lock from its read to its write (`docs/decisions/0021-one-writer-at-a-time-for-run-and-loop-state.md`) |
| Trigger | `trigger.kind`, `trigger.schedule` | see Triggers |

An episode is the chain of iterations toward one goal: it starts at a trigger and ends at an exit rule or a hard stop.
`max_iterations`, `max_minutes` and `max_usd` are counted per episode. `max_usd` counts print stages only
(`state.json` `cost.print_total_usd`); background sessions are bounded by `max_minutes` and by the OpenTelemetry cost alert.

A context entry a tick cannot read, `runs:` followed by anything but a number of days or a path that names nothing in
the repository, is named by `harness loop validate`, and a tick prints `exit` with the rule `invalid` before anything
starts. A run the loop waits for whose folder is gone, or whose state cannot be read, counts as a failed iteration;
`runs:<days>` leaves out a run whose state cannot be read.

## Prompt loops
A `prompt` loop creates no run, so code judges it by what an iteration leaves on disk
(`docs/decisions/0022-a-prompt-loop-is-judged-by-code.md`):

| What | How |
| --- | --- |
| Success | `exit.check`, required for a prompt loop: a condition from a closed list, checked at every tick. `no_active_runs`: no run has the status created, running, waiting_human or paused. When it holds the tick prints `exit` with the rule `success`. |
| Progress | the sha256 of every readable run's id, status and `changed_at`, taken at the next tick; the same key `no_progress_after` times in a row ends the episode with `no_progress` |
| Spend | the `total_cost_usd` of the night path's sessions of the loop in this episode (`<runs root>/_audit/night-tick/<loop>-<UTC time>.json`); an iteration run in the open manager session leaves no cost the harness can read and counts nothing |

## The pause switch
While the human's pause switch is set (`harness pause set --reason "<words>"`, `docs/decisions/0023-one-pause-switch.md`),
`harness loop tick` prints `wait` with `paused` and leaves the loop state as it is, and `harness loop due` starts no
night session. `harness pause lift` lets the loops go on where they were.

## Levels

| Level | What repeats | It ends when | Where it lives |
| --- | --- | --- | --- |
| Agent loop | tool calls inside one session | the session ends its turn with a valid, final `result.json` | Claude Code; `.claude/hooks/stop-gate.py` |
| Verification loop | attempts of one unit | the gate passes, or `max_attempts` is reached | `harness poll`, `harness resume`, `gates/<stage>.py` |
| Event loop | iterations started by a trigger | an exit rule or a hard stop of the loop file | this layer: `harness loop tick` |
| Hill-climbing loop | changes to instructions, skills, gates and evals | a human merges or rejects the pull request | `docs/quality/LEARNING.md`, loop `learning-review` |
| Supervision loop | which loops exist, their goals and budgets | never; it has no end condition | humans: `enabled`, `stops`, `owner` in the loop file; `docs/roles/HUMAN.md` |

Fan-out is not a loop. It is a topology inside a stage (`parallel: per_task`), usable at every level.

## Readiness: four conditions
`harness loop validate` refuses a loop whose `readiness` has a condition with `met: false` or without evidence.

| Condition | Meaning |
| --- | --- |
| `repeats_weekly` | the task comes back at least once a week |
| `verification_is_automatic` | a test, a build, a linter, a schema or a rubric decides, not a person |
| `budget_tolerates_waste` | a failed iteration costs less than the limit in `stops` |
| `agent_can_run_the_check` | the session has the tools to run the check itself |

Order of building: a manual run that is reliable, then a skill, then a loop, then a schedule.

## Minimal loop
One trigger, one action (a pipeline or a command), one state file, one gate. `context-audit.yaml` is the smallest example.

## Silent failures and what detects them

| Failure | Detector |
| --- | --- |
| No real verifier | `harness loop validate`: a pipeline action must name at least two role types; a command action is its own check |
| Soft completion | an iteration succeeds only when every gate verdict is `pass`; a session's claim is not read |
| No hard stop | the schema requires `max_iterations`, `max_minutes` and `no_progress_after` |
| Goal drift | the goal is rendered from the loop file into each brief; every iteration is a new run with new sessions |
| Self-preferential bias | verifying and judging stages are other role types than the making stage |
| Agentic laziness | gates count `passes` flags in `tasks.json`; nothing is "handled" without evidence |
| Repeating the same iteration | `no_progress_after`: the same progress key (stage statuses and failing checks; for a prompt loop the runs' statuses and `changed_at`) that many times in a row ends the episode with `no_progress` |
| A night session with nothing to do | `harness loop due` before every fire of `ops/night-tick.sh`: no open run, every unit still working, or the pause switch set, and no session starts |
| Context rot | state is on disk; no session lives across iterations |

Lessons are not kept in loop state. A lesson becomes a rule, a skill line or an eval case through the learning loop.
Where a rule lives, by who must obey it, is the ladder in the pipeline skill's `SKILL.md` ("Briefs").

## Triggers

| Trigger | Starts | Survives | Used here |
| --- | --- | --- | --- |
| `manual` | `/loop-tick <name>` typed in the manager session | nothing to survive | every loop |
| `session` | `/loop <interval> /loop-tick <name>` in the manager session | the session; expires after 7 days; restored on `--resume` | `poll` |
| `local-cron` | `ops/night-tick.sh <name>` from the operator's scheduler: `harness loop due` decides without a model and without a tick (for `wiki-ingest` after `ops/obsidian-ingest.py --refresh` has renewed the wiki's sources, pause or no pause, and, on `main`, committed the renewal: one `chore(wiki): renew the due sources (night tick)` commit of the ledgers, `wiki/log.md` and `wiki/hot.md`; on another branch or when git refuses, the log says `renewal not committed: <reason>`); only when it finds work, a new headless manager session, told a prompt loop's file (which ticks by itself) or `/loop-tick <name>`, so one fire ticks once | reboots; needs the machine on | `wiki-ingest`, `learning-review`, night polling |
| `ci-cron` | `.github/workflows/loops.yml`, `.github/workflows/doc-gardening.yml` | independent of any machine; sees the repository only, never the runs root | `context-audit`, `wiki-lint`, `doc-gardening` |
| Desktop scheduled task | a new local session per run, with its own permission mode | restarts of the terminal; needs the app open and the machine awake | not configured by this repository |
| Cloud routine | a cloud session on a fresh clone | everything local being off | not used: it cannot read `<runs root>/` |
| Repository event | GitHub Actions `on: pull_request` | — | `ci.yml`, `evals.yml`, `claude-review.yml` |

`/batch` is not a trigger here: it spawns background subagents, and the `Agent` tool is denied. Parallel work is `parallel: per_task`.

## Catalog

| Loop | Kind | Trigger | Action | Checked by | Ends when |
| --- | --- | --- | --- | --- | --- |
| `poll` | operations | session, 5 minutes; local-cron at night | prompt `.claude/loop.md` | `harness poll` output | no run is active |
| `doc-gardening` | maintenance | ci-cron, weekly | CI workflow `doc-gardening.yml` | `harness docs-check` | the check is clean or a fix-up pull request is open |
| `wiki-lint` | maintenance | ci-cron, weekly | command `harness wiki-lint` | exit code | exit code 0 |
| `context-audit` | maintenance | ci-cron, weekly; every pull request | command `harness audit --ci` | exit code | exit code 0 |
| `wiki-ingest` | distillation | local-cron, nightly | pipeline `wiki-ingest` | gates `ingest`, `wikicheck` | both gates pass |
| `learning-review` | distillation | local-cron, weekly | pipeline `learning` | gates `analyze`, `challenge`, `judge`; human approval | the judge's verdict is approved or rejected by a human |

Not in the catalog: loops over services this repository has no connection to (pull request babysitting, issue triage,
chat feedback, deploy watching, morning reports). Adding one means one file here with readiness evidence.
