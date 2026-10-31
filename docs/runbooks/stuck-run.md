# Runbook: a run that does not move

## Symptoms
`harness poll` prints the same actions on consecutive polls; `updated_at` in `state.json` is old; a unit stays `working`
past `max_minutes`, or is `blocked`.

## Cases

| What `poll` prints | Cause | Do |
| --- | --- | --- |
| `attention` with `waitingFor: "permission prompt"` | a tool call no rule allows | `claude attach <job-id>` and answer; if it will recur, add the rule in a pull request |
| `timeout` | the session is still working after `max_minutes`, or it is waiting for a limit inside the retry watchdog | `claude logs <job-id>`; for a limit wait leave it (`usage-limit.md`); otherwise `claude stop <job-id>`, then `uv run harness resume --run <run-id> --stage <stage>` |
| `resume` with the same failing checks every time | the session cannot satisfy the gate | let `max_attempts` end it; change the brief, the plan or the gate, not the session |
| `max_attempts` | no attempt is left | read `stages/<stage>/gate.json` and `progress.md`; the unit is not resumed again; fix the cause and start a new run from the brief; the old run directory stays as evidence |
| `escalation` | a role session asked a question and stopped | answer in `escalations/<NNN>.json` (`docs/roles/HUMAN.md`); `poll` then prints the `resume` that delivers it |
| `wait_limit`, `limit_human` | a limit or an API error | `usage-limit.md` |
| nothing, and the status is `paused` | no unit is active and none can start | `uv run harness status --run <run-id> --stage <stage>`: `blocked-by:<dep>`, `locked` or `config_changed` |

## Status answers of `harness status` and `launch`
- `locked`: a lock file exists. `poll` removes it when the session is no longer listed; do not delete it by hand while the
  session is listed.
- `config_changed`: a frozen file changed since the run started. Review the diff; `just refreeze <run-id>` or revert.
- `already_launched`: use `harness resume`; a unit is launched once.

## After the fix
Run `uv run harness handoff --run <run-id>`. If the cause was the harness (a gate that cannot pass, a missing permission
rule), write it down for the weekly learning review: it reads the run directory, not your memory.
