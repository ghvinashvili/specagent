# 004 Consolidation: one name, one place for ECC, history out of active, nothing personal

Date: 2026-10-31. Ordered by the owner on 2026-10-30 (`_inputs/facts.md` of run `consolidation-2026-10-30`, items 1-10). Base:
`feat/consolidation` from main `cb60f5b`; template 1.6.0. `tables.md` beside this file holds, per item (§S<n>, §R4), the places
by line, the literals, the texts and the tests; line numbers are at `cb60f5b`, re-found by `grep -n`. `<run>` = the run folder;
`<skill>` = `.claude/skills/running-chat-agent-pipelines` (after S10 `running-specagent-pipelines`); `G <pat>` = `git grep -Il <pat>
-- . ':!.raw' ':!wiki/meta' ':!specs/004-consolidation' ':!CHANGELOG.md' ':!docs/template/MIGRATIONS.md'`; `harness <c>` = `uv run
harness <c>`; `pytest <files>` = `(ulimit -v 8388608; uv run pytest -q <files>)`; a command named as a check passes.

## 1. Intent
One name, SpecAgent, in the template's text and in the names of its own things; every ECC text under `.claude/ecc/` with a
catalogue the manager reads before a brief for a role with a domain; finished plans out of `active/`; the two decision stores
explained once; no listed file naming the owner's language or circumstances; a new project with a README of its own and the
template's kept. Files move and references follow; nothing is merged, renumbered or rebuilt; the checks prove the template still
births a project.

## 2. Facts
At `cb60f5b`; `[n]` = the facts' `grep -rIl` count at `ce9d7af`, `.raw/` and `wiki/meta/` included.
- `git ls-files | wc -l` 1042; `ls -d .claude/skills/*/ | wc -l` 25 (11 from ECC); `git ls-files docs/references/ecc-agents | wc -l`
  73 (70 texts + 3); `git ls-files 'docs/references/ecc-*.md' | wc -l` 4; `git ls-files plugins/harness-conventions | wc -l` 7; `git
  ls-files <skill> | wc -l` 101; `git ls-files docs/exec-plans/active/manager-build | wc -l` 13, `pipeline-fold` 9 (no `completed/`);
  `ls docs/decisions/0*.md | wc -l` 29; `wiki/decisions/` 42 pages; `git ls-files '*.ka.md'` none; `<skill>/SKILL.md` 11,990 B,
  `wiki/index.md` 11,729 B (cap 12,000).
- `G ecc-agents` 24 [28]; `G references/ecc-` 25; `G harness-conventions` 12; `G exec-plans/active` 42 [45]; `G -E
  'active/(manager-build|pipeline-fold)'` 10; `G exec-plans/completed` 5; `G docs/template/README.md` 5; `git grep -ni aftpro` with
  `G`'s pathspecs `| grep -vE 'aftpro-commons|Desktop/aftpro' | wc -l` 8 (6 files) [22 files]; `G ADR-00` 110 [120], not rewritten;
  `G running-chat-agent-pipelines` 69 [86]; `G -E '[Cc]hat[ _-][Tt]ype'` 121 (511 lines); `G -i -E 'chat[ -]agent'` 81; `G
  pipelines-run-as-chat-agents` 6; `git grep -Il -E -f <run>/scratch/spec-writer/s6-words.txt -- . ':!.raw' ':!wiki/meta'
  ':!specs/004-consolidation'` 40 files, 133 lines [19, `docs/` only].
- Item 8 is built by the merge of specs/003 (`git log --oneline -- <skill>/scripts/manager/preflight.py` tops at `09a0fe5`; the
  seven `<skill>/example/*-settings.json` hold `"includeCoAuthoredBy": false`; `preflight.py:210-211,226-227`): dropped.

## 3. Items
R1 Every move is `git mv <old> <new>`; one touching a protected path (`example/common.md` "The sandbox") is asked for as that
command in one `SANDBOX:` line of `build-log.md` and run by the main session; a new file there is written with the Write tool;
`git diff --stat -M cb60f5b` shows each move as `=>`. R2 Every old literal in every tracked text file but `G`'s exclusions
(`CHANGELOG.md` and `MIGRATIONS.md` keep their old entries; S9 adds the new; S6 does rewrite them) is replaced by script, longest
first, never by hand; a path in pieces is edited to the same value; `build-log.md` holds each `G` count before and after; a test
that pins an old path is updated, never deleted. R3 Nothing else changes: the ECC texts byte for byte (`ops/tests/test_ecc_pins.py`
proves the sha256 at the new paths), the names §6 keeps, ADR numbers, `.raw/captured/*`, plan history. R4 The decision pages of
S1, S2, S4 and S5 (§R4; decided 2026-10-30, by owner), each with its `.summary.md` and index line, are in the item's commit;
§R4's ingest is the last unit. Order: S1, S6, S3, S2, S4, S5, S7, S10, S9. Every item's `G` counts of §2 end at 0 unless said.
- S1 Name. No move. `AFTPro (Agent Flow Template Pro)` → `SpecAgent (special agent)`; `AFTPro` → `SpecAgent`; `ghvinashvili/aftpro.git`
  → `ghvinashvili/specagent.git`; README.md:1 `# SpecAgent`; `new-project.py:135` "from SpecAgent"; `DESCRIPTION.txt` prefixed
  `SpecAgent: `. Places: §2's `aftpro` pipe (§S1). Checks: that pipe 0; `grep -m1 '^# ' README.md` = `# SpecAgent` (the banner is line 1).
- S2 ECC. `git mv docs/references/ecc-agents .claude/ecc/agents` (73 files); `git mv docs/references/ecc-<x>.md .claude/ecc/<x>.md`
  (the four). Rule: `docs/references/ecc-` → `.claude/ecc/`; links in the moved pages lose `ecc-` (§S2). New `.claude/ecc/README.md`
  (§S2): one line per text from its `description:`, one per ECC skill with its role types and when, one for the rules. "Before a
  brief for a role with a domain, read `.claude/ecc/README.md`." enters `SKILL.md` "## Briefs" (five edits, §S2) and `MANAGER.md`
  "## 14."; `wiki/hot.md` gets it from the page's ingest (§R4); `need-to-know.yaml` rows get `skills:`, unioned by `access.py` with
  the agent file's (§S2) [NEEDS CLARIFICATION: today only the agent file maps skills]; the two sandbox lists gain `.claude/ecc`.
  Checks: `git ls-files .claude/ecc | wc -l` 78; `grep -c '^- \[' .claude/ecc/README.md` 82; `wc -c <skill>/SKILL.md
  .claude/ecc/README.md` ≤ 12,000 each; `pytest ops/tests/test_ecc_pins.py packages/harness/tests/test_access.py`.
- S3 Plugin. `git mv plugins/harness-conventions/skills/commit-style .claude/skills/commit-style`, same for `doc-gardening`; `git rm
  -r plugins/harness-conventions` (commitizen keeps the convention). Places: 12 files by line in §S3 (`.claude/settings.json` by Edit;
  `ci.yml` → `./plugins/code-intel --strict`; the `evals.yml` job removed). Checks: `G harness-conventions` 1 (`task-08.md`, history);
  `test -d plugins/harness-conventions` false; `ls -d .claude/skills/*/ | wc -l` 27; `claude plugin validate ./plugins`; `harness extensions`.
- S4 Plans. `git mv docs/exec-plans/active/manager-build docs/exec-plans/done/manager-build` (13 files), same for `pipeline-fold` (9);
  new `done/README.md` (§S4). Literals: `exec-plans/active/<plan>` → `exec-plans/done/<plan>`; `exec-plans/completed` → `exec-plans/done`;
  `active/README.md` keeps no "## Plans" line; `docs/llms.txt` gains the Finished plans line; `catalog.py` L3 also lists done plans
  (block, test, places §S4). Stay: plan-lint (active only), `wiki/plans`, `omit:` (pipeline-fold stays copied: not ordered). Checks:
  `git ls-files docs/exec-plans/done | wc -l` 23; `git ls-files docs/exec-plans/active` = its README; `harness docs-check`; `pytest
  packages/harness/tests/test_docs_layers.py`.
- S5 Decisions. No move. `docs/decisions/README.md:3-4` → §S5's paragraph; `wiki/index.md:14` + §S5's sentence linking
  `../docs/decisions/README.md` (after §R4's four replacements). Checks: `grep -c 'cited as ADR-00nn' docs/decisions/README.md
  wiki/index.md` 1 each; `wc -c wiki/index.md` ≤ 12,000; `harness wiki-lint`.
- S6 Nothing personal. No move. Files: the 40 of §2's `s6-words.txt` grep (`CHANGELOG.md`, `MIGRATIONS.md` included). Rules:
  `<run>/scratch/spec-writer/s6-phrases.md` (old → new by script, longest first, all 133 lines; the run's, not this spec's: the
  template never holds the two words); a line it leaves is reworded by hand to the facts' "Neutral wording" and logged with its
  path:line; a decision keeps its date and its decision. Stay: the identifiers the table's head names [NEEDS CLARIFICATION];
  `.raw/captured/*` [NEEDS CLARIFICATION: a purge is the owner's call]. Checks: that grep `| wc -l` 0; `harness validate`; `pytest`
  the tests of §S6. No new page: `the-template-is-english-only` is reworded and superseded.
- S7 Project README. `git mv docs/template/README.md docs/template/PROJECTS.md` [NEEDS CLARIFICATION: the order puts the copied root
  README at a project's `docs/template/README.md`, where "This repository as a template" lives]; `docs/template/README.md` →
  `docs/template/PROJECTS.md` (5 files, §S7). `ops/new-project.py`: `copy_tracked` unchanged; a new `project_readme()` after it (:126)
  writes the copied README, links re-rooted `../../`, to `<target>/docs/template/README.md`, the stub to `<target>/README.md`, the llms
  line to `<target>/docs/llms.txt` (texts, rule, test §S7). Checks: `G docs/template/README.md` = `ops/new-project.py` and its test;
  `pytest ops/tests/test_new_project_readme.py ops/tests/test_bootstrap_steps.py ops/tests/test_new_project_omit.py`; §4.3.
- S9 Index and release. README.md "## What is here" (:23-43; the branch has no "Where everything lives" table) gets §S9's six lines;
  `docs/llms.txt` names every moved document (§S9); `CHANGELOG.md` "## [Unreleased]" gets "### Changed" and "### Removed", one line
  per item, by hand; `docs/template/VERSION` 1.6.0; `docs/roles/VERSION` 1.15.0 with its `## 1.15.0` heading; the §5 entry above
  `## 1.5.0` of `MIGRATIONS.md`, its "renamed:" list expanded from the `git mv` lines of S2, S3, S4, S7 and S10. Checks: `cat
  docs/template/VERSION` 1.6.0; `grep -c '^## 1.6.0' docs/template/MIGRATIONS.md` 1; `harness version-check --base cb60f5b`; `harness docs-check`.
- S10 Names after "chat agent". `git mv <skill> .claude/skills/running-specagent-pipelines` (101 files); `git mv` of
  `wiki/decisions/pipelines-run-as-chat-agents-from-a-template-skill{,.summary}.md` → `pipelines-run-as-specagent-sessions-from-a-template-skill`;
  `schemas/chat-type.schema.json`, `docs/generated/chat-types.md`, `templates/chat-type.md`, `.claude/skills/new-chat-type` →
  `role-type.schema.json`, `role-types.md`, `role-type.md`, `new-role-type` beside them. Literals in §S10's order: the two names,
  then the `chat agent`, `chat_type`, `chat-type` and `chat type` families → `SpecAgent session`, `role_type`, `role-type`, `role
  type` (plural and capital forms too); the page name also in `wiki/meta/ledgers/*.json` and `.raw/.manifest.json`, as ordered, in
  the `git mv` commit; no alias (§S10). Stay: `.raw/captured/*`, the ledgers' claim `text`, run folders, the manager's user-level
  copy; the main session's link at the merge (§S10). Checks: `git grep -Il pipelines-run-as-chat-agents -- . ':!.raw/captured'
  ':!specs/004-consolidation'` 0; `git ls-files .claude/skills/running-specagent-pipelines | wc -l` 101; `python3
  ops/adopt-obsidian.py lint` clean; `claude plugin validate .claude/skills`; `pytest`. No new page.

## 4. Verification
1. After each item's commit: its checks; `git diff --stat -M <parent>..<commit>` shows each move as `=>`; the verifier's `G` counts
   equal `build-log.md`'s. At each unit's end, in order: `uv run ruff check . && uv run ruff format --check .`; `pytest`, files 4
   at a time; `harness validate`; `harness docs-check`; `harness plan-lint`; `harness wiki-lint`; `just validate`; `claude plugin
   validate ./plugins/code-intel --strict`; `claude plugin validate .claude/skills`; `harness extensions`; `harness version-check
   --base cb60f5b`; `harness catalog` then `git status --short` empty; every `G` count of §2 at its end value; §R4's dry run.
2. The new project (binding): `python3 ops/new-project.py "$TMPDIR/probe" repo_name=probe org=probe-org`, then in it `uv sync`,
   `uv run harness validate`, `just validate`, `python3 ops/adopt-obsidian.py lint`, `uv run harness docs-check`, `head -1 README.md`
   = `# probe`, `test -f docs/template/README.md`, `test -f docs/template/PROJECTS.md`, `grep -c 'template/README.md' docs/llms.txt`
   1, `test ! -e docs/exec-plans/done/manager-build`.

## 5. Migration (the entry for `docs/template/MIGRATIONS.md`, above `## 1.5.0`)
## 1.6.0
- Changed template-owned paths: renamed: the `git mv` pairs of S2, S3, S4 (`pipeline-fold/` only), S7 and S10, each `old` →
  `new` (new: `.claude/ecc/README.md`, `docs/exec-plans/done/README.md`); deleted: `plugins/harness-conventions/`; changed:
  `.claude/settings.json`, `.claude/skills/running-specagent-pipelines/`, `docs/roles/` (`skills:` rows, `role_type:` keys, VERSION
  1.15.0), `packages/harness/`, `ops/new-project.py`, `plugins/.claude-plugin/marketplace.json`, `.github/workflows/`, `docs/`
  (`llms.txt`, `references/README.md`, `runbooks/README.md`, `decisions/README.md`, `architecture/documentation.md`,
  `template/variables.yaml`, `exec-plans/active/README.md`), `templates/vault/rules.md`, `wiki/index.md`, `wiki/decisions/`; never
  copied: `docs/exec-plans/done/manager-build/`
- Steps: finish or abort the active runs and pipelines, or keep one and refreeze it at the end; copy the paths above from the
  template at 1.6.0 over the project's, deleting each old path a rename names, and merge by hand, keeping the project's lines:
  `.claude/settings.json`, `docs/llms.txt`, `docs/template/variables.yaml`, `wiki/index.md`, `docs/exec-plans/active/README.md`; in
  the project's own files run the literal rewrites of §S2, §S4 and §S10 of `specs/004-consolidation/tables.md` (never §S1: the
  project's name is its own); write `docs/template/README.md` from the template's README with links prefixed `../../` and the llms
  line of §S7; keep an untracked link `.claude/skills/running-chat-agent-pipelines -> running-specagent-pipelines` until every live
  run ends and renew `~/.claude/skills/running-chat-agent-pipelines`; in a run kept, `"chat_type"` → `"role_type"` in its
  `manifest.json` and state files; `uv sync`; `uv run harness catalog`; `uv run harness refreeze` per run kept
- Checks: the 1.5.0 list, `claude plugin validate .claude/skills`, `python3 ops/adopt-obsidian.py lint`
- Breaks active runs: yes: `harness refreeze` (`.claude/settings.json`, `.claude/skills/`, `plugins/`, `templates/` changed); a run
  from before 1.6.0 names the old skill path (the link carries it) and holds `chat_type` keys (rewritten as above)

## 6. Out of scope
Item 8 (blind commits): built by the merge of specs/003 (§2); the economy run chose no `attribution` key over the blank one, both
blank the trailer in Claude Code 2.1.314. The decision stores stay two (an ingest of 29 ADRs rewrites 110 files for nothing);
`templates/` and `docs/template/` keep their names (6 and 10 code lines); `~/aftpro-commons`, `COMMONS_URL`, `example-repo-plugins`,
`example-repo` and `example-org` stay; the commons repository is not built; the GitHub rename and the About line are the manager's;
pipeline-fold is not added to `omit:`; the S6 identifiers, `/home/tite/...` in plan history and `.raw/captured/*` stay; no ADR
number or ECC text changes.
