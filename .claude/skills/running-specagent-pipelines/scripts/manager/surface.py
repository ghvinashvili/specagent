"""The owner's surface: one line per role and the run's risks, from the registry, by fixed phrases.

One line for the run (its cost, the total row of usage_report.py for the run's prefix, against the `$` amount of the
`Budget:` line of _launch.md), one per role of the registry its config names (the `registry` field of --config, default
_control/_agents.json; else _control/registry.json), the newest reading of _control/usage.json with the next reset, the
hand-over orders past the cap, the free disk and the open alarms of _control/monitor.json (need 2, need 7, answer 11a).
Each line is a phrase of the phrase file with the numbers inserted; the manager copies its status figures from these
lines and spends no tokens on them.

  python3 -I scripts/manager/surface.py RUN_DIR [--config FILE] [--phrases FILE] [--prefix P] [--since YYYY-MM-DD]
      [--now YYYY-MM-DDTHH:MM:SSZ] [--out FILE] [--every SECONDS] [--rounds N]
  python3 -I scripts/manager/surface.py --check-phrases FILE

Exit codes: 0 the lines printed or written, or the phrase file checked; 2 a refusal, one `surface: <reason>` line on
stderr (argparse's own 2 for a bad option).
"""

import argparse
import datetime
import json
import math
import os
import pathlib
import re
import shutil
import string
import subprocess
import sys
import time
from collections.abc import Callable
from typing import Any

FIELDS: dict[str, frozenset[str]] = {
    "run": frozenset({"run", "written_at", "cost", "budget", "pct", "running", "roles", "elapsed", "record"}),
    "run_unbudgeted": frozenset({"run", "written_at", "cost", "running", "roles", "elapsed", "record"}),
    "role": frozenset({"role", "state", "unit", "unit_elapsed", "context", "cost", "waiting", "record"}),
    "usage": frozenset({"taken_at", "limits", "next_reset", "record"}),
    "usage_missing": frozenset({"now", "record"}),
    "limit": frozenset({"name", "used_pct", "resets_at"}),
    "caps": frozenset({"count", "role", "at", "record"}),
    "caps_none": frozenset({"count", "record"}),
    "disk": frozenset({"free_mb", "record"}),
    "alarm": frozenset({"kind", "since", "text", "record"}),
    "duration": frozenset({"h", "mm"}),
    "none": frozenset(),
    "state_running": frozenset(),
    "state_stopped": frozenset(),
    "state_blocked": frozenset(),
    "state_done": frozenset(),
}
DEFAULT_PHRASES = pathlib.Path(__file__).resolve().parents[2] / "example" / "surface-phrases.en.json"
USAGE_REPORT = pathlib.Path(__file__).resolve().parents[1] / "usage_report.py"
TIME_FORMS = ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ")
BUDGET = re.compile(r"\$(\d+(?:\.\d+)?)")
CAP_KINDS = ("handoff", "unit-end")  # the hand-over order at the cap, and the one past 150k at a unit's end (K1)


class SurfaceError(Exception):
    """A refusal; main prints `surface: <message>` to stderr and returns 2."""


def used_fields(text: str) -> set[str]:
    """The `{field}` names a phrase uses; ValueError when the phrase is no format string."""
    return {name for _, name, _, _ in string.Formatter().parse(text) if name is not None}


def shown(names: set[str] | frozenset[str]) -> str:
    """Field names as the refusals print them, sorted: `{a, b}`."""
    return "{" + ", ".join(sorted(names)) + "}"


def phrase_problem(key: str, text: object) -> str | None:
    """What is wrong with one phrase: not a string, no format string, or other `{field}` names than FIELDS[key]."""
    if not isinstance(text, str):
        return f'phrase "{key}" is not a string'
    try:
        used = used_fields(text)
    except ValueError as error:
        return f'phrase "{key}" does not parse: {error}'
    if used != FIELDS[key]:
        return f'phrase "{key}" uses {shown(used)}, expected {shown(FIELDS[key])}'
    return None


def load_phrases(path: pathlib.Path) -> dict[str, str]:
    """The phrase file: a JSON object whose keys are exactly FIELDS' keys and whose values are strings using exactly
    FIELDS[key] as `{field}` names (string.Formatter().parse). Raises SurfaceError, the first problem in FIELDS' key
    order: `<path> does not parse: <json error>`, `<path>: missing phrase "<key>"`, `<path>: unknown phrase "<key>"`
    (keys sorted), `<path>: phrase "<key>" is not a string`,
    `<path>: phrase "<key>" uses {<names sorted, ", ">}, expected {<names sorted, ", ">}`."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise SurfaceError(f"{path} does not parse: {error}") from None
    if not isinstance(data, dict):
        raise SurfaceError(f"{path} does not parse: not a JSON object")
    problems = [f'missing phrase "{key}"' for key in FIELDS if key not in data]
    problems += [f'unknown phrase "{key}"' for key in sorted(data) if key not in FIELDS]
    problems += [problem for key in FIELDS if key in data and (problem := phrase_problem(key, data[key]))]
    if problems:
        raise SurfaceError(f"{path}: {problems[0]}")
    return {key: data[key] for key in FIELDS}


def parse_time(text: str) -> datetime.datetime:
    """A UTC time in `%Y-%m-%dT%H:%M:%SZ` or `%Y-%m-%dT%H:%MZ`, as an aware datetime (tz UTC); otherwise
    ValueError(f"not a UTC time: {text!r}"), the text the `Launched:` refusal quotes."""
    for form in TIME_FORMS:
        try:
            return datetime.datetime.strptime(text, form).replace(tzinfo=datetime.UTC)
        except ValueError:
            continue
    raise ValueError(f"not a UTC time: {text!r}")


def run_cost(prefix: str, since: str | None, timeout: float = 60) -> str:
    """Runs [sys.executable, "-I", USAGE_REPORT, "--prefix", prefix] (+ ["--since", since] when given), capture_output,
    text, check=False, timeout; returns the last whitespace field of the last stdout line whose first field is `total`.
    Raises SurfaceError: `usage_report.py did not finish in <timeout:g> s`,
    `usage_report.py failed (exit <rc>): <last non-empty stderr line>`, `usage_report.py printed no total row`."""
    command = [sys.executable, "-I", str(USAGE_REPORT), "--prefix", prefix, *(["--since", since] if since else [])]
    try:
        done = subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise SurfaceError(f"usage_report.py did not finish in {timeout:g} s") from None
    if done.returncode != 0:
        errors = [line.strip() for line in done.stderr.splitlines() if line.strip()]
        raise SurfaceError(f"usage_report.py failed (exit {done.returncode}): {errors[-1] if errors else ''}")
    totals = [line.split() for line in done.stdout.splitlines() if line.split()[:1] == ["total"]]
    if not totals:
        raise SurfaceError("usage_report.py printed no total row")
    return totals[-1][-1]


def read_json(path: pathlib.Path) -> Any:
    """A control file's data, None when the file does not exist; SurfaceError `<path> does not parse: <error>`."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except ValueError as error:
        raise SurfaceError(f"{path} does not parse: {error}") from None


def checked[T](path: pathlib.Path, build: Callable[..., T], *args: object) -> T:
    """build(*args); a missing field, a wrong type or a bad time in the file at path is `<path> does not parse: <e>`."""
    try:
        return build(*args)
    except KeyError as error:
        raise SurfaceError(f"{path} does not parse: no field {error}") from None
    except (TypeError, ValueError, AttributeError) as error:
        raise SurfaceError(f"{path} does not parse: {error}") from None


def registry_path(run_dir: pathlib.Path, config: pathlib.Path | None) -> pathlib.Path:
    """The registry the agents config names, as the watcher reads it: its `registry` field under run_dir, else
    _control/registry.json, also when the default config (_control/_agents.json) is missing. SurfaceError `no config at
    <path>` for a named config that is missing, `<path> does not parse: <error>`, `registry <value> leaves run_dir`."""
    path = run_dir / "_control" / "_agents.json" if config is None else config
    data = read_json(path)
    if data is None:
        if config is not None:
            raise SurfaceError(f"no config at {path}")
        data = {}
    name = data.get("registry", "_control/registry.json") if isinstance(data, dict) else None
    if not isinstance(name, str):
        raise SurfaceError(f'{path} does not parse: "registry" is no path')
    if not (run_dir / name).resolve().is_relative_to(run_dir.resolve()):
        raise SurfaceError(f"registry {name} leaves run_dir")
    return run_dir / name


def load_registry(path: pathlib.Path) -> tuple[pathlib.Path, dict, dict]:
    """The registry's path, its data and its `roles`; SurfaceError when it is missing or does not parse."""
    data = read_json(path)
    if data is None:
        raise SurfaceError(f"no registry at {path}")
    roles = data.get("roles") if isinstance(data, dict) else None
    if not isinstance(roles, dict) or not all(isinstance(entry, dict) for entry in roles.values()):
        raise SurfaceError(f'{path} does not parse: "roles" is no object of agents')
    return path, data, roles


def shared_prefix(roles: dict) -> str:
    """The part up to and including the first `/` that every agent name has and shares; SurfaceError otherwise."""
    found = {name[: name.index("/") + 1] if "/" in name else "" for name in roles}
    if len(found) != 1 or "" in found:
        raise SurfaceError("the agents share no prefix; pass --prefix")
    return found.pop()


def launch_line(run_dir: pathlib.Path, start: str) -> str | None:
    """The rest of the first line of _launch.md that starts with `start`; None without one or without the file."""
    path = run_dir / "_launch.md"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return None
    except ValueError as error:
        raise SurfaceError(f"{path} does not parse: {error}") from None
    return next((line.removeprefix(start) for line in lines if line.startswith(start)), None)


def budget(run_dir: pathlib.Path) -> str | None:
    """The first `$<amount>` on the first `Budget:` line of _launch.md, as written; None without one."""
    found = BUDGET.search(launch_line(run_dir, "Budget:") or "")
    return found.group(1) if found else None


def run_start(run_dir: pathlib.Path, roles: dict, registry: pathlib.Path) -> datetime.datetime | None:
    """The run's start (C17): the first `Launched:` line, else the earliest `launched_at` of the roles of the registry
    at `registry`, else None."""
    launched = launch_line(run_dir, "Launched:")
    if launched is not None:
        return checked(run_dir / "_launch.md", parse_time, launched.strip())
    found = [entry["launched_at"] for entry in roles.values() if entry.get("launched_at")]
    return min((checked(registry, parse_time, value) for value in found), default=None)


def duration(phrases: dict[str, str], start: datetime.datetime | None, now: datetime.datetime) -> str:
    """The `duration` phrase from start to now in whole minutes, floored and never below 0; `none` without a start."""
    if start is None:
        return phrases["none"]
    minutes = max(0, int((now - start).total_seconds()) // 60)
    return phrases["duration"].format(h=minutes // 60, mm=f"{minutes % 60:02d}")


def run_line(run_dir: pathlib.Path, phrases: dict[str, str], now: datetime.datetime, cost: str, registry: tuple) -> str:
    """Line 1: the run's cost against the `Budget:` amount, the roles running and the time since the run's start."""
    path, data, roles = registry
    written = data.get("written_at")
    values = {
        "run": run_dir.name,
        "written_at": phrases["none"] if written is None else str(written),
        "cost": cost,
        "running": sum(1 for entry in roles.values() if entry.get("state") == "running"),
        "roles": len(roles),
        "elapsed": duration(phrases, run_start(run_dir, roles, path), now),
        "record": str(path),
    }
    amount = budget(run_dir)
    if amount is None:
        return phrases["run_unbudgeted"].format(**values)
    pct = round(float(cost) / float(amount) * 100) if float(amount) else phrases["none"]
    return phrases["run"].format(**values, budget=amount, pct=pct)


def role_line(entry: dict, phrases: dict[str, str], now: datetime.datetime) -> str:
    """One role: its state, its unit and how long on it, context, cost, what it waits for and its record path."""
    none = phrases["none"]
    state, since, context = entry.get("state"), entry.get("unit_since"), entry.get("context")
    cost, waiting = entry.get("cost_usd"), entry.get("waiting_for")
    return phrases["role"].format(
        role=entry["role"],
        state=none if state is None else phrases.get(f"state_{state}", str(state)),
        unit=entry.get("unit") or none,
        unit_elapsed=duration(phrases, parse_time(since) if since else None, now),
        context=none if context is None else f"{context:,}",
        cost=none if cost is None else f"{cost:.2f}",
        waiting=none if waiting in (None, "") else str(waiting),
        record=entry["record"],
    )


def usage_line(path: pathlib.Path, phrases: dict[str, str], now: datetime.datetime) -> str:
    """The newest usage reading, its limits and the next reset at or after now; `usage_missing` without a reading."""
    readings = (read_json(path) or {}).get("readings") or []
    if not readings:
        return phrases["usage_missing"].format(now=now.strftime(TIME_FORMS[0]), record=str(path))
    newest = max(readings, key=lambda reading: parse_time(reading["taken_at"]))
    limits = newest.get("limits") or []
    shown_limits = [
        phrases["limit"].format(name=limit["name"], used_pct=f"{limit['used_pct']:g}", resets_at=limit["resets_at"])
        for limit in limits
    ]
    resets = [limit["resets_at"] for limit in limits if parse_time(limit["resets_at"]) >= now]
    return phrases["usage"].format(
        taken_at=newest["taken_at"],
        limits=", ".join(shown_limits),
        next_reset=min(resets, key=parse_time) if resets else phrases["none"],
        record=str(path),
    )


def caps_line(registry: tuple, phrases: dict[str, str]) -> str:
    """The hand-over orders past the cap (`handoff`, `unit-end`) of all roles, an order not sent yet included (the
    watcher keeps `sent_at` null until it sends, R501), and the role and time of the latest one sent; when none was
    sent, the role of the last one (roles in the registry's order, orders in list order) at the `none` phrase."""
    path, _, roles = registry
    caps = [
        (entry["role"], order["sent_at"])
        for entry in roles.values()
        for order in entry.get("orders") or []
        if order.get("kind") in CAP_KINDS
    ]
    if not caps:
        return phrases["caps_none"].format(count=0, record=str(path))
    sent = [(parse_time(at), role, at) for role, at in caps if at is not None]
    _, role, at = max(sent, key=lambda cap: cap[0]) if sent else (None, caps[-1][0], phrases["none"])
    return phrases["caps"].format(count=len(caps), role=role, at=at, record=str(path))


def disk_line(run_dir: pathlib.Path, phrases: dict[str, str]) -> str:
    """The free disk of the run folder's file system, in whole MiB."""
    return phrases["disk"].format(free_mb=shutil.disk_usage(run_dir).free // 1048576, record=str(run_dir))


def alarm_lines(path: pathlib.Path, phrases: dict[str, str]) -> list[str]:
    """One line per open alarm of the monitor's file, in the file's order; none without the file."""
    alarms = (read_json(path) or {}).get("alarms") or []
    return [
        phrases["alarm"].format(kind=alarm["kind"], since=alarm["since"], text=alarm["text"], record=str(path))
        for alarm in alarms
        if alarm.get("open")
    ]


def render(
    run_dir: pathlib.Path, phrases: dict[str, str], now: datetime.datetime, cost: str, path: pathlib.Path | None = None
) -> list[str]:
    """The surface's lines in their order: the run, one per role, the usage reading, the cap events, the free disk and
    one per open alarm. Reads the registry at path (default: the one the default config names, registry_path();
    SurfaceError `no registry at <path>` when missing), _control/usage.json, _control/monitor.json, _launch.md and
    shutil.disk_usage(run_dir); a control file that does not parse raises SurfaceError `<path> does not parse:
    <error>`."""
    registry = load_registry(path or registry_path(run_dir, None))
    path, _, roles = registry
    usage, monitor = run_dir / "_control" / "usage.json", run_dir / "_control" / "monitor.json"
    return [
        checked(path, run_line, run_dir, phrases, now, cost, registry),
        *(checked(path, role_line, entry, phrases, now) for entry in roles.values()),
        checked(usage, usage_line, usage, phrases, now),
        checked(path, caps_line, registry, phrases),
        disk_line(run_dir, phrases),
        *checked(monitor, alarm_lines, monitor, phrases),
    ]


def day(text: str) -> str:
    """A --since value: a date, passed on as `%Y-%m-%d`."""
    return datetime.date.fromisoformat(text).isoformat()


def seconds(text: str) -> float:
    """An --every value: a number of seconds above 0."""
    value = float(text)
    if not (math.isfinite(value) and value > 0):
        raise ValueError(f"not a number of seconds above 0: {text!r}")
    return value


def parser() -> argparse.ArgumentParser:
    """The command line: a run folder and its options, or --check-phrases FILE alone."""
    ap = argparse.ArgumentParser(description="The owner's surface: one line per role and the run's risks.")
    ap.add_argument("run_dir", nargs="?", help="the run folder")
    ap.add_argument(
        "--config", type=pathlib.Path, metavar="FILE", help="the agents config (default: _control/_agents.json)"
    )
    ap.add_argument("--phrases", type=pathlib.Path, default=DEFAULT_PHRASES, help="the phrase file (default: English)")
    ap.add_argument("--prefix", help="the agents' name prefix for usage_report.py (default: the registry's)")
    ap.add_argument("--since", type=day, help="YYYY-MM-DD for usage_report.py (default: the run's first day)")
    ap.add_argument("--now", type=parse_time, help="YYYY-MM-DDTHH:MM:SSZ for every round (default: the clock)")
    ap.add_argument("--out", type=pathlib.Path, help="write the lines to this file as well")
    ap.add_argument("--every", type=seconds, metavar="SECONDS", help="render and write --out every SECONDS")
    ap.add_argument("--rounds", type=int, default=0, metavar="N", help="with --every, stop after N renders (0: never)")
    ap.add_argument("--check-phrases", type=pathlib.Path, metavar="FILE", help="check a phrase file, nothing else")
    return ap


def surface_text(run_dir: pathlib.Path, phrases: dict[str, str], args: argparse.Namespace) -> str:
    """One round: the registry its config names, the prefix, the run's first day and the time taken again, the cost and
    the lines."""
    path = registry_path(run_dir, args.config)
    _, _, roles = load_registry(path)
    prefix = shared_prefix(roles) if args.prefix is None else args.prefix
    since = args.since
    if since is None:
        start = run_start(run_dir, roles, path)
        since = None if start is None else start.strftime("%Y-%m-%d")
    now = args.now or datetime.datetime.now(datetime.UTC).replace(microsecond=0)
    return "\n".join(render(run_dir, phrases, now, run_cost(prefix, since), path)) + "\n"


def write_out(out: pathlib.Path, text: str) -> None:
    """The text to out through its `.tmp` sibling and os.replace, so that a reader never sees half a surface."""
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, out)


def every(run_dir: pathlib.Path, phrases: dict[str, str], args: argparse.Namespace) -> int:
    """--every: render and write --out each round, stop after --rounds renders when above 0, sleep in between."""
    done = 0
    while True:
        write_out(args.out, surface_text(run_dir, phrases, args))
        done += 1
        if 0 < args.rounds <= done:
            return 0
        time.sleep(args.every)


def main(argv: list[str] | None = None) -> int:
    """0 when the lines were printed (one run) or written (--every), or the phrase file passed --check-phrases
    (stdout `phrases ok: <n> phrases in <path>`); 2 with `surface: <message>` on stderr for every SurfaceError and for
    `no run folder at <path>`, `--every needs --out`, `the agents share no prefix; pass --prefix`; argparse's own 2 for
    a bad option."""
    ap = parser()
    args = ap.parse_args(argv)
    try:
        if args.check_phrases is not None:
            print(f"phrases ok: {len(load_phrases(args.check_phrases))} phrases in {args.check_phrases}")
            return 0
        if args.run_dir is None:
            ap.error("a run folder or --check-phrases is required")
        if args.every is not None and args.out is None:
            raise SurfaceError("--every needs --out")
        run_dir = pathlib.Path(args.run_dir).absolute()
        if not run_dir.is_dir():
            raise SurfaceError(f"no run folder at {run_dir}")
        phrases = load_phrases(args.phrases)
        if args.every is not None:
            return every(run_dir, phrases, args)
        text = surface_text(run_dir, phrases, args)
        if args.out is not None:
            write_out(args.out, text)
        print(text, end="")
        return 0
    except (SurfaceError, OSError) as error:
        print(f"surface: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
