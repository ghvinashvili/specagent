"""The loop layer (harness/loops.py): one tick of a loop at a time, ticks that print one action whatever the runs root
holds, a prompt loop judged by code (docs/decisions/0022-a-prompt-loop-is-judged-by-code.md), `harness loop due`,
and the pause switch (docs/decisions/0023-one-pause-switch.md). Built on the small configuration, so a role session
runs these tests as the write gate does."""

from __future__ import annotations

import datetime as dt
import json
import shutil
import threading
import time
from pathlib import Path

import pytest
import yaml
from harness import cli, gates, launch, loops, pause, state

REPO = next(
    p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file() and (p / "schemas").is_dir()
)
BRIEF = "# Project brief — demo\n\n## Goal of this run\nNotes.\n\n## Constraints\n- Budget: 10 minutes per stage\n"
READY = {k: {"met": True, "evidence": "seen every week"} for k in
         ("repeats_weekly", "verification_is_automatic", "budget_tolerates_waste", "agent_can_run_the_check")}  # fmt: skip
NO_RUN = "no run has the status created, running, waiting_human or paused"


def loop_file(root: Path, name: str = "demo", **over) -> None:
    spec = {
        "schema_version": 1, "name": name, "enabled": True, "purpose": "A loop of this test, one pipeline run.",
        "goal": {"statement": "The demo pipeline passes its gates.", "done_when": ["every gate passes"]},
        "action": {"kind": "pipeline", "pipeline": "demo", "context": []}, "trigger": {"kind": "manual"},
        "owner": "test", "stops": {"max_iterations": 1, "max_minutes": 60, "no_progress_after": 2},
        "exit": {"success": "every gate passes", "failure": "a gate fails"}, "readiness": READY, **over,
    }  # fmt: skip
    path = root / "docs" / "loops" / f"{name}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")


PROMPT = {
    "action": {"kind": "prompt", "file": ".claude/loop.md"},
    "exit": {"success": NO_RUN, "check": "no_active_runs", "failure": "harness poll exits non-zero"},
    "stops": {"max_iterations": 50, "max_minutes": 600, "no_progress_after": 2},
}


@pytest.fixture()
def root(tmp_path, small_config, monkeypatch):
    """The small configuration with its table as the pipeline `demo`, and the poll loop's prompt file."""
    monkeypatch.setattr(state, "claude_version", lambda: "test")
    monkeypatch.delenv("HARNESS_ROLE", raising=False)  # the test is the human here, also inside a role session
    root = small_config(tmp_path / "repo")
    (root / "docs" / "roles" / "pipelines").mkdir()
    shutil.copy(root / "docs" / "roles" / "stages.yaml", root / "docs" / "roles" / "pipelines" / "demo.yaml")
    (root / ".claude").mkdir(exist_ok=True)
    (root / ".claude" / "loop.md").write_text("Run `uv run harness loop tick --name poll`.\n", encoding="utf-8")
    return root


def put_run(root: Path, name: str, doc: dict | str) -> Path:
    """A run folder with a state.json as given: a dict, or text (a cut file)."""
    run_dir = state.runs_root(root) / name
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")
    return run_dir


def loop_runs(root: Path) -> list[str]:
    return sorted(p.name for p in state.runs_root(root).glob("*-loop-demo"))


def test_two_ticks_of_one_loop_at_once_start_one_iteration(root, monkeypatch):
    """05/F30: the second tick waits for the first, then sees its iteration and starts none."""
    loop_file(root)
    real, inside, results = state.create_run, threading.Event(), {}

    def slow(*args, **kwargs):
        if threading.current_thread().name == "tick-1":
            inside.set()
            time.sleep(1.5)  # tick-2 starts here; run ids are made to the second
        return real(*args, **kwargs)

    monkeypatch.setattr(state, "create_run", slow)
    threads = {n: threading.Thread(target=lambda n=n: results.__setitem__(n, loops.tick(root, "demo")), name=n)
               for n in ("tick-1", "tick-2")}  # fmt: skip
    threads["tick-1"].start()
    assert inside.wait(30)
    threads["tick-2"].start()
    for t in threads.values():
        t.join(60)
    assert (results["tick-1"]["action"], results["tick-2"]["action"]) == ("launch", "wait")
    st = loops.load_state(root, "demo")
    assert loop_runs(root) == [results["tick-1"]["run_id"]] and st["iterations"] == 1
    assert st["last_run_id"] == results["tick-1"]["run_id"]


@pytest.mark.parametrize("damage", ["gone", "cut"])
def test_a_tick_whose_last_run_is_gone_or_unreadable_counts_it_a_failure(root, damage):
    """05/F28: one action, and the loop goes on as after a failed iteration."""
    loop_file(root, stops={"max_iterations": 2, "max_minutes": 60, "no_progress_after": 2})
    first = loops.tick(root, "demo")["run_id"]
    time.sleep(1.1)  # run ids are made to the second: the next iteration's run must not take the same folder
    if damage == "gone":
        shutil.rmtree(state.runs_root(root) / first)
    else:
        (state.runs_root(root) / first / "state.json").write_text('{"status": "do', encoding="utf-8")
    out = loops.tick(root, "demo")
    st = loops.load_state(root, "demo")
    assert out["action"] == "launch" and out["iteration"] == 2 and len(st["progress_keys"]) == 1


def test_validate_names_a_context_entry_a_tick_cannot_read_and_the_tick_ends_on_it(root):
    """05/F29: `runs:x` and a path that names nothing; the tick prints `exit` with rule `invalid`, starts nothing."""
    loop_file(root, action={"kind": "pipeline", "pipeline": "demo", "context": ["runs:x", "docs/nowhere.md", "runs:7"]})
    assert loops.validate(root)["problems"] == [
        "demo.yaml: context entry 'runs:x' is not runs:<days>",
        "demo.yaml: context entry 'docs/nowhere.md' names nothing in the repository",
    ]
    out = loops.tick(root, "demo")
    assert (out["action"], out["rule"]) == ("exit", "invalid") and "'runs:x'" in out["detail"]
    assert loop_runs(root) == [] and not (state.runs_root(root) / "_loops" / "demo" / "state.json").exists()


def test_an_entry_of_any_shape_in_the_context_is_named_and_never_raises(root):
    """The edges of a context entry: `runs:` without days or with a sign, a name longer than a file name may be, a
    path longer than a path may be, and a NUL byte are each named by validate, and the tick ends on them."""
    entries = ["runs:", "runs:-1", "x" * 300, "docs/" + "y" * 5000, "a\x00b"]
    loop_file(root, action={"kind": "pipeline", "pipeline": "demo", "context": entries})
    problems = loops.validate(root)["problems"]
    assert len(problems) == len(entries) and all(p.startswith("demo.yaml: context entry ") for p in problems)
    out = loops.tick(root, "demo")
    assert (out["action"], out["rule"]) == ("exit", "invalid") and len(out["detail"]) == 500
    assert loop_runs(root) == [] and not (state.runs_root(root) / "_loops" / "demo" / "state.json").exists()


def test_one_unreadable_state_json_never_stops_a_tick_over_past_runs(root):
    """refute#148: `runs:<days>` leaves a run it cannot read out, as leftovers does."""
    loop_file(root, action={"kind": "pipeline", "pipeline": "demo", "context": ["runs:7"]})
    done = put_run(root, "20261001-000000-done", {"status": "done", "updated_at": state.now()})
    put_run(root, "20261002-000000-cut", '{"status": "done", "updated_')
    out = loops.tick(root, "demo")
    brief = next((state.runs_root(root) / "_briefs").glob("loop-demo-*.md")).read_text(encoding="utf-8")
    assert out["action"] == "launch" and str(done) in brief and "20261002-000000-cut" not in brief


@pytest.mark.parametrize("days", ["99999999999", "9" * 5000], ids=["past_the_calendar", "past_the_digits_of_an_int"])
def test_runs_of_any_shape_and_more_days_than_the_calendar_holds_never_stop_a_tick(root, days):
    """The edges of `runs:<days>`: a state.json that holds no object, a status that is no text, and an `updated_at`
    that is missing, no date, a number or without a time zone are left out; more days than a date can go back name
    every finished run."""
    loop_file(root, action={"kind": "pipeline", "pipeline": "demo", "context": [f"runs:{days}"]})
    old = put_run(root, "20010101-000000-old", {"status": "done", "updated_at": "2001-01-01T00:00:00+00:00"})
    for name, doc in (
        ("20261002-000001-list", '["done"]'),
        ("20261002-000002-status", {"status": ["done"], "updated_at": state.now()}),
        ("20261002-000003-nodate", {"status": "done"}),
        ("20261002-000004-text", {"status": "done", "updated_at": "yesterday"}),
        ("20261002-000005-number", {"status": "done", "updated_at": 20261001}),
        ("20261002-000006-naive", {"status": "done", "updated_at": "2026-10-01T00:00:00"}),
    ):
        put_run(root, name, doc)
    out = loops.tick(root, "demo")
    brief = next((state.runs_root(root) / "_briefs").glob("loop-demo-*.md")).read_text(encoding="utf-8")
    assert out["action"] == "launch" and str(old) in brief and "20261002-" not in brief


def test_a_prompt_loop_exits_with_success_once_no_run_is_active(root):
    """7b: the exit check of a prompt loop is checked by code at every tick."""
    loop_file(root, **PROMPT)
    run_dir = put_run(root, "20261004-000000-open", {"status": "running", "updated_at": state.now()})
    assert loops.tick(root, "demo")["action"] == "prompt"
    put_run(root, run_dir.name, {"status": "done", "updated_at": state.now()})
    assert loops.tick(root, "demo") == {"ok": True, "action": "exit", "rule": "success", "detail": NO_RUN}
    st = loops.load_state(root, "demo")
    assert st["status"] == "idle" and st["last_exit"]["rule"] == "success"


def test_a_prompt_loop_ends_with_no_progress_when_its_runs_do_not_change(root):
    """7a: a prompt iteration is judged by the runs it acted on (their status and changed_at)."""
    loop_file(root, **PROMPT)
    run_dir = put_run(root, "20261004-000000-open", {"status": "running", "updated_at": state.now(), "changed_at": "1"})
    assert [loops.tick(root, "demo")["action"] for _ in range(2)] == ["prompt", "prompt"]
    put_run(root, run_dir.name, {"status": "running", "updated_at": state.now(), "changed_at": "2"})  # a change
    assert loops.tick(root, "demo")["action"] == "prompt"
    out = loops.tick(root, "demo")  # the same key twice in a row
    assert (out["action"], out["rule"]) == ("exit", "no_progress")
    assert len(loops.load_state(root, "demo")["progress_keys"]) == 2  # the last no_progress_after keys only


def test_a_prompt_loop_counts_what_its_night_sessions_cost_toward_max_usd(root):
    """7a: the spend of a prompt iteration that can be measured is the total_cost_usd of the night path's sessions."""
    loop_file(
        root, **{**PROMPT, "stops": {"max_iterations": 50, "max_minutes": 600, "no_progress_after": 9, "max_usd": 5}}
    )
    put_run(root, "20261004-000000-open", {"status": "running", "updated_at": state.now()})
    assert loops.tick(root, "demo")["action"] == "prompt"
    night = state.runs_root(root) / "_audit" / "night-tick"
    night.mkdir(parents=True)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    (night / f"demo-{stamp}.json").write_text(json.dumps({"total_cost_usd": 3.0}), encoding="utf-8")
    (night / "demo-20200101T000000Z.json").write_text(json.dumps({"total_cost_usd": 100}), encoding="utf-8")  # before
    (night / "demo-20991231T000000Z.json").write_text(json.dumps({"total_cost_usd": 2.5}), encoding="utf-8")
    (night / "demo-20991231T000001Z.json").write_text("claude: no structured output\n", encoding="utf-8")
    out = loops.tick(root, "demo")
    assert (out["action"], out["rule"], out["detail"]) == ("exit", "max_usd", "5.50")
    assert loops.load_state(root, "demo")["spent_usd"] == 5.5


def test_a_night_cost_that_is_no_cost_counts_nothing(root):
    """The edges of the night spend: a cost below zero, not a number or without end, a file that holds no object and
    a name whose time cannot be read are left out, so a tick never writes a spend the loop state refuses."""
    loop_file(
        root, **{**PROMPT, "stops": {"max_iterations": 50, "max_minutes": 600, "no_progress_after": 9, "max_usd": 5}}
    )
    put_run(root, "20261004-000000-open", {"status": "running", "updated_at": state.now()})
    assert loops.tick(root, "demo")["action"] == "prompt"
    night = state.runs_root(root) / "_audit" / "night-tick"
    night.mkdir(parents=True)
    for stamp, text in (
        ("20991231T000000Z", '{"total_cost_usd": -7}'),
        ("20991231T000001Z", '{"total_cost_usd": NaN}'),
        ("20991231T000002Z", '{"total_cost_usd": Infinity}'),
        ("20991231T000003Z", "[1.5]"),
        ("2099", '{"total_cost_usd": 1}'),
        ("20991231T000004Z", '{"total_cost_usd": 1.25}'),
    ):
        (night / f"demo-{stamp}.json").write_text(text, encoding="utf-8")
    assert loops.tick(root, "demo")["action"] == "prompt"
    assert loops.load_state(root, "demo")["spent_usd"] == 1.25


def test_a_prompt_loop_states_its_exit_check_and_the_poll_loop_does(root):
    """7b: the schema asks a prompt loop for `exit.check`; docs/loops/poll.yaml has it."""
    loop_file(root, **{**PROMPT, "exit": {"success": NO_RUN, "failure": "never"}})
    problems = loops.validate(root)["problems"]
    assert len(problems) == 1 and "'check' is a required property" in problems[0]
    (root / "docs" / "loops" / "demo.yaml").unlink()
    shutil.copy(REPO / "docs" / "loops" / "poll.yaml", root / "docs" / "loops" / "poll.yaml")
    assert loops.validate(root) == {"ok": True, "problems": []}
    assert loops.load_loop(root, "poll")["exit"]["check"] == "no_active_runs"


def test_a_paused_tick_waits_and_leaves_the_loop_state_as_it_is(root):
    """Item 8: no loop iteration starts while the switch is set, and the state stays as it is."""
    loop_file(root, stops={"max_iterations": 3, "max_minutes": 60, "no_progress_after": 2})
    loops.tick(root, "demo")
    path = state.runs_root(root) / "_loops" / "demo" / "state.json"
    before = path.read_bytes()
    assert pause.set_flag(root, "the human is away")["ok"]
    out = loops.tick(root, "demo")
    assert out["action"] == "wait" and out["paused"]["reason"] == "the human is away"
    assert path.read_bytes() == before and len(loop_runs(root)) == 1
    assert pause.lift(root)["lifted"] and loops.tick(root, "demo")["action"] == "wait"  # its run is still active


def a_run(root: Path, unit: dict) -> tuple[str, Path]:
    """A run of the small configuration whose read stage is as `unit` says."""
    brief = root.parent / "brief.md"
    brief.write_text(BRIEF, encoding="utf-8")
    run_id = state.create_run(root, "demo", brief, [])["run_id"]
    run_dir = state.runs_root(root) / run_id
    st = state.load(root, run_dir / "state.json", "run-state")
    st["stages"]["read"].update(unit)
    state.save(root, run_dir / "state.json", st, "run-state")
    return run_id, run_dir


LAUNCHED = {"status": "launched", "attempts": 1, "session_ids": ["s1"], "job_ids": ["j1"]}


def test_loop_due_is_no_tick_and_says_when_a_night_session_has_something_to_do(root, monkeypatch):
    """7c/7d: decided without a model and without a tick; due only when poll left the manager something to do."""
    loop_file(root, name="poll", **PROMPT)
    assert loops.due(root, "poll") == {"ok": False, "due": False, "why": "success", "detail": NO_RUN}
    a_run(root, {**LAUNCHED, "started_at": state.now()})
    monkeypatch.setattr(
        launch, "listing", lambda root: [{"id": "j1", "sessionId": "s1", "state": "working", "status": "busy"}]
    )
    assert loops.due(root, "poll") == {"ok": False, "due": False, "why": "nothing for the manager", "actions": []}
    monkeypatch.setattr(launch, "listing", lambda root: [])  # the session is gone: poll prints `resume`
    out = loops.due(root, "poll")
    assert out == {"ok": True, "due": True, "actions": ["resume"],
                   "message": "Read `.claude/loop.md` and do exactly what it says in this turn."}  # fmt: skip
    assert not (state.runs_root(root) / "_loops" / "poll" / "state.json").exists()  # no tick
    assert pause.set_flag(root, "away")["ok"] and loops.due(root, "poll")["why"] == "paused"


def test_loop_due_hands_a_passed_gate_to_the_session_and_names_the_skill_for_other_loops(root, monkeypatch):
    loop_file(root, name="poll", **PROMPT)
    loop_file(root, name="demo")
    a_run(root, {**LAUNCHED, "started_at": state.now()})
    monkeypatch.setattr(launch, "listing", lambda root: [{"id": "j1", "sessionId": "s1", "state": "done"}])
    monkeypatch.setattr(gates, "run_gate", lambda *a, **k: {"passed": True, "next": "advance"})
    out = loops.due(root, "poll")
    assert out["due"] and out["actions"] == ["gate"]
    assert '"action": "gate", "stage": "read", "next": "advance"' in out["message"]  # a later poll prints it no more
    assert loops.due(root, "demo") == {"ok": True, "due": True, "message": "/loop-tick demo"}


@pytest.mark.parametrize("action", ["rework", "recheck"])
def test_loop_due_hands_a_round_of_a_loop_to_the_session(root, monkeypatch, action):
    """specs/002-run-loop: a unit a loop sent back is the manager's to resume, also at night."""
    loop_file(root, name="poll", **PROMPT)
    run_id, _ = a_run(root, {**LAUNCHED, "started_at": state.now()})
    printed = {"ok": True, "run_id": run_id, "status": "running", "actions": [{"action": action, "stage": "read"}]}
    monkeypatch.setattr(loops.poll, "poll_all", lambda root: {"ok": True, "runs": [printed], "unreadable": []})
    out = loops.due(root, "poll")
    assert out["due"] and out["actions"] == [action]


def test_a_disabled_unready_invalid_or_ci_loop_is_never_due(root):
    """The other answers of `harness loop due` that start no night session, none of them a tick."""
    loop_file(root, name="off", enabled=False)
    loop_file(root, name="unready", readiness={**READY, "repeats_weekly": {"met": False, "evidence": "rarely so"}})
    loop_file(root, name="invalid", action={"kind": "pipeline", "pipeline": "demo", "context": ["runs:x"]})
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "x.yml").write_text("on: push\n", encoding="utf-8")
    loop_file(root, name="ci", action={"kind": "ci", "file": ".github/workflows/x.yml"})
    assert loops.due(root, "off") == {"ok": False, "due": False, "why": "disabled"}
    assert loops.due(root, "unready") == {"ok": False, "due": False, "why": "not_ready", "detail": "repeats_weekly"}
    assert loops.due(root, "invalid") == {
        "ok": False, "due": False, "why": "invalid", "detail": "context entry 'runs:x' is not runs:<days>",
    }  # fmt: skip
    assert loops.due(root, "ci") == {"ok": False, "due": False, "why": "external"}
    assert not (state.runs_root(root) / "_loops").exists()  # no tick, no loop state


def test_the_cli_prints_the_night_message_alone_or_why_there_is_none(root, monkeypatch, capsys):
    loop_file(root, name="poll", **PROMPT)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    capsys.readouterr()
    assert cli.main(["loop", "due", "--name", "poll", "--plain"]) == 1
    assert json.loads(capsys.readouterr().out) == {"ok": False, "due": False, "why": "success", "detail": NO_RUN}
    loop_file(root, name="demo")
    assert cli.main(["loop", "due", "--name", "demo", "--plain"]) == 0
    assert capsys.readouterr().out == "/loop-tick demo\n"


def test_the_cli_asks_for_the_name_of_the_loop_it_is_due_for(root, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    with pytest.raises(SystemExit) as stop:
        cli.main(["loop", "due", "--plain"])
    assert stop.value.code == 2 and "loop due needs --name" in capsys.readouterr().err


def test_the_pause_switch_is_set_and_lifted_by_the_human_only(root, monkeypatch, capsys):
    """Item 8: with HARNESS_ROLE set, setting and lifting the switch are refused and the flag stays as it was."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.setenv("HARNESS_ROLE", "writer")
    assert cli.main(["pause", "set", "--reason", "a writer tidying up"]) == 1 and pause.current(root) is None
    monkeypatch.delenv("HARNESS_ROLE")
    assert cli.main(["pause", "set", "--reason", "the human is away"]) == 0
    capsys.readouterr()
    assert cli.main(["pause", "status"]) == 0
    assert json.loads(capsys.readouterr().out)["paused"]["reason"] == "the human is away"
    monkeypatch.setenv("HARNESS_ROLE", "writer")
    assert cli.main(["pause", "lift"]) == 1 and pause.current(root)["reason"] == "the human is away"
    monkeypatch.delenv("HARNESS_ROLE")
    assert cli.main(["pause", "lift"]) == 0 and pause.current(root) is None


def test_the_cli_asks_the_pause_switch_for_the_human_s_words(root, monkeypatch, capsys):
    """`pause set` without a reason stops at the parser; a blank reason sets nothing; a lift with nothing set says so."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    with pytest.raises(SystemExit) as stop:
        cli.main(["pause", "set"])
    assert stop.value.code == 2 and "pause set needs --reason" in capsys.readouterr().err
    assert cli.main(["pause", "set", "--reason", "   "]) == 1 and pause.current(root) is None
    assert json.loads(capsys.readouterr().out)["status"] == "no_reason"
    assert cli.main(["pause", "lift"]) == 0 and json.loads(capsys.readouterr().out)["lifted"] is False
