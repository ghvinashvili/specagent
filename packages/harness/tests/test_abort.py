"""A run ends with integrate or abort, and what a run leaves behind is reported
(docs/decisions/0010-a-run-ends-with-integrate-or-abort.md)."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pytest
from harness import cli, doctor, launch, leftovers, loops, poll, state, work

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "docs" / "roles" / "stages.yaml").is_file())
BRIEF = "# Project brief — demo\n\n## Goal of this run\nNotes.\n\n## Constraints\n- Budget: 10 minutes per stage\n"


@pytest.fixture()
def made(tmp_path: Path, copy_config):
    """A copy of the repository's tables and schemas with one run just created."""
    root = tmp_path / "repo"
    copy_config(ROOT, root)
    brief = tmp_path / "brief.md"
    brief.write_text(BRIEF, encoding="utf-8")
    run_id = state.create_run(root, "demo", brief, [])["run_id"]
    return root, run_id, state.runs_root(root) / run_id


def test_changed_at_moves_only_when_what_matters_changes(made, monkeypatch):
    """A poll writes `updated_at` and `last_poll` every time; a run nobody works on must still look unchanged."""
    root, _, run_dir = made
    path = run_dir / "state.json"
    st = state.load(root, path, "run-state")
    first = st["changed_at"]
    monkeypatch.setattr(state, "now", lambda: "2031-01-01T00:00:00+00:00")
    st["updated_at"] = state.now()
    st["stages"]["read"]["last_poll"] = {"at": state.now(), "state": "working", "status": "idle", "waitingFor": None}
    state.save(root, path, st, "run-state")
    assert state.load(root, path, "run-state")["changed_at"] == first
    st["stages"]["read"]["status"] = "launched"
    state.save(root, path, st, "run-state")
    assert state.load(root, path, "run-state")["changed_at"] == "2031-01-01T00:00:00+00:00"


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch):
    for var in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"):
        monkeypatch.delenv(var, raising=False)
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "A Writer")
    git(root, "config", "user.email", "writer@example.com")
    git(root, "config", "commit.gpgsign", "false")
    (root / ".gitignore").write_text(".venv/\n")
    (root / "a.txt").write_text("one\n")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "base")
    return root


def checkout(root: Path, name: str) -> Path:
    path = root / ".claude" / "worktrees" / name
    git(root, "worktree", "add", "-q", "-b", f"worktree-{name}", str(path), "main")
    return path


def test_a_checkout_with_uncommitted_work_is_saved_before_it_goes(repo):
    """`git worktree remove -f -f` discarded uncommitted work unasked; now it becomes a commit the human can restore."""
    path = checkout(repo, "r1-write")
    (path / "a.txt").write_text("two\n")  # a tracked change
    (path / "new.txt").write_text("new\n")  # an untracked file
    (path / ".venv").mkdir()
    (path / ".venv" / "big").write_text("x")  # ignored: made again, not kept
    saved = work.remove_checkout(repo, path, "refs/harness/salvage/r1/r1-write")
    assert saved and not path.exists()
    assert git(repo, "rev-parse", "refs/harness/salvage/r1/r1-write") == saved
    assert git(repo, "show", f"{saved}:a.txt") == "two" and git(repo, "show", f"{saved}:new.txt") == "new"
    assert ".venv/big" not in git(repo, "ls-tree", "-r", "--name-only", saved)
    assert git(repo, "rev-parse", f"{saved}^") == git(repo, "rev-parse", "worktree-r1-write")


def test_a_clean_checkout_goes_without_a_ref(repo):
    path = checkout(repo, "r1-read")
    assert work.remove_checkout(repo, path, "refs/harness/salvage/r1/r1-read") is None
    assert not path.exists()
    assert git(repo, "for-each-ref", "refs/harness") == ""


@pytest.fixture()
def in_repo(made, monkeypatch):
    """The run of `made` in a repository of its own; `claude` is not run, its calls are recorded."""
    root, run_id, run_dir = made
    for var in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"):
        monkeypatch.delenv(var, raising=False)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "A Writer")
    git(root, "config", "user.email", "writer@example.com")
    git(root, "config", "commit.gpgsign", "false")
    (root / ".gitignore").write_text(".claude/worktrees/\n")
    (root / "notes.txt").write_text("one\n")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "base")
    calls: list[list[str]] = []
    real = subprocess.run

    def fake(cmd, *args, **kwargs):
        if cmd and cmd[0] == "claude":
            calls.append(list(cmd[:3]))
            return subprocess.CompletedProcess(cmd, 0, "[]" if cmd[1:2] == ["agents"] else "", "")
        return real(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake)
    return root, run_id, run_dir, calls


def test_abort_ends_a_run_and_keeps_its_record(in_repo):
    root, run_id, run_dir, calls = in_repo
    path = run_dir / "state.json"
    st = state.load(root, path, "run-state")
    st["stages"]["read"].update(status="done", attempts=1, session_ids=["s1"], job_ids=["j1"], gate="pass")
    st["stages"]["write"].update(status="working", attempts=1)
    shard = {"status": "working", "attempts": 1, "session_ids": ["s2"], "job_ids": ["j2"], "gate": "pending"}
    st["stages"]["write"]["shards"] = {"01": shard}
    st["status"] = "running"
    state.save(root, path, st, "run-state")
    (run_dir / "stages" / "write" / "01").mkdir(parents=True)
    name = launch.worktree_name(run_id, "write", 1)
    co = checkout(root, name)
    (co / "notes.txt").write_text("two\n")
    git(co, "commit", "-qam", "feat: two")
    (co / "draft.txt").write_text("half\n")  # work the writer had not committed

    out = work.abort_run(root, run_id, "the human stopped it")
    assert out["ok"] and out["status"] == "aborted" and out["from"] == "running"
    after = state.load(root, path, "run-state")
    assert after["status"] == "aborted"
    assert after["aborted"]["reason"] == "the human stopped it" and after["aborted"]["from"] == "running"
    assert (
        calls.index(["claude", "stop", "j2"]) < calls.index(["claude", "rm", "j2"]) and ["claude", "rm", "j1"] in calls
    )
    assert not co.exists() and f"worktree-{name}" in git(root, "branch", "--format=%(refname:short)").split()
    ref = f"refs/harness/salvage/{run_id}/{name}"
    assert out["salvaged"] == [ref] and git(root, "show", f"{ref}:draft.txt") == "half"
    assert (run_dir / "brief.md").is_file() and (run_dir / "manifest.json").is_file()


def test_abort_takes_a_finished_run_that_was_not_integrated(in_repo):
    root, run_id, run_dir, _ = in_repo
    st = state.load(root, run_dir / "state.json", "run-state")
    st["status"] = "done"
    state.save(root, run_dir / "state.json", st, "run-state")
    assert work.abort_run(root, run_id, "a trial, not to be merged")["ok"]
    assert state.load(root, run_dir / "state.json", "run-state")["aborted"]["from"] == "done"


def test_abort_refuses_an_integrated_run(in_repo):
    root, run_id, run_dir, _ = in_repo
    git(root, "branch", f"run/{run_id}")
    out = work.abort_run(root, run_id, "late")
    assert not out["ok"] and out["status"] == "integrated" and f"integrate --run {run_id} --clean" in out["hint"]
    assert state.load(root, run_dir / "state.json", "run-state")["status"] == "created"


def test_a_second_abort_changes_nothing(in_repo):
    root, run_id, run_dir, _ = in_repo
    assert work.abort_run(root, run_id, "first")["ok"]
    before = (run_dir / "state.json").read_text(encoding="utf-8")
    out = work.abort_run(root, run_id, "second")
    assert out["ok"] and out["already"] and (run_dir / "state.json").read_text(encoding="utf-8") == before


# The least each command needs besides --run.
ARGS = {
    "status": ["--stage", "read"],
    "assign": ["--stage", "read"],
    "launch": ["--stage", "read"],
    "poll": [],
    "resume": ["--stage", "read", "--message", "go on"],
    "gate": ["--stage", "read"],
    "approve": ["--stage", "read", "--decision", "approved"],
    "refreeze": [],
    "integrate": [],
    "escalations": [],
    "handoff": [],
    "limits": [],
    "material": ["--stage", "read"],
    "cache-report": [],
    "watch": ["--every", "1", "--max-minutes", "1"],
    "route": [],
    "abort": ["--reason", "again"],
    "steps": [],
}


def commands_with_a_run() -> set[str]:
    sub = next(a for a in cli.build_parser()._actions if isinstance(a, argparse._SubParsersAction))
    return {name for name, p in sub.choices.items() if any("--run" in a.option_strings for a in p._actions)}


def files(run_dir: Path) -> dict[str, bytes]:
    return {str(f.relative_to(run_dir)): f.read_bytes() for f in sorted(run_dir.rglob("*")) if f.is_file()}


def test_every_command_that_takes_a_run_says_whether_it_changes_one():
    """A new command must be declared, or this fails: that is how no command forgets the aborted run."""
    assert commands_with_a_run() == set(cli.RUN_COMMANDS) == set(ARGS)


@pytest.mark.parametrize("command", sorted(ARGS))
def test_no_command_changes_an_aborted_run(command, in_repo, monkeypatch, capsys):
    root, run_id, run_dir, calls = in_repo
    assert work.abort_run(root, run_id, "over")["ok"]
    calls.clear()
    capsys.readouterr()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    before = files(run_dir)
    code = cli.main([command, "--run", run_id, *ARGS[command]])
    out = capsys.readouterr().out
    assert files(run_dir) == before and all(c[1] == "agents" for c in calls)
    if cli.RUN_COMMANDS[command] == "changes":
        assert code == 1 and json.loads(out)["status"] == "run_aborted"


def test_a_loop_counts_an_aborted_run_as_a_failure(in_repo):
    """A run that is not finished counts as active, and a loop waited for ever on the one it had abandoned."""
    root, run_id, _, _ = in_repo
    assert work.abort_run(root, run_id, "over")["ok"]
    assert loops._outcome(root, run_id)[0] == "failure"


def finished_read(root: Path, run_dir: Path, approval: str) -> None:
    st = state.load(root, run_dir / "state.json", "run-state")
    unit = st["stages"]["read"]
    unit.update(status="done", attempts=1, session_ids=["s1"], job_ids=["j1"], gate="pass", approval=approval)
    state.save(root, run_dir / "state.json", st, "run-state")


def stops(monkeypatch) -> list[list[str]]:
    calls: list[list[str]] = []

    def fake(cmd, *args, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(poll.subprocess, "run", fake)
    return calls


IDLE = {"id": "j1", "sessionId": "s1", "pid": 4242, "status": "idle", "state": "done"}


def test_a_finished_stage_lets_its_idle_session_go(made, monkeypatch):
    """An idle session held about 300 MB until the run was integrated, and for ever when it was not; resume brings a
    stopped session back, so nothing is lost."""
    root, run_id, run_dir = made
    finished_read(root, run_dir, "not_required")
    calls = stops(monkeypatch)
    poll.poll(root, run_id, listing=[IDLE])
    assert calls == [["claude", "stop", "j1"]]


@pytest.mark.parametrize(
    ("approval", "row"),
    [
        ("pending", IDLE),  # the human may still ask it something
        ("not_required", {**IDLE, "status": "busy"}),
        ("not_required", {"id": "j1", "sessionId": "s1", "state": "stopped"}),  # already stopped
    ],
)
def test_a_session_that_may_still_be_needed_or_is_gone_is_left(made, monkeypatch, approval, row):
    root, run_id, run_dir = made
    finished_read(root, run_dir, approval)
    calls = stops(monkeypatch)
    poll.poll(root, run_id, listing=[row])
    assert calls == []


def plugin_records(config: Path, known: dict, installed: dict) -> None:
    (config / "plugins").mkdir(parents=True)
    (config / "plugins" / "known_marketplaces.json").write_text(json.dumps(known))
    (config / "plugins" / "installed_plugins.json").write_text(json.dumps({"version": 2, "plugins": installed}))


def test_leftovers_names_what_runs_left_behind(in_repo, tmp_path, monkeypatch):
    root, run_id, run_dir, _ = in_repo
    doc = json.loads((run_dir / "state.json").read_text())
    doc["changed_at"] = doc["updated_at"] = "2026-01-01T00:00:00+00:00"  # opened, then forgotten
    (run_dir / "state.json").write_text(json.dumps(doc))
    brief = tmp_path / "brief.md"
    gone = state.create_run(root, "gone", brief, [])["run_id"]
    st = state.load(root, state.runs_root(root) / gone / "state.json", "run-state")
    st["stages"]["read"].update(status="done", attempts=1, session_ids=["s9"], job_ids=["j9"], gate="pass")
    state.save(root, state.runs_root(root) / gone / "state.json", st, "run-state")
    assert work.abort_run(root, gone, "over")["ok"]
    (root / ".claude" / "worktrees" / "stray").mkdir(parents=True)
    (root / "plugins" / ".claude-plugin").mkdir(parents=True)
    (root / "plugins" / ".claude-plugin" / "marketplace.json").write_text(json.dumps({"name": "example-repo-plugins"}))
    config = tmp_path / "config"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
    missing = {"source": {"source": "directory", "path": str(tmp_path / "moved" / "plugins")}}
    plugin_records(
        config,
        {"example-repo-plugins": missing, "harness-internal": missing, "other-plugins": missing},
        {
            "code-intel@harness-internal": [{"scope": "project", "projectPath": str(tmp_path / "moved")}],
            "x@other-plugins": [{"scope": "project", "projectPath": str(tmp_path / "moved")}],
        },
    )
    rows = [{"id": "j9", "sessionId": "s9", "pid": 7, "status": "idle", "cwd": str(root)}]
    found = leftovers.find(root, listing=rows)
    kinds = sorted(f["kind"] for f in found)
    assert kinds == ["checkout", "live_session", "marketplace", "marketplace", "plugin", "stale_run"]
    assert all("other-plugins" not in f["what"] for f in found)  # another project's records are its own
    stale = next(f for f in found if f["kind"] == "stale_run")
    assert run_id in stale["what"] and f"harness abort --run {run_id}" in stale["fix"]
    assert "claude stop j9" in next(f for f in found if f["kind"] == "live_session")["fix"]


def test_a_project_with_nothing_left_behind_has_no_leftovers(made, tmp_path, monkeypatch):
    root, _, _ = made
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "config"))
    assert leftovers.find(root, listing=[]) == []


def test_a_marked_runs_folder_beside_another_checkout_is_named(tmp_path, copy_config, monkeypatch):
    root = tmp_path / "box" / "repo"
    copy_config(ROOT, root)
    (tmp_path / "box" / "clone" / ".git").mkdir(parents=True)
    (tmp_path / "box" / "runs").mkdir()
    (tmp_path / "box" / "runs" / state.RUNS_MARKER).write_text("")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "config"))
    found = leftovers.find(root, listing=[])
    assert [f["kind"] for f in found] == ["shared_runs"] and "clone" in found[0]["what"]


def test_a_new_run_names_the_runs_still_open(made, tmp_path, monkeypatch, capsys):
    """The manager asks the human about each open run before more work piles up; the new run is not one of them."""
    root, first, _ = made
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    capsys.readouterr()
    assert cli.main(["run", "--slug", "second", "--brief", str(tmp_path / "brief.md")]) == 0
    out = json.loads(capsys.readouterr().out)
    assert [r["run_id"] for r in out["open_runs"]] == [first]
    assert out["open_runs"][0]["waits_for"] == "nothing" and out["open_runs"][0]["status"] == "created"


def test_doctor_shows_the_leftovers_with_what_removes_them(in_repo, tmp_path, monkeypatch):
    root, _, _, _ = in_repo
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "config"))
    (root / ".claude" / "worktrees" / "stray").mkdir(parents=True)
    item = doctor.leftovers_check(root, listing=[])
    assert not item["ok"] and not item["required"] and [f["kind"] for f in item["found"]] == ["checkout"]
    assert "git worktree remove" in item["fix"]


def test_looking_for_leftovers_creates_nothing(tmp_path, monkeypatch):
    """`harness doctor` looks; it must not make the runs root it looks in (seen: a test of doctor made one)."""
    root = tmp_path / "fresh"
    root.mkdir()
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "config"))
    assert leftovers.find(root, listing=[]) == [] and leftovers.open_runs(root) == []
    assert sorted(p.name for p in tmp_path.iterdir()) == ["fresh"]


# --- the review of server-e6 (2026-10-03) ---

STEERING = sorted(c for c, kind in cli.RUN_COMMANDS.items() if kind == "changes") + ["abort"]


@pytest.mark.parametrize("command", STEERING)
def test_a_role_session_does_not_steer_its_run(command, made, monkeypatch, capsys):
    """Every session may run `uv run *`, and abort and integrate run outside the sandbox: a writer that decided to
    tidy up could stop every session of its run and remove its checkouts."""
    root, run_id, run_dir = made
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.setenv("HARNESS_ROLE", "writer")
    before = files(run_dir)
    capsys.readouterr()
    assert cli.main([command, "--run", run_id, *ARGS[command]]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "role_session" and files(run_dir) == before


def test_a_role_session_runs_only_the_commands_listed_for_it(tmp_path, small_config, monkeypatch, capsys):
    """02/F23 and item 4 of the brief of wave 1: with HARNESS_ROLE set every command refuses but the ones a role
    session or one of its hooks runs (cli.ROLE_COMMANDS). poll and watch were declared reads and passed, though each
    gates units, rewrites state.json and stops sessions; a command added later refuses as well."""
    monkeypatch.setattr(state, "claude_version", lambda: "test")  # no `claude` in a role session's sandbox
    root = small_config(tmp_path / "repo")
    brief = tmp_path / "brief.md"
    brief.write_text(BRIEF, encoding="utf-8")
    run_id = state.create_run(root, "demo", brief, [])["run_id"]
    run_dir = state.runs_root(root) / run_id
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.setenv("HARNESS_ROLE", "writer")
    for argv in (["poll", "--run", run_id], ["watch", "--run", run_id, "--every", "1", "--max-minutes", "1"]):
        before = files(run_dir)
        capsys.readouterr()
        assert cli.main(argv) == 1
        assert json.loads(capsys.readouterr().out)["status"] == "role_session" and files(run_dir) == before
    sub = next(a for a in cli.build_parser()._actions if isinstance(a, argparse._SubParsersAction))
    assert set(cli.ROLE_COMMANDS) <= set(sub.choices)
    for name in sub.choices:
        plain = argparse.Namespace(cmd=name, preview=False, op="tick")
        assert cli.role_may_run(plain) == (name in cli.ROLE_COMMANDS and name not in ("gate", "loop")), name
    assert cli.role_may_run(argparse.Namespace(cmd="gate", preview=True))  # the stop hook's preview
    assert cli.role_may_run(argparse.Namespace(cmd="loop", op="validate"))
    assert not cli.role_may_run(argparse.Namespace(cmd="a-command-added-later"))


def test_the_stop_hook_of_a_role_session_may_still_preview_its_gate(made, monkeypatch, capsys):
    root, run_id, _ = made
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.setenv("HARNESS_ROLE", "reader")
    capsys.readouterr()
    cli.main(["gate", "--run", run_id, "--stage", "read", "--preview"])
    assert json.loads(capsys.readouterr().out).get("status") != "role_session"


def test_a_run_from_before_changed_at_keeps_the_time_of_its_last_write(made):
    """Runs made before `changed_at` existed fell back to `updated_at`, which every poll moves: never stale."""
    root, _, run_dir = made
    doc = json.loads((run_dir / "state.json").read_text())
    del doc["changed_at"]
    doc["updated_at"] = "2026-01-01T00:00:00+00:00"
    (run_dir / "state.json").write_text(json.dumps(doc))
    st = state.load(root, run_dir / "state.json", "run-state")
    st["updated_at"] = state.now()  # a poll that found nothing new
    state.save(root, run_dir / "state.json", st, "run-state")
    assert state.load(root, run_dir / "state.json", "run-state")["changed_at"] == "2026-01-01T00:00:00+00:00"


def test_a_finished_run_that_was_never_closed_is_named(in_repo, monkeypatch, tmp_path):
    """A planning run ends `done` with nothing to integrate; its sessions stayed listed for ever."""
    root, run_id, run_dir, _ = in_repo
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "config"))
    doc = json.loads((run_dir / "state.json").read_text())
    doc["status"] = "done"
    doc["stages"]["read"].update(status="done", job_ids=["j1"], session_ids=["s1"])
    doc["changed_at"] = doc["updated_at"] = "2026-01-01T00:00:00+00:00"
    (run_dir / "state.json").write_text(json.dumps(doc))
    (run_dir / "stages" / "write" / "01").mkdir(parents=True)
    (root / ".claude" / "worktrees" / launch.worktree_name(run_id, "write", 1)).mkdir(parents=True)
    found = leftovers.find(root, listing=[{"id": "j1", "sessionId": "s1", "state": "stopped"}])
    assert [f["kind"] for f in found] == ["unclosed_run"]  # its checkout is its own, not "no open run"
    assert f"harness integrate --run {run_id} --clean" in found[0]["fix"]


def test_integrate_clean_closes_a_run_that_committed_nothing(in_repo):
    root, run_id, run_dir, calls = in_repo
    doc = json.loads((run_dir / "state.json").read_text())
    for ss in doc["stages"].values():
        ss.update(
            status="done", gate="pass", approval="approved" if ss["approval"] != "not_required" else "not_required"
        )
    doc["stages"]["plan"]["job_ids"] = ["j7"]
    (run_dir / "state.json").write_text(json.dumps(doc))
    out = work.integrate_run(root, run_id, clean=True)
    assert out["ok"] and out["status"] == "nothing_committed" and out["cleaned"]["sessions"] == ["j7"]
    assert ["claude", "rm", "j7"] in calls


def test_abort_takes_the_stages_the_run_was_made_with(in_repo, monkeypatch):
    """A stage dropped from the table after the run started still had a checkout to remove."""
    root, run_id, run_dir, _ = in_repo
    (run_dir / "stages" / "write" / "01").mkdir(parents=True)
    co = checkout(root, launch.worktree_name(run_id, "write", 1))
    real = state.load_table
    monkeypatch.setattr(
        state,
        "load_table",
        lambda r, p="default": {**real(r, p), "stages": [s for s in real(r, p)["stages"] if s["id"] != "write"]},
    )
    assert work.abort_run(root, run_id, "over")["ok"] and not co.exists()


def test_a_checkout_that_could_not_go_is_not_reported_as_gone(in_repo, monkeypatch):
    root, run_id, run_dir, _ = in_repo
    (run_dir / "stages" / "write" / "01").mkdir(parents=True)
    (run_dir / "stages" / "write" / "02").mkdir(parents=True)
    plain = root / ".claude" / "worktrees" / launch.worktree_name(run_id, "write", 1)
    plain.mkdir(parents=True)  # a folder git does not know: `git worktree remove` fails
    co = checkout(root, launch.worktree_name(run_id, "write", 2))
    (co / "draft.txt").write_text("half\n")
    monkeypatch.setattr(work, "SALVAGE", {**work.SALVAGE, "GIT_AUTHOR_NAME": ""})  # the save itself fails
    out = work.abort_run(root, run_id, "over")
    assert out["ok"] and out["removed"] == [] and plain.is_dir() and (co / "draft.txt").is_file()
    assert sorted(n["checkout"].rsplit("/", 1)[1] for n in out["not_removed"]) == sorted([plain.name, co.name])
    assert state.load(root, run_dir / "state.json", "run-state")["status"] == "aborted"
