"""surface.py: the owner's surface (need 2, need 7, answer 11a). One line for the run, one per role, then the usage
reading, the hand-over orders past the cap, the free disk and the monitor's open alarms, rendered from the control files
by fixed phrases; the run's cost is the total row of usage_report.py (10.18). The run folder is built in tmp_path and the
stub `claude` of transcript_home answers `agents --json --all`; no session starts. The expected lines are written out by
hand from the fixtures."""

import datetime
import importlib.util
import json
import pathlib
import re
import string
import sys
from types import SimpleNamespace

import pytest
from transcript_home import SCRIPTS, TEXT, Home

sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("surface", SCRIPTS / "manager" / "surface.py")
surface = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = surface
SPEC.loader.exec_module(surface)
PRICES = importlib.util.spec_from_file_location("usage_report_prices", SCRIPTS / "usage_report.py")
usage_report = importlib.util.module_from_spec(PRICES)
PRICES.loader.exec_module(usage_report)

NOW = "2026-10-29T21:00:30Z"
FIELDS = {
    "run": {"run", "written_at", "cost", "budget", "pct", "running", "roles", "elapsed", "record"},
    "run_unbudgeted": {"run", "written_at", "cost", "running", "roles", "elapsed", "record"},
    "role": {"role", "state", "unit", "unit_elapsed", "context", "cost", "waiting", "record"},
    "usage": {"taken_at", "limits", "next_reset", "record"},
    "usage_missing": {"now", "record"},
    "limit": {"name", "used_pct", "resets_at"},
    "caps": {"count", "role", "at", "record"},
    "caps_none": {"count", "record"},
    "disk": {"free_mb", "record"},
    "alarm": {"kind", "since", "text", "record"},
    "duration": {"h", "mm"},
    "none": set(),
    "state_running": set(),
    "state_stopped": set(),
    "state_blocked": set(),
    "state_done": set(),
}
FREE = 348 * 1048576 + 1047552  # 348 MiB and 1023 KiB: 348 floored, 349 rounded, 365 in millions of bytes
GEO = "".join(
    chr(c) for c in (0x10E1, 0x10E2, 0x10D0, 0x10E2, 0x10E3, 0x10E1, 0x10D8)
)  # a word of the refused blocks (D1)
GEORGIAN = re.compile(f"[{chr(0x10A0)}-{chr(0x10FF)}{chr(0x1C90)}-{chr(0x1CBF)}{chr(0x2D00)}-{chr(0x2D2F)}]")
OVERDUE = "overdue build-log-a.md:SANDBOX:1 SANDBOX build-log-a.md:3: open 16 min, bound 15 min"
MERGE = "merge-check Merged: a->b at 1234567 is no ancestor of feat/demo-b"
JSON_ERROR = "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"


@pytest.fixture(autouse=True)
def disk(monkeypatch):
    """The free disk is FREE wherever the surface asks; the folders it asked for are returned."""
    asked = []

    def usage(path):
        asked.append(pathlib.Path(path))
        return SimpleNamespace(total=4 * FREE, used=3 * FREE, free=FREE)

    monkeypatch.setattr(surface.shutil, "disk_usage", usage)
    return asked


def order(msg_id, kind, sent_at):
    return {
        "msg_id": msg_id,
        "kind": kind,
        "text": "...",
        "sent_at": sent_at,
        "resends": 0,
        "acked_at": None,
        "closed": None,
    }


def agent(run, role, record, **given):
    """A registry entry in the shape of Task 2's K1; `given` sets the fields the surface reads. The record file's line 1
    is older than the registry's `unit`, which the surface shows."""
    entry = {
        "role": role,
        "lane": None,
        "settings": f"_control/{role}-settings.json",
        "record": str(run / record),
        "unit": None,
        "unit_since": None,
        "state": "stopped",
        "row_state": None,
        "waiting_for": None,
        "job_id": None,
        "session_id": None,
        "session_ids": [],
        "launched_at": None,
        "context": None,
        "calls": 0,
        "cost_usd": 0.0,
        "revivals": 0,
        "handoff_since": None,
        "orders": [],
    }
    entry.update(given)
    (run / record).write_text("STATUS: an older line\n", encoding="utf-8")
    return entry


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def registry(run, roles):
    return {
        "version": 1,
        "run_dir": str(run),
        "written_at": "2026-10-29T20:59:00Z",
        "watcher": {"pid": 4242, "started_at": "2026-10-29T20:30:00Z", "round": 7, "interval": 120},
        "roles": roles,
    }


def full_roles(run):
    """The three roles of `full_run`, not in alphabetical order; `agent` writes each role's record file."""
    return {
        "demo/planner": agent(
            run,
            "planner",
            "planner-log.md",
            unit="STATUS: writing Task 3",
            unit_since="2026-10-29T19:55:00Z",
            state="running",
            launched_at="2026-10-29T20:34:00Z",
            context=61234,
            cost_usd=3.141593,
            orders=[
                order("c0ffee01", "handoff", "2026-10-29T20:40:00Z"),
                order("c0ffee02", "reload", "2026-10-29T20:50:00Z"),
                order("c0ffee03", "manager", "2026-10-29T20:55:00Z"),
            ],
        ),
        "demo/builder-a": agent(
            run,
            "builder-a",
            "build-log-a.md",
            state="blocked",
            waiting_for="permission",
            launched_at="2026-10-29T20:05:10Z",
            context=1234567,
            cost_usd=12.5,
            orders=[order("0badf00d", "unit-end", "2026-10-29T20:10:00Z")],
        ),
        "demo/critic": agent(
            run,
            "critic",
            "critique.md",
            unit="STATUS: through 2",
            unit_since="2026-10-29T21:00:59Z",
            state="done",
            cost_usd=0.004999,
        ),
    }


def full_usage():
    """Two usage readings, the newer one first."""
    return {
        "readings": [
            {
                "taken_at": "2026-10-29T20:30Z",
                "source": "get_usage",
                "extra_usage": False,
                "limits": [
                    {"name": "weekly", "used_pct": 17, "resets_at": "2026-11-02T08:00Z"},
                    {"name": "opus-weekly", "used_pct": 33.5, "resets_at": "2026-10-29T20:00Z"},
                    {"name": "five-hour", "used_pct": 42.0, "resets_at": "2026-10-29T23:40Z"},
                ],
            },
            {
                "taken_at": "2026-10-29T19:10Z",
                "source": "get_usage",
                "extra_usage": False,
                "limits": [{"name": "five-hour", "used_pct": 5, "resets_at": "2026-10-29T21:00Z"}],
            },
        ]
    }


def full_alarms():
    """Three alarms, the second one closed."""
    alarms = [
        {"id": "overdue:build-log-a.md:SANDBOX:1", "kind": "overdue", "text": OVERDUE, "since": "2026-10-29T20:44:00Z"},
        {"id": "claim-race:3", "kind": "claim-race", "text": "claim race Task 3", "since": "2026-10-29T20:20:00Z"},
        {"id": "merge-check:a->b", "kind": "merge-check", "text": MERGE, "since": "2026-10-29T20:58:00Z"},
    ]
    for alarm, is_open in zip(alarms, (True, False, True), strict=True):
        alarm["open"] = is_open
    return alarms


def full_run(root):
    """Three roles, not in alphabetical order; two usage readings, the newer one first; three alarms, one closed; a `$`
    figure on the `Estimate:` line above the `Budget:` line."""
    run = root / "demo-run"
    run.mkdir(parents=True)
    write_json(run / "_control" / "registry.json", registry(run, full_roles(run)))
    write_json(run / "_control" / "usage.json", full_usage())
    write_json(run / "_control" / "monitor.json", {"watch": None, "requests": [], "alarms": full_alarms()})
    (run / "_launch.md").write_text(
        (
            "Purpose: demo\nEstimate: $99 for three sessions\n"
            "Budget: $40 for the run; at $40 the manager launches nothing new and asks the owner\n"
        ),
        encoding="utf-8",
    )
    return run


def full_lines(run, cost, pct):
    r, u, m = (run / "_control" / name for name in ("registry.json", "usage.json", "monitor.json"))
    return [
        (
            f"Run demo-run as of 2026-10-29T20:59:00Z: cost ${cost} of the $40 budget ({pct}%), 1 of 3 roles running, "
            f"elapsed 0h55m. Record: {r}"
        ),
        (
            f'planner: running, unit "STATUS: writing Task 3" for 1h05m, context 61,234 tokens, cost $3.14, waiting for '
            f"none. Record: {run / 'planner-log.md'}"
        ),
        (
            f'builder-a: blocked, unit "none" for none, context 1,234,567 tokens, cost $12.50, waiting for permission. '
            f"Record: {run / 'build-log-a.md'}"
        ),
        (
            f'critic: done, unit "STATUS: through 2" for 0h00m, context none tokens, cost $0.00, waiting for none. '
            f"Record: {run / 'critique.md'}"
        ),
        (
            "Usage read at 2026-10-29T20:30Z: weekly 17% until 2026-11-02T08:00Z, opus-weekly 33.5% until "
            f"2026-10-29T20:00Z, five-hour 42% until 2026-10-29T23:40Z; next reset 2026-10-29T23:40Z. Record: {u}"
        ),
        f"Cap events: 2 hand-over orders, the last for planner at 2026-10-29T20:40:00Z. Record: {r}",
        f"Free disk at {run}: 348 MB.",
        f"Alarm overdue since 2026-10-29T20:44:00Z: {OVERDUE}. Record: {m}",
        f"Alarm merge-check since 2026-10-29T20:58:00Z: {MERGE}. Record: {m}",
    ]


def bare_run(root, variant):
    """One role, no order; either no optional file at all or files that carry no figure."""
    run = root / "demo-run"
    run.mkdir(parents=True)
    roles = {
        "demo/planner": agent(
            run,
            "planner",
            "planner-log.md",
            unit="STATUS: reading",
            unit_since="2026-10-29T20:58:10Z",
            state="running",
            context=0,
        )
    }
    write_json(run / "_control" / "registry.json", registry(run, roles))
    if variant == "files without figures":
        (run / "_launch.md").write_text("Budget: 300 calls and 4000000 output tokens per session\n", encoding="utf-8")
        write_json(run / "_control" / "usage.json", {"readings": []})
        closed = {"id": "x", "kind": "overdue", "text": "old", "since": "2026-10-29T20:00:00Z", "open": False}
        write_json(run / "_control" / "monitor.json", {"alarms": [closed]})
    return run


def bare_lines(run):
    r = run / "_control" / "registry.json"
    return [
        (
            "Run demo-run as of 2026-10-29T20:59:00Z: cost $0.00, no $ budget on the Budget: line of _launch.md, 1 of 1 "
            f"roles running, elapsed none. Record: {r}"
        ),
        (
            'planner: running, unit "STATUS: reading" for 0h02m, context 0 tokens, cost $0.00, waiting for none. '
            f"Record: {run / 'planner-log.md'}"
        ),
        (
            "No usage reading at 2026-10-29T21:00:30Z: the manager writes _control/usage.json before each launch. "
            f"Record: {run / '_control' / 'usage.json'}"
        ),
        f"Cap events: 0 hand-over orders. Record: {r}",
        f"Free disk at {run}: 348 MB.",
    ]


def georgian(root):
    """The shipped phrases with a word of the refused blocks before each, as the owner's own file translates them (D1)."""
    shipped = json.loads(surface.DEFAULT_PHRASES.read_text(encoding="utf-8"))
    path = root / "surface-phrases.ka.json"
    path.write_text(json.dumps({k: f"{GEO} {v}" for k, v in shipped.items()}, ensure_ascii=False), encoding="utf-8")
    return path


def rekey(run, old, new):
    path = run / "_control" / "registry.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["roles"][new] = data["roles"].pop(old)
    path.write_text(json.dumps(data), encoding="utf-8")


CALLS = {  # session -> (name, start, calls as (context, output tokens))
    "aaaa1111-0000-4000-8000-000000000001": (
        "demo/planner",
        "2026-10-29T20:35:00",
        [(1_000_010, 2000), (500_010, 1000)],
    ),
    "bbbb2222-0000-4000-8000-000000000002": ("demo/critic", "2026-10-29T20:40:00", [(200_010, 300)]),
    "cccc3333-0000-4000-8000-000000000003": ("demo/old", "2026-10-28T09:00:00", [(900_010, 9000)]),
    "dddd4444-0000-4000-8000-000000000004": ("other/x", "2026-10-29T10:00:00", [(800_010, 8000)]),
}


def total(*sids):
    """The cost of these sessions' calls at usage_report's prices (Task 10 may change them), as its total row prints it:
    each call is input 3, cache write 7, cache read context - 10 (transcript_home), on an Opus model."""
    p = usage_report.PRICE[usage_report.family("claude-opus-5-5")]
    calls = [call for sid in sids for call in CALLS[sid][2]]
    return f"{sum((3 * p[0] + out * p[1] + (ctx - 10) * p[2] + 7 * p[3]) / 1e6 for ctx, out in calls):.2f}"


RUN_DAY = ("aaaa1111-0000-4000-8000-000000000001", "bbbb2222-0000-4000-8000-000000000002")


@pytest.fixture
def home(tmp_path, monkeypatch):
    """The run's two sessions on its day, a session under its prefix a day earlier, one under another prefix."""
    home = Home(tmp_path / "home-root")
    for sid, (name, start, calls) in CALLS.items():
        home.session(name, sid, [(ctx, out, [TEXT]) for ctx, out in calls], start=start)
    for key in ("PATH", "HOME", "STUB_DIR"):
        monkeypatch.setenv(key, home.env()[key])
    return home


def test_the_shipped_phrases_use_exactly_the_fields_of_each_phrase():
    assert list(surface.FIELDS) == list(FIELDS)
    assert {key: set(names) for key, names in surface.FIELDS.items()} == FIELDS
    assert surface.DEFAULT_PHRASES == SCRIPTS.parent / "example" / "surface-phrases.en.json"
    phrases = surface.load_phrases(surface.DEFAULT_PHRASES)
    assert set(phrases) == set(FIELDS)
    for key, text in phrases.items():
        assert {name for _, name, _, _ in string.Formatter().parse(text) if name is not None} == FIELDS[key], key
    assert not GEORGIAN.search(surface.DEFAULT_PHRASES.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda p: p.pop("disk"), 'missing phrase "disk"'),
        (lambda p: p.update(extra="x"), 'unknown phrase "extra"'),
        (lambda p: p.update(none=0), 'phrase "none" is not a string'),
        (
            lambda p: p.update(role=p["role"].replace(", cost ${cost}", "")),
            (
                'phrase "role" uses {context, record, role, state, unit, unit_elapsed, waiting}, '
                "expected {context, cost, record, role, state, unit, unit_elapsed, waiting}"
            ),
        ),
        (
            lambda p: p.update(caps_none=p["caps_none"] + " {now}"),
            'phrase "caps_none" uses {count, now, record}, expected {count, record}',
        ),
    ],
    ids=["missing", "unknown", "not a string", "a field lost", "a field gained"],
)
def test_a_phrase_file_that_loses_or_gains_a_phrase_or_a_field_is_refused(tmp_path, change, message):
    phrases = json.loads(surface.DEFAULT_PHRASES.read_text(encoding="utf-8"))
    change(phrases)
    path = tmp_path / "phrases.json"
    path.write_text(json.dumps(phrases), encoding="utf-8")
    with pytest.raises(surface.SurfaceError) as caught:
        surface.load_phrases(path)
    assert str(caught.value) == f"{path}: {message}"


def test_parse_time_reads_both_forms_as_utc():
    assert surface.parse_time("2026-10-29T21:00:30Z") == datetime.datetime(2026, 10, 29, 21, 0, 30, tzinfo=datetime.UTC)
    assert surface.parse_time("2026-10-29T23:40Z") == datetime.datetime(2026, 10, 29, 23, 40, tzinfo=datetime.UTC)
    with pytest.raises(ValueError):
        surface.parse_time("2026-10-29 21:00")


def test_the_lines_carry_the_roles_the_usage_reading_the_cap_events_the_disk_and_the_open_alarms(tmp_path, disk):
    run = full_run(tmp_path)
    lines = surface.render(run, surface.load_phrases(surface.DEFAULT_PHRASES), surface.parse_time(NOW), "12.34")
    assert lines == full_lines(run, "12.34", "31")
    assert disk == [run]


@pytest.mark.parametrize("variant", ["no optional file", "files without figures"])
def test_without_a_budget_a_reading_an_order_or_an_open_alarm_the_lines_say_so(tmp_path, variant):
    run = bare_run(tmp_path, variant)
    lines = surface.render(run, surface.load_phrases(surface.DEFAULT_PHRASES), surface.parse_time(NOW), "0.00")
    assert lines == bare_lines(run)


@pytest.mark.parametrize("language", ["english", "georgian"])
def test_every_line_has_a_digit_besides_its_record_path(tmp_path, language):  # 10.18
    phrases = surface.DEFAULT_PHRASES if language == "english" else georgian(tmp_path)
    for name in ("full", "bare"):
        run = full_run(tmp_path / name) if name == "full" else bare_run(tmp_path / name, "no optional file")
        roles = json.loads((run / "_control" / "registry.json").read_text(encoding="utf-8"))["roles"]
        files = ("registry.json", "usage.json", "monitor.json")
        records = [str(run), *(str(run / "_control" / f) for f in files), *(r["record"] for r in roles.values())]
        records.sort(key=len, reverse=True)
        for line in surface.render(run, surface.load_phrases(phrases), surface.parse_time(NOW), "0.41"):
            assert any(record in line for record in records), line
            rest = line
            for record in records:
                rest = rest.replace(record, "")
            assert re.search(r"\d", rest), line


def test_a_georgian_phrase_file_changes_the_words_and_keeps_unit_context_and_cost(tmp_path):  # 10.6
    run = full_run(tmp_path)
    now = surface.parse_time(NOW)
    english = surface.render(run, surface.load_phrases(surface.DEFAULT_PHRASES), now, "12.34")
    translated = surface.render(run, surface.load_phrases(georgian(tmp_path)), now, "12.34")
    assert len(translated) == len(english) == 9
    assert all(GEORGIAN.search(line) for line in translated)
    for en, ka in zip(english[1:4], translated[1:4], strict=True):
        unit = re.search(r'unit "([^"]*)"', en).group(1)
        context = re.search(r"context (\S+) tokens", en).group(1)
        cost = re.search(r"cost \$(\S+),", en).group(1)
        assert [unit in ka, context in ka, f"${cost}" in ka] == [True, True, True], ka
    assert "$12.34" in translated[0]
    inner = [(1, f"{GEO} running"), (1, f"{GEO} 1h05m"), (2, f"{GEO} none"), (4, f"{GEO} weekly 17% until")]
    assert [word in translated[i] for i, word in inner] == [True] * 4  # the inner phrases are translated too


def test_the_run_cost_is_the_total_row_of_usage_report_for_the_prefix_and_the_day(home):  # 10.18
    printed = home.run("usage_report.py", "--prefix", "demo/", "--since", "2026-10-29").stdout.splitlines()
    assert surface.run_cost("demo/", "2026-10-29") == printed[-1].split()[-1] == total(*RUN_DAY)
    assert surface.run_cost("demo/", None) == total(*RUN_DAY, "cccc3333-0000-4000-8000-000000000003")
    assert home.claude_calls() == ["agents --json --all"] * 3


def test_the_run_cost_refuses_when_usage_report_fails_hangs_or_prints_no_total(home, tmp_path, monkeypatch):
    (home.stub / "agents.json").unlink()  # the stub's `agents --json --all` fails, and so does usage_report.py
    with pytest.raises(surface.SurfaceError) as caught:
        surface.run_cost("demo/", None)
    assert str(caught.value) == (
        "usage_report.py failed (exit 1): subprocess.CalledProcessError: Command "
        "'['claude', 'agents', '--json', '--all']' returned non-zero exit status 1."
    )
    silent = tmp_path / "silent.py"
    silent.write_text("print('agent day sess calls')\n", encoding="utf-8")
    monkeypatch.setattr(surface, "USAGE_REPORT", silent)
    with pytest.raises(surface.SurfaceError) as caught:
        surface.run_cost("demo/", None)
    assert str(caught.value) == "usage_report.py printed no total row"
    slow = tmp_path / "slow.py"
    slow.write_text("import time\ntime.sleep(10)\n", encoding="utf-8")
    monkeypatch.setattr(surface, "USAGE_REPORT", slow)
    with pytest.raises(surface.SurfaceError) as caught:
        surface.run_cost("demo/", None, timeout=0.5)
    assert str(caught.value) == "usage_report.py did not finish in 0.5 s"


def test_main_prints_the_lines_and_writes_the_same_text_to_out(home, tmp_path, capsys):  # 10.6
    run = full_run(tmp_path)
    out = run / "_control" / "surface.txt"
    assert surface.main([str(run), "--now", NOW, "--out", str(out)]) == 0
    printed = capsys.readouterr().out
    cost = total(*RUN_DAY)  # --prefix demo/ from the registry's keys, --since 2026-10-29 from builder-a's launched_at
    assert printed == "\n".join(full_lines(run, cost, round(float(cost) / 40 * 100))) + "\n"
    assert out.read_text(encoding="utf-8") == printed  # the manager quotes what the owner's file holds


def test_main_every_writes_each_round_and_sleeps_only_between_rounds(home, tmp_path, capsys, monkeypatch):
    run = full_run(tmp_path)
    out = run / "_control" / "surface.txt"
    slept = []

    def sleep(seconds):
        slept.append(seconds)
        path = run / "_control" / "registry.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["roles"]["demo/planner"]["unit"] = "STATUS: writing Task 4"
        path.write_text(json.dumps(data), encoding="utf-8")

    monkeypatch.setattr(surface.time, "sleep", sleep)
    assert surface.main([str(run), "--now", NOW, "--out", str(out), "--every", "60", "--rounds", "2"]) == 0
    assert slept == [60]
    assert out.read_text(encoding="utf-8").splitlines()[1].startswith('planner: running, unit "STATUS: writing Task 4"')
    assert not out.with_name("surface.txt.tmp").exists()
    assert capsys.readouterr().out == ""


def broken(name):
    return lambda run: (run / "_control" / name).write_text("{", encoding="utf-8")


REFUSALS = {  # case -> (change to the full run, argv after the run folder, message)
    "no run folder": (None, None, "no run folder at {run}-gone"),
    "no registry": (
        lambda run: (run / "_control" / "registry.json").unlink(),
        [],
        "no registry at {run}/_control/registry.json",
    ),
    "registry": (broken("registry.json"), [], "{run}/_control/registry.json does not parse: " + JSON_ERROR),
    "registry outside the run": (
        lambda run: write_json(run / "_control" / "_agents.json", {"registry": "../x.json"}),
        [],
        "registry ../x.json leaves run_dir",
    ),
    "config": (broken("_agents.json"), [], "{run}/_control/_agents.json does not parse: " + JSON_ERROR),
    "config whose registry is no path": (
        lambda run: write_json(run / "_control" / "_agents.json", {"registry": 5}),
        [],
        '{run}/_control/_agents.json does not parse: "registry" is no path',
    ),
    "named config missing": (None, ["--config", "{run}/_control/none.json"], "no config at {run}/_control/none.json"),
    "usage": (broken("usage.json"), [], "{run}/_control/usage.json does not parse: " + JSON_ERROR),
    "monitor": (broken("monitor.json"), [], "{run}/_control/monitor.json does not parse: " + JSON_ERROR),
    "phrases": (
        lambda run: (run / "ka.json").write_text("{", encoding="utf-8"),
        ["--phrases", "{run}/ka.json"],
        "{run}/ka.json does not parse: " + JSON_ERROR,
    ),
    "launched": (
        lambda run: (run / "_launch.md").write_text("Launched: 2026-10-29 20:00\n", encoding="utf-8"),
        [],
        "{run}/_launch.md does not parse: not a UTC time: '2026-10-29 20:00'",
    ),
    "every without out": (None, ["--every", "60"], "--every needs --out"),
    "two prefixes": (
        lambda run: rekey(run, "demo/critic", "other/critic"),
        [],
        "the agents share no prefix; pass --prefix",
    ),
    "a name without a prefix": (
        lambda run: rekey(run, "demo/critic", "critic"),
        [],
        "the agents share no prefix; pass --prefix",
    ),
}


@pytest.mark.parametrize("case", list(REFUSALS))
def test_main_refuses_with_exit_2_and_one_line(home, tmp_path, capsys, monkeypatch, case):
    monkeypatch.setattr(surface.time, "sleep", lambda seconds: pytest.fail("a refused run never sleeps"))
    change, argv, message = REFUSALS[case]
    run = full_run(tmp_path)
    if change:
        change(run)
    folder = f"{run}-gone" if argv is None else str(run)
    args = [folder, "--now", NOW, *(a.replace("{run}", str(run)) for a in argv or [])]
    assert surface.main(args) == 2
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", f"surface: {message.replace('{run}', str(run))}\n")


def test_main_passes_an_explicit_prefix_and_day_to_usage_report(home, tmp_path, capsys):
    run = full_run(tmp_path)
    rekey(run, "demo/critic", "other/critic")
    assert surface.main([str(run), "--now", NOW, "--prefix", "demo/", "--since", "2026-10-28"]) == 0
    cost = total(*RUN_DAY, "cccc3333-0000-4000-8000-000000000003")
    assert capsys.readouterr().out.splitlines()[0].startswith(f"Run demo-run as of 2026-10-29T20:59:00Z: cost ${cost} ")


def test_the_run_starts_at_the_launched_line_when_every_role_relaunched_after_midnight(home, tmp_path, capsys):
    run = full_run(tmp_path)  # C17, A7: a relaunch resets launched_at (task-02.md K6), the Launched: line stays
    launch = run / "_launch.md"
    launch.write_text("Launched: 2026-10-29T20:00:00Z\n" + launch.read_text(encoding="utf-8"), encoding="utf-8")
    path = run / "_control" / "registry.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for role in data["roles"].values():
        role["launched_at"] = "2026-10-30T00:10:00Z"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert surface.main([str(run), "--now", "2026-10-30T01:00:00Z"]) == 0
    cost = total(*RUN_DAY)  # --since 2026-10-29 from the Launched: line; 2026-10-30 would drop both sessions
    assert capsys.readouterr().out.splitlines()[0] == (
        f"Run demo-run as of 2026-10-29T20:59:00Z: cost ${cost} of the $40 budget ({round(float(cost) / 40 * 100)}%), "
        f"1 of 3 roles running, elapsed 5h00m. Record: {run / '_control' / 'registry.json'}"
    )


def test_check_phrases_passes_the_shipped_file_and_refuses_a_broken_one(tmp_path, capsys):
    assert surface.main(["--check-phrases", str(surface.DEFAULT_PHRASES)]) == 0
    assert capsys.readouterr().out == f"phrases ok: 16 phrases in {surface.DEFAULT_PHRASES}\n"
    path = georgian(tmp_path)
    assert surface.main(["--check-phrases", str(path)]) == 0
    assert capsys.readouterr().out == f"phrases ok: 16 phrases in {path}\n"
    path.write_text("{", encoding="utf-8")
    assert surface.main(["--check-phrases", str(path)]) == 2
    assert capsys.readouterr().err == f"surface: {path} does not parse: {JSON_ERROR}\n"
    with pytest.raises(SystemExit) as caught:
        surface.main([])
    assert caught.value.code == 2


def test_an_unsent_cap_order_counts_and_the_latest_sent_one_gives_role_and_time(home, tmp_path, capsys):  # R501
    # The watcher writes each order with "sent_at": null until it sends it, and launch_fresh closes an unsent one as
    # superseded (watch_agents.py add_order, launch_fresh); the registry keeps it for the rest of the run.
    run = tmp_path / "demo-run"
    run.mkdir()
    sent = order("0a0a0a0a", "handoff", "2026-10-30T00:50:00Z")
    unsent = {**order("0b0b0b0b", "unit-end", None), "closed": "superseded"}
    roles = {
        "demo/builder-a": agent(run, "builder-a", "build-log-a.md", orders=[sent]),
        "demo/builder-b": agent(run, "builder-b", "build-log-b.md", orders=[unsent]),
    }
    r = run / "_control" / "registry.json"
    args = [str(run), "--now", "2026-10-30T01:00:00Z", "--prefix", "demo/", "--since", "2026-10-29"]
    for kept, caps in (
        (("demo/builder-a", "demo/builder-b"), "2 hand-over orders, the last for builder-a at 2026-10-30T00:50:00Z"),
        (("demo/builder-b",), "1 hand-over orders, the last for builder-b at none"),
    ):
        write_json(r, registry(run, {name: roles[name] for name in kept}))
        assert surface.main(args) == 0
        captured = capsys.readouterr()
        assert captured.err == ""
        assert f"Cap events: {caps}. Record: {r}" in captured.out.splitlines()


@pytest.mark.parametrize(
    "config, argv, registry",
    [
        ("_agents.json", [], "_control/reg2.json"),
        ("_agents-judge.json", ["--config", "{run}/_control/_agents-judge.json"], "_control/reg2.json"),
        ("_agents.json", [], None),
    ],
    ids=["default-config", "named-config", "no-registry-key"],
)
def test_surface_reads_the_registry_at_the_path_its_config_names(home, tmp_path, capsys, config, argv, registry):
    """J9 (judge.md of manager-build-2026-10-29, #### J9): surface.py read the registry only at
    `_control/registry.json`, while the watcher's documented `registry` field can put it anywhere in the run folder."""
    run = full_run(tmp_path)
    old = run / "_control" / "registry.json"
    new = run / registry if registry else old
    old.rename(new)
    write_json(
        run / "_control" / config, {"run_dir": str(run), "agents": {}, **({"registry": registry} if registry else {})}
    )
    assert surface.main([str(run), "--now", NOW, *(a.replace("{run}", str(run)) for a in argv)]) == 0
    cost = total(*RUN_DAY)
    expected = full_lines(run, cost, round(float(cost) / 40 * 100))
    assert capsys.readouterr().out.splitlines() == [line.replace(str(old), str(new)) for line in expected]
