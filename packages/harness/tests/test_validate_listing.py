"""harness validate reads the files git tracks or is about to track (B11) and finds no letter of a refused block in them
(docs/decisions/0030-the-template-is-english-only.md)."""

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path

import pytest
from harness import catalog

ROOT = Path(__file__).resolve().parents[3]
QUIET = ("git", "-c", "core.hooksPath=/dev/null")
BROKEN = "broken.json: not valid JSON (Expecting property name enclosed in double quotes: line 1 column 2 (char 1))"
EMPTY = "ignored.json: not valid JSON (Expecting value: line 1 column 1 (char 0))"
LETTER = ": a letter of a refused block (U+10A0-U+10FF, U+1C90-U+1CBF, U+2D00-U+2D2F); tracked files are English only"
LOW, HIGH = chr(0x10A0), chr(0x10FF)
# Both edges of each refused block and the code point just outside it (8.3.11; lessons R4 and V3)
EDGES = {0x109F: False, 0x10A0: True, 0x10FF: True, 0x1100: False,
         0x1C8F: False, 0x1C90: True, 0x1CBF: True, 0x1CC0: False,
         0x2CFF: False, 0x2D00: True, 0x2D2F: True, 0x2D30: False}  # fmt: skip
STUBS = (".claude/commands", ".claude/output-styles", ".claude/routines", ".claude/launch.json",
         ".claude/scheduled_tasks.json", ".claude/settings.local.json")  # fmt: skip


def git(root: Path, *args: str) -> None:
    subprocess.run([*QUIET, "-C", str(root), *args], check=True, capture_output=True)


def repo(tmp_path: Path) -> Path:
    """A work tree: good.json tracked, gone.json tracked and deleted from disk, ignored.json ignored and empty,
    broken.json untracked and broken."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    (root / ".gitignore").write_text("/ignored.json\n/ignored.md\n")
    (root / "good.json").write_text("{}")
    (root / "gone.json").write_text("{}")
    git(root, "add", ".gitignore", "good.json", "gone.json")
    (root / "gone.json").unlink()
    (root / "ignored.json").write_text("")
    (root / "broken.json").write_text("{")
    return root


def test_validate_reads_tracked_and_untracked_json_and_skips_ignored_and_deleted_files(tmp_path: Path):
    assert catalog.json_problems(repo(tmp_path)) == [BROKEN]


def test_without_git_or_outside_a_work_tree_every_json_file_is_read(tmp_path: Path, monkeypatch):
    root = repo(tmp_path)
    (tmp_path / "bin").mkdir()
    with monkeypatch.context() as patch:
        patch.setenv("PATH", str(tmp_path / "bin"))
        assert sorted(catalog.json_problems(root)) == [BROKEN, EMPTY]
    shutil.rmtree(root / ".git")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    assert sorted(catalog.json_problems(root)) == [BROKEN, EMPTY]


def test_a_georgian_letter_in_a_listed_file_is_one_problem_at_its_first_line(tmp_path: Path, monkeypatch):
    root = repo(tmp_path)
    (root / "low.md").write_text("English\n" + LOW + "\n", encoding="utf-8")
    (root / "high.py").write_text("a = 1\nb = 2\nc = '" + HIGH + "'\n" + HIGH + "\n", encoding="utf-8")
    (root / "edges.md").write_text(chr(0x109F) + chr(0x1100) + "\n", encoding="utf-8")
    (root / "ignored.md").write_text(LOW + "\n", encoding="utf-8")
    (root / "binary.dat").write_bytes(b"\xff\xfe" + LOW.encode("utf-8"))
    (root / "link.md").symlink_to("low.md")
    git(root, "add", "low.md", "high.py", "edges.md", "binary.dat", "link.md")
    (root / "untracked.md").write_text(LOW + "\n", encoding="utf-8")
    want = [f"high.py:3{LETTER}", f"low.md:2{LETTER}", f"untracked.md:1{LETTER}"]
    assert catalog.english_only_problems(root) == want
    shutil.rmtree(root / ".git")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    assert catalog.english_only_problems(root) == [*want[:1], f"ignored.md:1{LETTER}", *want[1:]]


def test_a_project_narrows_the_letter_check_with_english_only(tmp_path: Path):
    root = repo(tmp_path)
    (root / "docs" / "template").mkdir(parents=True)
    (root / "docs" / "x.md").write_text(LOW + "\n", encoding="utf-8")
    (root / "web").mkdir()
    (root / "web" / "page.md").write_text(LOW + "\n", encoding="utf-8")
    variables = root / "docs" / "template" / "variables.yaml"
    variables.write_text("english_only: [docs/]\n", encoding="utf-8")
    assert catalog.english_only_problems(root) == [f"docs/x.md:1{LETTER}"]
    variables.write_text("english_only: []\n", encoding="utf-8")
    assert catalog.english_only_problems(root) == []
    variables.write_text("omit: [design/]\n", encoding="utf-8")
    assert catalog.english_only_problems(root) == [f"docs/x.md:1{LETTER}", f"web/page.md:1{LETTER}"]


@pytest.mark.parametrize("code", sorted(EDGES))
def test_each_georgian_block_is_a_problem_from_its_first_to_its_last_code_point(tmp_path: Path, code: int):
    root = repo(tmp_path)
    (root / "x.md").write_text("English\n" + chr(code) + "\n", encoding="utf-8")
    git(root, "add", "x.md")
    assert catalog.english_only_problems(root) == ([f"x.md:2{LETTER}"] if EDGES[code] else [])


def test_the_template_holds_no_georgian_letter():
    assert catalog.english_only_problems(ROOT) == []


def test_validate_runs_the_three_checks_in_order_and_each_function_is_small(monkeypatch):
    for name, mark in (("json_problems", "json"), ("table_problems", "table"), ("english_only_problems", "letter")):
        monkeypatch.setattr(catalog, name, lambda root, mark=mark: [mark])
    report = catalog.validate_repository(ROOT)
    assert [p for p in report["problems"] if p in ("json", "table", "letter")] == ["json", "table", "letter"]
    assert report["ok"] is False
    tree = ast.parse(Path(catalog.__file__).read_text(encoding="utf-8"))
    sizes = {f.name: f.end_lineno - f.lineno + 1 for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)}
    names = ("_listed", "_files", "json_problems", "table_problems", "english_only_problems", "validate_repository")
    assert {name: sizes[name] for name in names if sizes[name] >= 50} == {}


def test_the_ignore_file_hides_the_sandbox_stubs_and_lists_real_folders_of_their_names(tmp_path: Path):
    root = tmp_path / "repo"
    (root / ".claude").mkdir(parents=True)
    git(root, "init", "-q")
    shutil.copy2(ROOT / ".gitignore", root / ".gitignore")
    for rel in STUBS:
        (root / rel).write_text("")
    assert catalog._listed(root) == [".gitignore"]
    for name in ("commands", "output-styles", "routines"):
        (root / ".claude" / name).unlink()
        (root / ".claude" / name).mkdir()
        (root / ".claude" / name / "x.md").write_text("# x\n")
    want = [".claude/commands/x.md", ".claude/output-styles/x.md", ".claude/routines/x.md", ".gitignore"]
    assert catalog._listed(root) == want
