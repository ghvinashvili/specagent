"""Decision pages in the wiki (spec A1), the plans seen through wiki/plans (A4) and pages of at most 12 KB (A3)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
import yaml
from harness import wiki

REPO = Path(__file__).resolve().parents[3]
DECISION = {
    "title": "Use PostgreSQL",
    "type": "decision",
    "status": "draft",
    "updated": "2026-10-29",
    "decided": "2026-10-29",
    "by": "owner",
    "why": "the game's data is relational",
    "would_change_if": "a measured load that PostgreSQL cannot carry",
    "decision_status": "decided",
    "scope": "project",
}
LINE = "- [Use PostgreSQL](decisions/use-postgres.md): the store of the game\n"
PAGE = "wiki/decisions/use-postgres.md"


def page(fields: dict, body: str = "# Page\n") -> str:
    """A page as a builder writes it: YAML frontmatter, then the text."""
    return "---\n" + yaml.safe_dump(fields, sort_keys=False) + "---\n" + body


@pytest.fixture
def make_wiki(tmp_path: Path):
    """A root with the repository's page schema and a log; make(files) writes the files and returns the root."""
    (tmp_path / "schemas").mkdir()
    shutil.copy(REPO / "schemas" / "wiki-page.schema.json", tmp_path / "schemas")
    (tmp_path / "wiki").mkdir()
    (tmp_path / "wiki" / "log.md").write_text("# Wiki log\n", encoding="utf-8")

    def make(files: dict[str, str]) -> Path:
        for rel, text in files.items():
            (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / rel).write_text(text, encoding="utf-8")
        return tmp_path

    return make


def test_a_decision_page_with_its_fields_is_a_page_of_its_own_kind(make_wiki):
    out = wiki.lint(make_wiki({"wiki/index.md": LINE, PAGE: page(DECISION)}))
    assert (out["ok"], out["pages"], out["problems"]) == (True, 1, [])


@pytest.mark.parametrize("field", ["decided", "by", "why", "would_change_if", "decision_status", "scope"])
def test_a_decision_page_without_one_of_its_fields_is_a_problem(make_wiki, field):
    fields = {k: v for k, v in DECISION.items() if k != field}
    root = make_wiki({"wiki/index.md": LINE, PAGE: page(fields)})
    assert wiki.lint(root)["problems"] == [f"decisions/use-postgres.md: '{field}' is a required property"]


@pytest.mark.parametrize(
    ("field", "value", "allowed"),
    [("decision_status", "pending", "['decided', 'revised', 'withdrawn']"), ("scope", "team", "['project', 'global']")],
)
def test_a_decision_status_or_a_scope_outside_its_values_is_a_problem(make_wiki, field, value, allowed):
    root = make_wiki({"wiki/index.md": LINE, PAGE: page({**DECISION, field: value})})
    assert wiki.lint(root)["problems"] == [f"decisions/use-postgres.md: '{value}' is not one of {allowed}"]


def test_a_revised_decision_names_the_page_that_revises_it(make_wiki):
    old = {**DECISION, "title": "Use SQLite", "decision_status": "revised"}
    index = LINE + "- [Use SQLite](decisions/use-sqlite.md): the first store\n"
    root = make_wiki({"wiki/index.md": index, PAGE: page(DECISION), "wiki/decisions/use-sqlite.md": page(old)})
    assert wiki.lint(root)["problems"] == ["decisions/use-sqlite.md: 'revised_by' is a required property"]
    make_wiki({"wiki/decisions/use-sqlite.md": page({**old, "revised_by": "decisions/use-mysql.md"})})
    assert wiki.lint(root)["problems"] == ["decisions/use-sqlite.md: decisions/use-mysql.md does not exist"]
    make_wiki({"wiki/decisions/use-sqlite.md": page({**old, "revised_by": "decisions/use-postgres.md"})})
    assert wiki.lint(root)["problems"] == []


def test_a_decision_page_needs_its_index_line_and_no_other_page_that_links_it(make_wiki):
    root = make_wiki({"wiki/index.md": "# Wiki index\n", PAGE: page(DECISION)})
    assert wiki.lint(root)["problems"] == ["decisions/use-postgres.md: not listed in index.md"]
    make_wiki({"wiki/index.md": LINE})
    assert wiki.lint(root)["problems"] == []  # the index line is enough: a decision is no orphan


def test_a_decision_belongs_in_decisions(make_wiki):
    files = {"wiki/index.md": "- [D](concepts/use-postgres.md): d\n", "wiki/concepts/use-postgres.md": page(DECISION)}
    assert wiki.lint(make_wiki(files))["problems"] == [
        "concepts/use-postgres.md: type decision does not belong in concepts/",
        "concepts/use-postgres.md: orphan (no page links to it)",
    ]


def test_a_summary_beside_a_decision_page_is_no_page(make_wiki):
    summary = "Use PostgreSQL: the game's data is relational.\n"  # no frontmatter: a summary, not a page
    out = wiki.lint(
        make_wiki({"wiki/index.md": LINE, PAGE: page(DECISION), "wiki/decisions/use-postgres.summary.md": summary})
    )
    assert (out["ok"], out["pages"]) == (True, 1)


def test_a_page_or_the_index_over_12000_bytes_is_a_problem_counted_in_bytes(make_wiki):
    text = page(DECISION)
    fill = 12_000 - len(text.encode()) - 1
    root = make_wiki({"wiki/index.md": LINE, PAGE: text + "x" * fill + "\n"})
    assert len((root / PAGE).read_bytes()) == 12_000 and wiki.lint(root)["problems"] == []
    make_wiki({PAGE: text + "é" + "x" * (fill - 1) + "\n"})  # 12,000 characters, 12,001 bytes
    assert wiki.lint(root)["problems"] == ["decisions/use-postgres.md: 12001 bytes; a page stays at most 12000"]
    make_wiki({PAGE: text, "wiki/index.md": LINE + "x" * (12_000 - len(LINE)) + "\n"})
    assert wiki.lint(root)["problems"] == ["index.md: 12001 bytes; an index stays at most 12000"]


def test_links_inside_code_are_text_in_pages_and_in_the_index(make_wiki):
    body = "# Page\n\nQuoted: `[old](gone.md)`.\n\n```markdown\n[old](gone.md)\n```\n"
    index = LINE + "A line looks like `- [Name](decisions/name.md): what it decides`.\n"
    root = make_wiki({"wiki/index.md": index, PAGE: page(DECISION, body)})
    assert wiki.lint(root)["problems"] == []
    make_wiki({PAGE: page(DECISION, body + "\nSee [old](gone.md).\n")})
    assert wiki.lint(root)["problems"] == ["decisions/use-postgres.md: dead link gone.md"]


def test_the_index_links_the_plans_and_the_graph_and_a_graph_not_built_is_a_warning(make_wiki):
    index = "# Wiki index\n\n- [Log](log.md): the entries\n- [Plans](plans/README.md): the active plans\n"
    index += "- [Code graph](graph/index.md): built by `just graph`\n"
    root = make_wiki({"wiki/index.md": index, "docs/exec-plans/active/README.md": "# Plans\n"})
    os.symlink("../docs/exec-plans/active", root / "wiki" / "plans")
    out = wiki.lint(root)
    assert (out["ok"], out["problems"]) == (True, [])
    assert out["warnings"] == ["index.md: graph/index.md is not built (the graph recipe writes wiki/graph/)"]
    make_wiki({"wiki/graph/other.md": "# Other\n"})  # built, without the page the index names
    assert wiki.lint(root)["problems"] == ["index.md: graph/index.md does not exist"]
    make_wiki({"wiki/graph/index.md": "# Graph\n"})
    out = wiki.lint(root)
    assert (out["ok"], out["warnings"]) == (True, [])
    (root / "wiki" / "plans").unlink()
    assert wiki.lint(root)["problems"] == ["index.md: plans/README.md does not exist"]


@pytest.mark.parametrize("kind", ["folder", "another target", "absolute"])
def test_wiki_plans_is_the_relative_link_to_the_active_plans(make_wiki, kind):
    root = make_wiki({"wiki/index.md": "# Wiki index\n", "docs/exec-plans/active/README.md": "# Plans\n"})
    link = root / "wiki" / "plans"
    if kind == "folder":
        (link / "p").mkdir(parents=True)
    elif kind == "another target":
        os.symlink("../docs", link)
    else:
        os.symlink(root / "docs" / "exec-plans" / "active", link)
    assert wiki.lint(root)["problems"] == ["plans: not a link to ../docs/exec-plans/active"]
    shutil.rmtree(link) if kind == "folder" else link.unlink()
    os.symlink("../docs/exec-plans/active", link)
    assert wiki.lint(root)["problems"] == []


def test_a_plans_link_whose_target_is_missing_leaves_the_report_to_the_index_line(make_wiki):
    root = make_wiki({"wiki/index.md": "- [Plans](plans/README.md): the active plans\n"})
    os.symlink("../docs/exec-plans/active", root / "wiki" / "plans")  # this root has no docs/exec-plans/active
    assert wiki.lint(root)["problems"] == ["index.md: plans/README.md does not exist"]


def test_a_task_file_seen_through_wiki_plans_is_held_to_1500_lines_not_to_12000_bytes(make_wiki):
    row = "y" * 40 + "\n"
    files = {
        "wiki/index.md": "# Wiki index\n",
        "docs/exec-plans/active/README.md": "# Plans\n",
        "docs/exec-plans/active/p/00-index.md": "# Plan\n" + row * 2000,  # an index is no task file
        "docs/exec-plans/active/p/task-01.md": "# Task 1 — a\n" + row * 1499,  # 1,500 lines, 61,000 bytes and more
        "docs/exec-plans/active/p/task-02.md": "# Task 2 — b\n" + row * 1500,  # 1,501 lines
        "docs/exec-plans/active/run-loop.md": row * 2000,  # a single-file plan is no task file
    }
    root = make_wiki(files)
    os.symlink("../docs/exec-plans/active", root / "wiki" / "plans")
    assert wiki.lint(root)["problems"] == ["plans/p/task-02.md: 1501 lines, more than 1500"]


def test_the_template_wiki_lints_clean_with_its_first_decision_page():
    out = wiki.lint(REPO)
    assert out["ok"], out["problems"]
    text = (REPO / "wiki" / "decisions" / "decisions-are-written-with-the-work.md").read_text(encoding="utf-8")
    fm = yaml.safe_load(text.split("---", 2)[1])
    assert (fm["type"], fm["decision_status"], fm["scope"], fm["by"]) == ("decision", "decided", "global", "owner")
    assert "docs: none —" in text and "harness integrate" in text and "ADR-0027" in text
    assert (REPO / "wiki" / "decisions" / "decisions-are-written-with-the-work.summary.md").is_file()
    index = (REPO / "wiki" / "index.md").read_text(encoding="utf-8")
    for target in ("(decisions/decisions-are-written-with-the-work.md)", "(plans/README.md)", "(graph/index.md)"):
        assert target in index, target


def test_the_wiki_rules_name_the_second_writer_and_the_decision_fields():
    rules = (REPO / ".claude" / "rules" / "wiki.md").read_text(encoding="utf-8")
    assert rules.startswith("---\npaths:\n")
    for words in ("builder", "docs: none —", "decision_status", "revised_by", "would_change_if", "12,000 bytes"):
        assert words in rules, words
    for path in ("wiki/decisions/", "wiki/plans", "wiki/graph/", "docs/exec-plans/active/"):
        assert path in rules, path
