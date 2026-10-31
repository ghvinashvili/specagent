# Tasks: <feature>

| Id | Category | Description | Steps | Depends on | Acceptance |
| --- | --- | --- | --- | --- | --- |
| T001 | model | <what> | <step; step> | — | <test or check> |

Waves inside one shard (tasks with no unmet dependency run in parallel): W1 = T001; W2 = T002, T003. Across shards, `harness launch` keeps every dependency chain in one shard, so a task never waits on another worktree branch.
