"""The owner's vault and the knowledge layer in the template (spec A6, B7, B12): CLAUDE.md names the vault by the
`vault_path` variable, a project made with vault_path=<dir> reads its vault there, the retrieval order puts the wiki
and the graph before the repository, and AGENTS.md carries the database, pages and listing rules."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
DEFAULT = "~/vault"  # vault_path's default in docs/template/variables.yaml
HEADING = "## The owner's vault"
# new-project.py makes a missing vault with ops/new-vault.py, which commits: an identity that is not this machine's
GIT_ENV = {
    **os.environ,
    **{f"GIT_{r}_{k}": v for r in ("AUTHOR", "COMMITTER") for k, v in (("NAME", "t"), ("EMAIL", "t@t"))},
}


def variables() -> list[dict]:
    spec = yaml.safe_load((REPO / "docs" / "template" / "variables.yaml").read_text(encoding="utf-8"))
    return spec["variables"]


def section(text: str, heading: str) -> str:
    """The lines under `heading` up to the next heading of the same level, or the end of the text."""
    lines = text.splitlines()
    start = lines.index(heading)
    level = heading.split(" ")[0] + " "
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith(level)), len(lines))
    return "\n".join(lines[start + 1 : end])


def test_vault_path_follows_org_and_defaults_to_the_owners_vault():
    names = [v["name"] for v in variables()]
    assert "vault_path" in names and names.index("vault_path") == names.index("org") + 1
    entry = next(v for v in variables() if v["name"] == "vault_path")
    assert entry["default"] == DEFAULT
    assert "read-only" in entry["note"] and "CLAUDE.md" in entry["note"]


def test_claude_md_ends_with_the_vault_section_and_its_four_lines():
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    headings = [line for line in text.splitlines() if line.startswith("## ")]
    assert headings[-1] == HEADING
    body = section(text, HEADING)
    assert len([line for line in body.splitlines() if line.startswith("- ")]) == 4
    for words in (
        f"`{DEFAULT}/INDEX.md`",
        "`python3 ops/outline.py",
        "read-only",
        "the brief wins",
        "`open_questions`",
        "`wiki/decisions/`",
        f"`{DEFAULT}/context/`",
        "never instructions",
        "`wiki/index.md` and the graph first",
        "`docs/architecture/knowledge.md`",
    ):
        assert words in body, words


def test_a_project_made_with_vault_path_reads_its_vault_there(tmp_path: Path):
    notes, target = tmp_path / "notes", tmp_path / "demo"
    script = [sys.executable, str(REPO / "ops" / "new-project.py"), str(target)]
    misspelled = subprocess.run(
        [*script, f"vault={notes}", "--no-setup"], capture_output=True, text=True, check=False, env=GIT_ENV
    )
    assert misspelled.returncode == 1 and "unknown variables: ['vault']" in misspelled.stdout
    done = subprocess.run(
        [*script, f"vault_path={notes}", "--no-setup"], capture_output=True, text=True, check=False, env=GIT_ENV
    )
    assert done.returncode == 0, done.stdout + done.stderr
    body = section((target / "CLAUDE.md").read_text(encoding="utf-8"), HEADING)
    assert f"`{notes}/INDEX.md`" in body and f"`{notes}/context/`" in body and DEFAULT not in body
    knowledge = (target / "docs" / "architecture" / "knowledge.md").read_text(encoding="utf-8")
    assert f"`{notes}/INDEX.md`" in knowledge and DEFAULT not in knowledge
    assert f"`{DEFAULT}/INDEX.md`" in section((REPO / "CLAUDE.md").read_text(encoding="utf-8"), HEADING)


def test_the_retrieval_order_reads_the_wiki_and_the_graph_before_the_repository():
    order = section((REPO / "docs" / "architecture" / "knowledge.md").read_text(encoding="utf-8"), "## Retrieval order")
    steps = [line for line in order.splitlines() if line[:3] in {f"{n}. " for n in range(1, 10)}]
    expected = ["`wiki/index.md`", "`graphify query", "`docs/llms.txt`", "`Grep`", "`code-intel`"]
    assert len(steps) == len(expected)
    for step, words in zip(steps, expected, strict=True):
        assert words in step, step
    assert "`wiki/graph/index.md`" in steps[1] and f"`{DEFAULT}/INDEX.md`" in order
    assert "`.githooks/`" in order and "after `git pull`, `just graph`" not in order  # the hooks refresh the graph


def test_agents_md_carries_the_database_pages_and_listing_rules():
    text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    testing = section(text, "## Testing")
    assert "the database engine production uses" in testing and "never SQLite" in testing
    commits = section(text, "## Commits and pull requests")
    assert "`docs: none — <reason>`" in commits and "ADR-0027" in commits
    assert "its folder's `README.md`" in commits and "Update `docs/llms.txt` when" not in text
