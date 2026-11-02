"""task_lint.py: a task's Step 0 count, an Expected line for every command, quoted python passing the repo's ruff."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "task_lint.py"
FENCE = "```"
GOOD = f"""# Task 3 — the search step
builder: a
- [ ] **Step 0: Collect the tests at the base**
Run: `uv run pytest --collect-only -q packages/app`
Expected: 212 tests collected.
- [ ] **Step 1: Write the failing test**
{FENCE}python
from app.search import search


def test_search() -> None:
    assert search("a") == ["a"]
{FENCE}
- [ ] **Step 2: Run to see it fail**
{FENCE}bash
uv run pytest -q packages/app/tests/test_search.py
{FENCE}
Expected: FAIL (`search` missing).
"""
PYPROJECT = '[tool.ruff]\nline-length = 100\n\n[tool.ruff.lint]\nselect = ["F", "I"]\n'
PYPROJECT_WITH_E = PYPROJECT.replace('["F", "I"]', '["E", "F", "I"]')  # E402 is an E rule
BODY = 'from app.search import search\n\n\ndef test_search() -> None:\n    assert search("a") == ["a"]\n'


def lint(*args: str, path: str | None = None) -> subprocess.CompletedProcess:
    """task_lint.py run isolated; `path` replaces the PATH it finds ruff and uv on."""
    env = None if path is None else {**os.environ, "PATH": path}
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True, timeout=120, check=False, env=env
    )


def plan(tmp_path: Path, text: str, ruff: bool = True, pyproject: str = PYPROJECT) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    folder = repo / "docs" / "exec-plans" / "active" / "run"
    folder.mkdir(parents=True)
    if ruff:
        (repo / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    (folder / "task-03.md").write_text(text, encoding="utf-8")
    return repo, folder


def with_python(body: str) -> str:
    """GOOD with the body of its python block (the fence on line 7) replaced."""
    assert BODY in GOOD
    return GOOD.replace(BODY, body)


def test_a_task_with_its_step_0_count_expected_lines_and_clean_python_passes(tmp_path):
    repo, folder = plan(tmp_path, GOOD)
    r = lint(str(folder), "--repo", str(repo))
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines() == ["task_lint: 1 files, 0 problems"]


def test_a_command_without_expected_and_a_missing_or_countless_step_0_are_problems(tmp_path):
    no_expected = GOOD.replace("Expected: FAIL (`search` missing).\n", "- [ ] **Step 3: Implement**\n")
    repo, folder = plan(tmp_path, no_expected)
    task = folder / "task-03.md"
    assert lint(str(task), "--repo", str(repo)).stdout.splitlines() == [
        f"{task}:15: a command without an `Expected:` line",
        "task_lint: 1 files, 1 problems",
    ]
    task.write_text(GOOD.replace("Expected: 212 tests collected.", "Expected: the tests collected."), encoding="utf-8")
    assert f"{task}:3: `Step 0` has no `Expected:` line with a count" in lint(str(task), "--repo", str(repo)).stdout
    task.write_text(GOOD.replace("**Step 0: Collect", "**Step 9: Collect"), encoding="utf-8")
    r = lint(str(task), "--repo", str(repo))
    assert r.returncode == 1 and f"{task}:1: no `Step 0`" in r.stdout


def test_a_python_block_ruff_refuses_is_a_problem_in_the_task_and_its_code_file(tmp_path):
    unformatted = BODY.replace('assert search("a") == ["a"]', 'unused = search("a")').replace("\n\n\n", "\nx=1\n\n\n")
    repo, folder = plan(tmp_path, with_python(unformatted))
    (folder / "task-03.code.md").write_text(f"## Block 1a\n{FENCE}python\nx=1\n{FENCE}\n", encoding="utf-8")
    r = lint(str(folder), "--repo", str(repo))
    assert r.returncode == 1
    lines = r.stdout.splitlines()
    refused = f"{folder / 'task-03.md'}:7: ruff check refuses the python block: F841"
    assert any(line.startswith(refused) for line in lines)
    assert any(line.startswith(f"{folder / 'task-03.md'}:7: ruff format refuses") for line in lines)
    assert any(line.startswith(f"{folder / 'task-03.code.md'}:2: ruff format refuses") for line in lines)
    assert lines[-1] == "task_lint: 1 files, 3 problems"


def test_without_a_ruff_configuration_python_is_not_checked_and_other_languages_are_counted_unchecked(tmp_path):
    text = GOOD.replace("from app.search import search", "import os\nfrom app.search import search")
    text += f"{FENCE}rust\nfn main() {{}}\n{FENCE}\n"
    repo, folder = plan(tmp_path, text, ruff=False)
    r = lint(str(folder), "--repo", str(repo))
    assert r.returncode == 0 and r.stdout.splitlines() == ["task_lint: 1 files, 0 problems, unchecked rust 1"]


def test_a_path_that_is_not_there_exits_2(tmp_path):
    r = lint(str(tmp_path / "nowhere"))
    assert r.returncode == 2 and "no such file" in r.stderr


FRAGMENTS = {  # the rules that need the whole file, each with a block that trips only it
    "F401": "import os\n",
    "F811": "def f() -> None:\n    pass\n\n\ndef f() -> None:\n    pass\n",
    "F821": "print(REPO)\n",
    "E402": "x = 1\nimport os\n\nprint(os)\n",
    "I001": "import sys\nimport os\n\nprint(os, sys)\n",
}
METHOD = '    def test_it(self) -> None:\n        assert yaml.safe_load("a") == REPO\n'


@pytest.mark.parametrize("code", FRAGMENTS)
def test_a_python_block_is_checked_as_a_fragment_so_a_rule_that_needs_the_whole_file_does_not_refuse_it(tmp_path, code):
    """V10 of the verifier: a task's block is often the lines to add to a file and uses that file's names and imports;
    held to `until it exits 0` a planner could only pad it with imports the builder then pasted twice."""
    repo, folder = plan(tmp_path, with_python(FRAGMENTS[code]), pyproject=PYPROJECT_WITH_E)
    r = lint(str(folder), "--repo", str(repo))
    assert (r.returncode, r.stdout.splitlines()) == (0, ["task_lint: 1 files, 0 problems"]), code


def test_an_indented_fragment_is_checked_dedented_and_a_real_problem_in_it_is_still_refused(tmp_path):
    repo, folder = plan(tmp_path, with_python(METHOD))
    r = lint(str(folder), "--repo", str(repo))
    assert (r.returncode, r.stdout.splitlines()) == (0, ["task_lint: 1 files, 0 problems"])
    task = folder / "task-03.md"
    unused = METHOD.replace('assert yaml.safe_load("a") == REPO', "unused = REPO")
    task.write_text(with_python(unused), encoding="utf-8")
    r = lint(str(folder), "--repo", str(repo))
    first = r.stdout.splitlines()[0]
    assert r.returncode == 1 and first.startswith(f"{task}:7: ruff check refuses the python block: F841")
    assert r.stdout.splitlines()[-1] == "task_lint: 1 files, 1 problems"


def test_a_block_that_does_not_parse_alone_is_counted_as_an_unchecked_fragment_and_not_refused(tmp_path):
    """One entry of a set, one key of a dict: the lines are right in their file and make no module of their own."""
    repo, folder = plan(tmp_path, with_python('"a": 1,\n"b": 2,\n'))
    (folder / "task-03.code.md").write_text(f"{FENCE}python\n    one entry of a set,\n{FENCE}\n", encoding="utf-8")
    r = lint(str(folder), "--repo", str(repo))
    assert (r.returncode, r.stdout.splitlines()) == (0, ["task_lint: 1 files, 0 problems, unchecked fragment 2"])


@pytest.mark.parametrize(
    "body, summary",
    [
        ('    "surface-phrases.en.json",\n', "task_lint: 1 files, 0 problems, unchecked fragment 1"),
        ("# nothing yet\n", "task_lint: 1 files, 0 problems"),
        ('print("a")\n', "task_lint: 1 files, 0 problems"),
        ("print( 'a' )\n", "task_lint: 1 files, 1 problems"),
        ('x = 1\n"a",\n', "task_lint: 1 files, 1 problems"),  # a statement beside the entry: a module of its own
    ],
)
def test_a_block_of_expressions_that_are_no_calls_is_an_entry_of_a_literal_and_a_call_or_a_comment_is_not(
    tmp_path, body, summary
):
    """The template's done plan holds `"surface-phrases.en.json",` as one entry of a set; ruff reads the bare tuple as a
    useless expression and wants it in parentheses. A call is a statement, and a block with no code has nothing to skip."""
    repo, folder = plan(tmp_path, with_python(body))
    assert lint(str(folder), "--repo", str(repo)).stdout.splitlines()[-1] == summary


def quoting(opening: str, inner: str, closing: str) -> str:
    """A task whose Step 1 quotes `inner` in a block fenced by `opening` and `closing`, then a Step 2 with a shell block
    and no `Expected:` line: the one problem a lint that reads the fences right reports, at that shell block."""
    return (
        "# Task 3 — the search step\nbuilder: a\n"
        "- [ ] **Step 0: Collect the tests at the base**\n"
        "Run: `uv run pytest --collect-only -q packages/app`\nExpected: 212 tests collected.\n"
        f"- [ ] **Step 1: Quote the example**\n{opening}markdown\n{inner}\n{closing}\n"
        f"- [ ] **Step 2: Run to see it fail**\n{FENCE}bash\nuv run pytest -q packages/app/tests/test_search.py\n{FENCE}\n"
    )


QUOTED = f"{FENCE}bash\nuv run pytest -q x\n{FENCE}"  # a shell block, quoted inside another block
FENCES = {
    "a longer fence quotes a shorter one": ("````", QUOTED, "````"),
    "a closing fence may be longer than the opening": ("````", QUOTED, "`````"),
    "a tilde fence quotes backtick lines": ("~~~", QUOTED, "~~~"),
    "a line with an info string closes nothing": (FENCE, f"{FENCE}bash\nuv run pytest -q x", FENCE),
    "an indented fence, trailing spaces after the close": ("   " + FENCE, "plain text", "   " + FENCE + "  "),
}


@pytest.mark.parametrize("fences", FENCES.values(), ids=FENCES)
def test_a_fence_closes_on_a_line_of_its_own_kind_at_least_as_long_with_nothing_else_on_it(tmp_path, fences):
    """V9 of the verifier: the inner three-backtick line closed a four-backtick block, the outer closing line opened a
    new block, and that block swallowed the next step's command, so a command without `Expected:` went unreported."""
    text = quoting(*fences)
    repo, folder = plan(tmp_path, text, ruff=False)
    task = folder / "task-03.md"
    shell_at = max(n for n, line in enumerate(text.splitlines(), 1) if line == f"{FENCE}bash")
    assert lint(str(task), "--repo", str(repo)).stdout.splitlines() == [
        f"{task}:{shell_at}: a command without an `Expected:` line",
        "task_lint: 1 files, 1 problems",
    ]


def stub(folder: Path, name: str, body: str) -> str:
    """A stand-in tool `name` in `folder` that runs the shell `body`; returns a PATH that holds nothing else."""
    folder.mkdir()
    tool = folder / name
    tool.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    tool.chmod(0o755)
    return str(folder)


@pytest.mark.parametrize(
    "tool, body, named",
    [
        ("ruff", 'case "$1" in check) echo "error: boom" >&2; exit 2;; esac; exit 0', "ruff check"),
        ("ruff", 'case "$1" in format) echo "error: boom" >&2; exit 2;; esac; exit 0', "ruff format"),
        ("uv", 'echo "error: Failed to spawn: ruff" >&2; exit 2', "ruff check"),
    ],
    ids=["ruff check fails", "ruff format fails", "uv fails to start ruff"],
)
def test_when_ruff_does_not_run_task_lint_prints_the_tools_error_and_exits_2_and_blames_no_block(
    tmp_path, tool, body, named
):
    """V11 of the verifier: `Failed to spawn: ruff` was reported as two problems of every python block, the second a
    false "it would reformat it"; no edit of a block fixes a tool that does not run, so it is an exit 2 with its error."""
    repo, folder = plan(tmp_path, GOOD)
    r = lint(str(folder), "--repo", str(repo), path=stub(tmp_path / "bin", tool, body))
    assert (r.returncode, r.stdout) == (2, "")
    assert named in r.stderr and "error:" in r.stderr and "problems" not in r.stderr


def test_without_ruff_and_uv_on_the_path_task_lint_exits_2_and_names_what_it_could_not_start(tmp_path):
    (tmp_path / "empty").mkdir()
    repo, folder = plan(tmp_path, GOOD)
    r = lint(str(folder), "--repo", str(repo), path=str(tmp_path / "empty"))
    assert (r.returncode, r.stdout) == (2, "")
    assert "could not start" in r.stderr and "'uv'" in r.stderr


def test_a_run_or_step_line_quoted_in_a_block_is_text_and_neither_a_command_nor_a_step(tmp_path):
    """V12 of the verifier: lines inside a fence are skipped. A `markdown` block that quotes a `Run:` line and a step
    line, as a task about writing tasks does, would otherwise ask for an `Expected:` line and end the step it sits in."""
    quoted = f"{FENCE}markdown\nRun: `uv run pytest -q`\n- [ ] **Step 7: a step the block quotes**\n{FENCE}\n"
    step_2 = "- [ ] **Step 2: Run to see it fail**\n"
    repo, folder = plan(tmp_path, GOOD.replace(step_2, quoted + step_2), ruff=False)
    r = lint(str(folder), "--repo", str(repo))
    assert (r.returncode, r.stdout.splitlines()) == (0, ["task_lint: 1 files, 0 problems"])


def test_a_py_fence_is_python_and_ruff_refuses_what_it_holds(tmp_path):
    """V12 of the verifier: `lang not in ("python", "py")` could lose its `py` with every test passing."""
    repo, folder = plan(tmp_path, with_python("x=1\n").replace(f"{FENCE}python", f"{FENCE}py", 1))
    task = folder / "task-03.md"
    r = lint(str(task), "--repo", str(repo))
    assert (r.returncode, r.stdout.splitlines()) == (
        1,
        [f"{task}:7: ruff format refuses the python block: it would reformat it", "task_lint: 1 files, 1 problems"],
    )
