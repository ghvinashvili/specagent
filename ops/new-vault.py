#!/usr/bin/env python3
"""Make your own vault from the template's vault form (spec 11.1): ops/new-vault.py <vault_path> [commons_path=<path>].
It copies templates/vault/ into <vault_path> (missing or empty), draws the vault's opaque origin id (the `origin:` line
of README.md's frontmatter; the commons knows your pages by it, never by a name), writes commons_path (default: the
one in docs/template/variables.yaml) into INDEX.md, runs git init and one commit, and prints your own next step: a
private remote. A target that is not empty, or a machine where git has no identity, is refused before anything is
written. ops/new-project.py runs it for a vault_path that has no INDEX.md."""

import re
import secrets
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FORM = ROOT / "templates" / "vault"
COMMONS_URL = "https://github.com/ghvinashvili/aftpro-commons.git"  # the public commons (spec 11.3); doctor.py too


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1].startswith("-"):
        print(__doc__)
        return 0 if argv[1:2] in (["-h"], ["--help"]) else 2
    given = dict(arg.split("=", 1) for arg in argv[2:] if "=" in arg)
    if len(given) != len(argv) - 2 or set(given) - {"commons_path"}:
        print(f"unknown arguments: {argv[2:]}; the only one is commons_path=<path>")
        return 2
    target = Path(argv[1]).expanduser().resolve()
    if target == ROOT or ROOT in target.parents:
        print(f"{target} is inside the template; a vault lives beside it")
        return 1
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        print(f"{target} is not empty; a vault is made in a missing or empty folder")
        return 1
    if subprocess.run(["git", "var", "GIT_COMMITTER_IDENT"], capture_output=True, check=False).returncode:
        print("git has no identity on this machine, so the vault's first commit would fail; nothing written. Set it:")
        print('  git config --global user.name "<name>" && git config --global user.email "<e-mail>"')
        return 1
    spec = yaml.safe_load((ROOT / "docs" / "template" / "variables.yaml").read_text(encoding="utf-8"))
    commons = given.get("commons_path") or next(v["default"] for v in spec["variables"] if v["name"] == "commons_path")
    origin = secrets.token_hex(6)
    shutil.copytree(FORM, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    readme, index, log = target / "README.md", target / "INDEX.md", target / "log.md"
    readme.write_text(f"---\norigin: {origin}\n---\n" + readme.read_text(encoding="utf-8"), encoding="utf-8")
    text = re.sub(r"(?m)^commons_path: .*$", lambda _: f"commons_path: {commons}", index.read_text(encoding="utf-8"))
    index.write_text(text, encoding="utf-8")
    with log.open("a", encoding="utf-8") as out:
        out.write(
            f"- {datetime.now(UTC).date().isoformat()}: vault made from the template's vault form (ops/new-vault.py); origin {origin}\n"
        )
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["commit", "-q", "-m", f"vault made from the template's form, origin {origin}"],
    ):
        subprocess.run(["git", "-C", str(target), *args], check=True)
    print(f"made the vault {target}: origin {origin}, one commit")
    print("your own step: a private repository for it (the vault is yours; nothing in it is published):")
    print(f"  git -C {target} remote add origin <your-private-repository-url>")
    print(f"  git -C {target} push -u origin HEAD")
    print(f"the commons, a source and not an authority: git clone {COMMONS_URL} {commons}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
