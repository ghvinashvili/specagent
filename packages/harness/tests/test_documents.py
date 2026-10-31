"""What the documents say of the guards and of wave 1 agrees with what the code does and the tests show (R10, R11, R12
of run 20261009-022929-fix-w1-revise): a guard refuses the plain spellings of a command, and what a command builds at
run time is held by the sandbox and the write gate (docs/decisions/0025, which narrows 0020)."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
ADR_0020 = "0020-hooks-and-gates-fail-closed-and-open-nothing-outside-a-stage.md"
PROMISES = ("any spelling", "every spelling", "by no spelling", "matter of spelling", "as the shell reads",
            "as the shell does", "by_no_spelling", "every_spelling")  # fmt: skip
SAID = ["CHANGELOG.md", "docs/roles/CHANGELOG.md", "docs/architecture/harness.md", "docs/llms.txt",
        ".claude/hooks/guard-checkout.py", ".claude/hooks/guard-bash.py", ".claude/hooks/shellwords.py",
        "packages/harness/tests/test_guards.py", "docs/decisions/README.md"]  # fmt: skip


def adr_0025() -> Path:
    found = sorted((REPO / "docs" / "decisions").glob("0025-*.md"))
    assert len(found) == 1, found
    return found[0]


@pytest.mark.parametrize("rel", SAID)
def test_no_document_says_a_guard_refuses_every_spelling(rel: str):
    """R11: a guard that reads a command's text cannot refuse every spelling (wave 1's critic and verifier found new ones
    in every round); the documents, docstrings and test names say what the guards do."""
    text = " ".join((REPO / rel).read_text(encoding="utf-8").split()).lower()  # a phrase may cross a line break
    assert [p for p in PROMISES if p in text] == []


def test_the_changelog_names_only_the_hook_findings_wave_1_closed():
    """R10: 04/F8 and 04/F12 to F15 belong to waves 3 and 6."""
    text = " ".join((REPO / "CHANGELOG.md").read_text(encoding="utf-8").split())  # a sentence may cross a line break
    assert "04/F1 to F17" not in text
    assert "04/F1 to F7, F9 to F11, F16 and F17" in text


def test_the_architecture_says_guard_checkout_refuses_the_shared_checkout_also_from_inside_the_checkout():
    """R12: the repaired guard refuses wherever the shell stands, not only until the session is in its checkout."""
    text = (REPO / "docs" / "architecture" / "harness.md").read_text(encoding="utf-8")
    assert "until the session is inside its checkout" not in text
    assert "wherever the shell stands" in text


def test_adr_0025_narrows_adr_0020_which_points_to_it():
    """R11, and an accepted ADR is never edited but for one pointer line under More Information (.claude/rules/docs.md)."""
    new = adr_0025()
    text = new.read_text(encoding="utf-8")
    assert text.startswith("---\nstatus: accepted\n") and ADR_0020 in text
    for heading in ("## Context and Problem Statement", "## Decision Outcome", "### Consequences", "### Confirmation"):
        assert heading in text, heading
    assert "plain spellings" in text and "sandbox" in text and "write gate" in text
    old = (REPO / "docs" / "decisions" / ADR_0020).read_text(encoding="utf-8")
    assert "## More Information" in old and f"Amended by [ADR-0025]({new.name})" in old
    assert f"({new.name})" in (REPO / "docs" / "decisions" / "README.md").read_text(encoding="utf-8")  # ADR-0026
    assert "(decisions/README.md)" in (REPO / "docs" / "llms.txt").read_text(encoding="utf-8")
