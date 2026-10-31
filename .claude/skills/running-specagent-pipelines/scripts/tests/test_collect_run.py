"""collect_run.py: a finished run built in tmp_path (a repository whose main branch holds the plan, the tracker and
the merged work of two run worktrees; the run folder with final records and marked lessons; the jobs of its sessions
under the stub `claude` of transcript_home.py), the dry run's list, the save check's refusals, the owner's yes and the
removal (spec 5.9.4, 10.14).
"""

import ast
import hashlib
import json
import pathlib
import re
import subprocess

from transcript_home import Home

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "collect_run.py"
PLAN = "docs/exec-plans/active/demo"
TRACKER = "docs/exec-plans/tech-debt-tracker.md"
INDEX = """# Demo plan

## Deferred (with the reason)
- TD-003 the learning system (instinct model): stays by hand (spec 7.6).
- 8.3.17 per-plugin start-up cost: needs a per-plugin measurement
  that the catalogue does not make.

## Coverage
- 5.9.4 the collector: Task 6.
"""
TASK = """# Task 1 — Demo

## Deferred

1. A live check of the `--bg` output forms: copied from a verbatim log.

## Verified
- nothing deferred here: this item is under Verified.
"""
TASK_2 = """# Task 2 — Demo two

### Deferred
- TD-099 a row nobody wrote: names an id the tracker does not have.

  ````python
  ```markdown
  ````text
## Deferred
- A fixture item between fence lines: a test's fixture, never a Deferred item.
  ```
  ````

2. The registry ids: matched once the registry is merged.
"""
ROWS = """# Tech debt tracker

| Id | Area | Debt | Impact | Owner | Priority | Plan |
| --- | --- | --- | --- | --- | --- | --- |
| TD-003 | learning | the learning system | runs repeat mistakes | maintainers | medium | a later run |
| TD-013 | catalogue | per-plugin cost | unmeasured | maintainers | low | demo Deferred: 8.3.17 per-plugin start-up cost |
| TD-014 | watcher | the output forms | untested live | maintainers | low | demo Deferred: a live check of the --bg OUTPUT  forms |
"""
LESSONS = """# Lessons

## Read first
1. A rule from before the run: not checked.

## Lessons from this run
(roles add one-line rules here, with the finding ids)
- 10:00 UTC (planner; C1): an Expected count covers only the tests
  the steps so far can make green (skill: {main})
- 10:05 UTC (builder; B2): this run's scratch path was long (skill: none)
- 10:10 UTC (main session): Merged: a->b at {a}
"""


class Run:
    """A finished run whose record is saved, so the check passes; each test breaks one part of it."""

    def __init__(self, tmp_path: pathlib.Path):
        self.home = Home(tmp_path)
        self.repo = tmp_path / "repo"
        self.wt_a, self.wt_b = tmp_path / "wt-a", tmp_path / "wt-b"
        self.run = tmp_path / "runs" / "demo-run"
        self.jobs = tmp_path / "home" / ".claude" / "jobs"
        self.page = tmp_path / "vault" / "measurement.md"
        self.summary = self.repo / PLAN / "demo.summary.md"
        self.copy = tmp_path / "eval-copy"
        self.history = tmp_path / "runs" / "collect-history.jsonl"
        self.repo.mkdir()
        self.git(self.repo, "init", "-q", "-b", "main")
        self.write(self.repo / ".gitignore", ".venv/\n")
        self.write(self.repo / TRACKER, ROWS)
        self.write(self.repo / PLAN / "00-index.md", INDEX)
        self.write(self.repo / PLAN / "task-01.md", TASK)
        self.write(self.summary, "# Demo summary\n")
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-q", "-m", "base")
        for name, tree in (("a", self.wt_a), ("b", self.wt_b)):
            self.git(self.repo, "worktree", "add", "-q", "-b", f"feat/demo-{name}", str(tree))
            self.write(tree / f"{name}.txt", f"work {name}\n")
            self.git(tree, "add", "-A")
            self.git(tree, "commit", "-q", "-m", f"work {name}")
            self.git(self.repo, "merge", "-q", "--no-ff", f"feat/demo-{name}", "-m", f"merge {name}")
        self.write(self.wt_a / ".venv" / "lib" / "site.py", "# ignored\n")
        self.sha_a = self.git(self.repo, "rev-parse", "feat/demo-a")
        self.sha_b = self.git(self.repo, "rev-parse", "feat/demo-b")
        self.main = self.git(self.repo, "rev-parse", "main")
        for name in ("plan-log.md", "judge.md"):
            self.write(self.run / name, f"STATUS: done\n# {name}\n")
        self.write(self.run / "build-log-a.md", f"STATUS: done\n# Build log a\nTask 1: done — {self.sha_a}\n")
        self.write(self.run / "build-log-b.md", f"STATUS: done\n# Build log b\nTask 2: done — {self.sha_b[:7]}\n")
        self.write(self.run / "lessons.md", LESSONS.format(main=self.main[:12], a=self.sha_a[:7]))
        agents = {
            "demo/builder-a": {"cwd": str(self.wt_a)},
            "demo/builder-b": {"cwd": str(self.wt_b)},
            "demo/critic": {"cwd": str(self.run)},
        }
        self.write(self.run / "_control" / "_agents.json", json.dumps({"run_dir": str(self.run), "agents": agents}))
        self.write(self.run / "scratch" / "planner" / "notes.md", "abc")
        (self.run / "scratch" / "copy.bin").write_bytes(b"x" * 1_260_000)
        self.write(self.page, "# Measurement\n")
        self.write(self.copy / "result.json", "{}\n")
        self.job("0000000a", "demo/builder-a", self.wt_a, "done")
        self.job("0000000b", "demo/builder-b", self.wt_b, "stopped")
        self.job("0000000c", "demo/critic", self.run, "failed")
        self.job("0000000d", "demo/builder-a", tmp_path / "elsewhere", "done")  # the same name in another run
        self.job("0000000e", "other/planner", self.wt_a, "done")  # a role that is not in the agents file

    def git(self, cwd: pathlib.Path, *args: str) -> str:
        out = subprocess.run(
            ["git", "-C", str(cwd), "-c", "user.name=Demo", "-c", "user.email=demo@example.com"]
            + ["-c", "commit.gpgsign=false", *args],
            capture_output=True,
            text=True,
            check=True,
            env={**self.home.env(), "GIT_CONFIG_NOSYSTEM": "1"},
        )
        return out.stdout.strip()

    def git_error(self, *args: str) -> str:
        """The first stderr line of a git command in the main worktree that fails."""
        out = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            capture_output=True,
            text=True,
            check=False,
            env={**self.home.env(), "GIT_CONFIG_NOSYSTEM": "1"},
        )
        assert out.returncode != 0, out.stdout
        return out.stderr.strip().splitlines()[0]

    @staticmethod
    def write(path: pathlib.Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def job(self, ident: str, name: str, cwd: pathlib.Path, state: str, pid: int | None = None) -> None:
        """A row of `claude agents --json --all` in the live shape and its folder: 3 files, 1,000 bytes."""
        row = {
            "id": ident,
            "name": name,
            "sessionId": f"s-{ident}",
            "state": state,
            "kind": "background",
            "cwd": str(cwd),
            "startedAt": 1_761_000_000_000,
        }
        if pid is not None:
            row["pid"] = pid
        self.home.rows.append(row)
        self.home.save_rows()
        self.write(self.jobs / ident / "state.json", "{}\n")
        self.write(self.jobs / ident / "timeline.jsonl", "")
        self.write(self.jobs / ident / "tmp" / "out.txt", "x" * 997)

    def collect(self, *extra: str) -> subprocess.CompletedProcess:
        return self.home.run(
            "collect_run.py",
            str(self.run),
            "--repo",
            str(self.repo),
            "--plan",
            PLAN,
            "--kept",
            str(self.page),
            "--kept",
            str(self.summary),
            "--also",
            str(self.copy),
            *extra,
        )

    def digest(self) -> str:
        out = self.collect()
        assert out.returncode == 0, out.stdout + out.stderr
        return re.search(r"; digest ([0-9a-f]{12}); ", out.stdout.splitlines()[-1]).group(1)

    def side_commit(self) -> str:
        """A commit of the repository on no branch: not in main."""
        return self.git(self.repo, "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", "side")

    def untouched(self) -> bool:
        listed = self.git(self.repo, "worktree", "list", "--porcelain").splitlines()
        branches = self.git(self.repo, "branch", "--format=%(refname:short)").splitlines()
        return (
            [line for line in listed if line.startswith("worktree ")]
            == [f"worktree {self.repo}", f"worktree {self.wt_a}", f"worktree {self.wt_b}"]
            and sorted(branches) == ["feat/demo-a", "feat/demo-b", "main"]
            and (self.run / "scratch" / "copy.bin").is_file()
            and all((self.jobs / i / "state.json").is_file() for i in ("0000000a", "0000000b", "0000000c"))
            and (self.copy / "result.json").is_file()
        )


def refusals(out: subprocess.CompletedProcess) -> list[str]:
    return [line for line in out.stdout.splitlines() if line.startswith("refused: ")]


def test_a_dry_run_lists_every_deletion_with_what_it_loses_and_removes_nothing(tmp_path):
    r = Run(tmp_path)
    out = r.collect()
    assert out.returncode == 0, out.stdout + out.stderr
    a7, b7 = r.sha_a[:7], r.sha_b[:7]
    assert out.stdout.splitlines()[:-1] == [
        f"would remove worktree {r.wt_a} (branch feat/demo-a, HEAD {a7}): loses ignored .venv/",
        f"would remove worktree {r.wt_b} (branch feat/demo-b, HEAD {b7}): loses nothing",
        f"would delete branch feat/demo-a at {a7}: loses nothing (in main)",
        f"would delete branch feat/demo-b at {b7}: loses nothing (in main)",
        f"would remove {r.run / 'scratch'}: loses 2 files, 1.3 MB",
        f"would remove job {r.jobs / '0000000a'} (demo/builder-a, done): loses 3 files, 0.0 MB",
        f"would remove job {r.jobs / '0000000b'} (demo/builder-b, stopped): loses 3 files, 0.0 MB",
        f"would remove job {r.jobs / '0000000c'} (demo/critic, failed): loses 3 files, 0.0 MB",
        f"would remove {r.copy}: loses 1 files, 0.0 MB",
        f"keep {r.run / 'build-log-a.md'}",
        f"keep {r.run / 'build-log-b.md'}",
        f"keep {r.run / 'judge.md'}",
        f"keep {r.run / 'plan-log.md'}",
        f"keep {r.run / 'lessons.md'}",
        f"keep {r.page}",
        f"keep {r.summary}",
    ]
    assert re.fullmatch(
        r"total: 2 worktrees, 2 branches, 3 job folders, 2 paths; digest [0-9a-f]{12}; nothing removed without --apply",
        out.stdout.splitlines()[-1],
    )
    assert r.untouched() and (r.wt_a / ".venv" / "lib" / "site.py").is_file()
    assert r.home.claude_calls() == ["agents --json --all"]


def test_apply_with_the_owner_s_yes_removes_the_run_and_keeps_the_records(tmp_path):
    r = Run(tmp_path)
    digest = r.digest()
    out = r.collect("--apply", "--yes", digest)
    assert out.returncode == 0, out.stdout + out.stderr
    assert [line for line in out.stdout.splitlines() if line.startswith(("removed ", "deleted ", "failed "))] == [
        f"removed worktree {r.wt_a}",
        f"removed worktree {r.wt_b}",
        f"deleted branch feat/demo-a at {r.sha_a[:7]}",
        f"deleted branch feat/demo-b at {r.sha_b[:7]}",
        f"removed {r.run / 'scratch'}",
        f"removed job {r.jobs / '0000000a'}",
        f"removed job {r.jobs / '0000000b'}",
        f"removed job {r.jobs / '0000000c'}",
        f"removed {r.copy}",
    ]
    assert out.stdout.splitlines()[-1] == "done: 2 worktrees, 2 branches, 3 job folders, 2 paths removed; 0 failed"
    # 10.14, afterwards: git worktree list, git branch, scratch/ and the jobs folder show nothing of the run ...
    listed = r.git(r.repo, "worktree", "list", "--porcelain").splitlines()
    assert [line for line in listed if line.startswith("worktree ")] == [f"worktree {r.repo}"]
    assert r.git(r.repo, "branch", "--format=%(refname:short)").splitlines() == ["main"]
    assert not (r.run / "scratch").exists() and not r.copy.exists() and not r.wt_a.exists()
    assert sorted(p.name for p in r.jobs.iterdir()) == ["0000000d", "0000000e"]
    # ... and the kept items exist.
    for name in ("build-log-a.md", "build-log-b.md", "judge.md", "plan-log.md", "lessons.md", "_control/_agents.json"):
        assert (r.run / name).is_file(), name
    assert r.page.is_file() and r.summary.is_file()
    collected = (r.run / "collected.md").read_text(encoding="utf-8")
    assert re.match(
        r"# Collected \d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC\ndigest " + digest + "; the owner's yes\n", collected
    )
    assert f"\nremoved worktree {r.wt_a}\n" in collected and collected.endswith("; 0 failed\n")
    (line,) = r.history.read_text(encoding="utf-8").splitlines()
    record = json.loads(line)
    assert record == {"run": str(r.run), "at": record["at"], "digest": digest, "yes": True}
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", record["at"])


def test_a_removal_git_refuses_is_reported_and_the_rest_continues(tmp_path):
    r = Run(tmp_path)
    # A run worktree that holds a submodule: git removes it only with --force, which the collector never passes.
    sub = tmp_path / "sub"
    sub.mkdir()
    r.git(sub, "init", "-q", "-b", "main")
    r.write(sub / "s.txt", "s\n")
    r.git(sub, "add", "-A")
    r.git(sub, "commit", "-q", "-m", "s")
    r.git(r.wt_b, "-c", "protocol.file.allow=always", "submodule", "add", str(sub), "lib")
    r.git(r.wt_b, "commit", "-q", "-m", "lib")
    r.git(r.repo, "merge", "-q", "--no-ff", "feat/demo-b", "-m", "merge lib")
    digest = r.digest()
    out = r.collect("--apply", "--yes", digest)
    assert out.returncode == 1, out.stdout + out.stderr
    # git's own first stderr line for the same two removals, which still fail the same way
    wt_error = r.git_error("worktree", "remove", str(r.wt_b))
    branch_error = r.git_error("branch", "-D", "feat/demo-b")
    assert "submodule" in wt_error and "feat/demo-b" in branch_error
    assert [line for line in out.stdout.splitlines() if line.startswith(("removed ", "deleted ", "failed "))] == [
        f"removed worktree {r.wt_a}",
        f"failed worktree {r.wt_b}: {wt_error}",
        f"deleted branch feat/demo-a at {r.sha_a[:7]}",
        f"failed branch feat/demo-b: {branch_error}",
        f"removed {r.run / 'scratch'}",
        f"removed job {r.jobs / '0000000a'}",
        f"removed job {r.jobs / '0000000b'}",
        f"removed job {r.jobs / '0000000c'}",
        f"removed {r.copy}",
    ]
    assert out.stdout.splitlines()[-1] == "done: 1 worktrees, 1 branches, 3 job folders, 2 paths removed; 2 failed"
    assert (r.wt_b / "b.txt").is_file()
    assert r.git(r.repo, "branch", "--format=%(refname:short)").splitlines() == ["feat/demo-b", "main"]
    assert (r.run / "collected.md").read_text(encoding="utf-8").endswith("; 2 failed\n")
    assert json.loads(r.history.read_text(encoding="utf-8"))["yes"] is True


def test_a_record_whose_line_1_is_not_final_refuses_and_nothing_is_removed(tmp_path):
    r = Run(tmp_path)
    digest = r.digest()
    r.write(r.run / "judge.md", "STATUS: judging\n# Judge\n")
    r.write(r.run / "critique.md", "STATUS: reviewed, not done\n# Critique\n")
    r.write(r.run / "verify.md", "# Verify\nno STATUS line\n")
    r.write(r.run / "plan-log.md", "STATUS: done — Task 3 written last\n# Plan log\n")
    out = r.collect("--apply", "--yes", digest)
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        'refused: critique.md line 1 is "STATUS: reviewed, not done", not "STATUS: done"',
        'refused: judge.md line 1 is "STATUS: judging", not "STATUS: done"',
        "refused: check_formats.py exit 1: ERROR verify.md: line 1 is not `STATUS: …`",
    ]
    assert out.stdout.splitlines()[-1] == "nothing removed: 3 refusals"
    assert "digest" not in out.stdout and r.untouched()


def test_a_deferred_item_absent_from_the_tracker_on_main_refuses_and_fenced_code_holds_none(tmp_path):
    r = Run(tmp_path)
    # TASK_2's fenced block (indented; four backticks, holding a shorter fence and a longer-or-equal one with an info
    # string, neither of which closes it) holds a heading and an item: neither counts.
    r.write(r.repo / PLAN / "task-02.md", TASK_2)
    r.git(r.repo, "add", "-A")
    r.git(r.repo, "commit", "-q", "-m", "task 2")
    # The task file deleted in the main worktree and a row for one of its items added there, neither committed:
    # the check reads the main branch.
    (r.repo / PLAN / "task-02.md").unlink()
    with (r.repo / TRACKER).open("a", encoding="utf-8") as f:
        f.write("| TD-015 | watcher | ids | none | maintainers | low | demo Deferred: The registry ids |\n")
    out = r.collect()
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        'refused: Deferred item "TD-099 a row nobody wrote" (task-02.md) is not in the tracker',
        'refused: Deferred item "The registry ids" (task-02.md) is not in the tracker',
    ]


def test_a_final_commit_that_is_not_an_ancestor_of_main_refuses(tmp_path):
    r = Run(tmp_path)
    side = r.side_commit()
    lost = "fedcba9876543210fedcba9876543210fedcba98"
    with (r.run / "build-log-a.md").open("a", encoding="utf-8") as f:
        f.write(f"Task 4: done — {lost}\n")
    with (r.run / "build-log-b.md").open("a", encoding="utf-8") as f:
        f.write(f"- Task 3: done — {side}\n")
    unknown = "0123456789abcdef0123456789abcdef01234567"
    out = r.collect("--final", r.main, "--final", unknown)
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        f"refused: check_formats.py exit 1: ERROR build-log-a.md: Task 4: done — {lost} is not a commit of {r.repo}",
        f"refused: {lost} (build-log-a.md Task 4) is not a commit of {r.repo}",
        f"refused: {side[:7]} (build-log-b.md Task 3) is not an ancestor of main",
        f"refused: {unknown} (--final) is not a commit of {r.repo}",
    ]


def test_no_final_commit_named_refuses_until_one_is_given(tmp_path):
    r = Run(tmp_path)
    for name in ("build-log-a.md", "build-log-b.md"):
        r.write(r.run / name, "STATUS: done\n# Build log\n")
    out = r.collect()
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        'refused: no final commit named (no "Task N: done — <sha>" line in a build log, no --final)'
    ]
    out = r.collect("--final", r.main)
    assert out.returncode == 0, out.stdout + out.stderr


def test_unsaved_work_in_a_run_worktree_or_on_a_run_branch_refuses(tmp_path):
    r = Run(tmp_path)
    r.write(r.wt_a / "draft.txt", "never committed\n")
    r.write(r.wt_a / "a.txt", "changed\n")
    r.git(r.wt_b, "commit", "-q", "--allow-empty", "-m", "late work")
    late = r.git(r.wt_b, "rev-parse", "HEAD")
    loose_tree = tmp_path / "wt-c"
    r.git(r.repo, "worktree", "add", "-q", "--detach", str(loose_tree))
    r.git(loose_tree, "commit", "-q", "--allow-empty", "-m", "detached work")
    loose = r.git(loose_tree, "rev-parse", "HEAD")
    out = r.collect("--worktree", str(loose_tree))
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        f"refused: worktree {r.wt_a} has 2 uncommitted paths",
        f"refused: worktree {loose_tree} HEAD {loose[:7]} is not in main",
        f"refused: branch feat/demo-b at {late[:7]} has 1 commits not in main",
    ]
    lines = out.stdout.splitlines()
    a7 = r.sha_a[:7]
    assert (
        f"would remove worktree {r.wt_a} (branch feat/demo-a, HEAD {a7}): loses 2 uncommitted paths; ignored .venv/"
        in lines
    )
    assert f"would remove worktree {r.wt_b} (branch feat/demo-b, HEAD {late[:7]}): loses nothing" in lines
    assert f"would remove worktree {loose_tree} (detached, HEAD {loose[:7]}): loses 1 commits not in main" in lines
    assert f"would delete branch feat/demo-b at {late[:7]}: loses 1 commits not in main" in lines


def test_a_run_worktree_whose_only_untracked_paths_are_empty_placeholders_is_collected(tmp_path):
    r = Run(tmp_path)  # C505: the sandbox leaves 0-byte mount points, untracked, in a role's worktree
    r.write(r.wt_a / "docs" / ".mcp.json", "")
    r.write(r.wt_a / "docs" / ".claude" / "settings.json", "")
    r.write(r.wt_b / "notes" / "sub" / "empty.txt", "")
    link = r.wt_b / "notes" / "sub" / "link"
    link.symlink_to("empty.txt")  # a symlink is never empty, not even one to a 0-byte file
    out = r.collect()
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [f"refused: worktree {r.wt_b} has 1 uncommitted paths"]
    link.unlink()
    out = r.collect()
    assert out.returncode == 0, out.stdout + out.stderr
    a7, b7 = r.sha_a[:7], r.sha_b[:7]
    lines = out.stdout.splitlines()
    assert (
        f"would remove worktree {r.wt_a} (branch feat/demo-a, HEAD {a7}): loses 2 empty untracked paths; ignored .venv/"
        in lines
    )
    assert f"would remove worktree {r.wt_b} (branch feat/demo-b, HEAD {b7}): loses 1 empty untracked paths" in lines
    assert (r.wt_a / "docs" / ".mcp.json").is_file()  # the dry run removes nothing
    out = r.collect("--apply", "--yes", r.digest())
    assert out.returncode == 0, out.stdout + out.stderr
    done = [line for line in out.stdout.splitlines() if line.startswith(("removed worktree", "deleted ", "failed "))]
    assert done == [
        f"removed worktree {r.wt_a}",
        f"removed worktree {r.wt_b}",
        f"deleted branch feat/demo-a at {a7}",
        f"deleted branch feat/demo-b at {b7}",
    ]
    assert not r.wt_a.exists() and not r.wt_b.exists()


def test_a_session_of_the_run_still_running_refuses(tmp_path):
    r = Run(tmp_path)
    r.job("0000000f", "demo/builder-b", r.wt_b, "done", pid=4242)
    r.job("00000010", "demo/critic", r.run, "waiting")
    r.job("00000011", "demo/critic", tmp_path / "elsewhere", "running")  # another run's session
    out = r.collect()
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        "refused: session demo/builder-b (0000000f) is still running",
        "refused: session demo/critic (00000010) is still running",
    ]


def test_a_lesson_without_a_skill_mark_refuses_and_a_merge_record_needs_none(tmp_path):
    r = Run(tmp_path)
    side = r.side_commit()
    unmarked = "10:20 UTC (verifier; V3): an unmarked rule that never reached the skill"
    with (r.run / "lessons.md").open("a", encoding="utf-8") as f:
        f.write(f"- {unmarked}\n- 10:25 UTC (builder; B4): marked with a commit off main (skill: {side[:9]})\n")
    out = r.collect()
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        f"refused: lesson without a (skill: <sha>|none) mark: {unmarked[:60]}",
        f"refused: lesson mark {side[:9]} is not in main",
    ]


def test_a_missing_kept_item_or_one_inside_a_deletion_refuses(tmp_path):
    r = Run(tmp_path)
    missing = tmp_path / "vault" / "missing.md"
    notes = r.run / "scratch" / "planner" / "notes.md"
    out = r.collect("--kept", str(missing), "--kept", str(notes), "--kept", str(r.wt_a / "a.txt"))
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        f"refused: kept {missing} is missing",
        f"refused: kept {notes} lies inside {r.run / 'scratch'}",
        f"refused: kept {r.wt_a / 'a.txt'} lies inside {r.wt_a}",
    ]


def test_the_owner_s_yes_holds_for_the_list_it_was_given_for(tmp_path):
    r = Run(tmp_path)
    digest = r.digest()
    lines = [
        f"worktree {r.wt_a} {r.sha_a}",
        f"worktree {r.wt_b} {r.sha_b}",
        f"branch feat/demo-a {r.sha_a}",
        f"branch feat/demo-b {r.sha_b}",
        f"path {r.run / 'scratch'}",
        "job 0000000a",
        "job 0000000b",
        "job 0000000c",
        f"path {r.copy}",
    ]
    assert digest == hashlib.sha256("\n".join(sorted(lines)).encode()).hexdigest()[:12]
    r.git(r.wt_b, "commit", "-q", "--allow-empty", "-m", "late work")
    r.git(r.repo, "merge", "-q", "--no-ff", "feat/demo-b", "-m", "merge late work")
    now = r.digest()
    assert now != digest
    out = r.collect("--apply", "--yes", digest)
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [f"refused: the list changed since the owner's yes (digest {now}, yes given for {digest})"]
    assert r.untouched()
    r.write(r.run / "scratch" / "late.log", "written after the dry run\n")
    out = r.collect("--apply", "--yes", now)
    assert out.returncode == 0, out.stdout + out.stderr
    assert not (r.run / "scratch").exists()


def test_apply_without_a_yes_waits_for_three_runs_applied_with_one(tmp_path):
    r = Run(tmp_path)
    old = [
        {"run": "/runs/r1", "at": "2026-10-21T10:00:00Z", "digest": "0" * 12, "yes": True},
        {"run": "/runs/r2", "at": "2026-10-22T10:00:00Z", "digest": "1" * 12, "yes": False},
        {"run": "/runs/r3", "at": "2026-10-23T10:00:00Z", "digest": "2" * 12, "yes": True},
    ]
    r.write(r.history, "".join(json.dumps(x) + "\n" for x in old))
    out = r.collect("--apply")
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        f"refused: --apply needs --yes <digest> until the owner has said yes for three runs (2 of 3 in {r.history})"
    ]
    assert r.untouched()
    with r.history.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"run": "/runs/r4", "at": "2026-10-24T10:00:00Z", "digest": "3" * 12, "yes": True}) + "\n")
    out = r.collect("--apply")
    assert out.returncode == 0, out.stdout + out.stderr
    record = json.loads(r.history.read_text(encoding="utf-8").splitlines()[-1])
    assert record["yes"] is False and record["run"] == str(r.run)
    assert "; the standing rule\n" in (r.run / "collected.md").read_text(encoding="utf-8")


def test_one_run_applied_three_times_with_a_yes_counts_once_toward_the_three(tmp_path):
    r = Run(tmp_path)
    old = [
        {"run": "/runs/r1", "at": "2026-10-21T10:00:00Z", "digest": "0" * 12, "yes": True},
        {"run": "/runs/r1", "at": "2026-10-21T10:05:00Z", "digest": "1" * 12, "yes": True},
        {"run": "/runs/r1", "at": "2026-10-21T10:10:00Z", "digest": "2" * 12, "yes": True},
        {"run": "/runs/r2", "at": "2026-10-22T10:00:00Z", "digest": "3" * 12, "yes": False},
        {"at": "2026-10-23T10:00:00Z", "digest": "4" * 12, "yes": True},
    ]
    r.write(r.history, "".join(json.dumps(x) + "\n" for x in old))
    out = r.collect("--apply")
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        f"refused: --apply needs --yes <digest> until the owner has said yes for three runs (1 of 3 in {r.history})"
    ]
    assert r.untouched()


def test_a_deletion_that_holds_the_run_folder_or_the_main_worktree_refuses(tmp_path):
    r = Run(tmp_path)
    r.git(r.repo, "worktree", "add", "-q", "-b", "feat/demo-x", str(tmp_path / "wt-x"))
    (tmp_path / "plain").mkdir()
    out = r.collect(
        "--worktree",
        str(r.repo),
        "--worktree",
        str(tmp_path / "plain"),
        "--branch",
        "main",
        "--branch",
        "feat/none",
        "--branch",
        "feat/demo-x",
        "--also",
        str(tmp_path / "runs"),
        "--also",
        str(tmp_path / "gone"),
    )
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        f"refused: {r.repo} holds the run folder or the main worktree",
        f"refused: {tmp_path / 'plain'} is not a worktree of {r.repo}",
        "refused: branch main is the main branch",
        "refused: no branch feat/none",
        f"refused: branch feat/demo-x is checked out in {tmp_path / 'wt-x'}",
        f"refused: {tmp_path / 'runs'} holds the run folder or the main worktree",
        f"refused: {tmp_path / 'gone'} is missing",
    ]


def test_a_symlinked_scratch_is_skipped_and_never_followed(tmp_path):
    r = Run(tmp_path)
    elsewhere = tmp_path / "shared-scratch"
    (r.run / "scratch").rename(elsewhere)
    (r.run / "scratch").symlink_to(elsewhere, target_is_directory=True)
    out = r.collect()
    assert out.returncode == 0, out.stdout + out.stderr
    lines = out.stdout.splitlines()
    assert (
        lines[lines.index(f"would remove {r.copy}: loses 1 files, 0.0 MB") + 1]
        == f"skipped {r.run / 'scratch'}: a symlink"
    )
    assert not [line for line in lines if line.startswith(f"would remove {r.run / 'scratch'}")]
    assert lines[-1].startswith("total: 2 worktrees, 2 branches, 3 job folders, 1 paths; digest ")
    out = r.collect("--apply", "--yes", r.digest())
    assert out.returncode == 0, out.stdout + out.stderr
    assert (r.run / "scratch").is_symlink() and (elsewhere / "copy.bin").is_file()


def test_every_function_of_the_collector_is_under_50_lines():
    """.claude/rules/python.md:9: keep functions under 50 lines."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    lengths = {
        node.name: node.end_lineno - node.lineno + 1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "main" in lengths
    assert {name: n for name, n in lengths.items() if n >= 50} == {}


def test_a_missing_run_folder_agents_file_or_main_branch_or_a_failed_listing_exits_2(tmp_path):
    r = Run(tmp_path)
    out = r.home.run("collect_run.py", str(tmp_path / "no-run"), "--repo", str(r.repo), "--plan", PLAN, "--kept", "x")
    assert (out.returncode, out.stdout) == (2, "")
    assert out.stderr == f"collect_run.py: no run folder {tmp_path / 'no-run'}\n"
    out = r.collect("--main", "trunk")
    assert (out.returncode, out.stdout, out.stderr) == (2, "", f"collect_run.py: no branch trunk in {r.repo}\n")
    out = r.collect("--yes", "0" * 12)
    assert out.returncode == 2 and "collect_run.py: error: --yes needs --apply" in out.stderr
    (r.home.stub / "agents.json").write_text("not json", encoding="utf-8")
    out = r.collect()
    assert (out.returncode, out.stdout) == (2, "")
    assert out.stderr == "collect_run.py: claude agents --json --all failed or printed no JSON list\n"
    (r.run / "_control" / "_agents.json").unlink()
    out = r.collect()
    assert (out.returncode, out.stdout) == (2, "")
    assert out.stderr.startswith(f"collect_run.py: cannot read the agents file {r.run / '_control' / '_agents.json'}: ")
    assert r.untouched()


def test_also_refuses_a_path_inside_the_run_folder_other_than_scratch(tmp_path):
    """J4 (judge.md of manager-build-2026-10-29, #### J4): `--also` could name a kept record file, and nothing
    refused it."""
    r = Run(tmp_path)
    log, lessons, notes = r.run / "build-log-a.md", r.run / "lessons.md", r.run / "scratch" / "planner" / "notes.md"
    out = r.collect("--also", str(log), "--also", str(lessons), "--also", str(notes))
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        f"refused: {log} lies in the run folder outside scratch/",
        f"refused: {lessons} lies in the run folder outside scratch/",
    ]


def test_the_module_docstring_lists_the_also_refusal_of_the_save_check():
    """R13: the docstring's list of the save check's refusals holds J4's, in the order of docs/collect_run.md."""
    doc = " ".join(ast.get_docstring(ast.parse(SCRIPT.read_text(encoding="utf-8"))).split())
    assert "lies inside a deletion, an `--also` path lies in the run folder outside `scratch/`, a build log's" in doc
