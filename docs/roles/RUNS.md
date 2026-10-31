# Run directory layout

Run state lives outside the repository, in the **runs root** beside the checkout: `../runs/` when that folder
carries the marker file `.harness-runs` (a container that keeps a project, its runs and its experiments together;
`uv run harness runs-root --init` makes one, `ops/new-project.py --container` makes a project that way; both
refuse a folder that holds another checkout, whose runs the marked folder would take too), otherwise
`<parent>/<repo>-runs/` (for this repository `<runs root>/`). `uv run harness runs-root` prints it; the
documents call it `<runs root>`. A background session edits inside its own worktree under `.claude/worktrees/` and
Claude Code blocks its writes to the shared checkout, while a write outside the working directory is allowed;
the harness therefore computes this root from `CLAUDE_PROJECT_DIR` (`state.runs_root`) and hands it to every
session with `--add-dir`; sandboxed commands may write to an added directory by default. Nothing here is committed.

    <runs root>/
      _audit/                      hook logs of sessions that are not part of a run
      _audit/night-tick-<date>.jsonl   why a fire of ops/night-tick.sh started no session (`harness loop due`), and its stderr
      _audit/night-tick/<loop>-<UTC time>.json   the output of one night session; `harness loop tick` counts its cost
      _briefs/<slug>.md            briefs written before a run exists; `harness run --brief` copies one into the run
      _inbox/<slug>/               untrusted text copied by `harness inbox`; only a quarantine-reader session opens it
      _loops/<name>/state.json     loop state: episode, iterations, last run, last exit (`schemas/loop-state.schema.json`)
      _pause.json                  the pause switch, while the human holds the harness: when and why (ADR-0023)
      <run-id>/                    <yyyymmdd-hhmmss>-<slug>
        manifest.json              immutable after creation; session ids per stage and shard
        state.json                 every transition and the configuration fingerprint; written only by `harness`; `loop` holds the rounds per counter, their history, a round whose files are still moving and a stop that waits for the human; a unit in a loop has the status `rework` or `recheck` and its `round_start`
        brief.md                   the project brief (layer 2)
        assignments/<stage>.md     the manager's assignment of a stage: what it would write into the prompt of a subagent for the job; stored by `harness assign` before the first launch (drafts under `assignments/drafts/`); no role can read it
        HANDOFF.md                 rendered by `harness handoff`; read this first
        logs/polls/                `claude agents --json` snapshots, one per poll
        logs/notified.json         the actions that need the human in the last poll that told them, and `done`
        escalations/<NNN>.json     questions for the human; answered in place
        locks/<stage>[-NN].lock    one launch at a time per unit (stage, or shard NN); removed by poll when the session is gone
        _access/                   what each unit was given: `<unit>.inputs.json` (sources and hashes), `<unit>.work.json` (the work commit and its branches); no role can read it
        stages/<stage>[/<NN>]/     one directory per stage (per shard for `parallel: per_task`)
          prompt.md                the first message the session received: the type's instruction and rules, the brief, the assignment, the stage, the input paths
          pack.md                  role rules and knowledge pack appended to the system prompt; written at launch, and again when the unit checks again after a round
          input/                   read-only copies of this stage's declared inputs (harness/access.py); `assignment.md`, the assignment as the type may see it; for committed work `<alias>/changes.patch`
          progress.md              done / tried and failed / next / open, rewritten at every checkpoint
          tasks.json               a writer's tasks, beside result.json: every task of the plan for one writer, or in a wave this shard's dependency-closed part, written by `harness launch`; `passes` flags
          rework.md                the findings a stage answers in its next round, written by `harness poll` (harness/rounds.py); `--rework` delivers it
          rounds/<n>/              what the unit made in round n: result.json, gate.json, a reviewer's output/, copies of a writer's report.md, tasks.json, checks.json
          report.md                write stage: what the author states about its work (commits, a claim per task, decisions, what it noticed); the verify stage receives it
          output/                  deliverables that are files; committed work is on the unit's branch instead; a reader's `probes/`, a planner's `trial/`
          result.json              `schemas/stage-result.schema.json`
          gate.json                `schemas/gate-verdict.schema.json`
          checks.json              write stage: the commands the gate ran on the unit's branch outside any session (the whole suite, in a sandbox of its own without the gating process's environment, `docs/decisions/0017-the-write-gate-runs-a-branch-s-tests-in-a-sandbox.md`), with exit code and the end of the output; the verify stage receives it with the work
          logs/                    launch.txt, hook logs (instructions, session-end, skills, stop-failure), `test-*` (full output of a test run), print.json (the output of a print run; a failed one leaves `last_error` in state.json)

A run's `state.json`, its `logs/notified.json` and a loop's `state.json` each have one lock, `<file>.lock` beside the
file: every writer holds it around its read, change and write, never while a session or a gate runs, and writes
through a temporary file of its own, `<file>.<pid>.<random>.tmp`, that a rename puts in place
(`docs/decisions/0021-one-writer-at-a-time-for-run-and-loop-state.md`). A lock file that stays behind holds nothing.

While a session's sandboxed commands run, its stage directory holds an empty, read-only file for each run file
that does not exist yet (`result.json`, `tasks.json`, `escalation.json`, `gate.json`, `checks.json`, `.mcp.json`): the
mount points of the sandbox's denyWrite rules. The harness reads an empty run file as absent and replaces one it
writes; the session's Write tool replaces it too.

Paths inside `manifest.json` are relative to the runs root. An `outputs` path in `result.json` is relative to the
stage directory (`output/notes.md`); for kind `code` it is a repository path on the unit's branch. Never edit a
running stage's files; answer escalations in `escalations/<NNN>.json`.

Checkouts live in the repository, not here: `.claude/worktrees/<run-id>-<stage>[-NN]` on the branch
`worktree-<run-id>-<stage>[-NN]`. After the last approval `harness integrate --run <id> --clean` builds the branch
`run/<run-id>`, removes the checkouts and takes the run's sessions out of the session list
(`docs/architecture/harness.md`). A branch built before is never rewritten: with `--clean` the run is only cleaned,
and the branch is built again after the human deleted it.

A run the human gives up ends with `harness abort --run <id> --reason "<their words>"`
(`docs/decisions/0010-a-run-ends-with-integrate-or-abort.md`): its sessions are stopped and leave the session list,
its checkouts go, the run folder and branches with commits stay, and `state.json` records `status: aborted` with
`aborted: {at, reason, from}`. No command changes an aborted run, and a role session steers none: with
`HARNESS_ROLE` set only the commands listed in `cli.ROLE_COMMANDS` run, the gate preview its stop hook asks for among
them (`docs/decisions/0019-a-role-session-runs-only-the-harness-commands-listed-for-it.md`), and a role
session's settings deny it every command of `sandbox.excludedCommands` (they run outside the sandbox). A run that
committed nothing, such as a planning run, is closed with `harness integrate --run <id> --clean` alone. Whichever command removes a checkout first saves
its uncommitted work (tracked and untracked files; ignored files are made again and not kept) as one commit under
`refs/harness/salvage/<run-id>/<checkout>`; `git worktree add <dir> <ref>` brings it back. `poll` stops the idle
session of a stage that is done and needs no approval; `harness resume` continues it. `state.json` records
`changed_at`, the last change of a status, gate, approval, attempt count or escalation; `updated_at` is the last poll.
`harness doctor` names what earlier runs left behind, each with the command that removes it.
