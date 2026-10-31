# Reliability

## Sessions
- Unattended sessions run with `CLAUDE_CODE_RETRY_WATCHDOG=1` (429/529 retried without limit; other errors up to 300 times).
- A background session that crashes is restarted by the supervisor; a session idle for about an hour is parked and resumed on the next message.
- Every unit (stage, or shard) has a fixed session id in `manifest.json`; `harness resume` continues it with `--resume <id> --bg`. When Claude Code continues as a copy under a new id, the copy's id is appended to `state.json` and polled from then on.

## State
- The run directory lives beside the repository (`<runs root>/<run-id>/`), so a background session's
  worktree isolation never blocks a state write; sessions reach it through `--add-dir`.
- `state.json` is written atomically before and after each action: a temporary file of the write's own, then a
  rename. Every writer of a state file holds its one lock around its read, change and write and keeps what another
  command wrote meanwhile; no lock is held while a session or a gate runs, and a dead holder's lock stops nobody
  (`docs/decisions/0021-one-writer-at-a-time-for-run-and-loop-state.md`).
- `claude agents --json` is the only runtime source; a missing row means "stopped", never "done".

## Gates and retries
- `max_attempts` per unit; a failed gate, a stopped or failed session and a failed print run (`last_error`: exit code, stderr)
  all become one `resume` action of `harness poll`, with the message to deliver; after the limit `poll` prints `max_attempts`
  and the human decides. A unit is launched once; every retry continues the same session (`--resume`, or `-p --resume` for print units).
- Stop hooks block a role session up to 8 times; after that the gate catches the missing result.

## Known failure modes
- Permission prompt in an unattended session → `waitingFor: "permission prompt"`, human attaches.
- Context overflow → compaction; SessionStart(compact) re-injects the run pointers.
- Supervisor stopped on shutdown → sessions resume from disk on the next `claude agents` or `harness resume`.
- Usage limit or API error → the session waits by itself (retry watchdog), or the turn ends and `poll` prints `wait_limit` or
  `limit_human` instead of `resume` (`LIMITS.md`; runbook `docs/runbooks/usage-limit.md`).
- A run nobody watches → `harness poll` notifies through `HARNESS_NOTIFY_CMD` (`docs/runbooks/README.md`).
- Conflicting worktree branches at merge → `docs/runbooks/worktree-conflict.md`.
