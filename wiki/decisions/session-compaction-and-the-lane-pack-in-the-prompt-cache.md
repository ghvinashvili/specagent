---
title: A session compacts instead of handing over and reads its lane's frozen pack from the prompt cache
type: decision
status: draft
updated: 2026-11-01
created: 2026-11-01
audience: [all]
decided: 2026-11-01
by: owner
why: the prompt cache matches an exact prefix for 5 minutes from the last call; measured on a project's two runs, gaps past it rewrote 8.6% of all cache writes, the 1-hour TTL lost $32.60 net, and a compaction costs about $0.45 against $0.70-1.00 for a hand-over
would_change_if: a run with these rules measures more cost per unit than the hand-over rule, or a defect traced to a fact lost in a compaction
decision_status: decided
scope: project
tags:
  - decision
---
# A session compacts instead of handing over and reads its lane's frozen pack from the prompt cache

A role's session works unit after unit and compacts itself near 197k (`--autocompact 235000` in the watcher's `common`);
the watcher's hand-over, past `handoff_at` 250000 or `cap` 260000, is a backstop, and the manager orders one for a model
change or a stuck session. Each lane has one pack (`_common.md`, the role's assignment, `_first-pass-rules.md` where the
role reads it, `_handoff-rule.md`, the "Read first" section of `lessons.md`), built once by `make_pack.py --no-note`
before the lane's first launch, passed in the system prompt by the agent's own `extra_prompt` and frozen for the run (a
changed pack exits the watcher 4). `common` also carries `--exclude-dynamic-system-prompt-sections` and
`--system-prompt-snapshot on`, so git status, the folder and the date do not change the bytes before the pack.

Every role runs at the 5-minute TTL; the waiters return within 3.5 minutes and the role runs them again; a wait known to
be longer than about an hour ends the session through a note and the role's `work_check`. A lane keeps one model, and a
role writes the facts its next step needs into its record as it works. The pre-flight's `cache` check fails a lane that
misses one of these. It supersedes the TTL per role of
`the-cache-is-measured-in-dollars-and-set-per-role` and the hand-over by itself of
`pipeline-economy-hand-over-units-checks-facts-pack`.

Why: the cache matches an exact prefix and lives 5 minutes from the last call, and the system prompt survives a
compaction while the conversation does not. On 2026-11-01, 29 cold restarts after gaps past 5 minutes wrote 2,630,529
tokens (8.6% of writes); the 1-hour TTL cost $59.51 more in writes and saved $26.91; the balance C = c0 + sqrt(2Kg/r)
with c0 64.9k, g 2,250, K $0.45 and r $0.20/M gives about 166k, flat within 3% from 150k to 200k. The record is the
skill's `references/launch.md`, the README section "The cache and the context", and the owner's vault.
