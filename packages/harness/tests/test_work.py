"""Committed work reaches a later stage as one neutral commit in a checkout, and a finished run becomes one branch."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from harness import access, launch, work

REPO = Path(__file__).resolve().parents[3]
STAGES = [
    {"id": "read", "role_type": "reader", "inputs": ["brief"]},
    {"id": "write", "role_type": "writer", "inputs": ["brief", "read:output/notes.md"]},
    {"id": "verify", "role_type": "verifier", "inputs": ["brief", "write:output/", "write:tasks.json"]},
    {"id": "accept", "role_type": "test-verifier", "inputs": ["brief", "write:output/"]},
]
BY_ID = {s["id"]: s for s in STAGES}


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def env(tmp_path: Path, monkeypatch):
    for var in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"):
        monkeypatch.delenv(var, raising=False)
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "A Writer")
    git(root, "config", "user.email", "writer@example.com")
    git(root, "config", "commit.gpgsign", "false")
    (root / "a.txt").write_text("one\n")
    (root / "b.txt").write_text("one\n")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "base")
    run_dir = tmp_path / "repo-runs" / "r1"
    (run_dir / "stages").mkdir(parents=True)
    return root, run_dir, access.load_policy(REPO)


def shard(root: Path, run_dir: Path, n: int, file: str, text: str) -> str:
    """A writer shard: one commit on its own branch, and the result that names the branch."""
    branch = f"worktree-r1-write-{n:02d}"
    git(root, "checkout", "-q", "-b", branch, "main")
    (root / file).write_text(text)
    git(root, "add", file)
    git(root, "commit", "-q", "-m", f"feat: change {file}\n\nCo-Authored-By: Claude <noreply@anthropic.com>")
    git(root, "checkout", "-q", "main")
    unit = run_dir / "stages" / "write" / f"{n:02d}"
    unit.mkdir(parents=True)
    result = {"summary": f"Branch {branch}, one commit.", "outputs": [{"path": file, "kind": "code"}]}
    (unit / "result.json").write_text(json.dumps(result))
    return branch


def test_a_reviewer_gets_the_work_as_one_neutral_commit_and_a_patch(env):
    root, run_dir, policy = env
    shard(root, run_dir, 1, "a.txt", "two\n")
    stage_dir = run_dir / "stages" / "verify"
    got = work.prepare(root, policy, BY_ID, run_dir, BY_ID["verify"], stage_dir, "r1-verify")
    checkout = root / ".claude" / "worktrees" / "r1-verify"
    assert Path(got["path"]) == checkout and (checkout / "a.txt").read_text() == "two\n"
    assert (root / "a.txt").read_text() == "one\n"  # the shared checkout is still the base
    assert git(checkout, "log", "-1", "--format=%an|%ae|%s") == "work|work@localhost|work under review"
    assert "Claude" not in git(checkout, "log", "-1", "--format=%B")  # no trailer says who or what made it
    assert git(checkout, "rev-parse", "HEAD~1") == git(root, "rev-parse", "main")
    patch = (stage_dir / "input" / "work" / "changes.patch").read_text()
    assert "+two" in patch and "-one" in patch and "Author" not in patch
    again = work.prepare(root, policy, BY_ID, run_dir, BY_ID["verify"], stage_dir, "r1-verify")
    assert again["commit"] == got["commit"]  # the id follows from the content: a second launch changes nothing


def test_a_stage_that_depends_on_no_committed_work_gets_no_checkout(env):
    root, run_dir, policy = env
    assert work.prepare(root, policy, BY_ID, run_dir, BY_ID["write"], run_dir / "stages" / "write" / "01", "x") is None
    assert not (root / ".claude" / "worktrees").exists()


def test_shards_are_combined_and_shards_that_collide_refuse_the_launch(env):
    root, run_dir, policy = env
    shard(root, run_dir, 1, "a.txt", "two\n")
    shard(root, run_dir, 2, "b.txt", "two\n")
    stage_dir = run_dir / "stages" / "verify"
    got = work.prepare(root, policy, BY_ID, run_dir, BY_ID["verify"], stage_dir, "r1-verify")
    checkout = Path(got["path"])
    assert (checkout / "a.txt").read_text() == "two\n" and (checkout / "b.txt").read_text() == "two\n"
    assert git(checkout, "log", "--format=%s") == "work under review\nbase"  # one commit, whatever the shard count
    shard(root, run_dir, 3, "a.txt", "three\n")
    with pytest.raises(work.WorkConflict) as conflict:
        work.prepare(root, policy, BY_ID, run_dir, BY_ID["accept"], run_dir / "stages" / "accept", "r1-accept")
    assert conflict.value.files == ["a.txt"]


def test_a_finished_run_becomes_one_branch_with_the_real_commits(env):
    root, run_dir, policy = env
    shard(root, run_dir, 1, "a.txt", "two\n")
    stage_dir = run_dir / "stages" / "accept"
    got = work.prepare(root, policy, BY_ID, run_dir, BY_ID["accept"], stage_dir, "r1-accept")
    (run_dir / "_access").mkdir()
    (run_dir / "_access" / "accept.work.json").write_text(json.dumps(got))  # what the launcher records
    checkout = Path(got["path"])
    (checkout / "test_a.txt").write_text("a is two\n")
    git(checkout, "add", "test_a.txt")
    git(checkout, "-c", "user.name=T Verifier", "commit", "-q", "-m", "test: acceptance of a")
    (stage_dir / "result.json").write_text(json.dumps({"summary": "Branch worktree-r1-accept.", "outputs": []}))
    work.prepare(root, policy, BY_ID, run_dir, BY_ID["verify"], run_dir / "stages" / "verify", "r1-verify")

    out = work.integrate(root, policy, STAGES, run_dir)
    assert out["ok"] and out["branch"] == "run/r1" and out["commits"] == 2
    assert (
        git(root, "log", "--format=%an|%s", "run/r1")
        == "T Verifier|test: acceptance of a\nA Writer|feat: change a.txt\nA Writer|base"
    )
    assert git(root, "rev-parse", "run/r1^{tree}") == git(root, "rev-parse", "worktree-r1-accept^{tree}")
    assert "Co-Authored-By: Claude" in git(root, "log", "-1", "--format=%B", "run/r1~1")  # the author's own commit

    cleaned = work.clean_checkouts(root, policy, STAGES, run_dir)
    assert not checkout.exists() and not (root / ".claude" / "worktrees" / "r1-verify").exists()
    branches = git(root, "branch", "--format=%(refname:short)").split()
    assert "worktree-r1-verify" not in branches  # a review checkout goes with its branch
    assert {"worktree-r1-accept", "worktree-r1-write-01", "run/r1"} <= set(branches)
    assert "worktree-r1-accept" in cleaned["kept_branches"]


def test_only_a_unit_with_a_checkout_is_told_to_enter_one(env):
    root, run_dir, policy = env
    writer, verifier = BY_ID["write"], BY_ID["verify"]
    assert launch.worktree_of(root, policy, "r1", writer, 1) == "r1-write-01"  # its own, made when it enters
    assert launch.worktree_of(root, policy, "r1", verifier, None) is None  # a document review needs none
    shard(root, run_dir, 1, "a.txt", "two\n")
    work.prepare(root, policy, BY_ID, run_dir, verifier, run_dir / "stages" / "verify", "r1-verify")
    assert launch.worktree_of(root, policy, "r1", verifier, None) == "r1-verify"


def test_the_pages_of_a_wiki_run_become_verified_when_its_check_stage_accepted_them(env):
    root, run_dir, _ = env
    page = "---\ntitle: X\nstatus: draft\n---\n# X\n\nA page may say `status: draft` in its text.\nstatus: draft\n"
    git(root, "checkout", "-q", "-b", "worktree-r1-ingest", "main")
    (root / "wiki" / "concepts").mkdir(parents=True)
    (root / "wiki" / "concepts" / "x.md").write_text(page)
    (root / "wiki" / "index.md").write_text("- [X](concepts/x.md)\n")
    git(root, "add", "wiki")
    git(root, "commit", "-q", "-m", "docs(wiki): x")
    head = git(root, "rev-parse", "HEAD")
    git(root, "checkout", "-q", "main")
    base = git(root, "rev-parse", "main")
    stages = [{"id": "ingest", "gate": "ingest"}, {"id": "wikicheck", "gate": "wikicheck"}]
    check_dir = run_dir / "stages" / "wikicheck"
    check_dir.mkdir(parents=True)
    (check_dir / "result.json").write_text(json.dumps({"verdict": {"decision": "revise", "reasons": ["r"]}}))
    assert work.mark_verified(root, stages, run_dir, base, head) == (head, [])  # not accepted: nothing changes
    (check_dir / "result.json").write_text(json.dumps({"verdict": {"decision": "accept", "reasons": ["r"]}}))
    commit, pages = work.mark_verified(root, stages, run_dir, base, head)
    assert pages == ["wiki/concepts/x.md"] and commit != head
    text = git(root, "show", f"{commit}:wiki/concepts/x.md")
    assert text.splitlines()[2] == "status: verified" and text.count("status: draft") == 2  # only the frontmatter
    assert git(root, "show", f"{commit}:wiki/index.md") == "- [X](concepts/x.md)"  # nothing else is touched
    assert git(root, "log", "-1", "--format=%s", commit) == "docs(wiki): 1 pages verified"
    assert work.mark_verified(root, stages, run_dir, base, commit) == (commit, [])  # already verified


def test_a_reviewing_checkout_follows_the_work_when_its_author_commits_again(env):
    root, run_dir, policy = env
    branch = shard(root, run_dir, 1, "a.txt", "two\n")
    stage_dir = run_dir / "stages" / "verify"
    first = work.prepare(root, policy, BY_ID, run_dir, BY_ID["verify"], stage_dir, "r1-verify")
    checkout = Path(first["path"])
    git(root, "checkout", "-q", branch)  # the author is resumed and fixes something
    (root / "a.txt").write_text("three\n")
    git(root, "commit", "-q", "-am", "fix: a")
    git(root, "checkout", "-q", "main")
    again = work.prepare(root, policy, BY_ID, run_dir, BY_ID["verify"], stage_dir, "r1-verify")
    assert again["commit"] != first["commit"] and (checkout / "a.txt").read_text() == "three\n"
    assert git(checkout, "log", "--format=%s") == "work under review\nbase"  # still one neutral commit on the base
    assert "+three" in (stage_dir / "input" / "work" / "changes.patch").read_text()

    accept = work.prepare(root, policy, BY_ID, run_dir, BY_ID["accept"], run_dir / "stages" / "accept", "r1-accept")
    own = Path(accept["path"])
    (own / "t.txt").write_text("t\n")
    git(own, "add", "t.txt")
    git(own, "commit", "-q", "-m", "test: t")
    git(root, "checkout", "-q", branch)
    (root / "a.txt").write_text("four\n")
    git(root, "commit", "-q", "-am", "fix: a again")
    git(root, "checkout", "-q", "main")
    with pytest.raises(access.AccessError, match="its own commits"):  # replaying them is not the launcher's call
        work.prepare(root, policy, BY_ID, run_dir, BY_ID["accept"], run_dir / "stages" / "accept", "r1-accept")


def test_a_reviewing_checkout_with_changes_of_its_own_follows_the_work(env):
    """A recheck moves a checkout that only reviewed to the new work commit: what its session left changed there is
    no deliverable (that is under output/), and it does not keep the checkout from following."""
    root, run_dir, policy = env
    branch = shard(root, run_dir, 1, "a.txt", "two\n")
    stage_dir = run_dir / "stages" / "verify"
    checkout = Path(work.prepare(root, policy, BY_ID, run_dir, BY_ID["verify"], stage_dir, "r1-verify")["path"])
    (checkout / "a.txt").write_text("broken on purpose\n")  # the reviewer broke it once to see a test catch it
    git(root, "checkout", "-q", branch)
    (root / "a.txt").write_text("three\n")
    git(root, "commit", "-q", "-am", "fix: a")
    git(root, "checkout", "-q", "main")
    work.prepare(root, policy, BY_ID, run_dir, BY_ID["verify"], stage_dir, "r1-verify")
    assert (checkout / "a.txt").read_text() == "three\n"


def test_a_cleaned_run_leaves_the_session_list(monkeypatch):
    # the human asked that a finished chat does not stay listed for ever; the transcript is not touched by this
    calls = []

    def fake(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 1 if cmd[1:] == ["rm", "gone0000"] else 0, "", "")

    monkeypatch.setattr(work.subprocess, "run", fake)
    st = {
        "stages": {
            "read": {"job_ids": ["aaaa1111"]},
            "write": {"job_ids": ["bbbb2222", "cccc3333"], "shards": {"01": {"job_ids": ["bbbb2222", "cccc3333"]}}},
            "verify": {"job_ids": ["gone0000"]},
            "judge": {},
        }
    }
    assert work.remove_sessions(st) == ["aaaa1111", "bbbb2222", "cccc3333"]
    assert calls[:2] == [["claude", "stop", "aaaa1111"], ["claude", "rm", "aaaa1111"]]
    assert len(calls) == 8


def test_integrate_never_rewrites_the_branch_it_built(env):
    """`git branch -f` replaced `run/<run-id>` with new commits on every call and dropped what the human added to it."""
    root, run_dir, policy = env
    shard(root, run_dir, 1, "a.txt", "two\n")
    first = work.integrate(root, policy, STAGES, run_dir)
    assert first["ok"] and first["branch"] == "run/r1"
    git(root, "checkout", "-q", "run/r1")
    (root / "b.txt").write_text("the human's\n")
    git(root, "commit", "-qam", "fix: the human's own change")
    git(root, "checkout", "-q", "main")
    human = git(root, "rev-parse", "run/r1")
    again = work.integrate(root, policy, STAGES, run_dir)
    assert again["ok"] and again["status"] == "integrated_before" and again["head"] == human
    assert git(root, "rev-parse", "run/r1") == human


TRIAL = "diff --git a/added.py b/added.py\nnew file mode 100644\n--- /dev/null\n+++ b/added.py\n@@ -0,0 +1 @@\n+X = 1\n"
ATTACK = {"id": "attack", "role_type": "critic", "inputs": ["brief", "plan:output/"],
          "returns_to": {"stage": "plan", "counter": "plan"}}  # fmt: skip
PLAN_STAGES = {"plan": {"id": "plan", "role_type": "planner"}, "attack": ATTACK}


def trial_rig(env, patch: str = TRIAL):
    """The repository of `env`, and a run whose plan stage left trial.patch, with the base in its manifest."""
    root, run_dir, policy = env
    trial = run_dir / "stages/plan/output/trial"
    trial.mkdir(parents=True)
    (trial / "trial.patch").write_text(patch, encoding="utf-8")
    (run_dir / "manifest.json").write_text(json.dumps({"base_commit": git(root, "rev-parse", "HEAD")}))
    return root, run_dir, policy


def test_a_critic_of_a_plan_gets_a_checkout_of_the_base_with_the_trial(env):
    root, run_dir, policy = trial_rig(env)
    stage_dir = run_dir / "stages" / "attack"
    out = work.prepare(root, policy, PLAN_STAGES, run_dir, ATTACK, stage_dir, "r1-attack")
    assert out["from"] == [{"stage": "plan", "trial": str(run_dir / "stages/plan/output/trial/trial.patch")}]
    assert (Path(out["path"]) / "added.py").read_text(encoding="utf-8") == "X = 1\n"
    assert "added.py" in (stage_dir / "input/plan/changes.patch").read_text(encoding="utf-8")


def test_only_a_stage_that_returns_to_the_plan_gets_its_trial(env):
    root, run_dir, policy = trial_rig(env)
    reader = {k: v for k, v in ATTACK.items() if k != "returns_to"}  # a critic of a council, say
    assert work.prepare(root, policy, PLAN_STAGES, run_dir, reader, run_dir / "stages/attack", "r1-attack") is None


def test_a_trial_that_does_not_apply_is_refused_with_gits_words(env):
    root, run_dir, policy = trial_rig(env, patch="--- a/missing.py\n+++ b/missing.py\n@@ -1 +1 @@\n-a\n+b\n")
    with pytest.raises(access.AccessError, match="does not apply"):
        work.prepare(root, policy, PLAN_STAGES, run_dir, ATTACK, run_dir / "stages/attack", "r1-attack")


def test_a_judge_gets_the_patch_of_the_work_and_no_checkout(env):
    root, run_dir, policy = env
    git(root, "checkout", "-q", "-b", "worktree-r1-write", "main")
    (root / "a.txt").write_text("two\n")
    git(root, "commit", "-qam", "feat: two")
    git(root, "checkout", "-q", "main")
    (run_dir / "stages/write").mkdir(parents=True)
    (run_dir / "stages/write/result.json").write_text(json.dumps({"summary": "Branch worktree-r1-write."}))
    judge = {"id": "judge", "role_type": "judge", "inputs": ["write:checks.json"]}
    stage_dir = run_dir / "stages" / "judge"
    out = work.prepare(root, policy, BY_ID, run_dir, judge, stage_dir, "r1-judge", checkout=False)
    assert not Path(out["path"]).exists() and "+two" in Path(out["patch"]).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "path",
    [".claude/settings.json", ".mcp.json", ".claude/agents/critic.md", ".claude/skills/\u00e9t\u00e9/SKILL.md",
     ".CLAUDE/settings.json"],
)  # fmt: skip
def test_a_trial_that_changes_the_flows_configuration_gets_no_checkout(env, path):
    """A session that enters a checkout loads its settings, hooks and agents from there: a planner's trial that
    changes them would run its own commands in the critic's session, outside the sandbox."""
    patch = f"diff --git a/{path} b/{path}\nnew file mode 100644\n--- /dev/null\n+++ b/{path}\n@@ -0,0 +1 @@\n+{{}}\n"
    root, run_dir, policy = trial_rig(env, patch=patch)
    with pytest.raises(access.AccessError, match="closed"):
        work.prepare(root, policy, PLAN_STAGES, run_dir, ATTACK, run_dir / "stages/attack", "r1-attack")
    assert not (root / ".claude/worktrees/r1-attack").exists()
