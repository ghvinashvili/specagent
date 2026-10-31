# Observability

## Where the OpenTelemetry settings live
- Managed settings (`/etc/claude-code/managed-settings.json` in the dev container) or each developer's `~/.claude/settings.json`. The repository's `.claude/settings.json` cannot enable telemetry: exporter variables there are ignored.
- Variables: `CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_METRICS_EXPORTER=otlp`, `OTEL_LOGS_EXPORTER=otlp`, `OTEL_EXPORTER_OTLP_PROTOCOL`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_LOG_TOOL_DETAILS=1` (without it the names of this repository's agents are replaced with `"custom"` in `agent.name`; user-defined skill names appear verbatim in `skill.name` either way, only third-party plugin skills become `"third-party"`), `OTEL_RESOURCE_ATTRIBUTES`.

## What Claude Code exports
- Metrics: `claude_code.cost.usage` (attributes `model`, `agent.name`, `query_source`), `claude_code.token.usage` (`type`), `claude_code.session.count` (`start_type`), `claude_code.lines_of_code.count`, `claude_code.commit.count`, `claude_code.active_time.total`.
- Events: `user_prompt`, `assistant_response`, `tool_result`, `api_request`, `api_error`, `tool_decision`.

## What the harness exports
- Spans from `harness launch`/`resume`: `invoke_agent <type>` with `gen_ai.operation.name`, `gen_ai.agent.name`, `gen_ai.provider.name`, `gen_ai.request.model`, `harness.run_id`, `harness.stage`. Endpoint from `HARNESS_OTEL_ENDPOINT` (Claude Code does not pass `OTEL_*` to subprocesses): the full OTLP/HTTP traces URL, such as `http://localhost:4318/v1/traces`. Each span is sent by an OTLP/HTTP exporter when it ends (`harness/otel.py`, service name `harness`). Without the variable nothing is exported and OpenTelemetry is not imported; a collector that does not answer delays the end of a span by about 7 s (the exporter's three retries, measured) and the exporter names the failure on stderr.

## Budgets per role

| Role | Model | Effort | Minutes per stage | USD per stage (print) | Enforced by |
| --- | --- | --- | --- | --- | --- |
| reader | sonnet | medium | 120 | — | `max_minutes` + `claude stop` |
| planner | opus | high | 120 | — | same |
| writer | sonnet | high | 240 | — | same |
| verifier | sonnet | high | 120 | — | same |
| critic | opus | high | 90 | — | same |
| judge | opus | max | 30 | 5 | `--max-budget-usd` |

A cost alert per `agent.name` from `claude_code.cost.usage` is the only budget signal for background sessions; the threshold values are a human decision.
The table lists the default stage table. Every other role type has its numbers in the row of the pipeline that uses it
(`docs/roles/pipelines/*.yaml`: `model`, `effort`, `max_minutes`, `max_budget_usd`, `max_turns`); loops add `stops` per episode
(`docs/loops/*.yaml`). Cache behaviour and context size: `CONTEXT_BUDGET.md`. Skill use: the event `claude_code.skill_activated`
and `harness skill-usage`.
