# Stage patterns

The orchestration patterns of dynamic workflows, written as stage tables instead of workflow scripts. A workflow's
`agent()` call starts a subagent; here every agent is a session, so a pattern is a shape of `docs/roles/stages.yaml`
or of a file under `docs/roles/pipelines/`. Pick the pattern by the failure it prevents: drift needs fan-out,
self-preference needs adversarial verification, an open end needs loop-until-done, hard-to-score work needs comparison.

| Pattern | Stage form | Harness mechanism | Where | What does not transfer |
| --- | --- | --- | --- | --- |
| Classify-and-act | a `print` stage of `classifier` returns `label`; `routes` maps labels to pipelines | `harness route`; the manager starts the routed pipeline as a new run after the human confirmed its brief | `pipelines/intake.yaml` | branching inside one run: a run is one table; the action is another run |
| Fan-out-and-synthesize | a planner stage writes `tasks.json`; a `parallel: per_task` stage; a `synthesizer` stage | `launch.split_tasks`: dependency components become shards, at most `max_shards`; the stage is done when every shard passed its gate | `pipelines/research.yaml`, `pipelines/council.yaml`, `pipelines/software-factory.yaml` (`write`) | hundreds of agents (a shard is a full session) and streaming hand-over between agents (a barrier per stage only) |
| Adversarial verification | a checking stage of another role type that receives the artifact and the rubric, never the maker's conversation | separate sessions; `parallel_with`; a gate per stage | `stages.yaml` (`attack`, `verify`, `judge`), `pipelines/software-factory.yaml`, `pipelines/learning.yaml` | — |
| Evaluator-optimizer loop | a reviewer with `returns_to` sends proven findings back to the stage that made the work, within the table's `loop` bounds | `harness/rounds.py` under the lock of `state.json`; `harness resume --rework` | `stages.yaml`, `pipelines/fix.yaml` (`attack` → `plan`, `verify` and `judge` → `write`) | a loop over shards: `harness validate` refuses it |
| Generate-and-filter | one task per candidate in `tasks.json`; a `comparator` stage ranks; the judge or the human decides | `per_task` shards; the `ranking` block of `result.json` | `pipelines/council.yaml` (`advise`, `review`) | — |
| Tournament | one `comparator` call compares all candidates and returns `ranking.order` | the same as generate-and-filter | `pipelines/council.yaml` (`review`) | a pairwise bracket kept in deterministic code: not built |
| Loop-until-done | a unit is resumed with the failing checks until its gate passes or `max_attempts`; across runs, a loop file | `harness poll` (`resume` action), `harness loop tick` | every table; `docs/loops/` | a loop without a limit |
| Quarantine | `quarantine-reader` (the `Read` tool only, `print`, schema output); later stages receive the digest path | `harness inbox`, `.claude/hooks/guard-inbox.py`, `--strict-mcp-config`, `dontAsk` | `pipelines/intake.yaml` | text pasted into the manager's own conversation: the manager has seen it |
| Model routing | `model` and `effort` per stage row; the classifier runs on the smallest model | the manifest; `--model`, `--effort` | every table | choosing a model per item inside a stage |
| Explicit budget | `max_budget_usd` and `max_turns` on `print` stages; `max_minutes` on background stages | launcher flags; `harness poll` (`timeout`) | every table | a token budget for a background session: no flag exists; the OpenTelemetry cost alert is the signal |

## Combinations

| Work | Stages |
| --- | --- |
| Feature from request to pull request | research → story (human) → spec (human) → plan → write (shards) → accept and validate in parallel → judge (human) |
| Decision under uncertainty | frame → advise (five shards) → review → verdict (human) |
| Research briefing | frame → investigate (shards) → refute → synthesize (human) |
| Outside text | digest → classify → route to one of the above |
| Knowledge base upkeep | ingest → wikicheck |
| Improving the harness | analyze → challenge → judge (human) |
