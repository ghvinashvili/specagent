"""The vault form and ops/new-vault.py (spec 11.1 and 11.3; wiki/decisions/the-shared-knowledge-base.md): every user of
the template gets a vault of their own, made from templates/vault/ with an opaque origin id, one commit and the commons
named; ops/new-project.py makes it for a `vault_path` without an INDEX.md; the form holds the global pages that
ops/sync-vault-globals.py carried into it (spec 006, R5) and nothing of the owner's vault."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
FORM = REPO / "templates" / "vault"
SCRIPT = REPO / "ops" / "new-vault.py"
SCRIPTS = ("outline.py", "check_pages.py", "split_large.py", "build_indexes.py", "collect_memory.py")
FORM_FILES = (
    "README.md",
    "rules.md",
    "INDEX.md",
    "log.md",
    "decisions/global/.gitkeep",
    "context/owner-statements/.gitkeep",
    "context/measurements/.gitkeep",
    "concepts/.gitkeep",
    "ops/memory-topics.json",
    *(f"ops/{name}" for name in SCRIPTS),
)
# what ops/sync-vault-globals.py carried into the form (spec 006, R5): the global pages, the measurement pages that
# prove them, and the documents of context/ that ops/build_indexes.py lists
GLOBAL_PAGES = sorted((FORM / "decisions" / "global").glob("*.md"))
MEASUREMENT_PAGES = sorted((FORM / "context" / "measurements").glob("*.md"))
CONTEXT_DOCUMENTS = [p for p in (FORM / "context").rglob("*") if p.is_file() and not p.name.startswith(".")]
# the owner's own vault: its projects, its domain, its folders, its guide, its home folder and its account
OWNER = re.compile(
    r"(?i)trading|brooks|grantsdaily|gexhex|spoofing|zerogamma|design-record|structure-handoff|README\.ka|\btite\b"
    r"|ghvinashvili"
)
GEORGIAN = re.compile("[" + chr(0x10A0) + "-" + chr(0x10FF) + "]")
DOMAIN_PAGE = """---
title: Salt late
type: decision
scope: {scope}
status: verified
updated: 2026-10-29
audience: [all]
sources: [https://example.org/salt]
decided: 2026-10-29
by: owner
why: measured twice
decision_status: decided
would_change_if: a tasting that finds no difference
---
# Salt late
"""


def LESSON_KIND(page: str) -> str:
    """A global page names its kind (spec 006): the fixture is a lesson."""
    return page.replace("decision_status: decided\n", "decision_status: decided\nkind: lesson\n")


def git_env() -> dict[str, str]:
    """A git identity and no global or system configuration: the result does not depend on this machine's git setup."""
    who = {
        f"GIT_{role}_{key}": val for role in ("AUTHOR", "COMMITTER") for key, val in (("NAME", "t"), ("EMAIL", "t@t"))
    }
    return {**os.environ, **who, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args], cwd=cwd, capture_output=True, text=True, env=git_env(), check=False, timeout=120
    )


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, env=git_env(), check=True
    ).stdout


def variables() -> list[dict]:
    return yaml.safe_load((REPO / "docs" / "template" / "variables.yaml").read_text(encoding="utf-8"))["variables"]


def origin(vault: Path) -> str:
    head = re.match(r"---\norigin: ([0-9a-f]{12})\n---\n", (vault / "README.md").read_text(encoding="utf-8"))
    assert head, "README.md starts with the frontmatter that holds the origin id"
    return head.group(1)


def section(text: str, heading: str) -> str:
    lines = text.splitlines()
    start = lines.index(heading)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start + 1 : end])


def closing_line(output: str) -> str:
    """The last line of a script's output, e.g. `30 pages checked, 0 problems` (a substring test would take
    `30 pages checked` for `0 pages checked`)."""
    return output.strip().splitlines()[-1]


def frontmatter(path: Path) -> dict[str, str]:
    """The `key: value` lines between the first two `---` lines of a page, values as written (YAML would read
    `template: yes` as a boolean)."""
    head = path.read_text(encoding="utf-8").split("\n---\n", 1)[0].removeprefix("---\n")
    return {m.group(1): m.group(2) for m in re.finditer(r"(?m)^([a-z_]+): (.*)$", head)}


def test_a_new_vault_is_the_form_with_an_origin_id_one_commit_and_the_commons_named(tmp_path: Path):
    vault, commons = tmp_path / "notes", tmp_path / "shared"
    done = run(str(SCRIPT), str(vault), f"commons_path={commons}")
    assert done.returncode == 0, done.stdout + done.stderr
    for rel in FORM_FILES:
        assert (vault / rel).is_file(), rel
    assert f"commons_path: {commons}" in (vault / "INDEX.md").read_text(encoding="utf-8").splitlines()[:8]
    assert origin(vault) in (vault / "log.md").read_text(encoding="utf-8")
    assert git(vault, "rev-list", "--count", "HEAD").strip() == "1"
    assert git(vault, "status", "--porcelain") == "" and git(vault, "remote") == ""
    assert origin(vault) in done.stdout and "private" in done.stdout and "remote add origin" in done.stdout


def test_each_vault_draws_its_own_origin_and_names_the_default_commons(tmp_path: Path):
    first, second = tmp_path / "a", tmp_path / "b"
    assert run(str(SCRIPT), str(first)).returncode == 0 and run(str(SCRIPT), str(second)).returncode == 0
    assert origin(first) != origin(second)
    default = next(v["default"] for v in variables() if v["name"] == "commons_path")
    assert f"commons_path: {default}" in (first / "INDEX.md").read_text(encoding="utf-8")


def test_a_target_that_is_not_empty_is_refused_and_left_as_it_was(tmp_path: Path):
    target = tmp_path / "notes"
    target.mkdir()
    (target / "mine.md").write_text("mine\n", encoding="utf-8")
    done = run(str(SCRIPT), str(target))
    assert done.returncode == 1 and "not empty" in done.stdout
    assert sorted(p.name for p in target.iterdir()) == ["mine.md"]
    assert run(str(SCRIPT)).returncode == 2
    unknown = run(str(SCRIPT), str(tmp_path / "other"), "commons=x")
    assert unknown.returncode == 2 and not (tmp_path / "other").exists()


def test_a_machine_without_a_git_identity_is_told_so_before_anything_is_written(tmp_path: Path):
    env = {k: v for k, v in git_env().items() if not k.startswith(("GIT_AUTHOR_", "GIT_COMMITTER_")) and k != "EMAIL"}
    env |= {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "user.useConfigOnly", "GIT_CONFIG_VALUE_0": "true"}
    target = tmp_path / "notes"
    done = subprocess.run(
        [sys.executable, str(SCRIPT), str(target)], capture_output=True, text=True, env=env, check=False
    )
    assert done.returncode == 1 and "user.email" in done.stdout and not target.exists()


def test_the_fresh_vault_passes_its_own_checks_and_builds_its_indexes(tmp_path: Path):
    vault = tmp_path / "notes"
    assert run(str(SCRIPT), str(vault)).returncode == 0
    check = run("ops/check_pages.py", cwd=vault)
    assert GLOBAL_PAGES, "the template carries global pages (spec 006, R5)"
    assert check.returncode == 0 and closing_line(check.stdout) == f"{len(GLOBAL_PAGES)} pages checked, 0 problems", (
        check.stdout
    )
    assert run("ops/split_large.py", "--dry-run", cwd=vault).returncode == 0
    built = run("ops/build_indexes.py", cwd=vault)
    assert built.returncode == 0, built.stdout + built.stderr
    assert built.stdout.startswith(f"{len(CONTEXT_DOCUMENTS)} documents in "), built.stdout + built.stderr
    assert not [p for p in (vault / "context" / "_index").glob("*.md") if ".gitkeep" in p.read_text(encoding="utf-8")]
    assert run("ops/outline.py", "rules.md", cwd=vault).returncode == 0


def test_a_domain_decision_with_a_public_source_passes_the_vaults_check(tmp_path: Path):
    vault = tmp_path / "notes"
    assert run(str(SCRIPT), str(vault)).returncode == 0
    page = vault / "decisions" / "cooking" / "salt-late.md"
    page.parent.mkdir(parents=True)
    page.write_text(DOMAIN_PAGE.format(scope="cooking"), encoding="utf-8")
    index = vault / "INDEX.md"
    line = "- [salt-late](decisions/cooking/salt-late.md): late\n"
    index.write_text(index.read_text(encoding="utf-8") + line, encoding="utf-8")
    check = run(str(vault / "ops" / "check_pages.py"), str(vault))
    assert check.returncode == 0, check.stdout
    page.write_text(DOMAIN_PAGE.format(scope="global"), encoding="utf-8")
    check = run(str(vault / "ops" / "check_pages.py"), str(vault))
    assert check.returncode == 1 and "not under decisions/global/" in check.stdout


def test_a_global_decision_names_an_existing_proof_page_under_context(tmp_path: Path):
    vault = tmp_path / "notes"
    assert run(str(SCRIPT), str(vault)).returncode == 0
    page = vault / "decisions" / "global" / "salt-late.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    index = vault / "INDEX.md"
    index.write_text(
        index.read_text(encoding="utf-8") + "- [salt-late](decisions/global/salt-late.md): late\n", encoding="utf-8"
    )
    today = LESSON_KIND(DOMAIN_PAGE.replace("2026-10-29", "2026-10-31").format(scope="global"))
    page.write_text(today, encoding="utf-8")
    check = run(str(vault / "ops" / "check_pages.py"), str(vault))
    assert check.returncode == 1 and "names its proof" in check.stdout, check.stdout
    proven = today.replace(
        "why: measured twice\n", "why: measured twice\nproof: [context/measurements/2026-10-31-salt.md]\n"
    )
    page.write_text(proven, encoding="utf-8")
    check = run(str(vault / "ops" / "check_pages.py"), str(vault))
    assert check.returncode == 1 and "is not an existing page under context/" in check.stdout, check.stdout
    (vault / "context" / "measurements").mkdir(parents=True, exist_ok=True)
    (vault / "context" / "measurements" / "2026-10-31-salt.md").write_text("# Salt, measured twice\n", encoding="utf-8")
    check = run(str(vault / "ops" / "check_pages.py"), str(vault))
    assert check.returncode == 0, check.stdout
    old = LESSON_KIND(DOMAIN_PAGE.format(scope="global"))  # decided before the rule: its proof is asked all the same
    page.write_text(old, encoding="utf-8")
    check = run(str(vault / "ops" / "check_pages.py"), str(vault))
    assert check.returncode == 1 and "names its proof" in check.stdout, check.stdout


def test_a_page_copied_from_the_manager_lessons_form_passes_the_check_once_its_proof_is_set(tmp_path: Path):
    # The form is a global lesson (spec 006): it names `kind: lesson` and a `proof:`, so the page copied from it is
    # refused while the proof is a placeholder and passes when the copy sentence of the form has been followed.
    vault = tmp_path / "notes"
    assert run(str(SCRIPT), str(vault)).returncode == 0
    form = (vault / "forms" / "manager-lessons.md").read_text(encoding="utf-8")
    assert "\nkind: lesson\n" in form and "\nproof: [context/measurements/" in form
    page = vault / "decisions" / "global" / "manager-lessons.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(form, encoding="utf-8")
    index = vault / "INDEX.md"
    index.write_text(
        index.read_text(encoding="utf-8") + "- [manager-lessons](decisions/global/manager-lessons.md): own mistakes\n",
        encoding="utf-8",
    )
    statements = vault / "context" / "owner-statements"
    statements.mkdir(parents=True, exist_ok=True)
    (statements / "2026-10-31.md").write_text("# 2026-10-31\n", encoding="utf-8")
    check = run(str(vault / "ops" / "check_pages.py"), str(vault))
    assert check.returncode == 1 and "proof `context/measurements/" in check.stdout, check.stdout
    measurements = vault / "context" / "measurements"
    measurements.mkdir(parents=True, exist_ok=True)
    (measurements / "2026-10-31-demo.md").write_text("# Demo run, measured\n", encoding="utf-8")
    page.write_text(form.replace("YYYY-MM-DD-<run>", "2026-10-31-demo").replace("YYYY-MM-DD", "2026-10-31"), "utf-8")
    check = run(str(vault / "ops" / "check_pages.py"), str(vault))
    expected = f"{len(GLOBAL_PAGES) + 1} pages checked, 0 problems"  # the carried pages and the page of the form
    assert check.returncode == 0 and closing_line(check.stdout) == expected, check.stdout


def test_the_form_holds_nothing_of_the_owners_vault():
    for path in sorted(p for p in FORM.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        text = path.read_text(encoding="utf-8")
        found = OWNER.search(text)
        assert not found, f"{path.relative_to(REPO)}: {found.group(0) if found else ''}"
        assert not GEORGIAN.search(text), path
    topics = json.loads((FORM / "ops" / "memory-topics.json").read_text(encoding="utf-8"))
    assert topics["topics"] == {} and topics["files"] == {}
    assert not list(FORM.rglob("concepts/*.md"))
    for page in GLOBAL_PAGES:  # what the template carries is meant for every project and names its kind (spec 006)
        meta = frontmatter(page)
        assert meta.get("template") == "yes" and meta.get("kind") in ("lesson", "order"), page.name
        assert meta.get("scope") == "global" and meta.get("decision_status") != "withdrawn", page.name


def test_a_fresh_vault_holds_every_carried_page_byte_for_byte_and_its_index_line(tmp_path: Path):
    # R5: ops/new-vault.py copies templates/vault whole, so the pages and the INDEX lines the sync wrote come with it.
    vault = tmp_path / "notes"
    assert run(str(SCRIPT), str(vault)).returncode == 0
    assert GLOBAL_PAGES and MEASUREMENT_PAGES
    for page in [*GLOBAL_PAGES, *MEASUREMENT_PAGES]:
        assert (vault / page.relative_to(FORM)).read_bytes() == page.read_bytes(), page.name
    listed = section((vault / "INDEX.md").read_text(encoding="utf-8"), "## Decisions (global)")
    entries = [ln for ln in listed.splitlines() if ln.strip()]
    for page in GLOBAL_PAGES:
        mine = [ln for ln in entries if ln.startswith(f"- [{page.stem}](decisions/global/{page.name}): ")]
        assert len(mine) == 1 and len(mine[0].split(": ", 1)[1].strip()) > 0, page.name
    assert len(entries) == len(GLOBAL_PAGES), "one INDEX line per carried page, and no other line in the section"


def test_commons_path_follows_vault_path_and_claude_md_names_the_commons():
    names = [v["name"] for v in variables()]
    assert names.index("commons_path") == names.index("vault_path") + 1
    assert next(v for v in variables() if v["name"] == "commons_path")["default"] == "~/aftpro-commons"
    body = section((REPO / "CLAUDE.md").read_text(encoding="utf-8"), "## The owner's vault")
    for words in ("`~/aftpro-commons`", "a source, not an authority", "the vault page wins", "as a finding"):
        assert words in body, words


def test_new_project_makes_the_vault_when_its_index_is_missing_and_leaves_a_vault_alone(tmp_path: Path):
    vault, commons, script = tmp_path / "notes", tmp_path / "shared", str(REPO / "ops" / "new-project.py")
    made = run(script, str(tmp_path / "one"), f"vault_path={vault}", f"commons_path={commons}", "--no-setup")
    assert made.returncode == 0, made.stdout + made.stderr
    assert f"commons_path: {commons}" in (vault / "INDEX.md").read_text(encoding="utf-8")
    head = git(vault, "rev-parse", "HEAD")
    again = run(script, str(tmp_path / "two"), f"vault_path={vault}", "--no-setup")
    assert (
        again.returncode == 0 and git(vault, "rev-parse", "HEAD") == head and git(vault, "status", "--porcelain") == ""
    )
    taken = tmp_path / "taken"
    taken.mkdir()
    (taken / "mine.md").write_text("mine\n", encoding="utf-8")
    refused = run(script, str(tmp_path / "three"), f"vault_path={taken}", "--no-setup")
    assert refused.returncode == 1 and "not empty" in refused.stdout and not (tmp_path / "three").exists()
