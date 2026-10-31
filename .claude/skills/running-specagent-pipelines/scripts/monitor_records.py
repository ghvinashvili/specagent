"""The record monitor of a run (spec 5.1, 10.19): it wakes the manager once for each new fact in the records.

  python3 -I monitor_records.py watch <run-dir> [options]
  python3 -I monitor_records.py once <run-dir> [options]
  python3 -I monitor_records.py answer <run-dir> <request-id> <text> [--refuse] [options]
  python3 -I monitor_records.py report <run-dir> [options]
  python3 -I monitor_records.py status <run-dir> [options]

Options, after the command: --config FILE (default: the agents of every check_formats.CONFIGS file), --registry FILE
(_control/registry.json), --duties FILE (_control/duties.md), --state FILE (_control/monitor.json), --log FILE
(_control/monitor.log), --interval S (60), --hours H (8), --bound M (the request-line bound of _common.md, 15 when it
names none), --grace S (300); a relative path resolves against the run folder.

A round, in this order: (1) the request lines of every record (check_formats.request_pairs): a new request wakes with
its requester and task, one first seen with its answer is recorded late and does not wake, and an open one past the
bound wakes once and opens an `overdue` alarm, which its answer closes; (2) a `VERDICT:` line wakes once; (3)
plan-log.md: a task claimed by two roles wakes `claim-race` per later role until a release, and a claimed, unwritten
task whose first claimant the registry shows stopped, blocked or done for --grace seconds wakes `stalled-claim`; (4)
the unticked duties of the duty list: a merge or judge duty that becomes due wakes once; a due merge duty is ticked
when a `Merged:` line of lessons.md with its own marker holds the duty's done tasks and is an ancestor of HEAD in the
blocked builder's checkout (no wake in the round it becomes due), else `merge-check` wakes per line; a due duty left
unticked past the bound wakes `overdue-duty`; (5) the done lines of the build logs and the written lines of
plan-log.md are logged once; (6) the WAKE lines are logged and the state is saved whole (a temporary file, then
os.replace). An alarm stays open, and silent, until its cause ends.

`watch` logs `armed …`, runs a round at once and then one per interval with a heartbeat, prints the first WAKE lines
and `woke: <n>` and exits 0, or exits 1 after --hours (re-arm with the same command); `once` runs one round without a
heartbeat; `answer` appends the answer line with the clock time (`--refuse`: `REFUSED: <KIND> — <text>`) and records
the answer; `report` prints a table of the requests; `status` exits 0 while a watch is armed with a fresh heartbeat,
else 1 with the reason. Exit 2 on a missing run folder or an answer that cannot be written. The monitor never runs
claude, writes no record except through `answer` and never writes the registry. Standard library only.
"""

import argparse
import json
import pathlib
import re
import sys
import time
from collections.abc import Callable

sys.dont_write_bytecode = True  # `python3 -I` ignores PYTHONDONTWRITEBYTECODE; the skill folder stays clean
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_formats as cf
import duty_list as dl

STALL_GRACE = 300
STALLED = ("stopped", "blocked", "done")
VERDICT = re.compile(r"^(?:- )?VERDICT: (.*)$")
CLAIM = re.compile(r"^(?:- )?Task (\d+): started by ([\w./-]+)")
RELEASE = re.compile(r"^(?:- )?Task (\d+): claim released by ([\w./-]+)")
WRITTEN = re.compile(r"^(?:- )?Task (\d+): (?:index )?written — ([0-9a-f]{7,40})\b")
TASK = re.compile(r"\bTask (\d+)")
DUTY_ALARM = re.compile(r"(?:overdue-duty|merge-check):D(\d+)\b")
FIELDS = {"watch": dict, "requests": list, "alarms": list, "duties": dict, "stalls": dict, "noted": list}
COMMANDS = ("watch", "once", "answer", "report", "status")


def stamp(t: float) -> str:
    """Seconds since the epoch as `YYYY-MM-DDTHH:MM:SSZ`."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def shown(iso: str, seconds: bool = True) -> str:
    """`YYYY-MM-DDTHH:MM:SSZ` as `YYYY-MM-DD HH:MM:SS`, or as `YYYY-MM-DD HH:MM`."""
    return iso[: 19 if seconds else 16].replace("T", " ")


def age(iso: object, now: float) -> float:
    """Seconds from `iso` to `now`; 0 for a missing or broken time."""
    try:
        return now - cf.epoch(str(iso))
    except ValueError:
        return 0.0


def first_line(path: pathlib.Path) -> str:
    """Line 1 of a file, empty when it is missing."""
    return (cf.read(path).splitlines() or [""])[0]


def log(ctx: argparse.Namespace, message: str) -> None:
    """A line of the monitor log: `<YYYY-MM-DD HH:MM:SS> UTC <message>`."""
    ctx.log.parent.mkdir(parents=True, exist_ok=True)
    with ctx.log.open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} UTC {message}\n")


def load(path: pathlib.Path) -> dict:
    """The state; a missing or broken file, or a field left out or of another type, reads as absent."""
    try:
        data = json.loads(cf.read(path) or "{}")
    except ValueError:
        data = {}
    data = data if isinstance(data, dict) else {}
    return {key: data[key] if isinstance(data.get(key), kind) else kind() for key, kind in FIELDS.items()}


def save(ctx: argparse.Namespace, state: dict) -> None:
    """The state written whole: a temporary file, then os.replace (duty_list.write)."""
    dl.write(ctx.state, json.dumps(state, indent=1, ensure_ascii=False) + "\n")


def noted(state: dict, key: str) -> bool:
    """True the first time `key` is noted: a verdict, done or written line is given once."""
    if key in state["noted"]:
        return False
    state["noted"].append(key)
    return True


def alarm(state: dict, kind: str, aid: str, text: str, now: float, wakes: list[str]) -> None:
    """Alarm `aid` opened (again, when it was closed) with its WAKE text, which wakes; an open alarm wakes nothing."""
    found = next((a for a in state["alarms"] if a.get("id") == aid), None)
    if found is not None and found.get("open"):
        return
    entry = {"id": aid, "kind": kind, "text": text, "since": stamp(now), "open": True}
    if found is None:
        state["alarms"].append(entry)
    else:
        found.update(entry)
    wakes.append(text)


def close(state: dict, shut: Callable[[str], bool]) -> None:
    """The open alarms whose id `shut` accepts are closed."""
    for a in state["alarms"]:
        if a.get("open") and shut(str(a.get("id"))):
            a["open"] = False


def requester(ctx: argparse.Namespace, path: pathlib.Path) -> tuple[str, str]:
    """The config agent whose `status` is the record, and `Task <N>` from its line 1; each `-` when absent."""
    agent = next((name for name, a in ctx.config.items() if a.get("status") == path.name), "-")
    m = TASK.search(first_line(path))
    return agent, f"Task {m.group(1)}" if m else "-"


def new_request(state: dict, name: str, r: dict, now: float, late: bool) -> dict:
    """A request's state entry, `seen` now; a late one (first seen with its answer, or answered by `answer` before
    the monitor saw it) is answered now."""
    entry = {"id": r["id"], "kind": r["kind"], "file": name, "line": r["line"], "text": r["text"], "seen": stamp(now)}
    entry |= {"answered": stamp(now) if late else None, "late": late}
    state["requests"].append(entry)
    return entry


def requests(ctx: argparse.Namespace, state: dict, now: float) -> list[str]:
    """Step 1: a new request wakes (a late one does not), an open one past the bound wakes once with alarm
    `overdue:<id>`, and its answer sets `answered` (unless `answer` set it) and closes the alarm."""
    known, wakes, answered = {e.get("id"): e for e in state["requests"]}, [], set()
    for path in cf.records(ctx.run):
        for r in cf.request_pairs(path.name, cf.read(path))[0]:
            entry, where = known.get(r["id"]), f"{path.name}:{r['line']}"
            if entry is None:
                entry = known[r["id"]] = new_request(state, path.name, r, now, r["answer"] is not None)
                if not entry["late"]:
                    agent, task = requester(ctx, path)
                    wakes.append(f"request {r['id']} {r['kind']} {where} ({agent}, {task}): {r['text']}")
            elif r["answer"] is not None:
                entry["answered"] = entry.get("answered") or stamp(now)
                answered.add(f"overdue:{r['id']}")
            elif age(entry.get("seen"), now) > ctx.bound * 60:
                minutes = int(age(entry.get("seen"), now) // 60)
                text = f"overdue {r['id']} {r['kind']} {where}: open {minutes} min, bound {ctx.bound:g} min"
                alarm(state, "overdue", f"overdue:{r['id']}", text, now, wakes)
    close(state, lambda aid: aid in answered)
    return wakes


def verdicts(ctx: argparse.Namespace, state: dict) -> list[str]:
    """Step 2: each `VERDICT:` line of a record wakes once."""
    wakes = []
    for path in cf.records(ctx.run):
        for number, line in enumerate(cf.read(path).splitlines(), 1):
            if (m := VERDICT.match(line)) and noted(state, f"verdict {path.name}:{number}"):
                wakes.append(f"verdict {path.name}:{number}: {m.group(1)}")
    return wakes


def plan_log(run: pathlib.Path) -> tuple[dict[int, dict[str, int]], list[tuple[int, str, int]]]:
    """plan-log.md's unreleased claims, {task: {role: line}} in claim order (a role is a name's last `/` part, so one
    role claiming twice keeps its first line), and its written lines, [(task, sha, line)]."""
    claims: dict[int, dict[str, int]] = {}
    written = []
    for number, line in enumerate(cf.read(run / "plan-log.md").splitlines(), 1):
        if m := CLAIM.match(line):
            claims.setdefault(int(m.group(1)), {}).setdefault(m.group(2).rpartition("/")[2], number)
        elif m := RELEASE.match(line):
            claims.get(int(m.group(1)), {}).pop(m.group(2).rpartition("/")[2], None)
        elif m := WRITTEN.match(line):
            written.append((int(m.group(1)), m.group(2), number))
    return claims, written


def races(state: dict, claims: dict[int, dict[str, int]], now: float) -> list[str]:
    """Step 3, races: a task claimed by two roles wakes once per later role (alarm `claim-race:<N>:<role>`); the
    alarm closes when a release ends that race."""
    wakes, live = [], set()
    for n, roles in claims.items():
        order = list(roles.items())
        for other, line in order[1:]:
            first, first_at = order[0]
            live.add(f"claim-race:{n}:{other}")
            text = f"claim-race Task {n}: {first} (plan-log.md:{first_at}) and {other} (plan-log.md:{line})"
            alarm(state, "claim-race", f"claim-race:{n}:{other}", text, now, wakes)
    close(state, lambda aid: aid.startswith("claim-race:") and aid not in live)
    return wakes


def registry_states(path: pathlib.Path) -> dict[str, str]:
    """{role: state} from the registry's `roles.<agent>.state`, the role an agent name's last `/` part; a missing
    file or key gives no state. The registry is read, never written."""
    try:
        roles = json.loads(cf.read(path) or "{}").get("roles", {})
    except (ValueError, AttributeError):
        return {}
    found: dict[str, str] = {}
    for name, entry in roles.items() if isinstance(roles, dict) else []:
        if isinstance(entry, dict) and isinstance(entry.get("state"), str):
            found.setdefault(str(name).rpartition("/")[2], entry["state"])
    return found


def stalls(ctx: argparse.Namespace, state: dict, claims: dict, written: list, now: float) -> list[str]:
    """Step 3, stalls: a claimed, unwritten task whose first claimant the registry shows stopped, blocked or done for
    --grace seconds (`stalls.<N>` holds the first sight) wakes once (alarm `stalled-claim:<N>`); the stall and its
    alarm end when the task is written or the role runs again."""
    roles, done, wakes, live = registry_states(ctx.registry), {task for task, _, _ in written}, [], set()
    for n, claimants in claims.items():
        if not claimants or n in done:
            continue
        role, line = next(iter(claimants.items()))
        if roles.get(role) not in STALLED:
            continue
        live.add(str(n))
        first = state["stalls"].setdefault(str(n), stamp(now))
        if age(first, now) >= ctx.grace:
            text = f"stalled-claim Task {n}: {role} is {roles[role]} and Task {n} is not written (plan-log.md:{line})"
            alarm(state, "stalled-claim", f"stalled-claim:{n}", text, now, wakes)
    state["stalls"] = {key: when for key, when in state["stalls"].items() if key in live}
    close(state, lambda aid: aid.startswith("stalled-claim:") and aid.partition(":")[2] not in live)
    return wakes


def dones(run: pathlib.Path) -> list[tuple[str, int, int, str]]:
    """The `Task N: done — <sha>` lines of the build logs, [(log, line, task, sha)] in log order."""
    found = []
    for name in cf.build_logs(run):
        for number, line in enumerate(cf.read(run / name).splitlines(), 1):
            if m := cf.DONE.match(line):
                found.append((name, number, int(m.group(1)), m.group(2)))
    return found


def merged_lines(run: pathlib.Path) -> list[tuple[int, str, str]]:
    """The `Merged: <marker> at <sha>` lines of lessons.md with its code spans removed, [(line, marker, sha)]."""
    text = cf.CODE_SPAN.sub("", cf.read(run / "lessons.md"))
    return [
        (n, m.group(1), m.group(2)) for n, line in enumerate(text.splitlines(), 1) for m in cf.MERGED.finditer(line)
    ]


def merge_failure(cwd: str, sha: str, after: list[int], done: dict[int, str]) -> str | None:
    """Why a merged sha fails in `cwd`: a done task's sha that is not its ancestor, or it not an ancestor of HEAD."""
    for task in after:
        if not cf.git_ok(cwd, "merge-base", "--is-ancestor", done[task], sha):
            return f"Task {task}'s {done[task][:7]} is not in it"
    if not cf.git_ok(cwd, "merge-base", "--is-ancestor", sha, "HEAD"):
        return f"not an ancestor of HEAD in {cwd}"
    return None


def merge_duty(ctx: argparse.Namespace, state: dict, n: int, merge: re.Match, done: dict, now: float) -> tuple:
    """A due merge duty against each `Merged:` line whose marker is its own (duty_list.norm), in the checkout of the
    blocked builder: the evidence of the first line that passes, else None and a `merge-check` wake per failing line.
    No such checkout: no check."""
    cwd = cf.builder_cwd(ctx.config, merge.group("lane"))
    if not cwd or not pathlib.Path(cwd).is_dir():
        return None, []
    after, failed = dl.numbers(merge.group("after")), []
    for number, marker, sha in merged_lines(ctx.run):
        if dl.norm(marker) != dl.norm(merge.group("marker")):
            continue
        reason = merge_failure(cwd, sha, after, done)
        if reason is None:
            return f"lessons.md:{number}, {sha[:7]}", []
        failed.append((number, f"merge-check D{n}: lessons.md:{number} Merged: {marker} at {sha[:7]} fails: {reason}"))
    wakes: list[str] = []
    for number, text in failed:
        alarm(state, "merge-check", f"merge-check:D{n}:{number}", text, now, wakes)
    return None, wakes


def judge_due(ctx: argparse.Namespace) -> bool:
    """Every config agent with `status` and `final`, but a `*/judge`, has a status file whose line 1 starts with its
    final; without a config, every record but judge.md starts `STATUS: done`."""
    if not ctx.config:
        records = [path for path in cf.records(ctx.run) if path.name != "judge.md"]
        return bool(records) and all(first_line(path).startswith("STATUS: done") for path in records)
    agents = [
        a
        for name, a in ctx.config.items()
        if isinstance(a.get("status"), str) and isinstance(a.get("final"), str) and name.rpartition("/")[2] != "judge"
    ]
    return bool(agents) and all(first_line(ctx.run / a["status"]).startswith(a["final"]) for a in agents)


def duties(ctx: argparse.Namespace, state: dict, now: float) -> list[str]:
    """Step 4: an unticked merge or judge duty that becomes due wakes once (`duties.D<n>.due`), but a merge duty
    ticked in that round; a due merge duty is ticked when a `Merged:` line passes, else `merge-check` wakes after its
    `duty` line; a due duty unticked past the bound wakes `overdue-duty`; a ticked duty's alarms close."""
    done = {task: sha for _, _, task, sha in dones(ctx.run)}  # a task's last line wins
    wakes, ticks, finished = [], [], set()
    for duty in dl.parse_duties(cf.read(ctx.duties)):
        n, merge = duty["n"], dl.MERGE.match(duty["text"])
        if duty["done"] or not (merge or duty["text"] == dl.JUDGE):
            finished.update([n] if duty["done"] else [])
            continue
        fresh = not isinstance(state["duties"].get(f"D{n}"), dict)
        if fresh and not (all(t in done for t in dl.numbers(merge.group("after"))) if merge else judge_due(ctx)):
            continue
        if fresh:
            state["duties"][f"D{n}"] = {"due": stamp(now)}
        evidence, checks = merge_duty(ctx, state, n, merge, done, now) if merge else (None, [])
        if evidence:
            ticks.append((n, evidence))
            finished.add(n)
            continue
        wakes += [f"duty D{n} due: {duty['text'].split(' — due when')[0]}"] * fresh + checks
        due = state["duties"][f"D{n}"].get("due")
        if not fresh and age(due, now) > ctx.bound * 60:
            text = f"overdue-duty D{n}: open {int(age(due, now) // 60)} min since due, bound {ctx.bound:g} min"
            alarm(state, "overdue-duty", f"overdue-duty:D{n}", text, now, wakes)
    tick(ctx, ticks)
    close(state, lambda aid: (m := DUTY_ALARM.match(aid)) is not None and int(m.group(1)) in finished)
    return wakes


def tick(ctx: argparse.Namespace, ticks: list[tuple[int, str]]) -> None:
    """The merge duties that passed, ticked in the duty file as it reads now (a hand tick in between wins) and logged
    `ticked D<n> (<evidence>)`."""
    if not ticks:
        return
    text = cf.read(ctx.duties)
    for n, evidence in ticks:
        try:
            text = dl.tick(text, n, evidence, dl.clock())
        except (KeyError, ValueError):  # ticked by hand, or gone, since the round read the file
            continue
        log(ctx, f"ticked D{n} ({evidence})")
    dl.write(ctx.duties, text)


def note_lines(ctx: argparse.Namespace, state: dict, written: list[tuple[int, str, int]]) -> None:
    """Step 5: each done line of the build logs and written line of plan-log.md is logged once; neither wakes."""
    for name, number, task, sha in dones(ctx.run):
        if noted(state, f"done {name}:{number}"):
            log(ctx, f"done Task {task} {sha[:7]} ({name}:{number})")
    for task, sha, number in written:
        if noted(state, f"written plan-log.md:{number}"):
            log(ctx, f"written Task {task} {sha[:7]} (plan-log.md:{number})")


def one_round(ctx: argparse.Namespace, state: dict, now: float) -> list[str]:
    """Steps 1-6 of a round: its WAKE texts (each without `WAKE `), logged, and the state saved."""
    claims, written = plan_log(ctx.run)
    wakes = requests(ctx, state, now) + verdicts(ctx, state)
    wakes += races(state, claims, now) + stalls(ctx, state, claims, written, now)
    wakes += duties(ctx, state, now)
    note_lines(ctx, state, written)
    for text in wakes:
        log(ctx, f"WAKE {text}")
    save(ctx, state)
    return wakes


def woke(wakes: list[str]) -> str:
    """The WAKE lines and `woke: <n>`."""
    return "".join(f"WAKE {text}\n" for text in wakes) + f"woke: {len(wakes)}"


def run_once(ctx: argparse.Namespace) -> int:
    """One round without a heartbeat."""
    print(woke(one_round(ctx, load(ctx.state), time.time())))
    return 0


def run_watch(ctx: argparse.Namespace) -> int:
    """A round at once, then one per interval, each writing the heartbeat: exit 0 at the first wake, 1 after
    --hours; `watch.ended` says which."""
    start = time.time()
    watch = {"armed": stamp(start), "last_round": None, "interval": ctx.interval, "ended": None, "ended_at": None}
    log(ctx, f"armed {ctx.run} interval={ctx.interval:g} s hours={ctx.hours:g} bound={ctx.bound:g} min")
    while True:
        state, now = load(ctx.state), time.time()  # read again: `answer` may have written it since
        watch["last_round"] = stamp(now)
        state["watch"] = watch
        wakes = one_round(ctx, state, now)
        if wakes or time.time() - start >= ctx.hours * 3600:
            break
        time.sleep(ctx.interval)
    watch["ended"], watch["ended_at"] = "woke" if wakes else "expired", stamp(time.time())
    save(ctx, state)
    if wakes:
        print(woke(wakes))
        log(ctx, f"woke: {len(wakes)}")
        return 0
    log(ctx, f"expired after {ctx.hours:g} h")
    print(f"expired after {ctx.hours:g} h: re-arm with the same command")
    return 1


def fail(message: str) -> int:
    """An error line on stderr; exit 2."""
    print(message, file=sys.stderr)
    return 2


def run_answer(ctx: argparse.Namespace, request_id: str, text: str, refuse: bool) -> int:
    """The request's answer line, with the clock time, appended to its record (the oldest open request of its kind
    first), and its state entry answered, its `overdue` alarm closed."""
    name = request_id.rsplit(":", 2)[0]
    path = ctx.run / name
    found = cf.request_pairs(name, cf.read(path))[0] if path in cf.records(ctx.run) else []
    r = next((x for x in found if x["id"] == request_id), None)
    if r is None:
        return fail(f"{request_id}: no such request")
    if r["answer"] is not None:
        return fail(f"{request_id}: answered already ({name}:{r['answer_line']})")
    older = next((x for x in found if x["kind"] == r["kind"] and x["answer"] is None and x["line"] < r["line"]), None)
    if older is not None:
        return fail(f"{request_id}: answer {older['id']} first ({name}:{older['line']})")
    head = f"REFUSED: {r['kind']} —" if refuse else f"{cf.REQUEST_KINDS[r['kind']]}:"
    old = cf.read(path)
    with path.open("a", encoding="utf-8") as f:
        f.write(("" if not old or old.endswith("\n") else "\n") + f"{head} {' '.join(text.split())} — {dl.clock()}\n")
    number, now = len(old.splitlines()) + 1, time.time()
    state = load(ctx.state)
    entry = next((e for e in state["requests"] if e.get("id") == request_id), None)
    entry = entry if entry is not None else new_request(state, name, r, now, late=True)
    entry["answered"] = stamp(now)
    close(state, lambda aid: aid == f"overdue:{request_id}")
    save(ctx, state)
    log(ctx, f"answered {request_id} ({name}:{number})")
    print(f"answered {request_id}: {name}:{number}")
    return 0


def run_report(ctx: argparse.Namespace) -> int:
    """A row per state request, in state order: asked, answered (or open) and the whole minutes between (or to now);
    a late request shows dashes."""
    now = time.time()
    rows = ["| kind | file:line | asked (UTC) | answered (UTC) | minutes |", "|---|---|---|---|---|"]
    for e in load(ctx.state)["requests"]:
        answered = e.get("answered")
        cells = [shown(str(e.get("seen")), False), shown(str(answered), False) if answered else "open"]
        cells.append(str(int((age(e.get("seen"), now) - (age(answered, now) if answered else 0)) // 60)))
        cells = ["—"] * 3 if e.get("late") else cells
        rows.append(f"| {e.get('kind')} | {e.get('file')}:{e.get('line')} | {' | '.join(cells)} |")
    print("\n".join(rows))
    return 0


def run_status(ctx: argparse.Namespace) -> int:
    """Exit 0 while a watch is armed (it has not ended and its heartbeat is at most 2 x interval + 5 s old); else
    exit 1 with `not armed: <reason>`."""
    watch = load(ctx.state)["watch"]
    if not watch.get("armed"):
        print("not armed: no watch recorded")
        return 1
    if watch.get("ended"):
        ended_at = shown(str(watch.get("ended_at")))
        print(f"not armed: the last watch {watch['ended']} at {ended_at} UTC; re-arm with the same command")
        return 1
    interval, last = float(watch.get("interval") or 60), str(watch.get("last_round") or watch["armed"])
    if age(last, time.time()) > 2 * interval + 5:
        print(f"not armed: no round since {shown(last)} UTC (interval {interval:g} s); re-arm with the same command")
        return 1
    print(f"armed since {shown(str(watch['armed']))} UTC, last round {shown(last)} UTC, interval {interval:g} s")
    return 0


def parser() -> argparse.ArgumentParser:
    """The commands; each takes the run folder and the options after the command (a parent parser)."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("run", help="the run folder")
    common.add_argument("--config", help="an agents config (default: every check_formats.CONFIGS file)")
    common.add_argument("--registry", default="_control/registry.json", help="the watcher's registry, read only")
    common.add_argument("--duties", default="_control/duties.md", help="the duty list")
    common.add_argument("--state", default="_control/monitor.json", help="the monitor's state")
    common.add_argument("--log", default="_control/monitor.log", help="the monitor's log")
    common.add_argument("--interval", type=float, default=60.0, help="seconds between the rounds of watch")
    common.add_argument("--hours", type=float, default=8.0, help="hours after which watch expires (exit 1)")
    common.add_argument("--bound", type=float, help="minutes a request may stay open (default: _common.md's, or 15)")
    common.add_argument("--grace", type=float, default=float(STALL_GRACE), help="seconds before a claim is stalled")
    top = argparse.ArgumentParser(description="The record monitor of a run: wakes, answers, the report, the status.")
    commands = top.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        command = commands.add_parser(name, parents=[common])
        if name == "answer":
            command.add_argument("request_id", help="the request's id, <file>:<KIND>:<n>")
            command.add_argument("text", help="the answer's text")
            command.add_argument("--refuse", action="store_true", help="write `REFUSED: <KIND> — <text>`")
    return top


def config_of(run: pathlib.Path, path: pathlib.Path | None) -> dict[str, dict]:
    """The agents of `--config`, else those of every check_formats.CONFIGS file."""
    if path is None:
        return cf.agents(run)
    try:
        found = json.loads(cf.read(path) or "{}").get("agents", {})
    except (ValueError, AttributeError):
        return {}
    return {n: a for n, a in found.items() if isinstance(a, dict)} if isinstance(found, dict) else {}


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    run = pathlib.Path(args.run)
    if not run.is_dir():
        return fail(f"{args.run}: no such run folder")
    for key in ("registry", "duties", "state", "log"):
        setattr(args, key, run / getattr(args, key))
    args.run, args.config = run, config_of(run, run / args.config if args.config else None)
    args.bound = float(cf.bound_minutes(run) if args.bound is None else args.bound)
    if args.command == "answer":
        return run_answer(args, args.request_id, args.text, args.refuse)
    return {"watch": run_watch, "once": run_once, "report": run_report, "status": run_status}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
