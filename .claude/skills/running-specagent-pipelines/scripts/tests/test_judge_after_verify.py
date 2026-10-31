"""judge_after_verify.sh (spec B1; the judge comes once, after every task is verified): it waits until line 1 of each
record file named is `STATUS: done`, adds a detached worktree at the checkout's HEAD, launches the one agent of an
agents config there once, and then runs watch_agents.py on that config. A stub `claude` on PATH logs its working
folder and arguments as one JSON list per call.

  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests/test_judge_after_verify.py
"""

import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "judge_after_verify.sh"
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
STUB = """#!{python} -I
import json, os, pathlib, sys
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as f:
    f.write(json.dumps([os.getcwd(), *sys.argv[1:]]) + "\\n")
if sys.argv[1:] == ["agents", "--json", "--all"]:
    print("[]")
    sys.exit(0)
sys.exit(int(os.environ.get("STUB_EXIT", "0")))
"""
PROMPT = (
    "Read and follow the assignment in {run}/_judge-assignment.md. Start now. Work in English only (thinking, replies,"
    " tool descriptions, files)."
)


def git(repo: pathlib.Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=GIT_ENV, check=True)
    return out.stdout.strip()


def setup(tmp_path: pathlib.Path) -> tuple[dict, pathlib.Path, pathlib.Path, pathlib.Path]:
    """A checkout with one commit, a run folder whose record files are done, a one-agent config and the stub."""
    checkout, run, bin_dir = tmp_path / "checkout", tmp_path / "run", tmp_path / "bin"
    for d in (checkout, run, bin_dir):
        d.mkdir()
    git(checkout, "init", "-q")
    (checkout / "a.txt").write_text("a\n", encoding="utf-8")
    git(checkout, "add", "a.txt")
    git(checkout, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "one")
    for name in ("verify.md", "build-log-a.md", "judge.md"):
        (run / name).write_text("STATUS: done\n", encoding="utf-8")
    (run / "_judge-settings.json").write_text('{"permissions": {}}\n', encoding="utf-8")
    agent = {
        "cwd": str(tmp_path / "judge-wt"),
        "add_dirs": [str(run), str(tmp_path / "docs")],
        "settings": "_judge-settings.json",
        "status": "judge.md",
        "final": "STATUS: done",
    }
    config = run / "_agents-judge.json"
    config.write_text(
        json.dumps(
            {"run_dir": str(run), "common": ["--model", "opus", "--effort", "max"], "agents": {"demo/judge": agent}}
        ),
        encoding="utf-8",
    )
    claude = bin_dir / "claude"
    claude.write_text(STUB.replace("{python}", sys.executable), encoding="utf-8")
    claude.chmod(0o755)
    env = {
        **GIT_ENV,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "STUB_LOG": str(tmp_path / "calls.log"),
        "JUDGE_POLL": "1",
        "JUDGE_DELAY": "0",
    }
    return env, run, checkout, config


def launch(env: dict, *args: object, timeout: float = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *map(str, args)], capture_output=True, text=True, timeout=timeout, env=env, check=False
    )


def calls(tmp_path: pathlib.Path) -> list[list[str]]:
    log = tmp_path / "calls.log"
    return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []


def test_when_every_record_is_done_it_launches_the_judge_once_in_a_new_worktree_and_watches_it(tmp_path):
    env, run, checkout, config = setup(tmp_path)
    r = launch(env, config, checkout, "verify.md", "build-log-a.md")
    assert r.returncode == 0, r.stdout + r.stderr
    head, wt = git(checkout, "rev-parse", "HEAD"), tmp_path / "judge-wt"
    assert git(wt, "rev-parse", "HEAD") == head
    assert calls(tmp_path) == [
        [
            str(wt),
            "--name",
            "demo/judge",
            "--add-dir",
            str(run),
            str(tmp_path / "docs"),
            "--model",
            "opus",
            "--effort",
            "max",
            "--settings",
            '{"permissions": {}}',
            "--bg",
            PROMPT.format(run=run),
        ],
        [calls(tmp_path)[1][0], "agents", "--json", "--all"],
    ]
    log = (run / "_watch.log").read_text(encoding="utf-8").splitlines()
    assert re.fullmatch(r"\d\d:\d\d main: all 2 STATUS lines done; judge starts in 0 s", log[0])
    launched = rf"\d\d:\d\d main: demo/judge launched at {head} in {re.escape(str(wt))} \(exit 0\)"
    assert [x for x in log if re.fullmatch(launched, x)] != []
    assert "every STATUS line is final" in r.stdout and "every STATUS line is final" in log[-1]
    assert (run / "scratch" / "judge").is_dir()


def test_it_waits_while_a_record_file_is_not_done(tmp_path):
    env, run, checkout, config = setup(tmp_path)
    (run / "verify.md").write_text("STATUS: verifying Task 9\n", encoding="utf-8")
    with pytest.raises(subprocess.TimeoutExpired):
        launch(env, config, checkout, "verify.md", "build-log-a.md", timeout=4)
    assert (calls(tmp_path), (tmp_path / "judge-wt").exists(), (run / "scratch").exists()) == ([], False, False)


def test_a_failed_launch_exits_with_its_code_and_starts_no_watcher(tmp_path):
    env, run, checkout, config = setup(tmp_path)
    r = launch({**env, "STUB_EXIT": "3"}, config, checkout, "verify.md")
    assert r.returncode == 3
    assert [c[1] for c in calls(tmp_path)] == ["--name"]
    assert (run / "_watch.log").read_text(encoding="utf-8").rstrip().endswith("(exit 3)")


def test_too_few_arguments_or_a_config_without_exactly_one_agent_exits_2(tmp_path):
    env, _run, checkout, config = setup(tmp_path)
    r = launch(env, config, checkout)
    usage = "usage: judge_after_verify.sh <agents-judge.json> <checkout> <record-file>...\n"
    assert (r.returncode, r.stdout, r.stderr) == (2, "", usage)
    data = json.loads(config.read_text(encoding="utf-8"))
    data["agents"]["demo/second"] = data["agents"]["demo/judge"]
    config.write_text(json.dumps(data), encoding="utf-8")
    r = launch(env, config, checkout, "verify.md")
    assert r.returncode == 2 and "must name exactly one agent" in r.stderr
    assert (calls(tmp_path), (tmp_path / "judge-wt").exists()) == ([], False)
