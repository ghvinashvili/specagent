"""ops/contribute.py (spec 11.2 and 11.4; wiki/decisions/the-shared-knowledge-base.md): one global decision or concept
of the user's vault goes to the commons as a candidate page, with its evidence, on a branch of the clone and by pull
request; every refusal names its class, prints no secret, writes nothing, and no flag skips a check."""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "ops" / "contribute.py"
FIELDS = ["title", "summary", "type", "scope", "status", "projects", "sources", "would_change_if", "licence", "updated"]
PAGE = """---
title: Salt late
type: {type}
scope: global
status: {status}
updated: 2026-10-29
audience: [all]
sources: [{sources}]
decided: 2026-10-29
by: owner
why: measured twice
decision_status: decided
{would_change_if}{extra}---
# Salt late

Salt goes in at the end: {body}
"""
EVIDENCE = "# Tasting\n\nTen tasters of ten preferred the late salt.\n"
KEY = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1"  # the form of a GitHub token, built here so that no scanner sees one


def git_env() -> dict[str, str]:
    """A git identity and no global or system configuration: the result does not depend on this machine's git setup."""
    who = {
        f"GIT_{role}_{key}": val for role in ("AUTHOR", "COMMITTER") for key, val in (("NAME", "t"), ("EMAIL", "t@t"))
    }
    return {**os.environ, **who, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, env=git_env(), check=True
    ).stdout


def refs(repo: Path) -> str:
    return git(repo, "for-each-ref", "--format=%(refname) %(objectname)")


@pytest.fixture
def world(tmp_path: Path) -> SimpleNamespace:
    """A project (the script, the secret patterns, variables.yaml naming the vault and the clone), a vault made by
    ops/new-vault.py, a seeded commons with its clone, evidence, and a fake gh first on PATH that records its argv."""
    project, vault, seed, clone = (tmp_path / name for name in ("project", "vault", "seed", "clone"))
    for rel in ("ops/contribute.py", "templates/vault/ops/collect_memory.py"):
        (project / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, project / rel)
    spec = {
        "variables": [{"name": "vault_path", "default": str(vault)}, {"name": "commons_path", "default": str(clone)}]
    }
    (project / "docs" / "template").mkdir(parents=True)
    (project / "docs" / "template" / "variables.yaml").write_text(yaml.safe_dump(spec), encoding="utf-8")
    made = subprocess.run(
        [sys.executable, str(REPO / "ops" / "new-vault.py"), str(vault), f"commons_path={clone}"],
        capture_output=True,
        text=True,
        env=git_env(),
        check=False,
    )
    assert made.returncode == 0, made.stdout + made.stderr
    seed.mkdir()
    (seed / "INDEX.md").write_text("# Index of the commons\n", encoding="utf-8")
    git(seed, "init", "-q", "-b", "main")
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "seed")
    git(tmp_path, "clone", "-q", str(seed), str(clone))
    tools, argv = tmp_path / "bin", tmp_path / "gh-argv"
    tools.mkdir()
    (tools / "gh").write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" >> {argv}\necho https://example.org/pull/1\n")
    (tools / "gh").chmod(0o755)
    evidence = tmp_path / "public" / "tasting.md"
    evidence.parent.mkdir()
    evidence.write_text(EVIDENCE, encoding="utf-8")
    origin = re.match(r"---\norigin: ([0-9a-f]{12})\n", (vault / "README.md").read_text(encoding="utf-8")).group(1)
    return SimpleNamespace(
        tmp=tmp_path,
        project=project,
        vault=vault,
        seed=seed,
        clone=clone,
        tools=tools,
        argv=argv,
        evidence=evidence,
        origin=origin,
    )


def page(world: SimpleNamespace, folder: str = "decisions/global", name: str = "salt-late", **fields: str) -> Path:
    """A vault page in the form of the vault's rules, listed in INDEX.md; `fields` replaces a part of PAGE."""
    values = {
        "type": "decision",
        "status": "verified",
        "sources": "https://example.org/salt, context/measurements/tasting.md",
        "would_change_if": "would_change_if: a tasting that finds no difference\n",
        "extra": "",
        "body": "the tasting found it better.",
        **fields,
    }
    path = world.vault / folder / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PAGE.format(**values), encoding="utf-8")
    index = world.vault / "INDEX.md"
    line = f"- [{name}]({folder}/{name}.md): Salt late keeps the taste\n"
    index.write_text(index.read_text(encoding="utf-8") + line, encoding="utf-8")
    return path


def contribute(world: SimpleNamespace, *args: str | Path, path: str | None = None) -> subprocess.CompletedProcess:
    env = {**git_env(), "PATH": path or f"{world.tools}{os.pathsep}{os.environ['PATH']}"}
    return subprocess.run(
        [sys.executable, str(world.project / "ops" / "contribute.py"), *map(str, args)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=120,
    )


def frontmatter(text: str) -> dict:
    head = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    assert head, text
    return yaml.safe_load(head.group(1))


def test_an_accepted_page_goes_to_a_branch_of_the_clone_and_to_a_pull_request(world):
    head, before = git(world.clone, "rev-parse", "HEAD"), git(world.clone, "status", "--porcelain")
    done = contribute(world, page(world), world.evidence)
    assert done.returncode == 0, done.stdout + done.stderr
    branch = f"contribute/{world.origin}/salt-late"
    text = git(world.seed, "show", f"{branch}:pages/salt-late.md")  # pushed to the commons
    fields = frontmatter(text)
    assert list(fields) == FIELDS
    assert fields["status"] == "candidate" and fields["projects"] == [world.origin] and fields["type"] == "decision"
    assert fields["sources"] == ["https://example.org/salt", f"evidence/{world.origin}/tasting.md"]
    assert fields["summary"] == "Salt late keeps the taste" and fields["licence"] == "CC-BY-4.0"
    assert "## Evidence" in text and f"(../evidence/{world.origin}/tasting.md)" in text and "by: owner" not in text
    assert git(world.seed, "show", f"{branch}:evidence/{world.origin}/tasting.md") == EVIDENCE
    assert git(world.clone, "rev-parse", "HEAD") == head and git(world.clone, "status", "--porcelain") == before
    argv = world.argv.read_text(encoding="utf-8").splitlines()
    assert argv[:2] == ["pr", "create"] and argv[argv.index("--head") + 1] == branch


def test_a_concept_becomes_a_lesson_candidate_with_the_vaults_id_only(world):
    path = page(world, "concepts", "late-salt", type="concept", extra=f"projects: [{world.origin}]\n")
    done = contribute(world, path, world.evidence)
    assert done.returncode == 0, done.stdout + done.stderr
    fields = frontmatter(git(world.clone, "show", f"contribute/{world.origin}/late-salt:pages/late-salt.md"))
    assert fields["type"] == "lesson" and fields["status"] == "candidate" and fields["projects"] == [world.origin]


def test_the_dry_run_prints_the_page_and_writes_nothing(world):
    path = page(world)
    seen = (refs(world.clone), refs(world.seed), git(world.clone, "status", "--porcelain"))
    done = contribute(world, path, world.evidence, "--dry-run")
    assert done.returncode == 0, done.stdout + done.stderr
    assert 'status: "candidate"' in done.stdout and f"evidence/{world.origin}/tasting.md" in done.stdout
    assert (refs(world.clone), refs(world.seed), git(world.clone, "status", "--porcelain")) == seen
    assert not world.argv.exists()


def test_without_gh_the_branch_is_made_and_the_two_commands_are_printed(world):
    tools = world.tmp / "git-only"
    tools.mkdir()
    (tools / "git").symlink_to(shutil.which("git"))
    done = contribute(world, page(world), world.evidence, path=str(tools))
    assert done.returncode == 0, done.stdout + done.stderr
    branch = f"contribute/{world.origin}/salt-late"
    assert git(world.clone, "rev-parse", "--verify", branch) and branch not in refs(world.seed)
    assert f"push -u origin {branch}" in done.stdout and "gh pr create" in done.stdout


def test_a_real_run_without_a_clone_names_the_clone_command_and_writes_nothing(world):
    shutil.rmtree(world.clone)
    done = contribute(world, page(world), world.evidence)
    assert (
        done.returncode == 1
        and f"git clone https://github.com/ghvinashvili/aftpro-commons.git {world.clone}" in done.stdout
    )
    assert not world.clone.exists()
    dry = contribute(world, world.vault / "decisions" / "global" / "salt-late.md", world.evidence, "--dry-run")
    assert dry.returncode == 0 and "git clone" in dry.stdout


def setup_path(world):
    return [page(world, "decisions/cooking", type="decision"), world.evidence]


def setup_type(world):
    return [page(world, type="concept"), world.evidence]


def setup_missing_field(world):
    return [page(world, would_change_if=""), world.evidence]


def setup_private_source(world):
    return [page(world, sources="context/owner-statements/said.md")]


def setup_private_link(world):
    return [page(world, body="see [the notes](~/notes/salt.md)."), world.evidence]


def setup_source(world):
    return [page(world, sources="rules.md"), world.evidence]


def setup_origin(world):
    return [page(world, extra="projects: [Alice]\n"), world.evidence]


def setup_secret_origin(world):
    return [page(world, extra=f"projects: [{KEY}]\n"), world.evidence]


def setup_second_origin(world):
    return [page(world, status="rule", extra="projects: [0123456789ab]\n"), world.evidence]


def setup_rule(world):
    return [page(world, status="rule"), world.evidence]


def setup_secret(world):
    return [page(world, body=f"the key {KEY} opened the tasting."), world.evidence]


def setup_secret_in_evidence(world):
    world.evidence.write_text(EVIDENCE + f"token {KEY}\n", encoding="utf-8")
    return [page(world), world.evidence]


def setup_georgian(world):
    return [page(world, body="the word " + chr(0x10D0) + "."), world.evidence]


def setup_mtavruli(world):
    return [page(world, body="the word " + chr(0x1C90) + "."), world.evidence]


def setup_evidence(world):
    return [page(world), world.tmp / "public" / "absent.md"]


def setup_evidence_utf16(world):
    hidden = f"token {KEY}\n" + chr(0x10D0) + " see context/owner-statements/said.md\n"
    world.evidence.write_bytes((EVIDENCE + hidden).encode("utf-16"))
    return [page(world), world.evidence]


def setup_evidence_nul(world):
    world.evidence.write_bytes(EVIDENCE.encode("utf-8") + b"\0\n")
    return [page(world), world.evidence]


def setup_file_name(world):
    return [page(world, name="Salt_Late"), world.evidence]


def setup_georgian_file_name(world):
    return [page(world, name="salt-" + chr(0x10D0)), world.evidence]


def setup_secret_file_name(world):
    return [page(world, name="salt-" + KEY), world.evidence]


def setup_evidence_in_context(world):
    inside = world.vault / "context" / "measurements" / "tasting.md"
    inside.write_text(EVIDENCE, encoding="utf-8")
    return [page(world), inside]


def setup_exists(world):
    (world.clone / "pages").mkdir()
    (world.clone / "pages" / "salt-late.md").write_text("# taken\n", encoding="utf-8")
    git(world.clone, "add", "-A")
    git(world.clone, "commit", "-q", "-m", "taken")
    return [page(world), world.evidence]


def setup_size(world):
    return [page(world, body="salt " * 2600), world.evidence]


REFUSALS = [
    ("path", setup_path),
    ("type", setup_type),
    ("missing-field", setup_missing_field),
    ("private-path", setup_private_source),
    ("private-path", setup_private_link),
    ("source", setup_source),
    ("origin", setup_origin),
    ("origin", setup_secret_origin),
    ("origin", setup_second_origin),
    ("rule-under-two-ids", setup_rule),
    ("secret", setup_secret),
    ("secret", setup_secret_in_evidence),
    ("georgian", setup_georgian),
    ("georgian", setup_mtavruli),
    ("evidence", setup_evidence),
    ("evidence", setup_evidence_utf16),
    ("evidence", setup_evidence_nul),
    ("path", setup_file_name),
    ("georgian", setup_georgian_file_name),
    ("secret", setup_secret_file_name),
    ("private-path", setup_evidence_in_context),
    ("exists", setup_exists),
    ("size", setup_size),
]


@pytest.mark.parametrize(("kind", "setup"), REFUSALS, ids=[setup.__name__[6:] for _, setup in REFUSALS])
def test_every_refusal_names_its_class_and_writes_nothing(world, kind, setup):
    args = setup(world)
    seen = (refs(world.clone), refs(world.seed), git(world.clone, "status", "--porcelain"))
    for extra in ((), ("--dry-run",)):
        done = contribute(world, *args, *extra)
        assert done.returncode == 1, done.stdout + done.stderr
        assert f"refused ({kind})" in done.stdout, done.stdout
        assert KEY not in done.stdout + done.stderr
    assert (refs(world.clone), refs(world.seed), git(world.clone, "status", "--porcelain")) == seen
    assert not world.argv.exists()


@pytest.mark.parametrize("flag", ["--force", "--skip-checks", "--no-verify", "--yes", "--allow-private"])
def test_no_flag_skips_a_check(world, flag):
    args = setup_secret(world)
    done = contribute(world, *args, flag)
    assert done.returncode == 2 and "unknown option" in done.stdout
    assert contribute(world, *args, "--dry-run").returncode == 1
    assert not world.argv.exists() and f"contribute/{world.origin}/salt-late" not in refs(world.clone)


def test_the_georgian_check_is_the_check_of_harness_validate():
    from harness.catalog import GEORGIAN as VALIDATE

    spec = importlib.util.spec_from_file_location("contribute", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    codes = [*range(0x10A0, 0x1100), *range(0x1C90, 0x1CC0), *range(0x2D00, 0x2D30)]
    outside = [0x109F, 0x1100, 0x1C8F, 0x1CC0, 0x2CFF, 0x2D30]
    assert all(module.GEORGIAN.search(chr(c)) for c in codes)
    assert [c for c in codes + outside if bool(module.GEORGIAN.search(chr(c))) != bool(VALIDATE.search(chr(c)))] == []
    assert not any(module.GEORGIAN.search(chr(c)) for c in outside)
    assert not module.GEORGIAN.search("plain English, 2026-10-29")


def test_the_commons_url_is_one_value_in_the_three_places_that_name_it():
    pattern = re.compile(r'^COMMONS_URL = "([^"]+)"', re.MULTILINE)
    places = [REPO / "ops" / "new-vault.py", SCRIPT, REPO / "packages" / "harness" / "src" / "harness" / "doctor.py"]
    found = {pattern.search(p.read_text(encoding="utf-8")).group(1) for p in places}
    assert found == {"https://github.com/ghvinashvili/aftpro-commons.git"}
