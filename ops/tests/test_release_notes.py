"""The 1.6.0 entry of docs/template/MIGRATIONS.md and the [Unreleased] notes of CHANGELOG.md say what holds: a project
copies the template's changes over its own except the files it keeps its own lines in (merged by hand) and the files
that are its own record (read, not copied), and the cleanup of the owner's words stops at the captured sources."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MERGED = (
    "CLAUDE.md",
    "AGENTS.md",
    "ARCHITECTURE.md",
    "pyproject.toml",
    ".claude/settings.json",
    ".vault-meta/lint-allowlist.json",
    "docs/llms.txt",
    "docs/template/variables.yaml",
    "wiki/index.md",
    "wiki/log.md",
    "wiki/hot.md",
    "docs/exec-plans/active/README.md",
)
RECORDS = ("wiki/meta/ledgers/", ".raw/.manifest.json")


def bullets(version: str) -> dict[str, str]:
    """The one-line bullets of one migration entry by their first words."""
    text = (ROOT / "docs" / "template" / "MIGRATIONS.md").read_text(encoding="utf-8")
    entry = re.search(rf"(?ms)^## {re.escape(version)}\n(.*?)(?=^## |\Z)", text)
    assert entry, version
    return dict(re.findall(r"(?m)^- ([^:]+): (.*)$", entry.group(1)))


def test_a_file_a_project_keeps_its_own_lines_in_is_merged_by_hand():
    steps = bullets("1.6.0")["Steps"]
    (merged,) = re.findall(
        r"merge these by hand, keeping the project's lines and adding the template's: (.*?) \(a plan of", steps
    )
    assert [path for path in MERGED if f"`{path}`" not in merged] == []


def test_the_projects_own_record_is_read_not_copied():
    copied, _, rest = bullets("1.6.0")["Changed template-owned paths"].partition("; read, not copied: ")
    read = rest.partition("; never copied")[0]
    assert [path for path in RECORDS if f"`{path}`" in copied or f"`{path}`" not in read] == []


def test_the_changelog_says_where_the_cleanup_of_the_owners_words_stops():
    unreleased = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").split("\n## [1.5.0]")[0]
    (bullet,) = re.findall(r"(?ms)^- (No tracked text of the template .*?)(?=^- |^### |\Z)", unreleased)
    assert [path for path in (".raw/captured/", "wiki/meta/ledgers/claim-ledger.json") if path not in bullet] == []
