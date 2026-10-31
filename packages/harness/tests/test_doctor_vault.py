"""harness doctor's vault item (spec 11.1 and 11.3): the user's vault at vault_path holds INDEX.md, rules.md and its own
ops/check_pages.py that passes, and the clone of the commons at commons_path was fetched within seven days; each gap
names the command that closes it, and the item is optional (no role session needs it)."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import yaml
from harness import doctor

REPO = Path(__file__).resolve().parents[3]
NAME = "the vault and the commons are in place"


def git_env() -> dict[str, str]:
    who = {
        f"GIT_{role}_{key}": val for role in ("AUTHOR", "COMMITTER") for key, val in (("NAME", "t"), ("EMAIL", "t@t"))
    }
    return {**os.environ, **who, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def project(tmp_path: Path) -> tuple[Path, Path, Path]:
    """A project root whose variables.yaml names a vault and a commons clone under tmp_path (neither made yet)."""
    root, vault, commons = tmp_path / "project", tmp_path / "vault", tmp_path / "commons"
    (root / "docs" / "template").mkdir(parents=True)
    spec = {
        "variables": [{"name": "vault_path", "default": str(vault)}, {"name": "commons_path", "default": str(commons)}]
    }
    (root / "docs" / "template" / "variables.yaml").write_text(yaml.safe_dump(spec), encoding="utf-8")
    return root, vault, commons


def make(vault: Path, commons: Path) -> None:
    """The vault by ops/new-vault.py; the commons as a fresh clone of a one-commit repository."""
    done = subprocess.run(
        [sys.executable, str(REPO / "ops" / "new-vault.py"), str(vault), f"commons_path={commons}"],
        capture_output=True,
        text=True,
        env=git_env(),
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    seed = commons.parent / "seed"
    seed.mkdir()
    (seed / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["commit", "-q", "-m", "seed"],
        ["clone", "-q", str(seed), str(commons)],
    ):
        subprocess.run(["git", "-C", str(seed), *args], capture_output=True, env=git_env(), check=True)


def test_a_missing_vault_and_commons_name_the_commands_that_make_them(tmp_path: Path):
    root, vault, commons = project(tmp_path)
    item = doctor.vault_item(root)
    assert item["name"] == NAME and item["ok"] is False and item["required"] is False
    assert f"python3 ops/new-vault.py {vault}" in item["fix"]
    assert f"git clone {doctor.COMMONS_URL} {commons}" in item["fix"]


def test_a_new_vault_and_a_fresh_clone_pass(tmp_path: Path):
    root, vault, commons = project(tmp_path)
    make(vault, commons)
    item = doctor.vault_item(root)
    assert item["ok"] is True and "fix" not in item, item


def test_a_page_the_vaults_check_refuses_turns_the_item_red(tmp_path: Path):
    root, vault, commons = project(tmp_path)
    make(vault, commons)
    (vault / "decisions" / "global" / "bare.md").write_text("no frontmatter here\n", encoding="utf-8")
    item = doctor.vault_item(root)
    assert item["ok"] is False and "check_pages.py" in item["fix"] and "new-vault" not in item["fix"]


def test_a_clone_not_fetched_for_eight_days_asks_for_a_pull(tmp_path: Path):
    root, vault, commons = project(tmp_path)
    make(vault, commons)
    old = time.time() - 8 * 86400
    for name in ("FETCH_HEAD", "packed-refs"):
        stamp = commons / ".git" / name
        stamp.touch()
        os.utime(stamp, (old, old))
    item = doctor.vault_item(root)
    assert item["ok"] is False and item["fix"] == f"git -C {commons} pull --ff-only"


def test_the_doctor_lists_the_vault_item_once_as_optional():
    items = [c for c in doctor.check(REPO)["checks"] if c["name"] == NAME]
    assert len(items) == 1 and items[0]["required"] is False
