# Usage limits and API errors

## How a limit shows up
- The message: `You've hit your session limit · resets 3:45pm` (also `weekly limit · resets Mon 12:00am`, `Opus limit`,
  `Sonnet limit`). Claude Code blocks further requests until the time shown. Session and weekly limits are shared by every
  session of the account, so parallel shards reach them together.
- `529` and `Server is temporarily limiting requests (not your usage limit)` are capacity errors, not the account's limit.
- A turn that ends on an API error fires the `StopFailure` hook with `error`: `rate_limit`, `overloaded`,
  `authentication_failed`, `oauth_org_not_allowed`, `account_on_hold`, `billing_error`, `invalid_request`, `model_not_found`,
  `server_error`, `max_output_tokens`, `cloud_credential_error` or `unknown`. `.claude/hooks/stop-failure.py` appends it to
  the unit's `logs/stop-failure.jsonl`.

## Who waits

| Session | At a limit | Who acts next |
| --- | --- | --- |
| role session, background or print (`CLAUDE_CODE_RETRY_WATCHDOG=1` from `.claude/settings.json`) | `429` and `529` are retried without a cap; when the response carries a reset time the session waits out the window and continues | nobody |
| role session, `429` that reports a spend limit or exhausted usage credits | fails at once; the turn ends | `poll`: `wait_limit`, then `resume`; after `max_attempts` the human |
| role session, authentication, billing, organisation, credentials, unknown model | the turn ends | `poll`: `limit_human` |
| manager session (interactive, claude.ai subscription) | "continuing automatically at …"; stops after reaching the limit twice in a row | Claude Code, then the human |
| night tick (`claude -p`) | the automatic-continue option does not exist in `-p` and background sessions; the watchdog applies | the next scheduled tick |

`autoContinueAtUsageLimit` is a user or managed setting. It cannot be set from this repository.

## What `harness poll` does
- For a unit that is stopped, failed or behind a failed gate, `limits.decision` reads the last `StopFailure` record written
  since the unit's last start.
  - `rate_limit`, `overloaded`, `server_error`: action `wait_limit` with `resets_at` (the reset time parsed from the message,
    otherwise a fallback wait). No attempt is spent and nothing is resumed before that time.
  - authentication, billing, organisation, credentials, `model_not_found`, `invalid_request`: action `limit_human`; the run
    waits for the human.
  - anything else: the ordinary `resume` action.
- `uv run harness limits [--run <run-id>]` lists the units that are waiting and until when.

## Recovery
- By session id: `harness resume` continues the newest id in the unit's `session_ids`; a unit is never launched again.
  `progress.md` and the files on the worktree branch are where the session picks up.
- After a wait the prompt cache has expired: the first turn re-reads the whole conversation (`CONTEXT_BUDGET.md`, rule 5).
- Units released by the same reset share the limit again: when one of them stops on it once more, `poll` prints a new `wait_limit` and the wait repeats.

## Known gaps
- A session waiting inside the watchdog is `working` in `claude agents --json`. `max_minutes` can expire during the wait and
  `poll` prints `timeout`; read `claude logs <id>` before stopping such a session (`docs/runbooks/usage-limit.md`).
- Whether the `StopFailure` input carries the reset time is not documented. Without it the fallback wait in `limits.py` applies.
- An API key has no reset: only the spend limit and capacity errors exist there.
