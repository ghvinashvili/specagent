# HANDOFF — <run-id> (<updated-at>)

## Where the run stands
- Status: <state.json status>; current stage: <stage>
- Stages: <table: stage · status · gate · approval · session id · attempts>

## Rounds
- every round of the run's loops: who sent how many findings back to whom (state.json `loop`)

## What was produced
- <stage>: `stages/<stage>/output/<file>` — <one line>

## Gate warnings
- <stage>: <check: `step <n>: <rule>` or a check of part 3> — <why it failed>; recorded while the steps mode is `warn`

## Waiting on a human
- <escalation id or approval point, with the file to open>

## Next steps
1. <what the manager will do once unblocked>

## Costs and limits
- Print stages total: <usd>; bg sessions: see OpenTelemetry `cost.usage` by `agent.name`
