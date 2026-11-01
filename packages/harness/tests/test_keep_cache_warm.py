"""The keep-cache-warm hook of a role's settings (owner, 2026-11-01): a foreground call past 210 s is refused, and a
turn end of a session whose record is not final continues it with a keep-alive, up to the break-even."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "keep-cache-warm.py"


def hook(args, data, env=None):
    return subprocess.run(
        [sys.executable, "-I", str(HOOK), *args],
        input=json.dumps(data),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env=env,
    )


def bash(command, **fields):
    return {"tool_name": "Bash", "tool_input": {"command": command, **fields}}


@pytest.mark.parametrize(
    "data",
    [
        bash("uv run pytest -q", timeout=600000),
        bash("timeout -k 10 3500 sh scratch/waiter.sh"),
        bash("sleep 600 && cat verify.md"),
        bash("timeout 10m uv run pytest -q"),
        bash("for i in $(seq 1 16); do python3 -I _wait_for_log.py verify.md; done"),
    ],
)
def test_a_foreground_call_that_may_hold_the_turn_past_210_s_is_refused(data):
    r = hook(["pretool"], data)
    assert r.returncode == 2 and "210 s" in r.stderr and "run_in_background" in r.stderr


@pytest.mark.parametrize(
    "data",
    [
        bash("uv run pytest -q", timeout=200000),
        bash("timeout 200 uv run pytest -q"),
        bash("sleep 30"),
        bash("python3 -I _wait_for_log.py verify.md"),
        bash("for f in a b; do cat $f; done"),
        bash("timeout -k 10 3500 sh scratch/waiter.sh", run_in_background=True),
        {"tool_name": "Read", "tool_input": {"file_path": "x"}},
    ],
)
def test_a_short_call_a_background_call_or_another_tool_passes(data):
    r = hook(["pretool"], data)
    assert (r.returncode, r.stderr) == (0, "")


def test_a_turn_end_of_a_record_not_final_continues_the_session_with_a_keep_alive(tmp_path):
    record = tmp_path / "verify.md"
    record.write_text("STATUS: verifying Task 3\n", encoding="utf-8")
    env = {"TMPDIR": str(tmp_path), "PATH": "/usr/bin:/bin"}
    r = hook(["stop", str(record), "STATUS: done", "--wait", "0"], {"session_id": "s1"}, env)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["decision"] == "block" and out["reason"].startswith("Keep-alive for the prompt cache")


@pytest.mark.parametrize("line", ["STATUS: done", "STATUS: done after Task 4"])
def test_a_final_record_lets_the_turn_end(tmp_path, line):
    record = tmp_path / "verify.md"
    record.write_text(f"{line}\n", encoding="utf-8")
    env = {"TMPDIR": str(tmp_path), "PATH": "/usr/bin:/bin"}
    r = hook(["stop", str(record), "STATUS: done", "--wait", "0"], {"session_id": "s1"}, env)
    assert (r.returncode, r.stdout) == (0, "")


def test_the_keep_alive_stops_at_the_break_even_counted_from_the_first_turn_end(tmp_path):
    record = tmp_path / "verify.md"
    record.write_text("STATUS: waiting\n", encoding="utf-8")
    env = {"TMPDIR": str(tmp_path), "PATH": "/usr/bin:/bin"}
    args = ["stop", str(record), "STATUS: done", "--wait", "0", "--max-minutes", "60"]
    assert json.loads(hook(args, {"session_id": "s2"}, env).stdout)["decision"] == "block"
    state = tmp_path / "specagent-keep-warm-s2.json"
    state.write_text(json.dumps({"start": 0}), encoding="utf-8")  # the stretch began long ago
    r = hook(args, {"session_id": "s2", "stop_hook_active": True}, env)
    assert (r.returncode, r.stdout) == (0, "") and not state.exists()
    fresh = hook(args, {"session_id": "s2", "stop_hook_active": False}, env)  # a new stretch starts again
    assert json.loads(fresh.stdout)["decision"] == "block"
