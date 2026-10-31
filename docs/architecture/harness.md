# Harness architecture

## Components
- Manager session (`.claude/agents/manager.md`) — the human's only chat.
- Role types (`.claude/agents/<type>.md`) — one file per role; body = default instruction (layer 1).
- Project brief (`<runs root>/<run-id>/brief.md`) — layer 2; the first user message of every role session.
- Stage assignment (`<runs root>/<run-id>/assignments/<stage>.md`) — what the manager would write into the
  prompt of a subagent for the stage's job; it follows the brief in the first message. No stage starts without one.
- Stage table (`docs/roles/stages.yaml`) — order, modes, gates, approvals.
- Access table (`docs/roles/need-to-know.yaml`) — what each type receives, reads, keeps and may run on.
- Knowledge pack (`harness/pack.py`) — role rules, the type's pack files and wiki pages, appended to its system prompt.
- harness CLI (`packages/harness`) — launch, poll, resume, gate, approve, integrate, handoff, catalog, select, validate.
- Hooks (`.claude/hooks/`) — SessionStart context, checkout guard, Bash guard, test output, JSON validation, Stop gate, config freeze, audits.

## Run lifecycle
created → running (stage launched) → working/blocked/stopped (polled) → done + gate → approval (if any) → next stage → done → `harness integrate`.

## How a role session starts
`launch.session_flags` builds the flags of every start, every resume and every eval trial:

| Flag | What it carries |
| --- | --- |
| `--agent <type>` | the type's agent file becomes the system prompt |
| `--append-system-prompt-file <stage>/pack.md` | role rules and knowledge pack, written once at launch |
| `--tools` | the tool list of the agent file |
| `--settings` | deny rules and the read block, sandbox allowances, the `env` block, the model, cache lifetime, plugins and skills of the type |
| `--model`, `--effort` | the stage's, as the manifest fixed them when the run was created; a resume does not restore them, so they are passed every time |
| `--add-dir` | the stage directory and what the type's row opens |
| `--setting-sources project,local`, `--strict-mcp-config`, `--no-chrome` | nothing of the user's own configuration reaches a role session |

- The `model` and `effort` of a stage table are exact (ADR-0024): `harness run` writes them into `manifest.json` as
  the table has them (`state.choose_stage`). The model and the effort of the session that runs it are read from its
  transcript (`state.resolve_model_effort`) and recorded under `session`; they change no stage. `--effort
  <stage>=<level>` changes one stage for one run; an effort raised above the table's multiplies the stage's
  `max_minutes` (×2 on `xhigh`, ×3 on `max`). Every stage records the `source` of each value and its `floor`.
- The first user message is `prompt.md`: the type's instruction and the role rules (also in the system prompt; here
  they stand with the task, ADR-0008), the brief and the assignment as the type may see them, the stage, the input
  paths, the worktree name. `harness status` and `harness launch` answer `no_assignment` until the manager has stored
  the assignment with `harness assign`; a text without the sections `Deliver`, `Prove` and `Done when` is not one.
- A background session inherits the environment of Claude Code's background service, not of the launching command.
  What a session needs travels in the `env` block of `--settings` (`state.harness_env`, `access.env_extra`).
- A print stage (`mode: print`) is one `claude -p --json-schema` call. Its result returns through the
  `StructuredOutput` tool, which the type's agent file must list; a final message that is the same JSON is taken too.
- The rules the settings and the hooks hold whatever a session is told:
  [What settings and hooks enforce](harness-enforcement.md).

## The two caches
- State: `<runs root>/<run-id>/` files (outside the repository, reached with `--add-dir`) + fixed session ids + supervisor restarts + `CLAUDE_CODE_RETRY_WATCHDOG`.
- Instruction: agent file, role rules and pack in the system prompt (`--agent`, `--append-system-prompt-file`), the instruction and rules again with the brief and assignment in the first message, frozen tool set during a run, `promptCacheTtl` per type.
- Memory by type (working, episodic, semantic, procedural) and the two stores Claude writes itself: [memory.md](memory.md).

## How committed work travels
- A type with `changes_repository: true` (writer, test-verifier, librarian) commits on a branch of its own, in the
  checkout `.claude/worktrees/<run>-<stage>[-NN]`, which its session enters with `EnterWorktree`.
- Before a stage that depends on such a stage starts, `work.prepare` builds one work commit (the base plus the
  change of every shard, neutral author, no trailers), a checkout of it for the new stage, and
  `input/<alias>/changes.patch`. Shards that change the same lines refuse the launch (`work_conflict`).
- `guard-checkout` refuses the plain spellings of a command or a path of the shared checkout wherever the shell stands,
  also from inside the session's own checkout: the directory a session starts in is the base without the work. Once
  the session has entered its checkout, its sandbox hides the shared checkout from every shell command
  (`docs/decisions/0025-a-guard-refuses-the-plain-spellings-and-the-boundary-holds-the-rest.md`).
- A type with `trial_checkout: true` (planner) gets a checkout of its own as well, to build and run its design
  before it writes the plan. Nothing in it is integrated: the launcher removes the checkout and its branch when a
  stage that takes the plan starts (`launch.drop_trials`), except a stage that returns to the planner: the critic of
  the stage `attack` gets its own checkout of the base with `trial.patch` applied (`work.trial_commit`), and the
  planner's checkout stays while the plan may come back. A trial that changes the flow's configuration gets no
  checkout (`_common.closed_to`). What the planner built reaches the writer as `output/trial/trial.patch` among its
  inputs, a reference to start from; the test files it adds are kept as given (the write gate's protected tests).
- After the last approval `harness integrate --run <id> [--clean]` builds `run/<run-id>`: the first writer's commits
  as they are, later stages' own commits replayed on top. The human merges that branch. With `--clean` the run's
  checkouts are removed and its sessions leave Claude Code's session list (`claude stop`, `claude rm`); the
  transcripts stay where `cache-report` reads them. An existing `run/<run-id>` is never rewritten.
- `harness abort --run <id> --reason <text>` ends a run that will not be integrated (`work.abort_run`,
  `docs/decisions/0010-a-run-ends-with-integrate-or-abort.md`). A command that changes a run refuses an aborted one
  (`cli.RUN_COMMANDS`, `state.refuse_aborted`); `poll` reports it without writing. A checkout goes only after its
  uncommitted work is saved (`work.remove_checkout`, `refs/harness/salvage/`). `poll` stops the idle session of a
  finished stage. `harness.leftovers` names what runs left behind, for `harness doctor` and `harness run`.

## What poll decides
| What `claude agents --json` and the files say | Unit becomes | Action |
| --- | --- | --- |
| `done` | gated | `gate`, or `resume` with the failed checks |
| `blocked` with `waitingFor` | blocked | `attention` |
| `blocked` or `working`, idle, final `result.json` (for `working`: the log ends with a finished turn) | gated | as `done` |
| `working`, idle, log silent for 180 s, no final result | stopped | `resume` with a message |
| stopped with a complete result | gated | as `done` |
| a limit or an API error ended the turn | unchanged | `wait` until the reset, or `limit_human` |
| attempts used up | unchanged | `max_attempts` |

The retry rule lives in `poll.py` and nowhere else. `harness watch` polls until an action needs the manager.

## A session is held to its gate before it stops
- The Stop hook lets a role session end only with a final `result.json`. For `complete` it first asks
  `harness gate --preview` (`gates.preview`): the stage's checks without the commands a gate runs outside a session
  (`session_checks` of a gate module, where it has one). Failing checks send the session back with their names,
  while its context is still in the prompt cache; that is cheaper than a stop, a poll and a resume.
- A unit is held at most three times; then, and whenever the preview cannot be had, the stop is allowed.
  `harness gate` stays the verdict.
- What the gates ask for beyond form: a reader's probes with their records, a planner's decision per question of the
  reader and the trial of its design, a writer's test seen to fail on broken behaviour, a critic's evidence for
  every blocking finding.
- Every gate also runs the checks of `specs/001-chat-depth` (`gates.new_checks`): the rule of every step of the type's
  method against the unit's last session transcript, every `path:line`, every evidence command, and the content
  checks of judge, researcher and synthesizer. The steps mode the manifest fixed for the stage decides
  their weight. In `warn` they are advisory: `gate.json` records them under `advisory`, outside `passed`, the failing
  ones are listed in `HANDOFF.md` under `## Gate warnings`, and the preview does not hold the session on them. In
  `enforce` they stand among the stage's checks: a failing one fails the gate and the preview holds the session.
  `harness steps --run <id>` runs them on a finished run and writes nothing.

## Parallelism
- `parallel: per_task` — one `harness launch` call partitions the planner's tasks by dependency component (a task and everything it depends on stay together; largest components first to the least loaded shard; at most `max_shards` shards) and starts one session per shard on its own worktree branch; `tasks.json`, lock, gate and resume are per shard; the stage is done when every shard's gate passed.
- `parallel_with` — two reviewing stages run at the same time from the same work commit (software-factory: accept
  and validate). The default and fix tables have none since ADR-0024: the critic attacks the plan before the work,
  and verify reads its findings.

## Loops
- A stage with `returns_to` sends its proven findings back when its verdict is `revise` (`harness/rounds.py`): the
  stage it returns to gets `rework` and `rework.md`, every launched stage after it `recheck`; `harness resume
  --rework` continues them. The table's `loop` block bounds the rounds per counter and the starts of a stage; a
  bound, a round that repeats the findings of the one before, and the judge's `replan` or `reject` stop the run for
  the human, who answers with `harness approve`. The round is saved in `state.json` before its files move under
  `rounds/<n>/`.

## Module map (`packages/harness/src/harness/`)
One row per module and what it owns: [Harness module map](harness-modules.md).

## Adding a command
1. A function in the module that owns the data; it returns a dict with `ok`.
2. A subparser and a branch in `cli.py`.
3. A test under `packages/harness/tests/` that needs no Claude.
4. A row in `packages/harness/README.md`.
5. When the command writes under `docs/generated/`: a function that renders the text from its source, and a
   comparison of the file with that text in `catalog.docs_check`.
