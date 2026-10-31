# Instruction changelog

Versions of the harness instruction set: role types, skills, rules, hooks, settings, stage tables and templates.
The product changelog is `CHANGELOG.md` in the repository root. Newest first; one heading per version.

## 1.16.0
The spec 005 run (`specs/005-spec-writer-rule/spec.md`, `wiki/decisions/spec-writer-writes-the-skeleton.md`).
- Role types: the spec writer writes the skeleton, `output/spec.md` of about one page (intent, requirements, limits,
  done, out of scope; each acceptance criterion mapped to a requirement), and names no data model, interfaces,
  signatures, file lists, line numbers, moves or tests; the planner puts the flesh on it (data, flows, interfaces, tasks
  with files, commands and tests); the validator compares the work with the story and the spec.
- Pipelines: the `software-factory` spec stage writes `output/spec.md` (it was `output/technical-brief.md`) and feeds the
  plan stage; the spec gate checks the five sections, the mapping table and the `[NEEDS CLARIFICATION]` marker, and the
  spec stage has no content checks.
- Skill: `SKILL.md` ("## Owner rules", "## Briefs"), `references/choosing-roles-and-skills.md` and the example briefs say
  that the spec writer writes the skeleton and the planner the flesh, never the reverse; the lessons loop has a third
  step, a rule broken a second time becomes a check in code (`SKILL.md`, `example/lessons.md`).
- Manager's documents: `docs/roles/MANAGER.md` ("## 14."), `ROLE-MAP.md`, `catalogue.md` and `need-to-know.yaml` agree.
- Checks: `harness catalog` and `harness validate` refuse a spec-writer type whose `## Returns` (agent file or contract)
  or spec-stage gate names a data model, interfaces or tests; `harness docs-check` warns about a `specs/*/spec.md` that is
  not under 8,000 bytes (a warning never changes `ok`).

## 1.15.0
The consolidation run (`specs/004-consolidation/spec.md`, `wiki/decisions/ecc-texts-live-under-claude-ecc.md`,
`wiki/decisions/pipelines-run-as-specagent-sessions-from-a-template-skill.md`); the renames and a project's steps are in
`docs/template/MIGRATIONS.md`, 1.6.0.
- Role types: a stage's role type is the key `role_type` in `docs/roles/stages.yaml`, in the files under
  `docs/roles/pipelines/` and in the schemas of the stage table, of a stage's result and of a run's manifest; the agent
  files say role type and SpecAgent session, and `librarian.md`, `test-verifier.md` and `writer.md` preload the skill
  `commit-style`. A row of `docs/roles/need-to-know.yaml` may list `skills:`, which `access.py` unions with the agent
  file's (`writer` and `test-verifier` list `python-patterns` and `python-testing`, the ECC skills for the template's
  own language).
- ECC: every ECC text is under `.claude/ecc/`, and `.claude/ecc/README.md` is its catalogue; `SKILL.md` ("## Briefs")
  and `docs/roles/MANAGER.md` ("## 14.") tell the manager to read it before a brief for a role with a domain
  (`wiki/decisions/ecc-texts-live-under-claude-ecc.md`).
- Skills: the pipeline skill is `.claude/skills/running-specagent-pipelines/` and the skill that adds a role type is
  `new-role-type`; `commit-style` and `doc-gardening` are skills of the checkout, no longer of a plugin, and
  `commit-style` says where commitizen's commit-msg stage runs.
- `CLAUDE.md` and `AGENTS.md`: they say role types, and `just catalog` regenerates `docs/generated/role-types.md`.
- Hooks: `session-start.py` reports the session's role type under the key `role_type`.
- `settings.json` and plugins: the enable entry and the marketplace entry of the commit-convention plugin are gone, and
  so is its folder under `plugins/`; commitizen's commit-msg stage keeps the convention.
- Templates: `templates/role-type.md` is the template of a role type, and `templates/stage-assignment.md` and
  `templates/change-proposal.md` say role type.

## 1.14.0
The shared-base and manager-build runs (`wiki/decisions/the-shared-knowledge-base.md`,
`wiki/decisions/control-plane-in-the-skill.md`).
- Role types: `plan-fixer.md` and `translator.md` (new), the role types `docs/roles/types/plan-fixer.md` and
  `docs/roles/types/translator.md` with their rows in `docs/roles/need-to-know.yaml`
  (`wiki/decisions/plan-fixer-and-translator-are-role-types.md`); `docs/roles/catalogue.md` (new) lists the agents and
  skills a manager chooses from, and a brief takes an ECC text by its line range
  (`wiki/decisions/ecc-text-reaches-a-brief-by-line-range.md`).
- Skills: `running-specagent-pipelines` gains the manager's control plane: the watcher's version 3
  (`_control/registry.json`, orders acknowledged by `ACK <msg_id>` lines and resent by stop and resume, a changed brief
  reloaded with an order, the hand-over at a unit's end past `handoff_at`), `monitor_records.py`, `duty_list.py` and
  `collect_run.py` (new), `scripts/manager/` (new: `catalogue.py`, `preflight.py`, `surface.py`, `measure_manager.py`
  and their README), one page per script under `scripts/docs/` (new), `references/watching.md` (new), the order of
  measures after every run in `references/measuring.md`, and the example agents' settings under `_control/`.
- `CLAUDE.md`: its examples name no sample package (`just test <package>`, `feat(harness): ...`), and its line on the
  owner's vault follows the shared knowledge base.
- Hooks: `session-start.py` names graphify's skill and the user-level pipeline skill link among the work of
  `ops/bootstrap.py`.
- `settings.json` and plugins: Archify's entries and `plugins/archify/` are gone
  (`wiki/decisions/diagrams-are-mermaid-text.md`).
- Templates: `templates/vault/` (new) is the form of a user's vault (`README.md`, `rules.md`, `INDEX.md`, `log.md`, the
  scripts under `ops/`), with the forms `forms/manager-lessons.md` and `forms/learning-record.md`
  (`wiki/decisions/manager-lessons-live-in-the-vault.md`).

## 1.13.0
The template-core run (`docs/decisions/0029-a-checkout-sets-up-its-hooks-sandbox-and-graph.md`,
`docs/decisions/0030-the-template-is-english-only.md`).
- `CLAUDE.md` and `AGENTS.md`: `CLAUDE.md` asks the code graph first (`graphify query --budget 1500`,
  `wiki/graph/index.md`, refreshed by the hooks in `.githooks/`) and gains the section "The owner's vault"; `AGENTS.md`
  lists a new document in `docs/llms.txt` or its folder's README, carries a code change's pages in its commit (ADR-0027)
  and runs database tests on the production engine.
- Hooks: `format-on-edit.py` (new) runs ruff format on a Python file after Edit or Write; `test-alongside.py` (new)
  warns when a new source file has no test; `session-start.py` turns the git hooks on in every session.
- Rules: `docs.md` lists a new document in `docs/llms.txt` or its folder's README and gives a page the owner reads an
  English summary `<name>.summary.md`; `wiki.md` makes the builder a second writer and adds decision pages, the
  12,000-byte limit, `wiki/graph/` and `wiki/plans`; `ecc/` (new) holds ECC's C++, Python and TypeScript rules with
  ECC's `LICENSE` and `SHA256SUMS`.
- `settings.json`: the PreToolUse Write entry runs `test-alongside.py` after `validate-json.py`, and a new PostToolUse
  Edit|Write entry runs `format-on-edit.py`.
- Skills: `running-specagent-pipelines` (new) runs a pipeline of SpecAgent sessions from example briefs, settings, waiters and
  checks, every role sandboxed; `adr` adds a new ADR's line to `docs/decisions/README.md`; the eleven pinned ECC skills
  (new), each with ECC's `LICENSE` and its own `SHA256SUMS`.
- The role type critic (`.claude/agents/critic.md`): the attack stage writes `output/summary.md`, in English, at most
  one page.
- Workflows: `docs-gardening.js` counts a document listed in its folder's README as listed and asks no line for a
  `.summary.md` summary.

## 1.12.0
The revise of wave 1 of the fixes of the audit of 2026-10-04
(`docs/decisions/0025-a-guard-refuses-the-plain-spellings-and-the-boundary-holds-the-rest.md`).
- Hooks: the guards' command reader (`shellwords.py`) takes `#` as part of a word, so a command after `a#b;` is read;
  guard-checkout refuses a Glob whose pattern climbs into the shared checkout or above it, resolving the folder before
  its first wildcard from the search root; the docstrings of guard-checkout, guard-bash and shellwords say that the
  guards refuse the plain spellings and that the sandbox and the write gate hold what a command builds at run time.
- The 1.9.0 entry below said more of the guards than they do; it now names the plain spellings.
- The read block and the write limits a role session gets are the ones of 1.9.0, now held by tests over the settings
  the launcher builds (`packages/harness/tests/test_boundary_settings.py`).
- Made by the manager after the run is integrated, as the run's plan lists it: `.claude/settings.json` closes
  `../runs/_inbox` to the sandboxed commands of every session (`sandbox.filesystem.denyRead`); the quarantine reader
  reads the inbox with the Read tool, which a `denyRead` entry does not stop.

## 1.11.0
The loops inside a run and the attack stage (`docs/decisions/0024-a-run-loops-until-its-reviewers-pass.md`,
`specs/002-run-loop/spec.md`).
- Stage tables: the default and `fix` tables are plan → attack (a critic of the plan and its trial; the human approves
  the plan) → write (one session) → verify → judge, with `returns_to` and a `loop` block (counters `plan` 3 and `work`
  3, `max_runs.write` 5). Every stage of every table runs Opus at max but `classifier` and `quarantine-reader`; the
  model and effort of a table are exact, the creating session changes nothing.
- need-to-know: the critic reads the planner's and the reader's output, the writer and the verifier the critic's, the
  judge the planner's and the writer's (the change as `changes.patch`).
- Gates: `attack` (`result.json proposes accept or revise`, `revise names a blocks or must fix finding, accept none`,
  `every blocks or must fix finding has its evidence entry in result.json`, `output/tests/ holds attack tests under
  their repository paths`, `every attack test is a new file a writer may add`, `every task of the plan is named in the
  critique`, `output/summary.<language>.md is a translated one-page summary`); `verify` (`the verdict proposal is accept,
  revise or reject`, `revise or reject rests on a refuted entry, accept on none`, `every refuted entry has its evidence
  entry in result.json`, `every entry has a number of its own`); `judge` (`verdict.decision is accept, revise, replan
  or reject`); `write` (`the plan's and the critic's tests are on the branch as given`, `the plan's and the critic's
  tests run and pass as given`: their test modules by name, with the pytest plugins of the base's `uv.lock`).
- Agent files: critic steps 10–13 (the stage `attack`); planner, writer, verifier and judge rules for given tests, one
  owner per job, proven documents and rounds; the judge reads the plan and `changes.patch` and may say `replan`.
- `docs/quality/HAZARDS.md`: the classes of input and timing a critic and a verifier try.
- The manager's loop prompt and the resume-stage and run-stage skills resume a round with `--rework`.

## 1.10.0
The loops, the night path and the pause switch (`docs/decisions/0022-a-prompt-loop-is-judged-by-code.md`,
`docs/decisions/0023-one-pause-switch.md`), from run 20261004-121154-fix-w2-state-and-loops.
- The night session of a prompt loop is told the loop's prompt file ("Read `<file>` and do exactly what it says in this
  turn."), which ticks by itself, instead of `/loop-tick <name>`; `ops/night-tick.sh` starts it only when
  `harness loop due` finds work, and hands it the gate actions the pre-check's poll printed.
- A loop file states a prompt loop's success as `exit.check` (`schemas/loop.schema.json`); `docs/loops/poll.yaml` has
  `check: no_active_runs`.
- `harness loop tick` answers `wait` with `paused` while the pause switch is set, and `exit` with the rule `invalid` for
  a context entry it cannot read.
- Made by the manager after the run is integrated, as the run's plan lists them: `.claude/loop.md` (what the session
  does after an `exit` and while the switch is set), `.claude/skills/loop-tick/SKILL.md` (the `paused` wait and the rule
  `invalid`), `.claude/agents/manager.md` (the pause switch under Control).
## 1.9.0
Wave 1 of the fixes of the audit of 2026-10-04: what a role session may write, run and read
(`docs/decisions/0017-the-write-gate-runs-a-branch-s-tests-in-a-sandbox.md` to
`docs/decisions/0020-hooks-and-gates-fail-closed-and-open-nothing-outside-a-stage.md`).
- Hooks: guard-checkout refuses the plain spellings of a command or a path of the shared checkout wherever the shell
  stands, and a search rooted above the repository; guard-bash reads the simple commands of a command (`shellwords.py`:
  wrappers such as `env`, `sudo`, `exec` and `bash -c` taken off) and refuses the plain spellings of a whole-tree
  `git add` or `git commit`, of a shell write of a run's JSON files, of a read of the inbox and of a command of
  `sandbox.excludedCommands` behind a wrapper (`guard-bash.json` version 2: rules are patterns or named checks); what a
  command builds at run time is held by the sandbox and the write gate (1.12.0); stop-gate lets a session stop on an open
  escalation of its stage only, counts its holds in `<run>/logs/stop-gate/` and asks the main checkout's gate;
  compact-output rewrites every pytest form with the command on a line of its own; validate-json checks a run's JSON
  files only. Every guard exits 2 when it cannot decide, permission-request denies, stop-gate lets the stop through and
  logs it, compact-output and skill-audit get out of the way; every hook takes rules, schemas and runs from the main
  checkout.
- A role session's settings: `Edit(...)` deny rules and `sandbox.filesystem.denyWrite` per type, absolute `//` read
  rules, no write path inside the repository, `credentials.envVars` for the messaging token and socket, and the
  instruction files of reviewed work excluded for a reviewer.
- The CLI: a role session runs only `cli.ROLE_COMMANDS`.

## 1.8.0
What a role session reads, the flow files a fix run may change, the cache of a stage at max effort, and a pipeline
for a fix of known defects (`docs/decisions/0015-a-type-that-is-not-blind-reads-what-a-subagent-reads.md`,
`docs/decisions/0016-a-stage-at-max-effort-keeps-its-cache-for-an-hour.md`).
- `docs/roles/need-to-know.yaml`: `repo_deny` holds only what no role reads (`.claude/agent-memory/**`,
  `docs/handoff/**`); the agent files, the stage tables, the policy, `docs/generated/role-types.md` and `design/**`
  moved to `blind_deny`, which `access.type_row` adds for a blind type only. A type that is not blind reads what a
  subagent sent into the repository reads; a test names each exception with its reason (the writer's hidden eval
  cases, the two types that read untrusted text).
- The write gate's scope check keeps `.claude/**` closed to every branch, except the hook scripts under
  `.claude/hooks/` when the run's brief has the line `- Hooks: open`; it sees both paths of a moved file
  (`git diff --no-renames`).
- `permission-request.py` answers yes to an Edit or a Write under `.claude/hooks/` of a session's own checkout in such
  a run, for a type whose checkout is its own work (`HARNESS_OWN_CHECKOUT`), in a session started in the main
  checkout, on a path with no `..` and no link; every other prompt is denied, also one the hook cannot read. Every
  role session's settings say `"disableAllHooks": false`. `templates/project-brief.md` and `docs/roles/MANAGER.md`
  name the line.
- `cache_ttl` is one hour for every type but `classifier` and `quarantine-reader`, which keep a low effort of their own
  and five minutes.
- `docs/roles/pipelines/fix.yaml`: the default table without its reader; the planner starts from the brief and its
  material, the defects of an approved audit.

## 1.7.1
- The documentation rule on decisions (`.claude/rules/docs.md`) says what the repository does with an accepted
  ADR: it is never edited, except for one pointer line under More Information to the ADR that amends or supersedes
  it, as ADR-0006, ADR-0008 and ADR-0009 carry (row 9 of the critique of run 20261003-200017-chat-depth-fix).

## 1.7.0
A role session starts only inside the sandbox, and the machine sets the sandbox up by itself where it can
(`docs/decisions/0013-no-command-to-type-and-at-most-one-password.md`).
- The SessionStart hook of a session that is not a role session sets the sandbox up as this user where that is enough
  (`python3 ops/machine-setup.py --auto`, no password) and tells the session, with the reason, what only the
  administrator can do; it writes nothing to `~/.claude.json`, whose trust record the launcher now writes.
- `sandbox.excludedCommands` holds `python3 ops/machine-setup.py`, `… --user` and `… --undo` by their exact names:
  where the sandbox starts but refuses the namespace, no command runs inside it, root is out of its reach, and the
  user-space way writes in ~/.local. Role sessions are denied them, as every excluded command.

## 1.6.2
- The role rule on the material (`.claude/rules/harness.md`) names the type that is not asked to account as ADR-0012
  does: a type whose agent file lists tools, none of them Write or Bash. Such a type also gets no pieces chosen by
  script (`docs/decisions/0012-a-type-that-cannot-write-accounts-for-no-material.md`).

## 1.6.1
- The role rule on the material (`.claude/rules/harness.md`) says what the gate does since 2026-10-03: a type
  that cannot write a file (neither Write nor Bash among its tools: judge, comparator, quarantine reader,
  classifier) returns its structured result only and is not asked to account for its material
  (`docs/decisions/0008-a-role-session-works-to-a-subagents-depth.md`).

## 1.6.0
Every step of a method is checked (`docs/decisions/0011-every-step-of-a-method-is-checked.md`,
`specs/001-chat-depth/spec.md`).
- Step rules: every numbered step of the Working method of the eighteen role types ends with its rule,
  `<!-- check: ... -->`, in the closed language of `packages/harness/src/harness/gates/steps.py` (`read:`, `ran:`,
  `wrote:`, `output:`, `when:`, `trust:`). The gate checks the rule against the stage's files and the transcript of
  the unit's last session. The rules are `specs/001-chat-depth/step-rules.json`, inserted by
  `ops/insert-step-rules.py`. Once `docs/roles/need-to-know.yaml` gives a type a `steps` mode, `harness validate`
  names a step without a rule, a rule outside the language and an `output:` that names a check no gate of the type has.
- Warn, then enforce: `need-to-know.yaml` gives every type `steps: warn` (one line under `defaults`), and a type's own
  row with `steps: enforce` switches it. In `warn` the new checks (the step rules, every `path:line` names an existing
  file and line, every evidence command was run as the entry says, the content checks of judge, researcher,
  synthesizer and spec-writer) fail no stage: `gate.json` records them under `advisory` and `HANDOFF.md` lists the
  failing ones under `## Gate warnings`. In `enforce` they count in `checks` and in the stop hook's preview. The mode
  is fixed in `manifest.json` when the run is created.
- `harness steps --run <id>` (or `--run-dir <path> [--repo <path>]`) runs the new checks on a finished run, by type
  and step, and writes nothing; it reads a run, so a role session may run it.
- The judge names the source of every reason as `<stage>#<n>`; the spec-writer's technical brief has a Constitution
  section with a row per article of `specs/constitution.md`, and every file of Files to change exists or is marked
  `(new)`. The role rules say where the path of a `path:line` is found; the `new-role-type` skill gives every step its
  rule.
- Model and effort floors: the `model` and `effort` of a stage table are floors for sixteen types. `harness run` raises
  them to the model and effort of the session that runs it (`state.resolve_model_effort`); classifier and
  quarantine-reader keep the table's; `--effort` stands above everything. An effort raised above the table's
  multiplies `max_minutes` by 2 (`xhigh`) or 3 (`max`). `manifest.json` records the chosen values with their source and
  the table's floor, and what was read from the session (`inherited: false` with the reason when nothing could be).
- Templates: `handoff.md` has the section `## Gate warnings`; `role-type.md` asks a new type for the rule of every step.

## 1.5.0
A run ends with integrate or abort (`docs/decisions/0010-a-run-ends-with-integrate-or-abort.md`), and a project keeps its
checkout, its runs and its experiments in one folder.
- The manager ends a run the human gives up with `harness abort --run <id> --reason "<their words>"`, and asks the
  human about every run still open that `harness run` names (`open_runs`). The hint for a unit out of attempts names
  the command.
- `uv run harness abort *` and `uv run harness integrate *` are in `sandbox.excludedCommands`: both stop and remove
  sessions, which a sandboxed command cannot.
- A role session's settings deny it every command of `sandbox.excludedCommands`: those run outside the sandbox, on
  code a writer can change in its own checkout.
- Run state lives in the runs root: `../runs/` when that folder carries `.harness-runs`, otherwise `../<repo>-runs/`.
  The manager's instruction, the council, handoff, intake and run-stage skills, `RUNS.md`, the escalation template and
  `auto-mode.json` name it `<runs root>`; the seven hooks that find run state on their own follow the same rule.
- The internal plugin marketplace is named after the project (`example-repo-plugins`, `<repo_name>-plugins` in a new
  project): `.claude/settings.json`, `extensions.yaml` and `need-to-know.yaml` name the plugins by it.
  (These two changes landed in 5c4e4df..3e29409 without a version of their own.)

## 1.4.0
A checkout sets itself up (`docs/decisions/0009-a-checkout-sets-itself-up.md`).
- Every type that read or wrote code kept `pyright-lsp@claude-plugins-official`; it keeps
  `code-intel@harness-internal` instead: diagnostics after every edit and code navigation for Python, JavaScript and
  TypeScript, PHP, C and C++, HTML and CSS. The servers install on their own; a server starts only for a file of its
  language.
- The JSON hooks validate with the workspace's jsonschema when python3 has none.

## 1.3.0
A role session works to a subagent's depth (`docs/decisions/0008-a-role-session-works-to-a-subagents-depth.md`).
- The first message (`prompt.md`) begins with the type's instruction and the role rules, then the brief, the
  assignment, the stage and the inputs: a subagent has its instruction with its task. The system prompt is unchanged.
- Role rules: complete the task fully, without gold-plating and without leaving it half-done; be thorough; every step
  of the type's method is part of the task, also where the assignment does not name it.
- The material is given whole up to half the model's window (`pack.budget`: 2,000,000 characters on a
  1,000,000-token window, 320,000 on haiku); what does not fit is named before the launch.
- Every type accounts for every file of its material: it heads a section of the output, or it has its row in the
  output's Coverage (a section `Coverage` or `output/coverage.md`); the checks every gate makes fail a file no output
  names. Role rules say it; for a reader its notes' sections and Coverage serve.
- A role session compacts where Claude Code does: `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=100` in its settings.
- Manager and run-stage skill: `harness run --effort <stage>=<level>` raises the stages that decide in a hard run;
  `harness material` before every launch; `launch` refuses `material_does_not_fit`; files that are not text are
  named under `not_text` for the session to open with Read.

## 1.2.0
A role session gets every demand a subagent would get for the same job
(`docs/decisions/0006-a-role-session-gets-what-a-subagent-would-get.md`).
- The manager's instruction is written out (`.claude/agents/manager.md` held headings only). Before the first launch
  of a stage it writes the assignment as it would write the prompt of a subagent, and stores it with `harness assign`;
  `launch` and `status` answer `no_assignment` without one. Template: `templates/stage-assignment.md`.
- Every role type reads the assignment after the brief and treats it as binding. Role rules: work to the depth the
  job needs; a `complete` is held to the stage's gate by the stop hook.
- Every type that works in the repository has the project's `CLAUDE.md` and `AGENTS.md` in its pack, as a subagent
  would have them. Role rules: independent tool calls go out in one turn. Every type keeps its prompt cache for five
  minutes, as a subagent does; the one-hour rows are gone (they cost more and bought nothing in the measured runs).
- The material of a stage is chosen by script and given in the cache (`harness/pieces.py`, `pack.material`): its
  inputs, the brief's material when the stage receives `context`, the pieces the assignment lists under its optional
  `Material`, every place its texts cite as `path:line` with its piece, the short files they name, the pieces that
  match the brief; every line exactly after its number, empty lines left out. The manager writes places as
  `path:line` and lists a piece only when nothing points to it; `harness assign` refuses one that does not exist or
  that the type may not read.
- Hooks: `handoff.py` asks the manager's and a human's session for a handoff in `docs/handoff/` before Claude Code
  compacts it, and to read it back after; `docs/handoff/**` is closed to every role type.
- reader: reads what the goal needs beyond the listed paths (the files the work touches, similar code, the rules a
  change has to pass, derived knowledge); a section Probes with records under `output/probes/`, every record a
  source section with one located fact per result; computes what a later stage would have to compute; an index by
  the points of the brief and a pass over them before it finishes; `WebFetch` for the URLs a brief names; effort `high`.
- planner: builds and runs its design in a checkout of its own before it writes the plan (`EnterWorktree`,
  `trial_checkout`); sections Decisions, Trial and Reference output; `output/trial/trial.patch`;
  "prefer the smallest design" is gone. The plan stage receives the reader's whole output. The plan specifies
  (signatures, contracts, what each test asserts, measured numbers) and does not paste the code; one task per
  checkable change.
- writer: receives the planner's whole output and starts from the trial patch where there is one; the plan wins
  where they differ, and the writer answers for every line.
- writer: tests the edges, shows a test failing when the behaviour is broken, and states its work in `report.md`
  (commits, a claim per task, decisions, what it noticed), which the verify stage receives. verifier: the brief's
  definition of done, its constraints and every statement of the author's report are on its claim list; checks of
  its own under `output/checks/`; the project's rules on the changed files; the tests tested by breaking the code.
  critic: runs the work to reproduce a defect, also on inputs the repository does not hold yet; says what held up;
  evidence for every blocking finding. researcher: `Bash`, probes, effort `high`.
- spec-writer: `Bash`, checks by running how the existing code behaves; "prefer the smallest design" is gone.
  validator: `Bash`, runs the code where reading leaves a doubt.
- Gates: read (probes, their records as sources, two located texts per contradiction), plan (a decision per
  question, the trial, every file of the trial named, a specification and not pasted code), write (a test seen to
  fail, the report), verify (an entry per task of the author, its own checks kept), critique (evidence for
  `blocks`, the work was run).

## 1.1.0
After the first complete live run (`docs/decisions/0005-what-a-live-run-needs.md`).
- Role rules and the knowledge pack are in the system prompt; a role session no longer loads the root `CLAUDE.md`
  and `AGENTS.md` (`docs/decisions/0004-rules-and-pack-in-the-system-prompt.md`).
- writer, test-verifier and librarian enter their own checkout with `EnterWorktree`; verifier, critic and validator
  enter the checkout of the work they receive. `guard-checkout` refuses commands and repository paths before that.
- Every type that has `Write` has `Edit`. Print-stage types list `StructuredOutput`.
- A role session stages files by name; `git add -A`, `git add .` and `git commit -a` are refused.
- The test command of one package is `uv run pytest -q packages/<pkg>`.
- Access table: `models`, `role_rules`, `project_instructions`, `toolchain`, `changes_repository`, `plugin_skills`.
- The verify stage also receives the shard task lists.

## 1.0.0
- Initial set: nineteen role types, the default stage table, six pipelines, six loops.
