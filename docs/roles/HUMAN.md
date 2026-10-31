# Human involvement

## Approval points
- After `plan` (before any code is written) and after `judge` (before a branch is merged). Both are
  `approval: human` in `docs/roles/stages.yaml`; add or remove points there, not in prompts.
- A plan comes with the trial its author ran: `stages/plan/output/trial/trial.patch` and the section Trial of
  `plan.md`. A plan whose Trial begins with `nothing to run:` was not tried; decide whether the reason holds.

## What a role session is told
- Before a stage starts, the manager writes its assignment: what it would write into the prompt of a subagent sent to
  do the same job. Read it in `<run-id>/assignments/<stage>.md`; it is the place to look first when a stage's work
  is thinner than you expected. `harness launch` starts nothing without it (`MANAGER.md`, section 14).

## After the judge
- `accept`: approve the stage (`harness approve --run <id> --stage judge --decision approved`), then
  `harness integrate --run <id> --clean`. It builds the branch `run/<run-id>` with everything the run committed and
  removes the run's checkouts and its finished sessions from the list `claude agents` shows. Review `git diff <base> run/<run-id>` and merge it yourself; nothing merges by itself.
  The branch is never rewritten afterwards: delete it to have it built again.
- A run you give up: tell the manager, which runs `harness abort --run <id> --reason "<your words>"`. The sessions
  stop, the checkouts go, uncommitted work is kept under `refs/harness/salvage/<run-id>/`, and the folder stays.
- A run loops by itself: findings of the critic go back to the planner, findings of the verifier and the judge to
  the writer, each with its proof, at most three times per counter and five writer runs. You are asked to approve
  the plan (read `stages/attack/output/summary.md`), to approve the final verdict, and when the loop stops
  (`loop_cap`, `no_progress`, or the judge's `replan` or `reject`): `harness approve --decision approved` goes on with
  the work as it is (a reason that does not hold: a command the reviewer could not run in its sandbox is one you can
  run yourself), and `harness abort` ends the run, after which a new run starts from the brief with the reasons under
  Known decisions.

## Looking into a role session
- `claude agents --cwd <repository>` lists the sessions; `claude logs <id>` prints recent output; `claude attach <id>`
  opens one (`←` returns to the list, `Ctrl+Z` to your shell). The status line of the manager's terminal shows what
  is running.
- Do not type into a role session. A message of yours continues it as a copy on your own default model and without
  the stage's flags. Tell the manager, or answer the escalation.

## Unattended mode
- Role sessions never wait for a human. If they cannot decide, they write an escalation and stop.
- The manager runs unattended between approval points; it stops the run when a stage fails
  `max_attempts` times, a session exceeds `max_minutes`, or an escalation is blocking.
- Permission prompts do not occur in unattended sessions by design (`acceptEdits`, sandbox, allow rules; the
  project MCP server is pre-approved through `enabledMcpjsonServers`, and role sessions run with `--strict-mcp-config`).
  If one appears anyway, the manager reports the session id; attach with `claude attach <id>`.
- A stage with `permission_mode: auto` (`write` in `docs/roles/pipelines/software-factory.yaml`) lets a classifier decide tool calls
  that would otherwise prompt; `deny` and `ask` rules and the sandbox still apply. Auto mode reduces prompts and does not guarantee
  safety, so it is set only on stages whose output a later stage checks. After 3 blocks in a row or 20 in total the prompts return
  and the session shows as blocked; attach to it. What the classifier trusts is `docs/roles/auto-mode.json`; changing it is a
  pull request (`docs/quality/LEARNING.md`).
- Outside the terminal you are told when a run needs you: set `HARNESS_NOTIFY_CMD` (`.env.example`); see `docs/runbooks/README.md`.
- At night, loops run from `ops/night-tick.sh` with `dontAsk` and a budget; what they did is in
  `<runs root>/_loops/<name>/state.json` (`docs/loops/README.md`). A fire first asks `harness loop due` without a model:
  with no open run, every unit still working or the pause switch set, no session starts, and the reason is a line of
  `<runs root>/_audit/night-tick-<date>.jsonl`.

## Holding everything
- `harness pause set --reason "<your words>"` (or tell the manager): while the switch is set no session, loop iteration
  or night session starts or resumes, and no run's state changes; sessions already running finish their turn and
  wait. `harness pause lift` lets the same work go on; `harness pause status` shows the switch
  (`docs/decisions/0023-one-pause-switch.md`).
- Approvals, answers, `harness abort` and `harness integrate` still work while it is set. To stop a running session at
  once, `claude stop <job>`; `harness resume` continues it later.

## Answering an escalation
- Open `<runs root>/<run-id>/escalations/<NNN>.json`, fill `answer.text` (and `answer.option_id`
  if you chose an option), set `status` to `answered`. Or tell the manager the answer; it writes it verbatim.
- The manager resumes the stage with the answer as the next message.

## Accepting a configuration change during a run
- `harness launch`/`resume` print `config_changed` when `.claude/settings.json`, `.claude/settings.local.json`, `.mcp.json`,
  agents, skills, hooks, rules or `plugins/` changed since the run started. Review the diff, then `just refreeze <run-id>` to accept it,
  or revert the change.

## Reading a run
- Run state lives beside the repository, in `<runs root>/<run-id>/` (layout in `RUNS.md`); it is
  never committed. Open it in your editor, or through the manager, which `just manager` starts with
  `--add-dir <runs root>`.
- `HANDOFF.md` first; then `state.json`; then the stage's `output/`.
- Never edit files under `stages/` of a running stage.
- What Claude keeps between runs: the manager's auto memory (`/memory` in the manager session) and `.claude/agent-memory/manager/`;
  role sessions keep no notes (`docs/architecture/memory.md`).
