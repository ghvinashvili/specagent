# Manager specification

The manager is a Claude Code session started with `claude --agent manager` in the repository root.
It is the only session a human talks to. Everything below is a contract; the wording of the
manager's instruction lives in `.claude/agents/manager.md`.

## 1. What it receives from the human
- A run request: a slug, the spec or material paths, the definition of done, constraints
  (budget in minutes per stage, which stages need approval). It writes these into
  `<runs root>/_briefs/<slug>.md` from `templates/project-brief.md` (the run directory does not exist yet);
  the human confirms the brief, then `harness run --slug <slug> --brief <runs root>/_briefs/<slug>.md`
  creates the run and copies the brief to `<run-id>/brief.md`. This is the harness's manager, for a harness run the
  owner has named; a project's work runs through the pipeline skill and its manager chat (`docs/roles/manager-chat.md`),
  never through these stages by default.
- Answers to escalations, written into the escalation file (`answer` field) by the human or
  dictated to the manager, which writes them verbatim.
- Approvals: "approve plan", "reject judge verdict", written to `state.json` through `harness approve`.
- The cut of the work: one run changes one mechanism (one gate, one guard, one command), so one writer session holds
  it from start to end and the reviewers check one coherent change. Measured on 2026-10-04: a wave of 22 findings
  across four areas ended with 14 reasons to revise.
- Control: hold everything with the one pause switch, `uv run harness pause set --reason "<their words>"`, and lift it with `uv run harness pause lift` (`docs/decisions/0023-one-pause-switch.md`): while it is set no session, loop iteration or night session starts or resumes and no state changes; resume or stop a unit; abort a run the human gives up with `uv run harness abort --run <id> --reason "<their words>"`: its sessions stop and leave the session list, its checkouts go after their uncommitted work is saved under `refs/harness/salvage/`, and its folder stays as the record.

## 2. How it chooses a role type
- The stage table `docs/roles/stages.yaml` decides for every stage in the table.
- For an ad-hoc request the manager runs `harness select "<request>"`, which matches the request
  against the `description` of every type in `docs/generated/role-types.md` ("Use when:" sentence).
  A unique best match is used; anything else is a no-match.
- No-match rule: the manager never improvises a type. It writes an escalation with the candidate
  list and waits. A new type is created only with `/new-role-type` from the template.

## 3. How it launches
- Before a stage is launched for the first time the manager writes its assignment and stores it with
  `harness assign --run <run-id> --stage <stage>` (section 14). `harness status` and `harness launch` answer
  `no_assignment` for a stage without one: no role session starts on the brief and its type file alone.
- `harness launch --run <run-id> --stage <stage>`; the CLI builds the command:
  `claude --agent <type> --session-id <uuid from manifest> --name <run-id>/<stage> --add-dir <stage dir and what the type's access row opens>
  --permission-mode <from the stage table> --settings '{"crossSessionInbound":"refuse","attribution":{"commit":"<run, stage and session trailers>"},<the type's access rules>}' --setting-sources project,local --strict-mcp-config
  --model <from manifest> --effort <from manifest> --bg "<prompt.md>"`
  or, for `mode: print`, `claude -p --agent <type> ... --permission-prompts none --output-format json --json-schema <API copy of the schema> --max-turns <max_turns, default 60> --max-budget-usd <n> "<prompt.md>"`, run to completion by the launcher;
  the API copy (`state.api_schema`) drops the numeric and string constraints the structured-output API answers with a 400, and the returned verdict is validated locally against the full schema.
- The manager types `uv run harness launch|resume|poll|abort|integrate …` as they stand, or runs them through its
  skills `/run-stage` and `/resume-stage`: they are in `sandbox.excludedCommands`, and a `just` recipe around one
  would run inside the sandbox.
- A unit (stage, or shard) is launched once, with its session id from the manifest; every later attempt is `harness resume`
  (`launch` answers `already_launched`), so one id never starts two sessions. A print run that exits non-zero or returns no
  `structured_output` is recorded in the unit's `last_error` (exit code, stderr tail) with status `failed`; `poll` turns it into a `resume` action.
- A `parallel: per_task` stage is one call: `harness launch --run <run-id> --stage write` splits the planner's
  `tasks.json` into `stages/write/NN/tasks.json` and starts one session per shard, each with its own session id,
  lock and gate; `--shard N` relaunches one shard. Both commands refuse with `config_changed` when a frozen file changed.
- `<run dir>` is `<runs root>/<run-id>/`, outside the repository: a background session edits
  in its own worktree and may not write into the main checkout, while a write outside the working
  directory is allowed. `--add-dir` gives the session that directory; `--strict-mcp-config` keeps the
  project's `.mcp.json` server (and its approval prompt) out of role sessions.
- The prompt is the project brief, the stage's assignment and the stage's input paths. The default instruction is never
  repeated in the prompt: it comes from the agent file through `--agent`, so the system prefix is
  byte-identical across projects.
- The launcher sets `HARNESS_RUN_DIR`, `HARNESS_STAGE`, `HARNESS_ROLE`, `HARNESS_MODE` (and `HARNESS_SHARD` for a shard),
  `CLAUDE_CODE_FORCE_SESSION_PERSISTENCE=1`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` and `CLAUDE_CODE_SYNC_PLUGIN_INSTALL=1`
  in the session's environment, from one function (`state.session_env`) that `resume` and the eval runner call as well. Credentials are not
  inherited (`CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`); the launched session authenticates with the
  container user's stored `claude` login.

## 4. How it waits
- It does not block. It runs `harness poll --run <run-id>` on a `/loop` (default prompt in `.claude/loop.md`)
  or when the human asks. `poll` reads `claude agents --json --all --cwd <root>`, updates `state.json`
  and prints the actions to take: `gate` (passed), `resume` for every unit that is stopped, failed or behind a
  failed gate, with the message to deliver (the failing checks from `gate.json`, or a failed print run's exit code and
  stderr from `last_error`), `max_attempts` when no attempt is left, `attention` (blocked: needs input, permission prompt),
  `timeout`, `escalation`, `approval`, and `wait_limit` or `limit_human` when a limit or an API error ended the turn (section 12); for a sharded stage every action names its `shard`, and the stage counts as done
  only when every shard passed its gate.
- The loop of a run (section 12) adds: `rework` (a reviewer sent proven findings back to the stage; the manager
  resumes it with `--rework`), `recheck` (a stage after it checks the new work again once the stages before it passed;
  `--rework` as well), and for the human `loop_cap` (a counter or the stage's `max_runs` is used up), `no_progress`
  (the round brought back the findings of the round before, or none), `replan` and `rejected` (the judge's
  decision). Each stop comes with an `approval` of the reviewer: `harness approve --decision approved` goes on with
  the work as it is, `harness abort` ends the run.
- A session whose row disappears from `claude agents --json` is treated as stopped and resumed.
- While the pause switch is set, `poll` answers `paused` with no action and writes nothing, and `watch` returns at once.
- `claude logs <id>` is the only way it looks inside a running session; it never opens transcripts.

## 5. How it resumes
- `harness resume --run <run-id> --stage <stage> [--message "<text>"]` runs
  `claude --resume <session-id> --add-dir <the same directories as at launch> --permission-mode <mode> --settings '<the same JSON as at launch>' --setting-sources project,local --strict-mcp-config --bg "<message>"`.
  The session id is the one written in `manifest.json` before the first launch, so a resume is
  possible even when the launch output was lost. `--add-dir` and `--settings` are passed again
  because a resume does not restore them (`--permission-mode` is restored; passing it again is harmless).
- For a `mode: print` unit the same command runs `claude -p --resume <session-id> <the launch flags> "<message>"` to
  completion: a `-p` session is resumable by its id; the output is processed exactly like a first run, and a failure is
  recorded again in `last_error`.
- When Claude Code cannot continue in place it starts a copy under a new id and prints a `note:` line;
  `harness resume` reads the copy's `sessionId` from `claude agents --json`, appends it to the unit's
  `session_ids` in `state.json`, and `poll` follows the copy from then on.
- When there is nothing to deliver (no message, no answered escalation) and the old job is still
  listed as stopped or failed, the CLI runs `claude respawn <job-id>` instead: it restarts the same
  job and resumes its saved conversation. `respawn` takes no message, so an answer always goes
  through `--resume --bg`.
- An answered escalation is delivered as the resume message, verbatim, with the escalation id.
- Retry means resume: a unit is never launched twice under its session id; `poll` prints the `resume` action with the
  message, and after `max_attempts` it prints `max_attempts` and the run waits for the human.
- `--rework` continues a unit a loop sent back or asks to check again: the harness writes the message; a recheck
  rebuilds `input/`, the work's checkout and `changes.patch`, then the Material, first. Attempts count from the unit's
  `round_start` (a round gets its own `max_attempts`); `max_runs` bounds every start of a stage in one run.

## 6. When it asks the human
- Every open escalation (a role session wrote one and stopped).
- Every `approval: human` stage after its gate passed.
- A session blocked on a permission prompt (`waitingFor: "permission prompt"`): the human attaches with `claude attach <id>`.
- A stage that failed `max_attempts` times or exceeded `max_minutes`.
- A loop that stopped: `loop_cap`, `no_progress`, `replan`, `rejected` (section 4).
- The approval of `attack`: the human reads `stages/attack/output/summary.md` (one page in English) and
  `stages/plan/output/plan.md` before the work starts.
- A no-match in type selection.
It asks in one message: what happened, the file to read, the options, and what it will do on each answer.

## 7. Where it stores state
- Only on disk, under the run directory `<runs root>/<run-id>/` (beside the repository, never
  inside it; layout in `RUNS.md`): `manifest.json` (immutable after creation), `state.json`
  (every transition, plus the configuration fingerprint recorded by `harness run`), `escalations/`, `HANDOFF.md`. Its own context is not state: a new manager
  session must be able to continue any run from these files alone. The manager session itself is
  started with `--add-dir <runs root>` (`just manager`) so it can read and write there.
- Every state write goes through `harness` (validated against `schemas/`), never through a free-hand edit.

## 8. Limits it keeps
- `max_minutes` and `max_attempts` per stage from `stages.yaml`; `max_budget_usd` for print stages.
- At most one session per unit (stage, or shard): `locks/<stage>[-NN].lock`; a sharded stage has at most `max_shards` sessions; `max_minutes` and `max_attempts` are checked per unit from the manifest's stage entry.
- It never launches a stage whose dependencies have not passed their gate.

## 9. What it never does
- Never does role work (reading, planning, writing, verifying) itself.
- Never launches a stage on the brief alone, and never gives a role session less than it would give a subagent
  sent to do the same job (section 14).
- Never spawns subagents or workflows inside a run.
- Never edits `.claude/`, `schemas/`, `docs/roles/` while a run is active.
- Never reads transcripts or `~/.claude/jobs/`.
- Never summarises a stage's output from memory; it points to files.

## 10. How it protects the two caches
- State cache: state lives in files written before and after every action; a crash between two
  writes loses at most one action, which `poll` re-derives from `claude agents --json`. Every writer of a state file
  holds its one lock around its read, change and write, never while a session or a gate runs, and writes through a
  temporary file of its own; a writer that ran a session or a gate reads the file again and carries over only what it
  did (`docs/decisions/0021-one-writer-at-a-time-for-run-and-loop-state.md`).
- Instruction cache: the default instruction is only in the agent file; the brief and the assignment are only in the first
  user message; `.claude/settings.json`, `.claude/settings.local.json`, `.mcp.json`, agents, skills, hooks, rules and `plugins/` are frozen during a run:
  `harness run` records their fingerprint in `state.json` and every `launch`/`resume` refuses when it changed
  (`harness refreeze` after a human decision); the ConfigChange hook blocks settings and skill edits inside role
  sessions and logs every change (it does not fire for `.mcp.json`), and role sessions never load `.mcp.json`
  (`--strict-mcp-config`). A changed tool set or system prompt would invalidate the prompt cache.

## 11. What it remembers, and where
- Auto memory stays on for the manager (`autoMemoryEnabled: true` in `.claude/settings.json`): Claude's own notes about the
  human's corrections and this project (`user`, `feedback`, `project`, `reference`), at `<CLAUDE_CONFIG_DIR>/projects/<project>/memory/`
  (one directory for every worktree; not removed by `cleanupPeriodDays`; in the devcontainer inside the `~/.claude` volume).
  The human reviews it with `/memory`.
- Agent memory `memory: project` (`.claude/agent-memory/manager/MEMORY.md` plus topic files): patterns of running this
  harness; committed and reviewed in pull requests; its first 200 lines or 25 KB enter the manager's system prompt at session start.
- Role sessions remember nothing across runs. The launcher sets `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` for four reasons:
  auto memory is per repository and shared across worktrees, so it would carry notes from run to run and from the manager into
  roles; the `memory` field is part of auto memory and would be off with it anyway; a background session's write into
  `.claude/agent-memory/<type>/` would land on its worktree branch; and a memory file in the system prompt would change the
  cached role prefix. Cross-run learning goes through `result.json` and pull requests (`docs/architecture/memory.md`).
- Never writes a run's facts into any memory: state is the run directory (section 7).

## 12. Loops, limits and notifications
- A loop is a file in `docs/loops/`; its state is `<runs root>/_loops/<name>/state.json`. One tick is
  `harness loop tick --name <name>` (the loop-tick skill): the CLI checks readiness, the exit rule and the hard stops and prints
  one action (`wait`, `launch`, `prompt`, `external`, `exit`). The manager carries out that action and nothing else. One tick of a
  loop runs at a time; a `prompt` loop is judged by code, by its `exit.check`, the progress of the runs it acts on and the cost of
  its night sessions (`docs/decisions/0022-a-prompt-loop-is-judged-by-code.md`); while the pause switch is set the tick answers
  `wait` with `paused`.
- Triggers: `/loop` in the open manager session (`.claude/loop.md`); `ops/night-tick.sh` from the operator's scheduler, which first
  asks `harness loop due` (no model, no tick) and starts a fresh headless manager session only when there is work, told the prompt
  loop's file, which ticks by itself, or `/loop-tick <name>`; `.github/workflows/loops.yml` for loops that need no model. A cloud
  routine starts from a fresh clone and cannot see the run directory, so it never drives a run.
- Usage limits: role sessions wait out the window themselves (`CLAUDE_CODE_RETRY_WATCHDOG=1`). When a session ended on a limit,
  `poll` prints `wait_limit` with `resets_at` instead of `resume`, and the manager resumes only after that time; `limit_human`
  (billing, authentication, spend limit) goes to the human. Rules and numbers: `docs/quality/LIMITS.md`.
- The loop inside a run (`docs/decisions/0024-a-run-loops-until-its-reviewers-pass.md`): a stage with `returns_to`
  sends its proven findings back when its verdict is `revise` (`attack` to `plan` on the counter `plan`, `verify` and
  `judge` to `write` on the counter `work`). The table's `loop` block bounds the rounds per counter (3) and the starts
  of `write` (5). `poll` takes every round under the lock of `state.json` (`harness/rounds.py`); the manager resumes
  `rework` and `recheck` units with `--rework`, also at night (`harness loop due` hands them over), and reports a
  stop to the human.
- Notifications: after every poll the CLI sends one line per new action that needs the human (`escalation`, `approval`, `attention`,
  `max_attempts`, `timeout`, `limit_human`, `loop_cap`, `no_progress`, `rejected`, `replan`) through the command in `HARNESS_NOTIFY_CMD`; every line is also in
  `<runs root>/_audit/notify.jsonl`. An action is new when the last poll did not print it: one no poll prints any more is
  forgotten, so the next time a unit needs the human it is told again.

## 13. Pipelines, patterns and untrusted input
- `harness run --pipeline <name>` uses `docs/roles/pipelines/<name>.yaml` instead of `stages.yaml`; the name is written into the
  manifest and `launch`, `resume` and `route` read the table from there. Shapes and when to use each: `docs/roles/PATTERNS.md`.
- A council is convened only through the council skill, and only when its three conditions hold.
- Text that nobody in this repository wrote enters only through the intake skill: the file goes to `<runs root>/_inbox/`,
  the quarantine reader digests it, and every later stage receives the digest, never the file. The manager does not open inbox files.
- A `permission_mode: auto` stage receives its classifier environment from `docs/roles/auto-mode.json` through `--settings`;
  `deny` and `ask` rules apply before the classifier. Print stages that must not act use `dontAsk`.
- Commits made by role sessions carry `Harness-Run`, `Harness-Stage` and `Claude-Session-Id` trailers (`docs/quality/PROVENANCE.md`).

## 14. The assignment of a stage
- The rule: a role session is approached exactly as a subagent would be. It gets every demand a subagent of the same
  kind would get for the same job. Before the first launch of a stage the manager writes the demands the way it
  would write the prompt of a subagent it was about to send, and then gives that text to the role session.
  What the session does has to repeat, one to one, what that subagent would have done, and add what a subagent does
  not have: its instruction, its rules and its knowledge pack read from the prompt cache, the access rules of its
  type, and a gate it cannot finish past.
- Why it is a rule and not advice (`docs/decisions/0006-a-role-session-gets-what-a-subagent-would-get.md`): measured
  on one task, role sessions launched on the brief and their type file alone wrote a plan a quarter of the size of
  the plan of a subagent that had been told what to deliver and how exactly. The difference was in what they were told.
- Parity is more than the demands. Before a launch the manager goes through four things a subagent sent to do the
  job would have had, and the session has to have each of them. The demands: the assignment. The material:
  everything it would have attached or named for the subagent; the project's instruction files are in every pack,
  and an earlier stage's output the job needs has to be among the stage's `inputs`. When it is not, the stage table
  has a gap: the manager tells the human and does not launch with less. The tools, and what may be run. The effort
  level. On the first measured task each of these was found short once: no assignment, a lower effort level, no
  project instruction files, a critic that could not run the work, a verifier without the author's report, a writer
  without the reader's notes.
- What a session may read follows the same rule (`docs/decisions/0015-a-type-that-is-not-blind-reads-what-a-subagent-reads.md`):
  a type that is not blind reads what a subagent sent into the repository reads; only the blind types are refused the
  agent files, the stage tables, the policy and `design/`. A run that has to change hook scripts says so in its
  brief with the line `- Hooks: open`; then its writers' and its planner's trial edits under `.claude/hooks/` are
  allowed in their own checkouts, and the scope check lets the branch carry them. The rest of `.claude/` (settings,
  agents, skills, commands, rules) stays closed to every branch: a session that enters a checkout reads them from
  there. The manager changes them outside a run, and the human approves the change.
- The material of a stage is chosen by script, and the manager spends no turn on it. The reason a role session
  exists is that it starts with what its job needs, read from the prompt cache on every request, where a subagent
  finds and opens it file by file. At launch the harness (`harness/pieces.py`, `pack.material`) cuts the files of the
  repository at their natural seams (the sections of a document, the top-level definitions of code, the top-level
  keys of a table) and gives the session, after its pack and while they fit: the stage's inputs; the material of the
  brief when the stage receives `context`; the pieces the assignment lists under its optional `Material`; every place
  the brief, the assignment and the inputs cite as `path:line`, as the piece that holds it, the most cited first;
  every file they name that is short enough to be given whole; and the pieces whose words match the brief best.
  A type that cannot write a file, a type whose agent file lists tools, none of them Write or Bash, gets none of the
  pieces the script chooses: its material is its inputs, the pieces its assignment lists and, when the stage receives
  `context`, the material of the brief (`docs/decisions/0012-a-type-that-cannot-write-accounts-for-no-material.md`).
  What the script adds on its own has a budget inside the section's (about 50,000 of at most 500,000 tokens; 25,000 of 80,000 on haiku), and a piece
  chosen only for its words goes first. A file already in the pack, a path the type may not read and `context/` for
  a stage that does not receive it are never given. Nothing is rewritten: every line is given as the file has it,
  after its number, and an empty line is left out with its number. The same texts give the same bytes, so the shards
  of a stage share the cache. The manager helps the choice by writing every place it knows as `path:line` in the
  assignment; it lists a piece under `Material` only when no text of the stage points to it.
  `harness material --run <id> --stage <s>` shows the pieces and why, without a model, with `does_not_fit` (what the
  stage's texts list and the budget does not hold) and `not_text` (images and other files the prompt cannot hold,
  which the session opens with Read and accounts for like any other file). `harness launch` refuses a stage whose
  listed material does not fit (`material_does_not_fit`): the manager splits it or narrows its assignment, so that no
  session has to search for what its job names.
- The effort of a stage comes from the table and is the default for ordinary work. A hard run raises the stages whose
  output decides with `harness run --effort <stage>=max` (repeatable); the manifest records it for the whole run.
- What it holds (`templates/stage-assignment.md`): Goal, Known, Material (optional), Deliver, Prove, Hard parts, Done
  when. `harness assign` refuses a text without `Deliver`, `Prove` and `Done when`, a section that says next to
  nothing, a copy of the brief, a copy of another stage's assignment, and a listed piece that does not exist or that
  the type may not read.
- Where it lives: the manager's text is `<run>/assignments/<stage>.md` (its draft `assignments/drafts/<stage>.md`),
  beside the brief and closed to every role. The session gets it in its first message after the brief and as
  `input/assignment.md`, without the lines its type's row hides (`brief_drop`). The shards of a stage share one.
- What it cannot do: lift what the type's instruction forbids, or name to a reviewing type what its row hides
  (who made the work, what another reviewer found, the budget, a model). A spec writer's assignment asks for the
  skeleton only (intent, requirements, limits, done, out of scope; about one page); data, interfaces, tasks and
  tests are the planner's assignment.
- After the launch the assignment is not rewritten; what a session still owes reaches it through
  `harness resume --message`, written like a follow-up to a subagent.
- Depth is asked for in three places. The type's instruction says how the job is done at depth in any run: a reader
  probes where the material is silent, a planner builds and runs its design before it writes the plan, a writer shows
  a test failing on broken behaviour, a verifier writes checks of its own, a critic reproduces a defect. The
  assignment says what this run needs. The gate refuses what is missing, and the stop hook asks the gate before a
  session may end with `complete` (`harness gate --preview`), so the author repairs its work while its context is warm.
- Before a brief for a role with a domain, read `.claude/ecc/README.md`: it lists every ECC text and skill and the role types
  they suit. The brief names what fits in its `Spec:` line (a copy and its line range) and its `Skills:` line.
