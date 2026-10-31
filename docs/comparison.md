# A subagent vs a SpecAgent role session

SpecAgent is for hard work: many packages, many days, many roles. Inside that scope the table below holds in every
row, and each row links its evidence. Outside it, a subagent is the better tool: a short lookup inside one turn, with
nothing to record and nothing to resume, costs one call and no files.

Running several Claude Code sessions side by side is not new: tmux scripts and CLI parallelizers hand each session a
task and collect the result. SpecAgent takes the parallel-subagent idea the coding agents use and replaces the subagents
with full sessions, each with its own context, worktree, sandbox, transcript and hand-over note. What it adds is the
loop around those sessions: a manager chat, roles with briefs, gates in code, proof for every finding, one unit per
session with a hand-over, records on disk a human reads, the watcher, measurement per role, a private vault, and checks
in code before a page goes to a public commons (the commons repository itself is not built yet). The claim is that
combination, each part with its evidence; [How it works, step by step](how-it-works.md) shows the loop and
[Time and money](economy.md) its cost.

## The table

| Property | A subagent (the Agent tool) | A SpecAgent role session | Evidence |
| --- | --- | --- | --- |
| Context | a slice of the parent's window | its own window, one unit per session, a fresh session at the 200k cap | [hand-over rule][handoff] |
| Memory after the call | gone; its result is pasted into the parent | a transcript, a hand-over note and a record file | [how it works](how-it-works.md#7-a-session-hands-over) |
| Observability | internal to the parent's session | `build-log.md`, `verify.md`, `*.summary.md`, read while it works | [the files of a run](files-of-a-run.md) |
| Resumability | not from another session after a crash or a limit | `claude --resume <id>`; the watcher revives a stopped session from its files | [ADR-0001][a1], [scripts] |
| Isolation | the parent's tree and permissions | its own worktree, sandbox and settings; protected paths; requests answered by the manager | [decision][sandbox] |
| Verification | the parent trusts the output | a verifier in its own worktree, a repro per finding, 3 rounds then a rule, a judge once | [skill] |
| Tests | text the parent must test | the builder writes the failing test first and logs `N passed, M failed`; the verifier re-runs it | [measured](#the-measured-numbers) |
| Feedback loop | its result ends at the parent; peers do not talk | every plan-caused finding goes back to the planner, who fixes that task and every later one | [measured](#the-measured-numbers), [skill][skill] |
| Cycles to a product | its result is re-dispatched by the parent until it fits | one run, findings fixed inside it by the role that owns them | [measured](#the-measured-numbers), [skill][skill] |
| Cost | lumped into the parent's bill | measured per role (`usage_report.py`) and per session (`score_run.py`) | [decision][score] |
| Cache | its context is built anew for each call | its cached prefix is read call after call: 98% cache read | [measured](#the-measured-numbers) |
| Parallelism | inside the parent's session; every result lands in the parent's window | sessions side by side for hours, each in its own window: two builders, a critic, a verifier | [measured](#the-measured-numbers) |
| Failure | the parent's turn fails with it | the watcher hands over or revives; the records survive | [measured](#the-measured-numbers) |
| Scale | bounded by the parent's context | any number of sessions: 103 in one run | [measured](#the-measured-numbers) |
| Knowledge | none kept | decisions written with the work, a private vault; a page goes to a public commons only past checks in code (the commons repository itself is not built yet) | [decision][with-work], [decision][kb] |

## What a subagent cannot do, and a role session can

- Be read while it works: `tail -f <run>/build-log.md`.
- Be stopped, resumed or continued by its id: `claude stop <id>`, `claude --resume <id>`.
- Survive its parent: its transcript, note and commits remain when the manager chat is gone.
- Be checked by a peer in another worktree, with a repro for every finding.
- Hand over to a fresh session with a note of facts and keep going for hours.
- Be measured per role, with its own cost estimate in the launch table ([decision][launch]):
  `usage_report.py --prefix <run>/`.
- Be given its own sandbox and its own plugin set: the harness writes each role type's settings with only its plugins
  enabled ([access.py][access]).

## The measured numbers

All runs of 2026-10-30, from the measurement pages in a private vault (`2026-10-30-template-surface`,
`2026-10-30-obsidian-ingest`, `2026-10-30-pipeline-fold`, `2026-10-30-pipeline-economy`), and from this
repository's git history.

- **Cache.** `score_run.py` printed `cache-read 98%` for fold-task6 (the template's own build, 15 sessions) and for
  pipeline-fold (103 sessions); per role in pipeline-fold, 98% to 99%. A role session's prefix stays cached call after
  call, which is where the cost per call comes down.
- **Parallelism and scale.** pipeline-fold ran two builders on disjoint files (15 and 9 sessions), a critic (26), a plan
  fixer (29), a verifier (19) and a judge (5) side by side: 103 sessions, 5 tasks built, $277.40.
- **Feedback loop.** fold-task6 counted 14 V findings, all fixed: V1-V12 came from the pipeline-fold run, V13 and V14
  were its own; 3 were tagged `(plan)`, so they went to the plan fixer as well as the builder, and the plan fixer
  corrects that task and every later one.
- **Fixed at once.** The ingest run's commits read unit, fix, unit: Unit 4 at 20:13Z (`1108d9b`), V4's fix at 20:29Z
  (`e09a2c5`), Unit 5 at 20:37Z (`d9e79e5`), V5's fix at 20:49Z (`ce9d7af`) (`git log ce9d7af`, UTC). Nobody waited
  for a stage to end or for a human to dispatch the fix.
- **One cycle to a product.** The pipeline-economy run wrote its spec, built it, verified it and was merged (`cb60f5b`)
  in 3 h 12 min (21:14Z-00:26Z): 22 sessions, 1 finding, fixed test-first inside the run, 0 escaped to the gate; its
  milestone ran the whole suite (1,874 passed) and every lint. The ingest run built 5 units and fixed its 5 findings
  inside the run; its merge gate passed 1,840 tests. Neither run launched a judge.
- **Tests by the session itself.** The ingest run's 5 V findings were all fixed with tests and re-checked; the merge
  gate of 2026-10-30 passed 1,840 tests (`uv run pytest -q`).
- **Failure without loss.** In the ingest run, 4 of the builder's 14 sessions ended at the context cap; the watcher
  handed each over to a fresh session, and all 5 units were committed (`2026-10-30-obsidian-ingest`).
- **Cost per role.** fold-task6: builder $23.27, verifier $10.10, plan fixer $2.19, of $35.57; the ingest run: builder
  $21.03 over 14 sessions, verifier $21.98 over 9, of $43.01.

One earlier measurement is often read as sessions against subagents and is not: on one task (2026-10-02) the sessions
cost a twelfth of the subagents and passed more hidden checks, but wrote shallower documents. ADR-0006 traced the gap
to thin briefs against full ones, so a role session now gets every demand a subagent would get for the same job
([ADR-0006][a6]).

## The price

Roles coordinate by files and polling, and the manager cannot steer a role mid-turn ([ADR-0001][a1]). Each session
reads its brief and note before it works: the start costs tokens a subagent call does not pay (on
[Time and money](economy.md)). `.claude/settings.json` denies the Agent tool, and `harness validate` rejects a role
type that lists it.

[a1]: decisions/0001-role-chats-are-sessions.md
[a6]: decisions/0006-a-role-session-gets-what-a-subagent-would-get.md
[access]: ../packages/harness/src/harness/access.py
[handoff]: ../.claude/skills/running-specagent-pipelines/example/handoff-rule.md
[kb]: ../wiki/decisions/the-shared-knowledge-base.md
[launch]: ../wiki/decisions/the-launch-table-and-one-yes.md
[sandbox]: ../wiki/decisions/the-sandbox-sets-itself-up-and-a-refusal-is-reported.md
[score]: ../wiki/decisions/one-score-per-run-by-script.md
[scripts]: ../.claude/skills/running-specagent-pipelines/scripts/README.md
[skill]: ../.claude/skills/running-specagent-pipelines/SKILL.md
[with-work]: ../wiki/decisions/decisions-are-written-with-the-work.md
