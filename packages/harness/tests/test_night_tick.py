"""ops/night-tick.sh (docs/decisions/0022-a-prompt-loop-is-judged-by-code.md): a deterministic check before any model
session, one tick per fire, and one output file per fire whose cost a later tick counts. Run with stand-ins for `uv`
and `claude` on PATH, never the real ones, in a copy of the script inside the test's own checkout."""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from harness import loops, pause, state

REPO = next(
    p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file() and (p / "schemas").is_dir()
)
BRIEF = "# Project brief — demo\n\n## Goal of this run\nNotes.\n\n## Constraints\n- Budget: 10 minutes per stage\n"
MESSAGE = "Read `.claude/loop.md` and do exactly what it says in this turn."
UV = """#!{python}
import os, sys
args = sys.argv[1:]
assert args[:2] == ["run", "harness"], args  # the script runs `uv run harness ...` and nothing else through uv
os.execv({python!r}, [{python!r}, "-m", "harness.cli", *args[2:]])
"""
CLAUDE = """#!{python}
import json, os, sys
args = sys.argv[1:]
with open(os.environ["STANDIN_CALLS"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps(args) + "\\n")
if args[:1] == ["agents"]:
    print(open(os.environ["STANDIN_ROWS"], encoding="utf-8").read())
elif "-p" in args:
    print(json.dumps({{"total_cost_usd": 0.75, "result": "done"}}))
    sys.exit(int(os.environ.get("STANDIN_EXIT", "0")))
"""
REFRESH = """import json, os, sys
with open(os.environ["STANDIN_CALLS"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps(["obsidian-ingest", *sys.argv[1:]]) + "\\n")
renew = os.environ.get("STANDIN_RENEW", "").split()  # the files a real renewal rewrites
for rel in renew:
    with open(rel, "a", encoding="utf-8") as fh:
        fh.write("renewed\\n")
print("renewed the due sources" if renew else "nothing to renew")
sys.exit(int(os.environ.get("STANDIN_REFRESH_EXIT", "0")))
"""
RENEWED = ("wiki/log.md", "wiki/hot.md", "wiki/meta/ledgers/source-ledger.json")  # what `--refresh` rewrites
GIT = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}  # the owner's git settings stay out of the test


@pytest.fixture()
def night(tmp_path, small_config, monkeypatch):
    """The test's checkout with the night script and the poll loop, stand-ins on PATH, and its runs root beside it."""
    monkeypatch.setattr(state, "claude_version", lambda: "test")
    monkeypatch.delenv("HARNESS_ROLE", raising=False)
    root = small_config(tmp_path / "repo")
    (root / "ops").mkdir()
    shutil.copy(REPO / "ops" / "night-tick.sh", root / "ops" / "night-tick.sh")
    (root / "docs" / "loops").mkdir()
    shutil.copy(REPO / "docs" / "loops" / "poll.yaml", root / "docs" / "loops" / "poll.yaml")
    (root / ".claude").mkdir(exist_ok=True)
    (root / ".claude" / "loop.md").write_text("Run `uv run harness loop tick --name poll`.\n", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, text in (("uv", UV), ("claude", CLAUDE)):
        (bin_dir / name).write_text(text.format(python=sys.executable), encoding="utf-8")
        (bin_dir / name).chmod(0o755)
    calls, rows = tmp_path / "calls.jsonl", tmp_path / "rows.json"
    rows.write_text("[]", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("HARNESS_")}
    env.update(PATH=f"{bin_dir}{os.pathsep}{env['PATH']}", CLAUDE_PROJECT_DIR=str(root), STANDIN_CALLS=str(calls),
               STANDIN_ROWS=str(rows))  # fmt: skip
    return root, env, calls, rows


def fire(root: Path, env: dict, loop: str = "poll") -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(root / "ops" / "night-tick.sh"), loop], env=env, capture_output=True,
                          text=True, timeout=120, check=False)  # fmt: skip


def stood_in(calls: Path) -> list[list[str]]:
    lines = calls.read_text(encoding="utf-8").splitlines() if calls.is_file() else []
    return [json.loads(line) for line in lines]


def sessions(calls: Path) -> list[list[str]]:
    return [c for c in stood_in(calls) if "-p" in c]


def log_text(root: Path) -> str:
    today = dt.datetime.now(dt.UTC).astimezone().date()  # the script names its log by the local date (`date +%F`)
    return (state.runs_root(root) / "_audit" / f"night-tick-{today:%Y-%m-%d}.jsonl").read_text(encoding="utf-8")


def log_lines(root: Path) -> list[dict]:
    return [json.loads(line) for line in log_text(root).splitlines() if line.startswith("{")]


def a_run(root: Path, unit: dict) -> None:
    brief = root.parent / "brief.md"
    brief.write_text(BRIEF, encoding="utf-8")
    run_dir = state.runs_root(root) / state.create_run(root, "demo", brief, [])["run_id"]
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"]["read"].update(unit)
    state.save(root, run_dir / "state.json", st, "run-state")


LAUNCHED = {"status": "launched", "attempts": 1, "session_ids": ["s1"], "job_ids": ["j1"]}


def test_a_fire_with_no_active_run_starts_no_session_and_ticks_nothing(night):
    """7d: nothing to do, no model session; the check is no tick."""
    root, env, calls, _ = night
    done = fire(root, env)
    assert done.returncode == 0, done.stderr
    assert sessions(calls) == [] and log_lines(root)[-1]["why"] == "success"
    assert not (state.runs_root(root) / "_loops" / "poll" / "state.json").exists()


def test_a_fire_whose_runs_all_work_starts_no_session(night):
    root, env, calls, rows = night
    a_run(root, {**LAUNCHED, "started_at": state.now()})
    rows.write_text(
        json.dumps([{"id": "j1", "sessionId": "s1", "state": "working", "status": "busy"}]), encoding="utf-8"
    )
    assert fire(root, env).returncode == 0
    assert sessions(calls) == [] and log_lines(root)[-1]["why"] == "nothing for the manager"


def test_a_paused_fire_starts_no_session(night):
    """Item 8: ops/night-tick.sh honours the pause switch."""
    root, env, calls, _ = night
    a_run(root, {**LAUNCHED, "started_at": state.now()})  # its session is gone: there would be a resume
    assert pause.set_flag(root, "the human is away")["ok"]
    assert fire(root, env).returncode == 0
    assert sessions(calls) == [] and log_lines(root)[-1]["why"] == "paused"


def test_a_fire_with_work_for_the_manager_starts_one_session_that_ticks_once(night):
    """7c: the poll loop's session is told its prompt file, which ticks by itself, not the loop-tick skill; its cost
    lands in one file per fire, which a later tick counts."""
    root, env, calls, _ = night
    a_run(root, {**LAUNCHED, "started_at": state.now()})  # its session is gone: poll prints `resume`
    done = fire(root, env)
    assert done.returncode == 0, done.stderr
    started = sessions(calls)
    assert len(started) == 1 and started[0][-1] == MESSAGE and "/loop-tick poll" not in started[0]
    outputs = sorted((state.runs_root(root) / "_audit" / "night-tick").glob("poll-*.json"))
    assert len(outputs) == 1 and json.loads(outputs[0].read_text(encoding="utf-8"))["total_cost_usd"] == 0.75
    assert loops.night_spend(root, "poll", None) == 0.75
    assert not (state.runs_root(root) / "_loops" / "poll" / "state.json").exists()  # the session ticks, not the check


def test_a_night_session_that_fails_keeps_its_output_and_its_exit_code(night):
    """The fire ends with the session's exit code, and the session's output is kept as one file all the same, so a
    later tick counts what a failed session cost; no temporary file stays behind."""
    root, env, calls, _ = night
    a_run(root, {**LAUNCHED, "started_at": state.now()})
    done = fire(root, {**env, "STANDIN_EXIT": "3"})
    assert done.returncode == 3 and len(sessions(calls)) == 1
    night_dir = state.runs_root(root) / "_audit" / "night-tick"
    assert [p.name.startswith("poll-") for p in night_dir.iterdir()] == [True]
    assert loops.night_spend(root, "poll", None) == 0.75


def test_the_wiki_ingest_fire_renews_the_wikis_sources_first_and_goes_on_when_that_fails(night):
    """ops/obsidian-ingest.py --refresh runs before the loop's check, with the pause switch set; a failure is logged,
    never fatal."""
    root, env, calls, _ = night
    (root / "ops" / "obsidian-ingest.py").write_text(REFRESH, encoding="utf-8")
    assert pause.set_flag(root, "the human is away")["ok"]
    done = fire(root, {**env, "STANDIN_REFRESH_EXIT": "2"}, "wiki-ingest")
    assert done.returncode == 0, done.stderr
    assert stood_in(calls) == [["obsidian-ingest", "--refresh"]]  # no session, no other call
    assert "nothing to renew" in log_text(root) and "--refresh failed (exit 2)" in log_text(root)


def test_a_fire_of_another_loop_renews_nothing_and_a_checkout_without_the_driver_skips_it(night):
    root, env, calls, _ = night
    (root / "ops" / "obsidian-ingest.py").write_text(REFRESH, encoding="utf-8")
    assert fire(root, env).returncode == 0  # the poll loop
    assert stood_in(calls) == []
    (root / "ops" / "obsidian-ingest.py").unlink()
    assert fire(root, env, "wiki-ingest").returncode == 0
    assert stood_in(calls) == []


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(root), *args], env={**os.environ, **GIT}, capture_output=True, text=True,
                          check=True)  # fmt: skip
    return done.stdout.strip()


@pytest.fixture()
def wiki_night(night):
    """`night` with the `wiki-ingest` loop, the `--refresh` stand-in in place and the pause switch set, so that no fire
    starts a session: (root, env with git's settings, calls)."""
    root, env, calls, _ = night
    shutil.copy(REPO / "docs" / "loops" / "wiki-ingest.yaml", root / "docs" / "loops" / "wiki-ingest.yaml")
    (root / "ops" / "obsidian-ingest.py").write_text(REFRESH, encoding="utf-8")
    assert pause.set_flag(root, "the human is away")["ok"]
    return root, {**env, **GIT}, calls


@pytest.fixture()
def renewing(wiki_night):
    """`wiki_night` as a git checkout on `main` with one commit that holds the wiki files a renewal rewrites."""
    root, env, calls = wiki_night
    for rel in RENEWED:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("before\n", encoding="utf-8")
    for args in (("init", "-q", "-b", "main"), ("config", "user.name", "night"),
                 ("config", "user.email", "night@example.test"), ("add", "-A"), ("commit", "-q", "-m", "baseline")):  # fmt: skip
        git(root, *args)
    return root, env, calls


def test_the_renewal_is_committed_on_main_with_its_paths_only(renewing):
    """R7 (specs/003-pipeline-economy): the fire commits what `--refresh` renewed, on `main`, as one commit of those
    paths; a file staged for something else stays staged and out of it, so no dirty checkout blocks a merge that
    touches `wiki/log.md`."""
    root, env, _ = renewing
    base = git(root, "rev-parse", "HEAD")
    (root / "staged.txt").write_text("for another commit\n", encoding="utf-8")
    git(root, "add", "staged.txt")
    done = fire(root, {**env, "STANDIN_RENEW": " ".join(RENEWED)}, "wiki-ingest")
    assert done.returncode == 0, done.stderr
    assert len(git(root, "rev-list", f"{base}..HEAD").split()) == 1
    assert git(root, "log", "-1", "--format=%s") == "chore(wiki): renew the due sources (night tick)"
    assert sorted(git(root, "show", "--name-only", "--format=", "HEAD").split()) == sorted(RENEWED)
    assert git(root, "diff", "--cached", "--name-only") == "staged.txt"
    assert git(root, "status", "--porcelain", "--", "wiki") == ""  # nothing of the renewal is left dirty
    assert "renewal not committed" not in log_text(root)


def test_the_renewal_stays_in_the_checkout_on_another_branch_and_the_log_says_why(renewing):
    root, env, _ = renewing
    git(root, "switch", "-q", "-c", "feature")
    base = git(root, "rev-parse", "HEAD")
    done = fire(root, {**env, "STANDIN_RENEW": " ".join(RENEWED)}, "wiki-ingest")
    assert done.returncode == 0, done.stderr
    assert git(root, "rev-parse", "HEAD") == base
    assert sorted(git(root, "diff", "--name-only").split()) == sorted(RENEWED)
    assert "renewal not committed: on feature, not main" in log_text(root)


def test_a_refused_renewal_commit_is_logged_and_the_fire_goes_on(renewing):
    """A hook refuses the commit: the fire ends 0, the log has the reason, and the loop's own check ran after it."""
    root, env, calls = renewing
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho 'no commits today' >&2\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    done = fire(root, {**env, "STANDIN_RENEW": " ".join(RENEWED)}, "wiki-ingest")
    assert done.returncode == 0, done.stderr
    text = log_text(root)
    assert "renewal not committed: git commit failed: no commits today" in text
    assert text.index("renewal not committed") < text.index("paused")  # `harness loop due` ran and said why no session
    assert stood_in(calls) == [["obsidian-ingest", "--refresh"]]


def test_the_renewal_commit_waits_for_a_refresh_that_renewed_something_and_exited_0(renewing):
    """No commit while `--refresh` renews nothing or fails; the first fire after that renewed something commits."""
    root, env, _ = renewing
    base = git(root, "rev-parse", "HEAD")
    renew = " ".join(RENEWED)
    assert fire(root, env, "wiki-ingest").returncode == 0  # nothing to renew: the files stay as committed
    assert fire(root, {**env, "STANDIN_RENEW": renew, "STANDIN_REFRESH_EXIT": "2"}, "wiki-ingest").returncode == 0
    assert git(root, "rev-parse", "HEAD") == base
    assert "renewal not committed" not in log_text(root) and "--refresh failed (exit 2)" in log_text(root)
    assert fire(root, {**env, "STANDIN_RENEW": renew}, "wiki-ingest").returncode == 0
    assert len(git(root, "rev-list", f"{base}..HEAD").split()) == 1


def test_the_renewal_commit_in_a_checkout_that_is_no_git_repository_is_logged_and_the_fire_goes_on(wiki_night):
    """The night tests' own checkouts are no git repository: a renewal there cannot end the fire."""
    root, env, _ = wiki_night
    done = fire(root, {**env, "GIT_CEILING_DIRECTORIES": str(root.parent)}, "wiki-ingest")
    assert done.returncode == 0, done.stderr
    text = log_text(root)
    assert "renewal not committed: git status failed" in text
    assert text.index("renewal not committed") < text.index("paused")
