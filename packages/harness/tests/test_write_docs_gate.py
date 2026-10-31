"""The write gate holds a code task to its pages (spec A2, ADR-0027): a branch that changes code touches a page under
wiki/, docs/runbooks/ or docs/decisions/, or the planner gave every task of the shard `docs: none — <reason>`."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import jsonschema
import pytest
from harness import state
from harness.gates import write

REPO = Path(__file__).resolve().parents[3]
IDENTITY = ["-c", "user.email=t@example.com", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
NAME = "the code comes with its pages, or every task says docs: none with a reason"
WHY = "no page under wiki/, docs/runbooks/ or docs/decisions/; no docs: none — <reason> on "
NONE = "none — a rename that changes no behaviour"


def git(root: Path, *args: str) -> None:
    command = ["git", "-C", str(root), *IDENTITY]
    subprocess.run([*command, *args], check=True, capture_output=True)


def put(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")


@pytest.fixture
def work(tmp_path: Path):
    """A repository on main; work(files) commits them on a fresh branch work-1 and returns to main."""
    root = tmp_path / "repo"
    put(
        root,
        {
            "src/app.py": "A = 1\n",
            "wiki/index.md": "# Wiki index\n",
            "docs/runbooks/README.md": "# Runbooks\n",
            "docs/roles/need-to-know.yaml": (REPO / "docs/roles/need-to-know.yaml").read_text(encoding="utf-8"),
            "docs/roles/stages.yaml": 'version: 1\nstages:\n  - {id: write, inputs: ["plan:tasks.json"]}\n',
        },
    )
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "init")

    def commit(files: dict[str, str]) -> Path:
        git(root, "checkout", "-q", "-B", "work-1", "main")
        put(root, files)
        git(root, "add", "-A")
        git(root, "commit", "-qm", "feat: work")
        git(root, "checkout", "-q", "main")
        return root

    return commit


def pages_check(root: Path, tmp_path: Path, *docs: str | None, planned: tuple | None = None) -> list[dict]:
    """The pages check of the write gate (as the stop hook runs it) for a shard whose tasks carry these `docs`, split
    from the planner's list, whose tasks carry `planned` (the same `docs` unless given); the gate reads the planner's."""
    run = tmp_path / "runs" / "20261029-000000-demo"
    stage = run / "stages" / "write" / "01"
    lists = {"stages/write/01/tasks.json": docs, "stages/plan/tasks.json": docs if planned is None else planned}
    for rel, values in lists.items():
        tasks = [
            {"id": f"T{i:03d}", "category": "c", "description": "d", "steps": ["s"], "passes": True, "evidence": "e"}
            | ({"docs": d} if d is not None else {})
            for i, d in enumerate(values, 1)
        ]
        put(run, {rel: json.dumps({"schema_version": 1, "stage": rel.split("/")[1], "tasks": tasks})})
    put(stage, {"result.json": json.dumps({"summary": "branch work-1, one commit", "evidence": []})})
    return [c for c in write.session_checks(root, run, stage) if c["name"] == NAME]


def test_code_without_a_page_fails_and_names_every_task_without_docs_none(work, tmp_path):
    root = work({"src/app.py": "A = 2\n"})
    assert pages_check(root, tmp_path, None, None) == [{"name": NAME, "passed": False, "detail": WHY + "T001, T002"}]


@pytest.mark.parametrize(
    "page",
    [
        "wiki/decisions/use-postgres.md",
        "wiki/concepts/store.md",
        "docs/runbooks/restore.md",
        "docs/decisions/0030-x.md",
    ],
)
def test_code_with_a_page_passes(work, tmp_path, page):
    root = work({"src/app.py": "A = 2\n", page: "# Page\n"})
    assert pages_check(root, tmp_path, None) == [{"name": NAME, "passed": True}]


@pytest.mark.parametrize(
    "other",
    [
        "wiki/index.md",
        "wiki/log.md",
        "docs/runbooks/README.md",
        "wiki/decisions/use-postgres.summary.md",
        "wiki/.obsidian/app.json",
        "docs/guide.md",
        "docs/exec-plans/active/p/task-01.md",
    ],
)
def test_an_index_a_log_a_summary_a_setting_or_another_document_is_no_page(work, tmp_path, other):
    root = work({"src/app.py": "A = 2\n", other: "x\n"})
    assert pages_check(root, tmp_path, None) == [{"name": NAME, "passed": False, "detail": WHY + "T001"}]


@pytest.mark.parametrize(
    "code",
    ["src/app.py", "tests/test_app.py", "justfile", "schemas/x.schema.json", ".github/workflows/ci.yml", "docs.py"],
)
def test_tests_configuration_and_scripts_are_code(work, tmp_path, code):
    root = work({code: "x = 1\n"})
    assert pages_check(root, tmp_path, None)[0]["passed"] is False


def test_a_branch_without_code_needs_no_page(work, tmp_path):
    root = work({"docs/guide.md": "# Guide\n", ".claude/rules/x.md": "# Rule\n", "context/raw.txt": "raw\n"})
    assert pages_check(root, tmp_path, None) == [{"name": NAME, "passed": True}]


def test_every_task_says_docs_none_with_a_reason_or_the_check_fails(work, tmp_path):
    root = work({"src/app.py": "A = 2\n"})
    assert pages_check(root, tmp_path, NONE, NONE) == [{"name": NAME, "passed": True}]
    assert pages_check(root, tmp_path, NONE, None) == [{"name": NAME, "passed": False, "detail": WHY + "T002"}]
    assert pages_check(root, tmp_path, NONE, "none") == [{"name": NAME, "passed": False, "detail": WHY + "T002"}]


def test_the_writer_cannot_give_itself_docs_none(work, tmp_path):
    root = work({"src/app.py": "A = 2\n"})
    passed = [{"name": NAME, "passed": True}]
    lacking = [{"name": NAME, "passed": False, "detail": WHY + "T001"}]
    assert pages_check(root, tmp_path, "none — done", planned=(None,)) == lacking  # C14: the copy is the writer's
    assert pages_check(root, tmp_path, "none — done", planned=("none — done",)) == passed
    assert pages_check(root, tmp_path, None, planned=(NONE,)) == passed  # the planner's word, whatever the copy says
    lacking = [{"name": NAME, "passed": False, "detail": WHY + "T002"}]
    assert pages_check(root, tmp_path, NONE, NONE, planned=(NONE,)) == lacking  # a task the planner did not give


def test_the_task_schema_takes_docs_none_with_a_reason_only():
    task = {"id": "T001", "category": "c", "description": "d", "steps": ["s"], "passes": False, "docs": NONE}
    doc = {"schema_version": 1, "stage": "plan", "tasks": [task]}
    jsonschema.validate(doc, state.schema(REPO, "tasks"))
    for bad in ("none", "none —", "see wiki/decisions/", ""):
        task["docs"] = bad
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(doc, state.schema(REPO, "tasks"))


def test_the_planner_and_writer_contracts_carry_the_pages_rule():
    planner = (REPO / "docs" / "roles" / "types" / "planner.md").read_text(encoding="utf-8")
    writer = (REPO / "docs" / "roles" / "types" / "writer.md").read_text(encoding="utf-8")
    assert '"docs": "none — <reason>"' in planner and '"docs": "none — <reason>"' in writer
    assert "docs/runbooks/" in writer and "`draft`" in writer


def test_adr_0027_records_the_pages_rule():
    found = sorted((REPO / "docs" / "decisions").glob("0027-*.md"))
    assert [p.name for p in found] == ["0027-pages-are-written-with-the-work.md"]
    text = found[0].read_text(encoding="utf-8")
    assert text.startswith("---\nstatus: accepted\n")
    for heading in ("## Context and Problem Statement", "## Considered Options", "## Decision Outcome"):
        assert heading in text, heading
    for heading in ("### Consequences", "### Confirmation", "## More Information"):
        assert heading in text, heading
    assert "docs: none —" in text and "harness integrate" in text and "wiki/decisions/" in text
    assert "](../../design/" not in text  # a project receives no design/ (omit: in docs/template/variables.yaml)
    readme = (REPO / "docs" / "decisions" / "README.md").read_text(encoding="utf-8")
    assert "(0027-pages-are-written-with-the-work.md)" in readme
