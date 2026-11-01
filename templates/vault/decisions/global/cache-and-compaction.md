---
title: A role's session compacts instead of handing over and reads its frozen lane pack from the prompt cache
type: decision
scope: global
kind: lesson
template: yes
status: verified
updated: 2026-11-01
audience: [all]
sources: [context/measurements/2026-11-01-cache-and-compaction.md]
decided: 2026-11-01
by: owner
proof: [context/measurements/2026-11-01-cache-and-compaction.md]
why: the prompt cache matches an exact prefix for 5 minutes from the last call; measured, gaps past it rewrote 8.6% of all cache writes, the 1-hour TTL lost $32.60 net, and a compaction costs about $0.45 against $0.70-1.00 for a hand-over
decision_status: decided
would_change_if: a run with these rules measures more cost per unit or a defect traced to a fact lost in a compaction
---
# Compaction and a frozen lane pack in the prompt cache

**Rule.** A role's session compacts itself near 197k (`--autocompact 235000`) and goes on; the watcher's hand-over
(`handoff_at` 250000, `cap` 260000) is a backstop, used also for a model change or a stuck session. Each lane has one
pack (the common brief, the role's assignment, the first-pass and hand-over rules, the "Read first" section of
lessons) built once before its first launch, passed in the system prompt and never changed during the run. Every role
runs at the 5-minute cache TTL, its waiters return within 3.5 minutes, a wait longer than about an hour ends the
session, a lane keeps one model, and the facts the next step needs go into the record file as the work goes.

**Why.** The cache matches an exact prefix and lives 5 minutes from the last call, and the system prompt is rebuilt
the same on every call, so it survives a compaction while the conversation does not. Measured on two runs of
2026-11-01: 29 cold restarts after gaps past 5 minutes wrote 2,630,529 tokens (8.6% of writes); the 1-hour TTL cost
$59.51 more in writes and saved $26.91; the balance C = c0 + sqrt(2Kg/r) gives about 166k, flat within 3% from 150k to
200k.

**How to apply.**
- Config: `--autocompact 235000`, `--exclude-dynamic-system-prompt-sections` (git status, cwd and date out of the
  system prompt) and `--system-prompt-snapshot on` in `common`; `cap` 260000, `handoff_at` 250000; the empty 60% override.
- Pack: `make_pack.py --no-note` per lane, the agent's own `extra_prompt`; a changed pack stops the watcher.
- Settings: `CLAUDE_CODE_PROMPT_CACHE_TTL` 5m for every role and the lane's one model.
- Waiters back within 3.5 minutes, the role runs them again; a wait known past about 1 hour ends the session. The
  system guarantees it, not the role (owner, 2026-11-01 evening): the watcher wakes a non-final session idle 3.5
  minutes, up to about 1 hour, and a role's foreground call is refused past 210 s; a role's own waiter loop once
  held a session 8 and 14 minutes.
- A HANDOFF note only on the watcher's order; facts go into the record file as the work goes.
- The pre-flight's `cache` check fails a lane that misses one of these.

Related: [[keep-context-small]].
