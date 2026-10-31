# Runbook: usage limit or API error

Rules and the full table: `docs/quality/LIMITS.md`.

1. `uv run harness limits`: which units wait, for what, until when.
2. `wait_limit`: nothing to do before `resets_at`. The next `poll` after that time prints `resume`; the unit continues under
   its session id from `progress.md`. A night tick of the `poll` loop does this without you.
3. `limit_human`: the error names the cause.
   - `authentication_failed`, `oauth_org_not_allowed`, `cloud_credential_error`: check with `claude auth status`, log in again as the container user (`claude auth login`), then `harness resume`.
   - `billing_error`, `account_on_hold`: the account owner acts; then `harness resume`.
   - `model_not_found`, `invalid_request`: the stage table names a model or flag the account cannot use; fix it in a pull request and start a new run.
4. A session shown as `working` for longer than `max_minutes` while the account is at its limit is waiting inside the retry
   watchdog. Leave it; stopping and resuming it would spend an attempt and gain nothing.
5. The manager's own session: Claude Code shows "continuing automatically at …". If it shows "Automatic continue stopped",
   type the next prompt yourself after the reset.
6. Limits that return every day mean the load is wrong, not the policy: lower `max_shards`, move stages to a smaller model in
   the stage table, or spread loops across the night in `ops/night-tick.cron`.
