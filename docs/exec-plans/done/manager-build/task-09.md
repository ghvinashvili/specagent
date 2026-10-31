# Task 9 — The tracker sweep: TD-001, TD-007, TD-009, TD-012, the container's `docs/handoff/`, the user-level skill symlink, `just` in bootstrap

planner: c
builder: c
depends_on: —
files: `ops/new-project.py` (`--container` makes `docs/handoff/`), `ops/tests/test_container.py` (one test added); `ops/bootstrap.py` (graphify's skill, TD-007; the user-level pipeline skill as a link, 8.3.16; `just`, 8.3.12, unchanged), `ops/tests/test_bootstrap_steps.py` (the fixture and one test changed by name, four tests added); `.claude/hooks/session-start.py` (C21: the setup message names the two new steps and graphify's block in `~/.claude/CLAUDE.md`; edited with Edit, `.claude/hooks` is closed to shell commands), `packages/harness/tests/test_setup.py` (C21: one test's step list gains the two steps, one assert the block); `packages/harness/tests/test_doc_rules.py` (new: TD-012's docs-check case and TD-009's size check); `.claude/skills/adr/SKILL.md` and `.claude/workflows/docs-gardening.js` are read by that test, not changed (TD-012 found them right); `docs/architecture/harness.md` (the module map moved out), `docs/architecture/harness-modules.md` (new), `docs/architecture/index.md` (its line at the end of the list); `docs/exec-plans/tech-debt-tracker.md` (rows TD-001, TD-007, TD-009, TD-012: the Plan cell only); `docs/quality/QUALITY_SCORE.md` (line 6, the reason cell); `docs/llms.txt` (one line, at the end of `## Start here`). Not touched: `packages/harness/src/harness/state.py` and `catalog.py` (TD-001 is found implemented, departure 1), `ops/machine-setup.py`, `ops/container.py`
acceptance: 10.19 for the bootstrap step (the two new steps add no `sleep` and no waiting loop: Step 3's check); no other check of section 10 is this task's (the index's row 9)

All paths below are relative to the checkout. Builder C starts Task 9 on `feat/manager-build-c` after Tasks 6 and 8;
neither of them lists a file Task 9 touches (index rows 6 and 8), and every file Task 9 reads or changes is identical
at main f70e84c, at the plan branch's 434cf7b and de15a76, and on `feat/manager-build-c` (still at f70e84c on
2026-10-29), where every figure below was measured (Step 0 prints the proof). The
`ops/` scripts and their tests use the standard library and pytest only (Global Constraint 9); no letter of a refused block
anywhere (D1).

## Goal
Close the four tracker rows the index gives this task and the three small gaps of spec 8.3 next to them, each with the
one test or command that proves it: TD-001 (found implemented: closed with the evidence), TD-007 (bootstrap installs
graphify's skill for Claude Code at user level), TD-009 (`docs/architecture/harness.md` under 12 KB), TD-012 (one rule
for a new decision record's index line, the adr skill and the docs-gardening workflow aligned on it, one docs-check
case), `ops/new-project.py --container` giving a project the `docs/handoff/` folder `ops/container.py` gives (the
owner's final plan, 0.6), the user-level pipeline skill as a link to the checkout's (8.3.16), and `just` in bootstrap
(8.3.12, met since 81fd5c1: proved, not changed).

## Departures (from the spec and the index, with the reason)
1. TD-001 is closed as stale, with no code. The row says `write_handoff` and `validate_repository` "are interfaces, not
   implementations"; at f70e84c both are implemented and called: `state.py:588` renders HANDOFF.md for `harness handoff`
   (`cli.py:408`), `catalog.py:222` is `harness validate` (`cli.py:421`), and tests call them (`test_depth.py:360`,
   `test_assign.py:268`, `test_rounds.py:655`; `test_validate_listing.py:97`, `test_map.py:331`). The index row offered
   "implement, or re-scope with a decision page"; neither applies, so `state.py` and `catalog.py` stay untouched (Task 11
   alone edits `catalog.py`, its `GEORGIAN` set) and no decision page is written. Step 6 runs the tests that call both
   functions as the proof.
2. 8.3.12 (`just` absent, bootstrap installs it as optional) is met at f70e84c: bootstrap's step 3 installs
   `rust-just==1.58.0` with `uv tool install` when `just` is missing (`ops/bootstrap.py:11, :41, :126-129`, added by
   81fd5c1 on 2026-10-29, after the spec's measurement of 2026-10-28), and `test_bootstrap_steps.py:49-56` pins the
   command. This machine has `just` 1.59.0 (`uv tool list`: `rust-just v1.59.0`; `command -v just`:
   `/home/tite/.local/bin/just`), installed outside bootstrap, which skips a present `just`. Task 9 keeps the step and
   proves it (Step 3); making `just` a failing step instead of an optional one is not asked (README.md:46 lists it as
   optional).
3. 8.3.16 (the user-level skill is a copy, not the link): on this machine the link exists already, made by hand
   (`~/.claude/skills/running-specagent-pipelines -> <template checkout>/.claude/skills/running-specagent-pipelines`,
   2026-10-29 11:08, the old copy kept as `running-specagent-pipelines.old`); no script makes it on a new machine.
   Bootstrap now makes it when there is none. An existing link is kept whatever it points to (a dangling one
   is named in the log with the `ln -sfn` that replaces it, C20), and an existing folder (a copy) is kept and named
   in the log with the command that replaces it: a set-up step never deletes the owner's
   files. The first checkout set up on a machine owns the link (normally the template's own, cloned first).
4. TD-007 names two things: graphify's skill and graphify's PreToolUse hook. Task 9 installs the skill only (user
   level, the row's impact cell: "graph queries from a session need the user-level skill"). The hook is project-scoped
   (`graphify install --project`, graphify 0.9.64 `install.py:744`), would edit the tracked `.claude/settings.json`,
   and the graph is refreshed by the git hooks of bootstrap's step 4 already: Deferred.
5. `graphify install --platform claude` also appends a four-line block to `~/.claude/CLAUDE.md` (graphify 0.9.64
   `install.py:698-714`, `_skill_registration`): graphify's own registration, about 60 tokens in every session. The
   docstring and the SessionStart setup message say so (C21); bootstrap does not edit `~/.claude/CLAUDE.md` itself.
6. `CLAUDE_CONFIG_DIR` (which graphify honours, `install.py:132-133`) is not read: bootstrap looks for both skills
   under `~/.claude/skills/` only (Deferred, with the reason).
7. `docs/quality/QUALITY_SCORE.md` line 6 loses its stale reason, but its score stays 2: the file's rule is "a score
   changes only with a linked measurement" (line 10), and Task 9 runs its own tests only (C503's rule, `lessons.md`
   22:27); the release review re-scores it (Deferred).
8. The manager's sandbox note (8.3.8) is Task 7's (`docs/roles/manager-chat.md`), as the index's row 9 says.
9. TD-012 is found aligned at f70e84c, so the adr skill and the docs-gardening workflow, both listed in the index's row
   9, are read and not changed. The adr skill's step 3 (`.claude/skills/adr/SKILL.md:12`) writes the record's line in
   `docs/decisions/README.md`. The audit's clause (3) (`.claude/workflows/docs-gardening.js:20`) asks for a line in
   `docs/llms.txt` or in the folder `README.md` that `docs/llms.txt` links, and needs none for a `.summary.md`. Both
   agree with ADR-0026, `AGENTS.md:33` and `catalog.listed` (`catalog.py:277`). The leftover patch of the template-core
   run (`experiments/template-core/leftovers/verify-worktree-uncommitted.patch`) would bring back the older rule, so it
   is dropped. The row's "one docs-check case" is the two TD-012 tests of `test_doc_rules.py` (Step 4).

## Contracts
- For Task 11 (sent to `manager/plan-fixer`, the fixer of odd tasks, as `planner-c: contract for Task 11 — ...`): Task 9
  leaves `packages/harness/src/harness/state.py` and `catalog.py` untouched (TD-001 is found implemented, departure 1),
  so Task 11 alone edits `catalog.py` (its `GEORGIAN` set); `docs/quality/QUALITY_SCORE.md` line 6 keeps its score 2
  for the release review to score (departure 7); Task 9 changes only the last cell of the tracker rows TD-001 (line 5),
  TD-007 (line 11), TD-009 (line 13) and TD-012 (line 16). The four items under "Deferred" below are real items: Task 11
  turns each into a tracker row (the index's row 11, Task 6's K1: Deferred items are read outside fenced code).
- From Task 1 (`task-01.md` Contracts, 1971558; the index's row 9): the tracker is index-like (Global Constraint 14). A
  row this run closes keeps its place and every cell but the last, and its Plan cell becomes
  `closed: manager-build Task 9 — <what closed it>`. TD-007 is line 11, next to Task 1's TD-006 at line 10; the main
  session keeps both changed lines at the merge.
- `docs/llms.txt` is index-like too (Global Constraint 14; Tasks 1, 7 and 11 add lines of their own): Task 9 adds one
  line at the end of `## Start here` (after line 14 at f70e84c) and changes no other line.
- `ops/`, `.claude/skills/adr/`, `.claude/workflows/`, `docs/architecture/` and the tracker are lane C's (Global
  Constraint 14), and Tasks 6 and 8, which builder C builds first, list none of the files Task 9 touches or reads (the
  index's rows 6 and 8). Step 0 checks this on the builder's HEAD before anything is written.

## Interfaces
`ops/new-project.py` (no new name; standard library only):
- The `--container` branch makes `<container>/docs/handoff/` with `mkdir(parents=True, exist_ok=True)` right after it
  makes `experiments/`, so the container holds the folders of `ops/container.py`'s `FOLDERS` (`container.py:20`) and a
  second run changes nothing.
- Docstring line 6, `beside it runs/ (marked as the runs root, docs/roles/RUNS.md) and experiments/ (copies made for
  trials). With`, becomes these two lines:

  ```text
  beside it runs/ (marked as the runs root, docs/roles/RUNS.md), experiments/ (copies made for trials) and
  docs/handoff/ (the manager's hand-over notes), as ops/container.py lays them out. With
  ```

`ops/bootstrap.py` (standard library only; `os`, `shutil` and `Path` are imported at f70e84c):
- Two module constants right before `PLATFORM` (`bootstrap.py:42` at f70e84c), each with a short trailing comment:
  `USER_SKILLS = Path.home() / ".claude" / "skills"` (Claude Code's user-level skills; graphify's install writes there
  too) and `PIPELINE_SKILL = "running-specagent-pipelines"`. The tests patch `USER_SKILLS` (the `boot` fixture, with
  `raising=False`, so that the old file fails on the asserts, not in the fixture).
- `install_graphify_skill(log) -> None`: `graphify = shutil.which("graphify")`; when graphify is found and
  `USER_SKILLS / "graphify" / "SKILL.md"` is not a file, it calls
  `step("graphify-skill", [graphify, "install", "--platform", "claude"], log)` (`step`, `bootstrap.py:73` at f70e84c,
  logs the command and a non-zero exit). The result is ignored: the install is optional and never enters `failed`.
- `link_user_skill(log) -> None`, with `source = ROOT / ".claude" / "skills" / PIPELINE_SKILL` and
  `link = USER_SKILLS / PIPELINE_SKILL`, in this order:
  1. returns and writes nothing when `source` is not a folder, or when `link.is_symlink()` and `link.exists()` (a live
     link is kept whatever checkout it points to);
  2. when `link.is_symlink()` (a dangling link, C20): writes
     `skill: {link} -> {os.readlink(link)} is dangling, kept; ln -sfn {source} {link} makes it the link\n`
     and returns (`os` is imported at `bootstrap.py:31` at f70e84c; ruff's format puts the f-string on its own
     line inside `log.write(`);
  3. when `link.exists()` (a copy): writes
     `skill: {link} is a copy, kept; mv {link} {link}.old && ln -s {source} {link} makes it the link\n` and returns;
  4. otherwise `link.parent.mkdir(parents=True, exist_ok=True)` and `link.symlink_to(source, target_is_directory=True)`
     with the absolute `source`, then writes `skill: {link} -> {source}\n`; an `OSError` here writes
     `skill: {link} not linked: {exc}\n` instead.
  It never deletes or moves a file and never enters `failed`.
- `setup(log) -> list[str]`: calls `install_graphify_skill(log)` and then `link_user_skill(log)` after the
  `build_graph(log)` step, before it returns `failed`. Measured on the scratch build: `setup` grows from 41 to 43 lines,
  the new functions have 5 and 20 lines (C20's branch adds 5).
- The module docstring gets two items after item 8 and the doctor item becomes 11 (the fresh-checkout test reads
  `graphify install --platform claude` and `~/.claude/skills/running-specagent-pipelines` in `module.__doc__`):

  ```text
  9. graphify's skill for Claude Code, when graphify is installed and ~/.claude/skills/graphify/SKILL.md is missing:
     `graphify install --platform claude`, which also appends its four-line block to ~/.claude/CLAUDE.md; optional.
  10. The pipeline skill at user level: ~/.claude/skills/running-specagent-pipelines becomes a symbolic link to this
      checkout's .claude/skills/running-specagent-pipelines when it is missing; an existing link or copy is kept, and a
      copy or a dangling link is named in the log with the command that replaces it; optional.
  11. `harness doctor`: ...  (the old item 9, its text unchanged)
  ```

`packages/harness/tests/test_doc_rules.py` (new): no product code; it reads `.claude/skills/adr/SKILL.md`,
`.claude/workflows/docs-gardening.js` and `docs/architecture/`, and calls `harness.catalog.docs_check` (`catalog.py:324`)
on a tree it builds in `tmp_path`.

`docs/architecture/harness-modules.md` (new): lines 1-4 are

```text
# Harness module map

One row per module of `packages/harness/src/harness/`; how the modules work together: [Harness architecture](harness.md).

```

and lines 5-28 are `docs/architecture/harness.md` lines 123-146 of f70e84c, moved verbatim (the table's heading row,
its separator and 22 module rows). `docs/architecture/harness.md` keeps its line 122 (`## Module map (...)`) and puts in
place of the table the line `One row per module and what it owns: [Harness module map](harness-modules.md).` and a blank
line.

## Steps
`W` is your worktree (builder C's, on `feat/manager-build-c`). Every command runs from the shell's start folder, with
no top-level `cd`. `<t>` stands for pytest's time. The figures were measured on scratch copies of f70e84c ("Verified").
The builder runs this task's four test files, its own commands and the ruff pair. The whole harness suite,
`harness validate`, `docs-check`, `wiki-lint` and `map --check` are the verifier's at M2 (C503's rule, `lessons.md`
22:27). On the scratch build `catalog.docs_check` gives ok with 0 problems and 0 warnings.
`BASE` is the commit Task 9 began on, where the build log's review range starts: `HEAD` at Step 0 when no hand-over
committed WIP, else the parent of the first WIP commit; Step 7 measures the whole change from it, never from `HEAD`
(lessons 23:45, B2 of build-log-c).

- [ ] **Step 0: the base.** Before anything is written, check that Tasks 6 and 8 changed no file this task touches or
  reads (the lessons' 23:03 rule).
  Run:
  ```bash
  git -C "${W:?}" diff --stat f70e84c HEAD -- ops/new-project.py ops/container.py ops/bootstrap.py \
    ops/tests/test_container.py ops/tests/test_bootstrap_steps.py packages/harness/tests/test_doc_rules.py \
    packages/harness/src/harness/catalog.py packages/harness/src/harness/state.py packages/harness/src/harness/cli.py \
    packages/harness/tests/test_depth.py packages/harness/tests/test_assign.py \
    packages/harness/tests/test_validate_listing.py packages/harness/tests/test_map.py .claude/skills/adr/SKILL.md \
    .claude/workflows/docs-gardening.js docs/architecture docs/exec-plans/tech-debt-tracker.md \
    docs/quality/QUALITY_SCORE.md docs/llms.txt AGENTS.md .claude/hooks/session-start.py \
    packages/harness/tests/test_setup.py
  ```
  Expected: no output (measured 2026-10-29 on `feat/manager-build-c`, then still at f70e84c, and on the plan branch at
  de15a76; C21's two paths at 22eca3d and aafa868). If anything is printed, stop and send the output to
  `manager/plan-fixer`. The line numbers below hold only for these files as they are at f70e84c.

- [ ] **Step 1: the tests and the red run.**
  1. Write `packages/harness/tests/test_doc_rules.py` exactly as under "Tests in full" (a new file, no shebang).
  2. Apply the three diffs under "Tests in full" to `ops/tests/test_container.py`, `ops/tests/test_bootstrap_steps.py`
     and `packages/harness/tests/test_setup.py`:
     hunk by hunk with Edit, or save each block to your scratch folder and run `git -C "${W:?}" apply --check <file>`
     and then `git -C "${W:?}" apply <file>`.
     Run: `git -C "${W:?}" diff --numstat -- ops/tests packages/harness/tests/test_setup.py`
     Expected:
     ```text
     83	3	ops/tests/test_bootstrap_steps.py
     22	0	ops/tests/test_container.py
     2	1	packages/harness/tests/test_setup.py
     ```
  3. Run: `(cd "${W:?}" && uv sync -q && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider ops/tests/test_container.py ops/tests/test_bootstrap_steps.py packages/harness/tests/test_doc_rules.py 2>&1 | tail -n 10)`
     Expected: nine `FAILED` lines naming these tests (a ` - <message>` tail may follow a name), then the count:
     ```text
     FAILED ops/tests/test_container.py::test_new_project_with_container_gives_the_folders_container_py_gives
     FAILED ops/tests/test_bootstrap_steps.py::test_a_fresh_checkout_gets_just_its_hooks_and_its_sandbox_then_its_first_graph
     FAILED ops/tests/test_bootstrap_steps.py::test_on_macos_the_seatbelt_is_checked_and_a_hooks_folder_of_the_checkout_is_kept
     FAILED ops/tests/test_bootstrap_steps.py::test_graphifys_skill_is_installed_only_where_graphify_is_and_its_skill_is_not
     FAILED ops/tests/test_bootstrap_steps.py::test_a_failed_graphify_skill_install_is_not_a_failed_setup
     FAILED ops/tests/test_bootstrap_steps.py::test_the_user_level_pipeline_skill_becomes_a_link_to_the_checkouts_once
     FAILED ops/tests/test_bootstrap_steps.py::test_an_existing_link_or_copy_of_the_pipeline_skill_is_kept_and_a_checkout_without_it_links_nothing
     FAILED packages/harness/tests/test_doc_rules.py::test_every_architecture_page_is_at_most_12000_bytes
     FAILED packages/harness/tests/test_doc_rules.py::test_the_module_map_is_a_page_of_its_own_that_the_architecture_links
     9 failed, 11 passed in <t>s
     ```
     The two TD-012 tests of `test_doc_rules.py` pass already: they pin a rule that is found right (departure 9). The
     wrong versions W16a-W19 turned them red ("Verified").
  4. Run: `(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider packages/harness/tests/test_setup.py 2>&1 | tail -n 2)`
     Expected (C21: the setup message does not name the two new steps yet; a ` - <message>` tail may follow the
     name):
     ```text
     FAILED packages/harness/tests/test_setup.py::test_the_setup_message_names_every_step_of_the_bootstrap
     1 failed, 13 passed in <t>s
     ```

- [ ] **Step 2: `ops/new-project.py --container` makes `docs/handoff/`.** Edit `ops/new-project.py` as "Interfaces"
  says: docstring line 6 becomes two lines, and one line goes after the `experiments` mkdir.
  Run: `(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider ops/tests/test_container.py 2>&1 | tail -n 1)`
  Expected: `5 passed in <t>s`
  Run: `git -C "${W:?}" diff --numstat -- ops/new-project.py`
  Expected: `3	1	ops/new-project.py`

- [ ] **Step 3: `ops/bootstrap.py`: graphify's skill (TD-007), the user-level skill link (8.3.16), `just` proved
  (8.3.12).** Edit `ops/bootstrap.py` as "Interfaces" says: the two constants, the two functions, the two calls in
  `setup()`, and docstring items 9 and 10 (the doctor item becomes 11). Nothing else changes. Bootstrap's own item 3,
  the `just` install (`JUST = "rust-just==1.58.0"`, `bootstrap.py:41` at f70e84c), stays as it is (departure 2). The
  fresh-checkout test still pins its command.
  Run: `(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider ops/tests/test_bootstrap_steps.py 2>&1 | tail -n 1)`
  Expected: `11 passed in <t>s`
  Then the setup message of `.claude/hooks/session-start.py` (C21, departure 5): `.claude/hooks/` is closed to shell
  commands, so make this one change with Edit, in `start_setup`'s `return (` (lines 132-134 at f70e84c, each line
  indented by eight spaces in the file); nothing else in the hook changes. Replace
  ```python
          "Setting up this checkout in the background (uv, the workspace, `just`, the git hooks, the plugins, the "
          f"language servers, the sandbox, the first code graph); the log is {root / '.claude' / 'bootstrap.log'}. Run "
          "`python3 ops/bootstrap.py --wait` to wait for it."
  ```
  with
  ```python
          "Setting up this checkout in the background (uv, the workspace, `just`, the git hooks, the plugins, the "
          "language servers, the sandbox, the first code graph, graphify's skill, the user-level pipeline skill link; "
          "graphify's skill install appends a block to ~/.claude/CLAUDE.md); the log is "
          f"{root / '.claude' / 'bootstrap.log'}. Run `python3 ops/bootstrap.py --wait` to wait for it."
  ```
  Run: `(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider packages/harness/tests/test_setup.py 2>&1 | tail -n 1)`
  Expected: `14 passed in <t>s`
  Run (10.19's clause for the bootstrap step: no `sleep` and no waiting loop; 8.3.12: the pin kept):
  `grep -c sleep "${W:?}/ops/bootstrap.py"; grep -cE '^\s*while ' "${W:?}/ops/bootstrap.py"; grep -c '^JUST = "rust-just==1.58.0"' "${W:?}/ops/bootstrap.py"`
  Expected:
  ```text
  0
  0
  1
  ```

- [ ] **Step 4: TD-012, one rule pinned by a docs-check case (departure 9).** No file changes. The adr skill's step 3
  (`.claude/skills/adr/SKILL.md:12`) and clause (3) of the docs-gardening audit (`.claude/workflows/docs-gardening.js:20`)
  already state the layered rule of ADR-0026 (`AGENTS.md:33`, `catalog.listed`, `catalog.py:277`). The two TD-012 tests
  of `test_doc_rules.py` pin both texts to what `docs_check` accepts. The patch
  `experiments/template-core/leftovers/verify-worktree-uncommitted.patch` (outside the checkout) holds the older rule:
  it is dropped, neither applied nor deleted.
  Run: `(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider packages/harness/tests/test_doc_rules.py -k 'adr_skill or docs_gardening' 2>&1 | tail -n 1)`
  Expected: `2 passed, 2 deselected in <t>s` (the other two wait for Step 5)
  Run: `git -C "${W:?}" diff --quiet f70e84c -- .claude/skills/adr .claude/workflows && echo unchanged`
  Expected: `unchanged`

- [ ] **Step 5: TD-009: `docs/architecture/harness.md` under 12 KB, and the new page listed.**
  1. Make `docs/architecture/harness-modules.md` from `harness.md` while the table is still there: its lines 1-4, then
     `harness.md` lines 123-146 verbatim. Then put the one link line in place of those lines of `harness.md`. This
     command does both (the block sits at two spaces, since docs-check reads a fence only at three spaces or fewer,
     `catalog.py:57`):
  ```bash
  ( cd "${W:?}" && { printf '%s\n' '# Harness module map' '' 'One row per module of `packages/harness/src/harness/`; how the modules work together: [Harness architecture](harness.md).' ''; sed -n '123,146p' docs/architecture/harness.md; } > docs/architecture/harness-modules.md && sed -i '123,146c One row per module and what it owns: [Harness module map](harness-modules.md).' docs/architecture/harness.md )
  ```
  2. `docs/architecture/index.md`: after line 9 (`- [Connections between chats](connections.md): ...`, the last line
     of the list) add
     `- [Harness module map](harness-modules.md): one row per module of the harness package and what it owns`
  3. `docs/llms.txt` (index-like, see Contracts): after line 14 (`- [Architecture index](architecture/index.md): ...`,
     the last line of `## Start here`) add
     `- [Harness module map](architecture/harness-modules.md): one row per module of packages/harness/src/harness/ and what it owns`
  Run:
  ```bash
  ( cd "${W:?}" && diff <(git show f70e84c:docs/architecture/harness.md | sed -n '123,146p') <(sed -n '5,28p' docs/architecture/harness-modules.md) && sed -n '122,125p' docs/architecture/harness.md && wc -c docs/architecture/harness.md docs/architecture/harness-modules.md docs/architecture/index.md docs/llms.txt )
  ```
  Expected (no diff output: the table moved verbatim):
  ```text
  ## Module map (`packages/harness/src/harness/`)
  One row per module and what it owns: [Harness module map](harness-modules.md).

  ## Adding a command
  11241 docs/architecture/harness.md
   3422 docs/architecture/harness-modules.md
    828 docs/architecture/index.md
   6405 docs/llms.txt
  21896 total
  ```
  Run: `(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider packages/harness/tests/test_doc_rules.py 2>&1 | tail -n 1)`
  Expected: `4 passed in <t>s`

- [ ] **Step 6: TD-001's proof, the tracker rows, `QUALITY_SCORE.md` line 6.**
  Run (the tests that call `write_handoff` and `validate_repository`, departure 1):
  `(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider packages/harness/tests/test_depth.py::test_the_handoff_lists_the_failing_advisory_checks packages/harness/tests/test_assign.py::test_the_handoff_of_a_run_names_the_assignment_as_the_next_step packages/harness/tests/test_validate_listing.py::test_validate_runs_the_three_checks_in_order_and_each_function_is_small packages/harness/tests/test_map.py::test_the_real_tables_have_no_map_problem_and_validate_reports_an_order_problem 2>&1 | tail -n 1)`
  Expected: `4 passed in <t>s`
  Then edit `docs/exec-plans/tech-debt-tracker.md`. In rows TD-001 (line 5), TD-007 (line 11), TD-009 (line 13) and
  TD-012 (line 16), only the last cell (Plan) changes, to these texts (each between `| ` and ` |`):
  - TD-001: ``closed: manager-build Task 9 — found implemented: `write_handoff` (`state.py:588`, `harness handoff`) and `validate_repository` (`catalog.py:222`, `harness validate`), each called by tests (`test_depth.py`, `test_assign.py`; `test_validate_listing.py`, `test_map.py`)``
  - TD-007: ``closed: manager-build Task 9 — `ops/bootstrap.py` step 9 runs `graphify install --platform claude` when graphify is installed and `~/.claude/skills/graphify/SKILL.md` is missing; the project-scoped PreToolUse hook is in Task 9's Deferred list``
  - TD-009: ``closed: manager-build Task 9 — the module map moved to `docs/architecture/harness-modules.md`; `harness.md` 11,241 bytes; `test_doc_rules.py` holds every page of `docs/architecture/` at most 12,000 bytes``
  - TD-012: ``closed: manager-build Task 9 — the layered rule holds (ADR-0026, `AGENTS.md:33`, `catalog.listed`); the patch reverts the adr skill's step 3 and the docs-gardening clause to the older rule and is dropped, not applied; `test_doc_rules.py` pins both texts to docs-check``

  In `docs/quality/QUALITY_SCORE.md` line 6 only the reason cell changes: `interfaces without implementation (TD-001)`
  becomes `not re-scored since TD-001 was closed as stale (manager-build Task 9); the release review scores it`. The
  score 2 and the other cells stay (departure 7).
  Run:
  ```bash
  ( cd "${W:?}" && git diff --numstat -- docs/exec-plans/tech-debt-tracker.md docs/quality/QUALITY_SCORE.md && diff <(git show f70e84c:docs/exec-plans/tech-debt-tracker.md | sed -n '5p;11p;13p;16p' | sed 's/|[^|]*|$//') <(sed -n '5p;11p;13p;16p' docs/exec-plans/tech-debt-tracker.md | sed 's/|[^|]*|$//') && echo first-cells-kept )
  ```
  Expected:
  ```text
  4	4	docs/exec-plans/tech-debt-tracker.md
  1	1	docs/quality/QUALITY_SCORE.md
  first-cells-kept
  ```

- [ ] **Step 7: the ruff pair, the four test files once more, the commit and the log line.**
  Run:
  ```bash
  ( cd "${W:?}" && F=".claude/hooks/session-start.py ops/new-project.py ops/bootstrap.py ops/tests/test_container.py ops/tests/test_bootstrap_steps.py packages/harness/tests/test_doc_rules.py packages/harness/tests/test_setup.py" && uv run ruff check $F && uv run ruff format --check $F )
  ```
  Expected:
  ```text
  All checks passed!
  7 files already formatted
  ```
  Run: `(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider ops/tests/test_container.py ops/tests/test_bootstrap_steps.py packages/harness/tests/test_doc_rules.py packages/harness/tests/test_setup.py 2>&1 | tail -n 1)`
  Expected: `34 passed in <t>s`
  Stage the thirteen paths, then check that no added Python line is over 120 characters (the lessons' 23:12 rule; three
  lines of `ops/new-project.py` are 121 characters at f70e84c and stay as they are; the moved table rows are Markdown):
  ```bash
  git -C "${W:?}" add .claude/hooks/session-start.py docs/architecture/harness-modules.md docs/architecture/harness.md docs/architecture/index.md docs/exec-plans/tech-debt-tracker.md docs/llms.txt docs/quality/QUALITY_SCORE.md ops/bootstrap.py ops/new-project.py ops/tests/test_bootstrap_steps.py ops/tests/test_container.py packages/harness/tests/test_doc_rules.py packages/harness/tests/test_setup.py && git -C "${W:?}" diff --cached -U0 "${BASE:?}" -- .claude/hooks ops packages/harness/tests | grep '^+[^+]' | awk 'length > 121' | wc -l
  ```
  Expected: `0`
  Commit with this message (subject line, blank line, body), with the attribution lines your assignment gives:
  ```text
  feat(manager): Task 9 — the tracker sweep: TD-001, TD-007, TD-009, TD-012, the container's docs/handoff/, the user-level skill link, just in bootstrap

  bootstrap installs graphify's skill for Claude Code and links the user-level pipeline skill to the checkout's,
  and the SessionStart setup message names both; new-project --container makes docs/handoff/ as ops/container.py
  does; the harness module map moves to its own page, harness.md 11,241 bytes; TD-001 closed as found implemented,
  TD-007, TD-009 and TD-012 closed; just in bootstrap proved, unchanged.
  ```
  Run: `git -C "${W:?}" diff --name-only "${BASE:?}" HEAD && git -C "${W:?}" ls-files -s ops/bootstrap.py ops/new-project.py packages/harness/tests/test_doc_rules.py | cut -c1-6`
  Expected (the counts of `git diff --stat` depend on your code, so the paths and modes are the check):
  ```text
  .claude/hooks/session-start.py
  docs/architecture/harness-modules.md
  docs/architecture/harness.md
  docs/architecture/index.md
  docs/exec-plans/tech-debt-tracker.md
  docs/llms.txt
  docs/quality/QUALITY_SCORE.md
  ops/bootstrap.py
  ops/new-project.py
  ops/tests/test_bootstrap_steps.py
  ops/tests/test_container.py
  packages/harness/tests/test_doc_rules.py
  packages/harness/tests/test_setup.py
  100755
  100755
  100644
  ```
  Then append `Task 9: done — <sha7 of HEAD>` to `build-log-c.md` in the run folder, as your assignment says.

## Tests in full (Step 1; measured on f70e84c, ruff 0.16.10 check and format clean)
`packages/harness/tests/test_doc_rules.py` (new, in full):

```python
"""Two documentation rules the tracker sweep closed (manager-build Task 9). TD-012: a new decision record is listed by
its line in docs/decisions/README.md, the folder index docs/llms.txt links (ADR-0026, AGENTS.md:33); the adr skill's
step 3 writes that line and the docs-gardening audit asks for one of the two places docs-check accepts. TD-009: every
page under docs/architecture/ stays at most 12,000 bytes (Global Constraint 4), the harness's module map on a page of
its own."""

from __future__ import annotations

import re
from pathlib import Path

from harness import catalog

REPO = Path(__file__).resolve().parents[3]
ARCH = REPO / "docs" / "architecture"


def adr_step(n: int) -> str:
    """Step n of the adr skill, one line."""
    text = (REPO / ".claude" / "skills" / "adr" / "SKILL.md").read_text(encoding="utf-8")
    return next(line for line in text.splitlines() if line.startswith(f"{n}. "))


def test_the_line_the_adr_skill_writes_is_a_line_docs_check_lists(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(catalog, "render_catalog", lambda root: "catalog\n")
    monkeypatch.setattr(catalog.stagemap, "docs_problems", lambda root: [])
    third = adr_step(3)
    assert "`docs/decisions/README.md`" in third and "llms.txt" not in third
    found = re.search(r"\(`(- \[ADR-NNNN Title\]\(NNNN-\$0\.md\): one sentence)`\)", third)
    assert found, third
    line = found.group(1).replace("NNNN", "0031").replace("$0", "one-rule")
    readme = "# Decisions\n\n- [ADR-0030 English only](0030-english-only.md): e\n"
    files = {
        "docs/generated/role-types.md": "catalog\n",
        "docs/llms.txt": "- [Decisions](decisions/README.md): every record, one line each\n",
        "docs/decisions/README.md": readme + line + "\n",
        "docs/decisions/0030-english-only.md": "# English only\n",
        "docs/decisions/0031-one-rule.md": "# One rule\n",
    }
    for rel, text in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text, encoding="utf-8")
    assert catalog.docs_check(tmp_path)["problems"] == []
    (tmp_path / "docs" / "decisions" / "README.md").write_text(readme, encoding="utf-8")
    assert catalog.docs_check(tmp_path)["problems"] == ["docs/llms.txt: decisions/0031-one-rule.md is not listed"]


def test_the_docs_gardening_audit_asks_for_the_two_places_docs_check_accepts() -> None:
    text = " ".join((REPO / ".claude" / "workflows" / "docs-gardening.js").read_text(encoding="utf-8").split())
    clause = text[text.index("(3) ") :].split(". ", 1)[0]
    assert "docs/llms.txt" in clause and "the folder README.md that docs/llms.txt links" in clause
    assert ".summary.md" in clause and ".<language>.md" not in clause


def test_every_architecture_page_is_at_most_12000_bytes() -> None:
    sizes = {p.name: len(p.read_bytes()) for p in sorted(ARCH.glob("*.md"))}
    assert "harness.md" in sizes and "harness-modules.md" in sizes
    assert {name: size for name, size in sizes.items() if size > 12_000} == {}


def test_the_module_map_is_a_page_of_its_own_that_the_architecture_links() -> None:
    page = (ARCH / "harness.md").read_text(encoding="utf-8")
    modules = (ARCH / "harness-modules.md").read_text(encoding="utf-8")
    assert "(harness-modules.md)" in page and "| Module | Owns |" not in page
    assert modules.startswith("# Harness module map\n") and "(harness.md)" in modules
    rows = [line for line in modules.splitlines() if line.startswith("| `")]
    assert len(rows) == 22 and rows[0].startswith("| `cli.py` |") and rows[-1].startswith("| `pipeline_report.py` |")
```

`ops/tests/test_container.py` (one import, one test; the diff applies to f70e84c, `patch -p1 --dry-run`):

```diff
diff --git a/ops/tests/test_container.py b/ops/tests/test_container.py
index 9879880..b4fe7ee 100644
--- a/ops/tests/test_container.py
+++ b/ops/tests/test_container.py
@@ -5,6 +5,7 @@ without the marker; a second run changes nothing."""
 
 from __future__ import annotations
 
+import importlib.util
 import shutil
 import subprocess
 import sys
@@ -68,3 +69,24 @@ def test_a_runs_folder_without_the_marker_is_refused(tmp_path: Path) -> None:
     assert r.returncode == 1
     assert MARKER in r.stdout
     assert not (tmp_path / "box" / "experiments").exists()
+
+
+def test_new_project_with_container_gives_the_folders_container_py_gives(tmp_path: Path) -> None:
+    """The owner's final plan, 0.6: `ops/new-project.py --container` lays a new project out as `ops/container.py`
+    does, the hand-over notes' `docs/handoff/` beside the checkout, not inside it."""
+    template = tmp_path / "template"
+    for rel in ("ops/new-project.py", "docs/template/variables.yaml", "docs/template/VERSION"):
+        (template / rel).parent.mkdir(parents=True, exist_ok=True)
+        shutil.copy2(REPO / rel, template / rel)
+    subprocess.run(["git", "init", "-q"], cwd=template, check=True)
+    subprocess.run(["git", "add", "-A"], cwd=template, check=True)
+    box = tmp_path / "box"
+    command = [sys.executable, str(template / "ops" / "new-project.py"), str(box), "repo_name=demo", "--container"]
+    done = subprocess.run([*command, "--no-setup"], capture_output=True, text=True, check=False)
+    assert done.returncode == 0, done.stdout + done.stderr
+    spec = importlib.util.spec_from_file_location("ops_container_folders", REPO / "ops" / "container.py")
+    module = importlib.util.module_from_spec(spec)
+    spec.loader.exec_module(module)
+    assert "docs/handoff/" in module.FOLDERS
+    assert [folder for folder in module.FOLDERS if not (box / folder).is_dir()] == []
+    assert (box / "demo" / "ops" / "new-project.py").is_file() and not (box / "demo" / "docs" / "handoff").exists()
```

`ops/tests/test_bootstrap_steps.py` (the fixture patches `USER_SKILLS` with `raising=False`; three tests changed by name: `test_a_fresh_checkout_gets_just_its_hooks_and_its_sandbox_then_its_first_graph` and `test_on_macos_the_seatbelt_is_checked_and_a_hooks_folder_of_the_checkout_is_kept` gain `graphify-skill` at the end of their step list, `test_a_checkout_that_is_set_up_installs_neither_again` gains the installed graphify skill so its list stays; four tests added; the diff applies to f70e84c):

```diff
diff --git a/ops/tests/test_bootstrap_steps.py b/ops/tests/test_bootstrap_steps.py
index a405156..2063fee 100644
--- a/ops/tests/test_bootstrap_steps.py
+++ b/ops/tests/test_bootstrap_steps.py
@@ -5,6 +5,7 @@ packages/harness/tests/test_setup.py loads it; the order is then tested offline.
 
 import importlib.util
 import io
+import os
 import sys
 from pathlib import Path
 from types import SimpleNamespace
@@ -35,6 +36,7 @@ def boot(tmp_path, monkeypatch):
 
     monkeypatch.setattr(module, "ROOT", root)
     monkeypatch.setattr(module, "LOCAL_BIN", tmp_path / "bin")
+    monkeypatch.setattr(module, "USER_SKILLS", tmp_path / "home" / ".claude" / "skills", raising=False)
     monkeypatch.setattr(module, "step", step)
     monkeypatch.setattr(module, "uv_path", lambda: Path("/opt/bin/uv"))
     monkeypatch.setattr(module, "install_plugins", lambda log: [])
@@ -51,13 +53,16 @@ def test_a_fresh_checkout_gets_just_its_hooks_and_its_sandbox_then_its_first_gra
 
     assert module.setup(io.StringIO()) == []
 
-    assert [name for name, _ in rec.calls] == ["workspace", "just", "hooks", "code-intel", "sandbox", "graph"]
+    names = ["workspace", "just", "hooks", "code-intel", "sandbox", "graph", "graphify-skill"]
+    assert [name for name, _ in rec.calls] == names
     commands = dict(rec.calls)
     assert commands["just"] == ["/opt/bin/uv", "tool", "install", "rust-just==1.58.0"]
     assert commands["hooks"] == ["git", "-C", str(rec.root), "config", "--local", "core.hooksPath", ".githooks"]
     assert commands["sandbox"] == [sys.executable, str(rec.root / "ops" / "machine-setup.py"), "--auto"]
     assert commands["graph"] == ["bash", str(rec.root / "ops" / "graph.sh")]
-    for text in ("rust-just", "core.hooksPath", "machine-setup.py --auto", "sandbox-exec", "ops/graph.sh"):
+    assert commands["graphify-skill"] == ["/opt/bin/graphify", "install", "--platform", "claude"]
+    texts = ("rust-just", "core.hooksPath", "machine-setup.py --auto", "sandbox-exec", "ops/graph.sh")
+    for text in (*texts, "graphify install --platform claude", "~/.claude/skills/running-specagent-pipelines"):
         assert text in module.__doc__, text
 
 
@@ -67,6 +72,8 @@ def test_a_checkout_that_is_set_up_installs_neither_again(boot, tmp_path):
     (rec.root / "wiki" / "graph" / "index.md").write_text("# Code graph\n", encoding="utf-8")
     (tmp_path / "bin").mkdir()
     (tmp_path / "bin" / "just").write_text("", encoding="utf-8")
+    (tmp_path / "home" / ".claude" / "skills" / "graphify").mkdir(parents=True)
+    (tmp_path / "home" / ".claude" / "skills" / "graphify" / "SKILL.md").write_text("# graphify\n", encoding="utf-8")
     rec.hooks = ".githooks"
 
     assert module.just_path() == tmp_path / "bin" / "just"
@@ -103,7 +110,7 @@ def test_on_macos_the_seatbelt_is_checked_and_a_hooks_folder_of_the_checkout_is_
 
     assert module.setup(log) == []
 
-    assert [name for name, _ in rec.calls] == ["workspace", "just", "code-intel", "graph"]
+    assert [name for name, _ in rec.calls] == ["workspace", "just", "code-intel", "graph", "graphify-skill"]
     assert "hooks: core.hooksPath is .husky/_, kept" in log.getvalue()
     del rec.tools["sandbox-exec"]
     assert module.setup(io.StringIO()) == ["sandbox"]
@@ -132,3 +139,76 @@ def test_a_folder_that_is_not_the_top_of_a_repository_gets_no_hooks_path(boot):
 
         assert "hooks" not in [name for name, _ in rec.calls]
         assert f"hooks: {rec.root} is not the top of a git repository yet" in log.getvalue()
+
+
+def test_graphifys_skill_is_installed_only_where_graphify_is_and_its_skill_is_not(boot, tmp_path):
+    module, rec = boot
+    skill = tmp_path / "home" / ".claude" / "skills" / "graphify"
+    skill.mkdir(parents=True)  # a folder without SKILL.md is no skill
+
+    assert module.setup(io.StringIO()) == []
+    assert dict(rec.calls)["graphify-skill"] == ["/opt/bin/graphify", "install", "--platform", "claude"]
+
+    (skill / "SKILL.md").write_text("# graphify\n", encoding="utf-8")
+    rec.calls = []
+    assert module.setup(io.StringIO()) == []
+    assert "graphify-skill" not in [name for name, _ in rec.calls]
+
+    (skill / "SKILL.md").unlink()
+    del rec.tools["graphify"]
+    rec.calls = []
+    assert module.setup(io.StringIO()) == []
+    assert "graphify-skill" not in [name for name, _ in rec.calls]
+
+
+def test_a_failed_graphify_skill_install_is_not_a_failed_setup(boot):
+    module, rec = boot
+    rec.fail = {"graphify-skill"}
+
+    assert module.setup(io.StringIO()) == []
+    assert "graphify-skill" in [name for name, _ in rec.calls]
+
+
+def test_the_user_level_pipeline_skill_becomes_a_link_to_the_checkouts_once(boot, tmp_path):
+    module, rec = boot
+    source = rec.root / ".claude" / "skills" / "running-specagent-pipelines"
+    source.mkdir(parents=True)
+    (source / "SKILL.md").write_text("---\nname: running-specagent-pipelines\n---\n", encoding="utf-8")
+    link = tmp_path / "home" / ".claude" / "skills" / "running-specagent-pipelines"
+    log = io.StringIO()
+
+    assert module.setup(log) == []
+
+    assert link.is_symlink() and os.readlink(link) == str(source)
+    assert (link / "SKILL.md").read_text(encoding="utf-8") == "---\nname: running-specagent-pipelines\n---\n"
+    assert f"skill: {link} -> {source}\n" in log.getvalue()
+    again = io.StringIO()
+    assert module.setup(again) == []
+    assert os.readlink(link) == str(source) and f"skill: {link}" not in again.getvalue()
+
+
+def test_an_existing_link_or_copy_of_the_pipeline_skill_is_kept_and_a_checkout_without_it_links_nothing(boot, tmp_path):
+    module, rec = boot
+    link = tmp_path / "home" / ".claude" / "skills" / "running-specagent-pipelines"
+    module.link_user_skill(io.StringIO())
+    assert not link.exists() and not link.is_symlink()
+    source = rec.root / ".claude" / "skills" / "running-specagent-pipelines"
+    source.mkdir(parents=True)
+    link.parent.mkdir(parents=True)
+    elsewhere, gone = tmp_path / "template-skill", tmp_path / "gone"
+    elsewhere.mkdir()
+    dangling = f"skill: {link} -> {gone} is dangling, kept; ln -sfn {source} {link} makes it the link\n"
+    for target, said in ((elsewhere, ""), (gone, dangling)):  # a live link stays quiet, a dangling one is named
+        link.symlink_to(target, target_is_directory=True)
+        out = io.StringIO()
+        module.link_user_skill(out)
+        assert link.is_symlink() and os.readlink(link) == str(target) and out.getvalue() == said
+        link.unlink()
+    link.mkdir()
+    (link / "mine.md").write_text("kept\n", encoding="utf-8")
+    log = io.StringIO()
+
+    module.link_user_skill(log)
+
+    assert not link.is_symlink() and (link / "mine.md").read_text(encoding="utf-8") == "kept\n"
+    assert f"skill: {link} is a copy, kept;" in log.getvalue() and f"ln -s {source} {link}" in log.getvalue()
```

`packages/harness/tests/test_setup.py` (C21: `test_the_setup_message_names_every_step_of_the_bootstrap`, its step
list gains the two new steps and one assert the `~/.claude/CLAUDE.md` clause; the diff applies to f70e84c):

```diff
diff --git a/packages/harness/tests/test_setup.py b/packages/harness/tests/test_setup.py
index 6c449f8..62a55ed 100644
--- a/packages/harness/tests/test_setup.py
+++ b/packages/harness/tests/test_setup.py
@@ -320,5 +320,6 @@
     home.mkdir()
     message = run_session_start(root, home, env_file)["systemMessage"]
     steps = ("uv", "the workspace", "`just`", "the git hooks", "the plugins", "the language servers", "the sandbox",
-             "the first code graph")  # fmt: skip
+             "the first code graph", "graphify's skill", "the user-level pipeline skill")  # fmt: skip
     assert [step for step in steps if step not in message] == [], message
+    assert "appends a block to ~/.claude/CLAUDE.md" in message, message
```

## Deferred (with the reason)
Each item is real; Task 11 turns each into a tracker row (Contracts).
- graphify's PreToolUse hook, the second half of TD-007. It is project-scoped (`graphify install --project`, graphify
  0.9.64 `install.py:744`) and would edit the tracked `.claude/settings.json`. Bootstrap's step 4 git hooks already
  refresh the graph after each commit (departure 4). A later run decides whether sessions need the hook for graph
  queries.
- `CLAUDE_CONFIG_DIR`. graphify honours it (`install.py:132-133`), but bootstrap looks for both skills under
  `~/.claude/skills/` only. Claude Code's handling of the variable could not be checked here: `claude` is denied in the
  planner's sandbox (departure 6).
- The score of `packages/harness` in `docs/quality/QUALITY_SCORE.md`. Line 6 keeps 2: the file changes a score only
  with a linked measurement (its line 10), and Task 9 runs only its own tests (C503's rule). The release review scores
  it (departure 7).
- The module map has no row for `gitcall.py`, `leftovers.py` or `pause.py`, because the table moved verbatim (copy tasks
  stay thin, `lessons.md` Read first 8). The next edit of the map adds them.

## Verified
- The base: `git diff --stat f70e84c <rev> -- <Step 0's paths>` prints nothing for `<rev>` = de15a76 (the plan
  branch) and `feat/manager-build-c` (`git log -1`: f70e84c), run 2026-10-29; the index's rows 6 and 8 list none of
  those paths (`00-index.md:109`, `:111` at de15a76).
- The figures, measured on scratch copies (`scratch/planner-c/t9/`: `tree` = f70e84c's files with the tests, `green`
  = the full scratch build): the three files red `9 failed, 11 passed` on `tree` (the nine names of Step 1) and
  `20 passed` on `green`. Per file on `green`: `test_container.py` 5, `test_bootstrap_steps.py` 11, `test_doc_rules.py`
  4. `-k 'adr_skill or docs_gardening'` on `test_doc_rules.py` alone gives `2 passed, 2 deselected` on `tree`.
- The 23 wrong versions (`scratch/planner-c/t9/wrong.py`, `CASES`) are all red, `23 of 23 red`, re-run 2026-10-29:
  W1-W3 for `new-project.py` (no `docs/handoff/`; the folder inside the checkout; no `parents=True`), W4-W15 for
  `bootstrap.py` (the skill's failure counted; a folder checked instead of `SKILL.md`; graphify by bare name; no
  `--platform`; a relative link; a copy instead of a link; the copy checked before the link; a dangling link replaced;
  a link made without the source; the link not called from `setup`; the copy replaced; a relink on every run), and
  W16a-W22 for the documents (the adr step 3 sent to `llms.txt`; the clause reverted; the line form with a path; the
  clause's old summary name; docs-check without L2; `harness.md` not shortened; a row dropped; no back-link).
- C20/A8 (plan fixer; `scratch/plan-fixer/t9/c20_red.py` on a copy of `green` with the fix): the kept-link test
  gives `1 failed` on each of five versions (the plan before C20, a dangling link kept silently; a live link named as
  dangling; a dangling link replaced; one named without the command; one given the copy's `mv`/`ln -s` command) and
  `1 passed` on the fix; the three files `20 passed`; ruff 0.16.10 check and format clean on both files;
  `link_user_skill` 20 lines, `install_graphify_skill` 5, `setup` 43 (`ast`). `Path.exists()` follows the link, so it
  is False for a dangling one, and `Path.is_symlink()` is True for it (Python 3.12, `pathlib`); `ln --help` (GNU
  coreutils): `-s` symbolic, `-f` removes an existing destination, `-n` treats a link to a folder as a file.
- C21 (plan fixer; `scratch/plan-fixer/t9/c21_edit.py` on `green`, whose hook and `test_setup.py` are f70e84c's):
  with the test change, `test_setup.py` gives `1 failed, 13 passed` on f70e84c's message and on two wrong ones (the
  two steps without the `~/.claude/CLAUDE.md` clause; graphify's skill and the clause without the pipeline skill
  link), and `14 passed` on Step 3's message; the four test files `34 passed` on `green`; ruff 0.16.10 on Step 7's
  seven files `All checks passed!` and `7 files already formatted`. The new message lines are at most 117
  characters (the hook's lines 66 and 154, 121 and 124, are f70e84c's own). The diff applies to f70e84c
  (`git apply --numstat`: `2 1 packages/harness/tests/test_setup.py`) and rebuilds the tested file (`cmp`).
  `git diff --stat f70e84c <rev>` on the two paths prints nothing at aafa868 (the plan branch) and 22eca3d
  (`feat/manager-build-c`); no index row named either before C21 (`grep -n 'session-start\|test_setup'
  00-index.md` at aafa868). `start_setup` (`session-start.py:107-109` at f70e84c) starts `ops/bootstrap.py` in the
  background when uv or the workspace is missing; the two steps run after `build_graph` (Interfaces, `setup`), so
  they close the message's list. `.claude/hooks` is closed to shell commands, open to Edit (`_common.md:124-126`).
- The diffs apply cleanly to f70e84c: `git apply --numstat` gives `22 0 ops/tests/test_container.py` and
  `83 3 ops/tests/test_bootstrap_steps.py` (83 since C20). The scratch commit (`scratch/planner-c/t9/base`, 7d53790) changes the eleven
  paths of Step 7 other than C21's two (the hook and `test_setup.py`).
- Step 5's command rebuilds the scratch build's `harness-modules.md` and `harness.md` byte for byte (`cmp`). Sizes at
  f70e84c are `harness.md` 14,439, `docs/llms.txt` 6,279 and `index.md` 725 (`git show f70e84c:<path> | wc -c`); after
  Step 5 they are 11,241, 6,405 and 828, with `harness-modules.md` at 3,422 (`wc -c`). `harness.md:122` is
  `## Module map (...)`, :123-146 the table (heading row, separator, 22 rows), :148 `## Adding a command`.
  `INDEX_MAX_BYTES = 12_000` is at `catalog.py:59`.
- TD-001: `write_handoff` is at `state.py:588` and `validate_repository` at `catalog.py:222` (`grep -n`, de15a76 equal to
  f70e84c). They run as `harness handoff` (`cli.py:408`) and `harness validate` (`cli.py:421`). Step 6's four tests give
  `4 passed` on `tree` and on `green`.
- TD-012: `.claude/skills/adr/SKILL.md:12` (step 3, `docs/decisions/README.md`), `.claude/workflows/docs-gardening.js:20`
  (clause (3), `.summary.md`), `AGENTS.md:33`, `catalog.listed` at `catalog.py:277` and `docs_check` at `catalog.py:324`.
  The patch exists at `experiments/template-core/leftovers/verify-worktree-uncommitted.patch` (`ls`).
- Bootstrap at f70e84c: `PLATFORM` is at :42, `step(name, cmd, log, env=None) -> bool` at :73 and `JUST = "rust-just==1.58.0"`
  at :41, the pin added by 81fd5c1. `os`, `shutil` and `Path` are imported (`grep -n`). After the change
  `grep -c sleep` and `grep -cE '^\s*while '` both give 0 (the scratch build).
- `ops/new-project.py:124-128` (f70e84c) makes `runs/` and `experiments/` only. `ops/container.py:20` is `FOLDERS`.
  `packages/harness/tests/test_documents.py:43-45` needs "wherever the shell stands" (`harness.md:56`, kept by the move).
- graphify 0.9.64 (pipx venv `graphifyy`). The usage line is `graphify install [--project] [--strict] [--platform P|P]`
  (`install.py:741`). The Claude skill goes to `Path.home() / ".claude" / "skills" / "graphify" / "SKILL.md"`
  (`install.py:399`, `CLAUDE_CONFIG_DIR` at :132-133), and the `~/.claude/CLAUDE.md` block is at `install.py:698-714`.
- This machine: `~/.claude/skills/running-specagent-pipelines` is a link to the template checkout's skill, made by
  hand on 2026-10-29 at 11:08, next to `running-specagent-pipelines.old` and `graphify/` (`ls -l`). `just` 1.59.0 is
  installed outside bootstrap (`uv tool list`: `rust-just v1.59.0`; `command -v just`: `/home/tite/.local/bin/just`).
- The command form: `uv run pytest -q -p no:cacheprovider ops/tests/test_container.py ops/tests/test_bootstrap_steps.py`
  run from the plan checkout (f70e84c's files) gives `11 passed`.
- ruff 0.16.10 (`.venv/bin/ruff --version`) on `green`'s five files prints `All checks passed!` and
  `5 files already formatted`. Lines 4, 7 and 131 of `ops/new-project.py` are 121 characters at f70e84c. In the scratch
  commit no added Python line is over 120 (`git show -U0 | grep '^+[^+]' | awk 'length > 121'`: none).
- Modes at f70e84c (`git ls-tree`): `ops/bootstrap.py` and `ops/new-project.py` are 100755, the two test files 100644.
  The scratch commit adds `test_doc_rules.py` as 100644 and adds no shebang (`lessons.md` 22:23).
- `git diff --name-only <BASE> HEAD` prints the whole change's paths, sorted, with no blank first line, and
  `git diff --cached -U0 <BASE>` sees a line that a WIP commit added, which `git diff --cached` and `git show HEAD`
  miss (git 2.43.0, `scratch/plan-fixer/t9/base_probe.sh`: a 130-character line in a WIP commit counts 1 from
  `BASE` and 0 from `HEAD`).
- The subject is Global Constraint 12's form, `feat(manager): Task N — <title>` (`00-index.md:64`; lessons 23:45;
  R3 of the Task 6 diff); the built Tasks 1-4 and 6 committed so (`git log -1 --format=%s` of cabb8a3, 1963628,
  73b2b0a, 177c331, 22eca3d), and no hook checks a message (`.githooks` at f70e84c: post-checkout, post-commit,
  post-merge).
- The tracker check: `sed 's/|[^|]*|$//'` strips only the last cell. The four rows keep every other cell from `tree` to
  `green` (`first-cells-kept`). `git diff --numstat` gives 4/4 for the tracker and 1/1 for `QUALITY_SCORE.md`.
