"""harness audit measures the memory indexes that agent memory loads (spec B13; vault load-on-need): a MEMORY.md over
5,000 bytes is a warning and never fails `audit --ci`; rules in subfolders of .claude/rules are instruction files too,
since Claude Code discovers them recursively."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml
from harness import audit

REPO = Path(__file__).resolve().parents[3]


def make_root(tmp_path: Path) -> Path:
    """A repository root with the real budget file, settings without hooks and no instruction file."""
    root = tmp_path / "repo"
    (root / "docs" / "quality").mkdir(parents=True)
    shutil.copy(REPO / "docs" / "quality" / "context-budget.yaml", root / "docs" / "quality" / "context-budget.yaml")
    (root / ".claude").mkdir()
    (root / ".claude" / "settings.json").write_text("{}\n", encoding="utf-8")
    return root


def write(root: Path, rel: str, text: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")


def test_a_memory_index_over_5000_bytes_is_a_warning_counted_in_bytes(tmp_path):
    root = make_root(tmp_path)
    write(root, ".claude/agent-memory/manager/MEMORY.md", "€" * 1667)  # 5,001 bytes, 1,667 characters
    write(root, ".claude/agent-memory-local/helper/MEMORY.md", "x" * 5000)
    write(root, ".claude/agent-memory/manager/patterns.md", "y" * 9000)  # a topic file, read on need
    out = audit.context_audit(root, ci=True)
    assert out["ok"] is True  # a warning never fails the CI audit
    assert out["memory_indexes"] == [
        {"file": ".claude/agent-memory-local/helper/MEMORY.md", "bytes": 5000},
        {"file": ".claude/agent-memory/manager/MEMORY.md", "bytes": 5001},
    ]
    assert [f for f in out["findings"] if f["limit"] == "memory_index_max_bytes"] == [
        {
            "limit": "memory_index_max_bytes",
            "severity": "warning",
            "where": ".claude/agent-memory/manager/MEMORY.md",
            "value": 5001,
            "max": 5000,
        }
    ]


def test_a_tree_without_agent_memory_has_no_memory_index(tmp_path):
    out = audit.context_audit(make_root(tmp_path))
    assert out["memory_indexes"] == [] and out["findings"] == []


def test_rules_in_subfolders_are_instruction_files(tmp_path):
    """The critic's "To check" of the index round: Task 8 puts rules under .claude/rules/ecc/<language>/."""
    root = make_root(tmp_path)
    write(root, ".claude/rules/ecc/python/coding-style.md", "line\n" * 201)
    out = audit.context_audit(root, ci=True)
    assert out["ok"] is False
    assert [(f["limit"], f["where"]) for f in out["findings"] if f["severity"] == "error"] == [
        ("instruction_file_max_lines", ".claude/rules/ecc/python/coding-style.md")
    ]


def test_the_budget_file_and_its_page_state_the_memory_limit_and_its_source():
    budget = yaml.safe_load((REPO / "docs" / "quality" / "context-budget.yaml").read_text(encoding="utf-8"))
    limit = budget["limits"]["memory_index_max_bytes"]
    assert (limit["value"], limit["severity"]) == (5000, "warning")
    assert "load-on-need" in limit["source"] and "25KB" in limit["source"]
    assert budget["memory_globs"] == [".claude/agent-memory/*/MEMORY.md", ".claude/agent-memory-local/*/MEMORY.md"]
    assert ".claude/rules/**/*.md" in budget["instruction_globs"]
    assert ".claude/rules/*.md" not in budget["instruction_globs"]
    page = (REPO / "docs" / "quality" / "CONTEXT_BUDGET.md").read_text(encoding="utf-8")
    assert "MEMORY.md" in page and "5,000 bytes" in page and "/memory" in page
