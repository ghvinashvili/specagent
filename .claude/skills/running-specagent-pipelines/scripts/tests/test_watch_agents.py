"""Tests of watch_agents.py (version 2): a stub `claude` on PATH answers `agents --json --all` from canned rounds
(and may write files during a round, to change the state after the watcher started) and logs every other invocation;
transcripts are synthetic files under a temporary HOME.

  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests
"""

import ast
import datetime
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import time

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "watch_agents.py"
SID = "11111111-2222-3333-4444-555555555555"
SID2 = "66666666-7777-8888-9999-000000000000"
SID3 = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
ORDER = "Orders from the owner: your context has passed the size limit (200k tokens per call)."
STUB = """#!{python} -I
import json, os, pathlib, sys, time
state = pathlib.Path(os.environ["STUB_DIR"])


def apply(changes):
    for path, text in changes.items():
        if text is None:
            pathlib.Path(path).unlink(missing_ok=True)
        else:
            pathlib.Path(path).write_text(text)


def count(name):
    counter = state / name
    n = int(counter.read_text()) if counter.exists() else 0
    counter.write_text(str(n + 1))
    return n


if sys.argv[1:] == ["agents", "--json", "--all"]:
    rounds = json.loads((state / "rounds.json").read_text())
    answer = rounds[min(count("agents-calls"), len(rounds) - 1)]
    time.sleep(answer.get("sleep", 0))
    apply(answer.get("write", {}))
    print(json.dumps(answer["rows"]))
    sys.exit(0)
with open(state / "calls.jsonl", "a") as f:
    f.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd()}) + "\\n")
if sys.argv[1:2] == ["stop"]:
    if (state / "on-stop.json").exists():
        apply(json.loads((state / "on-stop.json").read_text()))
    print("s 12345678      show recent output")
    sys.exit(0)
out = state / "launch-out.json"
if out.exists():
    texts = json.loads(out.read_text())
    print(texts[min(count("launch-calls"), len(texts) - 1)])
else:
    print("s 12345678      show recent output")
"""


def iso(t: float) -> str:
    stamp = datetime.datetime.fromtimestamp(t, datetime.UTC).isoformat(timespec="milliseconds")
    return stamp.replace("+00:00", "Z")


def row(
    name: str = "t/builder",
    sid: str = SID,
    state: str = "working",
    status: str | None = "busy",
    pid: int | None = 4242,
    waiting: str | None = None,
    age: int = 3600,
    cwd: str | None = None,
) -> dict:
    """One `claude agents --json --all` row in the live shape (a stopped session has no status and no pid)."""
    r = {
        "id": sid[:8],
        "name": name,
        "sessionId": sid,
        "state": state,
        "kind": "bg",
        "startedAt": int((time.time() - age) * 1000),
    }
    r.update({k: v for k, v in (("status", status), ("pid", pid), ("waitingFor", waiting), ("cwd", cwd)) if v})
    return r


class Pipeline:
    """A run folder, a checkout, a HOME with transcripts, and the stub `claude` on PATH."""

    def __init__(self, root: pathlib.Path):
        self.root, self.run, self.checkout = root, root / "run", root / "checkout"
        self.projects = root / "home" / ".claude" / "projects" / "-checkout"
        self.stub = root / "stub"
        for d in (self.run, self.checkout, self.projects, self.stub, root / "bin"):
            d.mkdir(parents=True)
        claude = root / "bin" / "claude"
        claude.write_text(STUB.replace("{python}", sys.executable), encoding="utf-8")
        claude.chmod(0o755)
        for role in ("builder", "verifier", "critic"):
            self.write(f"_{role}-settings.json", json.dumps({"permissions": {"allow": ["Read"], "role": role}}) + "\n")
            self.write(f"_{role}-assignment.md", f"# the {role}'s brief\n")
        self.write("build-log.md", "STATUS: building Task 3\n")
        self.write("verify.md", "STATUS: verifying Task 2\n")
        self.write("critique.md", "STATUS: reviewing Task 4\n")
        self.config = {
            "run_dir": str(self.run),
            "common": ["--model", "opus", "--effort", "max"],
            "blocked_files": ["build-log.md"],
            "interval": 0,
            # the hand-over thresholds these tests were written for; the defaults moved to 260000 and 250000 (2026-11-01)
            "cap": 200_000,
            "handoff_at": 150_000,
            "agents": {"t/builder": self.agent("builder", "build-log.md")},
        }
        self.rounds([row()])

    def agent(self, role: str, status: str) -> dict:
        return {
            "cwd": str(self.checkout),
            "add_dirs": [str(self.run), "/elsewhere"],
            "settings": f"_{role}-settings.json",
            "status": status,
            "final": "STATUS: done",
        }

    def write(self, name: str, text: str, mtime: float | None = None) -> pathlib.Path:
        path = self.run / name
        path.write_text(text, encoding="utf-8")
        if mtime is not None:
            os.utime(path, (mtime, mtime))
        return path

    def transcript(self, sid=SID, start=None, end=None, calls=1, context=1_000, output=10, prompts=(), first=0):
        """A transcript in the live shape: one line per content block, the blocks of a call sharing its message id."""
        now = time.time()
        start = now - 3600 if start is None else start
        end = now - 60 if end is None else end
        lines = [
            {"type": "custom-title", "customTitle": "t", "sessionId": sid},
            {
                "type": "user",
                "timestamp": iso(start),
                "sessionId": sid,
                "message": {"role": "user", "content": "You are a fresh session; read your note."},
            },
        ]
        for i in range(calls):
            for block in ("thinking", "tool_use"):
                lines.append(
                    {
                        "type": "assistant",
                        "timestamp": iso(start + 1 + i),
                        "sessionId": sid,
                        "requestId": f"req_{first + i}",
                        "message": {
                            "id": f"msg_{first + i}",
                            "role": "assistant",
                            "content": [{"type": block}],
                            "usage": {
                                "input_tokens": 3,
                                "cache_creation_input_tokens": 7,
                                "cache_read_input_tokens": context - 10,
                                "output_tokens": output,
                            },
                        },
                    }
                )
        for t, text in prompts:
            lines.append(
                {"type": "user", "timestamp": iso(t), "sessionId": sid, "message": {"role": "user", "content": text}}
            )
        lines.append({"type": "system", "subtype": "turn_duration", "timestamp": iso(end), "sessionId": sid})
        (self.projects / f"{sid}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines), encoding="utf-8")

    def rounds(self, *answers):
        """The stub's answers, one per round (the last repeats): a list of rows, or {"rows": [...], "write": {...}}."""
        data = [a if isinstance(a, dict) else {"rows": a} for a in answers]
        for answer in data:  # a row without a cwd runs in the checkout, the agents' cwd (J5)
            for r in answer.get("rows", []):
                r.setdefault("cwd", str(self.checkout))
        (self.stub / "rounds.json").write_text(json.dumps(data), encoding="utf-8")

    def watch(self, *args: str, rounds: int = 1) -> subprocess.CompletedProcess:
        config = self.run / "_agents-v2.json"
        config.write_text(json.dumps(self.config, indent=2), encoding="utf-8")
        env = {
            **os.environ,
            "PATH": f"{self.root / 'bin'}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(self.root / "home"),
            "STUB_DIR": str(self.stub),
        }
        tail = [] if "--check" in args or "--order" in args else [str(rounds)]
        return subprocess.run(
            [sys.executable, "-I", str(SCRIPT), *args, str(config), *tail],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            cwd=self.root,
            check=False,
        )

    def calls(self) -> list[dict]:
        path = self.stub / "calls.jsonl"
        return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []

    def stops(self) -> list[str]:
        return [c["argv"][1] for c in self.calls() if c["argv"][:1] == ["stop"]]

    def launches(self) -> list[dict]:
        return [c for c in self.calls() if c["argv"][:1] != ["stop"]]


@pytest.fixture
def p(tmp_path) -> Pipeline:
    return Pipeline(tmp_path)


def note(p: Pipeline, task: int = 3, mtime: float | None = None) -> str:
    line = f"HANDOFF builder after Task {task} — 2026-10-26 06:00"
    p.write("handoff-builder.md", line + "\nState: Task 3 done.\n", mtime=time.time() - 120 if mtime is None else mtime)
    return line


def flags(p: Pipeline, settings: str = "_builder-settings.json") -> list[str]:
    return [
        "--name",
        "t/builder",
        "--add-dir",
        str(p.run),
        "/elsewhere",
        "--model",
        "opus",
        "--effort",
        "max",
        "--settings",
        str(p.run / settings),
    ]


ORDER_LINE = re.compile(r"^Order ([0-9a-f]{8}): append the line `ACK \1` to (\S+) before anything else\.$")
RELOAD = "Orders from the main session:"
UNIT_END = "Orders from the owner: your context has passed the hand-over mark (150,000 tokens) and your unit of work"
MID, MID2 = "c0ffee01", "c0ffee02"


def utc(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def seconds(stamp: str) -> float:
    return datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.UTC).timestamp()


def registry(p: Pipeline) -> dict:
    return json.loads((p.run / "_control" / "registry.json").read_text(encoding="utf-8"))


def order(msg_id: str = MID, kind: str = "manager", text: str = "Read critique.md again.", ago: int = 60) -> dict:
    """An open order as the registry keeps it, sent `ago` seconds before now."""
    return {
        "msg_id": msg_id,
        "kind": kind,
        "text": text,
        "sent_at": utc(time.time() - ago),
        "resends": 0,
        "acked_at": None,
        "closed": None,
    }


def seed_registry(p: Pipeline, **fields) -> None:
    """The registry an earlier watcher of this run left: t/builder on session SID, with `fields` changed."""
    entry = {
        "job_id": SID[:8],
        "session_id": SID,
        "session_ids": [SID],
        "launched_at": None,
        "unit": "STATUS: building Task 3",
        "unit_since": utc(time.time() - 600),
        "revivals": 0,
        "handoff_since": None,
        "orders": [],
    }
    data = {
        "version": 1,
        "run_dir": str(p.run),
        "written_at": utc(time.time() - 60),
        "watcher": {"pid": 1, "started_at": utc(time.time() - 900), "round": 3, "interval": 0},
        "roles": {"t/builder": {**entry, **fields}},
    }
    path = p.run / "_control" / "registry.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def launch_out(p: Pipeline, *texts: str) -> None:
    """What the stub prints for each launch, in order (the last repeats)."""
    (p.stub / "launch-out.json").write_text(json.dumps(texts), encoding="utf-8")


def order_line(p: Pipeline, msg_id: str) -> str:
    return f"Order {msg_id}: append the line `ACK {msg_id}` to {p.run / 'build-log.md'} before anything else."


def usage_report():
    """The skill's usage_report module, for its prices (Task 10 may change them; the tests follow)."""
    spec = importlib.util.spec_from_file_location("usage_report", SCRIPT.parent / "usage_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "override, expected",
    [
        ({}, None),
        (
            {"lang": "", "fresh": {"builder": "Custom fresh text for {run}/_builder-assignment.md."}},
            "Custom fresh text for {run}/_builder-assignment.md.",
        ),
    ],
)
def test_handoff_launches_a_fresh_session_with_the_flags_and_bg_last(p, override, expected):
    p.config.update(override)
    p.transcript()
    line = note(p)
    r = p.watch(rounds=2)
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"fresh t/builder after note: {line} | s 12345678" in r.stdout
    assert p.stops() == [SID[:8]]
    [launch] = p.launches()  # one launch over two rounds: the note is acted on once
    assert launch["cwd"] == str(p.checkout)
    assert launch["argv"][:-2] == flags(p)
    assert launch["argv"][-2] == "--bg"
    prompt = launch["argv"][-1]
    if expected is None:
        assert prompt.startswith("You are a fresh builder session; the previous one handed over")
        assert f"{p.run}/handoff-builder.md" in prompt
        assert prompt.endswith(
            "a script outside the Latin blocks costs about twice the tokens; see _common.md, Language."
        )
    else:
        assert prompt == expected.replace("{run}", str(p.run))


def test_note_from_before_start_is_taken_as_handled_and_a_foreign_note_launches_nothing(p):
    p.transcript(start=time.time() - 7200, end=time.time() - 3600)
    note(p, task=2, mtime=time.time() - 9000)  # older than the session: the fresh session after it is running
    p.rounds(
        [row()],
        {
            "rows": [row()],
            "write": {str(p.run / "handoff-builder.md"): "HANDOFF builder after Task 3 — 2026-10-26 06:00\n"},
        },
    )
    r = p.watch(rounds=3)
    assert r.returncode == 1, r.stdout + r.stderr
    assert p.calls() == []
    # the new note is written now, an hour after the session's last transcript line
    assert r.stdout.count("note not from t/builder: handoff-builder.md") == 1
    assert "Task 2" not in r.stdout


def test_cap_orders_a_hand_over_once_then_waits(p):
    p.transcript(context=250_000)
    r = p.watch(rounds=3)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "cap t/builder 250,000 tokens; ordered to hand over | s 12345678" in r.stdout
    assert p.stops() == [SID[:8]]
    [launch] = p.launches()
    assert launch["argv"][:2] == ["--resume", SID]
    assert launch["argv"][2:-2] == flags(p) and launch["argv"][-2] == "--bg"
    assert launch["argv"][-1].startswith(ORDER)
    assert f"{p.run}/_handoff-rule.md" in launch["argv"][-1]


def test_cap_without_a_note_starts_a_fresh_session_after_handoff_wait(p):
    p.config["handoff_wait"] = 0
    p.transcript(context=250_000)
    r = p.watch(rounds=2)
    assert "fresh t/builder without a note (timeout) | s 12345678" in r.stdout, r.stdout + r.stderr
    assert p.stops() == [SID[:8], SID[:8]]
    order, fresh = p.launches()
    assert order["argv"][:2] == ["--resume", SID]
    assert fresh["argv"][:-2] == flags(p)
    assert fresh["argv"][-1].startswith("You are a fresh builder session")


@pytest.mark.parametrize("ago, launched", [(60, False), (2000, True)])
def test_an_order_found_in_the_transcript_is_not_given_again(p, ago, launched):
    """A watcher that ran before this one gave the order: the wait counts from the order's timestamp."""
    p.transcript(context=250_000, prompts=[(time.time() - ago, ORDER + " Finish the step you are on.")])
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "ordered to hand over" not in r.stdout
    if launched:
        assert "fresh t/builder without a note (timeout)" in r.stdout
        [fresh] = p.launches()
        assert fresh["argv"][:-2] == flags(p)
    else:
        assert p.calls() == []


def test_nudge_limit(p):
    p.config["nudges"] = 2
    p.rounds([row(state="stopped", status=None, pid=None)])
    r = p.watch(rounds=5)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("continued t/builder 11111111 | s 12345678") == 2
    assert r.stdout.strip().endswith("t/builder was revived 2 times; check it")
    assert p.stops() == []
    launches = p.launches()
    assert len(launches) == 2
    assert all(
        c["argv"][:2] == ["--resume", SID] and c["argv"][-1].startswith("Your process was stopped") for c in launches
    )


@pytest.mark.parametrize(
    "wait, waiting, rounds, code, line, unblocked",
    [
        (3600, "permission prompt", 2, 1, "watcher stopped after its last round", False),
        (0, "permission prompt", 1, 1, "unblock t/builder | s 12345678", True),
        (0, "input", 1, 0, "t/builder is blocked (input)", False),
        (None, "permission prompt", 1, 0, "t/builder is blocked (permission prompt)", False),
    ],
)
def test_permission_prompt_after_permission_wait(p, wait, waiting, rounds, code, line, unblocked):
    p.config["permission_wait"] = wait
    p.rounds([row(state="blocked", status="waiting", waiting=waiting)])
    r = p.watch(rounds=rounds)
    assert r.returncode == code, r.stdout + r.stderr
    assert line in r.stdout
    if unblocked:
        assert p.stops() == [SID[:8]]
        [launch] = p.launches()
        assert launch["argv"][:2] == ["--resume", SID]
        assert launch["argv"][-1].startswith("Your last command waited more than 10 minutes")
    else:
        assert p.calls() == []


def test_a_waiting_session_is_left_alone(p):
    """Blocked and busy with no waitingFor: idle at its prompt with a waiter shell running."""
    p.config["permission_wait"] = 0
    p.rounds([row(state="blocked", status="busy")])
    r = p.watch(rounds=2)
    assert r.returncode == 1 and p.calls() == [], r.stdout + r.stderr


@pytest.mark.parametrize(
    "budget, agent_budget, code",
    [
        ({"calls": 2}, None, 3),
        ({"output_tokens": 250}, None, 3),
        ({"calls": 2}, {"calls": 5}, 1),
        ({}, None, 1),
    ],
)
def test_budget_event_and_exit_code_3(p, budget, agent_budget, code):
    p.config["budget"] = budget
    if agent_budget:
        p.config["agents"]["t/builder"]["budget"] = agent_budget
    p.transcript(calls=3, output=100)  # six lines, three calls: one call per message id
    r = p.watch(rounds=1)
    assert r.returncode == code, r.stdout + r.stderr
    assert ("budget t/builder calls=3 output=300 session=11111111" in r.stdout) == (code == 3)
    assert p.calls() == []  # never stopped for a budget


@pytest.mark.parametrize(
    "state, status, line",
    [
        ("working", "STATUS: blocked on V3 (needs the owner)", "build-log.md: STATUS: blocked on V3 (needs the owner)"),
        ("failed", "STATUS: building Task 3", "t/builder failed"),
        ("working", "STATUS: done", "every STATUS line is final"),
    ],
)
def test_a_blocked_status_or_a_failed_agent_exits(p, state, status, line):
    p.write("build-log.md", status + "\n")
    done = status == "STATUS: done"  # a finished session at its prompt is stopped by the watcher (owner, 2026-10-30)
    p.rounds([row(state="done" if done else state, status="idle" if done else "busy")])
    r = p.watch(rounds=3)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.strip().endswith(line)
    assert p.launches() == [] and p.stops() == ([SID[:8]] if done else [])


def test_milestone_switch(p):
    p.config["milestones"] = [7, 13]
    p.config["agents"]["t/verifier"] = p.agent("verifier", "verify.md")
    p.write("build-log.md", "STATUS: building Task 7\n")
    p.write("verify.md", "STATUS: verified through Task 6\n")
    rows = [row(), row(name="t/verifier", sid=SID2)]
    p.rounds(
        rows,
        {
            "rows": rows,
            "write": {
                str(p.run / "build-log.md"): "STATUS: milestone done after Task 7\n",
                str(p.run / "verify.md"): "STATUS: verified through Task 7\n",
            },
        },
    )
    r = p.watch(rounds=3)
    assert r.returncode == 1, r.stdout + r.stderr
    assert p.stops() == [SID[:8], SID2[:8]]
    builder, verifier = p.launches()
    assert builder["argv"][:-2] == flags(p)
    assert "Tasks 1–7 are built and committed" in builder["argv"][-1]
    assert "continue with Task 8" in builder["argv"][-1]
    assert verifier["argv"][:2] == ["--name", "t/verifier"]
    assert "Tasks 1–7 are verified" in verifier["argv"][-1] and "Rebuild" in verifier["argv"][-1]
    assert "fresh t/builder after milestone Task 7" in r.stdout
    assert "fresh t/verifier after milestone Task 7" in r.stdout


def test_milestone_lines_from_before_start_are_not_switched_again(p):
    p.config["milestones"] = [7]
    p.config["agents"]["t/verifier"] = p.agent("verifier", "verify.md")
    p.write("build-log.md", "STATUS: milestone done after Task 7\n")
    p.write("verify.md", "STATUS: verified through Task 9\n")
    p.rounds([row(), row(name="t/verifier", sid=SID2)])
    r = p.watch(rounds=2)
    assert r.returncode == 1 and p.calls() == [], r.stdout + r.stderr


@pytest.mark.parametrize(
    "name, text", [("_builder-settings.json", "changed after the watcher started\n"), ("_builder-assignment.md", None)]
)
def test_a_changed_control_file_exits_4_instead_of_launching(p, name, text):
    """A changed settings file and a removed brief still exit 4 (spec 8.1.4); a brief whose content changed is
    reloaded instead (test_a_changed_brief_is_reloaded_with_an_order_instead_of_exit_4)."""
    p.transcript()
    note(p)
    p.rounds({"rows": [row()], "write": {str(p.run / name): text}})
    r = p.watch(rounds=2)
    assert r.returncode == 4, r.stdout + r.stderr
    assert f"control file changed: {name}" in r.stdout
    assert p.calls() == []  # not even the stop


def test_a_control_file_changed_during_the_stop_exits_4_before_the_launch(p):
    """The settings file is passed as a path, so it is read when claude starts: the hashes are checked once more
    right before the launch, after the stop, and a file changed in between exits 4 with no launch."""
    p.transcript()
    note(p)
    (p.stub / "on-stop.json").write_text(
        json.dumps({str(p.run / "_builder-settings.json"): "changed during the stop\n"})
    )
    r = p.watch(rounds=2)
    assert r.returncode == 4, r.stdout + r.stderr
    assert "control file changed: _builder-settings.json" in r.stdout
    assert p.stops() == [SID[:8]] and p.launches() == []


def test_a_changed_config_is_reloaded_at_the_next_round_and_an_invalid_one_is_kept_out(p):
    """B9: round 1 runs on the config as written and rewrites it with a lower cap; round 2 reloads it, orders
    t/builder's hand-over and writes `{` into it; round 3 keeps round 2's config, so t/verifier, first seen in that
    round, is ordered under the lower cap. Neither change exits (A3, A6)."""
    p.config["cap"] = 300_000  # both 250k contexts are under it
    p.config["agents"]["t/verifier"] = p.agent("verifier", "verify.md")
    p.transcript(context=250_000)
    p.transcript(sid=SID2, context=250_000)
    config = str(p.run / "_agents-v2.json")
    p.rounds(
        {"rows": [row()], "write": {config: json.dumps({**p.config, "cap": 200_000})}},
        {"rows": [row()], "write": {config: "{"}},
        [row(), row(name="t/verifier", sid=SID2)],
    )
    r = p.watch(rounds=3)
    assert r.returncode == 1, r.stdout + r.stderr  # no exit 2, no exit 4; a crash returns 1 too, hence the next line
    assert "watcher stopped after its last round" in r.stdout
    assert r.stdout.count("config reloaded: _agents-v2.json") == 1
    assert r.stdout.count("config invalid, kept the previous one: ") == 1
    assert "control file changed" not in r.stdout
    assert "cap t/builder 250,000 tokens; ordered to hand over | s 12345678" in r.stdout
    assert "cap t/verifier 250,000 tokens; ordered to hand over | s 12345678" in r.stdout
    # round 2 orders t/builder on the reloaded 200k; round 3 orders t/verifier on round 2's 200k, not the start's 300k
    assert [c["argv"][:2] for c in p.launches()] == [["--resume", SID], ["--resume", SID2]]
    assert all(c["argv"][-1].startswith(ORDER) for c in p.launches())


@pytest.mark.parametrize(
    "change, message",
    [
        ({"fresh": []}, "fresh is not an object of strings"),
        ({"cap": "200k"}, "cap is not a non-negative number"),
        ({"interval": -1}, "interval is not a non-negative number"),
        ({"agents": {"t/builder": 1}}, "t/builder is not an object"),
        (
            {
                "agents": {
                    "t/builder": {
                        "cwd": "/x",
                        "add_dirs": [],
                        "settings": 5,
                        "status": "build-log.md",
                        "final": "STATUS: done",
                    }
                }
            },
            "t/builder: settings is not a string",
        ),
    ],
)
def test_a_changed_config_of_a_wrong_type_is_kept_out_and_the_watcher_goes_on(p, change, message):
    """R1: round 1 rewrites the config with JSON that the checks of __init__ refuse, a type or a negative number
    (before, each raised out of reload() or a later round: a `"200k"` cap was applied and met the context of a session
    with a process and a transcript, `time.sleep` refuses -1); round 2 keeps it out, round 3 runs on the start's."""
    p.transcript()
    config = str(p.run / "_agents-v2.json")
    p.rounds({"rows": [row()], "write": {config: json.dumps({**p.config, **change})}}, [row()])
    r = p.watch(rounds=3)
    assert r.returncode == 1, r.stdout + r.stderr  # a crash returns 1 too, hence the next lines
    assert "watcher stopped after its last round" in r.stdout
    assert r.stdout.count(f"config invalid, kept the previous one: {message}") == 1
    assert "config reloaded" not in r.stdout and "Traceback" not in r.stderr
    assert p.calls() == []


def test_check_prints_the_decisions_and_runs_nothing(p):
    p.config["agents"]["t/verifier"] = p.agent("verifier", "verify.md")
    p.config["agents"]["t/critic"] = p.agent("critic", "critique.md")
    p.config["budget"] = {"calls": 2}
    p.transcript(calls=1)
    p.transcript(sid=SID3, calls=3)
    line = note(p)
    p.rounds(
        [
            row(),
            row(name="t/verifier", sid=SID2, state="stopped", status=None, pid=None),
            row(name="t/critic", sid=SID3),
        ]
    )
    r = p.watch("--check")
    assert r.returncode == 0, r.stdout + r.stderr
    assert p.calls() == []
    assert (p.stub / "agents-calls").read_text() == "1"
    out = {x.split(": ", 1)[0]: x for x in r.stdout.splitlines() if x.startswith("t/")}
    assert f"fresh t/builder after note: {line}" in out["t/builder"]
    assert "would stop 11111111" in out["t/builder"] and "would launch" in out["t/builder"]
    assert "claude --name t/builder" in out["t/builder"] and "--bg" in out["t/builder"]
    assert f"cat {p.run}/_builder-settings.json" in out["t/builder"]
    assert "would nudge" in out["t/verifier"] and "--resume 66666666-7777" in out["t/verifier"]
    assert "would exit budget t/critic calls=3 output=30 session=aaaaaaaa" in out["t/critic"]
    assert r.stdout.strip().splitlines()[-1].startswith("would exit 3")


def test_extra_prompt_for_new_sessions_and_for_resumes_that_started_with_it(p):
    mark = "Extra voice is on for this whole session"
    p.write("_extra.md", f"# {mark}\n")
    p.config["extra_prompt"] = {"file": "_extra.md", "mark": mark}
    p.config["agents"]["t/verifier"] = p.agent("verifier", "verify.md")
    p.config["agents"]["t/critic"] = p.agent("critic", "critique.md")
    p.transcript()
    p.transcript(sid=SID2)
    p.transcript(sid=SID3, prompts=[(time.time() - 3000, f"<system-reminder>{mark}</system-reminder>")])
    note(p)
    stopped = {"state": "stopped", "status": None, "pid": None}
    p.rounds([row(), row(name="t/verifier", sid=SID2, **stopped), row(name="t/critic", sid=SID3, **stopped)])
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    extra = ["--append-system-prompt-file", str(p.run / "_extra.md")]
    by_name = {c["argv"][c["argv"].index("--name") + 1]: c["argv"] for c in p.launches()}
    assert by_name["t/builder"][-4:-2] == extra  # a new session gets it
    assert extra[0] not in by_name["t/verifier"]  # a resume of a session that started without it does not
    assert by_name["t/critic"][-4:-2] == extra  # a resume of a session that started with it keeps it


def test_a_lanes_own_extra_prompt_replaces_the_runs_and_the_others_keep_the_runs(p):
    """One frozen pack per lane in the system prompt (owner, 2026-11-01): an agent's own `extra_prompt` replaces the
    run's for that agent, a new session and a resume that started with its mark get it, an agent without one keeps the
    run's."""
    mark, own = "Extra voice is on for this whole session", "Your standing orders: the builder lane's pack"
    p.write("_extra.md", f"# {mark}\n")
    p.write("_pack-builder.md", f"# {own}\n")
    p.config["extra_prompt"] = {"file": "_extra.md", "mark": mark}
    p.config["agents"]["t/builder"]["extra_prompt"] = {"file": "_pack-builder.md", "mark": own}
    p.config["agents"]["t/verifier"] = p.agent("verifier", "verify.md")
    p.transcript()
    p.transcript(sid=SID2)
    note(p)
    stopped = {"state": "stopped", "status": None, "pid": None}
    p.rounds([row(), row(name="t/verifier", sid=SID2, **stopped)])
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    by_name = {c["argv"][c["argv"].index("--name") + 1]: c["argv"] for c in p.launches()}
    assert by_name["t/builder"][-4:-2] == ["--append-system-prompt-file", str(p.run / "_pack-builder.md")]
    assert str(p.run / "_extra.md") not in by_name["t/builder"]
    assert "--append-system-prompt-file" not in by_name["t/verifier"]  # its resume started without the run's mark


def test_a_resume_that_started_with_the_lanes_own_mark_keeps_its_own_pack(p):
    """The resume rule reads the lane's own mark, not the run's: a session whose transcript carries the builder pack's
    mark is resumed with that pack, and a dead one with only the run's mark is not resumed but started fresh with its
    lane's pack (2026-11-02: a resume never gets the pack)."""
    mark, own = "Extra voice is on for this whole session", "Your standing orders: the builder lane's pack"
    p.write("_extra.md", f"# {mark}\n")
    p.write("_pack-builder.md", f"# {own}\n")
    p.config["extra_prompt"] = {"file": "_extra.md", "mark": mark}
    p.config["agents"]["t/builder"]["extra_prompt"] = {"file": "_pack-builder.md", "mark": own}
    p.config["agents"]["t/verifier"] = p.agent("verifier", "verify.md")
    p.config["agents"]["t/verifier"]["extra_prompt"] = {"file": "_pack-builder.md", "mark": own}
    p.transcript(prompts=[(time.time() - 3000, f"<system-reminder>{own}</system-reminder>")])
    p.transcript(sid=SID2, prompts=[(time.time() - 3000, f"<system-reminder>{mark}</system-reminder>")])
    stopped = {"state": "stopped", "status": None, "pid": None}
    p.rounds([row(**stopped), row(name="t/verifier", sid=SID2, **stopped)])
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    by_name = {c["argv"][c["argv"].index("--name") + 1]: c["argv"] for c in p.launches()}
    assert by_name["t/builder"][-4:-2] == ["--append-system-prompt-file", str(p.run / "_pack-builder.md")]
    assert by_name["t/builder"][:2] == ["--resume", SID]
    assert "--resume" not in by_name["t/verifier"]
    assert by_name["t/verifier"][-4:-2] == ["--append-system-prompt-file", str(p.run / "_pack-builder.md")]


def test_a_lanes_pack_changed_during_the_run_exits_4_instead_of_launching(p):
    """A lane's pack is frozen for the run: like a settings file, a changed pack stops the launch with exit 4."""
    own = "Your standing orders: the builder lane's pack"
    p.write("_pack-builder.md", f"# {own}\n")
    p.config["agents"]["t/builder"]["extra_prompt"] = {"file": "_pack-builder.md", "mark": own}
    p.transcript()
    note(p)
    p.rounds({"rows": [row()], "write": {str(p.run / "_pack-builder.md"): "# a lesson added mid-run\n"}})
    r = p.watch(rounds=2)
    assert r.returncode == 4, r.stdout + r.stderr
    assert "control file changed: _pack-builder.md" in r.stdout
    assert p.calls() == []


@pytest.mark.parametrize(
    "change, message",
    [
        ({"pack": True}, "config error: pack"),
        (
            {
                "agents": {
                    "t/designer": {
                        "cwd": "/x",
                        "add_dirs": [],
                        "settings": "_builder-settings.json",
                        "status": "build-log.md",
                        "final": "STATUS: done",
                    }
                }
            },
            "config error: no fresh text for role designer",
        ),
        ({"cap": "200k"}, "config error: cap is not a non-negative number"),
        ({"extra_prompt": {"file": 5, "mark": "x"}}, "config error: extra_prompt needs file and mark, each a string"),
        (
            {
                "agents": {
                    "t/builder": {
                        "cwd": "/x",
                        "add_dirs": [],
                        "settings": "../_builder-settings.json",
                        "status": "build-log.md",
                        "final": "STATUS: done",
                    }
                }
            },
            "config error: t/builder: settings ../_builder-settings.json leaves run_dir",
        ),
        (
            {"extra_prompt": {"file": "/etc/passwd", "mark": "x"}},
            "config error: extra_prompt file /etc/passwd leaves run_dir",
        ),
        (
            {
                "agents": {
                    "t/builder": {
                        "cwd": "/x",
                        "add_dirs": [],
                        "settings": "_builder-settings.json",
                        "status": "build-log.md",
                        "final": "STATUS: done",
                        "extra_prompt": {"file": "_pack.md"},
                    }
                }
            },
            "config error: t/builder: extra_prompt is not an object with file and mark, each a string",
        ),
        (
            {
                "agents": {
                    "t/builder": {
                        "cwd": "/x",
                        "add_dirs": [],
                        "settings": "_builder-settings.json",
                        "status": "build-log.md",
                        "final": "STATUS: done",
                        "extra_prompt": {"file": "../_pack.md", "mark": "x"},
                    }
                }
            },
            "config error: t/builder: extra_prompt file ../_pack.md leaves run_dir",
        ),
    ],
)
def test_config_errors_exit_2_before_any_claude_command(p, change, message):
    p.config.update(change)
    r = p.watch(rounds=1)
    assert r.returncode == 2, r.stdout + r.stderr
    assert message in r.stdout
    assert not (p.stub / "agents-calls").exists() and p.calls() == []


def synthetic(p: Pipeline, sid: str = SID):
    """A line Claude Code writes itself at the end of a transcript ("No response requested.", a usage-limit notice):
    model '<synthetic>', zero usage, an id of its own; no call."""
    line = {
        "type": "assistant",
        "timestamp": iso(time.time() - 30),
        "sessionId": sid,
        "message": {
            "id": "9a1120fc-047d-4860-9010-8390fbe4df54",
            "model": "<synthetic>",
            "role": "assistant",
            "content": [{"type": "text", "text": "No response requested."}],
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        },
    }
    with open(p.projects / f"{sid}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")


def test_a_synthetic_last_line_keeps_the_context_of_the_last_call(p):
    """B3: 3 of 1,716 live transcripts end on a '<synthetic>' line; read as a call, it made the context 0."""
    p.transcript(context=250_000)
    synthetic(p)
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "cap t/builder 250,000 tokens; ordered to hand over" in r.stdout


def test_a_synthetic_line_is_no_call_for_the_budget(p):
    p.config["budget"] = {"calls": 3}
    p.transcript(calls=3)
    synthetic(p)
    r = p.watch(rounds=1)
    assert r.returncode == 1 and "budget t/builder" not in r.stdout, r.stdout + r.stderr


def test_the_registry_lists_the_need_1_fields_of_every_role_and_follows_a_planted_status_change(p):
    p.config["agents"]["t/verifier"] = p.agent("verifier", "verify.md")
    p.config["agents"]["t/critic"] = p.agent("critic", "critique.md")
    p.write("verify.md", "STATUS: done after Task 2\n")  # final by its start, as v2 reads it; equality: "stopped"
    p.transcript(context=42_000, calls=2)
    rows = [row(), row(name="t/verifier", sid=SID2, state="stopped", status=None, pid=None)]
    p.rounds(rows, {"rows": rows, "write": {str(p.run / "build-log.md"): "STATUS: building Task 4\n"}})
    start = time.time()
    r = p.watch(rounds=2)
    assert r.returncode == 1, r.stdout + r.stderr
    data = registry(p)
    assert (data["version"], data["run_dir"], data["watcher"]["round"]) == (1, str(p.run), 2)
    assert start - 1 <= seconds(data["written_at"]) <= time.time() + 1  # written in the round that saw the change
    roles = data["roles"]
    assert set(roles) == {"t/builder", "t/verifier", "t/critic"}
    need_1 = {"role", "lane", "job_id", "session_id", "state", "unit", "context", "calls", "cost_usd", "revivals"}
    assert all(need_1 | {"orders"} <= set(entry) for entry in roles.values())
    b, v, c = roles["t/builder"], roles["t/verifier"], roles["t/critic"]
    assert (b["state"], b["unit"], b["job_id"], b["session_id"]) == ("running", "STATUS: building Task 4", SID[:8], SID)
    assert (b["context"], b["calls"], b["revivals"], b["orders"]) == (42_000, 2, 0, [])
    assert (b["role"], b["lane"], b["settings"]) == ("builder", None, "_builder-settings.json")
    assert b["record"] == str(p.run / "build-log.md")
    assert (v["state"], v["unit"], v["session_id"]) == ("done", "STATUS: done after Task 2", SID2)
    assert (c["state"], c["unit"], c["session_id"], c["job_id"]) == ("stopped", "STATUS: reviewing Task 4", None, None)
    assert "adopted t/builder 11111111 by name" in r.stdout


def test_calls_and_cost_count_each_call_once_over_every_session_of_the_role(p):
    seed_registry(p, session_id=SID2, session_ids=[SID, SID2], job_id=SID2[:8])
    p.transcript(sid=SID, calls=3)  # msg_0 .. msg_2
    p.transcript(sid=SID2, calls=4, first=2)  # msg_2 .. msg_5: a resumed session repeats the call it continues
    p.rounds([row(sid=SID2)])
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    entry = registry(p)["roles"]["t/builder"]
    ur = usage_report()
    p0, p1, p2, p3 = ur.PRICE[ur.family(None)]
    # six calls, msg_0 .. msg_5: the current session alone gives 4, msg_2 twice gives 7, the lines give 14
    assert entry["calls"] == 6
    assert entry["cost_usd"] == round(6 * (3 * p0 + 10 * p1 + 990 * p2 + 7 * p3) / 1e6, 6)  # 0.002796 at ff3354a
    assert (entry["context"], entry["session_id"], entry["session_ids"]) == (1_000, SID2, [SID, SID2])


def test_a_renamed_session_stays_matched_by_its_id_and_a_stopped_namesake_is_ignored(p):
    p.rounds([row()], [row(name="t/renamed"), row(sid=SID2, state="stopped", status=None, pid=None, age=7200)])
    r = p.watch(rounds=2)
    assert r.returncode == 1, r.stdout + r.stderr
    assert p.calls() == []  # by name, the stopped namesake SID2 would be revived
    entry = registry(p)["roles"]["t/builder"]
    assert (entry["session_id"], entry["session_ids"], entry["state"]) == (SID, [SID], "running")


def test_a_fresh_session_is_matched_by_the_job_id_its_launch_printed(p):
    p.transcript()
    note(p)
    launch_out(p, "fresh | s aaaaaaaa      show recent output\n  claude stop aaaaaaaa      stop this session")
    stopped = row(state="stopped", status=None, pid=None)
    p.rounds([row()], [stopped, row(name="t/other", sid=SID3, age=0)])
    r = p.watch(rounds=2)
    assert r.returncode == 1, r.stdout + r.stderr
    assert p.stops() == [SID[:8]] and len(p.launches()) == 1
    entry = registry(p)["roles"]["t/builder"]
    assert (entry["job_id"], entry["session_id"], entry["session_ids"]) == ("aaaaaaaa", SID3, [SID, SID3])
    assert entry["state"] == "running" and entry["launched_at"] is not None


def test_a_copy_that_a_revival_started_is_kept_as_the_role_s_session(p):
    """The copy carries the conversation and the prompt, so it is the role's session. The text is the tail v2 logged on
    2026-10-25 (vault, measurements/2026-10-25-jobs-tmp-and-run-logs.md:29): no process ran, so nothing is stopped."""
    launch_out(p, "d a copy as 28319368. Without flags, the same command continues 11111111 itself.")
    p.rounds([row(state="stopped", status=None, pid=None)])
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    [launch] = p.launches()
    assert launch["argv"][:2] == ["--resume", SID] and launch["argv"][-1].startswith("Your process was stopped")
    assert p.stops() == []
    assert "copy t/builder 28319368 kept" in r.stdout
    entry = registry(p)["roles"]["t/builder"]
    assert (entry["job_id"], entry["session_id"], entry["session_ids"]) == ("28319368", None, [SID])


def test_a_resume_that_starts_a_copy_keeps_the_copy_and_the_order_and_stops_the_original_again(p):
    """The text of claude 2.1.289 when the stop before the resume is still running. The next round matches the copy by
    its job id (6e rule 2), and the original, stopped the round before, is no second session (6i.1)."""
    copy = "28319368-0000-0000-0000-000000000000"
    p.config["ack_wait"] = 0
    seed_registry(p, orders=[order()])
    launch_out(
        p,
        "note: session 11111111 is already running in the background, so this started a copy as 28319368."
        " `claude attach 11111111` opens the original.",
    )
    ack = {str(p.run / "build-log.md"): f"STATUS: building Task 3\nACK {MID}\n"}
    p.rounds([row()], {"rows": [row(), row(sid=copy, age=0)], "write": ack})
    r = p.watch(rounds=2)
    assert r.returncode == 1, r.stdout + r.stderr
    [launch] = p.launches()
    assert launch["argv"][:2] == ["--resume", SID]
    assert launch["argv"][-1] == f"Read critique.md again.\n\n{order_line(p, MID)}"
    assert p.stops() == [SID[:8], SID[:8]]  # before the resume and after it; never the copy's 28319368
    assert "copy t/builder 28319368 kept" in r.stdout and f"ack t/builder {MID}" in r.stdout
    assert "adopted t/builder" not in r.stdout and "copies t/builder" not in r.stdout
    entry = registry(p)["roles"]["t/builder"]
    assert (entry["job_id"], entry["session_id"], entry["session_ids"]) == ("28319368", copy, [SID, copy])
    [o] = entry["orders"]
    assert (o["resends"], o["closed"]) == (1, "acked")


def test_two_running_sessions_of_one_role_end_the_watch_with_exit_0(p):
    p.rounds([row(), row(sid=SID2, age=10)])
    r = p.watch(rounds=2)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "copies t/builder: 11111111, 66666666" in r.stdout
    assert p.calls() == []


def test_a_changed_brief_is_reloaded_with_an_order_instead_of_exit_4(p):
    brief = p.run / "_builder-assignment.md"
    p.rounds({"rows": [row()], "write": {str(brief): "# the builder's brief, changed\n"}})
    r = p.watch(rounds=2)
    assert r.returncode == 1, r.stdout + r.stderr
    assert r.stdout.count("control file reloaded: _builder-assignment.md") == 1
    assert p.stops() == [SID[:8]]
    [launch] = p.launches()
    assert launch["argv"][:2] == ["--resume", SID] and launch["argv"][2:-2] == flags(p)
    prompt = launch["argv"][-1]
    assert prompt.startswith(f"{RELOAD} {brief} was changed at ")
    m = ORDER_LINE.match(prompt.splitlines()[-1])
    assert m and m.group(2) == str(p.run / "build-log.md")
    [o] = registry(p)["roles"]["t/builder"]["orders"]
    assert (o["msg_id"], o["kind"], o["resends"], o["closed"]) == (m.group(1), "reload", 0, None) and o["sent_at"]


@pytest.mark.parametrize(
    "name, stopped", [("_builder-assignment.md", [SID[:8]]), ("_handoff-rule.md", sorted([SID[:8], SID2[:8]]))]
)
def test_a_reload_order_goes_to_the_roles_whose_texts_name_the_file(p, name, stopped):
    """The builder's fresh text names its brief; the hand-over order, common to every role, names _handoff-rule.md,
    which does not exist when the watcher starts: a brief created later is reloaded too."""
    p.config["agents"]["t/verifier"] = p.agent("verifier", "verify.md")
    p.rounds({"rows": [row(), row(name="t/verifier", sid=SID2)], "write": {str(p.run / name): "# changed\n"}})
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    assert r.stdout.count(f"control file reloaded: {name}") == 1
    assert sorted(p.stops()) == stopped and len(p.launches()) == len(stopped)
    assert all(c["argv"][-1].startswith(f"{RELOAD} {p.run / name} was changed at ") for c in p.launches())


@pytest.mark.parametrize("text, code, launches", [("# changed during the stop\n", 1, 1), (None, 4, 0)])
def test_a_brief_changed_during_the_stop_is_launched_and_a_removed_one_exits_4(p, text, code, launches):
    """A fresh session reads its brief when it starts, so a brief changed during the stop needs no exit; a removed
    one would leave the session a brief it cannot read."""
    p.transcript()
    note(p)
    (p.stub / "on-stop.json").write_text(json.dumps({str(p.run / "_builder-assignment.md"): text}))
    r = p.watch(rounds=1)
    assert r.returncode == code, r.stdout + r.stderr
    assert p.stops() == [SID[:8]] and len(p.launches()) == launches
    assert ("control file changed: _builder-assignment.md" in r.stdout) == (code == 4)


@pytest.mark.parametrize(
    "context, line, ordered",
    [
        (160_000, "STATUS: building Task 4\n", True),
        (100_000, "STATUS: building Task 4\n", False),
        (160_000, "STATUS: building Task 3\n", False),
    ],
)
def test_a_unit_end_past_the_mark_orders_a_hand_over_and_the_middle_of_a_unit_never(p, context, line, ordered):
    p.config["unit_end_grace"] = 0  # the order at once; the grace has its own tests below
    p.transcript(context=context)
    p.rounds([row()], {"rows": [row()], "write": {str(p.run / "build-log.md"): line}})
    r = p.watch(rounds=3)
    assert r.returncode == 1, r.stdout + r.stderr
    assert (f"unit end t/builder {context:,} tokens; ordered to hand over" in r.stdout) == ordered
    if not ordered:
        assert p.calls() == []
        return
    assert p.stops() == [SID[:8]]
    [launch] = p.launches()  # once: the hand-over is pending in round 3
    assert launch["argv"][:2] == ["--resume", SID]
    prompt = launch["argv"][-1]
    assert prompt.startswith(UNIT_END) and f"{p.run}/_handoff-rule.md" in prompt
    assert ORDER_LINE.match(prompt.splitlines()[-1])
    entry = registry(p)["roles"]["t/builder"]
    assert entry["handoff_since"] is not None and [o["kind"] for o in entry["orders"]] == ["unit-end"]


def test_a_unit_end_while_the_session_waits_is_ordered_and_sent_in_the_first_round_it_is_not_blocked(p):
    """A blocked row that waits (busy, no waitingFor) launches nothing, so its unit end still gives the order (6i.2,
    6i.3); 6j holds it while the row is blocked. The stop writes the marker after round 3's listing, not before."""
    p.config["unit_end_grace"] = 0  # the order at once; the grace has its own tests below
    p.transcript(context=160_000)
    marker = p.stub / "marker"
    (p.stub / "on-stop.json").write_text(json.dumps({str(marker): "stopped"}))
    p.rounds(
        [row()],
        {"rows": [row(state="blocked")], "write": {str(p.run / "build-log.md"): "STATUS: building Task 4\n"}},
        {"rows": [row()], "write": {str(marker): "round 3"}},
    )
    r = p.watch(rounds=3)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "unit end t/builder 160,000 tokens; ordered to hand over" in r.stdout
    assert p.stops() == [SID[:8]] and marker.read_text() == "stopped"
    [launch] = p.launches()
    assert launch["argv"][:2] == ["--resume", SID] and launch["argv"][-1].startswith(UNIT_END)
    entry = registry(p)["roles"]["t/builder"]
    assert entry["handoff_since"] is not None and [o["kind"] for o in entry["orders"]] == ["unit-end"]


def new_line_1(p, ago):
    """A watcher started now finds line 1 of the build log changed, written `ago` s ago, with the session at 180k."""
    seed_registry(p)  # its unit is "STATUS: building Task 3"
    p.write("build-log.md", "Task 3: done — abc1234\n", mtime=time.time() - ago)
    p.transcript(context=180_000)


@pytest.mark.parametrize("ago, ordered", [(300, False), (650, True)])
def test_a_unit_end_order_waits_until_the_new_line_1_is_the_grace_old(p, ago, ordered):
    """`unit_end_grace` is 600 s unless the config says otherwise: a line 1 of 300 s gives no order, one of 650 s does."""
    new_line_1(p, ago)
    r = p.watch(rounds=3)
    assert r.returncode == 1, r.stdout + r.stderr
    assert ("unit end t/builder 180,000 tokens; ordered to hand over" in r.stdout) == ordered
    if not ordered:
        assert "grace t/builder: new line 1 at 180,000 tokens; the unit-end order comes in " in r.stdout
        assert p.calls() == []
        return
    assert p.stops() == [SID[:8]]
    [launch] = p.launches()
    assert launch["argv"][:2] == ["--resume", SID] and launch["argv"][-1].startswith(UNIT_END)


def test_grace_zero_orders_a_unit_end_at_once(p):
    p.config["unit_end_grace"] = 0
    new_line_1(p, 0)
    r = p.watch(rounds=2)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "unit end t/builder 180,000 tokens; ordered to hand over" in r.stdout
    assert "grace t/builder" not in r.stdout
    assert p.stops() == [SID[:8]] and len(p.launches()) == 1


def test_a_busy_session_gets_the_unit_end_order_in_the_round_after_the_grace(p):
    """A 2 s grace and a round that answers after 2.2 s: round 1 waits, round 2 orders, round 3 finds it pending."""
    p.config["unit_end_grace"] = 2
    new_line_1(p, 0)
    p.rounds([row()], {"rows": [row()], "sleep": 2.2}, [row()])
    r = p.watch(rounds=3)
    assert r.returncode == 1, r.stdout + r.stderr
    waits, orders = r.stdout.find("grace t/builder:"), r.stdout.find("unit end t/builder 180,000 tokens; ordered")
    assert 0 <= waits < orders
    assert p.stops() == [SID[:8]] and len(p.launches()) == 1


def test_a_note_inside_the_grace_starts_the_fresh_session_and_no_order_is_given(p):
    """The same timing, with the session's own note arriving in round 2: the usual fresh session, never the order."""
    p.config["unit_end_grace"] = 2
    new_line_1(p, 0)
    hand_over = {str(p.run / "handoff-builder.md"): "HANDOFF builder after Task 3 — 2026-10-30 21:00\nState: done.\n"}
    p.rounds([row()], {"rows": [row()], "sleep": 2.2, "write": hand_over}, [row()])
    r = p.watch(rounds=3)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "fresh t/builder after note: HANDOFF builder after Task 3" in r.stdout
    assert "ordered to hand over" not in r.stdout
    [fresh] = p.launches()
    assert fresh["argv"][:-2] == flags(p)


def test_an_order_goes_to_the_inbox_and_is_resent_by_stop_and_resume_when_no_ack_comes(p):
    p.config["ack_wait"] = 0
    o = p.watch("--order", "t/builder", "Read critique.md again.")
    assert o.returncode == 0, o.stdout + o.stderr
    assert p.calls() == [] and not (p.stub / "agents-calls").exists()
    first, *rest = o.stdout.splitlines()
    mid = re.fullmatch(r"order ([0-9a-f]{8}) t/builder", first).group(1)
    prompt = f"Read critique.md again.\n\n{order_line(p, mid)}"
    assert "\n".join(rest) == prompt
    [line] = (p.run / "_control" / "orders.jsonl").read_text(encoding="utf-8").splitlines()
    sent = json.loads(line)
    assert (sent["msg_id"], sent["agent"], sent["text"]) == (mid, "t/builder", "Read critique.md again.")
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"resent {mid} to t/builder (1 of 2)" in r.stdout
    assert p.stops() == [SID[:8]]
    [launch] = p.launches()
    assert launch["argv"][:2] == ["--resume", SID] and launch["argv"][-1] == prompt
    [entry] = registry(p)["roles"]["t/builder"]["orders"]
    assert (entry["msg_id"], entry["kind"], entry["resends"], entry["closed"]) == (mid, "manager", 1, None)


@pytest.mark.parametrize(
    "answer, acked", [(f"ACK {MID}\n", True), (f"I will append the line `ACK {MID}` later\n", False)]
)
def test_an_ack_line_closes_the_order_and_a_quoted_one_does_not(p, answer, acked):
    p.config["ack_wait"] = 0
    seed_registry(p, orders=[order()])
    p.write("build-log.md", "STATUS: building Task 3\n" + answer)
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    assert (f"ack t/builder {MID}" in r.stdout) == acked
    assert (f"resent {MID} to t/builder (1 of 2)" in r.stdout) == (not acked)
    assert len(p.launches()) == (0 if acked else 1)
    [o] = registry(p)["roles"]["t/builder"]["orders"]
    assert (o["closed"], o["acked_at"] is not None) == (("acked", True) if acked else (None, False))


def test_an_order_still_without_ack_after_the_last_resend_ends_the_watch_with_exit_0(p):
    p.config.update(ack_wait=0, ack_resends=1)
    seed_registry(p, orders=[order()])
    r = p.watch(rounds=3)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"resent {MID} to t/builder (1 of 1)" in r.stdout
    assert f"no ack t/builder {MID} after 1 resends" in r.stdout
    assert len(p.launches()) == 1
    [o] = registry(p)["roles"]["t/builder"]["orders"]
    assert (o["resends"], o["closed"]) == (1, "no ack")


def test_a_final_line_with_a_suffix_is_done(p):
    p.config["agents"]["t/verifier"] = p.agent("verifier", "verify.md")
    p.write("verify.md", "STATUS: done after Task 2\n")
    p.rounds([row(), row(name="t/verifier", sid=SID2, state="stopped", status=None, pid=None)])
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    v = registry(p)["roles"]["t/verifier"]
    assert (v["state"], v["unit"]) == ("done", "STATUS: done after Task 2")  # equality gives "stopped"
    assert p.launches() == []


def wake_line(p: Pipeline, record: str, msg_id: str) -> str:
    return (
        f"Your record {p.run / record} is final on line 1. After the ACK, set line 1 to `STATUS: working on order "
        f"{msg_id}`; when this order's work is done, set it back to your final line."
    )


def test_a_manager_order_wakes_a_final_agent_by_a_resume_with_the_wake_line(p):  # owner, 2026-11-01
    p.config["agents"]["t/verifier"] = p.agent("verifier", "verify.md")
    p.write("verify.md", "STATUS: done after Task 2\n")
    o = p.watch("--order", "t/verifier", "Verify Task 3 again.")
    mid = re.fullmatch(r"order ([0-9a-f]{8}) t/verifier", o.stdout.splitlines()[0]).group(1)
    p.rounds([row(), row(name="t/verifier", sid=SID2, state="stopped", status=None, pid=None)])
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    [launch] = p.launches()
    order = f"Order {mid}: append the line `ACK {mid}` to {p.run / 'verify.md'} before anything else."
    assert launch["argv"][:2] == ["--resume", SID2]
    assert launch["argv"][-1] == f"Verify Task 3 again.\n\n{wake_line(p, 'verify.md', mid)}\n\n{order}"
    [entry] = registry(p)["roles"]["t/verifier"]["orders"]
    assert entry["closed"] is None and entry["sent_at"] is not None


def test_a_manager_order_wakes_a_final_on_demand_fixer_and_it_is_not_left_unrevived(p):  # owner, 2026-11-01
    fixer(p)
    p.write("fixer-log.md", "STATUS: done\n")
    o = p.watch("--order", "t/plan-fixer", "The owner answered the three held points.")
    assert o.returncode == 0, o.stdout + o.stderr
    p.rounds([row(), row(name="t/plan-fixer", sid=SID2, state="stopped", status=None, pid=None)])
    r = p.watch(rounds=1)
    [launch] = p.launches()
    assert launch["argv"][:2] == ["--resume", SID2] and "not revived" not in r.stdout
    assert launch["argv"][-1].startswith("The owner answered the three held points.\n\nYour record ")


def test_a_manager_order_launches_an_on_demand_fixer_that_has_no_session(p):
    fixer(p)
    o = p.watch("--order", "t/plan-fixer", "Answer C7 again.")
    mid = re.fullmatch(r"order ([0-9a-f]{8}) t/plan-fixer", o.stdout.splitlines()[0]).group(1)
    p.rounds([row()])
    r = p.watch(rounds=1)
    [launch] = p.launches()
    assert f"demand t/plan-fixer: order {mid}; launched" in r.stdout and "--resume" not in launch["argv"]
    assert launch["argv"][-1].startswith("Fixer: answer the open ids. ") and "Answer C7 again." in launch["argv"][-1]


def test_a_watcher_restarted_after_exit_4_logs_the_same_pending_orders_and_revival_counts(p):
    """10.8, second clause: the first watcher ends with exit 4 (a settings file changed before the resend), the second
    restores the order and the revival count, the third resends the order once it is due."""
    seed_registry(p, revivals=1, orders=[order()])
    settings = str(p.run / "_builder-settings.json")
    p.rounds({"rows": [row()], "write": {settings: "changed after the watcher started\n"}})
    restored = f"registry: t/builder revivals=1 orders={MID}"
    p.config["ack_wait"] = 0
    first = p.watch(rounds=1)
    assert first.returncode == 4 and restored in first.stdout, first.stdout + first.stderr
    assert p.calls() == []
    p.config["ack_wait"] = 3600
    second = p.watch(rounds=1)
    assert second.returncode == 1 and restored in second.stdout, second.stdout + second.stderr
    assert p.calls() == []
    p.config["ack_wait"] = 0
    third = p.watch(rounds=1)
    assert f"resent {MID} to t/builder (1 of 2)" in third.stdout, third.stdout + third.stderr
    assert len(p.launches()) == 1


def test_revivals_count_across_restarts(p):
    p.config["nudges"] = 2
    p.rounds([row(state="stopped", status=None, pid=None)])
    runs = [p.watch(rounds=1) for _ in range(3)]
    assert [r.returncode for r in runs] == [1, 1, 0], [r.stdout for r in runs]
    assert "registry: t/builder revivals=1 orders=-" in runs[1].stdout
    assert "registry: t/builder revivals=2 orders=-" in runs[2].stdout
    assert runs[2].stdout.strip().endswith("t/builder was revived 2 times; check it")
    assert len(p.launches()) == 2


def test_a_note_acted_on_before_a_restart_is_not_acted_on_again(p):
    p.transcript()
    note(p)
    first, second = p.watch(rounds=1), p.watch(rounds=1)
    assert (first.returncode, second.returncode) == (1, 1), first.stdout + second.stdout
    assert len(p.launches()) == 1 and p.stops() == [SID[:8]]


def test_the_cap_order_ends_with_an_order_line_and_is_recorded_as_a_pending_hand_over(p):
    p.transcript(context=250_000)
    r = p.watch(rounds=2)
    assert r.returncode == 1, r.stdout + r.stderr
    [launch] = p.launches()
    prompt = launch["argv"][-1]
    assert prompt.startswith(ORDER)
    m = ORDER_LINE.match(prompt.splitlines()[-1])
    assert m and m.group(2) == str(p.run / "build-log.md")
    entry = registry(p)["roles"]["t/builder"]
    [o] = entry["orders"]
    assert (o["msg_id"], o["kind"], o["resends"], o["acked_at"], o["closed"]) == (m.group(1), "handoff", 0, None, None)
    assert entry["handoff_since"] is not None and entry["context"] == 250_000


def test_a_fresh_session_gets_the_open_manager_orders_and_the_watcher_s_are_superseded(p):
    seed_registry(p, orders=[order(), order(MID2, "reload", "Orders from the main session: an old reload.")])
    p.transcript()
    note(p)
    start = time.time()
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    [launch] = p.launches()
    prompt = launch["argv"][-1]
    assert prompt.startswith("You are a fresh builder session; the previous one handed over")
    assert prompt.endswith(f"\n\nRead critique.md again.\n\n{order_line(p, MID)}") and MID2 not in prompt
    manager, reload = registry(p)["roles"]["t/builder"]["orders"]
    assert seconds(manager["sent_at"]) >= start - 1 and (manager["resends"], manager["closed"]) == (0, None)
    assert reload["closed"] == "superseded"


@pytest.mark.parametrize(
    "change, message",
    [
        ({"handoff_at": 250_000}, "config error: handoff_at 250000 is not below cap 200000"),
        ({"registry": "../registry.json"}, "config error: registry ../registry.json leaves run_dir"),
        ({"ack_resends": -1}, "config error: ack_resends is not a non-negative number"),
        ({"ack_wait": "15m"}, "config error: ack_wait is not a non-negative number"),
        ({"unit_end_order": 7}, "config error: unit_end_order is not a string"),
        ({"unit_end_grace": -1}, "config error: unit_end_grace is not a non-negative number"),
    ],
)
def test_v3_config_errors_exit_2_before_any_claude_command(p, change, message):
    p.config.update(change)
    r = p.watch(rounds=1)
    assert r.returncode == 2, r.stdout + r.stderr
    assert message in r.stdout
    assert not (p.stub / "agents-calls").exists() and p.calls() == []


@pytest.mark.parametrize(
    "agent, text, message",
    [("t/nobody", "Read it.", "config error: no agent t/nobody"), ("t/builder", "   ", "config error: empty order")],
)
def test_an_order_for_no_agent_or_without_text_exits_2_and_writes_nothing(p, agent, text, message):
    r = p.watch("--order", agent, text)
    assert r.returncode == 2, r.stdout + r.stderr
    assert message in r.stdout
    assert not (p.run / "_control" / "orders.jsonl").exists() and p.calls() == []


def test_log_lines_carry_the_utc_time(p, monkeypatch):
    monkeypatch.setenv("TZ", "XXX+4")  # local time 4 hours behind UTC: a local stamp cannot pass
    p.transcript(context=250_000)
    before = time.time()
    r = p.watch(rounds=1)
    after = time.time()
    [line] = [x for x in r.stdout.splitlines() if "cap t/builder" in x]
    assert line.split(" ", 1)[0] in {time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(t)) for t in (before, after)}, line


def test_every_function_of_the_watcher_is_under_50_lines():
    """`.claude/rules/python.md:9` (at ff3354a: Watcher.agent 83 lines, Transcripts.stats 55, Watcher.__init__ 50)."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    sizes = {
        f"{n.name}:{n.lineno}": n.end_lineno - n.lineno + 1
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    assert {name: size for name, size in sizes.items() if size >= 50} == {}


def test_the_example_configs_name_no_model_and_set_the_hand_over_mark_and_the_ack_rules():
    example = SCRIPT.parents[1] / "example"
    for name in ("agents.json", "agents-judge.json"):
        assert "--model" not in json.loads((example / name).read_text(encoding="utf-8"))["common"], name
    config = json.loads((example / "agents.json").read_text(encoding="utf-8"))
    assert (config["handoff_at"], config["ack_wait"], config["ack_resends"]) == (250_000, 900, 2)
    assert config["unit_end_grace"] == 600


LAUNCH = """# Launch table of a run

| lane | role | skills | settings | ECC texts | cost estimate |
| --- | --- | --- | --- | --- | --- |
| b | `t/builder` | none | `_control/_builder-settings.json` | none | $40 |
| v | `t/ghost` | none | `_control/_ghost-settings.json` | none | $5 |
"""


@pytest.mark.parametrize(
    "table, lane, settings", [(LAUNCH, "b", "_control/_builder-settings.json"), (None, None, "_builder-settings.json")]
)
def test_the_registry_takes_lane_and_settings_from_the_launch_table(p, table, lane, settings):
    if table:
        p.write("_launch.md", table)
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    roles = registry(p)["roles"]
    assert set(roles) == {"t/builder"}
    assert (roles["t/builder"]["lane"], roles["t/builder"]["settings"]) == (lane, settings)
    assert ("launch table: t/ghost is not watched" in r.stdout) == bool(table)


NOTHING = [sys.executable, "-c", "raise SystemExit(3)"]  # a work_check that reports nothing to take
FLAG = "import os, sys; sys.exit(0 if os.path.exists(sys.argv[1]) else 3)"  # work waits once the file exists


def test_a_note_of_a_dead_session_with_an_order_waiting_launches_fresh_with_the_order_in_the_same_round(p):
    """A run of 2026-11-02: the note of an agent's dead session met a waiting manager order, the work check found
    nothing, and the order went out a round later; the order is work to take now."""
    p.config["agents"]["t/builder"]["work_check"] = NOTHING
    p.transcript()
    note(p)
    p.watch("--order", "t/builder", "Answer V7 in Task 3.")
    p.rounds([row(state="stopped", status=None, pid=None)])
    r = p.watch(rounds=1)
    assert "idle t/builder" not in r.stdout, r.stdout + r.stderr
    [launch] = p.launches()
    assert "--resume" not in launch["argv"] and "Answer V7 in Task 3." in launch["argv"][-1]


def test_a_note_with_nothing_to_take_logs_idle_and_launches_nothing(p):
    p.config["agents"]["t/builder"]["work_check"] = NOTHING
    p.transcript()
    line = note(p)
    r = p.watch(rounds=2)
    assert r.stdout.count("idle t/builder: nothing to take") == 1 and p.launches() == [], r.stdout + r.stderr
    assert p.stops() == [SID[:8]], r.stdout + r.stderr  # V9: R6 stops a role that is not on demand too
    assert registry(p)["roles"]["t/builder"]["idle"] == line


def test_check_mode_says_the_exit_3_stop_and_runs_no_claude_command(p):  # V10
    p.config["agents"]["t/builder"]["work_check"] = NOTHING
    p.transcript()
    note(p)
    r = p.watch("--check")
    assert r.returncode == 0 and p.calls() == [], r.stdout + r.stderr
    assert "idle t/builder: nothing to take" in r.stdout and f"would stop {SID[:8]}" in r.stdout, r.stdout + r.stderr


def test_an_idle_role_is_launched_when_its_check_passes_later(p, tmp_path):
    flag = tmp_path / "flag"
    p.config["agents"]["t/builder"]["work_check"] = [sys.executable, "-c", FLAG, str(flag)]
    p.transcript()
    note(p)
    p.watch(rounds=1)
    assert p.launches() == []
    flag.write_text("")
    r = p.watch(rounds=1)  # a restarted watcher: the registry's `idle`, not the note, brings the role back
    assert "fresh t/builder after idle: work waits" in r.stdout and len(p.launches()) == 1, r.stdout + r.stderr


@pytest.mark.parametrize(
    "check, line",
    [
        (["/no/such/check"], "work_check failed to run"),
        ([sys.executable, "{skill}/open_ids.py", "{run}", "--no-such-flag"], "work_check failed (exit 2)"),
        ([sys.executable, "{skill}/no_such_script.py"], "work_check failed (exit 2)"),
    ],
)
def test_a_work_check_that_fails_or_cannot_run_launches(p, check, line):  # C5, A4
    p.config["agents"]["t/builder"]["work_check"] = check
    p.transcript()
    note(p)
    r = p.watch(rounds=1)
    assert len(p.launches()) == 1 and line in r.stdout, r.stdout + r.stderr


def test_work_check_fills_run_and_skill(p):  # A1: unfilled, the check finds no folder `{run}` and exits 1
    record = "import pathlib, sys; pathlib.Path(sys.argv[1], 'argv.txt').write_text(sys.argv[2])"
    p.config["agents"]["t/builder"]["work_check"] = [sys.executable, "-c", record, "{run}", "{skill}/watch_agents.py"]
    p.transcript()
    note(p)
    r = p.watch(rounds=1)
    assert "work_check failed" not in r.stdout and len(p.launches()) == 1, r.stdout + r.stderr
    assert pathlib.Path((p.run / "argv.txt").read_text()).samefile(SCRIPT)


def test_work_check_must_be_a_list_of_strings(p):  # C9
    p.config["agents"]["t/builder"]["work_check"] = "not a list"
    r = p.watch(rounds=1)
    assert r.returncode == 2 and "config error: t/builder: work_check is not a list of strings" in r.stdout


def test_an_idle_role_whose_session_stopped_is_not_revived(p):  # C4, A2
    p.config["agents"]["t/builder"]["work_check"] = NOTHING
    p.rounds([row(state="stopped", status=None, pid=None)])
    p.transcript()
    note(p)
    r = p.watch(rounds=2)
    assert p.launches() == [] and "continued t/builder" not in r.stdout, r.stdout + r.stderr
    assert r.stdout.count("idle t/builder") == 1


def test_a_note_after_a_hand_over_order_launches_without_the_work_check(p):  # C4, A3 (a)
    p.config["handoff_wait"] = 0
    p.config["agents"]["t/builder"]["work_check"] = NOTHING
    p.transcript(context=250_000)
    text = "HANDOFF builder after Task 3 — 2026-10-26 06:00\nState: in the middle of Step 4.\n"
    p.rounds([row()], {"rows": [row()], "write": {str(p.run / "handoff-builder.md"): text}})
    r = p.watch(rounds=2)
    assert "fresh t/builder after note" in r.stdout and "without a note (timeout)" not in r.stdout, r.stdout + r.stderr
    assert "idle t/builder" not in r.stdout and len(p.launches()) == 2  # the order's resume, then the fresh session


def test_an_idle_role_survives_a_config_reload(p, tmp_path):  # C4, A3 (b)
    flag = tmp_path / "flag"
    p.config["agents"]["t/builder"]["work_check"] = [sys.executable, "-c", FLAG, str(flag)]
    config = str(p.run / "_agents-v2.json")
    p.rounds(
        {"rows": [row()], "write": {config: json.dumps({**p.config, "nudges": 5})}},
        {"rows": [row()], "write": {str(flag): ""}},
        [row()],
    )
    p.transcript()
    note(p)
    r = p.watch(rounds=3)
    assert r.stdout.count("config reloaded: _agents-v2.json") == 1, r.stdout + r.stderr
    assert "fresh t/builder after idle: work waits" in r.stdout and len(p.launches()) == 1


@pytest.mark.parametrize("left", [None, []])
def test_an_idle_role_whose_work_check_a_reload_removes_is_launched(p, left):  # B2: no KeyError, no silenced role
    p.config["agents"]["t/builder"]["work_check"] = NOTHING
    agent = {k: v for k, v in p.config["agents"]["t/builder"].items() if k != "work_check"}
    agent.update({} if left is None else {"work_check": left})
    config = str(p.run / "_agents-v2.json")
    p.rounds({"rows": [row()], "write": {config: json.dumps({**p.config, "agents": {"t/builder": agent}})}}, [row()])
    p.transcript()
    note(p)
    r = p.watch(rounds=2)
    assert r.returncode == 1 and "config reloaded: _agents-v2.json" in r.stdout, r.stdout + r.stderr
    assert "fresh t/builder after idle" in r.stdout and len(p.launches()) == 1


def fixer(p: Pipeline, **fields) -> None:
    """t/plan-fixer on demand, `fields` added to its entry, with a fresh text of its own and line 1 `STATUS: fixing`."""
    p.config["agents"]["t/plan-fixer"] = {**p.agent("plan-fixer", "fixer-log.md"), "on_demand": True, **fields}
    p.config["fresh"] = {"plan-fixer": "Fixer: answer the open ids. {run}"}
    p.write("fixer-log.md", "STATUS: fixing\n")


def bump(p: Pipeline, name: str, ident: str, ago: int) -> None:
    """The registry as a watcher that first saw `ident` `ago` seconds earlier left it."""
    data = registry(p)
    seen = data["roles"][name]["first_seen"]
    seen[ident] = utc(seconds(seen[ident]) - ago)
    (p.run / "_control" / "registry.json").write_text(json.dumps(data), encoding="utf-8")


def critique(*idents: str, task: int = 1) -> str:
    """critique.md with `idents` filed under `## Task <task>`."""
    return f"STATUS: reviewed through Task {task}\n## Task {task}\n" + "".join(f"#### {i} — t\n" for i in idents)


def test_an_on_demand_agent_is_not_launched_at_start_or_revived(p):
    fixer(p)
    stopped = row(name="t/plan-fixer", sid=SID2, state="stopped", status=None, pid=None)
    p.rounds([row()], [row(), stopped])
    r = p.watch(rounds=2)
    assert p.launches() == [] and "demand t/plan-fixer: done, not revived" in r.stdout


def test_the_demand_queue_launches_the_fixer_once_with_its_fresh_text(p):
    fixer(p, demand={"kinds": ["C", "A"], "parity": "all", "queue": 2, "wait_minutes": 45})
    p.write("critique.md", critique("C1", "C2"))
    p.write("critique-response.md", "STATUS: writing Task 2\n")
    p.rounds([row()], [row(), row(name="t/plan-fixer", sid=SID2, age=0)])
    r = p.watch(rounds=2)
    [launch] = p.launches()
    assert "demand t/plan-fixer: 2 open ids, oldest 0 min; launched" in r.stdout and p.stops() == []
    assert launch["argv"][-1].startswith("Fixer: answer the open ids. ") and "{run}" not in launch["argv"][-1]


def test_the_demand_age_launches_the_fixer_after_wait_minutes(p):
    fixer(p, demand={"kinds": ["C"], "queue": 10, "wait_minutes": 1})
    p.write("critique.md", critique("C1"))
    p.watch(rounds=1)
    assert p.launches() == []
    bump(p, "t/plan-fixer", "C1", 120)
    r = p.watch(rounds=1)
    assert len(p.launches()) == 1 and "demand t/plan-fixer: 1 open ids, oldest 2 min; launched" in r.stdout


def test_answered_ids_leave_the_demand_queue_and_first_seen(p):
    fixer(p, demand={"kinds": ["C"], "queue": 3})
    p.write("critique.md", critique("C1", "C2"))
    p.watch(rounds=1)
    assert sorted(registry(p)["roles"]["t/plan-fixer"]["first_seen"]) == ["C1", "C2"]
    p.write("critique-response.md", "STATUS: writing Task 2\nC1: applied — x\nC2: rejected — y\n")
    p.watch(rounds=1)
    assert registry(p)["roles"]["t/plan-fixer"]["first_seen"] == {} and p.launches() == []


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"demand": {"queue": 1}}, "t/plan-fixer: demand needs on_demand"),
        ({"on_demand": True, "demand": {"queue": "6"}}, "t/plan-fixer: demand.queue is not a positive integer"),
        ({"on_demand": True, "demand": {"size": 6}}, "t/plan-fixer: unknown demand fields size"),
    ],
)
def test_the_demand_fields_are_checked_before_any_claude_command(p, fields, message):
    p.config["agents"]["t/plan-fixer"] = {**p.agent("plan-fixer", "fixer-log.md"), **fields}
    r = p.watch(rounds=1)
    assert r.returncode == 2 and f"config error: {message}" in r.stdout and p.calls() == []


def test_the_demand_defaults_count_every_kind_and_drop_code_findings(p):
    fixer(p)
    p.write("critique.md", critique("C1", "C2", "A1"))
    p.write("build-log.md", "STATUS: building Task 3\nB1: sent to plan-fixer — the plan names a missing file\n")
    p.write("verify.md", "STATUS: verifying Task 2\n## Task 1\n#### V1 — (plan) major: x\n#### V2 — (code) minor: y\n")
    sixth = {str(p.run / "critique.md"): critique("C1", "C2", "C3", "A1")}
    p.rounds([row()], {"rows": [row()], "write": sixth})
    r = p.watch(rounds=2)
    assert len(p.launches()) == 1 and "demand t/plan-fixer: 6 open ids, oldest 0 min; launched" in r.stdout


def test_an_idle_on_demand_fixer_is_stopped_and_not_relaunched_below_the_demand_queue(p):
    check = ["python3", "{skill}/open_ids.py", "{run}", "--kind", "C,A", "--cause", "plan"]
    fixer(p, demand={"kinds": ["C", "A"], "queue": 6, "wait_minutes": 45}, work_check=check)
    p.transcript(sid=SID2)
    p.write("handoff-plan-fixer.md", "HANDOFF plan-fixer after Task 1 — 2026-10-30 07:00\n", mtime=time.time() - 120)
    live = row(name="t/plan-fixer", sid=SID2)
    stopped = row(name="t/plan-fixer", sid=SID2, state="stopped", status=None, pid=None)
    p.rounds([row(), live], {"rows": [row(), stopped], "write": {str(p.run / "critique.md"): critique("C1")}})
    r = p.watch(rounds=2)
    assert "idle t/plan-fixer: nothing to take" in r.stdout and p.stops() == [SID2[:8]]
    assert p.launches() == [] and "fresh t/plan-fixer after idle" not in r.stdout


def test_two_on_demand_fixers_by_parity_keep_their_own_first_seen(p):
    fixer(p, demand={"kinds": ["C"], "parity": "odd"})
    p.config["agents"]["t/plan-fixer-b"] = {
        **p.agent("plan-fixer-b", "fixer-log-b.md"),
        "on_demand": True,
        "demand": {"kinds": ["C"], "parity": "even"},
    }
    p.config["fresh"]["plan-fixer-b"] = "Fixer b: answer the open ids."
    p.write("fixer-log-b.md", "STATUS: fixing\n")
    p.write("critique.md", critique("C1", task=2))
    p.watch(rounds=1)
    bump(p, "t/plan-fixer-b", "C1", 50 * 60)
    r = p.watch(rounds=1)
    [launch] = p.launches()
    assert launch["argv"][launch["argv"].index("--name") + 1] == "t/plan-fixer-b"
    assert "demand t/plan-fixer-b: 1 open ids, oldest 50 min; launched" in r.stdout
    assert registry(p)["roles"]["t/plan-fixer"]["first_seen"] == {}


def test_a_fixer_never_launched_does_not_hold_back_the_final_exit(p):  # R8
    fixer(p)
    p.config["final_stop_minutes"] = None  # the builder's busy final session is this test's fixture, not its subject
    (p.run / "fixer-log.md").unlink()  # never launched: no record yet
    p.write("build-log.md", "STATUS: done\n")
    r = p.watch(rounds=3)
    assert r.returncode == 0 and r.stdout.strip().endswith("every STATUS line is final"), r.stdout + r.stderr
    assert p.launches() == []


@pytest.mark.parametrize(
    ("files", "rows", "plain"),
    [
        pytest.param({"critique.md": critique("C1")}, [row()], {}, id="an open id below the queue"),
        pytest.param({}, [row(), row(name="t/plan-fixer", sid=SID2, age=0)], {}, id="a live fixer not yet written"),
        pytest.param({}, [row()], {"t/critic": ("critic", "critic-log.md")}, id="a plain role with no session"),
    ],
)
def test_open_ids_a_live_fixer_or_a_plain_role_hold_back_the_final_exit(p, files, rows, plain):  # R8
    fixer(p, demand={"kinds": ["C"], "queue": 6})
    (p.run / "fixer-log.md").unlink()
    p.write("build-log.md", "STATUS: done\n")
    for name, text in files.items():
        p.write(name, text)
    p.config["agents"].update({name: p.agent(*entry) for name, entry in plain.items()})
    p.rounds(rows)
    r = p.watch(rounds=2)
    assert "every STATUS line is final" not in r.stdout and p.launches() == [], r.stdout + r.stderr


def test_a_relaunched_fixer_stopped_before_its_first_write_does_not_hold_back_the_final_exit(p):  # V11 (R8)
    fixer(p, demand={"kinds": ["C"], "queue": 1})
    p.config["final_stop_minutes"] = None  # the builder's busy final session is this test's fixture, not its subject
    p.write("fixer-log.md", "STATUS: done\n", mtime=time.time() - 600)  # the last session's: final() stays False
    p.write("build-log.md", "STATUS: done\n")
    p.write("critique.md", critique("C1"))
    stopped = row(name="t/plan-fixer", sid=SID2, state="stopped", status=None, pid=None, age=0)
    answered = {str(p.run / "critique-response.md"): "STATUS: writing Task 2\nC1: applied — x\n"}
    p.rounds([row()], {"rows": [row(), stopped], "write": answered})
    r = p.watch(rounds=3)
    assert "demand t/plan-fixer: 1 open ids, oldest 0 min; launched" in r.stdout and len(p.launches()) == 1
    assert r.returncode == 0 and r.stdout.strip().endswith("every STATUS line is final"), r.stdout + r.stderr


def test_a_failed_on_demand_fixer_exits_and_is_not_relaunched(p):  # R9
    fixer(p, demand={"kinds": ["C"], "queue": 1})
    p.write("critique.md", critique("C1"))
    p.rounds([row(), row(name="t/plan-fixer", sid=SID2, state="failed", status=None, pid=None)])
    r = p.watch(rounds=2)
    assert r.returncode == 0 and r.stdout.strip().endswith("t/plan-fixer failed"), r.stdout + r.stderr
    assert p.launches() == []


def test_a_stopped_on_demand_fixer_is_launched_again_when_its_ids_wait(p):  # R9: only a failed one is held back
    fixer(p, demand={"kinds": ["C"], "queue": 1})
    p.write("critique.md", critique("C1"))
    p.rounds([row(), row(name="t/plan-fixer", sid=SID2, state="stopped", status=None, pid=None)])
    r = p.watch(rounds=1)
    assert len(p.launches()) == 1 and "demand t/plan-fixer: 1 open ids, oldest 0 min; launched" in r.stdout


def test_an_on_demand_fixer_launched_after_done_is_capped_like_any_role(p):
    fixer(p, demand={"kinds": ["C"], "queue": 1})
    p.write("fixer-log.md", "STATUS: done\n", mtime=time.time() - 600)
    p.write("critique.md", critique("C1"))
    p.transcript(sid=SID2, context=250_000)
    p.rounds([row()], [row(), row(name="t/plan-fixer", sid=SID2, age=0)])
    r = p.watch(rounds=2)
    fresh, order = p.launches()
    assert fresh["argv"][-1].startswith("Fixer: answer the open ids. ")
    assert order["argv"][:2] == ["--resume", SID2] and order["argv"][-1].startswith(ORDER)
    assert "cap t/plan-fixer 250,000 tokens; ordered to hand over" in r.stdout


def test_check_mode_says_the_demand_stop_and_runs_no_claude_command(p):  # V10
    fixer(p)
    p.write("fixer-log.md", "STATUS: done\n")
    p.rounds([row(), row(name="t/plan-fixer", sid=SID2)])
    r = p.watch("--check")
    assert r.returncode == 0 and p.calls() == [], r.stdout + r.stderr
    assert f"would stop {SID2[:8]}" in r.stdout, r.stdout + r.stderr


def test_a_done_on_demand_fixer_is_stopped_when_its_demand_queue_is_empty(p):
    fixer(p)
    p.write("fixer-log.md", "STATUS: done\n")
    p.rounds([row(), row(name="t/plan-fixer", sid=SID2)])
    r = p.watch(rounds=1)
    assert p.stops() == [SID2[:8]] and p.launches() == []
    assert "demand t/plan-fixer: queue empty, stopped" in r.stdout


ELSEWHERE = row(sid=SID2, state="stopped", status=None, pid=None, age=60, cwd="/elsewhere")  # an earlier run's


@pytest.mark.parametrize(
    "rows, adopted",
    [
        ([ELSEWHERE, row(age=3600)], SID),  # the newer namesake, stopped, ran in another folder
        ([ELSEWHERE], None),  # no row in the agent's cwd: no session, and nothing revived
    ],
    ids=["older-here", "elsewhere-only"],
)
def test_rule_3_adopts_only_a_namesake_in_the_agent_s_cwd(p, rows, adopted):
    """J5 (judge.md of manager-build-2026-10-29, #### J5): with launched_at None, rule 3 adopted the newest row of the
    agent's name from any folder, so an earlier run's session of the same name was adopted, then revived."""
    p.rounds(rows)
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    assert registry(p)["roles"]["t/builder"]["session_id"] == adopted
    assert p.calls() == []  # by name alone, the stopped SID2 was adopted and revived


@pytest.mark.parametrize("age, adopted", [(3600, None), (600, SID)], ids=["before-yes", "after-yes"])
def test_rule_3_before_a_launch_adopts_a_row_started_after_the_first_yes_line(p, age, adopted):
    """J5, C35: before the watcher's first launch, rule 3's floor is the first `Yes:` line of `_launch.md` minus 5 s,
    which the run writes once before any launch; entries made in the run folder after the agent started move nothing."""
    yes = time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(time.time() - 1800))
    p.write("_launch.md", f"Yes: {yes} — t/builder\nYes: 2099-01-01T00:00Z — a later line\n")
    p.rounds([row(age=age)])
    (p.run / "scratch" / "planner").mkdir(parents=True)
    p.write("handoff-critic.md", "HANDOFF critic after Task 1 — 2026-10-30 09:00\n")
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    assert registry(p)["roles"]["t/builder"]["session_id"] == adopted


def test_check_mode_adopts_no_namesake_in_another_folder(p):
    """J5 under --check, which matches by name and cwd alone: an earlier run's stopped namesake in another folder is
    not the agent's row, so a --check round says nothing of it and runs no claude command."""
    p.rounds([ELSEWHERE])
    r = p.watch("--check")
    assert r.returncode == 0 and p.calls() == [], r.stdout + r.stderr
    out = {x.split(": ", 1)[0]: x for x in r.stdout.splitlines() if x.startswith("t/")}
    assert SID2[:8] not in out["t/builder"], r.stdout


def test_a_final_agents_live_session_is_stopped_at_its_prompt(p):
    # Owner (2026-10-30): sessions close without the owner; the watcher stops them, the main session never runs
    # `claude stop` (the auto-mode classifier refuses it there).
    p.write("build-log.md", "STATUS: done after Task 3\n")
    p.transcript()
    p.rounds([row(state="done", status="idle")])
    r = p.watch(rounds=1)
    assert r.returncode == 0, r.stdout + r.stderr
    assert p.stops() == [SID[:8]] and p.launches() == []
    assert "stopped t/builder 11111111: final (STATUS: done after Task 3)" in r.stdout
    assert "every STATUS line is final" in r.stdout


def test_a_busy_final_session_is_left_for_final_stop_minutes_then_stopped(p):
    # A waiter shell shows the session as busy; the record's age decides, so a last commit is not cut.
    p.write("build-log.md", "STATUS: done after Task 3\n")
    p.transcript()
    p.rounds([row(state="working", status="busy")])
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    assert p.stops() == [] and "every STATUS line is final; waiting for busy t/builder" in r.stdout
    p.write("build-log.md", "STATUS: done after Task 3\n", mtime=time.time() - 11 * 60)
    r = p.watch(rounds=1)
    assert r.returncode == 0 and p.stops() == [SID[:8]], r.stdout + r.stderr
    assert "stopped t/builder 11111111: final (STATUS: done after Task 3)" in r.stdout


def test_final_stop_minutes_null_leaves_a_final_session_live(p):
    p.config["final_stop_minutes"] = None
    p.write("build-log.md", "STATUS: done after Task 3\n")
    p.transcript()
    p.rounds([row(state="done", status="idle")])
    r = p.watch(rounds=1)
    assert r.returncode == 0 and p.stops() == [], r.stdout + r.stderr
    assert "every STATUS line is final" in r.stdout


def test_check_says_it_would_stop_a_final_session(p):
    p.write("build-log.md", "STATUS: done after Task 3\n")
    p.transcript()
    p.rounds([row(state="done", status="idle")])
    r = p.watch("--check")
    assert r.returncode == 0 and p.stops() == [], r.stdout + r.stderr
    assert "t/builder: would stop 11111111" in r.stdout and "would exit 0: every STATUS line is final" in r.stdout


def test_a_second_fixer_without_shared_ids_is_not_launched_over_a_build_logs_b_line(p):  # judge J3 (pipeline-fold)
    fixer(p, demand={"kinds": ["C", "B"], "queue": 1, "parity": "odd"})
    p.config["agents"]["t/plan-fixer-b"] = {
        **p.agent("plan-fixer-b", "fixer-b-log.md"),
        "on_demand": True,
        "demand": {"kinds": ["C", "B"], "queue": 1, "parity": "even", "shared": False},
    }
    p.config["fresh"]["plan-fixer-b"] = "Fixer b: answer the open ids of the even tasks. {run}"
    p.write("fixer-b-log.md", "STATUS: fixing\n")
    p.write("build-log-b.md", "STATUS: building Task 3\nB7: sent to plan-fixer — step 2 names a file Task 1 removed\n")
    p.rounds([row()])
    r = p.watch(rounds=1)
    assert "demand t/plan-fixer: 1 open ids, oldest 0 min; launched" in r.stdout, r.stdout + r.stderr
    assert "demand t/plan-fixer-b" not in r.stdout
    names = [c["argv"][c["argv"].index("--name") + 1] for c in p.launches()]
    assert names == ["t/plan-fixer"]


@pytest.mark.parametrize("code, final", [(0, False), (3, True)])
def test_a_final_builder_whose_lane_has_work_is_revived_not_left_final(p, code, final):
    """A project's run of 2026-11-01: a builder's `STATUS: done` came before the verifier's (code) findings for its lane, and
    nothing took them for ten hours. Its `final_check` exits 0 while its lane has work: then it is not final and its
    stopped session is resumed; exit 3 keeps it final."""
    p.write("build-log.md", "STATUS: done\n")
    p.config["agents"]["t/builder"]["final_check"] = [sys.executable, "-c", f"print('V12'); raise SystemExit({code})"]
    p.transcript()
    p.rounds([row(state="stopped", status=None, pid=None)])
    r = p.watch(rounds=1)
    if final:
        assert r.returncode == 0 and "every STATUS line is final" in r.stdout, r.stdout + r.stderr
        assert p.launches() == []
    else:
        assert "final, but its lane has work: V12" in r.stdout, r.stdout + r.stderr
        assert [c["argv"][c["argv"].index("--resume") + 1] for c in p.launches()] == [SID]


def own_pack(p):
    """t/builder has a pack of its own whose mark its session's transcript does not carry."""
    p.write("_pack-builder.md", "Your standing orders: the builder lane's pack\n")
    p.config["agents"]["t/builder"]["extra_prompt"] = {
        "file": "_pack-builder.md",
        "mark": "Your standing orders: the builder lane's pack",
    }


def test_a_session_without_its_pack_hands_over_at_a_unit_end_at_any_context(p):  # owner, 2026-11-01
    p.config["unit_end_grace"] = 0
    own_pack(p)
    seed_registry(p)
    p.write("build-log.md", "Task 3: done — abc1234\n")
    p.transcript(context=40_000)
    r = p.watch(rounds=2)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "unit end t/builder: its session lacks the pack; ordered to hand over" in r.stdout
    [launch] = p.launches()
    assert launch["argv"][:2] == ["--resume", SID] and "without your lane's pack" in launch["argv"][-1]


def test_a_final_builder_without_its_pack_is_revived_fresh_with_the_pack(p):
    own_pack(p)
    p.write("build-log.md", "STATUS: done\n")
    p.config["agents"]["t/builder"]["final_check"] = [sys.executable, "-c", "print('V12')"]
    p.transcript()
    p.rounds([row(state="stopped", status=None, pid=None)])
    r = p.watch(rounds=1)
    assert "fresh t/builder: revived with its pack" in r.stdout, r.stdout + r.stderr
    [launch] = p.launches()
    assert "--resume" not in launch["argv"]
    assert launch["argv"][launch["argv"].index("--append-system-prompt-file") + 1].endswith("_pack-builder.md")


def test_an_order_to_a_final_agent_without_its_pack_starts_it_fresh_with_the_pack_and_the_order(p):
    own_pack(p)
    p.write("build-log.md", "STATUS: done\n")
    p.watch("--order", "t/builder", "Fix V12 in Task 3.")
    p.transcript()
    p.rounds([row(state="stopped", status=None, pid=None)])
    r = p.watch(rounds=1)
    assert "fresh t/builder: woken by an order, with its pack" in r.stdout, r.stdout + r.stderr
    [launch] = p.launches()
    assert "--resume" not in launch["argv"] and "Fix V12 in Task 3." in launch["argv"][-1]
    assert "--append-system-prompt-file" in launch["argv"]


@pytest.mark.parametrize("ordered", [True, False])
def test_a_dead_session_without_its_pack_is_never_resumed_even_when_not_final(p, ordered):
    """A run of 2026-11-02: a plan fixer at `STATUS: fixing` whose session predated the pack was resumed for an order,
    and its first call rewrote 157k tokens without the pack. A dead session's cache is cold anyway: it starts fresh with
    the pack, its open orders in its prompt."""
    own_pack(p)
    p.write("build-log.md", "STATUS: building Task 3\n")
    if ordered:
        p.watch("--order", "t/builder", "Answer V7 in Task 3.")
    p.transcript()
    p.rounds([row(state="stopped", status=None, pid=None)])
    r = p.watch(rounds=1)
    [launch] = p.launches()
    assert "--resume" not in launch["argv"] and "--append-system-prompt-file" in launch["argv"], r.stdout + r.stderr
    assert ("Answer V7 in Task 3." in launch["argv"][-1]) == ordered


def test_a_live_session_of_the_agent_s_name_beside_a_finished_recorded_one_is_adopted_and_nothing_launches(p):
    """A project's run of 2026-11-02: the registry held a finished job while a session launched by hand ran busy; the watcher
    took the role for done and launched two more beside it. A live row of its name in its cwd, newer than the recorded
    one, is the agent's."""
    seed_registry(p)
    p.write("build-log.md", "STATUS: building Task 3\n")
    p.transcript()
    p.transcript(sid=SID2)
    cwd = p.config["agents"]["t/builder"]["cwd"]
    p.rounds([row(state="done", status=None, pid=None, age=7200), row(sid=SID2, age=600, cwd=cwd)])
    r = p.watch(rounds=1)
    assert f"adopted t/builder {SID2[:8]} by name: live beside its recorded {SID[:8]}" in r.stdout, r.stdout + r.stderr
    assert p.launches() == [] and registry(p)["roles"]["t/builder"]["job_id"] == SID2[:8]


def test_a_live_namesake_in_another_folder_or_older_than_the_recorded_row_is_not_adopted(p):
    seed_registry(p)
    p.write("build-log.md", "STATUS: building Task 3\n")
    p.transcript()
    cwd = p.config["agents"]["t/builder"]["cwd"]
    p.rounds([row(state="done", status=None, pid=None, age=600), row(sid=SID2, age=7200, cwd=cwd)])
    r = p.watch(rounds=1)
    assert "adopted t/builder" not in r.stdout, r.stdout + r.stderr
