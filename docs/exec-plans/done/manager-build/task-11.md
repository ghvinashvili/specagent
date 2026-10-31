# Task 11 — Release 1.5.0: VERSION, MIGRATIONS, CHANGELOG, this run's decision pages, the three blocks in `harness validate`, the final checks

planner: a
builder: a
depends_on: 1-10 (`Merged: a+b+c+d at <sha>` in `lessons.md`, the merge of every lane into `feat/manager-build`)
files: `packages/harness/src/harness/catalog.py` (`GEORGIAN` and `LETTER`: the three blocks), `packages/harness/tests/test_validate_listing.py` (`LETTER` changed, one parametrized test added), `ops/tests/test_contribute.py` (one test renamed and tightened: the two checks now agree; K12); `.claude/skills/running-specagent-pipelines/example/agents.json` and `example/agents-judge.json` (each `settings` value under `_control/`), `scripts/tests/test_skill_example.py` (the settings check), `scripts/tests/test_docs.py` (the v2 config test makes `_control/` first), `scripts/tests/test_preflight.py` (V5's test of the example pair passes `check_launch` whole; K13), `scripts/README.md` (the `settings` row; K13); `SKILL.md` (the lines for builder B's tools and Task 7's script; at most 12,000 bytes), `references/watching.md` (text moved out of SKILL.md, Step 3), `references/measuring.md` (line 2), `scripts/tests/test_skill_md.py` (the tools' phrases pinned); `docs/exec-plans/tech-debt-tracker.md` (TD-002, TD-008, TD-010, TD-011 and one row per Deferred item); `docs/template/PROJECTS.md` (:17, :19-20), `ops/new-project.py` (the docstring, :3-4), `ops/tests/test_bootstrap_steps.py` (one test added: the README and the docstring name bootstrap's eleven steps; K14), `docs/quality/LEARNING.md` (:19); `wiki/decisions/<page>.md` with `.summary.md` (Step 6's list); `docs/template/VERSION`, `docs/template/MIGRATIONS.md`, `CHANGELOG.md`, `docs/roles/VERSION`, `docs/roles/CHANGELOG.md`, `docs/template/variables.yaml` (two `omit:` lines) and `ops/tests/test_new_project_omit.py` (two tests; K15); `wiki/index.md`, `wiki/log.md`, `docs/exec-plans/active/README.md`. Not touched: `docs/decisions/0028-pipeline-evals.md`, `0029-*.md`, `0030-*.md` (history: the run's pages name the lines they supersede), `packages/harness/src/harness/evals.py` (already three blocks, Task 8) and `gates/attack.py` (it imports `catalog.GEORGIAN` and so checks the three blocks from this task on)
acceptance: 10.1-10.20 once, by the verifier at M3 (index row 11), each with the command of the task the index's acceptance column names; this task's own steps carry 10.14's tracker part (Coverage: "the tracker rows closed and the Deferred items added as rows", 5.9.4) and the release (5.9.1)

All paths below are relative to the checkout; `S` is `.claude/skills/running-specagent-pipelines`. Builder A starts
Task 11 on the commit of the `Merged: a+b+c+d at <sha>` line in `lessons.md`: every lane merged into
`feat/manager-build`, which also holds this plan folder. That line names 19a4a95 (main session, 02:2x UTC: Tasks 1-10
built and verified, the repo-root `uv run pytest -q` 1567 passed); 19a4a95 holds no plan file, so builder A's `HEAD` is
a descendant of it that adds this folder. Every figure below was measured on the provisional merged tree 51dd0ce
(worktree `manager-build-m`, 1566 passed, main session 01:16 UTC) and re-checked on 19a4a95; every worktree of the
template shares one object store, so `git diff 19a4a95 HEAD` works in builder A's worktree. `git diff --stat 51dd0ce
19a4a95` lists twelve files, the fixes of R502 (5b8d3b1: the `milestones` row of `$S/scripts/README.md`), V7
(c3c1cf0: four example briefs and one new test in `$S/scripts/tests/test_skill_example.py`, after :237) and V6
(94feff2: `evals/graders/pipeline_plan.py` and five files of `evals/regression/`). This task changes two of them, and
the anchors it names there hold on 19a4a95 (`scripts/README.md`'s `settings` row :88, `test_skill_example.py` :97);
V7's test moves two counts, Step 2's and Step 0's repo-root count, both given on 19a4a95. Scripts use the standard
library and pytest only (Global Constraint 9); no letter of a refused block anywhere (D1): a test builds one with `chr()`.

## Goal
Release the template as 1.5.0: `docs/template/VERSION`, a `MIGRATIONS.md` entry that a project's sync run takes as
its brief, the changelog, the role bundle's version; the decision pages builder B's tasks and the unbuilt answers left
to this task; `harness validate` refusing a letter of any of the three blocks (8.3.11); the example agents
reading their settings from `_control/` (Task 2's K7); `SKILL.md` naming the tools the other lanes built; the tracker
closing what the run closed and holding a row for every Deferred item, so the collector accepts the run (Task 6's K1);
the texts that the run made false corrected; and the full checks once, by the verifier at M3.

## Departures (from the spec and the index, with the reason)
1. `ops/tests/test_contribute.py` joins the files (K12): its test
   `test_the_georgian_check_covers_the_check_of_harness_validate_and_the_two_blocks_it_misses` (:357) describes
   `catalog.GEORGIAN` as this task leaves it no longer (lesson 00:42, B5 and B6: a step that changes what a component
   holds greps every text describing it). The index's row 11 gets the path from `manager/plan-fixer`.
2. `docs/decisions/0030-the-template-is-english-only.md:36` ("a letter of a refused block (U+10A0-U+10FF)") is history like
   0028's lines: Step 7's changelog and migration entry say that `harness validate` now checks three blocks.
3. The Deferred items become ten tracker rows grouped by owner and next step, not one row each (Step 4): one row per
   item (thirty) would take the tracker past Global Constraint 4's 12 KB, which the ten grouped rows already bring from
   5,007 to 11,723 bytes. Each row quotes the key of every item it holds in its Plan cell, as K3 asks.
4. The title of Task 10's page `skill-script-pages` loses its colon (Step 6, block 6h): "The skill's script docs: one
   page per script, the README an index" (`task-10.md:917`) becomes "The skill's script docs are one page per script,
   the README an index", since a `: ` inside a frontmatter value is a YAML mapping, on which `wiki.lint` raises.

## Contracts (binding; from the fixers' messages and the tasks' `## For Task 11` sections)
- K1 (Task 1, planner-b): `docs/roles/VERSION` 1.13.0 -> 1.14.0 and a `docs/roles/CHANGELOG.md` heading naming the two
  role types, the need-to-know rows and `docs/roles/catalogue.md`. The 9a and 13a pages are Task 1's
  (`wiki/decisions/plan-fixer-and-translator-are-role-types.md`, `ecc-text-reaches-a-brief-by-line-range.md`): linked,
  never written again.
- K2 (Task 1's tracker contract, `task-01.md` Contracts, 1971558; Global Constraint 14): a closed row keeps its place
  and every cell but the last; its Plan cell becomes `closed: manager-build Task <N> — <what closed it>`; new rows are
  appended at the end of the table, numbered on from the highest id.
- K3 (Task 6's K1, `task-06.md:49`, planner-c; C508): `collect_run.py` refuses a run while an item under a
  `## Deferred` heading of a plan `*.md` on main, read outside fenced code, neither names a tracker id nor has its key
  (its first line up to the first ": ") inside a tracker row (`check_deferred`, `collect_run.py:482-498` at 51dd0ce).
  Each new row quotes the item's key verbatim in its Plan cell; every plan file counts, this task's own Deferred list
  too.
- K4 (Task 2's K7 and `## For Task 11`, `task-02.md:114-122` and `:1165-1167`): every `settings` value of
  `example/agents.json` and `example/agents-judge.json` becomes `_control/<role>-settings.json`, with the tests that read
  them in the same commit; `--model` stays out of `common`.
- K5 (V4, `verify.md:574`; lesson 00:47): every `SKILL.md` edit keeps whole the `## Briefs` sentence that
  `ops/tests/test_ecc_pins.py::test_the_pipeline_briefs_carry_the_input_and_finishing_rules` pins ("Every brief also
  carries the two rules of `example/common.md`: ..."); `ops/tests/test_ecc_pins.py` stays green; a pinned phrase changes
  together with its pin in one commit.
- K6 (Task 8's `## For Task 11`, `task-08.md:1376-1378`; B6): the run's eval page supersedes
  `docs/decisions/0028-pipeline-evals.md` :17, :40, :45, :47, :52, :70, :78 and :104, which stay as history.
- K7 (lesson 00:42 on Task 9 at b8ddbe6; B5, B6, B7): `docs/template/PROJECTS.md` :17 and `ops/new-project.py` :3-4 list
  bootstrap's work as ADR-0009 did; README :19-20 leaves out `docs/handoff/`; ADR-0029 :38-40 is superseded by this
  run's page.
- K8 (C506, `task-10.md` `## For Task 11`): `references/measuring.md:2` points at the script pages under `scripts/docs/`.
- K9 (Task 3's contract; Task 2's K4 and `## For Task 11`): `SKILL.md` names `duty_list.py extract <plan-dir> --out
  <run-dir>/_control/duties.md` and `monitor_records.py watch <run-dir>`, and the watcher's v3: exit 4 only for a changed
  settings file or a removed control file, a changed brief reloaded with an order, `--order`, the registry, the hand-over
  at a unit's end past `handoff_at` 150000.
- K10 (Task 7's `## For Task 11`, `task-07.md:815-816`): the sentence about `measure_manager.py` in `SKILL.md`.
- K11 (V5, lesson 00:57): after K4's move, Task 4's launch and pre-flight tests run again on the two examples.
- K12 (this task, sent to `manager/plan-fixer` for row 11's files cell): `ops/tests/test_contribute.py` (departure 1).
- K13 (this task, sent to `manager/plan-fixer` for row 11's files cell): `$S/scripts/tests/test_preflight.py` (:659-678, V5's test says the example's settings stay outside `_control/` "until Task 11" and lets settings problems pass) and `$S/scripts/README.md` (its `settings` row, :88, K4's "README's `settings` row"; after the TD-008 split the config table stayed in `scripts/README.md`).
- K14 (this task, sent to `manager/plan-fixer` for row 11's files cell): `ops/tests/test_bootstrap_steps.py` (Step 5's test: the template README and `ops/new-project.py`'s docstring name the eleven steps of `ops/bootstrap.py`).
- K15 (this task, sent to `manager/plan-fixer` for row 11's files cell): `docs/template/variables.yaml` (two `omit:` lines, this run's plan folder active and completed, Step 7.5) and `ops/tests/test_new_project_omit.py` (its docstring, two constants and two tests, block 7f).

## Interfaces
Each value below gets a test on which its plausible wrong versions fail (run red on a scratch copy of 51dd0ce,
"Verified").

- `packages/harness/src/harness/catalog.py` (Step 1):
  - `GEORGIAN: re.Pattern[str]` matches one code point of U+10A0-U+10FF, U+1C90-U+1CBF or
    U+2D00-U+2D2F and nothing else. It is built from code points with `chr()`, as `evals.py:53-57`
    builds its own, so the source holds no letter of a refused block (D1); its comment names the three blocks.
  - `LETTER = ": a letter of a refused block (U+10A0-U+10FF, U+1C90-U+1CBF, U+2D00-U+2D2F); tracked files are English only"`, the
    suffix `english_only_problems` writes after `<rel>:<line>` (`catalog.py:218`).
  - `english_only_problems(root: Path) -> list[str]` and `validate_repository(root: Path) -> dict` keep their
    signatures and their order of problems. `gates/attack.py:11` imports `GEORGIAN`, so the attack gate refuses a
    summary holding a letter of any of the three blocks from this task on; `attack.py` itself is not edited.
- `$S/example/agents.json` and `$S/example/agents-judge.json` (Step 2, K4): each agent's `"settings"` is
  `_control/<role>-settings.json`, `<role>` being the agent's name after its last `/` (`<project>/planner` ->
  `_control/planner-settings.json`, `<project>/judge` -> `_control/judge-settings.json`): the path `example/launch.md`'s
  `settings` cells name (:19-25), Task 4's `check_launch` compares (`preflight.py`), and the roles' `_control/**` deny
  hides. The file it names ships as `example/<role>-settings.json`. Nothing else in the two files changes.
- `$S/SKILL.md` and `$S/references/watching.md` (Step 3; K9, K10): SKILL.md stays at most 12,000 bytes with the
  same seven `## ` headings, names verbatim the phrases block 3b lists (the duty list's and the monitor's commands,
  the collector with `--apply --yes <digest>`, `handoff_at` (150000), `_control/registry.json`, `ACK <msg_id>`, the
  `--order` command, exit 4 only for a settings file, the extra prompt file or a removed brief, and
  `scripts/manager/measure_manager.py`), drops the v2 clause and links `references/watching.md`, whose first line is
  `# Watcher, monitor and collector` (`MOVED`) and which keeps the exit codes, the ACK resends and the collector's yes.

## Steps
`W` is builder A's worktree, at the merge commit of `Merged: a+b+c+d`. Every command runs from the shell's start
folder, with no top-level `cd`. `<t>` stands for pytest's time. The builder runs this task's test files, its own
commands and the ruff pair, and the repo-root suite once before the commit (lesson 00:47). `harness validate`,
`docs-check`, `wiki-lint`, `map --check` and the checks of section 10 are the verifier's at M3 (C503's rule).
`BASE` is the commit Task 11 began on: `HEAD` at Step 0 when no hand-over committed WIP, else the parent of the first
WIP commit; whole-change checks measure from it, never from `HEAD` (lesson 23:45).

- [ ] **Step 0 — the base.** Before anything is written, check that the tree holds every lane and the plan, record
  `BASE`, and count the tests (the count V6's fix moves; Step 9 compares against it).
  ```bash
  R=/home/tite/Desktop/agent-system-run/manager-build-2026-10-29
  SHA=$(grep -oE 'Merged: a\+b\+c\+d at [0-9a-f]{7,40}' "$R/lessons.md" | tail -n 1 | grep -oE '[0-9a-f]{7,40}$')
  git -C "${W:?}" merge-base --is-ancestor "${SHA:?}" HEAD && echo "base holds $SHA"
  ```
  Expected: `base holds <sha>`. With no marker `SHA` is empty and the command stops at `${SHA:?}`: wait, do not start.
  ```bash
  git -C "${W:?}" ls-tree --name-only HEAD docs/exec-plans/done/manager-build/ | grep -c '\.md$'
  ```
  Expected: `13` (`00-index.md`, `task-01.md` to `task-11.md`, `manager-build.summary.md`).
  ```bash
  S=.claude/skills/running-specagent-pipelines
  git -C "${W:?}" diff --stat 19a4a95 HEAD -- packages/harness/src/harness/catalog.py \
    packages/harness/tests/test_validate_listing.py ops/contribute.py ops/tests/test_contribute.py \
    "$S/SKILL.md" "$S/references" "$S/example/agents.json" "$S/example/agents-judge.json" "$S/example/README.md" \
    "$S/scripts/tests/test_skill_example.py" "$S/scripts/tests/test_docs.py" "$S/scripts/tests/test_skill_md.py" \
    "$S/scripts/tests/test_preflight.py" "$S/scripts/README.md" evals/graders/pipeline_plan.py evals/regression \
    "$S/scripts/manager" ops/tests/test_ecc_pins.py ops/tests/test_new_project_omit.py \
    docs/exec-plans/tech-debt-tracker.md docs/template \
    ops/new-project.py ops/bootstrap.py docs/quality/LEARNING.md docs/roles/VERSION docs/roles/CHANGELOG.md \
    CHANGELOG.md wiki/index.md wiki/log.md wiki/decisions docs/llms.txt docs/exec-plans/active/README.md
  ```
  Expected: no output (19a4a95 is `Merged: a+b+c+d`, every fix of Tasks 1-10 in it; the main session's merge of this
  plan folder touches none of these paths).
  If a file is listed, the line numbers below do not hold for it: find each anchor this task names by its text
  (`grep -n`), note the shift in the build log, and send the `--stat` lines to `manager/plan-fixer` only when an anchor
  text is gone.
  ```bash
  S=.claude/skills/running-specagent-pipelines
  git -C "${W:?}" rev-parse --short HEAD
  uv run --project "${W:?}" pytest -q --collect-only "${W:?}/packages" "${W:?}/$S/scripts/tests" "${W:?}/ops/tests" \
    | tail -n 1
  ```
  Expected: the short sha, which is `BASE` (write it into the build log), then `<N0> tests collected in <t>s`; write
  `N0` into the build log (1567 on 19a4a95, the main session's repo-root run at the merge). Step 9.2 expects
  `N0 + 16` tests: the twelve cases of block 1b, the test of block 3b, the test of block 5d and the two tests of
  block 7f (1c replaces a test, 2a-2c change tests). The three paths are the `testpaths` of `pyproject.toml` (:25):
  pytest reads `testpaths` only when it runs from the rootdir with no path given, and a bare `"${W:?}"` collects
  fewer (1174 on 19a4a95), because pytest's default `norecursedirs` skips `.claude` and with it the skill's tests.
- [ ] **Step 1 — the three blocks in `harness validate`.** Spec 8.3.11; Interfaces `catalog.py`.
  1. Write the three blocks of "Tests in full", 1a-1c: in `packages/harness/tests/test_validate_listing.py` replace
     lines 17-18 (`LETTER`, `LOW, HIGH`) with block 1a, add `import pytest` on the line above `from harness import
     catalog` (one import block, as `test_evals_llm.py:9-10`; ruff's I001 refuses a blank line between them), and put
     block 1b just above `def test_the_template_holds_no_georgian_letter():`; in `ops/tests/test_contribute.py` replace
     the function at :357-366 (`test_the_georgian_check_covers_the_check_of_harness_validate_and_the_two_blocks_it_misses`)
     with block 1c.
  2. The red run:
     ```bash
     uv run --project "${W:?}" pytest -q "${W:?}/packages/harness/tests/test_validate_listing.py" \
       "${W:?}/ops/tests/test_contribute.py"
     ```
     Expected: `9 failed, 46 passed in <t>s`. The nine: `test_a_georgian_letter_in_a_listed_file_is_one_problem_at_its_first_line`
     and `test_a_project_narrows_the_letter_check_with_english_only` (the new `LETTER`), six cases of
     `test_each_georgian_block_is_a_problem_from_its_first_to_its_last_code_point` (`[4256]`, `[4351]`: found, old
     suffix; `[7312]`, `[7359]`, `[11520]`, `[11567]`: not found), and `test_the_georgian_check_is_the_check_of_harness_validate`.
  3. Edit `catalog.py:61-62` as "Interfaces" says: `GEORGIAN` holds the three blocks, `LETTER` names them.
  4. The green run: the command of 2. Expected: `55 passed in <t>s`.
  5. The texts that name the old figure (lesson 00:42, B5 and B6):
     ```bash
     git -C "${W:?}" grep -n -e 'U+10A0-U+10FF)' -e 'two_blocks_it_misses' -e 'the refused block;' -- . ':!docs/exec-plans'
     ```
     Expected: one line, `docs/decisions/0030-the-template-is-english-only.md:36:...` (history, departure 2; Step 7's
     entries say what changed). `ops/tests/test_new_vault.py:37` keeps its own one-block pattern: it checks the vault
     script's output, not `harness validate` ("Deferred").
- [ ] **Step 2 — the example agents read their settings under `_control/`.** K4, K11; Interfaces `agents.json`.
  1. Write blocks 2a-2c of "Tests in full": in `$S/scripts/tests/test_skill_example.py`, the last line of
     `test_the_configs_name_every_role_and_only_files_the_example_has` (:97) becomes block 2a; in
     `$S/scripts/tests/test_docs.py`, `test_the_example_config_is_v2_and_check_accepts_it` makes `_control/` before it
     writes the settings files (block 2b, :126-128); in `$S/scripts/tests/test_preflight.py`, the comment above
     `test_the_example_launch_table_has_a_row_for_every_agent_of_the_example_configs` (:660-662), which says the
     example's settings stay outside `_control/` "until Task 11", and the test's last two lines (:677-678), which let
     settings problems pass, become block 2c (V5's test now requires the pair to pass `check_launch` whole).
  2. The red run:
     ```bash
     S=.claude/skills/running-specagent-pipelines
     uv run --project "${W:?}" pytest -q "${W:?}/$S/scripts/tests/test_skill_example.py" \
       "${W:?}/$S/scripts/tests/test_docs.py" "${W:?}/$S/scripts/tests/test_preflight.py"
     ```
     Expected: `2 failed, 62 passed in <t>s` (19a4a95; 61 passed on 51dd0ce, before V7's test):
     `test_the_configs_name_every_role_and_only_files_the_example_has`
     and `test_the_example_launch_table_has_a_row_for_every_agent_of_the_example_configs`; block 2b passes before the
     move as after it.
  3. The move: each `"settings": "_<role>-settings.json"` of `example/agents.json` (:54, :69, :84, :98, :112, :128) and
     `example/agents-judge.json` (:30) becomes `"settings": "_control/<role>-settings.json"`. The `settings` row of
     `$S/scripts/README.md` (`| \`settings\` | its settings file in \`run_dir\`, ...`, :88 at 19a4a95, R502's fix
     5b8d3b1 included) names the form: `| \`settings\` | its settings file in \`run_dir\`
     (\`_control/<role>-settings.json\` in the examples, behind every role's \`_control/**\` deny), passed as text with
     \`--settings\` |`. Every other reader says `_control/<role>-settings.json` already (`example/README.md:10-12`,
     `example/launch.md:19-25`, `references/launch.md:4`, `references/sandbox-and-blindness.md:6`).
  4. The green run: the command of 2. Expected: `64 passed in <t>s` (19a4a95).
  5. Every reader of the old value (lesson 20:53; the tests build their own configs and keep theirs):
     ```bash
     git -C "${W:?}" grep -n -E '"_[a-z-]+-settings\.json"|`_[a-z-]+-settings\.json`|_\{role\}-settings' -- "$S" ':!*/tests/*'
     ```
     Expected: no output (on 19a4a95 it lists exactly the seven lines of 3).
- [ ] **Step 3 — `SKILL.md` names the tools of the other lanes.** K5, K8, K9, K10; Interfaces `SKILL.md` and
  `references/watching.md`. SKILL.md is 11,764 bytes at 51dd0ce, 236 under the cap: the watcher's detail moves to a
  new reference page, SKILL.md keeps what the manager runs, and `## Briefs` is not touched (K5).
  1. Write blocks 3a and 3b of "Tests in full" into `$S/scripts/tests/test_skill_md.py`: 3a replaces the last line of
     `MOVED` (`"choosing-roles-and-skills.md": "Choosing roles and skills",`, :34); 3b follows the file's last test,
     after two blank lines.
  2. The red run:
     ```bash
     S=.claude/skills/running-specagent-pipelines
     uv run --project "${W:?}" pytest -q "${W:?}/$S/scripts/tests/test_skill_md.py"
     ```
     Expected: `3 failed, 3 passed in <t>s` (51dd0ce): `test_skill_md_keeps_six_sections_and_each_moved_section_is_one_reference_file`
     (no `watching.md`), `test_skill_md_and_its_references_name_only_files_the_skill_has_and_the_current_rules` (no
     link to it) and `test_skill_md_names_the_manager_tools_and_the_third_watcher_and_its_page_holds_the_rest`.
  3. The texts, from "Texts in full": in `$S/SKILL.md`, the third bullet of `## Waiting, parking, watching` (from
     `- The supervisor stops an agent's process` to ``writes its `_agents-v2.json`.``, :83-95) becomes block 3c (two
     bullets); the second bullet of `## Changing orders` (from `- Anything else:` to `Pause the watcher while you do
     this.`, :101-103) becomes block 3d; the `[Measuring the pipeline]` entry of `## References` (:115-116) becomes
     block 3e; block 3f is appended after the last entry (:121). `$S/references/watching.md` is block 3g; lines 2-3 of
     `$S/references/measuring.md` become block 3h (K8: after Task 10 the README holds no usage line).
  4. The green run: the command of 2. Expected: `6 passed in <t>s`. Then:
     ```bash
     wc -c < "${W:?}/$S/SKILL.md"
     uv run --project "${W:?}" pytest -q "${W:?}/ops/tests/test_ecc_pins.py"
     ```
     Expected: `11696` (no other step edits SKILL.md), then `13 passed in <t>s` (K5).
  5. Every pointer into the moved and changed text (lesson 01:19; B9: tests left out, 3b's assert quotes the bullet):
     ```bash
     git -C "${W:?}" grep -n -e 'exit 4, instead of a launch' -e 'Pause the watcher' -e 'usage and options in' -- . ':!docs/exec-plans' ':!*/tests/*'
     ```
     Expected: no output (on 51dd0ce `$S/SKILL.md:92`, `$S/SKILL.md:103` and `$S/references/measuring.md:2`, the
     lines 3 replaces; no other page or script text quotes the watcher's bullet, `git grep` of its phrases).
- [ ] **Step 4 — the tracker: closed rows, TD-002, and a row for every Deferred item.** K2, K3; spec 5.9.4 (Coverage:
  "the tracker rows closed and the Deferred items added as rows"); departure 3. Three rows close (TD-008 by Task 10,
  TD-010 by Task 6, TD-011 by Task 8), TD-002 stays open with its reason, and ten rows follow TD-012: nine open rows
  holding the plan's 31 debts by owner and next step, and TD-022, closed, holding the 16 items that a task of the run
  carried or a decision settled. Each Plan cell quotes the keys of its items (K3); the first item of `task-09.md` names
  TD-007 and passes by it, so TD-018 quotes its first words only.
  1. The tracker is 19a4a95's (the same as 51dd0ce's, where block 4a was measured), and the three done commits are in
     the tree:
     ```bash
     git -C "${W:?}" diff --quiet 19a4a95 HEAD -- docs/exec-plans/tech-debt-tracker.md && echo same
     for c in 129a9d5 22eca3d baf3590; do git -C "${W:?}" merge-base --is-ancestor "$c" HEAD && echo "$c"; done
     ```
     Expected: `same`, then `129a9d5`, `22eca3d` and `baf3590` (the done commits of Tasks 10, 6 and 8:
     `build-log-b.md:14`, `build-log-c.md:6`, `build-log-c.md:14`).
  2. The red run, the collector's own check (`check_deferred`, K3) on BASE:
     ```bash
     S=.claude/skills/running-specagent-pipelines
     D='import argparse, importlib.util, sys; s = importlib.util.spec_from_file_location("c", sys.argv[1]); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); print("\n".join(m.check_deferred(argparse.Namespace(repo=sys.argv[2], main=sys.argv[3], plan="docs/exec-plans/done/manager-build"))) or "no refusal")'
     python3 -I -c "$D" "${W:?}/$S/scripts/collect_run.py" "${W:?}" "${BASE:?}" | grep -c '^refused: Deferred item'
     ```
     Expected: `47`: the 46 Deferred items of the index and Tasks 1-10 that name no tracker id, and this task's own
     (measured on a scratch repository holding this plan folder and 51dd0ce's tracker; without the `grep`, the first
     line is `refused: Deferred item "8.3.17 per-plugin start-up cost" (00-index.md) is not in the tracker`). Another
     count means the plan changed after this measurement: each refused item that block 4a does not quote gets its key
     quoted in the Plan cell of its owner's row, in the same form, and the build log names it.
  3. The edit, from "Texts in full": in `docs/exec-plans/tech-debt-tracker.md` the lines of TD-002, TD-008, TD-010 and
     TD-011 become the first four lines of block 4a (each keeps its place and every cell but Plan, K2); the ten lines
     TD-013 to TD-022 of block 4a follow the last row (TD-012), with no line between.
  4. The green run:
     ```bash
     S=.claude/skills/running-specagent-pipelines
     D='import argparse, importlib.util, sys; s = importlib.util.spec_from_file_location("c", sys.argv[1]); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); print("\n".join(m.check_deferred(argparse.Namespace(repo=sys.argv[2], main=sys.argv[3], plan="docs/exec-plans/done/manager-build"))) or "no refusal")'
     git -C "${W:?}" add docs/exec-plans/tech-debt-tracker.md
     python3 -I -c "$D" "${W:?}/$S/scripts/collect_run.py" "${W:?}" "$(git -C "${W:?}" write-tree)"
     ```
     Expected: `no refusal`.
  5. K2 and the size:
     ```bash
     git -C "${W:?}" show "${BASE:?}:docs/exec-plans/tech-debt-tracker.md" | python3 -I -c 'import sys; cut = lambda rows: [r.rsplit(" | ", 1)[0] for r in rows]; old = [l for l in sys.stdin.read().splitlines() if l.startswith("| TD-")]; lines = open(sys.argv[1], encoding="utf-8").read().splitlines(); new = [l for l in lines if l.startswith("| TD-")]; ids = [r.split(" | ", 1)[0][2:] for r in new]; changed = [o.split(" | ", 1)[0][2:] for o, n in zip(old, new) if o != n]; same = cut(new[:len(old)]) == cut(old) and lines[4:] == new and ids == [f"TD-{i:03d}" for i in range(1, len(new) + 1)]; print("ok" if same else "changed", len(old), len(new), *changed)' "${W:?}/docs/exec-plans/tech-debt-tracker.md"
     wc -c < "${W:?}/docs/exec-plans/tech-debt-tracker.md"
     ```
     Expected: `ok 12 22 TD-002 TD-008 TD-010 TD-011` (the twelve rows keep their place and every cell but Plan, only
     those four Plan cells change, and the rows run TD-001 to TD-022 with no line between them), then `11723` (Global
     Constraint 4: at most 12,000; 5,007 at 51dd0ce).
  Measured on the scratch repository: red 47, green `no refusal`. Without TD-020 the check refuses one item (this
  task's own), without TD-022 sixteen, and with one key paraphrased (index item 8 without "Task 1's") or cut (Task 2's
  first item before its parenthesis) one each; the K2 check prints `changed` for a cell but Plan changed (TD-010's
  priority), new rows numbered from TD-012 or a blank line before them, and an extra id when any other Plan cell
  changes (TD-004).
- [ ] **Step 5 — the texts the run made false.** Lesson 00:42 (B7, K7; index row 11's files cell): three texts say less
  than the tree does. `docs/template/PROJECTS.md` :17 and `ops/new-project.py` :4 name four of the eleven steps of
  `ops/bootstrap.py` (its docstring, items 1-11), README :19-20 leaves `docs/handoff/` out of what `--container` makes
  (new-project :6-7 names it), and `docs/quality/LEARNING.md` :19 says CI runs "the regression suite (threshold 0.9)",
  where Task 8's `ci.yml` runs it on every push and pull request, graded on its recorded baselines at threshold 1.0, and
  `evals.yml` no longer runs it.
  1. Write block 5d of "Tests in full" after the last test of `ops/tests/test_bootstrap_steps.py` (11 tests at
     51dd0ce), and add `import ast` on the line above `import importlib.util` and `import re` between `import os` and
     `import sys` (one import block).
  2. The red run:
     ```bash
     uv run --project "${W:?}" pytest -q "${W:?}/ops/tests/test_bootstrap_steps.py"
     ```
     Expected: `1 failed, 11 passed in <t>s`. The one is
     `test_the_template_readme_and_new_project_name_every_step_of_the_bootstrap`: `just`, the git hooks, the sandbox,
     the first code graph, graphify's skill, the user-level pipeline skill and harness doctor are missing from both
     texts.
  3. The edits, from "Texts in full": block 5a in place of `docs/template/PROJECTS.md` :17-21 (five lines, from "sets the
     project up" to "Without it the"), block 5b in place of the docstring's line `ops/new-project.py` :4 (from "uv, the
     workspace" to "[--no-setup]"), block 5c in place of `docs/quality/LEARNING.md` :18-19 (item 6, "Gate.").
  4. The green run: the command of 2. Expected: `12 passed in <t>s`.
  5. The old texts are gone:
     ```bash
     git -C "${W:?}" grep -n -e 'uv, the workspace, the plugins, the language servers' \
       -e 'and `experiments/` (copies made for trials); a' -e 'regression suite (threshold 0.9)' -- . ':!docs/exec-plans'
     ```
     Expected: no output (at 51dd0ce four lines: README :17 and :20, new-project :4, LEARNING :19). The root
     `README.md:164` stays: its row says that `uv`, the workspace, the plugins and the language servers set themselves
     up, which is true and claims no full list; `docs/decisions/README.md:14` and ADR-0028 :70 are history (Step 6's
     pages supersede ADR-0028 and ADR-0029 :38-40, K6, K7).
  Measured on a copy of 51dd0ce with Steps 1-3: red `1 failed, 11 passed`, green `12 passed`, `ruff check` and
  `ruff format --check` clean on both `.py` files. Each wrong version alone is red: the docstring left as it was; the
  docstring without `harness doctor`; the README without it (README :28 says "`harness doctor` checks both paths",
  which is why the test reads the span up to the first `--no-setup` and not the paragraph); "the role sandbox" for
  "the sandbox"; "adjust" for "just" (whole words).
- [ ] **Step 6 — this run's decision pages.** ADR-0027: the owner's decisions this run built are written with the
  work, a page each under `wiki/decisions/` with its `.summary.md` (index row 11's files cell). The pages Task 1 wrote
  for answers 9a and 13a exist and are linked, not written again.
  1. Write blocks 6a-6m of "Texts in full" verbatim, each page and its summary whole (`updated: 2026-10-30`, the build
     day the plan expects; a later build day changes that value only):

     | block | page `wiki/decisions/<slug>.md` | from |
     |---|---|---|
     | 6a | `control-plane-in-the-skill` | Task 2's decision 10a (`task-02.md:1159`); question 10 |
     | 6b | `monitor-answers-no-request` | Task 3's list (`task-03.md:1331`); spec 5.5, need 4 |
     | 6c | `request-answer-lines` | Task 3's list; spec 5.4, 8.3.3, check 10.7 |
     | 6d | `duty-list-from-the-plan` | Task 3's list; spec 5.1.2, 8.2.3, check 10.11 |
     | 6e | `collector-yes-then-standing-rule` | Task 6's list (`task-06.md:1050`); answer 4a |
     | 6f | `collector-save-check` | Task 6's list; spec 5.9.4, 8.2.13, TD-010 |
     | 6g | `code-cases-gate-every-push-sessions-run-nightly` | Task 8 (`task-08.md:1376-1378`); K6: supersedes eight lines of ADR-0028 |
     | 6h | `skill-script-pages` | Task 10 (`task-10.md:917`); TD-008, spec 8.3.9; departure 4 |
     | 6i | `dated-api-prices` | Task 10 (`task-10.md:921`); spec 8.3.14 |
     | 6j | `roles-and-sessions-keep-their-names` | answer 7a, which no task implements (index row 11) |
     | 6k | `the-spec-writers-model-is-a-dated-exception` | answer 8a, the same; the page names no model |
     | 6l | `a-vault-graph-is-measured-before-it-is-built` | answer 12, the same; tracker TD-015 |
     | 6m | `bootstrap-runs-eleven-steps-in-order` | K7 (lesson 00:42, B7): supersedes ADR-0029 :38-40 |

  2. The red run, the test file that pins the wiki (lesson 22:27: `wiki-lint` itself is the verifier's):
     ```bash
     uv run --project "${W:?}" pytest -q "${W:?}/packages/harness/tests/test_wiki_decisions.py"
     ```
     Expected: `1 failed, 22 passed in <t>s` (`23 passed` before the pages):
     `test_the_template_wiki_lints_clean_with_its_first_decision_page`, whose message begins
     `AssertionError: ['decisions/a-vault-graph-is-measured-before-it-is-built.md: not listed in index.md', ` and holds
     only such problems, one per page; Step 8's index lines turn it green. Another message (a YAML error from a value
     that holds `: ` or ` #`, a dead link, a field value outside its list) is a copy error: compare the page with its
     block.
  3. Every page and summary in place, and none names a model or a plan file (a plan moves to `completed/`, and the lint
     passes a link into `active/` while the plan is there):
     ```bash
     ls "${W:?}/wiki/decisions" | grep -c -x -E '(control-plane-in-the-skill|monitor-answers-no-request|request-answer-lines|duty-list-from-the-plan|collector-yes-then-standing-rule|collector-save-check|code-cases-gate-every-push-sessions-run-nightly|skill-script-pages|dated-api-prices|roles-and-sessions-keep-their-names|the-spec-writers-model-is-a-dated-exception|a-vault-graph-is-measured-before-it-is-built|bootstrap-runs-eleven-steps-in-order)(\.summary)?\.md'
     grep -l -i -E 'opus|sonnet|haiku|fable|exec-plans' "${W:?}"/wiki/decisions/*.md
     ```
     Expected: `26`, then no output (no page at 19a4a95 matches the second).

  Measured on an export of 19a4a95 with this plan folder and Steps 3 and 5's files: the test file 23 passed, then
  `1 failed, 22 passed` with the pages, then 23 passed with Step 8's blocks 8a and 8b; `wiki.lint` alone lists exactly
  the thirteen `not listed in index.md` problems after the pages. Wrong versions, each run once: `why: list prices:
  they change,` in 6i raises yaml's `ScannerError` (`mapping values are not allowed here`); a link to
  `scripts/README-old.md` in 6h, one `dead link` problem; `decision_status: accepted` in 6c, one problem (`'accepted'
  is not one of ['decided', 'revised', 'withdrawn']`); 6d's index line left out at Step 8, one `not listed` problem.
  The largest page is 2,432 bytes.
- [ ] **Step 7 — the release: VERSION, MIGRATIONS, CHANGELOG, the role bundle, the omit lines.** Spec 5.9.1; K1, K15;
  departure 2; the items of Task 7's and Task 10's `## For Task 11` (`task-07.md:810-822`, `task-10.md:926-928`). The
  release counts from 1.4.0 (63b25a3, the last commit of `docs/template/VERSION`), so it also carries the shared-base
  run's unreleased changes: the `## [Unreleased]` items of `CHANGELOG.md` become 1.5.0's, and the migration entry lists
  every template-owned path changed since 1.4.0 (`git diff --stat 63b25a3 19a4a95` and this task's files).
  1. `docs/template/VERSION`: `1.4.0` becomes `1.5.0`; `docs/roles/VERSION`: `1.13.0` becomes `1.14.0` (K1;
     `harness version-check` asks a new roles version when an instruction file changed: `audit.py:17-20` at 19a4a95
     counts `.claude/skills/`, `.claude/agents/`, `.claude/hooks/`, `.claude/settings.json`, `templates/` and
     `plugins/`). Each file holds the version and one newline.
  2. Block 7a goes into `docs/roles/CHANGELOG.md` right above `## 1.13.0` (:6 at 19a4a95), followed by one blank line:
     the 1.14.0 heading names the instruction files changed since 1.13.0 (63b25a3), the shared-base run's and this
     run's, with the two role types, the need-to-know rows and `docs/roles/catalogue.md` (K1) and Task 7's files.
  3. Block 7b goes into `docs/template/MIGRATIONS.md` right above `## 1.4.0` (:6 at 19a4a95), followed by one blank
     line: the four items of `## Entry format` (:59-63), each on one line as the 1.4.0 entry writes them, so that a
     project's sync run takes the entry as its brief.
  4. `CHANGELOG.md`: the line `## [1.5.0] - 2026-10-30` and one blank line go right below `## [Unreleased]` and its blank
     line (:5-6 at 19a4a95), as the 1.4.0 release did (63b25a3), so `## [Unreleased]` stays, empty; block 7c goes right
     below the first `### Added` (the shared-base run's items follow it), block 7d right below the first `### Changed`.
     The date is this plan's day; a build on a later UTC day writes that day (`date -u +%F`) in this heading only.
  5. `docs/template/variables.yaml`: block 7e is appended after the last `omit:` line (:27 at 19a4a95, the completed
     template-core folder). `omit:` names the template-core plan and not this one, so a project made from the 1.5.0
     tree would get this folder and Step 8's plans line: `ops/new-project.py` copies every tracked file but the `omit:`
     prefixes (:51 at 19a4a95) and drops a copied page's line that links into an omitted folder (:30-41, :65-66).
     Block 7f is the test (K15): in `ops/tests/test_new_project_omit.py` the module docstring (:1-2) becomes 7f's first
     part, the two constants go right below `DONE` (:15), and the two tests follow the file's last test after two blank
     lines.
  6. The red run, with block 7f in and before block 7e:
     ```bash
     uv run --project "${W:?}" pytest -q "${W:?}/ops/tests/test_new_project_omit.py"
     ```
     Expected: `2 failed, 3 passed in <t>s` (the two new tests). The green run, after block 7e and the changelogs:
     ```bash
     uv run --project "${W:?}" pytest -q "${W:?}/ops/tests/test_new_project_omit.py" \
       "${W:?}/packages/harness/tests/test_documents.py"
     ```
     Expected: `17 passed in <t>s` (`test_documents.py` reads both changelogs for the phrases R11 bans).
  7. The form of the release:
     ```bash
     cat "${W:?}/docs/template/VERSION" "${W:?}/docs/roles/VERSION"
     grep -n '^## 1\.1[34]\.0$' "${W:?}/docs/roles/CHANGELOG.md"
     grep -n '^## ' "${W:?}/docs/template/MIGRATIONS.md" | head -n 2
     sed -n '/^## 1\.5\.0$/,/^## 1\.4\.0$/p' "${W:?}/docs/template/MIGRATIONS.md" \
       | grep -cE '^- (Changed template-owned paths|Steps|Checks|Breaks active runs): '
     grep -n '^## \[' "${W:?}/CHANGELOG.md" | head -n 3
     ```
     Expected: `1.5.0`, `1.14.0`; `6:## 1.14.0`, `30:## 1.13.0`; `6:## 1.5.0`, `12:## 1.4.0`; `4`; `5:## [Unreleased]`,
     `7:## [1.5.0] - 2026-10-30`, `71:## [1.4.0] - 2026-10-29`.

  Measured on a fresh export of 19a4a95, a git copy with one base commit: the omit test file `2 failed, 3 passed` with
  block 7f alone and `5 passed` with 7e; with `test_documents.py`, `17 passed` after the changelogs; the five commands as
  expected; ruff check and format clean on the test file; the longest line of 7a, 7c, 7d and 7f 119 characters; no
  character outside ASCII in any block. Wrong `omit:` lines, each run once: none, `2 failed, 3 passed`; the active
  folder only, `2 failed` (the completed folder is copied); both lines without the trailing slash, `1 failed` (the list
  test); `docs/exec-plans/active/` whole, `4 failed, 1 passed`; `manager_build/`, `2 failed`. `harness version-check`
  (Step 9.4) on the same copy with Step 3's `SKILL.md` committed: `"ok": true`; with `docs/roles/VERSION` left at
  1.13.0, `instruction files changed and docs/roles/VERSION did not`; with the heading `## 1.14`,
  `docs/roles/CHANGELOG.md has no heading for 1.14.0`.
- [ ] **Step 8 — the indexes: `wiki/index.md`, `wiki/log.md`, `docs/llms.txt`, the plans list.**
  1. Block 8a, the thirteen index lines in the order of blocks 6a-6m, goes into `wiki/index.md` right after the line
     that links `decisions/the-manager-profile-is-measured-at-its-first-call.md` (:27 at 19a4a95, the last line of
     `## Decisions`). Block 8b is appended to `wiki/log.md` after one blank line.
  2. The plans list: one line under `## Plans` of `docs/exec-plans/active/README.md`, after the blank line below the
     heading (the section is empty at 19a4a95), unless the main session's merge of this folder brought it:
  ```markdown
  - [manager-build](manager-build/00-index.md): the template's manager-build run, eleven tasks to release 1.5.0
  ```
     `harness docs-check` finds the plan's files through this line (`catalog.listed`, its third way,
     `catalog.py:277-292` at 19a4a95); without it none of this folder's thirteen files is listed. `docs/llms.txt` needs
     no line: Task 11 adds no file under `docs/`, and it links `exec-plans/active/README.md` already.
  3. The green run: the command of Step 6.2. Expected: `23 passed in <t>s`.
  4. The index's size and the plans line:
     ```bash
     wc -c < "${W:?}/wiki/index.md"
     grep -c '(manager-build/00-index.md)' "${W:?}/docs/exec-plans/active/README.md"
     ```
     Expected: `8330` (5,016 at 19a4a95; an index is at most 12 KB, Global Constraint 4), then `1`.

  Measured on the export of Step 6: the test file 23 passed after blocks 8a and 8b; `catalog.listed` finds none of the
  folder's 13 files before the plans line and all 13 after it; the line pointing at `manager-build/README.md` or at
  `manager_build/` finds none.
- [ ] **Step 9 — the checks, the commit and the log line.** Lesson 00:47 (the repo-root suite once, before the done
  line), lessons 23:12 and 23:58 (no added code line over 120 characters, counted in characters), lesson 23:45 (the
  whole change measured from `BASE`), Global Constraint 12 (the commit's form).
  1. The task's test files, then ruff on the whole tree, as the CI step does (`.github/workflows/ci.yml:16`):
     ```bash
     S=.claude/skills/running-specagent-pipelines
     uv run --project "${W:?}" pytest -q "${W:?}/packages/harness/tests/test_validate_listing.py" \
       "${W:?}/packages/harness/tests/test_wiki_decisions.py" "${W:?}/packages/harness/tests/test_documents.py" \
       "${W:?}/ops/tests/test_contribute.py" "${W:?}/ops/tests/test_bootstrap_steps.py" \
       "${W:?}/ops/tests/test_new_project_omit.py" "${W:?}/ops/tests/test_ecc_pins.py" \
       "${W:?}/$S/scripts/tests/test_skill_example.py" "${W:?}/$S/scripts/tests/test_docs.py" \
       "${W:?}/$S/scripts/tests/test_preflight.py" "${W:?}/$S/scripts/tests/test_skill_md.py" | tail -n 1
     uv run --project "${W:?}" ruff check "${W:?}" && uv run --project "${W:?}" ruff format --check "${W:?}"
     ```
     Expected: `189 passed in <t>s`, then `All checks passed!` and `215 files already formatted` (both counts on
     19a4a95 with this task's files). A file the formatter would change is named instead; fix it and run 1 again.
  2. The repo-root suite, once, with `pyproject.toml`'s three `testpaths` (Step 0):
     ```bash
     S=.claude/skills/running-specagent-pipelines
     (ulimit -v 8388608; timeout -k 10 900 uv run --project "${W:?}" pytest -q "${W:?}/packages" \
       "${W:?}/$S/scripts/tests" "${W:?}/ops/tests" | tail -n 1)
     ```
     Expected: `<N0 + 15> passed, 1 skipped in <t>s` (`1582 passed, 1 skipped` on 19a4a95 with this task, about 95
     seconds); copy the line into the build log. The skipped test is `packages/harness/tests/test_gate_sandbox.py:57`:
     it skips when no sandbox can start inside the session's own ("no sandbox on this machine"), as in every repo-root
     run of this build's logs; outside a sandbox the line is `<N0 + 16> passed`. A failure, or a total other than
     `N0 + 16`, stops the task here: a pinned phrase this task changed is changed together with its pin (lesson 00:47).
  3. Stage the fifty-four paths of the `files:` line, then check the staged change against `BASE`:
     ```bash
     S=.claude/skills/running-specagent-pipelines
     D=wiki/decisions; PAGES=""
     for s in control-plane-in-the-skill monitor-answers-no-request request-answer-lines duty-list-from-the-plan \
       collector-yes-then-standing-rule collector-save-check code-cases-gate-every-push-sessions-run-nightly \
       skill-script-pages dated-api-prices roles-and-sessions-keep-their-names \
       the-spec-writers-model-is-a-dated-exception a-vault-graph-is-measured-before-it-is-built \
       bootstrap-runs-eleven-steps-in-order; do PAGES="$PAGES $D/$s.md $D/$s.summary.md"; done
     git -C "${W:?}" add -- packages/harness/src/harness/catalog.py packages/harness/tests/test_validate_listing.py \
       ops/tests/test_contribute.py "$S/example/agents.json" "$S/example/agents-judge.json" \
       "$S/scripts/tests/test_skill_example.py" "$S/scripts/tests/test_docs.py" "$S/scripts/tests/test_preflight.py" \
       "$S/scripts/README.md" "$S/SKILL.md" "$S/references/watching.md" "$S/references/measuring.md" \
       "$S/scripts/tests/test_skill_md.py" docs/exec-plans/tech-debt-tracker.md docs/template/PROJECTS.md \
       ops/new-project.py ops/tests/test_bootstrap_steps.py docs/quality/LEARNING.md $PAGES \
       docs/template/VERSION docs/template/MIGRATIONS.md CHANGELOG.md docs/roles/VERSION docs/roles/CHANGELOG.md \
       docs/template/variables.yaml ops/tests/test_new_project_omit.py wiki/index.md wiki/log.md \
       docs/exec-plans/active/README.md
     git -C "${W:?}" diff --cached --name-only "${BASE:?}" | wc -l
     git -C "${W:?}" status --porcelain --untracked-files=no | grep -c -v '^[AM]  '
     git -C "${W:?}" diff --cached -U0 "${BASE:?}" -- '*.py' | python3 -I -c 'import sys; print(sum(1 for s in
       sys.stdin.buffer.read().decode("utf-8").splitlines() if s[:1] == "+" and s[:3] != "+++" and len(s) > 121))'
     ```
     Expected: `54` (27 changed files, `references/watching.md` and the 26 page files new), then `0` (no tracked file
     changed outside the staged list), then `0` (no added Python line over 120 characters: 110 added lines on 19a4a95,
     the longest 120; characters, not mawk's bytes, lesson 23:58). Then commit with the message of `## Commit message`
     (subject line, blank line, body) and the attribution lines your assignment gives.
  4. After the commit, the whole change and the role bundle's version:
     ```bash
     git -C "${W:?}" diff --name-only "${BASE:?}" HEAD | wc -l
     CLAUDE_PROJECT_DIR="${W:?}" uv run --project "${W:?}" harness version-check --base "${BASE:?}"
     ```
     Expected: `54`, then (measured on the 19a4a95 copy of Step 7 with this task committed on top of the plan folder):
     ```text
     {
       "ok": true,
       "version": "1.14.0",
       "changed": [
         ".claude/skills/running-specagent-pipelines/SKILL.md",
         ".claude/skills/running-specagent-pipelines/example/agents-judge.json",
         ".claude/skills/running-specagent-pipelines/example/agents.json",
         ".claude/skills/running-specagent-pipelines/references/measuring.md",
         ".claude/skills/running-specagent-pipelines/references/watching.md",
         ".claude/skills/running-specagent-pipelines/scripts/README.md",
         ".claude/skills/running-specagent-pipelines/scripts/tests/test_docs.py",
         ".claude/skills/running-specagent-pipelines/scripts/tests/test_preflight.py",
         ".claude/skills/running-specagent-pipelines/scripts/tests/test_skill_example.py",
         ".claude/skills/running-specagent-pipelines/scripts/tests/test_skill_md.py"
       ],
       "problems": []
     }
     ```
     The command takes the root from `CLAUDE_PROJECT_DIR` or the working directory (`cli.py:39-42`) and reads
     `git diff --name-only BASE...HEAD` (`audit.py:175-194`): only committed work counts, and with nothing committed it
     answers `{"ok": true, "status": "no_instruction_change"}` (`audit.py:183`), which is not this step's result.
     With `docs/roles/VERSION` at 1.13.0 the answer is `"ok": false` with `instruction files changed and
     docs/roles/VERSION did not`; with the heading `## 1.14`, `docs/roles/CHANGELOG.md has no heading for 1.14.0`
     (Step 7's measure).
  5. Append `Task 11: done — <sha7 of HEAD>` to `build-log-a.md` in the run folder, as your assignment says, with the
     last line of the run of 2 (lesson 00:47).

  Measured on a fresh export of 19a4a95 (a git copy) with this plan folder, the files of Steps 1-5 (Step 2's
  `scripts/README.md` row included), the tracker of Step 4, Steps 6 and 8 and Step 7: the collect count 1567 before
  and 1583 after, with the three paths (a bare path collects 1174 and 1189); 1 as expected; the suite
  `1582 passed, 1 skipped` both from the tree's root (its `testpaths`) and with the three paths from outside, the skip
  `test_gate_sandbox.py:57` (this session's own sandbox); 3 `54`, `0`, `0`; after the commit 4 as shown. The four
  blocks ran verbatim on a clone in the builder's state (HEAD at the plan folder, the task's files unstaged; 1 and 2
  with `uv run --project` mapped onto the plan worktree's venv), and the commit's tree was the measured one. Wrong
  versions, each once: 3's list without `$PAGES`, `28`; without `wiki/index.md`, `53` and `1`; an added comment line
  of 121 characters (em dashes, 359 bytes), `1`, and 1 then ends `1 file would be reformatted, 214 files already
  formatted`.

## Tests in full
**1a** `packages/harness/tests/test_validate_listing.py`, replacing lines 17-18 (`LETTER`, `LOW, HIGH`):
```python
LETTER = ": a letter of a refused block (U+10A0-U+10FF, U+1C90-U+1CBF, U+2D00-U+2D2F); tracked files are English only"
LOW, HIGH = chr(0x10A0), chr(0x10FF)
# Both edges of each refused block and the code point just outside it (8.3.11; lessons R4 and V3)
EDGES = {0x109F: False, 0x10A0: True, 0x10FF: True, 0x1100: False,
         0x1C8F: False, 0x1C90: True, 0x1CBF: True, 0x1CC0: False,
         0x2CFF: False, 0x2D00: True, 0x2D2F: True, 0x2D30: False}  # fmt: skip
```

**1b** the same file, just above `def test_the_template_holds_no_georgian_letter():`:
```python
@pytest.mark.parametrize("code", sorted(EDGES))
def test_each_georgian_block_is_a_problem_from_its_first_to_its_last_code_point(tmp_path: Path, code: int):
    root = repo(tmp_path)
    (root / "x.md").write_text("English\n" + chr(code) + "\n", encoding="utf-8")
    git(root, "add", "x.md")
    assert catalog.english_only_problems(root) == ([f"x.md:2{LETTER}"] if EDGES[code] else [])
```

**1c** `ops/tests/test_contribute.py`, replacing the function at :357-366:
```python
def test_the_georgian_check_is_the_check_of_harness_validate():
    from harness.catalog import GEORGIAN as VALIDATE

    spec = importlib.util.spec_from_file_location("contribute", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    codes = [*range(0x10A0, 0x1100), *range(0x1C90, 0x1CC0), *range(0x2D00, 0x2D30)]
    outside = [0x109F, 0x1100, 0x1C8F, 0x1CC0, 0x2CFF, 0x2D30]
    assert all(module.GEORGIAN.search(chr(c)) for c in codes)
    assert [c for c in codes + outside if bool(module.GEORGIAN.search(chr(c))) != bool(VALIDATE.search(chr(c)))] == []
    assert not any(module.GEORGIAN.search(chr(c)) for c in outside)
    assert not module.GEORGIAN.search("plain English, 2026-10-29")
```
**2a** `$S/scripts/tests/test_skill_example.py`, in place of the last line of `test_the_configs_name_every_role_and_only_files_the_example_has` (:97, `assert sorted(f for f in named if not (f.startswith("_") and (EXAMPLE / f[1:]).is_file())) == []`):
```python
    assert {name: agent["settings"] for name, agent in every.items()} == {
        name: f"_control/{name.split('/')[-1]}-settings.json" for name in every
    }  # K4: each settings file sits under `_control/`, out of every role's reach
    shipped = {f: re.sub(r"^_(?:control/)?", "", f) for f in named}  # `_control/<x>` and `_<x>` ship as example/<x>
    assert sorted(f for f, s in shipped.items() if f == s or not (EXAMPLE / s).is_file()) == []
```

**2b** `$S/scripts/tests/test_docs.py`, in place of the lines `run = tmp_path / "run"`, `run.mkdir()`, `for agent in config["agents"].values():` (:126-128):
```python
    run = tmp_path / "run"
    (run / "_control").mkdir(parents=True)  # K4: each settings value is `_control/<role>-settings.json`
    for agent in config["agents"].values():
```

**2c** `$S/scripts/tests/test_preflight.py`, the comment above `test_the_example_launch_table_has_a_row_for_every_agent_of_the_example_configs` (:660-662) becomes:
```python
# V5 (K2, index row 4): a role cell is an agent name as `_agents.json` writes it (`<project>/planner`). Since Task 11
# the example's settings values sit under `_control/` (K4), so the example's table and configs, `<project>` = demo,
# pass `check_launch` with no problem at all.
```

and the test's last two lines (:677-678, `problems = ...` and the `assert [p for p in problems if not re.fullmatch(...)]`) become one:
```python
    assert result.status == "PASS", result.detail
```

**3a** `$S/scripts/tests/test_skill_md.py`, replacing the last line of `MOVED` (:34):
```python
    "choosing-roles-and-skills.md": "Choosing roles and skills",
    "watching.md": "Watcher, monitor and collector",
```

**3b** `$S/scripts/tests/test_skill_md.py`, after the file's last test:
```python
def test_skill_md_names_the_manager_tools_and_the_third_watcher_and_its_page_holds_the_rest():
    # Task 11 (K9, K10): the duty list, the monitor and the collector by command; the watcher's third version (the
    # hand-over at a unit's end past handoff_at, orders acknowledged by a line, the registry, exit 4 without a changed
    # brief); the manager's own measures. The v2 rule that a changed brief exits 4 is gone; the page keeps the rest.
    skill = " ".join((SKILL / "SKILL.md").read_text(encoding="utf-8").split())
    needed = (
        "`python3 -I scripts/duty_list.py extract <plan-dir> --out <run-dir>/_control/duties.md`",
        "`python3 -I scripts/monitor_records.py watch <run-dir>`",
        "`scripts/collect_run.py` (a dry run, then `--apply --yes <digest>`",
        "`handoff_at` (150000)",
        "`_control/registry.json`",
        "`ACK <msg_id>`",
        "`python3 -I scripts/watch_agents.py --order <agent> <text> <agents.json>`",
        "exits 4 only when a settings file or the extra prompt file changed or a brief was removed",
        "a changed brief is reloaded",
        "`scripts/manager/measure_manager.py`",
    )
    assert [x for x in needed if x not in skill] == []
    assert "(a settings file, a brief) changed" not in skill and "Pause the watcher" not in skill
    page = " ".join((REFERENCES / "watching.md").read_text(encoding="utf-8").split())
    kept = ("exit 3 when", "exit 4 when", "`ack_resends`", "`--apply --yes <digest>`", "three runs applied with a yes")
    assert [x for x in kept if x not in page] == []
```

**5d** `ops/tests/test_bootstrap_steps.py`, after its last test (the two imports of Step 5.1 come with it):
```python
def test_the_template_readme_and_new_project_name_every_step_of_the_bootstrap() -> None:
    """Task 11 (lesson 00:42): the texts that say what `ops/bootstrap.py` sets up name all eleven of its steps, each as
    whole words: in `docs/template/PROJECTS.md` and in the docstring of `ops/new-project.py`, read without backticks, the
    span from `ops/bootstrap.py:` to the first `--no-setup` after it."""
    steps = ("uv", "the workspace", "just", "the git hooks", "the plugins", "the language servers", "the sandbox",
             "the first code graph", "graphify's skill", "the user-level pipeline skill", "harness doctor")  # fmt: skip
    texts = {
        "README": (REPO / "docs" / "template" / "README.md").read_text(encoding="utf-8"),
        "new-project": ast.get_docstring(ast.parse((REPO / "ops" / "new-project.py").read_text(encoding="utf-8"))),
    }
    flat = {name: " ".join(text.replace("`", "").split()) for name, text in texts.items()}
    assert {name: text.count("ops/bootstrap.py:") for name, text in flat.items()} == {"README": 1, "new-project": 1}
    spans = {name: text.split("ops/bootstrap.py:", 1)[1].split("--no-setup", 1)[0] for name, text in flat.items()}
    missing = {name: [s for s in steps if not re.search(rf"\b{re.escape(s)}\b", span)] for name, span in spans.items()}
    assert missing == {"README": [], "new-project": []}
```

**7f** `ops/tests/test_new_project_omit.py` (Step 7.5). The module docstring, in place of :1-2:
```python
"""The template's own plans stay in the template (C4): ops/new-project.py copies every tracked file except the
`omit:` prefixes of docs/template/variables.yaml, and those include the template-core and manager-build plans, active
or completed."""
```
The two constants, right below `DONE = ...` (:15):
```python
MANAGER_PLAN = "docs/exec-plans/done/manager-build/"  # the plan of the manager-build run (release 1.5.0)
MANAGER_DONE = "docs/exec-plans/done/manager-build/"
```
The two tests, after the file's last test:
```python
def test_the_omit_list_adds_both_manager_build_plan_folders():
    spec = yaml.safe_load((REPO / "docs" / "template" / "variables.yaml").read_text(encoding="utf-8"))
    assert MANAGER_PLAN in spec["omit"] and MANAGER_DONE in spec["omit"]


def test_a_project_gets_none_of_the_manager_build_plan_nor_its_plans_line(tmp_path: Path):
    root, target = template(tmp_path), tmp_path / "demo"
    for rel in (f"{MANAGER_PLAN}00-index.md", f"{MANAGER_PLAN}task-11.md", f"{MANAGER_DONE}00-index.md"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("# Plan\n", encoding="utf-8")
    readme = ("# Active plans\n\n## Plans\n\n"
              "- [manager-build](manager-build/00-index.md): the template's manager-build run, eleven tasks to release"
              " 1.5.0\n- [demo](demo/00-index.md): a plan of the project\n")  # fmt: skip
    (root / "docs/exec-plans/active/README.md").write_text(readme, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    command = [sys.executable, str(root / "ops" / "new-project.py"), str(target), "--no-setup"]
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    assert not (target / MANAGER_PLAN).exists() and not (target / MANAGER_DONE).exists()
    assert (target / "docs/exec-plans/active/demo/00-index.md").is_file()
    assert (target / "docs/exec-plans/active/README.md").read_text(encoding="utf-8") == (
        "# Active plans\n\n## Plans\n\n- [demo](demo/00-index.md): a plan of the project\n"
    )
```

## Texts in full
Each block is copied verbatim; its lines are the file's lines.

**3c** `$S/SKILL.md`, replacing :83-95 (the watcher's bullet) with two bullets:
```markdown
- The supervisor stops an agent's process after about an hour idle and unattached; a background shell waiter is not
  listed as work that keeps it alive. Run `python3 -I scripts/watch_agents.py <agents.json>` in the background from
  the main session, one watcher per pipeline (config fields in `scripts/README.md`, a config in
  `example/agents.json`), after one round of `--check`. It starts the fresh session at a hand-over note, orders the
  hand-over at a unit's end past `handoff_at` (150000), revives stopped agents, keeps the sessions in
  `_control/registry.json`, and resends each order until the record holds its `ACK <msg_id>` line. It exits 4 only
  when a settings file or the extra prompt file changed or a brief was removed: a changed brief is reloaded. The
  rest: [Watcher, monitor and collector](references/watching.md).
- The manager's commands: `python3 -I scripts/duty_list.py extract <plan-dir> --out <run-dir>/_control/duties.md`
  before the launch; `python3 -I scripts/monitor_records.py watch <run-dir>` in the background (a `WAKE` line per
  event; answer, then re-arm); after the run, `scripts/collect_run.py` (a dry run, then `--apply --yes <digest>`).
```

**3d** `$S/SKILL.md`, replacing :101-103 (`## Changing orders`, the second bullet):
```markdown
- Anything else: a message from the main session (bypass mode) to an agent in auto mode is held and expires. Use
  `python3 -I scripts/watch_agents.py --order <agent> <text> <agents.json>`: the running watcher delivers it by stop
  and resume. With no watcher: `claude stop <id>`, then `claude --resume <sessionId> --bg "<new orders>"` from the
  same directory with the same flags (the conversation is kept).
```

**3e** `$S/SKILL.md`, replacing :115-116 (the `[Measuring the pipeline]` entry):
```markdown
- [Measuring the pipeline](references/measuring.md): the read-only reports (records, gates, cost, budget, lessons,
  replay), what they measured, and the jobs' disk; after every run, `scripts/manager/measure_manager.py` measures the
  manager itself.
```

**3f** `$S/SKILL.md`, appended after :121 (the last entry of `## References`):
```markdown
- [Watcher, monitor and collector](references/watching.md): the watcher's rounds, orders, registry and exit codes; the
  monitor, the duty list, the collector.
```

**3g** `$S/references/watching.md`, the whole file:
```markdown
# Watcher, monitor and collector
The main session's long-running and end-of-run tools besides the waiters. Each script's usage, options and files are
on its page under `scripts/docs/`, indexed in `scripts/README.md`.

### The watcher, `scripts/watch_agents.py` (version 3)
- Each round: a fresh session when a hand-over note appears, if the note's mtime lies within its session's transcript
  plus five minutes; builder and verifier switched at the config's `milestones`; a permission prompt cancelled after
  `permission_wait`; a stopped agent continued with a nudge, at most `nudges` times (6).
- Hand-over: at a unit's end (a new line 1 in the agent's record) once its last call passes `handoff_at` (150000),
  never in the middle of a unit; past the `cap` (200000) at once.
- Orders: the watcher's (`handoff`, `unit-end`, `reload`) and the manager's (`--order <agent> <text>`) reach a session
  by a stop and a resume whose prompt ends with ``Order <msg_id>: append the line `ACK <msg_id>` to <record> before
  anything else.``; without that line the order is resent after `ack_wait` seconds, at most `ack_resends` times, and
  then the watcher returns.
- Registry: `_control/registry.json`, written whole at the end of every round: per agent its lane, settings, record,
  unit, state, session ids, context, calls, cost, revivals and open orders. A restarted watcher reads it and keeps the
  orders, the revivals and the session ids.
- Returns: exit 0 on an event (an agent failed or blocked, two live copies of one agent, an order with no ACK line
  after its resends, every STATUS final); exit 3 when a session passes its `budget` (the session is not stopped:
  decide, then restart the watcher); exit 4 when a settings file or the extra prompt file changed or a brief was
  removed. A changed brief is reloaded with a `reload` order, a changed config at the next round (an invalid one is
  kept out, with a log line).
- Give the planner the builder's final status, so it stays revivable while the builder may still report wrong steps.
  A pipeline that runs an older copy of the watcher moves at its next restart: `scripts/migrate_agents_json.py
  <run-dir>` writes its `_agents-v2.json`.

### The duty list and the record monitor
- `scripts/duty_list.py extract <plan-dir> --out <run-dir>/_control/duties.md`, after the index and before the launch:
  every merge the task table implies, every marker the prose names, every `Request point:` line of a task file and
  the judge's approval, each with the task it blocks; `tick` marks one duty done with its time and evidence.
- `scripts/monitor_records.py watch <run-dir>`, the manager's background command: it exits 0 with one `WAKE` line
  per new event (a `SANDBOX:`, `COPY-REQUEST:`, `CHECKOUT-REQUEST:` or `FF-REQUEST:` line, a request open past the
  bound, a second or stalled claim, a due duty, a `VERDICT:` line, a failed merge check) and exits 1 after `--hours`.
  It answers no request: `answer` writes the answer line into the requester's file; re-arm it with the same command.

### The collector
- `scripts/collect_run.py RUN_DIR --repo DIR --plan PATH --kept PATH`, after the run, never by a role: a dry run lists
  what goes and what each deletion loses, and refuses while the record is not saved (final record lines, each lesson
  marked, the done commits in the main branch, every Deferred item of the plan a tracker row). `--apply --yes
  <digest>` removes on the owner's yes for that list; after three runs applied with a yes, `--apply` alone.
```

**3h** `$S/references/measuring.md`, replacing lines 2-3:
```markdown
Read-only scripts for the main session (usage and options on each script's page under `scripts/docs/`, indexed in
`scripts/README.md`); none runs a model, and they may run while the pipeline works.
```

**4a** `docs/exec-plans/tech-debt-tracker.md`: the lines of TD-002, TD-008, TD-010 and TD-011, each in place of
the row with its id, then TD-013 to TD-022, after TD-012:
```markdown
| TD-002 | evals | no regression case for `judge` | verdict changes go unnoticed | harness maintainers | medium | manager-build Deferred (00-index.md, task-08.md): a verdict has no code-graded form; a case needs a recorded judge output as its baseline, which `evals/nightly.sh` records |
| TD-008 | docs | the pipeline skill's `scripts/README.md` is 18,977 bytes with a section per script, over the 12 KB folder-README rule; the size check reads `docs/` only | the rule is not enforced on the skill; the split changes the skill's tests | harness maintainers | medium | closed: manager-build Task 10 — `scripts/README.md` is an index under 12,000 bytes; each script's usage and options are on its page under `scripts/docs/`; `scripts/tests/test_docs.py` holds both |
| TD-010 | ops | no garbage collector when a run is done (owner, 2026-10-29: check that nothing was missed, then delete): its worktrees, `scratch/`, the sessions' job outputs and result copies stay on the disk after the records are saved (owner, 2026-10-29: delete what is saved) | the template-core run left five worktrees, 14 GB of job outputs and 17.7 GB of scratch | harness maintainers | medium | closed: manager-build Task 6 — `scripts/collect_run.py` removes a finished run's worktrees, branches, `scratch/` and job folders only after its save check, on the owner's `--yes <digest>` for three runs, then by the standing rule |
| TD-011 | evals | the llm grader runs `claude -p` with the user's setting sources, so the owner's `~/.claude/CLAUDE.md` language rule reaches it (reader-quotes-locations, 2026-10-29 15:24 UTC: the dimension texts came back translated) | scores unaffected so far; a grader that follows user rules is not reproducible on another machine | harness maintainers | low | closed: manager-build Task 8 — the llm grader runs `claude -p` with `--setting-sources local` and refuses a grade holding a letter of a refused block; `test_evals_llm.py` pins both |
| TD-013 | pipeline | live behaviour the stub tests stand in for | a changed `claude` output form or listing key breaks the watcher or the collector silently | main session | medium | manager-build Deferred: "10.9, the live part" (task-01), "A live check of the `--bg` output forms the watcher parses (`claude stop <id>`, `a copy as <id>`, `claude attach <id>` … `opens the original`)" (task-02), "10.5 and 10.8 live, on the next run" (task-02), "A probe against a live run folder with the real bwrap" (task-04), "The live 10.6" (task-05), "The live `cwd` key of `claude agents --json --all` rows" (task-06) — the next run's first launch, status answer and collection check each one live |
| TD-014 | pipeline | steps the scripts leave to the manager or to a weaker match | a step by hand at each run; nothing is lost | harness maintainers | low | manager-build Deferred: "`--session-id` at launch (Departure 3)." (task-02), "A brief changed while a fresh launch's stop runs" (task-02), "The monitor answering a request itself (need 4 allows it)" (task-03), "Point duties (`COPY-REQUEST`, `CHECKOUT-REQUEST`, `FF-REQUEST` points) ticked by `answer`" (task-03), "The pre-flight running Task 1's `catalogue.py briefs` (Task 4's contract, 668dfe5)" (00-index), "The pre-flight does not run Task 1's `catalogue.py briefs`" (task-04), "Job folders matched by the registry's session ids" (task-06), "A sandbox marker for the collector" (task-06), "a script for 10.3 and 10.4" (task-07) — a later run adds each with its own test; the item's text says why it waits |
| TD-015 | measurement | measurements and vault pages that are the main session's | the rules they would back stay unmeasured | main session | low | manager-build Deferred: "8.3.17 per-plugin start-up cost" (00-index), "8.3.17 (the start-up cost per plugin in tokens)" (task-01), "The graph over the vault (question 12)" (00-index), "7.5 the graph over the vault" (task-07), "The vault measurement page with the request and answer times (`report`'s table)" (task-03), "the vault pages of 8.3.13" (task-07) — the main session writes each page in the owner's vault after this run |
| TD-016 | runs | runs and a schedule that are the owner's to start | the A/B cost and portability stay unmeasured; the session evals run by hand | owner | low | manager-build Deferred: "The A/B cost measurement, the sync of the owner's other project and the portability runs" (00-index), "The owner's cron line for `evals/nightly.sh` on this machine" (task-08) — the owner's call |
| TD-017 | evals | the access probe's case left with the `critique` stage | the probe has no regression case | harness maintainers | low | manager-build Deferred: "The access probe's port to the `attack` stage" (task-08) — a new fixture and a baseline from a live run |
| TD-018 | bootstrap | graphify's project-scoped hook and `CLAUDE_CONFIG_DIR` | graph queries need the user-level skill; a moved config folder is not followed | harness maintainers | low | manager-build Deferred: "graphify's PreToolUse hook, the second half of TD-007" (task-09), "`CLAUDE_CONFIG_DIR`. graphify honours it (`install.py:132-133`), but bootstrap looks for both skills under `~/.claude/skills/` only" (task-09) — a later run decides on the hook, and on the variable once Claude Code's handling is checked |
| TD-019 | docs | the harness package's quality score; three modules missing from the module map | an old score; three missing rows | harness maintainers | low | manager-build Deferred: "The score of `packages/harness` in `docs/quality/QUALITY_SCORE.md`. Line 6 keeps 2" (task-09), "The module map has no row for `gitcall.py`, `leftovers.py` or `pause.py`, because the table moved verbatim (copy tasks stay thin, `lessons.md` Read first 8)" (task-09) — the release review scores the package; the next edit of the map adds the rows |
| TD-020 | ops | the vault script's test checks one refused block | a letter of U+1C90-U+1CBF or U+2D00-U+2D2F in a file `ops/new-vault.py` writes passes it | harness maintainers | low | manager-build Deferred: "The one-block pattern of `ops/tests/test_new_vault.py:37`" (task-11) — the test takes the three blocks when next edited |
| TD-021 | pipeline | prices `usage_report.py` leaves out | long Haiku prompts, fast mode and `inference_geo` priced low; an old price table not flagged | harness maintainers | low | manager-build Deferred: "Haiku 5.5's long-prompt prices (over 100,000 prompt tokens, counting input, cache reads and cache writes; each request priced on its own)" (task-10), "Fast mode (Opus 5.5 $8 / $40) and `inference_geo: "us"` (1.1x)" (task-10), "A warning when `PRICES_AS_OF` is older than a set number of days" (task-10) — one `price(model, usage)` for the watcher and the report; fast mode once a transcript records the field; the warning with a clock the tests control |
| TD-022 | plan | plan Deferred items that are not debt | none | harness maintainers | low | closed: manager-build Tasks 1-11 — carried or settled in the run: "Not deferred, named for the index's Coverage rows (C14)" (task-01: Task 1), "Not deferred (C14)" (task-01: Task 1), "10.15" (task-01: Tasks 2 and 4), "10.17" (task-01: Task 7), "The configs' settings paths under `_control/`" (task-01: Task 11), "`docs/roles/VERSION` 1.14.0 and its `docs/roles/CHANGELOG.md` heading" (task-01: Task 11), "A check that `docs/roles/catalogue.md` equals `catalogue.py table`" (task-01: not added), "The registry fields beyond need 1 that Task 5's surface may want (for example the budget left per agent)" (task-02: Task 5 listed none), "The owner's surface showing the monitor's alarms" (task-03: Task 5), "The `SKILL.md` lines and the decision pages" (task-03: Task 11), "`sim_bwrap.py` gains only the `~/` expansion" (task-04: settled), "The usage reading itself" (task-04: the manager's), "No `SKILL.md` line for `surface.py`" (task-05: settled), "The owner's own phrase file is the owner's, outside the template (D1)" (task-05: the owner's), "The prices of `usage_report.py` (8.3.14) are row 10's; the surface keeps no price table (Departure 4), so a price fixed there reaches the run line" (task-05: Task 10), "the 30,000 limit enforced at start-up" (task-07: settled) |
```

**5a** `docs/template/PROJECTS.md`, replacing :17-21:
```markdown
   sets the project up on this machine with `ops/bootstrap.py`: uv, the workspace, `just`, the git hooks, the plugins,
   the language servers, the sandbox, the first code graph, graphify's skill, the user-level pipeline skill and
   `harness doctor` (each step in its docstring; `docs/decisions/0009-a-checkout-sets-itself-up.md`). `--no-setup`
   copies only. `--container` makes `<target-dir>` the project's own folder: the repository goes to
   `<target-dir>/<repo_name>/`, beside it `runs/` (marked `.harness-runs`: the runs root, `docs/roles/RUNS.md`),
   `experiments/` (copies made for trials) and `docs/handoff/` (the manager's hand-over notes); a `<target-dir>` that
   holds another checkout is refused, as that checkout would take the same runs root. Without it the
```

**5b** `ops/new-project.py`, replacing the docstring's line :4:
```text
uv, the workspace, just, the git hooks, the plugins, the language servers, the sandbox, the first code graph, graphify's
skill, the user-level pipeline skill and harness doctor). Usage: ops/new-project.py <target-dir> name=value ...
[--no-setup]
```

**5c** `docs/quality/LEARNING.md`, replacing :18-19 (item 6):
```markdown
6. Gate. `.github/workflows/evals.yml` runs on every pull request that touches `.claude/`, `plugins/`, `templates/`,
   `schemas/`, `docs/roles/` or `evals/`: `harness version-check` and the plugin evals. `.github/workflows/ci.yml` runs
   the tests and the regression suite graded on its recorded baselines, with no session (threshold 1.0), on every push
   and pull request; the session cases run nightly on the owner's machine (`evals/nightly.sh`).
```

**6a** `wiki/decisions/control-plane-in-the-skill.md`, the whole file:
```markdown
---
title: The control plane lives in the skill
type: decision
status: draft
updated: 2026-10-30
audience: [all]
decided: 2026-10-29
by: owner
why: the pipeline skill starts and watches the roles, so the files that follow them are written by its scripts in the run folder, out of the roles' reach
would_change_if: a run in which the manager needed the harness's state or status line to follow a skill run, or a file under `_control/` lost an order or a session
decision_status: decided
scope: global
---
# The control plane lives in the skill

The registry, the orders and the record monitor of a pipeline run are files in the run folder, written by the pipeline
skill's scripts with the standard library only: `watch_agents.py` (version 3) keeps `_control/registry.json`, with each
session matched by the id recorded at its launch, and appends each `--order` to `_control/orders.jsonl`;
`monitor_records.py` keeps `_control/monitor.json`; `scripts/manager/surface.py` renders the owner's surface from the
registry. The harness's `state.json`, `harness poll` and `statusline.py` are not extended to skill runs. `_control/`
sits behind the run folder's deny, so the roles stay blind to these files. This is the owner's answer (a) to question 10
of the manager spec (2026-10-29); answer (b), the harness's state, fell with question 1, which made the skill's main
session the manager.

## Record and source
- [The watcher](../../.claude/skills/running-specagent-pipelines/scripts/docs/watch_agents.md)
- [Watching a run](../../.claude/skills/running-specagent-pipelines/references/watching.md)
- [The record monitor](../../.claude/skills/running-specagent-pipelines/scripts/docs/monitor_records.md)
- [The manager is the pipeline skill's main session](the-manager-is-the-pipeline-skill-main-session.md)
```
`wiki/decisions/control-plane-in-the-skill.summary.md`, the whole file:
```markdown
Decision (owner, 2026-10-29): the control plane lives in the skill.
The registry, the orders and the record monitor are files under the run folder's _control/, written by the skill's scripts.
The harness's state.json, harness poll and statusline.py are not extended to skill runs.
The roles stay blind to these files: _control/ sits behind the run folder's deny.
```

**6b** `wiki/decisions/monitor-answers-no-request.md`, the whole file:
```markdown
---
title: The record monitor answers no request
type: decision
status: draft
updated: 2026-10-30
audience: [all]
decided: 2026-10-29
by: owner
why: every answer to a request changes a worktree or the sandbox, and the manager's guards cover only the commands the manager runs
would_change_if: the guards come to cover the monitor's own commands, and a run shows requests waiting on the manager long enough to cost a role's session
decision_status: decided
scope: global
---
# The record monitor answers no request

`monitor_records.py watch <run-dir>` reads the run's records, finds the request lines (`SANDBOX:`, `COPY-REQUEST:`,
`CHECKOUT-REQUEST:` and `FF-REQUEST:`), the claims, the `VERDICT:` lines and the `Merged:` lines, and wakes the
manager; it answers no request itself. The manager does what a request asks, answers it with
`monitor_records.py answer <run-dir> <request-id> <text>` (`--refuse` for a refusal) and re-arms the monitor with the
same `watch` command. Every answer changes a worktree or the sandbox, and the manager's four guards cover only the
commands the manager runs (manager spec 5.5, need 4).

## Record and source
- [The record monitor](../../.claude/skills/running-specagent-pipelines/scripts/docs/monitor_records.md)
- [The manager runs without the sandbox, with four guards](the-manager-runs-without-the-sandbox.md)
```
`wiki/decisions/monitor-answers-no-request.summary.md`, the whole file:
```markdown
Decision (owner, 2026-10-29): the record monitor answers no request.
monitor_records.py finds the request lines, claims, verdicts and Merged: lines and wakes the manager.
The manager does what a request asks and answers with monitor_records.py answer, then re-arms the monitor.
Every answer changes a worktree or the sandbox, and the manager's guards cover only the manager's own commands.
```

**6c** `wiki/decisions/request-answer-lines.md`, the whole file:
```markdown
---
title: A request is answered below it, in the requester's file
type: decision
status: draft
updated: 2026-10-30
audience: [all]
decided: 2026-10-29
by: owner
why: a role waits on its own file, so the answer lands there in one form a script can find, with its time at a fixed place
would_change_if: a run in which a role missed an answer written in this form, or two open requests of one kind were closed in the wrong order
decision_status: decided
scope: global
---
# A request is answered below it, in the requester's file

A request line is answered in the requester's own file, below it, by one line: `SUPPLIED:` for a `SANDBOX:` request,
`COPIED:` for `COPY-REQUEST:`, `CHECKED-OUT:` for `CHECKOUT-REQUEST:`, `FF-DONE:` for `FF-REQUEST:`, or
`REFUSED: <KIND> — <why>`, each ending with its `date -u` time; an answer closes the oldest open request of its kind
(`check_formats.py`'s `REQUEST_KINDS`; manager spec 5.4 and 8.3.3, acceptance check 10.7). The template-core run
answered a `COPY-REQUEST:` with `COPIED:` in the requester's file (its `build-log-b.md:22` and `:24`), with the time
inside the text rather than at a fixed place, so no script could read it; `monitor_records.py answer` now writes the
line.

## Record and source
- [The record monitor](../../.claude/skills/running-specagent-pipelines/scripts/docs/monitor_records.md)
- [The format checks](../../.claude/skills/running-specagent-pipelines/scripts/docs/check_formats.md)
- [The record monitor answers no request](monitor-answers-no-request.md)
```
`wiki/decisions/request-answer-lines.summary.md`, the whole file:
```markdown
Decision (owner, 2026-10-29): a request is answered below it, in the requester's file.
SUPPLIED:, COPIED:, CHECKED-OUT: or FF-DONE: answers SANDBOX:, COPY-REQUEST:, CHECKOUT-REQUEST: or FF-REQUEST:.
A refusal is REFUSED: <KIND> — <why>; each answer ends with its date -u time.
An answer closes the oldest open request of its kind.
```

**6d** `wiki/decisions/duty-list-from-the-plan.md`, the whole file:
```markdown
---
title: The manager's duties come from the plan
type: decision
status: draft
updated: 2026-10-30
audience: [all]
decided: 2026-10-29
by: owner
why: the merges, markers, request points and the judge's approval of a run are written in its plan, and a duty kept only in the manager's context is lost at a hand-over
would_change_if: a run in which a duty the plan implied was missing from the list, or a duty was ticked without its evidence
decision_status: decided
scope: global
---
# The manager's duties come from the plan

After the plan's index is written and before the launch, the manager runs `duty_list.py extract <plan-dir> --out
<run-dir>/_control/duties.md`: every merge the task table implies, every marker the prose names, every
`Request point:` line of a task file and the judge's approval, each with the task it blocks; a second run appends only
the new duties. The manager reads the list at every wake-up, and `duty_list.py tick` writes each tick's `date -u` time
and its evidence; the record monitor ticks a merge on a `Merged:` line whose sha `git merge-base --is-ancestor`
confirms (manager spec 5.1.2 and 8.2.3, acceptance check 10.11).

## Record and source
- [The duty list](../../.claude/skills/running-specagent-pipelines/scripts/docs/duty_list.md)
- [The record monitor](../../.claude/skills/running-specagent-pipelines/scripts/docs/monitor_records.md)
```
`wiki/decisions/duty-list-from-the-plan.summary.md`, the whole file:
```markdown
Decision (owner, 2026-10-29): the manager's duties come from the plan.
duty_list.py extract writes _control/duties.md after the index and before the launch: merges, markers, request points, the judge.
The manager reads the list at every wake-up; duty_list.py tick writes each tick's time and evidence.
The record monitor ticks a merge on a Merged: line whose sha git merge-base --is-ancestor confirms.
```

**6e** `wiki/decisions/collector-yes-then-standing-rule.md`, the whole file:
```markdown
---
title: The collector deletes on the owner's yes for three runs, then by a standing rule
type: decision
status: draft
updated: 2026-10-30
audience: [all]
decided: 2026-10-29
by: owner
why: a deletion cannot be undone, so the owner approves the exact list until three runs have shown that the list is right
would_change_if: a run in which the collector's list held something the owner would have kept, which brings the yes back
decision_status: decided
scope: global
---
# The collector deletes on the owner's yes for three runs, then by a standing rule

`collect_run.py` lists a finished run's leftovers (its worktrees and branches, `scratch/`, the sessions' job outputs
and result copies) in a dry run that prints the list's digest. For the first three runs it deletes only on the owner's
yes for that exact list, `--apply --yes <digest>`; once its history file holds three runs applied with a yes,
`--apply` alone deletes by the standing rule, and the owner reads `collected.md` in the run folder afterwards. This is
the owner's answer to question 4 of the manager spec, "4 (a) for three runs, then (b)" (2026-10-29; spec 5.9.4).

## Record and source
- [The collector](../../.claude/skills/running-specagent-pipelines/scripts/docs/collect_run.md)
- [A run is collected only after its record is checked as saved](collector-save-check.md)
```
`wiki/decisions/collector-yes-then-standing-rule.summary.md`, the whole file:
```markdown
Decision (owner, 2026-10-29): the collector deletes on the owner's yes for three runs, then by a standing rule.
collect_run.py's dry run lists a finished run's leftovers with the list's digest.
For three runs it deletes only with --apply --yes <digest>, the owner's yes for that exact list.
Then --apply alone deletes, and the owner reads collected.md in the run folder afterwards.
```

**6f** `wiki/decisions/collector-save-check.md`, the whole file:
```markdown
---
title: A run is collected only after its record is checked as saved
type: decision
status: draft
updated: 2026-10-30
audience: [all]
decided: 2026-10-29
by: owner
why: what the collector deletes is gone, so it first proves that the run's records, lessons, done commits and Deferred items reached the main branch, the skill or the tracker
would_change_if: a collected run whose lesson, done commit or Deferred item turned out lost, or a check that refused a run whose record was saved
decision_status: decided
scope: global
---
# A run is collected only after its record is checked as saved

Before it deletes anything, `collect_run.py` checks the run's record: the final record lines; each lesson of the run
marked `(skill: <sha>)` with that commit in the main branch, or `(skill: none)` (a script cannot judge whether a
lesson's meaning reached the skill, so the manager marks each lesson and the collector checks the marks); every build
log's done commit and each `--final` commit in the main branch; every Deferred item of the plan, read outside fenced
code, in a tracker row; and nothing unsaved in what goes. A failed check refuses the run and names what is missing
(manager spec 5.9.4 and 8.2.13; tracker TD-010).

## Record and source
- [The collector](../../.claude/skills/running-specagent-pipelines/scripts/docs/collect_run.md)
- [The collector's yes, then the standing rule](collector-yes-then-standing-rule.md)
```
`wiki/decisions/collector-save-check.summary.md`, the whole file:
```markdown
Decision (owner, 2026-10-29): a run is collected only after its record is checked as saved.
collect_run.py checks the final record lines, each lesson's (skill: <sha>) or (skill: none) mark, the done commits.
Every --final commit must be in the main branch, and every Deferred item of the plan in a tracker row.
A failed check refuses the run and names what is missing; nothing unsaved is deleted.
```

**6g** `wiki/decisions/code-cases-gate-every-push-sessions-run-nightly.md`, the whole file:
```markdown
---
title: Code cases gate every push, session cases run nightly
type: decision
status: draft
updated: 2026-10-30
audience: [all]
decided: 2026-10-29
by: owner
why: a lesson class comes back unseen unless a case fails at push time, and a session case costs money and needs a key that GitHub Actions does not hold
would_change_if: a regression that the gate passed and a nightly session case caught first, or nightly runs that cost more than the cap
decision_status: decided
scope: global
---
# Code cases gate every push, session cases run nightly

`.github/workflows/ci.yml` runs `uv run harness eval --suite regression --baseline --threshold 1.0` on every push and
pull request: the fourteen code cases (`session: false`, graded by the thirteen checks of
`evals/graders/pipeline_plan.py`) and every session case's code graders on its recorded baseline, with no session and
no key. The session cases run nightly on the owner's machine (`evals/nightly.sh`), at threshold 1.0, under a cost cap
that counts each started case at its worst; `evals.yml` keeps `instruction-version` and `plugin-evals`, and its
session job is gone. Each lesson class of 2026-10-29 has its guard: `pipeline-job-timeouts` (the wrapper timeout),
`pipeline-handoff-pointers` (a hand-over note with pointers instead of facts), `pipeline-ancestor-deny` (a sandbox deny
on an ancestor), the critic case's recorded baseline (the grader regex) and the lint that fails a suite naming a stage
that no longer exists (the stale case); `pipeline-waiters` checks the waiters (acceptance check 10.19).
`access-probe-critic` is removed, not ported, since its `critique` stage is gone (tracker TD-017). Graders are written
from recorded outputs (`evals/README.md`); the llm grader runs with `--setting-sources local` and refuses dimensions
that are not in English (TD-011).

This page supersedes these lines of ADR-0028, which stay as history: :17 and :104 (the probe left for later), :40 and
:52 (ten code cases, graded by `--no-sessions`), :45 (nine checks), :47 (standard library only: the job-timeouts check
imports `harness.evals`), :70 (the full suite at threshold 0.9, run by the main session) and :78 (the gate named as
`--no-sessions`).

## Record and source
- Task 8 of the manager-build run, commit baf3590: its Departures 2-5 and the four cases above
- [ADR-0028 Pipeline evals](../../docs/decisions/0028-pipeline-evals.md)
- [The evals](../../evals/README.md)
```
`wiki/decisions/code-cases-gate-every-push-sessions-run-nightly.summary.md`, the whole file:
```markdown
Decision (owner, 2026-10-29): code cases gate every push, session cases run nightly.
ci.yml grades the fourteen code cases and every session case's code graders on its recorded baseline, at threshold 1.0.
The session cases run nightly on the owner's machine (evals/nightly.sh) at 1.0, under a worst-case cost cap.
Each lesson class of 2026-10-29 has a case or a lint; access-probe-critic is removed. Supersedes ADR-0028's lines.
```

**6h** `wiki/decisions/skill-script-pages.md`, the whole file:
```markdown
---
title: The skill's script docs are one page per script, the README an index
type: decision
status: draft
updated: 2026-10-30
audience: [all]
decided: 2026-10-29
by: owner
why: one README with a section per script grew past the 12 KB rule for a folder README, and a page per script is read alone when a step needs it
would_change_if: a script page that drifts from its script's --help, or the README over 12,000 bytes again
decision_status: decided
scope: global
---
# The skill's script docs are one page per script, the README an index

Each script of the pipeline skill has its page, `scripts/docs/<stem>.md`, with its usage, options and files;
`scripts/README.md` holds the index line of each page, the config fields and the tests, at most 12,000 bytes, and a new
script adds its page and its line. `scripts/tests/test_docs.py` keeps both. The README held a section per script,
19,156 bytes, when the manager-build run began (tracker TD-008; manager spec 8.3.9).

## Record and source
- [The scripts' index](../../.claude/skills/running-specagent-pipelines/scripts/README.md)
- Task 10 of the manager-build run, commit 129a9d5
```
`wiki/decisions/skill-script-pages.summary.md`, the whole file:
```markdown
Decision (owner, 2026-10-29): the skill's script docs are one page per script, the README an index.
Each script's usage, options and files live in scripts/docs/<stem>.md.
scripts/README.md holds the index lines, the config fields and the tests, at most 12,000 bytes.
A new script adds its page and its index line; test_docs.py keeps both.
```

**6i** `wiki/decisions/dated-api-prices.md`, the whole file:
```markdown
---
title: usage_report.py's prices carry their date and source
type: decision
status: draft
updated: 2026-10-30
audience: [all]
decided: 2026-10-29
by: owner
why: list prices change, and a cost figure is worth only as much as the date and page of the prices it was computed from
would_change_if: a report printed with prices the official page no longer lists, or a price table changed without its date
decision_status: decided
scope: global
---
# usage_report.py's prices carry their date and source

`usage_report.py` prices each model family with the list prices of 2026-10-29 from the official pricing page
(`https://platform.claude.com/docs/en/about-claude/pricing`): the prices in `PRICE`, their date in `PRICES_AS_OF` and
the page in `PRICES_URL`, printed on the report's first line, `prices of <date> from <url>` (the header is now line 2).
Each family has one flat tuple; long-prompt prices, fast mode and US-only inference are left out (tracker TD-021).
The rows it replaced held the prices of older models (manager spec 8.3.14).

## Record and source
- [usage_report.py](../../.claude/skills/running-specagent-pipelines/scripts/docs/usage_report.md)
- Task 10 of the manager-build run, commit 129a9d5
```
`wiki/decisions/dated-api-prices.summary.md`, the whole file:
```markdown
Decision (owner, 2026-10-29): usage_report.py's prices carry their date and source.
The list prices of 2026-10-29 from the official pricing page sit in PRICE, with PRICES_AS_OF and PRICES_URL.
The report's first line names the date and the page; the header is line 2.
Long-prompt prices, fast mode and US-only inference are left out (tracker TD-021).
```

**6j** `wiki/decisions/roles-and-sessions-keep-their-names.md`, the whole file:
```markdown
---
title: Roles and sessions keep their names until the owner names them
type: decision
status: draft
updated: 2026-10-30
audience: [all]
decided: 2026-10-29
by: owner
why: the skill, the spec and the template already say roles and sessions, and a rename would touch every file before the owner has chosen a name
would_change_if: the owner names the pipeline's agents
decision_status: decided
scope: global
---
# Roles and sessions keep their names until the owner names them

A pipeline's agents are called roles, and one run of a role a session, as the pipeline skill and the manager spec say.
The owner dropped their earlier name (2026-10-29); until the owner gives another, these words stay and no
file is renamed. The template itself is named SpecAgent (special agent). This is the owner's answer (a) to
question 7 of the manager spec, "(a) until the owner names it" (2026-10-29).

## Record and source
- [The pipeline skill](../../.claude/skills/running-specagent-pipelines/SKILL.md)
- [Pipelines run as SpecAgent sessions from a template skill](pipelines-run-as-specagent-sessions-from-a-template-skill.md)
```
`wiki/decisions/roles-and-sessions-keep-their-names.summary.md`, the whole file:
```markdown
Decision (owner, 2026-10-29): roles and sessions keep their names until the owner names them.
A pipeline's agents are roles, one run of a role a session, as the skill and the manager spec say.
The owner dropped their earlier name; no file is renamed until the owner gives another name.
The template itself is named SpecAgent (special agent).
```

**6k** `wiki/decisions/the-spec-writers-model-is-a-dated-exception.md`, the whole file:
```markdown
---
title: The spec writer's model is a dated exception
type: decision
status: draft
updated: 2026-10-30
audience: [all]
decided: 2026-10-29
by: owner
why: the owner ordered a model for spec writing that the standing rule for launched sessions does not give, and an exception without its date and evidence becomes a silent second rule
would_change_if: the owner's next order for the spec writer, or a measured spec run that shows the standing rule's models write specs as well
decision_status: decided
scope: global
---
# The spec writer's model is a dated exception

The spec writer of a pipeline runs on the model the owner ordered for spec writing on 2026-10-29, which the standing
rule for launched sessions does not include. The order is recorded on the owner's vault page
`decisions/global/models-per-role.md` as a dated exception with its `would_change_if`, not as a new rule, and the
launch table's message, the one place a run names its models, carries it. This is the owner's answer (a) to question 8
of the manager spec (2026-10-29; spec 4.3).

## Record and source
- [The launch table and one yes](the-launch-table-and-one-yes.md)
```
`wiki/decisions/the-spec-writers-model-is-a-dated-exception.summary.md`, the whole file:
```markdown
Decision (owner, 2026-10-29): the spec writer's model is a dated exception.
The spec writer runs on the model the owner ordered for spec writing, outside the standing rule for launched sessions.
The order is recorded on the vault page decisions/global/models-per-role.md with its date and would_change_if.
The launch table's message, the one place a run names its models, carries it.
```

**6l** `wiki/decisions/a-vault-graph-is-measured-before-it-is-built.md`, the whole file:
```markdown
---
title: A graph over the vault is measured before it is built
type: decision
status: draft
updated: 2026-10-30
audience: [all]
decided: 2026-10-29
by: owner
why: the vault held 169 KB of pages when the question was asked, which its index and outline tool may serve without a graph
would_change_if: a measurement that shows queries the vault's `INDEX.md` and `outline.py` answer late or wrong and a graph answers better
decision_status: decided
scope: global
---
# A graph over the vault is measured before it is built

No graph over the owner's vault is built in the manager-build run. The main session first measures what the vault's
queries cost and miss with its `INDEX.md` and `ops/outline.py`, then decides whether a graph pays (tracker TD-015);
the template's code graph of the repository (`bash ops/graph.sh`) is unchanged. This is the owner's answer to question
12 of the manager spec, "measure, then decide" (2026-10-29; spec 7.5).

## Record and source
- [The code graph](the-code-graph-is-generated-layered-and-refreshed-by-hooks.md)
- [The shared knowledge base](the-shared-knowledge-base.md)
```
`wiki/decisions/a-vault-graph-is-measured-before-it-is-built.summary.md`, the whole file:
```markdown
Decision (owner, 2026-10-29): a graph over the vault is measured before it is built.
No vault graph is built in the manager-build run.
The main session measures what INDEX.md and ops/outline.py cost and miss, then decides (tracker TD-015).
The template's code graph of the repository is unchanged.
```

**6m** `wiki/decisions/bootstrap-runs-eleven-steps-in-order.md`, the whole file:
```markdown
---
title: Bootstrap runs eleven steps in order
type: decision
status: draft
updated: 2026-10-30
audience: [all]
decided: 2026-10-29
by: owner
why: two steps were added after ADR-0029 listed them, and the texts that name bootstrap's work fell behind its docstring
would_change_if: a step added to or removed from `ops/bootstrap.py`, which changes this page, the template README and `ops/new-project.py`'s docstring together
decision_status: decided
scope: global
---
# Bootstrap runs eleven steps in order

`ops/bootstrap.py` runs eleven steps in this order, each skipped when it is done: uv; the workspace; `just`; the git
hooks; the plugins; the language servers; the sandbox; the first code graph; graphify's skill; the user-level pipeline
skill, a link to the checkout's; `harness doctor`. Its docstring describes each step, and the template README and the
docstring of `ops/new-project.py` name all eleven, which `ops/tests/test_bootstrap_steps.py` checks. This page
supersedes ADR-0029 :38-40, which stays as history: its list ends at the first code graph, and the manager-build run's
Task 9 added graphify's skill and the pipeline skill's link (items 9 and 10).

## Record and source
- [ADR-0029](../../docs/decisions/0029-a-checkout-sets-up-its-hooks-sandbox-and-graph.md)
- [ADR-0009 A checkout sets itself up](../../docs/decisions/0009-a-checkout-sets-itself-up.md)
- [The template's README](../../docs/template/PROJECTS.md)
```
`wiki/decisions/bootstrap-runs-eleven-steps-in-order.summary.md`, the whole file:
```markdown
Decision (owner, 2026-10-29): bootstrap runs eleven steps in order.
uv, the workspace, just, the git hooks, the plugins, the language servers, the sandbox, the first code graph.
Then graphify's skill, the user-level pipeline skill link and harness doctor; each step is skipped when done.
The template README and new-project's docstring name all eleven; supersedes ADR-0029 :38-40.
```

**7a** `docs/roles/CHANGELOG.md`, right above `## 1.13.0` (Step 7.2):
```markdown
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
```

**7b** `docs/template/MIGRATIONS.md`, right above `## 1.4.0` (Step 7.3; four long lines, as the 1.4.0 entry):
```markdown
## 1.5.0
- Changed template-owned paths: `CLAUDE.md`, `.claude/agents/` (new: `.claude/agents/plan-fixer.md`, `.claude/agents/translator.md`), `.claude/hooks/` (`session-start.py`), `.claude/settings.json` (Archify's entries gone), `.claude/skills/running-specagent-pipelines/` (the manager's control plane: the watcher's version 3 with `_control/registry.json` and `ACK <msg_id>` lines; new: `scripts/collect_run.py`, `scripts/duty_list.py`, `scripts/monitor_records.py`, `scripts/manager/` with `catalogue.py`, `preflight.py`, `surface.py`, `measure_manager.py` and their README, `scripts/docs/` with one page per script, `references/watching.md`; `usage_report.py` prints the date and source of its prices on its first line; the example agents' settings under `_control/`), `.github/` (`CODEOWNERS`; `workflows/ci.yml` runs the tests and the regression suite's code cases on every push; `workflows/evals.yml`), `plugins/.claude-plugin/marketplace.json` (Archify's entry gone), `templates/vault/` (new: the form of a user's vault, with `forms/manager-lessons.md` and `forms/learning-record.md`), `context/README.md`, `context/_index/` (new: `context/_index/other.md`), `docs/WHY.md` and `docs/WHY.summary.md` (new), `docs/architecture/` (new: `docs/architecture/harness-modules.md`), `docs/decisions/`, `docs/exec-plans/active/README.md`, `docs/llms.txt`, `docs/quality/`, `docs/references/`, `docs/roles/` (new: `docs/roles/catalogue.md` and its `.summary.md`, `docs/roles/manager-chat.md`, `docs/roles/types/plan-fixer.md`, `docs/roles/types/translator.md`; roles 1.14.0), `docs/template/` (new: `docs/template/DESCRIPTION.txt`), `evals/` (new: `evals/nightly.sh`, `evals/regression/README.md` and the cases `pipeline-ancestor-deny`, `pipeline-handoff-pointers`, `pipeline-job-timeouts` and `pipeline-waiters` under `evals/regression/`; deleted: `evals/regression/access-probe-critic/`, `evals/baseline/access-probe-critic/`), `ops/` (new: `ops/container.py`, `ops/contribute.py`, `ops/new-vault.py` and their tests), `packages/harness/`, `pyproject.toml`, `uv.lock`, `specs/001-chat-depth/`, `specs/002-run-loop/`, `wiki/decisions/`, `wiki/index.md`, `wiki/log.md`; deleted: `plugins/archify/`, `context/archify/`; no longer the template's: `packages/ingest/`, `context/ingest-samples/`, `wiki/concepts/content-hash-dedupe.md`, `wiki/entities/ingest-package.md`, `wiki/sources/ingest-samples.md`, `docs/exec-plans/active/run-loop.md`, `specs/001-chat-depth/actions-2026-10-02.jsonl`; read, not copied: `CHANGELOG.md`, `README.md`, `docs/exec-plans/tech-debt-tracker.md`; never copied (`omit:` in `docs/template/variables.yaml`): `docs/exec-plans/done/manager-build/`
- Steps: finish or abort the active runs and SpecAgent pipelines, or keep one and refreeze it at the end; in the template, `git log --format='%h %s' -- docs/template/VERSION` names the 1.4.0 and 1.5.0 commits, and `git diff --stat <1.4.0> <1.5.0> -- <path>` shows each path's change; copy the paths above from the template at 1.5.0 over the project's, but merge these by hand, keeping the project's lines and adding the template's: `CLAUDE.md`, `.claude/settings.json`, `.github/CODEOWNERS`, `pyproject.toml`, `context/README.md`, `docs/llms.txt`, `docs/exec-plans/active/README.md` (the template's own plan lines, `manager-build` among them, stay out), `docs/template/variables.yaml` (new: the variable `commons_path`, and the two `omit:` lines of the manager-build plan), `wiki/index.md`, `wiki/log.md`; delete `plugins/archify/` and `context/archify/` (`harness map --render` is gone); of the paths no longer the template's, delete each the project never changed and keep the rest as the project's own; `uv sync`; `uv run harness map` (it writes `docs/generated/maps/<name>.md` and removes the old `*.workflow.json`); `uv run harness catalog`; a vault made before 1.5.0 has no `forms/` (`ops/new-vault.py` copies the form only into an empty folder): copy `templates/vault/forms/` into the vault, then `forms/manager-lessons.md` once to `decisions/global/manager-lessons.md` with its dates and `sources` set and one `INDEX.md` line, and run `python3 <vault>/ops/check_pages.py <vault>` (0 problems); a project script that reads the report of `usage_report.py` takes its header from line 2 (line 1 is now `prices of <date> from <url>`; the total row is unchanged), and a link to a script's section of the skill's `scripts/README.md` goes to the script's page `scripts/docs/<stem>.md`; a pipeline config made from the skill's example keeps its `settings` paths or moves the files under `_control/` as the example now does; `uv run harness validate` names each file with a letter of the three blocks (U+10A0-U+10FF, U+1C90-U+1CBF, U+2D00-U+2D2F; before 1.5.0 the first only, as `docs/decisions/0030-the-template-is-english-only.md` still says); `uv run harness refreeze` for each run kept
- Checks: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q`, `uv run harness eval --suite regression --baseline --threshold 1.0`, `uv run harness validate`, `uv run harness loop validate`, `uv run harness audit --ci`, `uv run harness wiki-lint`, `uv run harness docs-check`, `uv run harness plan-lint`
- Breaks active runs: yes: they need `harness refreeze` (`config_changed`: `.claude/settings.json`, `.claude/agents/`, `.claude/hooks/`, `.claude/skills/` and `plugins/` changed), and an attack stage whose `output/summary.md` holds a letter of U+1C90-U+1CBF or U+2D00-U+2D2F fails its gate until it writes the summary in English
```

**7c** `CHANGELOG.md`, right below the first `### Added` (Step 7.4):
```markdown
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
```

**7d** `CHANGELOG.md`, right below the first `### Changed` (Step 7.4):
```markdown
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
```

**7e** `docs/template/variables.yaml`, after its last line (Step 7.5):
```yaml
  - docs/exec-plans/done/manager-build/      # the plan of the template's own manager-build run
  - docs/exec-plans/done/manager-build/   # the same plan once docs/exec-plans/active/README.md moves it
```

**8a** `wiki/index.md`, after the line that links `decisions/the-manager-profile-is-measured-at-its-first-call.md`:
```markdown
- [The control plane lives in the skill](decisions/control-plane-in-the-skill.md): the registry, the orders and the record monitor are files under the run folder's `_control/`, written by the skill's standard-library scripts; the harness's state is not extended to skill runs
- [The record monitor answers no request](decisions/monitor-answers-no-request.md): `monitor_records.py` finds the request lines and wakes the manager; the manager answers with `monitor_records.py answer`, since every answer changes a worktree or the sandbox
- [A request is answered below it, in the requester's file](decisions/request-answer-lines.md): `SUPPLIED:`, `COPIED:`, `CHECKED-OUT:`, `FF-DONE:` or `REFUSED: <KIND> — <why>` below the request in the requester's file, ending with its `date -u` time; it closes the oldest open request of its kind
- [The manager's duties come from the plan](decisions/duty-list-from-the-plan.md): `duty_list.py extract` writes `_control/duties.md` from the plan before the launch; the manager reads it at every wake-up and the monitor ticks a merge on a verified `Merged:` line
- [The collector deletes on the owner's yes for three runs, then by a standing rule](decisions/collector-yes-then-standing-rule.md): the owner's yes for the exact list (`--apply --yes <digest>`) for three runs, then `--apply` alone by the standing rule, the owner reading `collected.md` afterwards
- [A run is collected only after its record is checked as saved](decisions/collector-save-check.md): the collector deletes nothing until the final record lines, each lesson's skill mark, the done commits and every Deferred item's tracker row are checked
- [Code cases gate every push, session cases run nightly](decisions/code-cases-gate-every-push-sessions-run-nightly.md): `ci.yml` grades the code cases and the session cases' baselines at 1.0 on every push; the session cases run nightly by `evals/nightly.sh`; supersedes eight lines of ADR-0028
- [The skill's script docs are one page per script, the README an index](decisions/skill-script-pages.md): each script's usage, options and files on its page under `scripts/docs/`; `scripts/README.md` is the index, at most 12,000 bytes
- [usage_report.py's prices carry their date and source](decisions/dated-api-prices.md): `usage_report.py`'s list prices carry their date and page (`PRICES_AS_OF`, `PRICES_URL`), printed on the report's first line
- [Roles and sessions keep their names until the owner names them](decisions/roles-and-sessions-keep-their-names.md): a pipeline's agents are roles and one run of a role a session; nothing is renamed until the owner names them
- [The spec writer's model is a dated exception](decisions/the-spec-writers-model-is-a-dated-exception.md): the model the owner ordered for spec writing is recorded in the vault as a dated exception with its `would_change_if`, not as a new rule
- [A graph over the vault is measured before it is built](decisions/a-vault-graph-is-measured-before-it-is-built.md): no vault graph in this run; the main session measures `INDEX.md` and `outline.py` first, then decides
- [Bootstrap runs eleven steps in order](decisions/bootstrap-runs-eleven-steps-in-order.md): `ops/bootstrap.py`'s eleven steps in order, named in full by the template README and `ops/new-project.py`; supersedes ADR-0029 :38-40
```

**8b** `wiki/log.md`, appended after one blank line:
```markdown
## 2026-10-30 pages written with Task 11 of the manager-build run
- commit: Task 11 of the manager-build run
- created: decisions/control-plane-in-the-skill.md
- created: decisions/monitor-answers-no-request.md
- created: decisions/request-answer-lines.md
- created: decisions/duty-list-from-the-plan.md
- created: decisions/collector-yes-then-standing-rule.md
- created: decisions/collector-save-check.md
- created: decisions/code-cases-gate-every-push-sessions-run-nightly.md
- created: decisions/skill-script-pages.md
- created: decisions/dated-api-prices.md
- created: decisions/roles-and-sessions-keep-their-names.md
- created: decisions/the-spec-writers-model-is-a-dated-exception.md
- created: decisions/a-vault-graph-is-measured-before-it-is-built.md
- created: decisions/bootstrap-runs-eleven-steps-in-order.md
- updated: index.md
```

## Commit message
```text
feat(manager): Task 11 — release 1.5.0: VERSION, MIGRATIONS, CHANGELOG, this run's decision pages, the three blocks in harness validate, the final checks

The template is 1.5.0 and the role bundle 1.14.0; the MIGRATIONS.md entry 1.5.0, counted from 1.4.0, is the brief
of a project's sync run; CHANGELOG.md gets [1.5.0]. harness validate refuses a letter of U+10A0-U+10FF,
U+1C90-U+1CBF and U+2D00-U+2D2F (8.3.11). The example agents read their settings under _control/; SKILL.md names
the tools of the other lanes and the watcher's detail moves to references/watching.md. The tracker closes TD-008,
TD-010 and TD-011, keeps TD-002 open with its reason and holds every Deferred item in TD-013 to TD-022 (5.9.4).
The template README, new-project's docstring and LEARNING.md say what the run built: bootstrap's eleven steps,
docs/handoff/, ci.yml at threshold 1.0. Thirteen decision pages with their index lines; new projects leave this
plan folder out. Spec 5.9.1, 5.9.4, 8.3.11; acceptance 10.1-10.20 by the verifier at M3.
```

## Deferred (with the reason)
- The one-block pattern of `ops/tests/test_new_vault.py:37`: it checks the files `ops/new-vault.py` writes for
  U+10A0-U+10FF only; it is a test of the shared-base run, which this task does not reopen (Step 1.5), and it takes the
  three blocks when it is next edited. Tracker row TD-020 (Step 4).

## Verified
All at 19a4a95 unless another commit is named; "the copy" is a fresh export of 19a4a95 in the planner's scratch
folder, a git repository with the plan folder and this task's steps applied as each step says.
- The base: `lessons.md` holds `Merged: a+b+c+d at 19a4a95` (`grep -c`, 1); `git diff --stat 51dd0ce 19a4a95`:
  `12 files changed, 74 insertions(+), 14 deletions(-)` (R502 5b8d3b1, V7 c3c1cf0, V6 94feff2).
- Step 0: `pyproject.toml:25` `testpaths` (packages, the skill's `scripts/tests`, `ops/tests`); pytest 9.1.1 in the
  plan worktree's venv takes `testpaths` only with no path given and run from the rootdir
  (`_pytest/config/__init__.py:1410-1416`), and its default `norecursedirs` holds `.*` (`_pytest/main.py:229-239`);
  collect on the copy: 1567 with the three paths, 1174 with a bare path.
- Step 1: `catalog.py:61-62` (`GEORGIAN` one block, `LETTER`), `catalog.py:277` (`listed`);
  `test_validate_listing.py:17-18`; `test_contribute.py:357-366`; `test_evals_llm.py:9-10` (one import block);
  red `9 failed, 46 passed`, green `55 passed` (51dd0ce, the files unchanged at 19a4a95).
- Step 2: `example/agents.json` `settings` at :54, :69, :84, :98, :112, :128 and `example/agents-judge.json:30`;
  `scripts/README.md:88`; `test_skill_example.py:97`; `test_docs.py:126-128`; `test_preflight.py:660-662` (the
  comment) and :677-678; red `2 failed, 62 passed`, green `64 passed`.
- Step 3: `SKILL.md` 11,764 bytes (the same at 51dd0ce), :83, :101, :115 and :121 as Step 3 names them; 11,696
  bytes on the copy; red `3 failed, 3 passed`, green `6 passed`, `test_ecc_pins.py` `13 passed`.
- Step 4: the tracker 5,007 bytes, 11,723 on the copy with 22 rows TD-001 to TD-022; `check_deferred` of
  `collect_run.py` red 47, green `no refusal` (a scratch repository with this plan folder and 51dd0ce's tracker,
  which is 19a4a95's).
- Step 5: `docs/template/PROJECTS.md:17-21`, `ops/new-project.py:4`, `docs/quality/LEARNING.md:18-19`; red
  `1 failed, 11 passed`, green `12 passed` (51dd0ce with Steps 1-3).
- Steps 6 and 8: `wiki/index.md:27` is the last line of `## Decisions`, 5,016 bytes, 8,330 on the copy;
  `wiki/decisions/` 42 files, 68 on the copy; `test_wiki_decisions.py` red `1 failed, 22 passed`, green `23 passed`;
  `docs/exec-plans/active/README.md` ends with `## Plans` and one blank line.
- Step 7: `docs/template/MIGRATIONS.md` entry form :59-63 and the 1.4.0 entry :6-10; `git log --
  docs/template/VERSION`: 63b25a3 made 1.4.0; `CHANGELOG.md` :5 `[Unreleased]`, :7, :18, :34, :43 `[1.4.0]`;
  `docs/roles/CHANGELOG.md:6` `## 1.13.0`; `test_documents.py:13-17`; `state.py:28-38`; `variables.yaml:22-27`;
  `ops/new-project.py` :5-7, :30-41, :51, :65-66; `test_new_project_omit.py` :14-15, :18-37, :40-78;
  `.github/workflows/ci.yml` on push `["**"]` and pull_request, run steps :16-22; `pyproject.toml:18` line length
  120; `templates/vault/ops/check_pages.py:5`; `harness map [-h] [--check]`; `watch_agents.py:388`.
- Step 9: `audit.py:17-20` (`INSTRUCTION`), :175-194 (`version_check`), :183 (`no_instruction_change`);
  `cli.py:39-42` (`root_dir`), :253 (`version-check`); on the copy: the task's files `189 passed`, `ruff check` (ruff
  0.16.10) `All checks passed!`, `ruff format --check` `215 files already formatted`, the suite `1582 passed,
  1 skipped` both ways, the skip `test_gate_sandbox.py:57`; the logs show the same skip (`build-log-a.md:16` and
  :18, `build-log-c.md:17`, `verify.md:1079`); blocks 3 and 4 verbatim: `54`, `0`, `0`, then `54` and the JSON.
