---
status: accepted
date: 2026-10-04
decision-makers: the human, who chose it on 2026-10-04; measured by server-19, checked by server-e6
consulted: harness maintainers
informed: all package owners
---

# A stage at max effort keeps its prompt cache for an hour

## Context and Problem Statement
ADR-0003 gave every type a five-minute prompt cache, because a session that starts its long commands in the
background never pauses past five minutes (measured on 2026-10-02: a planner at one hour paid 1.06 $ more and paused
212 seconds at most). Since 2026-10-03 every stage runs at max effort, the human's rule, and there one response can
generate for five to nine minutes: the entry expires while the model writes, and the next request writes the whole
conversation again.

## Decision Drivers
* The cost of a run, at the same effort and for the same work.
* The time a request waits while 600,000 to 850,000 tokens are processed again.
* Nothing a session sees or does may change.

## Considered Options
* One hour for every type; five minutes for the two types that keep a low effort of their own
* Five minutes for every type (ADR-0003)
* One hour only for the types that run long commands

## Decision Outcome
Chosen option: the first. Measured on 2026-10-04 on two sessions at max effort, the planner of run
20261003-231228-checks-fix and the frame of run 20261004-011757-audit-max: all 8 cache misses were expiries. In 7 of
them the previous response had generated for 5.2 to 9.3 minutes, with no wait after it; once a new job came 26 minutes
after the session's last answer. None was a change of the prefix. Timed by the start of each request, one hour would
have cost 14 % less on both sessions (72.12 $ to 61.81 $, 23.02 $ to 19.70 $), although a one-hour write costs 1.6
times a five-minute one. `classifier` (haiku, low) and `quarantine-reader` (sonnet, medium) keep an effort of their own
and keep five minutes.

### Consequences
* Good, because a session at max effort costs about 14 % less and does not wait for its whole conversation to be
  processed again after a long response.
* Bad, because a session that never pauses past five minutes pays 1.6 times for its cache writes; at max effort this
  is rarer than the expiry it prevents.
* Neutral: `harness cache-report` still names these misses "prefix changed", because it times a miss by the response
  timestamps; the final fix after the audit corrects it.

### Confirmation
`test_stage_settings_carry_skills_cache_lifetime_and_no_auto_memory` and `test_a_shard_cannot_read_its_sibling_shards`
in `packages/harness/tests/test_access.py` read the lifetime a session is given; `harness cache-report` shows the
misses of the next runs.

## Pros and Cons of the Options

### One hour, five minutes for the two low-effort types
* Good, because it fits the effort each type runs at.
* Bad, because a short session at max effort pays for a lifetime it does not use.

### Five minutes for every type
* Good, because a cache write costs the least.
* Bad, because every response longer than five minutes is followed by a full rewrite of the conversation.

### One hour only for the types that run long commands
* Good, because fewer sessions pay the dearer write.
* Bad, because the expiry comes from the length of a response at max effort, which every type has.

## More Information
Amends [ADR-0003](0003-brief-as-first-message.md), its paragraph on the lifetime. The rule on long commands in
`.claude/rules/harness.md` stays: a command still runs in the background, so the session goes on working.
