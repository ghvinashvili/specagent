"""harness plan-lint (spec A4, B5; ADR-0026): a plan folder under docs/exec-plans/active/ has a `00-index.md` whose
`## Task order` table names its tasks, row `| N |` naming `task-NN.md`. Each named task exists, starts with `# Task N`
and has at most 1,500 lines counted at newlines; no task file is outside the index. Single-file plans are not linted."""

from __future__ import annotations

import json
from pathlib import Path

from harness import cli, plans

# The form of docs/exec-plans/active/template-core/00-index.md (A1 of the index round): file names in prose and the
# rows of other tables are not the task order.
INDEX = (
    "# Plan: demo — index\n\n"
    "Task files `task-01.md` … `task-03.md` sit beside this index.\n\n"
    "## Commands\n"
    "| Command | Expected |\n"
    "| --- | --- |\n"
    "| 7 | a row of another table |\n\n"
    "## Task order\n"
    "| Task | title | builder | depends_on | files | milestone |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
    "| 1 | First | a | — | `a.py` | M1 |\n"
    "| 2 | Second | b | — | `b.py` | M1 |\n"
    "| 3 | Third | a | 1, 2 | `c.py` | M2 |\n\n"
    "## Milestones\n"
    "| 9 | not a task |\n"
)


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


def plan_dir(root: Path) -> Path:
    return root / "docs" / "exec-plans" / "active" / "demo"


def test_the_task_numbers_come_from_the_task_order_table_only():
    assert plans.task_numbers(INDEX) == [1, 2, 3]
    assert plans.task_numbers("# Plan\n\n## Goal\nNo table.\n") == []


def test_a_plan_whose_index_names_every_task_file_passes(tmp_path):
    root = make_plan(tmp_path)
    (plan_dir(root) / "notes.md").write_text("# Notes\n", encoding="utf-8")  # other files may sit beside the tasks
    assert plans.plan_lint(root) == {
        "ok": True,
        "plans": [{"plan": "demo", "tasks": 3, "written": 3, "blocks": 0}],
        "problems": [],
    }


def test_a_missing_task_a_task_outside_the_index_and_a_long_task_are_one_problem_each(tmp_path):
    """A1 (a)-(c) of the index round: each defect gives exactly one problem, which names the file."""
    root = make_plan(tmp_path)
    (plan_dir(root) / "task-02.md").unlink()
    assert plans.plan_lint(root)["problems"] == ["demo/task-02.md: named in 00-index.md but missing"]
    (plan_dir(root) / "task-02.md").write_text("# Task 2 — step 2\n", encoding="utf-8")
    (plan_dir(root) / "task-04.md").write_text("# Task 4 — step 4\n", encoding="utf-8")
    assert plans.plan_lint(root)["problems"] == ["demo/task-04.md: not in the task order of 00-index.md"]
    (plan_dir(root) / "task-04.md").unlink()
    (plan_dir(root) / "task-03.md").write_text("# Task 3 — step 3\n" + "x\n" * 1500, encoding="utf-8")
    out = plans.plan_lint(root)
    assert out["ok"] is False and out["problems"] == ["demo/task-03.md: 1501 lines, more than 1500"]


def test_lines_are_counted_at_newlines_only(tmp_path):
    """U+2028 and a form feed are characters inside a line, as `wc -l` counts (spec B2: the outline's U+2028 bug)."""
    assert plans.count_lines("") == 0
    assert plans.count_lines("a") == 1
    assert plans.count_lines("a\nb\n") == 2
    assert plans.count_lines("a\nb") == 2
    assert plans.count_lines("a\u2028b\x0cc\n") == 1
    root = make_plan(tmp_path)
    (plan_dir(root) / "task-01.md").write_text("# Task 1 — step 1\n" + "x\u2028y\n" * 1499, encoding="utf-8")
    assert plans.plan_lint(root)["ok"] is True  # 1,500 lines; str.splitlines() would count 2,999


def test_a_task_file_starts_with_its_own_number(tmp_path):
    """A renumbered task or a heading written for another task is caught (lessons.md, Known error classes)."""
    root = make_plan(tmp_path)
    (plan_dir(root) / "task-02.md").write_text("# Task 5 — step 2\n", encoding="utf-8")
    (plan_dir(root) / "task-03.md").write_text("Task 3, without its heading\n", encoding="utf-8")
    assert sorted(plans.plan_lint(root)["problems"]) == [
        "demo/task-02.md: the first line must be '# Task 2 — <title>'",
        "demo/task-03.md: the first line must be '# Task 3 — <title>'",
    ]


def test_a_task_named_twice_in_the_task_order_is_a_problem(tmp_path):
    root = make_plan(tmp_path, index=INDEX.replace("| 3 | Third |", "| 2 | Third |"), tasks=(1, 2))
    assert plans.plan_lint(root)["problems"] == ["demo/00-index.md: Task 2 appears twice in the task order"]


def test_a_plan_folder_without_an_index_or_without_a_task_order_is_a_problem(tmp_path):
    root = make_plan(tmp_path, index="# Plan: demo — index\n\n## Goal\nA goal.\n", tasks=())
    loose = root / "docs" / "exec-plans" / "active" / "loose"
    loose.mkdir()
    (loose / "task-01.md").write_text("# Task 1 — a step\n", encoding="utf-8")
    assert sorted(plans.plan_lint(root)["problems"]) == [
        "demo/00-index.md: no task order (a '## Task order' table with rows '| N | ...')",
        "loose: no 00-index.md",
    ]


def test_single_file_plans_and_a_tree_without_plans_are_not_linted(tmp_path):
    root = tmp_path / "repo"
    assert plans.plan_lint(root) == {"ok": True, "plans": [], "problems": []}
    active = root / "docs" / "exec-plans" / "active"
    active.mkdir(parents=True)
    (active / "README.md").write_text("# Active plans\n", encoding="utf-8")
    (active / "run-loop.md").write_text("# Plan\n" + "x\n" * 2000, encoding="utf-8")  # a single-file plan
    assert plans.plan_lint(root) == {"ok": True, "plans": [], "problems": []}


def test_the_command_exits_1_on_a_problem_and_a_role_session_may_run_it(tmp_path, monkeypatch, capsys):
    root = make_plan(tmp_path)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    assert cli.main(["plan-lint"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    (plan_dir(root) / "task-01.md").unlink()
    assert cli.main(["plan-lint"]) == 1
    assert json.loads(capsys.readouterr().out)["problems"] == ["demo/task-01.md: named in 00-index.md but missing"]
    monkeypatch.setenv("HARNESS_ROLE", "planner")  # the checks of a writer's work (cli.ROLE_COMMANDS)
    assert cli.main(["plan-lint"]) == 1
    assert json.loads(capsys.readouterr().out)["problems"] == ["demo/task-01.md: named in 00-index.md but missing"]


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


def test_a_block_line_inside_a_fence_of_the_code_file_is_code_not_a_heading(tmp_path):
    fixture = '    CODE = """\\\n## Block 1a\n## Block 2b\n"""\n'  # a test whose fixture is a code file (V7)
    root = make_plan(tmp_path, code={1: "## Block 1a\n\n```python\ndef test_x(tmp_path):\n" + fixture + "```\n"})
    (plan_dir(root) / "task-01.md").write_text("# Task 1 — step 1\n\n- [ ] Step 1: Block 1a\n", encoding="utf-8")
    d = plans.plan_lint(root)
    assert d["problems"] == [] and d["plans"][0]["blocks"] == 1


def test_a_fence_closes_only_with_a_bare_run_of_its_own_character_at_least_as_long():
    text = (
        "## Block 1a\n````markdown\n```\n## Block 8a\n````\n"  # a shorter run inside a longer fence is text
        "## Block 1b\n~~~\n```\n## Block 8b\n~~~~\n"  # a run of the other character does not close it
        "## Block 1c\n```\n```text\n## Block 8c\n```\n"  # nor does a run with an info string after it
        "## Block 1d\r\n   ```\r\n## Block 8d\r\n"  # an unclosed fence runs to the end of the file; CRLF lines
    )
    assert plans.block_ids(text) == ["1a", "1b", "1c", "1d"]


def test_the_help_of_plan_lint_names_the_code_file_rules(monkeypatch):
    monkeypatch.setenv("COLUMNS", "400")  # argparse wraps at the terminal width; this keeps one line per command
    line = next(s for s in cli.build_parser().format_help().splitlines() if s.strip().startswith("plan-lint "))
    assert "each task-NN.code.md has its task file and defines once every Block <id> its steps name" in line
