# Changelog

All notable changes are recorded here, grouped by release, generated from Conventional Commits by the `release` skill.

## [Unreleased]

### Added
- The template steps of 2026-11-02, from a project's run of that day and the owner's orders: `lessons_report.py` takes
  `--repo <checkout>` (and `--projects`) and counts a recurrence only when the session that made the error held the
  lesson (the commit's `Role-Session:` trailer names the session; a lesson dated `added <ISO>` after that session's
  start makes the repeat `not_held`, and no recurrence; a session or lesson date unknown makes it `held_unknown`, which
  still counts), and the builder briefs end each commit with `Role-Session: $CLAUDE_CODE_SESSION_ID`;
  `measure_manager.py lessons` accepts `cost unmeasured` and a firing's `no record` and prints
  `unmeasured: <n> (items …)`; `scripts/task_lint.py` checks a task's `Step 0` count, its `Expected:` lines and its
  python under the repository's own ruff before the planner writes `Task N: written`; guard-bash's `relative_cd` check
  refuses a relative `cd` or `pushd` into a subfolder of a linked worktree, where the sandbox lays `/dev/null` stubs;
  `wait_for_ready.py --index <00-index.md> --lane <a|b>` releases a builder's task by its own lane and the index's
  build order, so the other lane's open ids no longer hold it. The skill's briefs and references carry the rules that
  run taught, each with its reason and pinned by a test: seven task rules for the planner and the plan fixer, the
  builders' mutation, set, pattern and base-gate rules, the `wait_for_log.py` count, one line in the critic's
  checklist, the missing Chromium of a role's sandbox, a web layout checklist and the plan fixer's capacity (Task 6).
  The vault form gains the owner's orders `measure-the-effect-of-every-improvement`, `verify-every-template-change` and
  `agent-orders-give-the-reason-without-shouting` (Task 7). The warm cache by rule and the frozen pack per lane carry a
  `measure:` line with their numbers before and after (Task 8). `watch_agents.py --launch <agent> [--dry-run]
  <config>` starts the first session of a role added in the middle of a run, which the watcher then adopts by name
  (Task 9). Every order in a brief gives its reason in one clause and none shouts, and the pre-flight's `wording` check
  refuses a pack whose files hold a capitalised alarm word or an exclamation mark outside a code span, a fenced block
  or a quote (Task 10). The README and `references/measuring.md` say so (Task 11).
- The run's own gaps of 2026-11-01, closed at the template so a new project starts right: the watcher delivers an
  order to a role with no process or a final record (once, no hand resume, no second copy); `catalogue.py fill`
  pastes each brief's ECC ranges and the pre-flight refuses an unfilled brief; `.claude/hooks/keep-cache-warm.py`
  keeps every role's prompt cache warm by rule (no foreground call past 210 s, a keep-alive at a turn's end for up to
  an hour); a session without its lane's pack hands over at its unit end and a finished one wakes fresh with it;
  the pre-flight checks each role's model class (large for judgment roles, mid-size for the builder, top for the
  spec writer); `.claude/hooks/language-gate.py` holds the manager chat to the user's language; the vault form gains
  cache-and-compaction, manager-replies-in-the-users-language and no-one-agent-mode. The README's cache and
  manager-chat sections and ARCHITECTURE.md say so.
- The README rewritten for a reader on GitHub under the name SpecAgent: a banner (`docs/assets/banner.svg`), what the
  system does and how it differs from subagents (11 properties side by side), each strength with its evidence, the run
  loop (the spec-writer first when no spec exists), the roles, the knowledge layer and a session's life, each a picture
  drawn by the archify skill from `docs/assets/src/` (`run-loop.svg`, `roles.svg`, `knowledge.svg`, `session-life.svg`;
  their Mermaid text is `docs/assets/src/README.md`), the manager chat (what it does that the sandbox refuses the roles,
  its four guards, the four kinds of question it asks you), the measurements of 2026-10-30 and the platforms.
  Three documents carry the detail: `docs/how-it-works.md` (one run start to end, each step with who acts, the record
  it writes and what closes it, then step by step; the record files, what a role session may touch and the end of a run
  are on pages of their own, `docs/files-of-a-run.md`, `docs/what-a-role-may-touch.md` and `docs/the-end-of-a-run.md`),
  `docs/comparison.md` (a subagent and a role
  session on 15 properties, with the measured numbers) and `docs/economy.md` (time, money and what quality costs).
  `ARCHITECTURE.md` says where everything lives and draws the layers and one stage
  of a run as Mermaid diagrams; `docs/assets/sandbox.svg` and `docs/assets/records.svg`, drawn by the archify skill from
  the specs in `docs/assets/src/`, picture a role session's sandbox and the record files of a run.
- The checkout is a claude-obsidian vault (owner, 2026-10-30; `wiki/decisions/the-checkout-is-a-claude-obsidian-vault.md`):
  `ops/adopt-obsidian.py` declares the plugin (`obsidian-vault@<marketplace>`, a github source installed from git at
  project scope by bootstrap), adopts the checkout with the plugin's own command (`.claude-obsidian.json`, `.obsidian/`
  at the root, `.raw/`, `inbox/`, `wiki/hot.md`, `wiki/overview.md`, `wiki/meta/ledgers/`), keeps the plugin's lint
  clean (`just wiki-lint`, part of `just validate`; `.vault-meta/lint-allowlist.json`) and sets
  `CLAUDE_OBSIDIAN_SESSION_CONTEXT=1`, so every session starts with `wiki/hot.md`. Pages carry `created` and `tags`
  (`schemas/wiki-page.schema.json`). The vault settings moved from `wiki/.obsidian/` to `.obsidian/`; a project on
  1.5.0 runs `python3 ops/adopt-obsidian.py --apply` after taking the template's files.
- `ops/obsidian-ingest.py` puts pages already in the wiki into the vault's ledgers (owner, 2026-10-30): a page's text at a
  commit is captured into `.raw/captured/`, and one `ingest` operation of the plugin writes its source, one claim per
  rule (the bullets of its `## The rule`, else its sentences) with the lines they cite, its entry at the top of
  `wiki/log.md` and its line in `wiki/hot.md`; the page and its summary stay as they are. `--dry-run` prints the
  bundle, `--all-decisions` lists the `wiki/decisions/` pages in no source yet. `wiki/log.md` now keeps the plugin's
  entries newest first at the top and the hand-written ones below them. A source is due 365 days after it is recorded
  (the plugin's gate refuses every operation of a vault with one source past its date): `--due` lists the pages due
  within 30 days, `--refresh` renews them and the pages named in one operation, and `ops/night-tick.sh wiki-ingest` runs
  it each night. A page changed after its ingest (a decision revised as `.claude/rules/wiki.md` says) is held back by
  `--refresh`, and `--supersede <page>` records its new text as a new source, supersedes the old one and deprecates its
  claims, in one operation that renews the due pages. A page in a source is never removed (the plugin refuses every
  operation of a vault whose claims cite a missing page): a decision that turned out wrong is `withdrawn` and recorded by
  `--supersede`, and the driver stops with that way out when a page is gone. All forty decision pages are ingested.
- The pipeline's economy: hand-over, unit size, verifier cadence and facts pack (owner, 2026-10-30;
  `wiki/decisions/pipeline-economy-hand-over-units-checks-facts-pack.md`): a session writes its hand-over note at its
  unit's end, and the watcher's unit-end order waits `unit_end_grace` (600 s, `0` = at once; a config without the key
  takes 600) for it; a repeat's unit is sized `k = floor((handoff_at - start) / per-item)` to end under `handoff_at`
  (ingest: 5 pages, not 9), and a builder ordered to hand over inside a unit writes `Unit size: <k> -> <k-1>`; the
  verifier checks repeat units in pairs at the later commit (`Repeat units:` in its assignment), a driver's replay once
  per driver and the full suites once at the end; the manager writes a facts pack `_inputs/<topic>.md` before the
  launch, which the briefs name in place of a tool's documentation (it and a hand-over note are sized so a fresh session
  starts under about 60k tokens). `score_run.py` prints an economy row after its
  tables (`--json`: `economy`): units, cost, sessions, copies and findings per unit, and escaped; the ingest run's row
  is `5 | $8.60 | 4.6 | 1.8 | 1.0 | 0`.
- The pipeline's economy, second part: the estimate, the model classes and the open items (owner, 2026-10-30;
  `wiki/decisions/pipeline-economy-estimate-model-classes-open-items.md`): a launch's `Estimate:` line names the last
  run's measurement page, its dollars per session and its start-up read, and `preflight.py` fails a line without one of
  the three; `preflight.py check` lists `claude agents --json --all` and fails on a busy session outside the run, in the
  checkout or its worktrees, that no `Live:` line of the launch file names; the class text names three classes by the
  work, specification (spec writer), judgment and mechanical (the builder is no longer a fixed judgment role, effort max
  for every role, no skill file names a model); `ops/night-tick.sh` commits the renewal on `main`
  (`chore(wiki): renew the due sources (night tick)`, only `wiki/meta/ledgers`, `wiki/log.md` and `wiki/hot.md`; another
  branch or a refused commit is logged as `renewal not committed: <reason>`); a finding's cause may be `(brief)` in a run
  without a planner; `ops/obsidian-ingest.py lint` stops on a plugin answer without `summary.category_counts`; the
  supersede loop is a recorded to-check in `docs/architecture/knowledge.md`.
- No commit of a role names a model (owner's order, 2026-10-30; the same decision page): every role's settings carry
  `"includeCoAuthoredBy": false`, which blanks the `Co-Authored-By` trailer of Claude Code's default commit text (the
  seven `example/*-settings.json`, `references/launch.md`, `references/sandbox-and-blindness.md`), and `preflight.py`'s
  `blind` check fails a settings file where the key is absent, `true` or no boolean, and one with an `attribution`
  key, whatever it holds (V1: a valid object wins over the key and can bring the trailer back). The run generator's
  templates (`_control/make_run.py`) are the main session's to change.
- The spec-writer check (owner, 2026-10-31; `wiki/decisions/spec-writer-writes-the-skeleton.md`): `harness validate` and
  `harness catalog` refuse a spec-writer role type whose `## Returns` section, in `.claude/agents/spec-writer.md` or
  `docs/roles/types/spec-writer.md`, names a data model, interfaces or tests, and a spec stage gate that requires one;
  `harness docs-check` warns about a `specs/*/spec.md` of 8,000 bytes or more, since a longer spec is a sign the brief
  asked for the plan (`packages/harness/tests/test_spec_writer_check.py`).
- The cache in dollars (owner, 2026-10-31; `wiki/decisions/the-cache-is-measured-in-dollars-and-set-per-role.md`):
  `usage_report.py` prints cache reads, cache writes and output as dollars, each after its token count (`rd $`, `wr $`
  and `out $`; `usage_report.dollars()`), one usage per message id; `score_run.py` adds `read $`, `write $` and `output
  $` to its role table, and its economy row a "cache write $ per unit" column; `docs/economy.md` has the measurement of
  2026-10-31 (the readme writer's $129.61 is 31% cache reads, 29% cache writes and 40% output; at 5m a cache write costs
  37.5% less, a net of +$13.49 for that writer after its rewrites) and names its source, the vault page
  `context/measurements/2026-10-31-cache-ttl.md`.
- `make_pack.py --no-note` (owner, 2026-10-31; the same decision page) leaves every `handoff-*.md` file out of a pack,
  so that a pack holds only what is identical across a role's sessions; packs stay off until a run measures one in
  dollars.
- `CLAUDE_CODE_PROMPT_CACHE_TTL` per role (owner, 2026-10-31; the same decision page): the settings `env` of the seven
  `example/*-settings.json` sets `5m` for the builders and the planner, which wait on no other role, and `1h` for the
  verifier, the critic, the plan fixer and the judge, which do; `references/launch.md` has the rule and a table. It is
  the rule for the SpecAgent role sessions launched with the skill's settings: the harness's stage types keep the hour
  that `docs/roles/need-to-know.yaml` sets (ADR-0016).
- `ops/tests/test_reading_order.py` (owner, 2026-10-31): it fails on a text of the template that gives a fresh session's
  reading order with the hand-over note before the shared files, and on a watcher text that does (the lessons loop's
  third step: a rule broken a second time becomes a check in code).
- Version 1.7.0 of the template (`docs/template/VERSION`) with its entry in `docs/template/MIGRATIONS.md`, and roles
  1.16.0 (`docs/roles/CHANGELOG.md`).
- The template carries the global rules (owner, 2026-10-31; `specs/006-global-decisions/spec.md`): a global page is a
  lesson (a proof page under `context/` is mandatory) or an order (the owner's standing decision on how the work is
  done: no proof, a `review:` date one year on, never deleted for lack of a proof). `ops/sync-vault-globals.py --vault
  <path>` copies into `templates/vault/decisions/global/` every page of the vault's `decisions/global/` that says
  `template: yes` and is an order, or a lesson whose proof page exists, with the measurement pages they cite and their
  lines under `## Decisions (global)` of `templates/vault/INDEX.md`; it drops from a closing `Related:` paragraph the
  entries whose page does not travel, and refuses, without writing it, a page that holds a Georgian letter, a model
  name, an owner marker or anything the form's `ops/check_pages.py` refuses (it never writes the vault). Its first run
  carried 30 pages (3 lessons, 27 orders), refused 19 with their reasons and skipped 12 (`template: no`);
  `ops/new-vault.py` copies `templates/vault/` whole, so a new vault starts with them
  (`ops/tests/test_sync_vault_globals.py`, `ops/tests/test_new_vault.py`).
- `templates/vault/ops/check_pages.py` refuses a global page without `kind: lesson` or `kind: order`, a lesson without an
  existing proof page under `context/`, an order without `review:`, a quoted text of the owner (a quote with a Georgian
  letter, or whose words are mostly not English), a Georgian letter in a global page, a global page or a candidate over
  4,000 bytes (the manager's lessons page: under 8,000, the limit its form states) and a candidate in
  `context/candidates/` past its `review:` date (`ops/tests/test_check_pages.py`: a test per refusal).
- The way in and out of a global page is the manager's end-of-run routine, next to the measurement page
  (`docs/roles/manager-chat.md`, "## After a run"): the main session proposes a rule with its proof page, the page
  enters on the owner's yes, and it is marked `withdrawn` with the record's path when a run's verifier records its
  `would_change_if` case.
- Every template change carries its migration line (owner, 2026-10-31): `docs/template/MIGRATIONS.md` keeps an
  `## Unreleased` entry above the versions, and `ops/tests/test_migrations_entry.py` (run by `uv run pytest -q`) fails
  when a path changed since the last release is not named in the newest entry, and when a commit changes a
  template-owned path and adds no line to it.
- Version 1.8.0 of the template (`docs/template/VERSION`) with its entry in `docs/template/MIGRATIONS.md`, and roles
  1.17.0 (`docs/roles/CHANGELOG.md`).

### Changed
- The lessons loop is a ladder written once (owner, 2026-10-31): in the pipeline skill's `SKILL.md` ("Briefs") a finding
  is recorded in the run, a cause shared by two findings becomes a rule in the run's `lessons.md`, a cause found in two
  runs becomes a rule where its reader is, a rule broken a second time becomes a check in code, and the proof exists
  before a rule cites it; `docs/roles/manager-chat.md`, `templates/vault/rules.md` and the skill's `example/` and
  `references/` point to it.
- The template is named SpecAgent, one word, read as "special agent" (owner, 2026-10-30;
  `wiki/decisions/the-template-is-named-specagent.md`): the README title, the line `ops/new-project.py` prints, the
  description in `docs/template/DESCRIPTION.txt` and every text that gave the old name AFTPro say SpecAgent; the
  repository is renamed `specagent` at the public push and the old address redirects, and `~/aftpro-commons` and the
  marketplace name `example-repo-plugins` keep their names.
- Every ECC text lives under `.claude/ecc/` (owner, 2026-10-30; `wiki/decisions/ecc-texts-live-under-claude-ecc.md`):
  the 70 agent texts, byte for byte, and the pages about the pin moved from `docs/references/` (`ecc-agents/` is
  `.claude/ecc/agents/`, `ecc-<page>.md` is `.claude/ecc/<page>.md`), and `.claude/ecc/README.md` is a catalogue, a line
  per text, per ECC skill and for the rules, which the manager reads before a brief for a role with a domain; a row of
  `docs/roles/need-to-know.yaml` may list `skills:`.
- The two skills of the `harness-conventions` plugin are skills of the checkout (owner, 2026-10-30): `commit-style` and
  `doc-gardening` live in `.claude/skills/`, `librarian`, `test-verifier` and `writer` preload `commit-style`, and
  commitizen's commit-msg stage, which `pre-commit install` writes beside the pre-commit stage
  (`default_install_hook_types` in `.pre-commit-config.yaml`), keeps the commit convention; CI validates
  `./plugins/code-intel --strict`.
- Finished plans live in `docs/exec-plans/done/` (owner, 2026-10-30;
  `wiki/decisions/finished-plans-live-in-exec-plans-done.md`): `manager-build/` and `pipeline-fold/` moved there from
  `active/` with their history, `done/README.md` lists them and `docs/llms.txt` links it, `harness docs-check` accepts a
  plan folder listed in `active/` or in `done/`, plan-lint reads `active/` only, `exec-plans/completed` became
  `exec-plans/done` in the text, `manager-build` stays out of new projects through the `omit:` list and `pipeline-fold`
  is copied.
- The ADRs of `docs/decisions/` and the decision pages of `wiki/decisions/` stay two stores (owner, 2026-10-30;
  `wiki/decisions/adrs-and-decision-pages-stay-two-stores.md`): a paragraph in `docs/decisions/README.md` and a sentence
  in `wiki/index.md` say which holds what; no ADR changes its number or its decision.
- No tracked text of the template names the language or the circumstances of its owner (owner, 2026-10-30), except the
  captured sources of its wiki (`.raw/captured/`) and the claim ledger (`wiki/meta/ledgers/claim-ledger.json`), which
  keep the text of the pages as they were ingested: the lines that did, `CHANGELOG.md` and `docs/template/MIGRATIONS.md`
  among them, say it in neutral words, and a rule about a refused block names the block, not a language.
- A project made by `ops/new-project.py` has a README of its own (owner, 2026-10-30): the script writes a stub
  `README.md` named after the project, keeps this repository's README at `docs/template/README.md` with its links
  re-rooted and lists it in the project's `docs/llms.txt`; the page about creating a project and receiving updates, which
  had that path, is `docs/template/PROJECTS.md`, and an update never touches a project's `README.md`.
- The names after "chat agent" follow SpecAgent (owner, 2026-10-31;
  `wiki/decisions/pipelines-run-as-specagent-sessions-from-a-template-skill.md`): a chat agent is a SpecAgent session
  and a chat type is a role type, so `chat_type` is `role_type` (in `docs/roles/stages.yaml`, `docs/roles/pipelines/`,
  the schemas of the stage table, of a stage's result and of a run's manifest, a run's `manifest.json` and state files,
  the output of `harness pack` and of the hook `session-start.py`), the pipeline skill is
  `.claude/skills/running-specagent-pipelines/`, `new-chat-type` is `new-role-type`, and the schema, the catalog and the
  template are `schemas/role-type.schema.json`, `docs/generated/role-types.md` and `templates/role-type.md`; no alias
  keeps an old name, so a run started before 1.6.0 needs the rewrite of `docs/template/MIGRATIONS.md`.
- The spec writer writes the skeleton and the planner the flesh (owner, 2026-10-31;
  `wiki/decisions/spec-writer-writes-the-skeleton.md`): a spec is one page under 8,000 bytes (intent, requirements,
  limits, what counts as done, out of scope) and names no data model, interfaces, signatures, file lists, line numbers,
  moves or tests; the planner adds the data, flows, interfaces, and tasks with files, commands and tests. In the
  `software-factory` pipeline the spec stage's output is `output/spec.md` (it was `output/technical-brief.md`), the
  plan, write and validate stages read it, and its gate checks five sections and no longer the constitution rows or the
  paths of the files to change. The role types, the pipeline skill (`SKILL.md`,
  `references/choosing-roles-and-skills.md`, the example briefs) and the manager's documents say so (roles 1.16.0). A
  run whose spec stage finished before the change holds the old file: `docs/template/MIGRATIONS.md`, 1.7.0.
- Stable first, unique last (owner, 2026-10-31; `wiki/decisions/the-cache-is-measured-in-dollars-and-set-per-role.md`):
  a launch prompt names what is byte-identical across a role's sessions first (the brief, the hand-over rule, the "Read
  first" section of `lessons.md`, the facts pack) and the hand-over note last, because a cached prefix is only as long
  as what is identical; `README.md` ("A session's life"), `example/handoff-rule.md`, `example/first-pass-rules.md`,
  `references/common-mistakes.md`, the session picture and the watcher's fresh-session text for the plan fixer say so.
- The lessons loop has a third step (owner, 2026-10-31; `wiki/decisions/spec-writer-writes-the-skeleton.md`): a finding
  is recorded where it was made, a cause shared by two or more findings becomes a rule, and a rule broken a second time
  becomes a check in code (a hook, a watcher or monitor script, a `check_formats.py` or `harness validate` rule, a
  test); the pipeline skill's `SKILL.md` ("Briefs") and `example/lessons.md` say so.

### Removed
- The `harness-conventions` plugin left the template (owner, 2026-10-30): `plugins/harness-conventions/`, its entry in
  `plugins/.claude-plugin/marketplace.json`, its enable entry in `.claude/settings.json` and the `plugin-evals` job of
  `.github/workflows/evals.yml`; its skills moved (Changed) and commitizen keeps the convention its commit-message hook
  enforced.

### Fixed
- `just validate` and `python3 ops/adopt-obsidian.py lint` pass in a project that built its code graph: the vault lint
  leaves the generated pages of `wiki/graph/` alone (`wiki/graph/*` in `exclude` of `.vault-meta/lint-allowlist.json`).
- `ops/new-project.py` leaves `.raw/captured/` as it was ingested (`skip:` of `docs/template/variables.yaml`): a project
  that replaced a value found in a captured text (`example-repo`, say) failed the ledger's hash check of that source.

## [1.5.0] - 2026-10-30

### Removed
- Archify left the template (owner, 2026-10-29: "I do not like that archify is part of the template"): the vendored
  plugin `plugins/archify/`, its reference material `context/archify/`, its entries in the marketplace,
  `docs/roles/extensions.yaml`, `docs/roles/need-to-know.yaml` and `.claude/settings.json`, `harness map --render`
  and the doctor's node item (`wiki/decisions/diagrams-are-mermaid-text.md`).
- The template's own development records left the repository (owner, 2026-10-29: a clean template for a new project):
  `design/`, `context/fix-20261004/` and `docs/exec-plans/active/template-core/` (the run's plan, with its downstream
  project's names) now live in the template's development container; `omit` in `docs/template/variables.yaml` keeps
  their names. The sample package `packages/ingest/`, its material `context/ingest-samples/`, the three sample wiki
  pages, the run-loop plan and the action record of `specs/001-chat-depth/` left with them: a project adds its own.

### Added
- The manager's control plane in the pipeline skill (`wiki/decisions/control-plane-in-the-skill.md`): the watcher's
  version 3 keeps `_control/registry.json`, sends orders that a session acknowledges with an `ACK <msg_id>` line in its
  record file and resends them by stop and resume, reloads a changed brief instead of exiting, and orders the hand-over
  at a unit's end past 150,000 tokens; `monitor_records.py` reports the request lines to the manager and answers none;
  `duty_list.py` takes the manager's duties from the plan's index; `collect_run.py` deletes a finished run's files only
  after its record is checked as saved, on the owner's yes for its first three runs and then by a standing rule
  (`--apply --yes <digest>`); under `scripts/manager/`, `catalogue.py`, `preflight.py` (the launch table
  `example/launch.md`, the settings simulated, the clock and the capacity rules), `surface.py` (the owner's STATUS
  surface) and `measure_manager.py` (the manager's first call against 30,000 tokens).
- The role types plan fixer and translator (`.claude/agents/plan-fixer.md`, `.claude/agents/translator.md`,
  `docs/roles/types/`), the catalogue of agents and skills `docs/roles/catalogue.md`, the manager's page
  `docs/roles/manager-chat.md` and the vault forms `templates/vault/forms/manager-lessons.md` and
  `learning-record.md`; four regression cases from the lesson classes of 2026-10-29 (`pipeline-ancestor-deny`,
  `pipeline-handoff-pointers`, `pipeline-job-timeouts` and `pipeline-waiters` under `evals/regression/`),
  `evals/nightly.sh` for the session cases, and the run's decision pages under `wiki/decisions/`.
- The shared knowledge base (owner, 2026-10-29: every user gets a vault of their own and a way to share global
  decisions into one public commons): the vault form `templates/vault/` (rules, index, log, folders and the vault's
  scripts); `ops/new-vault.py` makes a vault from it with an opaque origin id, one commit and `commons_path` in its
  index, and `ops/new-project.py ... vault_path=<path>` runs it when the vault is missing; the variable
  `commons_path` (default `~/aftpro-commons`); `harness doctor` checks the vault and the clone of the commons;
  `ops/contribute.py` offers a global decision or concept to the commons by pull request and refuses private
  paths, secrets, names, letters of the refused blocks and the rest by class, in code, with no flag that skips a check
  (`wiki/decisions/the-shared-knowledge-base.md`).
- `ops/container.py` lays the project's folder out around an existing checkout: `runs/` (the runs root), `experiments/`
  and `docs/handoff/` beside it, refused when the parent holds another checkout (owner, 2026-10-29: the runs and the
  experiments live in one folder with the repository); the README's "Before the first run" gives the clone command.
- `docs/WHY.md` (and its `.summary.md`): every rule a reader may question, its reason and the decision page or
  measurement it comes from (owner, 2026-10-29: so that people do not start arguing); `docs/template/DESCRIPTION.txt`:
  the repository's one-line description on GitHub.

### Changed
- `harness validate` and the attack gate refuse a letter of any of the three blocks, U+10A0-U+10FF,
  U+1C90-U+1CBF and U+2D00-U+2D2F (before, the first only; `docs/decisions/0030-the-template-is-english-only.md`
  keeps its words as history); `usage_report.py` prints the date and source of its prices on its first line
  (`wiki/decisions/dated-api-prices.md`); each script of the pipeline skill has its page under `scripts/docs/`, and
  `scripts/README.md` is their index (`wiki/decisions/skill-script-pages.md`); the example agents read their settings
  under `_control/`; the tests and the regression suite's code cases run on every push, the session cases nightly
  (`wiki/decisions/code-cases-gate-every-push-sessions-run-nightly.md`); `ops/bootstrap.py` runs eleven steps,
  graphify's skill and the user-level link of the pipeline skill among them
  (`wiki/decisions/bootstrap-runs-eleven-steps-in-order.md`), and `ops/new-project.py --container` makes
  `docs/handoff/` as `ops/container.py` does; `docs/template/variables.yaml` omits the manager-build plan as it omits
  the template-core plan.
- `harness map` writes one Mermaid flowchart per stage table to `docs/generated/maps/<name>.md`: the stages in their
  order with their chat types and tags, a diamond where a human approves, the returns for revision and the routes;
  GitHub and Obsidian draw it as it stands. The `*.workflow.json` sources are gone, and `harness map` removes them
  from a project made before (`packages/harness/tests/test_map.py`).
- `README.md` is written for a reader who has never seen the template (owner, 2026-10-29): what it is, a table "What
  you get | How | Measured" with each number's file, four Mermaid diagrams (the pipeline, one session's life, the
  knowledge flow, the folder), and a link to `docs/WHY.md`; every section that still held is kept.

## [1.4.0] - 2026-10-29

### Added
- `harness validate` reports a letter of a refused block in a file git tracks or is about to track, and `english_only:` in
  `docs/template/variables.yaml` narrows it (`docs/decisions/0030-the-template-is-english-only.md`);
  `just evals <run_dir>`, the regression cases without a session and the run report; `harness doctor` checks
  `sandbox-exec` on macOS; ADR-0029, ADR-0030 and ten decision pages under `wiki/decisions/`.
- The loops inside a run (`docs/decisions/0024-a-run-loops-until-its-reviewers-pass.md`): a reviewer's `revise` sends
  its proven findings back (`harness/rounds.py`), the stages after it check again, and the loop stops for the human at
  its bounds, on repeated findings or on the judge's `replan` or `reject`
  (`packages/harness/tests/test_rounds.py`).
- `harness resume --rework`: continues a unit a loop sent back or asks to check again; a recheck rebuilds its inputs,
  the work's checkout and patch, and its Material (`test_resume_rework_delivers_the_findings_and_starts_a_round`,
  `test_a_recheck_reads_the_new_change_in_its_material`).
- The attack gate and the critic's stage before the work: attack tests, proofs per finding, a translated summary for
  the human (`test_the_attack_gate_takes_a_proven_revise_with_new_tests_and_a_georgian_summary`).
- Protected tests in the write gate: the tests a trial adds and the critic's attack tests run as given, once more by
  name in the base's pytest configuration (`test_the_write_gate_runs_the_protected_tests_as_given_and_by_name`,
  `test_the_protected_tests_run_with_the_bases_configuration`).
- `docs/quality/HAZARDS.md`.

### Changed
- Summaries are `<name>.summary.md`, in English, and the attack stage writes `output/summary.md`; the SessionStart hook
  turns the git hooks on in every session (`docs/decisions/0029-a-checkout-sets-up-its-hooks-sandbox-and-graph.md`);
  `harness validate` reads its files from the git listing, so ignored local files and the sandbox's empty stubs are not
  read, and a role session's deny rules read an empty `.claude/settings.local.json` as no settings (a broken one still
  raises); `ops/new-project.py` drops a copied page's line that links into an omitted folder.
- The default and `fix` tables: plan → attack → write (one session) → verify → judge, every stage Opus at max
  (`test_the_work_tables_attack_the_plan_and_loop`, `test_every_table_runs_opus_max_but_the_fixed_types`).
- A stage runs with its table's model and effort; the session that creates a run is recorded and changes nothing
  (`test_the_table_is_exact_and_the_session_changes_nothing`).
- The judge reads the plan and the change as `changes.patch` and may decide `replan`
  (`test_a_judge_gets_the_patch_of_the_work_and_no_checkout`, `test_a_judge_may_replan_and_cite_a_place_in_the_change`).
- Closed paths are read as git stores them (`-z`), in lower case, at any depth; `.mcp.json` is closed to writers
  (`test_a_closed_path_is_found_however_git_spells_it`).

### Fixed
- No git command of the harness runs a git hook (`packages/harness/src/harness/gitcall.py`), so a role's branch cannot
  run its scripts through a checkout or merge the harness makes.
- The revise of wave 1 (`docs/decisions/0025-a-guard-refuses-the-plain-spellings-and-the-boundary-holds-the-rest.md`):
  the guards' command reader takes `#` as part of a word and guard-checkout refuses a Glob whose pattern climbs into
  the shared checkout (`test_a_command_after_a_hash_inside_a_word_is_read_by_the_guards`,
  `test_a_glob_whose_relative_pattern_climbs_into_the_shared_checkout_is_refused`); the write gate refuses a branch that
  changes a file the project's settings close (`test_a_branch_that_changes_a_file_the_project_settings_hide_is_refused`),
  and a settings rule that leaves the repository closes nothing in it
  (`test_a_settings_rule_that_climbs_out_of_the_repository_or_names_its_root_closes_nothing`); the read gate, its probe
  check and the locator check open no closed path and nothing outside the stage, and answer alike whether it exists
  (`test_the_read_gate_answers_the_same_about_a_closed_file_whether_it_exists_or_not`,
  `test_the_probe_check_answers_the_same_about_a_path_outside_the_stage_whether_it_exists_or_not`,
  `test_the_locator_check_opens_nothing_outside_the_stage_and_the_repository`); no closed file becomes material, and an
  assignment that lists one is refused (`test_a_file_the_project_settings_close_is_never_material`,
  `test_an_assignment_that_lists_a_file_the_project_settings_close_is_refused`); a reviewing unit's `changes.patch` is
  read-only and indexed with its sha256 on its launch, a recheck and a resume
  (`test_a_change_patch_is_written_read_only_and_indexed_with_its_sha256`,
  `test_a_recheck_writes_the_new_patch_read_only_with_its_new_sha256`,
  `test_a_resume_records_the_patch_it_writes_again`,
  `test_a_plain_resume_indexes_the_patch_it_writes_again_with_its_sha256`); four repairs of wave 1 are held by tests
  (`packages/harness/tests/test_held_repairs.py`).
- A recheck or a resume never writes through a link a session planted in its stage directory
  (`test_a_recheck_never_writes_its_pack_through_a_link_the_session_planted`,
  `test_a_resume_never_logs_through_a_link_the_session_planted`).
- `harness pause set --reason <text>`, `harness pause lift`, `harness pause status`: one switch, `<runs root>/_pause.json`,
  that `harness launch`, `harness resume`, `harness loop tick`, `harness poll` and `ops/night-tick.sh` honour; while it is
  set no session, loop iteration or night session starts or resumes and no state changes. Only the human sets and
  lifts it (`docs/decisions/0023-one-pause-switch.md`).
- `harness loop due --name <loop> [--plain]`: whether a night session has anything to do, decided without a model and
  without a tick; `ops/night-tick.sh` asks it before it starts `claude`
  (`docs/decisions/0022-a-prompt-loop-is-judged-by-code.md`).
- `exit.check` in a loop file (`no_active_runs`), required for a `prompt` loop and checked at every tick; a prompt loop
  counts the progress of the runs it acts on and the cost of its night sessions toward its hard stops.
- `harness mcp-state` serves run state read-only over stdio: `harness_list_runs`, `harness_get_run`,
  `harness_open_escalations`, `harness_stage_result`.
- `docs/roles/pipelines/fix.yaml`, a fix of known defects: plan (approval), write, verify and critique, judge
  (approval), with no reader first; and `context/fix-20261004/`, the approved audit of 2026-10-04 cut into one file per
  fix wave with its probes, which a new project leaves out.
- The brief line `- Hooks: open` lets the branches of a run change the hook scripts under `.claude/hooks/`: the
  permission hook allows those edits in a session's own checkout, and the scope check lets the branch carry them; the
  rest of `.claude/` stays closed (`docs/decisions/0015-a-type-that-is-not-blind-reads-what-a-subagent-reads.md`).
- `harness/transcript.py`, the one reader of a session's transcript: the Read, Bash, Edit and Write calls of a session
  in order (a refused call did not run; a background command's exit code comes from its notification), and the model
  and effort the session runs on (`specs/001-chat-depth`, `docs/decisions/0011-every-step-of-a-method-is-checked.md`).
- `harness/gates/steps.py`: the rule at the end of every step of a type's Working method, checked against the
  transcript and the stage's files in every gate, beside `common_checks`; `harness validate` names a step without a
  rule, a rule outside the language and an `output:` naming a check no gate of the type has.
- `harness steps --run <id>` (or `--run-dir <path> [--repo <path>]`): the new checks on a finished run, one row per
  check by type and step; it writes nothing and asks no model.
- Checks of content in every gate: every `path:line` of a stage's texts names an existing file and line, at the run's
  base commit; every evidence command was run in the session, or by the harness outside it (`checks.json`), and ended
  as the entry says. And the four content checks: the judge's reasons cite existing entries as `<stage>#<n>` and an
  `accept` answers every blocking finding; a researcher cites only lines it read or was given; a synthesis names every
  input and both sides of a clash; a technical brief has a Constitution row per article and names existing or new
  files. While a type's steps mode is `warn` they are recorded in `gate.json` (`advisory`) and `HANDOFF.md`
  (`## Gate warnings`) and fail nothing.
- Model and effort of a run: the stage table's values are floors, raised to the model and effort of the session that
  runs `harness run` (classifier and quarantine-reader keep the table's; `--effort` stands above everything); a raised
  effort multiplies the time limit by 2 or 3; `manifest.json` records the choice, its source, the floor, the session
  read and the run's base commit.
- A role session starts only inside the sandbox (`sandbox.failIfUnavailable` in its settings), and `harness launch`
  and `harness resume` say why when it cannot (`no_sandbox`). `ops/machine-setup.py` sets a Linux machine up for it:
  as this user where every program may make a user namespace (a checked copy of bubblewrap and socat in
  `~/.local/bin`, started by the SessionStart hook and refreshed when the system's bubblewrap or apt's version
  changes), else with one password in the system's window (the documented AppArmor profile, then socat; a script that
  undoes it is kept). `--plan` shows either. The launcher records the checkout's trust, which `claude --bg` needs
  (`harness/trust.py`) (`docs/decisions/0013-no-command-to-type-and-at-most-one-password.md`).
- `harness abort --run <id> --reason <text>` ends a run that will not be integrated: its sessions stop and leave the
  session list, its checkouts go after their uncommitted work is saved under `refs/harness/salvage/`, its folder and
  branches with commits stay (`docs/decisions/0010-a-run-ends-with-integrate-or-abort.md`). No command changes an
  aborted run; a loop counts one as a failure.
- `harness doctor` names what earlier runs left behind, each with the command that removes it; `harness run` names
  the runs still open (`open_runs`).
- A checkout sets itself up (`docs/decisions/0009-a-checkout-sets-itself-up.md`): `ops/bootstrap.py` installs uv when
  the machine has none, makes the workspace, installs the project plugins and the language servers, and ends with
  `harness doctor`; the SessionStart hook runs it in the background in a fresh checkout and `ops/new-project.py` runs
  it at once.
- `plugins/code-intel`: language servers for Python, JavaScript and TypeScript, PHP, C and C++, HTML and CSS, pinned
  and installed into the plugin's data directory by its own hook; it replaces `pyright-lsp`, whose server was never
  installed on the machine the template was built on, so no session ever got a diagnostic.
- `harness doctor` checks that the language servers are installed and answer, sends native Windows to WSL2, and
  accepts the workspace's jsonschema for the hooks; the JSON hooks use it when python3 has none.
- `harness assign` and the assignment of a stage: before a role session starts, the manager writes what it would
  write into the prompt of a subagent for the same job; `launch` and `status` answer `no_assignment` without one.
  The text follows the brief in the first message (`docs/decisions/0006-a-role-session-gets-what-a-subagent-would-get.md`).
- `harness gate --preview` and the stop hook that asks it: a session that says `complete` is held to its stage's gate.
- A checkout for the planner's trial (`trial_checkout`), removed when the next stage starts; the trial's patch is
  among the writer's inputs, so tried work is not typed again.
- Gate checks for depth: a reader's probes and their records as located facts, a planner's decisions and trial, a
  writer's test seen to fail, a critic's evidence for every blocking finding.
- The project's `CLAUDE.md` and `AGENTS.md` in the pack of every role type that works in the repository.
- The material of every stage in its cached system prompt, chosen by script at launch (`harness/pieces.py`): the
  stage's inputs, the brief's material for a stage that receives `context`, the pieces the assignment lists, every
  place the stage's texts cite as `path:line` with the piece that holds it, the short files they name, and the
  pieces that match the brief. Every line exactly, after its number; an empty line left out with its number; files
  of the pack not repeated. The session works from the cache instead of opening files one by one, and the manager
  spends no turn on it. `harness material --run <id> --stage <s>` shows the pieces and why.
- The handoff of a conversation: before Claude Code compacts the manager's or a human's session,
  `.claude/hooks/handoff.py` asks it to write `docs/handoff/<date>-<time>-handoff.md` and once more to bring it up to
  date, and after the compaction asks it to read the newest handoff. The handoff keeps the main points of the
  conversation and the state of the work, never a copy of the conversation. The notices follow the real compaction point; the folder is not committed and is
  closed to role sessions
  (`docs/decisions/0007-a-conversation-hands-itself-off-before-compaction.md`).
- Every role type keeps its prompt cache for five minutes, as a subagent does; the one-hour lifetime of planner,
  writer, verifier and test-verifier cost more for the cache writes and saved nothing in the measured runs.
- `harness map`: one Archify workflow source per stage table in `docs/generated/maps/`, computed from the table by
  rule; `--check` and `docs-check` report a stale or missing map; `--render <dir>` renders HTML. A stage a human
  approves carries a person icon, and a card under the map lists those stages and the routes of a routing table.
- Archify 3.0.1 as an internal plugin (`plugins/archify/`), on for the manager session only.
- `harness integrate --run <id> [--clean]`: the branch `run/<run-id>` with everything a run committed.
- `harness doctor`: what the machine needs before a role session can run.
- `harness watch`: poll a run until something needs the manager; a status line with the running role sessions.
- Committed work reaches the stage that reviews it: one neutral work commit, a checkout per reviewing session and
  `changes.patch` among its inputs (`harness/work.py`).
- A wiki page becomes `verified` when the check stage of its run accepted it; only verified pages enter a pack.
- `checks.json`: what the write gate ran on a branch outside any session, delivered with the work to the verifier.
- Design awaiting approval: parts, contracts and the project brain (`design/specs/`).
- The measured comparison of role sessions with subagents on one task (`design/experiments/2026-10-02-stage-map/`).

### Changed
- Every writer of a run's `state.json`, its `logs/notified.json` and a loop's state holds the file's one lock around
  its read, change and write, never while a session or a gate runs, and writes through a temporary file of its own;
  one tick of a loop runs at a time (`docs/decisions/0021-one-writer-at-a-time-for-run-and-loop-state.md`).
- `ops/night-tick.sh` starts a manager session only when `harness loop due` finds work, and one fire ticks once; each
  fire's output is a file under `<runs root>/_audit/night-tick/`.
- A notification is sent each time an action that needs the human appears; an action no poll prints any more is
  forgotten.
- The spans of `harness launch` are exported to `HARNESS_OTEL_ENDPOINT` (an OTLP/HTTP traces URL).
- A type that is not blind reads the agent files, the stage tables, the policy and `design/`, as a subagent sent into
  the repository does; only the blind types are refused them, by `blind_deny`
  (`docs/decisions/0015-a-type-that-is-not-blind-reads-what-a-subagent-reads.md`).
- A role session keeps its prompt cache for an hour, five minutes only for `classifier` and `quarantine-reader`
  (`docs/decisions/0016-a-stage-at-max-effort-keeps-its-cache-for-an-hour.md`).
- `harness integrate` never rewrites an existing `run/<run-id>`; with `--clean` it only cleans. Removing a run's
  checkouts saves their uncommitted work first instead of discarding it.
- A role session cannot steer its run: with `HARNESS_ROLE` set, every command that changes a run, and `abort`,
  refuse (`role_session`); the gate preview of the stop hook still answers. `harness integrate --clean` closes
  a run that committed nothing, such as a planning run.
- `poll` stops the idle session of a stage that is done and needs no approval (`harness resume` continues it), and
  the run state records `changed_at`, the last change that matters.
- A role session works to a subagent's depth (`docs/decisions/0008-a-role-session-works-to-a-subagents-depth.md`):
  its first message begins with its type's instruction and the role rules, as a subagent receives them with its task;
  the role rules ask it to complete the task fully and to be thorough; its material is given whole up to half the
  model's window (about 500,000 tokens; 80,000 on haiku); every gate fails a file of the material that no output heads
  or covers, whatever the type; it compacts where Claude Code does (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=100` in its
  settings), whatever the human's own sessions use; `harness run --effort <stage>=<level>` sets the effort of a stage
  for one run; `harness launch` refuses a stage whose listed material does not fit (`material_does_not_fit`), and
  `harness material` names `does_not_fit` and `not_text` (images and other files the session opens with Read).
  Instruction version 1.3.0.
- The manager's instruction is written out; reader, planner, writer, verifier, critic and researcher work to the
  depth a subagent given the same job was measured to reach (instruction set 1.2.0, `docs/roles/CHANGELOG.md`).
- Role rules and the knowledge pack are part of the system prompt; a role session no longer loads the root
  `CLAUDE.md` and `AGENTS.md` (`docs/decisions/0004-rules-and-pack-in-the-system-prompt.md`).
- Every start and every resume of a session names the model and effort of its stage.
- The test command of one package is `uv run pytest -q packages/<pkg>`.
- An evidence entry may name the exit code its command is meant to end with (`expected_exit_code`).
- The internal plugin marketplace is named after the project (`example-repo-plugins`, `<repo_name>-plugins` in a
  new project): Claude Code knows a marketplace by one name on the whole machine, and projects that shared
  `harness-internal` shared it. code-intel finds its data directory by that name (`ensure.py --print-data`).
- Runs live in the runs root: `../runs/` when that folder carries `.harness-runs`, otherwise `../<repo>-runs/`
  (`harness runs-root`); `ops/new-project.py --container` makes a project folder with the checkout, `runs/` and
  `experiments/`. Template version 1.1.0 (`docs/template/MIGRATIONS.md`).

### Fixed
- Wave 1 of the fixes of the audit of 2026-10-04, the leaks (`context/fix-20261004/wave-1-leaks.md`):
  - What a role session may write: no write path inside the repository for any type, `Edit(...)` deny rules beside
    the sandbox's `denyWrite` (a type without a checkout writes nothing of the repository, a type with one its own
    checkout without the configuration Claude Code loads from it), read-only input copies the gate checks by their
    sha256, no shell write of a run's JSON files, no messaging token in a sandboxed command, and no `CLAUDE.md` of
    reviewed work in a reviewer (`docs/decisions/0018-a-role-session-writes-its-stage-and-its-own-checkout-only.md`).
  - What reaches a session: a stage-table input that leaves its producer's directory is refused, and a link in an
    output is not copied (01/F13, 01/F14); an agent file without a built-in tool starts a session with none, and a
    unit whose agent file is gone is not resumed (01/F15).
  - The write gate runs a branch's suite in a sandbox of its own, without the gating process's environment
    (`docs/decisions/0017-the-write-gate-runs-a-branch-s-tests-in-a-sandbox.md`).
  - A role session runs only the harness commands listed for it; `poll` and `watch` refuse it
    (`docs/decisions/0019-a-role-session-runs-only-the-harness-commands-listed-for-it.md`).
  - Hooks fail closed in the way their event allows, take their rules from the main checkout, and read the plain
    spellings of a command; the gates and the stop hook open nothing outside a stage, the read gate no location outside
    its bases; guard-checkout, guard-bash, stop-gate, compact-output and validate-json close the holes 04/F1 to F7, F9
    to F11, F16 and F17, the guards for the plain spellings of a command; 04/F8 and F12 to F15 belong to waves 3 and 6
    (`docs/decisions/0020-hooks-and-gates-fail-closed-and-open-nothing-outside-a-stage.md`, amended by
    `docs/decisions/0025-a-guard-refuses-the-plain-spellings-and-the-boundary-holds-the-rest.md`).
- `harness poll`, `harness launch` and `harness resume` no longer write back a copy of `state.json` read before a gate
  or a session, which undid an approval or an abort recorded meanwhile (01/F03, 02/F01); saves at once no longer share
  `state.json.tmp`, which raised and left half a file (02/F02).
- A damaged `logs/notified.json` no longer makes every `harness poll` raise (02/F09), and the second time a unit needs
  the human is announced (02/F10).
- One run whose `state.json` cannot be read no longer stops `harness poll --all-active` or `harness limits` (02/F26),
  nor a loop tick over `runs:<days>` (the critic's row 148 of the audit).
- `harness loop tick` prints one action when the run it waits for is gone (05/F28) and on any context entry, and
  `harness loop validate` names an entry a tick cannot read (05/F29); two ticks of one loop at once start one iteration
  (05/F30).
- `harness mcp-state`, enabled for the manager, no longer raises NotImplementedError (05/F31); the launcher's span
  reaches `HARNESS_OTEL_ENDPOINT` (05/F32).
- The write gate's scope check named a file moved out of a closed path by its new path only and let it pass; it now
  lists both paths of a move.
- `permission-request.py` answers no when it cannot read a request, instead of failing and leaving a background
  session waiting on the prompt.
- `ops/machine-setup.py`: socat 1.8 of Ubuntu ships `usr/bin/socat` as a link to `socat1`, and the user-space way
  moved in the link alone, which named nothing; it now moves in the file the link names, followed inside the
  unpacked package only. An argument the script does not know prints its usage and changes nothing: `--help` set
  the machine up, as the plain command does (seen 2026-10-03).
- The gate no longer asks a type that cannot write a file (neither Write nor Bash among its tools: judge, comparator,
  quarantine reader, classifier) to account for its material: it returns structured output only and has no document
  to account in. Seen on 2026-10-03: a judge failed its gate on the 39 files of its material.
- A type that cannot write a file (a type whose agent file lists tools, none of them Write or Bash) no longer gets
  pieces chosen by script, neither cited, nor named, nor related: it could account for none of them, and the judge
  may not open the sources they come from. Its material is its inputs, the pieces its assignment lists and, for a
  stage that receives `context`, the pieces its brief lists
  (`docs/decisions/0012-a-type-that-cannot-write-accounts-for-no-material.md`).
- A role session could leave the sandbox: it can change the code of its own checkout, and the commands of
  `sandbox.excludedCommands` (`uv run harness launch …` and the rest) run that code outside the sandbox. The launcher
  now denies a role session every one of them by permission rules, from `.claude/settings.json` and
  `.claude/settings.local.json` alike.
- `harness integrate --clean` ran inside the sandbox and could not take sessions out of the session list; it is in
  `sandbox.excludedCommands` now, with `harness abort`.
- Thirteen findings of the first complete live run (`docs/decisions/0005-what-a-live-run-needs.md`): sandbox and
  toolchain access, worktree entry, resume, gates for finished sessions, the result of a print stage.
- A resumed session ran on the user's default model instead of the model of its stage.
- `harness validate` passed a stage table whose `depends_on` named no stage, repeated an entry or closed a cycle, and
  one that used a stage id twice; `harness map` wrote a map of such a table that Archify then rejected. Both name
  the problem now, and `harness map` also refuses a stage id or chat type longer than a node holds.
- A background session inherited the environment of the command that first started the background service.
