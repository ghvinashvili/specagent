---
title: The cache is measured in dollars and set per role
type: decision
status: draft
updated: 2026-11-01
created: 2026-10-31
audience: [all]
decided: 2026-10-31
by: owner
why: a token count hides what a cache write costs (29% of the readme writer's $129.61), and a role that waits on no one has no use for an hour of cache
would_change_if: a run priced in dollars shows the 5m cache costing more than the hour for a role that waits on no one, or a run that launches a role that waits at 5m and shows it ahead of the hour in dollars (the figures of 2026-10-31 re-price sessions that ran at 1h), or Claude Code changes the TTL values or the write price
decision_status: decided
scope: project
tags:
  - decision
---
# The cache is measured in dollars and set per role

Superseded in part (2026-11-01): the TTL is 5m for every role and a session compacts instead of handing over by itself; see [decisions/session-compaction-and-the-lane-pack-in-the-prompt-cache.md](session-compaction-and-the-lane-pack-in-the-prompt-cache.md).

A token count hides what the cache costs: a cache write is priced at twice an input token for an hour and at 1.25 times for five
minutes, and the readme writer's $129.61 was 31% cache reads, 29% cache writes and 40% output. So the measuring scripts print
money. `usage_report.py` shows cache reads, cache writes and output as dollars beside their token counts (one usage per message
id), `score_run.py` does the same in its role table, and its economy row has a "cache write $ per unit" column. The figures are on
the owner's vault page `context/measurements/2026-10-31-cache-ttl.md` and in [Time and money](../../docs/economy.md).

A cached prefix is only as long as what is byte-identical from one call to the next, so a launch prompt follows "stable first,
unique last": what is identical across a role's sessions comes first (the brief, the hand-over rule, the "Read first" section of
`lessons.md`, the facts pack), and what is unique to one session comes last (the hand-over note). `make_pack.py --no-note` leaves
the note out of a pack. Packs stay off until a run measures one in dollars.

The cache's time to live is set per role in the role's settings `env`, `CLAUDE_CODE_PROMPT_CACHE_TTL`: `5m` for the builder, the
writer and the planner, which wait on no other role, and `1h` for the verifier, the critic, the plan fixer and the judge, which do.
At 5m a cache write costs 37.5% less, so the saving is at most 37.5% of a role's write dollars, less the rewrites after gaps of 5
to 60 minutes. The sessions measured on 2026-10-31 came out ahead at 5m: the writer and the builder keep almost all of the saving,
the verifiers lose 69% and 41% of it to rewrites, and keep the hour until a run measures one at 5m. The rule is for the SpecAgent
role sessions launched with the skill's settings; the harness's stage types keep the hour that `docs/roles/need-to-know.yaml`
sets (ADR-0016).

## Record and source
- [Spec 005](../../specs/005-spec-writer-rule/spec.md): requirement 7
- [Time and money](../../docs/economy.md): the measurement of 2026-10-31 and its figures
- [The pipeline skill's launch page](../../.claude/skills/running-specagent-pipelines/references/launch.md): the TTL per role
- [The pipeline-economy decision](pipeline-economy-hand-over-units-checks-facts-pack.md): the economy row it decided gains the column "cache write $ per unit" after "cost per unit" (requirement 7a); its four rules and the rest of its row stand, so it keeps `decision_status: decided`
