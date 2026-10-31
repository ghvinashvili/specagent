"""A builder's pages become verified when the run's checks accepted the work (spec A2): `harness integrate` marks the
pages under wiki/ the run changed, decisions included, and nothing else."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from harness import work

IDENTITY = ["-c", "user.email=t@example.com", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
DRAFT = "---\ntitle: {0}\nstatus: draft\n---\n# {0}\n"
STAGES = [{"id": "write", "gate": "write"}, {"id": "verify", "gate": "verify"}, {"id": "judge", "gate": "judge"}]


def git(root: Path, *args: str) -> str:
    command = ["git", "-C", str(root), *IDENTITY]
    return subprocess.run([*command, *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def run(tmp_path: Path):
    """A writer's branch with code, two draft pages, a summary and a runbook: (root, run_dir, base, head)."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.txt").write_text("one\n", encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")
    base = git(root, "rev-parse", "HEAD")
    git(root, "checkout", "-q", "-b", "worktree-r1-write-01")
    files = {
        "src/app.py": "A = 1\n",
        "wiki/decisions/use-postgres.md": DRAFT.format("Use PostgreSQL"),
        "wiki/concepts/store.md": DRAFT.format("Store"),
        "wiki/decisions/use-postgres.summary.md": "status: draft\n",
        "docs/runbooks/restore.md": DRAFT.format("Restore"),
    }
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "feat: the store with its pages")
    head = git(root, "rev-parse", "HEAD")
    git(root, "checkout", "-q", "main")
    run_dir = tmp_path / "repo-runs" / "r1"
    (run_dir / "stages").mkdir(parents=True)
    return root, run_dir, base, head


def verdicts(run_dir: Path, **decisions: str) -> None:
    for stage, decision in decisions.items():
        (run_dir / "stages" / stage).mkdir(parents=True, exist_ok=True)
        verdict = {"verdict": {"decision": decision, "reasons": ["r"]}}
        (run_dir / "stages" / stage / "result.json").write_text(json.dumps(verdict), encoding="utf-8")


def test_a_writers_pages_become_verified_when_every_verdict_of_the_run_is_accept(run):
    root, run_dir, base, head = run
    verdicts(run_dir, verify="accept", judge="accept")
    commit, pages = work.mark_verified(root, STAGES, run_dir, base, head)
    assert pages == ["wiki/concepts/store.md", "wiki/decisions/use-postgres.md"] and commit != head
    assert git(root, "show", f"{commit}:wiki/decisions/use-postgres.md").splitlines()[2] == "status: verified"
    assert git(root, "diff", "--name-only", head, commit).splitlines() == pages  # the summary and the runbook stay


@pytest.mark.parametrize(
    "decisions",
    [{}, {"verify": "accept", "judge": "revise"}, {"verify": "revise", "judge": "accept"}, {"verify": "reject"}],
)
def test_without_a_verdict_or_with_one_other_than_accept_the_pages_stay_draft(run, decisions):
    root, run_dir, base, head = run
    verdicts(run_dir, **decisions)
    assert work.mark_verified(root, STAGES, run_dir, base, head) == (head, [])


def test_a_result_that_is_no_json_is_no_accept(run):
    root, run_dir, base, head = run
    verdicts(run_dir, verify="accept")
    (run_dir / "stages" / "judge").mkdir()
    (run_dir / "stages" / "judge" / "result.json").write_text("{not json", encoding="utf-8")
    assert work.mark_verified(root, STAGES, run_dir, base, head) == (head, [])


def test_a_stage_result_without_a_verdict_does_not_stop_the_marking(run):
    root, run_dir, base, head = run
    verdicts(run_dir, verify="accept", judge="accept")
    (run_dir / "stages" / "write").mkdir()
    result = {"summary": "branch worktree-r1-write-01", "evidence": []}  # what every write stage leaves (A5)
    (run_dir / "stages" / "write" / "result.json").write_text(json.dumps(result), encoding="utf-8")
    commit, pages = work.mark_verified(root, STAGES, run_dir, base, head)
    assert pages == ["wiki/concepts/store.md", "wiki/decisions/use-postgres.md"] and commit != head
