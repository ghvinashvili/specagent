"""docs-check reads the documentation in layers (ADR-0026; spec A4, A5): docs/llms.txt links a document, or links the
folder README.md that links it; a plan folder is listed by docs/exec-plans/active/README.md and checked by plan-lint; a
`.summary.md` summary is listed nowhere; links inside code are text; an index stays at most 12,000 bytes; a decision page or
runbook without its summary is a warning, never a problem."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
from harness import catalog

REPO = Path(__file__).resolve().parents[3]
FENCE = "`" * 3

# A2 of the index round: builder B lists its new pages in the folder READMEs that docs/llms.txt links.
B_LISTINGS = {
    "docs/llms.txt": "- [Runbooks](runbooks/README.md): r\n- [References](references/README.md): f\n",
    "docs/runbooks/README.md": "# Runbooks\n\n- [Server windows](server-windows.md): s\n",
    "docs/references/README.md": "# References\n\n- [Sources](sources.md): e\n",
    "docs/runbooks/server-windows.md": "# Server windows\n",
    "docs/runbooks/server-windows.summary.md": "A summary.\n",
    "docs/references/sources.md": "# Sources\n",
}
# A1 (d) of the index round: a plan folder in the form of docs/exec-plans/active/template-core/.
PLAN = {
    "docs/llms.txt": "- [Active plans](exec-plans/active/README.md): a\n",
    "docs/exec-plans/active/README.md": "# Active plans\n\n- [Demo](demo/00-index.md): d\n",
    "docs/exec-plans/active/demo/00-index.md": (
        "# Plan: demo — index\n\n## Task order\n| Task | title |\n| --- | --- |\n| 1 | One |\n| 2 | Two |\n"
    ),
    "docs/exec-plans/active/demo/task-01.md": "# Task 1 — One\n",
    "docs/exec-plans/active/demo/task-02.md": "# Task 2 — Two\n",
    "docs/exec-plans/active/demo/demo.summary.md": "A summary.\n",
}


@pytest.fixture
def make_docs(tmp_path: Path, monkeypatch):
    """A repository root holding only the files given; the generated catalog and the maps are not under test here."""
    monkeypatch.setattr(catalog, "render_catalog", lambda root: "catalog\n")
    monkeypatch.setattr(catalog.stagemap, "docs_problems", lambda root: [])

    def make(files: dict[str, str]) -> Path:
        root = tmp_path / "repo"
        for rel, text in {"docs/generated/role-types.md": "catalog\n", **files}.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text, encoding="utf-8")
        return root

    return make


def test_a_document_listed_by_its_folder_readme_is_listed_and_a_summary_needs_no_line(make_docs):
    root = make_docs(B_LISTINGS)
    assert catalog.docs_check(root) == {"ok": True, "problems": [], "warnings": []}
    (root / "docs" / "runbooks" / "README.md").write_text("# Runbooks\n", encoding="utf-8")
    assert catalog.docs_check(root)["problems"] == ["docs/llms.txt: runbooks/server-windows.md is not listed"]


def test_a_finished_plan_is_listed_by_the_done_readme_as_an_active_one_is_by_the_active_readme(make_docs):
    """S4: L3 reads the README of the plan's state folder, `active` or `done`, and only when docs/llms.txt links it."""
    files = {
        "docs/llms.txt": "- [Finished plans](exec-plans/done/README.md): f\n",
        "docs/exec-plans/done/README.md": "# Finished plans\n\n- [Old](old/00-index.md): an old run\n",
        "docs/exec-plans/done/old/00-index.md": "# Old\n",
        "docs/exec-plans/done/old/task-01.md": "# Task 1 — One\n",
        "docs/exec-plans/done/old/old.summary.md": "A summary.\n",
    }
    root = make_docs(files)
    assert catalog.docs_check(root) == {"ok": True, "problems": [], "warnings": []}
    (root / "docs" / "exec-plans" / "done" / "README.md").write_text("# Finished plans\n", encoding="utf-8")
    assert catalog.docs_check(root)["problems"] == [
        "docs/llms.txt: exec-plans/done/old/00-index.md is not listed",
        "docs/llms.txt: exec-plans/done/old/task-01.md is not listed",
    ]
    (root / "docs" / "llms.txt").write_text("# Index\n", encoding="utf-8")
    assert "docs/llms.txt: exec-plans/done/README.md is not listed" in catalog.docs_check(root)["problems"]


def test_a_folder_readme_lists_only_by_a_link_and_only_when_llms_txt_links_it(make_docs):
    root = make_docs(
        {
            "docs/llms.txt": "- [Guide](guide.md): g\n- [Runbooks](runbooks/README.md): r\n",
            "docs/guide.md": "# Guide\n",
            "docs/runbooks/README.md": "| a run is stuck | `stuck.md` |\n\n- [Slow](slow.md): s\n",
            "docs/runbooks/stuck.md": "# Stuck\n",
            "docs/runbooks/stuck.summary.md": "A summary.\n",
            "docs/runbooks/slow.md": "# Slow\n",
            "docs/runbooks/slow.summary.md": "A summary.\n",
            "docs/decisions/README.md": "- [ADR-0001 One](0001-one.md): o\n",
            "docs/decisions/0001-one.md": "# One\n",
            "docs/decisions/adr-template.md": "# Template\n",
        }
    )
    assert sorted(catalog.docs_check(root)["problems"]) == [
        "docs/llms.txt: decisions/0001-one.md is not listed",
        "docs/llms.txt: decisions/README.md is not listed",
        "docs/llms.txt: runbooks/stuck.md is not listed",
    ]


def test_a_plan_folder_is_listed_through_the_active_plans_readme_and_plan_lint_runs_inside(make_docs):
    root = make_docs(PLAN)
    assert catalog.docs_check(root) == {"ok": True, "problems": [], "warnings": []}
    extra = root / "docs" / "exec-plans" / "active" / "demo" / "task-03.md"
    extra.write_text("# Task 3 — Three\n", encoding="utf-8")
    assert catalog.docs_check(root)["problems"] == ["plan-lint: demo/task-03.md: not in the task order of 00-index.md"]
    extra.unlink()
    (root / "docs" / "exec-plans" / "active" / "README.md").write_text("# Active plans\n", encoding="utf-8")
    assert sorted(catalog.docs_check(root)["problems"]) == [
        "docs/llms.txt: exec-plans/active/demo/00-index.md is not listed",
        "docs/llms.txt: exec-plans/active/demo/task-01.md is not listed",
        "docs/llms.txt: exec-plans/active/demo/task-02.md is not listed",
    ]


def test_a_decision_page_or_runbook_without_its_summary_is_a_warning_not_a_problem(make_docs):
    """A2 (b), (c) of the index round; spec A5: docs-check warns."""
    root = make_docs(B_LISTINGS)
    (root / "docs" / "runbooks" / "server-windows.summary.md").unlink()
    out = catalog.docs_check(root)
    assert out["ok"] is True and out["problems"] == []
    assert out["warnings"] == ["docs/runbooks/server-windows.md: no summary server-windows.summary.md beside it"]
    (root / "wiki" / "decisions").mkdir(parents=True)
    (root / "wiki" / "decisions" / "x.md").write_text("# X\n", encoding="utf-8")
    (root / "wiki" / "decisions" / "y.md").write_text("# Y\n", encoding="utf-8")
    (root / "wiki" / "decisions" / "y.summary.md").write_text("A summary.\n", encoding="utf-8")
    out = catalog.docs_check(root)
    assert out["ok"] is True
    assert out["warnings"] == [
        "docs/runbooks/server-windows.md: no summary server-windows.summary.md beside it",
        "wiki/decisions/x.md: no summary x.summary.md beside it",
    ]


def too_long(rel: str, size: int) -> str:
    return f"{rel}: {size} bytes; a spec stays under 8000, and a longer one is a sign the brief asked for the plan"


def test_a_spec_file_that_is_not_under_8000_bytes_is_a_warning_not_a_problem(make_docs):
    """Requirement 5 of specs/005-spec-writer-rule: a spec is about one page, under 8,000 bytes, as the spec-writer's
    instruction says; exactly 8,000 is not under it."""
    files = {f"specs/00{n}-demo/spec.md": "x" * size for n, size in ((1, 7_999), (2, 8_000), (3, 8_001))}
    out = catalog.docs_check(make_docs({**B_LISTINGS, **files}))
    assert out["ok"] is True and out["problems"] == []
    assert out["warnings"] == [too_long("specs/002-demo/spec.md", 8_000), too_long("specs/003-demo/spec.md", 8_001)]


def test_the_spec_size_is_counted_in_bytes_not_characters(make_docs):
    text = "—" * 2_700  # 2,700 characters, 8,100 bytes
    assert (len(text), len(text.encode())) == (2_700, 8_100)
    out = catalog.docs_check(make_docs({**B_LISTINGS, "specs/001-demo/spec.md": text}))
    assert out["ok"] is True and out["warnings"] == [too_long("specs/001-demo/spec.md", 8_100)]


def test_only_the_spec_file_of_a_spec_folder_is_measured_and_all_warnings_are_sorted_by_path(make_docs):
    root = make_docs(
        {
            **B_LISTINGS,
            "specs/001-demo/spec.md": "x" * 9_000,
            "specs/001-demo/methods.md": "x" * 20_000,
            "specs/constitution.md": "x" * 20_000,
            "wiki/decisions/x.md": "# X\n",
        }
    )
    (root / "docs" / "runbooks" / "server-windows.summary.md").unlink()
    out = catalog.docs_check(root)
    assert out["ok"] is True and out["problems"] == []
    assert out["warnings"] == [
        "docs/runbooks/server-windows.md: no summary server-windows.summary.md beside it",
        too_long("specs/001-demo/spec.md", 9_000),
        "wiki/decisions/x.md: no summary x.summary.md beside it",
    ]


def test_the_repository_warns_of_each_of_its_specs_that_is_not_under_8000_bytes():
    sizes = {p.relative_to(REPO).as_posix(): p.stat().st_size for p in sorted((REPO / "specs").glob("*/spec.md"))}
    warned = [w.split(":")[0] for w in catalog.docs_check(REPO)["warnings"] if w.startswith("specs/")]
    assert warned == [rel for rel, size in sizes.items() if size >= 8_000] and len(sizes) >= 5


def test_prose_keeps_the_text_outside_fenced_blocks_and_inline_code():
    text = f"a [x](one.md) `[y](two.md)` b\n{FENCE}python\n[z](three.md)\n{FENCE}\nc [w](four.md)\n"
    assert catalog.LINK.findall(catalog.prose(text)) == ["one.md", "four.md"]
    longer = f"{FENCE}`\n{FENCE}\n[inside](five.md)\n{FENCE}\n{FENCE}`\n[after](six.md)\n"
    assert catalog.LINK.findall(catalog.prose(longer)) == ["six.md"]  # a fence closes only on one as long
    assert catalog.LINK.findall(catalog.prose("~~~\n[tilde](seven.md)\n~~~\n")) == []
    assert catalog.LINK.findall(catalog.prose(f"{FENCE}\n[open](eight.md)\n")) == []  # unclosed: code to the end


def test_links_inside_code_are_text_and_links_in_prose_must_resolve(make_docs):
    """As lychee reads Markdown without --include-verbatim; a plan's tests quote fixture links that are not links."""
    guide = (
        "# Guide\n\nSee [the index](llms.txt) and `[a fixture](gone.md)`.\n\n"
        f"{FENCE}python\nLINE = '- [Runbooks](runbooks/README.md): r'\n{FENCE}\n\n"
        "And [a real one](nowhere.md).\n"
    )
    root = make_docs({"docs/llms.txt": "- [Guide](guide.md): g\n", "docs/guide.md": guide})
    assert catalog.docs_check(root)["problems"] == ["docs/guide.md: broken link nowhere.md"]


def test_an_index_over_12000_bytes_is_a_problem(make_docs):
    """Small and layered (lessons.md, Known error classes: a flat index over 12 KB); 12 KB as the vault's split counts."""
    head = "- [Runbooks](runbooks/README.md): r\n"
    root = make_docs({"docs/llms.txt": head + "x" * (12_000 - len(head)), "docs/runbooks/README.md": "# Runbooks\n"})
    assert catalog.docs_check(root)["problems"] == []
    (root / "docs" / "llms.txt").write_text(head + "x" * (12_001 - len(head)), encoding="utf-8")
    (root / "docs" / "runbooks" / "README.md").write_text("é" * 6_001, encoding="utf-8")  # 12,002 bytes, 6,001 chars
    assert sorted(catalog.docs_check(root)["problems"]) == [
        "docs/llms.txt: 12001 bytes; an index stays at most 12000",
        "docs/runbooks/README.md: 12002 bytes; an index stays at most 12000",
    ]


def test_the_readme_a_project_keeps_of_its_template_is_a_document_not_an_index(make_docs):
    """S7: ops/new-project.py moves the root README, over 16 KB, into the project's docs/template/ folder; no other README
    of docs/ is spared the 12,000-byte rule."""
    kept, other = "/".join(catalog.KEPT_README), "docs/runbooks/README.md"
    llms = "- [Kept](template/README.md): k\n- [Runbooks](runbooks/README.md): r\n"
    root = make_docs({"docs/llms.txt": llms, kept: "x" * 16_000, other: "# Runbooks\n"})
    assert catalog.docs_check(root)["problems"] == []
    (root / other).write_text("x" * 12_001, encoding="utf-8")
    assert catalog.docs_check(root)["problems"] == [f"{other}: 12001 bytes; an index stays at most 12000"]


def test_a_project_made_from_the_template_passes_docs_check_with_the_template_readme_kept(tmp_path: Path):
    """S7: after the re-rooting every link of the kept README resolves in the project, reference-style ones too, the
    project's docs/llms.txt lists it and the project's own README is the stub."""
    project = tmp_path / "probe"
    command = [sys.executable, str(REPO / "ops" / "new-project.py"), str(project), "repo_name=probe", "--no-setup"]
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    kept = project.joinpath(*catalog.KEPT_README)
    assert (project / "README.md").read_text(encoding="utf-8").startswith("# probe\n")
    assert len(kept.read_bytes()) > catalog.INDEX_MAX_BYTES
    assert catalog.docs_check(project)["problems"] == []
    defined = re.findall(r"^\[[^\]]+\]:[ \t]*(\S+)", kept.read_text(encoding="utf-8"), re.MULTILINE)
    assert defined and [link for link in defined if not (kept.parent / link).exists()] == []


def test_the_repository_lists_its_decisions_in_their_own_index():
    llms = (REPO / "docs" / "llms.txt").read_text(encoding="utf-8")
    readme = (REPO / "docs" / "decisions" / "README.md").read_text(encoding="utf-8")
    assert "(decisions/README.md)" in llms and "(decisions/0" not in llms
    adrs = sorted(p.name for p in (REPO / "docs" / "decisions").glob("[0-9][0-9][0-9][0-9]-*.md"))
    assert adrs and [name for name in adrs if f"({name})" not in readme] == []
    assert "(adr-template.md)" in readme
    for index in ("docs/llms.txt", "docs/decisions/README.md", "docs/exec-plans/active/README.md"):
        assert len((REPO / index).read_bytes()) <= 12_000, index


def test_adr_0026_records_the_layering():
    found = sorted((REPO / "docs" / "decisions").glob("0026-*.md"))
    assert [p.name for p in found] == ["0026-plans-in-parts-and-layered-document-indexes.md"]
    text = found[0].read_text(encoding="utf-8")
    assert text.startswith("---\nstatus: accepted\n")
    for heading in ("## Context and Problem Statement", "## Considered Options", "## Decision Outcome"):
        assert heading in text, heading
    for heading in ("### Consequences", "### Confirmation", "## More Information"):
        assert heading in text, heading
    assert "plan-lint" in text and "README.md" in text and ".summary.md" in text and "1,500" in text
    assert "](../../design/" not in text  # design/ is under omit: in docs/template/variables.yaml


def test_the_pages_rules_and_skill_describe_the_layers():
    page = REPO / "docs" / "architecture" / "documentation.md"
    text = page.read_text(encoding="utf-8").lower()
    for words in ("user guide", "design wiki", "balance tables", "runbooks", "decisions", ".summary.md", "plan-lint"):
        assert words in text, words
    assert "12,000 bytes" in text and "1,500 lines" in text and len(page.read_bytes()) <= 12_000
    assert (REPO / "docs" / "architecture" / "documentation.summary.md").is_file()
    assert "(architecture/documentation.md)" in (REPO / "docs" / "llms.txt").read_text(encoding="utf-8")
    active = (REPO / "docs" / "exec-plans" / "active" / "README.md").read_text(encoding="utf-8")
    assert "00-index.md" in active and "task-NN.md" in active and "plan-lint" in active and "plansDirectory" in active
    assert "One file per plan" not in active
    rules = (REPO / ".claude" / "rules" / "docs.md").read_text(encoding="utf-8")
    assert "README.md" in rules and "12,000 bytes" in rules and ".summary.md" in rules
    skill = (REPO / ".claude" / "skills" / "adr" / "SKILL.md").read_text(encoding="utf-8")
    assert "docs/decisions/README.md" in skill and 'under "Decisions"' not in skill
