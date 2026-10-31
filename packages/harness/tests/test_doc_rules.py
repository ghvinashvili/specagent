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
