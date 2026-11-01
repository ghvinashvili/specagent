Decision (owner, 2026-11-01): a role's session compacts near 197k (`--autocompact 235000`) instead of handing over; the watcher's hand-over (250k/260k) is a backstop, also for a model change or a stuck session.
One frozen pack per lane (brief, rules, lessons.md's "Read first") in the system prompt via the agent's own `extra_prompt`; `--exclude-dynamic-system-prompt-sections` and `--system-prompt-snapshot on` keep the bytes before it fixed.
5m TTL for every role, waiters back within 3.5 minutes, a wait past about an hour ends the session; one model per lane; facts into the record as work goes; the pre-flight's `cache` check enforces it.
Measured: 29 cold restarts wrote 8.6% of all cache writes; the 1-hour TTL lost $32.60 net; a compaction costs about $0.45 against $0.70-1.00 for a hand-over.
It supersedes the TTL per role and the hand-over by itself in the two earlier decision pages.
