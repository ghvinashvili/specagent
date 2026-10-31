# Task 3 — The plan file split: steps and blocks

builder: b
depends_on: —
milestone: M2

## Goal
`task-NN.md` keeps the steps; every fenced block longer than 10 lines moves to `task-NN.code.md` under a heading
`## Block <id>`, and the step names it (`Block 3b`). `harness plan-lint` checks the pair. The briefs give each role its
reading rule: the critic reads the steps file whole and every test block; the builder and the verifier open a block
when a step names it. Tests stay written in full by the planner; texts become a facts list plus a test, and the builder
writes the prose.

**Files:**
- Modify: `packages/harness/src/harness/plans.py`, `packages/harness/tests/test_plan_lint.py`
- Modify: `docs/exec-plans/active/README.md` (the form of a plan folder)
- Modify (under `.claude/skills/running-specagent-pipelines/example/`): `planner-assignment.md` ("The plan: part
  files"), `critic-assignment.md` (reading rule), `builder-a-assignment.md`, `builder-b-assignment.md`,
  `verifier-assignment.md` (reading rule), `common.md` ("Context": one sentence)
- Create: `wiki/decisions/plan-steps-and-blocks-in-two-files.md`, `wiki/decisions/plan-steps-and-blocks-in-two-files.summary.md`
- Modify: `wiki/index.md` (one line at the end of `## Decisions`), `wiki/log.md` (one section at the end)

**Interfaces:**
- Consumes: `plans._lint_folder(folder)`, `plans._task_problems(...)`, `plans.TASK_FILE`, `plans.count_lines`.
- Produces: `plans.CODE_FILE = re.compile(r"task-(\d{2,})\.code\.md")`; `plans.BLOCK_HEADING = re.compile(r"^## Block
  ([0-9]+[a-z]?)\s*$", re.MULTILINE)`; `plans.BLOCK_REF = re.compile(r"\bBlock ([0-9]+[a-z]?)\b")`;
  `plans.code_problems(folder, name, number, tasks) -> list[str]`: rules 1-4 for one task number, `name` its
  `task-NN.code.md`, which may be missing (then it defines no block); problems named `<plan>/task-NN.code.md: ...`
  and `<plan>/task-NN.md: names Block ...`.
- The entry (C11): every entry of `plan_lint`'s `plans` gains `"blocks": <n>`, the `## Block` headings across the
  folder's code files (a heading twice counts twice; rule 3 reports it). The no-index entry (`plans.py:52`) carries it
  too, counted from the files like `written`, and the docstring's key list (`:69`) names it. `test_plan_lint.py:55`
  pins the whole result without the key, so Step 1 rewrites it.
- Where the rules run: after the task rules (`plans.py:62-63`); a folder without an index or without a task order
  reports that problem alone, as today (`:52`, `:57`). Step 1's last test pins both.

## The rules plan-lint applies
1. A code file whose task file is missing: `task-NN.code.md: no task-NN.md beside it`, its only problem (rules 3 and 4
   do not read it; Step 1's second test counts four problems).
2. A block named in `task-NN.md` (`Block 3b`) with no `## Block 3b` in `task-NN.code.md`: `task-NN.md: names Block 3b,
   not in task-NN.code.md`, once per id. Scope (C10): every task file of a plan folder that holds at least one
   `task-NN.code.md`, so a task whose code file was never written is a problem; a folder with no code file is linted
   as before. Both active folders name blocks and hold no code file (`manager-build/task-11.md:384`, `:387`, `:398`,
   `:433`, `:435`; this file's examples), so both stay green (Step 6); A8's test pins both sides.
3. A block heading twice in one code file: `task-NN.code.md: Block 3b twice`, once per id.
4. A block heading that no step names: a problem too (`task-NN.code.md: Block 6a is named by no step`), so a code
   file carries nothing the steps do not use.
5. The code file has no line limit; the steps file keeps `MAX_TASK_LINES`. Block ids are `<step number><letter>`
   (`1a`, `12c`); a reference inside a fence of the steps file counts like one in prose (the steps file has no fence
   longer than 10 lines, so a reference there is always a step's); A9's test pins it.

- [ ] **Step 1: Write the failing tests**

In `test_plan_lint.py` (C12: the helper and every test in full; each `write_text` names its encoding, as the file's
other tests do), `make_plan` (`:32-40`) becomes:

```python
def make_plan(
    tmp_path: Path, index: str = INDEX, tasks: tuple[int, ...] = (1, 2, 3), code: dict[int, str] | None = None
) -> Path:
    """A repository root with the plan folder `demo`: its index, the task and code files given, the summary."""
    folder = tmp_path / "repo" / "docs" / "exec-plans" / "active" / "demo"
    folder.mkdir(parents=True)
    (folder / "00-index.md").write_text(index, encoding="utf-8")
    for n in tasks:
        (folder / f"task-{n:02d}.md").write_text(f"# Task {n} — step {n}\n\nbuilder: a\n", encoding="utf-8")
    for n, text in (code or {}).items():
        (folder / f"task-{n:02d}.code.md").write_text(text, encoding="utf-8")
    (folder / "demo.summary.md").write_text("A summary.\n", encoding="utf-8")
    return tmp_path / "repo"
```

`test_a_plan_whose_index_names_every_task_file_passes` (`:52-55`) pins the whole result, so it becomes (C11):

```python
def test_a_plan_whose_index_names_every_task_file_passes(tmp_path):
    root = make_plan(tmp_path)
    (plan_dir(root) / "notes.md").write_text("# Notes\n", encoding="utf-8")  # other files may sit beside the tasks
    assert plans.plan_lint(root) == {
        "ok": True,
        "plans": [{"plan": "demo", "tasks": 3, "written": 3, "blocks": 0}],
        "problems": [],
    }
```

After the last test of the file, six new tests: the three rule tests, A8's (rule 2's scope), A9's (a reference inside
a short fence) and the entry of a folder without an index (C11):

```python
def test_a_code_file_beside_its_task_passes_and_counts_its_blocks(tmp_path):
    root = make_plan(tmp_path, code={1: "## Block 1a\n```python\nx = 1\n```\n"})
    (plan_dir(root) / "task-01.md").write_text(
        "# Task 1 — step 1\n\nbuilder: a\n\n- [ ] Step 1: write Block 1a\n", encoding="utf-8"
    )
    d = plans.plan_lint(root)
    assert d["ok"] and d["plans"][0]["blocks"] == 1


def test_an_orphan_code_file_a_missing_a_double_and_an_unnamed_block_are_one_problem_each(tmp_path):
    code = {1: "## Block 1a\n\n## Block 1a\n\n## Block 9z\n", 4: "## Block 4a\n"}
    root = make_plan(tmp_path, code=code)
    (plan_dir(root) / "task-01.md").write_text(
        "# Task 1 — step 1\n\n- [ ] Step 1: Block 1a and Block 1b\n", encoding="utf-8"
    )
    problems = plans.plan_lint(root)["problems"]
    assert "demo/task-04.code.md: no task-04.md beside it" in problems
    assert "demo/task-01.md: names Block 1b, not in task-01.code.md" in problems
    assert "demo/task-01.code.md: Block 1a twice" in problems
    assert "demo/task-01.code.md: Block 9z is named by no step" in problems
    assert len(problems) == 4


def test_a_code_file_is_not_a_task_file_and_has_no_line_limit(tmp_path):
    root = make_plan(tmp_path, code={1: "## Block 1a\n" + "x\n" * 2000})
    (plan_dir(root) / "task-01.md").write_text("# Task 1 — step 1\n\nBlock 1a\n", encoding="utf-8")
    d = plans.plan_lint(root)
    assert d["ok"] and d["plans"][0]["written"] == 3


def test_an_old_plan_naming_a_block_stays_green_and_a_forgotten_code_file_is_a_problem(tmp_path):
    old = make_plan(tmp_path / "old")
    (plan_dir(old) / "task-02.md").write_text(
        "# Task 2 — step 2\n\n- [ ] Step 1: Block 7a goes into README.md\n", encoding="utf-8"
    )
    d = plans.plan_lint(old)
    assert d["ok"] and d["problems"] == [] and d["plans"][0]["blocks"] == 0
    new = make_plan(tmp_path / "new", code={1: "## Block 1a\n"})
    (plan_dir(new) / "task-01.md").write_text("# Task 1 — step 1\n\n- [ ] Step 1: Block 1a\n", encoding="utf-8")
    (plan_dir(new) / "task-02.md").write_text("# Task 2 — step 2\n\n- [ ] Step 1: Block 2a\n", encoding="utf-8")
    assert plans.plan_lint(new)["problems"] == ["demo/task-02.md: names Block 2a, not in task-02.code.md"]


def test_a_block_named_inside_a_short_fence_of_the_steps_file_counts(tmp_path):
    root = make_plan(tmp_path, code={1: "## Block 1a\n"})
    (plan_dir(root) / "task-01.md").write_text("# Task 1 — step 1\n\n```\nBlock 1a\n```\n", encoding="utf-8")
    d = plans.plan_lint(root)
    assert d["ok"] and d["problems"] == [] and d["plans"][0]["blocks"] == 1


def test_a_folder_without_an_index_counts_its_blocks_and_reports_only_the_index(tmp_path):
    root = make_plan(tmp_path, code={1: "## Block 1a\n\n## Block 1b\n"})
    (plan_dir(root) / "00-index.md").unlink()
    assert plans.plan_lint(root) == {
        "ok": False,
        "plans": [{"plan": "demo", "tasks": 0, "written": 3, "blocks": 2}],
        "problems": ["demo: no 00-index.md"],
    }
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest -q packages/harness/tests/test_plan_lint.py`
Expected: 6 failed, 9 passed (C12; measured with these tests on the base `plans.py`): the rewritten `:55` test, the
first two rule tests, A8's, A9's and the no-index test fail (no `blocks` key; the second on its first assert, as the
base reports no problem); `test_a_code_file_is_not_a_task_file_and_has_no_line_limit` passes already, because
`TASK_FILE.fullmatch` (`plans.py:10`, `:49`) skips a code file, and stays to guard rule 5 against later code.

- [ ] **Step 3: Implement the rules in `plans.py`**

`code_problems` as named in Interfaces: for one task number, rule 1 alone when the code file has no task file, else
rules 2-4 for the pair. `_lint_folder` collects the code files (`CODE_FILE.fullmatch`) and counts `blocks` before the
index check (`plans.py:50-52`), so both entries carry it; when the folder holds a code file (rule 2's scope) it calls
`code_problems` for every number of a task file or a code file, ascending, after the task rules (`:62-63`). The
docstring of `plan_lint` (`:69`) names `blocks` with the other three keys.

- [ ] **Step 4: Run them to verify they pass**

Run: `uv run pytest -q packages/harness/tests/test_plan_lint.py`
Expected: 15 passed (the nine old, `:55` rewritten, and Step 1's six).

- [ ] **Step 5: The plan form and the briefs**

`docs/exec-plans/active/README.md`: one paragraph after the first: the optional `task-NN.code.md`, the heading form,
rules 1-5 in one sentence each. `example/planner-assignment.md`, "The plan: part files": the `task-NN.md` item says
"every fenced block longer than 10 lines goes to `task-NN.code.md` under `## Block <step><letter>` and the step names
it as `Block 3b`; tests in full stay yours; a text (changelog entry, decision page, documentation prose) is a facts
list in the step and a test that pins the facts, and the builder writes the prose". `critic-assignment.md`, the
coverage round: "read `task-NN.md` whole (by ranges), then every test block of `task-NN.code.md` in full, and another
block only when a finding needs it". `builder-a/b-assignment.md` and `verifier-assignment.md`: "open a block of
`task-NN.code.md` when the step names it (`grep -n '^## Block 3b' ...` then `sed -n`), never the file whole".
`common.md`, "Context": "A plan's code file is read by block, never whole."

The decision page (spec Decided 4, `docs/design-docs/pipeline-fold.md:101-116`; one decision per page, in the commit
with its code, `_common.md`, "Documentation with the code"): `wiki/decisions/plan-steps-and-blocks-in-two-files.md`,
titled "The plan file is
split: steps in one file, blocks in another", front matter with the keys of `wiki/decisions/skill-script-pages.md:1-13`
(`type: decision`, `status: draft`, `decided: 2026-10-30`, `by: owner`, `decision_status: decided`, `scope: global`);
the decision: `task-NN.md` keeps the steps, every fenced block over 10 lines goes to `task-NN.code.md` under `## Block
<id>`, and `harness plan-lint` checks the pair; `why` from the spec's Intent (`:8-25`); `would_change_if` from
Measurement 3 (`:147-148`: the measurement run loses quality and this pair is unfolded); under 12,000 bytes. Its
`.summary.md`: four lines, the first `Decision (owner, 2026-10-30): ...`. `wiki/index.md`: one line at the end of
`## Decisions`, in the form of `wiki/index.md:35`. `wiki/log.md`: a section at the end in the form of
`wiki/log.md:48-63`: `## 2026-10-30 pages written with Task 3 of the pipeline-fold run`, `- commit: Task 3 of the
pipeline-fold run`, `- created: decisions/plan-steps-and-blocks-in-two-files.md`, `- updated: index.md`. Both files are
index-like: a task appends its own lines at the end and never reorders another task's; Task 2 (lane a) appends to both
in parallel and the main session keeps both lanes' lines at the merge (the rule of the manager-build run,
`lessons.md`, 22:45 UTC).

Run: `(cd .claude/skills/running-specagent-pipelines/scripts && python3 -m pytest -q tests/test_skill_example.py tests/test_skill_md.py)`
Expected: 18 passed (12 + 6, the counts at 4fbf4cf; every brief still ends with its domain section; the waiters are
unchanged).

- [ ] **Step 6: The task's checks, once, and commit**

Run: `uv run pytest -q packages/harness/tests/test_plan_lint.py`; `uv run ruff check .`; `uv run ruff format --check .`;
`uv run harness plan-lint`; `wc -c wiki/decisions/plan-steps-and-blocks-in-two-files*.md`;
`grep -c 'decisions/plan-steps-and-blocks-in-two-files.md' wiki/index.md wiki/log.md`
Expected: 15 passed (the nine old and Step 1's six); ruff clean; plan-lint `"problems": []` (neither active folder
holds a code file, so rule 2 leaves both as they were and `blocks` is 0 for each); each page under 12,000 bytes;
`wiki/index.md:1`, `wiki/log.md:1`.
Checks once each (`_common.md`, "Checks once each"): the full suites (`uv run pytest -q`, `just validate`, `uv run harness
docs-check`, `uv run harness wiki-lint`) are the verifier's at M2, not this task's; for this task this replaces the
index's Global Constraints line on them (`00-index.md:28-29`). `plan-lint` stays: it is this task's own command.

```bash
git add packages/harness docs/exec-plans/active/README.md .claude/skills/running-specagent-pipelines/example \
  wiki/decisions/plan-steps-and-blocks-in-two-files.md wiki/decisions/plan-steps-and-blocks-in-two-files.summary.md \
  wiki/index.md wiki/log.md
git commit -m "feat(harness): plan-lint checks task-NN.code.md blocks; briefs read a plan's code by block"
```

## Verified (plan fixer, C10-C14, A8-A9, in lane b at f091b2e; `plans.py`, `test_plan_lint.py` as at 63b25a3)
- The entry is built at `plans.py:52` (no index) and `:55` (the no-task-order return `:57` reuses it); the task rules
  run at `:62-63`; the docstring lists the keys at `:69`; `TASK_FILE` (`:10`) is matched with `fullmatch` (`:49`).
- `test_plan_lint.py`: `make_plan` is `:32-40`; nine tests (`:47`, `:52`, `:58`, `:72`, `:84`, `:95`, `:100`, `:111`,
  `:121`); only `:55` asserts an entry (`grep -n '"written"\|== {'`: `:55`, `:113`, `:118`, the last two
  `"plans": []`).
- Step 2's Expected, measured: Step 1's three blocks spliced into a copy of `test_plan_lint.py` and run against the
  base `plans.py`: `6 failed, 9 passed`, on the entry, `KeyError: 'blocks'` and the second test's first assert. The
  blocks pass `ruff format --check` and `ruff check` with `pyproject.toml:17-18` (line length 120).
- Rule 2's scope: `grep -rnoE '\bBlock [0-9]+[a-z]?\b' docs/exec-plans/active/*/task-*.md` hits
  `manager-build/task-11.md:384`, `:387`, `:398`, `:433`, `:435` and this file; `ls docs/exec-plans/active/*/ | grep
  -c 'code\.md'` gives 0; `uv run harness plan-lint` at f091b2e: `"problems": []`; `harness docs-check` adds every
  plan-lint problem (`catalog.py:354`).
- `harness wiki-lint` limits only `TASK_FILE.fullmatch` names (`wiki.py:126-129`): a code file has no limit there
  either (rule 5).

## Deferred
- A converter that splits an existing task file into steps and blocks (the manager-build plan stays as written; it
  is complete).
- Rule 2 in a plan folder with no code file (C10's scope): a plan written in the split form whose every code file is
  missing passes plan-lint; a marker in the index that turns the rule on for such a folder is left for a later plan.
