"""A project keeps the captured sources of its wiki as they were ingested: the source ledger holds the hash of each, and
ops/new-project.py replaces the template's literal values in every tracked text file except the `skip:` prefixes of
docs/template/variables.yaml, which therefore name `.raw/captured/`."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CAPTURED = ".raw/captured/0000.md"


def test_a_project_keeps_the_captured_sources_byte_for_byte(tmp_path: Path):
    root, target = tmp_path / "template", tmp_path / "demo"
    for rel in ("ops/new-project.py", "docs/template/variables.yaml", "docs/template/VERSION"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, root / rel)
    text = "The marketplace `example-repo-plugins` keeps its name.\n"
    for rel in (CAPTURED, "notes.md"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    command = [sys.executable, str(root / "ops" / "new-project.py"), str(target), "repo_name=demo", "--no-setup"]
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    assert (target / CAPTURED).read_text(encoding="utf-8") == text
    assert (target / "notes.md").read_text(encoding="utf-8") == text.replace("example-repo", "demo")
