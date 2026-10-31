# Task 5 — The owner's surface and risk visibility

planner: b
builder: d
depends_on: 1, 2 (builder d starts after the main session's `Merged: a->d` line, after Task 1, and its `Merged: b->d`
  line, after Task 2; `lessons.md` 21:29 and 22:27 UTC, `00-index.md` row 5 at 6c3a1cc)
files: S = `.claude/skills/running-specagent-pipelines`: `S/scripts/manager/surface.py` (new),
  `S/example/surface-phrases.en.json` (new), `S/scripts/tests/test_surface.py` (new), `S/scripts/tests/test_skill_example.py`
  (`FILES` gains the phrase file), `S/example/README.md` (the phrase file's line), `S/scripts/manager/README.md`
  (`## surface.py` with its `Usage:` line), `S/references/measuring.md` (`### The owner's surface`),
  `wiki/decisions/owner-surface-by-script.md` and `.summary.md` (answer 11a), `wiki/index.md`, `wiki/log.md`
acceptance: 10.6, 10.18

## Goal
The owner reads a run's state without asking: one line per role (state, unit, how long on it, context, cost, what it
waits for, its record path), one line for the run (cost so far against the budget of `_launch.md`, roles running,
elapsed), the usage reading with the next reset, the hand-over orders past the cap, the free disk and the monitor's open
alarms. A script renders the lines from the registry and the control files with fixed phrases and the numbers inserted
(answer 11a); the manager spends no tokens on it and takes its status figures from these lines (10.6). The run's cost is
`usage_report.py`'s total, run by the surface (10.18). The template ships English phrases; the owner's own phrase
file lives outside the template and is passed by path (D1).

## Spec carried
- Need 2 (spec :779-785): one line per role with unit, context, cost, elapsed, what it waits for and the record path,
  refreshed from the registry by a script; the manager's status answer comes from the same surface. Answer 11a (:1078).
- Need 7 (spec :815-821): cost per role and per run, the cap events, the next reset, the free disk, and the budget the
  surface compares against, named by the launch message (`_launch.md`'s `Budget:` line, Task 4).
- 5.7, the owner's reports (numbers and a record path), with Task 7 (the questions and the manager's role page).
- 10.6 (spec :1101-1102) and 10.18 (spec :1131-1132). D1 (English only; the script takes the phrase file by path; a test
  that needs a letter of a refused block builds it with `chr()`), D2 (the surface text sits under `_control/`), D3 (the usage
  reading is the manager's `get_usage`, read from `_control/usage.json`).

## Departures (from the spec and the index, with the reason)
1. "In translation" (need 2, 10.6) is met by the owner's phrase file, passed with `--phrases`; the template ships
   `example/surface-phrases.en.json` and no letter of a refused block (D1, ADR-0030). The tests build such a file with `chr()`.
2. Need 7's list also names the watcher's budget line (exit 3) and a long job's timeout (5.9.1); its "Met when" does not,
   and neither is on the surface: a watcher that exited 3 shows as the role's `stopped` state and in `_watch.log`, and the
   timeouts are Task 4's pre-flight (5.9.1). The surface shows exactly the "Met when" items.
3. The cap events are read from the registry's orders (`orders[].kind` `handoff`, the cap, and `unit-end`, past 150k at a
   unit's end; K1), not from the watcher's log lines (K5): the registry is the surface's only source for the roles, so a
   restart of the watcher (need 3, its orders restored) loses no event.
4. The cost per role is the registry's `cost_usd` (the watcher's figure from `usage_report.calls` and `PRICE`, K1 and
   K6); the run's cost is the last field of `usage_report.py`'s `total` row (10.18), which also counts sessions under the
   run's prefix that the registry does not list (the manager's helpers), so the roles need not add up to the run.

## Contracts
Read from other tasks (each one stubbed in the tests by fixture files):
- Task 2, K1 (`task-02.md:54-81`, 6773a1f): `<run>/_control/registry.json`, top-level `written_at`; per agent (the key is
  the config's name, e.g. `manager/planner-d`): `role`, `record`, `unit`, `unit_since`, `state` (`running`, `stopped`,
  `blocked`, `done`), `waiting_for`, `launched_at`, `context`, `cost_usd`, `orders` (`kind`, `sent_at`). Times
  `%Y-%m-%dT%H:%M:%SZ`. The surface reads no other field and never writes the registry.
- Task 3 (`task-03.md:60-63`, `:243-254`, 8d86fb3): `<run>/_control/monitor.json` `alarms`, each `{id, kind, text, since,
  open}`; the surface shows the open ones in the file's order; a missing file means no alarms.
- Task 4 (`task-04.md:27-30`): `<run>/_control/usage.json` `readings`, each `{taken_at, source, extra_usage, limits:
  [{name, used_pct, resets_at}]}`, times `%Y-%m-%dT%H:%MZ`; the newest reading has the latest `taken_at` (not
  necessarily the last in the list).
- Task 4 (contract sent to `manager/plan-fixer`, `planner-b: contract for Task 4 — the Budget: amount`): `example/launch.md`'s
  `Budget:` line names the run's spend as `$<amount>` (digits, an optional `.` and decimals), e.g.
  `Budget: $40 for the run; at $40 the manager launches nothing new and asks the owner`. The surface compares the run's
  cost with the first `$<amount>` on the first line of `<run>/_launch.md` that starts with `Budget:`; without one it
  renders the `run_unbudgeted` phrase.
- Task 4 (asked of `manager/plan-fixer-b` for task-04.md, C17): when the first role starts, the manager appends one
  line `Launched: <YYYY-MM-DDTHH:MM:SSZ>` (UTC) to `<run>/_launch.md`, once: no relaunch, resume or hand-over changes it
  (`example/launch.md` says so; the pre-flight has run by then, so the line is no placeholder it checks). The surface
  takes the run's start (line 1's `elapsed`, the default `--since`) from the first line that starts with `Launched:`;
  without one, from the earliest `launched_at`, which Task 2 resets at every fresh launch (`task-02.md:870-874`).
- `usage_report.py` (`:100-104`, `:144` at ff3354a; Task 10 keeps the form, C4 point 3): run as
  `python3 -I usage_report.py --prefix P [--since YYYY-MM-DD]`; its last line starting with `total` ends with the run's
  cost (`{total:8.2f}`). The surface keeps that text as printed and has no price table.
Given to other tasks:
- Task 7 (contract sent to `manager/plan-fixer`, `planner-b: contract for Task 7 — the status answer`):
  `docs/roles/manager-chat.md` says that the manager's status answer to the owner is two or three short lines, "now:
  …, next: …" (spec 5.7, `:695`; C18), whose figures (a role's unit, context and cost, the run's cost) are copied as
  printed from the stdout of `python3 -I <skill>/scripts/manager/surface.py <run> --phrases <owner phrase file>`, never
  computed (10.6), each line with a figure and the record path `<run>/_control/surface.txt` (10.18); the whole stdout
  only when the owner asks for the costs or the full state; and that after the launch the manager starts
  `python3 -I <skill>/scripts/manager/surface.py <run> --phrases <file> --out <run>/_control/surface.txt --every 120`
  as a background command and re-arms it after every exit, as it does the monitor.
- The owner, once (the summary): the owner's own phrase file outside the template, the shipped English file with each value
  translated and every `{field}` kept; `surface.py --check-phrases <file>` checks it.

## Interfaces
`S/scripts/manager/surface.py`, standard library only, run as `python3 -I`:
```text
python3 -I S/scripts/manager/surface.py <run-dir> [--phrases FILE] [--prefix P] [--since YYYY-MM-DD]
        [--now YYYY-MM-DDTHH:MM:SSZ] [--out FILE] [--every SECONDS] [--rounds N]
python3 -I S/scripts/manager/surface.py --check-phrases FILE
```
```python
"""The owner's surface: one line per role and the run's risks, from the registry, by fixed phrases."""

FIELDS: dict[str, frozenset[str]]  # phrase key -> the exact {field} names its template uses (table below)
DEFAULT_PHRASES: pathlib.Path  # Path(__file__).resolve().parents[2] / "example" / "surface-phrases.en.json"
USAGE_REPORT: pathlib.Path  # Path(__file__).resolve().parents[1] / "usage_report.py"


class SurfaceError(Exception):
    """A refusal; main prints `surface: <message>` to stderr and returns 2."""


def load_phrases(path: pathlib.Path) -> dict[str, str]:
    """The phrase file: a JSON object whose keys are exactly FIELDS' keys and whose values are strings using exactly
    FIELDS[key] as `{field}` names (string.Formatter().parse). Raises SurfaceError, the first problem in FIELDS' key
    order: `<path> does not parse: <json error>`, `<path>: missing phrase "<key>"`, `<path>: unknown phrase "<key>"`
    (keys sorted), `<path>: phrase "<key>" is not a string`,
    `<path>: phrase "<key>" uses {<names sorted, ", ">}, expected {<names sorted, ", ">}`."""


def parse_time(text: str) -> datetime.datetime:
    """A UTC time in `%Y-%m-%dT%H:%M:%SZ` or `%Y-%m-%dT%H:%MZ`, as an aware datetime (tz UTC); otherwise
    ValueError(f"not a UTC time: {text!r}"), the text the `Launched:` refusal quotes."""


def run_cost(prefix: str, since: str | None, timeout: float = 60) -> str:
    """Runs [sys.executable, "-I", USAGE_REPORT, "--prefix", prefix] (+ ["--since", since] when given), capture_output,
    text, check=False, timeout; returns the last whitespace field of the last stdout line whose first field is `total`.
    Raises SurfaceError: `usage_report.py did not finish in <timeout:g> s`,
    `usage_report.py failed (exit <rc>): <last non-empty stderr line>`, `usage_report.py printed no total row`."""


def render(run_dir: pathlib.Path, phrases: dict[str, str], now: datetime.datetime, cost: str) -> list[str]:
    """The surface's lines, in the order and with the values of the table below. Reads <run>/_control/registry.json
    (SurfaceError `no registry at <path>` when missing), _control/usage.json, _control/monitor.json, _launch.md and
    shutil.disk_usage(run_dir); a control file that does not parse raises SurfaceError `<path> does not parse: <error>`."""


def main(argv: list[str] | None = None) -> int:
    """0 when the lines were printed (one run) or written (--every), or the phrase file passed --check-phrases
    (stdout `phrases ok: <n> phrases in <path>`); 2 with `surface: <message>` on stderr for every SurfaceError and for
    `no run folder at <path>`, `--every needs --out`, `the agents share no prefix; pass --prefix`; argparse's own 2 for
    a bad option."""
```
The lines `render` returns, in this order (`R` is `<run>/_control/registry.json`, each `{record}` an absolute path):

| # | phrase | when | fields |
| --- | --- | --- | --- |
| 1 | `run` or `run_unbudgeted` | always; `run` when `_launch.md` has a `Budget:` line with a `$<amount>` | `run` = the run folder's name; `written_at` = R's, as recorded; `cost` = the `cost` argument, as given; `budget` = the amount as written; `pct` = `round(float(cost) / float(budget) * 100)`; `running` = roles whose `state` is `running`; `roles` = the number of roles; `elapsed` = the `duration` phrase from the run's start (`main`, below; C17) to `now` (`none` when there is none); `record` = R |
| 2.. | `role` | one per key of R's `roles`, in the file's order | `role` = its `role`; `state` = the `state_<state>` phrase (an unknown state as written); `unit` = its `unit` or `none`; `unit_elapsed` = `duration` from `unit_since` to `now` or `none`; `context` = `f"{context:,}"` or `none`; `cost` = `f"{cost_usd:.2f}"`; `waiting` = `str(waiting_for)` or `none`; `record` = its `record` |
| next | `usage` or `usage_missing` | `usage_missing` when `_control/usage.json` is missing or has no reading | `taken_at`, as recorded, of the reading with the latest `taken_at`; `limits` = its limits in their order, each the `limit` phrase (`name`; `used_pct` as `f"{v:g}"`; `resets_at` as recorded), joined by `", "`; `next_reset` = the earliest `resets_at` at or after `now`, as recorded, or `none`; `now` (usage_missing) = `now` as `%Y-%m-%dT%H:%M:%SZ`; `record` = `<run>/_control/usage.json` |
| next | `caps` or `caps_none` | `caps_none` when no order has `kind` `handoff` or `unit-end` | `count` = the orders of those two kinds over all roles; `role`, `at` = the `role` and `sent_at` (as recorded) of the one with the latest `sent_at`; `record` = R |
| next | `disk` | always | `free_mb` = `shutil.disk_usage(run_dir).free // 1048576`; `record` = the run folder |
| last | `alarm` | one per alarm of `_control/monitor.json` whose `open` is true, in the file's order | `kind`, `since`, `text` as recorded; `record` = `<run>/_control/monitor.json` |

`duration`: `h` = whole minutes // 60, `mm` = whole minutes % 60 as two digits, the minutes floored and never below 0.
`none`, `state_running`, `state_stopped`, `state_blocked`, `state_done` take no field. `FIELDS` is exactly:
`run` {run, written_at, cost, budget, pct, running, roles, elapsed, record}; `run_unbudgeted` {run, written_at, cost,
running, roles, elapsed, record}; `role` {role, state, unit, unit_elapsed, context, cost, waiting, record}; `usage`
{taken_at, limits, next_reset, record}; `usage_missing` {now, record}; `limit` {name, used_pct, resets_at}; `caps`
{count, role, at, record}; `caps_none` {count, record}; `disk` {free_mb, record}; `alarm` {kind, since, text, record};
`duration` {h, mm}; `none`, `state_running`, `state_stopped`, `state_blocked`, `state_done` {} (16 phrases).
`main`: `--phrases` defaults to `DEFAULT_PHRASES`; `--prefix` to the part up to and including the first `/` of R's role
keys when every key has one and they agree (else the refusal above); `--since` to the date (`%Y-%m-%d`) of the run's
start, no `--since` when there is none. The run's start (C17): the time after `Launched:` on the first line of
`_launch.md` that starts with it, stripped and read by `parse_time` (Task 4's contract; a relaunch never moves it),
else the earliest `launched_at` of R's roles (Task 2 resets it at every fresh launch), else none; `--now` to the
current UTC time. One run prints the lines (and writes them to `--out`
when given); `--every S` renders, writes `--out` (a `.tmp` sibling, then `os.replace`), stops after `--rounds N` renders
when N > 0 (default 0, no end) and otherwise calls `time.sleep(S)`, printing nothing; the first refusal ends it with 2.
The refusals in their order, the first one wins: `--check-phrases FILE` loads only that file and ignores every other
argument; no run folder and no `--check-phrases`: `ap.error("a run folder or --check-phrases is required")` (argparse's
exit 2, so `main([])` raises `SystemExit(2)`); `--every needs --out`; `no run folder at <path>`; the `--phrases` file
(`load_phrases`); then, in each round, the registry (`no registry at <path>`, `<path> does not parse: <error>`), the
prefix (no role key, a key without a `/` or two different prefixes: `the agents share no prefix; pass --prefix`),
the run's start (a `Launched:` value that `parse_time` refuses: `<path> does not parse: not a UTC time: '<value>'`;
`render` reads it when `--since` is given), `run_cost`, `render`. Each round takes the defaults and the time again:
`--now` fixes every round's time; without it,
`datetime.datetime.now(datetime.UTC)` with the microseconds dropped. Module facts the tests rely on: `shutil`,
`subprocess` and `time` are imported as modules and called through them (the tests replace `shutil.disk_usage` and
`time.sleep` on the module objects); `run_cost` reads the module-level `USAGE_REPORT` when it is called, never as a
default argument (the tests replace it with a silent and a slow script); the `.tmp` sibling is
`out.with_name(out.name + ".tmp")`. The file has no shebang line: it always runs as `python3 -I <path>`, the builder
cannot make it executable (Step 3a: no shell command under `.claude/skills/`, `chmod` included;
`git update-index --chmod=+x` sets the index's mode, not the file's), and ruff 0.16.10 fails `uv run ruff check .` on a
shebang in a file that is not executable (`EXE001`). The older `scripts/*.py` keep theirs: git gives them mode 755.

## Steps
- [ ] Step 1: `test_surface.py` in full (red: no module).
- [ ] Step 2: `example/surface-phrases.en.json`, its `example/README.md` line, `FILES` in `test_skill_example.py` (green).
- [ ] Step 3: `surface.py` against the tests (green), ruff.
- [ ] Step 4: `## surface.py` in `scripts/manager/README.md`.
- [ ] Step 5: `### The owner's surface` in `references/measuring.md`.
- [ ] Step 6: the 11a decision page, its `.summary.md`, `wiki/index.md` and `wiki/log.md` lines.
- [ ] Step 7: 10.6 and 10.18 on a scratch run folder; the skill's tests and the ruff pair.
- [ ] Step 8: commit.

### Step 1 — `test_surface.py` in full (red)
- [ ] 1a. Write `S/scripts/tests/test_surface.py` exactly as below (586 lines; 15 test functions, 30 tests with the
  parametrized cases). It loads `S/scripts/manager/surface.py` by its path (`scripts/manager/` is no package) and
  `S/scripts/usage_report.py` for its `PRICE` table, and uses the suite's helper `transcript_home.py` (`SCRIPTS`,
  `TEXT`, `Home`: a transcripts home in `tmp_path` and the stub `claude` on PATH that answers `agents --json --all`;
  unchanged by every task of this plan); no session starts. The expected lines are written out by hand from the
  fixtures (`full_lines`, `bare_lines`), never taken from `render`. Do not weaken a test; if one is wrong, send the
  plan fixer the proof.
```python
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
GEO = "".join(chr(c) for c in (0x10E1, 0x10E2, 0x10D0, 0x10E2, 0x10E3, 0x10E1, 0x10D8))  # a word of the refused blocks (D1)
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
```
- [ ] 1b. Run it (red) and both ruff commands:
```bash
uv run pytest -q .claude/skills/running-specagent-pipelines/scripts/tests/test_surface.py
uv run ruff check .claude/skills/running-specagent-pipelines/scripts/tests/test_surface.py
uv run ruff format --check .claude/skills/running-specagent-pipelines/scripts/tests/test_surface.py
```
Expected: `Interrupted: 1 error during collection` (`FileNotFoundError`: `scripts/manager/surface.py` does not exist
yet); `All checks passed!`; `1 file already formatted` (ruff 0.16.10; measured on a scratch copy of the skill at
ff3354a and from the plan worktree at 5876714 with `--stdin-filename`).

### Step 2 — The English phrase file, its README line and `FILES` (the example tests green)
- [ ] 2a. In `S/scripts/tests/test_skill_example.py`, append one line as the last entry of `FILES`, after its last
  entry (at ff3354a `*(f"{r}-settings.json" for r in ROLES),`) and before the closing `}` (C3; Global Constraint 14,
  C19: never between other tasks' entries). Task 4 (builder a) appends `"launch.md",` to the same set and a `launch.md`
  entry to the same README list the same way; the main session keeps both lines at each merge.
```python
    "surface-phrases.en.json",
```
Run the README test (red):
```bash
uv run pytest -q ".claude/skills/running-specagent-pipelines/scripts/tests/test_skill_example.py::test_the_example_readme_lists_every_file_and_every_placeholder_of_the_configs"
```
Expected: `1 failed`, with `Extra items in the right set:` and `'surface-phrases.en.json'` (`FILES` names a file the
example does not have yet).
- [ ] 2b. Write `S/example/surface-phrases.en.json` exactly as below: one JSON object, the 16 keys of `FIELDS`
  (Interfaces), each value using exactly its `{field}` names, a final newline. No value holds a `<name>`: the README
  test reads every `example/*.json` for `<name>` placeholders and wants a README line for each one.
```json
{
  "run": "Run {run} as of {written_at}: cost ${cost} of the ${budget} budget ({pct}%), {running} of {roles} roles running, elapsed {elapsed}. Record: {record}",
  "run_unbudgeted": "Run {run} as of {written_at}: cost ${cost}, no $ budget on the Budget: line of _launch.md, {running} of {roles} roles running, elapsed {elapsed}. Record: {record}",
  "role": "{role}: {state}, unit \"{unit}\" for {unit_elapsed}, context {context} tokens, cost ${cost}, waiting for {waiting}. Record: {record}",
  "usage": "Usage read at {taken_at}: {limits}; next reset {next_reset}. Record: {record}",
  "usage_missing": "No usage reading at {now}: the manager writes _control/usage.json before each launch. Record: {record}",
  "limit": "{name} {used_pct}% until {resets_at}",
  "caps": "Cap events: {count} hand-over orders, the last for {role} at {at}. Record: {record}",
  "caps_none": "Cap events: {count} hand-over orders. Record: {record}",
  "disk": "Free disk at {record}: {free_mb} MB.",
  "alarm": "Alarm {kind} since {since}: {text}. Record: {record}",
  "duration": "{h}h{mm}m",
  "none": "none",
  "state_running": "running",
  "state_stopped": "stopped",
  "state_blocked": "blocked",
  "state_done": "done"
}
```
- [ ] 2c. In `S/example/README.md`, append these three lines as the last entry of the file list, after its last line
  and before the blank line above `## Placeholders` (Global Constraint 14, C19: never between other tasks' entries; at
  ff3354a the last entry is `packs.json`, whose second line ends `measure again).`, `:52-53`). `FILE`, not a `<name>`,
  so the Placeholders list needs no line:
```markdown
- `surface-phrases.en.json`: the English phrases of the owner's surface, `../scripts/manager/surface.py` (answer 11a):
  one string per key, each `{field}` filled from the control files. The owner's own file keeps every key and every
  field, lives outside the template and is passed with `--phrases`; `surface.py --check-phrases FILE` checks it.
```
- [ ] 2d. Run the README test and the whole file (green):
```bash
uv run pytest -q ".claude/skills/running-specagent-pipelines/scripts/tests/test_skill_example.py::test_the_example_readme_lists_every_file_and_every_placeholder_of_the_configs"
uv run pytest -q .claude/skills/running-specagent-pipelines/scripts/tests/test_skill_example.py
```
Expected: `1 passed`; no `failed` (`9 passed` at ff3354a; Task 1 adds tests to this file, so the count is higher when
lane a is merged). `test_surface.py` stays red until Step 3.

### Step 3 — `surface.py` against the tests (green), ruff
- [ ] 3a. Write `S/scripts/manager/surface.py` to the Interfaces: Python 3.12 standard library only, the constants, the
  class and the five functions with the names and the signatures given (helpers of your own are free), no function of 50 lines
  or more (`.claude/rules/python.md:9`; `render` gives each kind of line a helper) and no shebang line (Interfaces,
  `EXE001`).
  `.claude/skills/` is a protected path: Write and Edit only, never a shell command (`sed -i`, `cp`, `mv`, `chmod`, a
  heredoc). The tests pin every phrase key and field, each value's form, the order of the lines and every
  refusal; add nothing the Interfaces do not ask for: no price table (the run's cost is `usage_report.py`'s text,
  Departure 4), no write to the registry, no state between rounds.
- [ ] 3b. Run the tests, both ruff commands and the phrase check:
```bash
uv run pytest -q .claude/skills/running-specagent-pipelines/scripts/tests/test_surface.py
uv run ruff check .claude/skills/running-specagent-pipelines/scripts/manager/surface.py .claude/skills/running-specagent-pipelines/scripts/tests/test_surface.py
uv run ruff format --check .claude/skills/running-specagent-pipelines/scripts/manager/surface.py .claude/skills/running-specagent-pipelines/scripts/tests/test_surface.py
python3 -I -c 'import ast, pathlib, sys; t = ast.parse(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")); print(max(n.end_lineno - n.lineno + 1 for n in ast.walk(t) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))))' .claude/skills/running-specagent-pipelines/scripts/manager/surface.py
python3 -I -c 'import ast, pathlib, sys; t = ast.parse(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")); print(max(n.end_lineno - n.lineno + 1 for n in ast.walk(t) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))))' .claude/skills/running-specagent-pipelines/scripts/tests/test_surface.py
python3 -I .claude/skills/running-specagent-pipelines/scripts/manager/surface.py --check-phrases .claude/skills/running-specagent-pipelines/example/surface-phrases.en.json
python3 -I .claude/skills/running-specagent-pipelines/scripts/manager/surface.py; echo "exit $?"
```
Expected: `30 passed`; `All checks passed!`; `2 files already formatted`; two numbers of at most `49`, one per line
(the longest function of surface.py, where the planner's first version, its `render` in one piece, printed `89`;
then of test_surface.py, `40` for `full_roles`, since V2 split the block's 83-line `full_run`);
`phrases ok: 16 phrases in .claude/skills/running-specagent-pipelines/example/surface-phrases.en.json`; a `usage:` line,
then `surface.py: error: a run folder or --check-phrases is required` and `exit 2`.

### Step 4 — `## surface.py` in `scripts/manager/README.md`
- [ ] 4a. Precondition. Task 1 (lane a) creates `S/scripts/manager/README.md` and its test
  `test_the_manager_readme_documents_every_script_of_its_folder` in `S/scripts/tests/test_catalogue.py`; builder D has
  both from the main session's `Merged: a->d` line, which `depends_on:` names (row 5 at 6c3a1cc, `lessons.md` 22:27
  UTC); the check below confirms that the merge brought them.
```bash
test -f .claude/skills/running-specagent-pipelines/scripts/manager/README.md && test -f .claude/skills/running-specagent-pipelines/scripts/tests/test_catalogue.py && echo both
```
Expected: `both`. Otherwise create neither file: wait for the `Merged: a->d at <sha>` line in `lessons.md` (match the
hex sha, check it with `git merge-base --is-ancestor`; Read first 3). Steps 5 and 6 do not need it.
- [ ] 4b. Run Task 1's README test (red: `surface.py` exists since Step 3, its section does not):
```bash
uv run pytest -q ".claude/skills/running-specagent-pipelines/scripts/tests/test_catalogue.py::test_the_manager_readme_documents_every_script_of_its_folder"
```
Expected: `1 failed`, with `AssertionError: surface.py`.
- [ ] 4c. Append the section below to `S/scripts/manager/README.md`, after one blank line, below the sections already
  there (Task 1's `## catalogue.py`; Task 4's `## preflight.py` when lane a's merge brought it). Task 7 appends its
  section after this one and edits neither. Each `Usage:` line stands alone as its own paragraph: the test reads
  `^Usage: .*scripts/manager/surface.py\b`.
```markdown
## surface.py
The owner's surface (need 2, need 7, answer 11a): one line for the run (its cost from `usage_report.py` against the
`$` amount of the `Budget:` line of `_launch.md`), one per role of `_control/registry.json` (state, unit and how long on
it, context, cost, what it waits for, the record path), the newest reading of `_control/usage.json` with the next reset,
the hand-over orders past the cap, the free disk and the open alarms of `_control/monitor.json`. Each line is a phrase
of the phrase file (default `example/surface-phrases.en.json`) with the numbers inserted. The manager answers status
questions from it and keeps `_control/surface.txt` fresh with `--out` and `--every 120` in the background.
Exit 0; 2 with one `surface: <reason>` line on stderr (argparse's own 2 for a bad option).

Usage: python3 -I scripts/manager/surface.py RUN_DIR [--phrases FILE] [--prefix P] [--since YYYY-MM-DD] [--now YYYY-MM-DDTHH:MM:SSZ] [--out FILE] [--every SECONDS] [--rounds N]

Usage: python3 -I scripts/manager/surface.py --check-phrases FILE
```
- [ ] 4d. Run it again (green) and measure the file:
```bash
uv run pytest -q ".claude/skills/running-specagent-pipelines/scripts/tests/test_catalogue.py::test_the_manager_readme_documents_every_script_of_its_folder"
wc -c < .claude/skills/running-specagent-pipelines/scripts/manager/README.md
```
Expected: `1 passed`; a number of at most `12000` (D4; the section adds 1,052 bytes with its blank line).

### Step 5 — `### The owner's surface` in `references/measuring.md`
- [ ] 5a. Append the section below to `S/references/measuring.md`, after one blank line (at ff3354a the file ends with
  the `Disk:` bullet). The file keeps its one `# Measuring the pipeline` title (`MOVED` pins line 1) and takes `###`
  headings only (`lessons.md` 20:36, C1-C3). Every `scripts/`, `example/` and `references/` path in the section exists
  once Steps 2 and 3 are done (`test_docs.py`,
  `test_skill_md_and_its_references_name_only_files_the_skill_has_and_the_current_rules`). Task 7 appends
  `### After every run, in this order` after this section and edits neither.
```markdown
### The owner's surface
- `scripts/manager/surface.py <run-dir>` renders the run's state in fixed phrases with the numbers inserted (answer
  11a): one line for the run (its cost from `scripts/usage_report.py` against the `$` amount of the `Budget:` line of
  `_launch.md`), one per role of `_control/registry.json` (state, unit and how long on it, context, cost, what it waits
  for, the record path), the newest reading of `_control/usage.json` with the next reset, the hand-over orders past the
  cap, the free disk and the open alarms of `_control/monitor.json`.
- The manager spends no tokens on it: its status answer is two or three short lines, "now: …, next: …", whose
  figures it copies from the output as printed (no figure of its own), the whole output only when the owner asks for
  the costs; it keeps `_control/surface.txt` fresh with `--out` and `--every 120` in the background, re-armed on each
  exit.
- Phrases: `example/surface-phrases.en.json` holds the English words; the owner's own file keeps every key and
  every `{field}`, lives outside the template and is passed with `--phrases`; `--check-phrases FILE` checks it.
- A role's cost is the watcher's figure in the registry; the run's cost is the total row of `scripts/usage_report.py`
  for the run's prefix, which also counts the manager's helpers, so the roles need not add up to the run.
```
- [ ] 5b. Check the headings and run the skill's whole suite:
```bash
grep -c '^# ' .claude/skills/running-specagent-pipelines/references/measuring.md
grep -c "^### The owner's surface$" .claude/skills/running-specagent-pipelines/references/measuring.md
uv run pytest -q .claude/skills/running-specagent-pipelines/scripts/tests
```
Expected: `1`; `1`; no `failed`, and the count is the suite's count before this task plus 30 (`176 passed` = 146 + 30 on
a scratch copy of the skill at ff3354a with Steps 1-5 applied; Tasks 1 and 2 add tests of their own once merged).

### Step 6 — The decision page of answer 11a, its summary, `wiki/index.md` and `wiki/log.md`
The index gives these files to this task (row 5; `lessons.md` 20:36, C5, C8: a decision goes into the commit of the
code that carries it). The form is Task 1's Step 7: the frontmatter fields in that order and a 4-line `.summary.md`;
`uv run harness wiki-lint` validates the frontmatter, the type per folder, the `wiki/index.md` line and every link (a
link resolves from `wiki/decisions/`). `updated:` is the build day. Step 6 does not need Step 4's merge.
- [ ] 6a. `wiki/decisions/owner-surface-by-script.md`:
```markdown
---
title: The owner's surface is rendered by a script
type: decision
status: draft
updated: <build day, YYYY-MM-DD>
audience: [all]
decided: 2026-10-29
by: owner
why: the owner's rule is scripts, not manager tokens; a script renders the same lines from the registry each time at no token cost, while a manager composing the status on request spends its context and can round or drop a figure
would_change_if: the owner needs answers the fixed lines cannot give, often enough that the manager composes them anyway, or the registry stops carrying a figure the lines show
decision_status: decided
scope: global
---
# The owner's surface is rendered by a script

`scripts/manager/surface.py` renders the owner's view of a run from `_control/registry.json` and the control files: one
line for the run (its cost from `usage_report.py` against the `$` amount of the `Budget:` line of `_launch.md`), one per
role (state, unit and how long on it, context, cost, what it waits for, the record path), the newest usage reading with
the next reset, the hand-over orders past the cap, the free disk and the monitor's open alarms. Each line is a fixed
phrase with the numbers inserted. The manager's status answer is two or three short lines whose figures are copied
from the output, the whole output only when the owner asks for the costs; it adds no figure of its own and keeps
`_control/surface.txt` fresh in the background. The template ships the English phrases
(`example/surface-phrases.en.json`); the owner's own phrase file lives outside the template and is passed with
`--phrases`, so no letter of a refused block enters the template. This is answer (a) to question 11 of the manager spec; answer
(b), the manager rendering the status on request, was not taken.

## Record and source
- [Measuring the pipeline](../../.claude/skills/running-specagent-pipelines/references/measuring.md)
- [The skill's example files](../../.claude/skills/running-specagent-pipelines/example/README.md)
- [The template is English only](the-template-is-english-only.md)
```
- [ ] 6b. `wiki/decisions/owner-surface-by-script.summary.md`, these four lines:
```markdown
Decision (owner, 2026-10-29): the owner's surface is rendered by a script.
`scripts/manager/surface.py` renders one line per role and the run's risks from the registry, in fixed phrases.
The manager copies its status figures from it at no token cost; the English phrases ship, the owner's file stays out.
The record is .claude/skills/running-specagent-pipelines/references/measuring.md.
```
- [ ] 6c. `wiki/index.md`, appended at the end of the decision lines (after line 19, "The shared knowledge base", at
  `ff3354a`; Tasks 1, 4 and 7 append theirs in their own lanes and the main session's merge keeps every line; an
  index-like file):
```markdown
- [The owner's surface is rendered by a script](decisions/owner-surface-by-script.md): `surface.py` renders one line per role and the run's risks from the registry in fixed phrases; the manager copies its status figures from it
```
- [ ] 6d. `wiki/log.md`, appended at its end (the form of its last entry):
```markdown
## <build day> pages written with Task 5 of the manager-build run
- commit: Task 5 of the manager-build run
- created: decisions/owner-surface-by-script.md
- updated: index.md
```
- [ ] 6e. No run in this step: `uv run harness wiki-lint` and `docs-check` are the verifier's full suites at M2
  (`_common.md:74-76`, Global Constraint 6; `lessons.md` 22:27 UTC, C503's rule). There `wiki-lint` gives
  `True <n+1> []`, n the page count before this task (13 at `ff3354a`, so `True 14 []`: measured on `git archive` of
  `feat/manager-build` at 8d2d438, whose `wiki/` is `ff3354a`'s, with this step's four files; without 6c's line it
  prints `False 14 ['decisions/owner-surface-by-script.md: not listed in index.md']`), and docs-check gives `[] []` (a
  decision page without its summary would be a warning, `catalog.py:60`).

### Step 7 — 10.6 and 10.18 on a scratch run folder; the skill's tests and the ruff pair
- [ ] 7a. Run, each from the checkout root (`command -v just` first if you run `just check` instead of the two ruff
  commands; `justfile:10` is the same pair):
```bash
uv run pytest -q .claude/skills/running-specagent-pipelines/scripts/tests
uv run ruff check . && uv run ruff format --check .
```
Expected: no `failed`, and the count is Step 5b's (`176 passed` on the scratch copy); `All checks passed!` then
`... files already formatted`. The task adds no harness test. The whole harness suite, `harness validate`,
`docs-check` and `wiki-lint` are the verifier's full suites at M2 (`_common.md:74-76`, Global Constraint 6;
`lessons.md` 22:27 UTC, C503's rule); measured on `git archive` of `feat/manager-build` at 8d2d438 with this task's
files: `harness validate` exits 0, docs-check `[] []`, wiki-lint as in 6e.
- [ ] 7b. 10.6 ("one line per role translated, with digits and a record path; the manager's status answer and the
  surface agree on unit, context and cost", spec :1101-1102) and 10.18 ("every status line to the owner contains a
  digit and a record path; the cost in the translated summary equals `usage_report.py`'s total for the run", spec
  :1131-1132) through the command line. The script below builds `test_surface.py`'s fixtures in an empty folder (the
  transcripts under a fake home, the full run folder, the owner's phrase file made with `chr()`), renders the surface
  in English and with the owner's file and `--out` (the file the manager quotes), runs `usage_report.py` for the
  run's prefix and first day, and prints the translated lines, the three exit codes and six checks; no session starts.
  Write it with the Write tool to `/home/tite/Desktop/agent-system-run/manager-build-2026-10-29/scratch/builder-d/accept.py`
  (your scratch folder: never the checkout, never `/tmp`):
```python
"""Task 5, Step 7: 10.6 and 10.18 through the CLI on a scratch run folder (argv: the skill, an empty scratch folder).
The run folder, the transcripts and the owner's phrase file are the fixtures of test_surface.py; no session starts."""

import importlib.util
import json
import pathlib
import re
import sys

skill, root = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve()
sys.path.insert(0, str(skill / "scripts" / "tests"))
spec = importlib.util.spec_from_file_location("test_surface", skill / "scripts" / "tests" / "test_surface.py")
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
home = t.Home(root / "home-root")
for sid, (name, start, calls) in t.CALLS.items():
    home.session(name, sid, [(ctx, out, [t.TEXT]) for ctx, out in calls], start=start)
run, ka = t.full_run(root), t.georgian(root)
out = run / "_control" / "surface.txt"
english = home.run("manager/surface.py", str(run), "--now", t.NOW)
local = home.run("manager/surface.py", str(run), "--now", t.NOW, "--phrases", str(ka), "--out", str(out))
roles = json.loads((run / "_control" / "registry.json").read_text(encoding="utf-8"))["roles"]
prefix = {name.split("/")[0] + "/" for name in roles}.pop()
launch = (run / "_launch.md").read_text(encoding="utf-8").splitlines()
starts = [ln.removeprefix("Launched:").strip() for ln in launch if ln.startswith("Launched:")]  # C17: as main reads it
day = starts[0][:10] if starts else min(r["launched_at"][:10] for r in roles.values() if r.get("launched_at"))
report = home.run("usage_report.py", "--prefix", prefix, "--since", day)
total = [line.split()[-1] for line in report.stdout.splitlines() if line.split()[:1] == ["total"]][-1]
en, ge = english.stdout.splitlines(), local.stdout.splitlines()
pick = re.compile(r'unit "([^"]*\d[^"]*)"|context ([\d,]+) tokens|cost \$([\d.]+)')  # the figures, not the words
print(local.stdout, end="")
print("exit codes:", english.returncode, local.returncode, report.returncode)
print("10.6 one line per role:", len(ge) == len(en) and sum(" tokens, cost $" in x for x in ge) == len(roles))
print("10.6 translated words:", all(any(0x10A0 <= ord(c) <= 0x10FF for c in x) for x in ge))
print("10.6 unit, context, cost agree:", [pick.findall(x) for x in en] == [pick.findall(x) for x in ge])
print("10.6 surface.txt equals the stdout:", out.read_text(encoding="utf-8") == local.stdout)
bare = [re.sub(re.escape(str(run)) + r"\S*", "", x) for x in ge]  # each line without its record path
print("10.18 a digit and a path on every line:", all(str(run) in x and re.search(r"\d", b) for x, b in zip(ge, bare)))
print("10.18 run cost = usage_report total:", re.search(r"\$([\d.]+)", ge[0]).group(1) == total, total)
```
```bash
A=/home/tite/Desktop/agent-system-run/manager-build-2026-10-29/scratch/builder-d
R=$(mktemp -d "$A/t5-accept.XXXXXX")
uv run python -I "$A/accept.py" .claude/skills/running-specagent-pipelines "$R" | LC_ALL=C sed -E 's/[^ -~]+/<GE>/g'
```
Expected (the `sed` shows each run of letters of the refused blocks as `<GE>`, which spares the tokens; `<R>` is the folder `mktemp`
made): nine surface lines, each starting with `<GE>`, the first
`<GE> Run demo-run as of 2026-10-29T20:59:00Z: cost $0.41 of the $40 budget (1%), 1 of 3 roles running, elapsed <GE> 0h55m. Record: <R>/demo-run/_control/registry.json`,
then one line each for planner, builder-a and critic, the usage reading, the cap events, the free disk (your disk's
figure in MB) and two alarms; then exactly:
```text
exit codes: 0 0 0
10.6 one line per role: True
10.6 translated words: True
10.6 unit, context, cost agree: True
10.6 surface.txt equals the stdout: True
10.18 a digit and a path on every line: True
10.18 run cost = usage_report total: True 0.41
```
In the suite the same checks are claimed by `test_a_georgian_phrase_file_changes_the_words_and_keeps_unit_context_and_cost`
and `test_main_prints_the_lines_and_writes_the_same_text_to_out` (10.6), and by
`test_every_line_has_a_digit_besides_its_record_path[english]`, `[georgian]` and
`test_the_run_cost_is_the_total_row_of_usage_report_for_the_prefix_and_the_day` (10.18). The live 10.6, the manager's
first status answer with its figures from `_control/surface.txt`, is the next run's (Deferred).

### Step 8 — The commit and the log line
- [ ] 8a. Write the commit message below with the Write tool to
  `/home/tite/Desktop/agent-system-run/manager-build-2026-10-29/scratch/builder-d/t5-commit.txt`, then commit the
  eleven files of the `files:` line with a pathspec:
```bash
S=.claude/skills/running-specagent-pipelines
F=("$S/scripts/manager/surface.py" "$S/example/surface-phrases.en.json" "$S/scripts/tests/test_surface.py"
  "$S/scripts/tests/test_skill_example.py" "$S/example/README.md" "$S/scripts/manager/README.md"
  "$S/references/measuring.md" wiki/decisions/owner-surface-by-script.md
  wiki/decisions/owner-surface-by-script.summary.md wiki/index.md wiki/log.md)
git add -- "${F[@]}"
git diff --cached --name-only "${BASE:?}" | wc -l
git commit -F /home/tite/Desktop/agent-system-run/manager-build-2026-10-29/scratch/builder-d/t5-commit.txt -- "${F[@]}"
```
Expected: `11` (five new files and six edited ones since `BASE`, nothing else), then git's summary line of the
commit.
`BASE` is the commit Task 5 began on, where the build log's review range starts: `HEAD` now when no
hand-over committed WIP, else the parent of the first WIP commit (lessons 23:45, B2 of build-log-c).
```text
feat(manager): Task 5 — the owner's surface, rendered by a script in fixed phrases

manager-build Task 5. scripts/manager/surface.py renders the owner's view of a run: one line for the run (its cost,
the total row of usage_report.py for the run's prefix, against the Budget: line of _launch.md), one per role of
_control/registry.json (state, unit and how long on it, context, cost, what it waits for, the record path), the
newest usage reading with the next reset, the hand-over orders past the cap, the free disk and the monitor's open
alarms. Each line is a phrase of example/surface-phrases.en.json with the numbers inserted; the owner's own
phrase file stays outside the template and is passed with --phrases (answer 11a; needs 2 and 7; 10.6, 10.18).
wiki/decisions/owner-surface-by-script.md records the decision.
```
- [ ] 8b. Append `Task 5: done — <sha>` to your build log.

## Wiki, index and llms lines
- Decision page with its `.summary.md`: `wiki/decisions/owner-surface-by-script.md` (answer 11a; 6a, 6b).
- `wiki/index.md`: the line of 6c; `wiki/log.md`: the entry of 6d.
- `docs/llms.txt`: no line. The task adds no file under `docs/`, and docs-check gives `[] []` without one (7a).

## Deferred
- The live 10.6: the manager's first status answer of the next run, two or three lines with their figures from
  `_control/surface.txt`. The manager's page that makes it answer from the surface and keep `--every 120` running is
  Task 7's (Contracts; the plan fixer carries it into `task-07.md` with C15 and C16, by its answer to planner-b).
- No `SKILL.md` line for `surface.py`: `SKILL.md` is builder A's, 11,933 of its 12,000 bytes at `ff3354a` (D4), and it
  reaches the surface through `references/measuring.md`, which it links (`SKILL.md:115`).
- The owner's own phrase file is the owner's, outside the template (D1): `--check-phrases` checks it, and
  `manager-build.summary.md` lists it among the owner's one-time actions.
- The prices of `usage_report.py` (8.3.14) are row 10's; the surface keeps no price table (Departure 4), so a price
  fixed there reaches the run line and, through the watcher's `cost_usd`, the role lines.

## Verified
- ruff 0.16.10 (`uv run ruff --version`; `pyproject.toml`: line length 120, no `select`): `EXE001 Shebang is present
  but file is not executable` on a 0644 file with a shebang; `git update-index --chmod=+x` set the index to 100755
  while the file on disk stayed 644 (a scratch repository); the 13 older `scripts/*.py` are 100755 in git, the 14
  `scripts/tests/*.py` 100644 (`git ls-files -s`).
- A scratch copy of the skill at `ff3354a` with Steps 1-5 applied (`surface.py` without a shebang, mode 664): the
  skill's suite `176 passed` (146 + 30), `test_surface.py` `30 passed`; over the skill's folder `ruff check --config
  pyproject.toml` prints `All checks passed!` and `ruff format --check` `30 files already formatted`; `--check-phrases`
  prints `phrases ok: 16 phrases in ...`; the run without arguments exits 2 with the `ap.error` line.
- The wrong versions of `surface.py`, each run once against the tests: 40 of 41 red; the 41st (the first `total` row
  instead of the last) stays green and is equivalent, since `usage_report.py` prints one `total` row (`:144`).
- `usage_report.py:24-28` (`PRICE`, opus `(4.0, 20.0, 0.20, 8.0)`), `:32-34` (the family), `:63-64` (the transcripts
  glob), `:100-104` (the command line, `--prefix` and `--since`), `:144` (the `total` row); `transcript_home.py:50-63`
  (`Home(root)`), `:162` (its environment), `:170` (`run`), unchanged by every task (its last commit a76caa9).
- `test_skill_example.py:62` (`WORDS`) and `:116-121` (a README line per file); `test_docs.py:142` (the skill's folder
  name); `task-02.md` contract K1 (the registry's top-level `roles`); `SKILL.md:115` (the link to
  `references/measuring.md`); `catalog.py:60` (`SUMMARY_FOLDERS`); `task-01.md` "Before you start" (the protected
  paths); `.claude/rules/python.md:9` (functions under 50 lines; 3b's `ast` line prints `89` on the planner's first
  version, whose `render` is one piece).
- Step 6 on `git archive` of `feat/manager-build` at 8d2d438 with its four files: wiki-lint `True 14 []`, and
  `False 14 [...]` without the index line; docs-check `[] []`; `harness validate` exits 0.
- 7b's script on the scratch copy: nine surface lines, `exit codes: 0 0 0`, the five `True` checks and
  `10.18 run cost = usage_report total: True 0.41`.
- `spec.md:1101-1102` (10.6) and `:1131-1132` (10.18); `00-index.md` row 5 at 6c3a1cc (depends on 1 and 2, milestone
  M2) and row 10 (the prices); `lessons.md` 22:23 UTC (EXE001) and 22:27 UTC (C503's rule; the `Merged: a->d` point).
- C19 (2a, 2c): at ff3354a `test_skill_example.py:18-30` (`FILES`, its last entry `*(f"{r}-settings.json" for r
  in ROLES),` at `:29`, the closing `}` at `:30`) and `example/README.md:50-55` (the last file entry `packs.json` at
  `:52-53`, a blank line, `## Placeholders`) (`git show ff3354a:<path>`); `00-index.md` Global Constraint 14 at cc5f177
  and `lessons.md` 22:45 UTC (main session: both lists index-like, a task appends at the end); `task-04.md` at 129bad6
  (Task 4 appends `launch.md` the same way).
- C17, A7 (plan-fixer): the scratch copy above with a `run_start` helper (the first `Launched:` line of `_launch.md`
  through `parse_time`, else the earliest `launched_at`) used by `render` and `defaults`: `test_surface.py` `30
  passed`, the skill's suite `176 passed`, ruff `All checks passed!` and `2 files already formatted`; the two new tests
  red on the old version (`cost $0.00 ... (0%)` and `elapsed 0h50m` for `$0.41 ... (1%)` and `5h00m`; the `launched`
  case exits 0); three wrong versions each red on one test (`elapsed` from `launched_at`, `--since` from `launched_at`,
  a bad `Launched:` value that falls back); `task-02.md:870-874` (a fresh launch sets `launched_at` = now);
  `usage_report.py:116` (calls before `--since` dropped); `task-04.md:1074-1077` (the pre-flight holds the launch until
  every line is filled, `Yes:` lines appended).
- C18 (plan-fixer): `spec.md:695` (5.7, [owner]: "Status is two or three lines, "now: …, next: …""); the vault's
  `decisions/global/owner-questions-and-status.md:17-18` ("Costs and the long plan only when asked"); the README section
  of 4c measured from this file: 1,078 bytes with its blank line before C18, 1,052 after.
- V2 (plan-fixer; `verify.md:327`, Global Constraint 9 at `00-index.md:59`): the verifier's `planfunclen.py` (each
  python block parsed with `ast`) on this file printed `task-05.md:318: full_run 83 lines`; after the split into
  `full_roles` (40 lines), `full_usage` (22), `full_alarms` (10) and `full_run` (16) it prints only
  `task-05.md:798: block does not parse` (2a's one-line fragment). On the plan fixer's scratch build of Task 5
  (`scratch/plan-fixer/t5/sk`, its `test_surface.py` the old block byte for byte) the new block gives `30 passed`,
  ruff 0.16.10 `All checks passed!` and `1 file already formatted`, 3b's second `ast` line `40`, and the old and the
  new `full_run` write the same seven files byte for byte (`scratch/plan-fixer/v2/equiv.py`).
