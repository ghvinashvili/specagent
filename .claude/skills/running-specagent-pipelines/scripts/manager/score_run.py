"""One score per run folder (pipeline-fold Task 1): findings per task by kind with the `(plan)` V ids the critic
missed, sessions, cap hand-overs and idle restarts per role, cost attributed to tasks, request lines with their
minutes, and the lesson classes repeated. Reuses usage_report.py, findings_report.py and check_formats.py.

  python3 -I scripts/manager/score_run.py <run-dir> [--prefix <name>/] [--since YYYY-MM-DD] [--json]

Rules (the same for every run; scripts/manager/README.md repeats them with the table columns and an example line):
- A session belongs to the tasks named `Task N` (at a line start, after a quote, or in a `## Task N` heading) inside
  the text of its tool calls that write a record file of the run; two tasks split its cost equally; none: row `none`.
- A call writes a record file when it is an Edit or Write of one, or a Bash command whose stdout redirection (`>`,
  `>>`), `tee` or `sed -i` names one outside quotes; a Read, `2>/dev/null`, `2>&1` or `>&2` writes nothing.
- A session is idle when it wrote no record file, ran no `git commit`, and no call reached the cap.
- `cap` counts `cap <agent>` lines of `_watch.log`; `sessions` the rows of `claude agents --json --all` under the
  prefix; `first_call` the median first-call context of the role; `cache_ratio` cache-read over all context tokens.
- `missed` is a `(plan)` V on a task that has a `## Task N` section in critique.md, with or without a finding in it.
- A B id counts once per build log, for the task its text names first after its first ` — `, else for the task of the
  next `Task N: done` line below it, else for `none`.
- `repeated` lists the findings whose `Checklist:` item is a line of lessons.md (any path ending in it), by item, from
  one finding up; a `Checklist:` quoted in backticks is not a citation.
- A missing source leaves the cells it fills `n/a` and adds a note to the line, never an exception: `_watch.log`
  fresh and cap, `claude agents` sessions, a role's transcripts its idle, first call, cache read and cost.
- `economy` (the last table; `--json`: `economy`): per unit, a numbered task, the cost, the cache write dollars, the
  sessions, the copies (the `cap` and `unit end` lines of `_watch.log`, else of the older `_control/watch.out`) and the
  findings C + A + R + V, then `escaped`: the M, J and O ids of findings_report.py, past the verifier. A missing source
  (a partial cost or cache write total too) or no unit leaves `n/a`.
- The cache is measured in money (spec 005): beside its `cost` a role shows `read $`, `write $` and `output $`
  (`--json`: `cache_read_cost`, `cache_write_cost`, `output_cost`), the dollars of its cache reads, cache writes and
  output at usage_report.py's prices (`ur.dollars`, one usage per message id); the rest of the cost is input.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import re
import statistics
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import check_formats as cf
import findings_report as fr
import usage_report as ur

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure_manager as mm

RECORD = re.compile(
    r"(?:critique(?:-response)?|verify(?:-kb)?|plan-log|fixer(?:-b)?-log|judge|build-log[^\s/'\"]*)\.md"
)
TASK = re.compile(r"(?:^|['\"\n]|## )Task (\d+)\b")
TIME = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC")
FRESH = re.compile(r"\bfresh (\S+) after\b")
CAP_LINE = re.compile(r"\bcap (\S+) [\d,]+ tokens")
COPY_LINE = re.compile(r"\b(?:cap|unit end) (\S+) [\d,]+ tokens")  # an order that starts a copy; no `grace` line
LESSON = re.compile(r"(?:^|/)lessons\.md:\d+$")
# Task 6 Step 0 (V5, R4, C31): an id line (`#### <id>` or `<id>:`), a request line and a rejected answer, as a record
# write holds them (at a line start, after a quote as a Bash command writes it, or after a list dash).
ID_LINE = re.compile(r"(?:^|['\"\n])(?:- )?(?:#### )?([A-Z]{1,2}\d+)(?=:| — )")
REQUEST_LINE = re.compile(r"(?:^|['\"\n])(?:- )?(?:SANDBOX|COPY-REQUEST|CHECKOUT-REQUEST|FF-REQUEST):")
REJECTED = re.compile(r"(?m)^(?:- )?([A-Z]{1,2}\d+): rejected\b")
ROW = {"C": 0, "A": 0, "R": 0, "V": 0, "V_plan": 0, "missed": 0, "B": 0, "rejected": 0, "cost": 0.0}
DONE = re.compile(r"(?:- )?Task (\d+): done\b")
TEXT_KEY = {"Bash": "command", "Edit": "file_path", "MultiEdit": "file_path", "Write": "file_path"}
QUOTED = re.compile(r"'[^']*'|\"(?:[^\"\\]|\\.)*\"")
REDIRECT = re.compile(r"(?<![\d>&])[&1]?>>?(?![>&])\s*([^\s;|&<>()]+)")
SED_TEE = re.compile(r"(?:^|[;|&(\n])\s*(?:sed\s+(?:-\S+\s+)*-i\S*|tee(?:\s+-\S+)*)\s+([^;|&<>()]+)")
CAP = 200_000
KINDS = ("C", "A", "R", "V")
ECONOMY_PER_UNIT = ("sessions_per_unit", "copies_per_unit", "findings_per_unit")  # the cells between cost and escaped


def role_of(agent: str, prefix: str) -> str:
    return agent[len(prefix) :] if prefix and agent.startswith(prefix) else agent.split("/")[-1]


def b_rows(run: pathlib.Path) -> list[tuple[str, str, str, bool]]:
    """Each build log's B ids once (an `answered` line repeats the id): (log, id, task, sent). The task is the one its
    text names first after its first ` — `, else that of the next `Task N: done` line below it, else `none`; `sent`
    when its first line says `sent to` (the planner's or the plan fixer's B)."""
    out: list[tuple[str, str, str, bool]] = []
    for log in cf.build_logs(run):
        lines = cf.read(run / log).splitlines()
        seen: set[str] = set()
        for i, line in enumerate(lines):
            m = re.match(r"(?:- )?(B\d+):(.*)", line)
            if not m or m.group(1) in seen:
                continue
            seen.add(m.group(1))
            named = re.match(r"\s*Task (\d+)\b", m.group(2).partition(" — ")[2])
            below = (d.group(1) for d in map(DONE.match, lines[i + 1 :]) if d)
            task = named.group(1) if named else next(below, "none")
            out.append((log, m.group(1), task, bool(re.match(r"\s*sent to\b", m.group(2)))))
    return out


def filing(run: pathlib.Path) -> dict:
    """Where each id is filed (Step 0 rule 2): `ids` C, A and R by critique.md's sections, V by verify.md's (an id's
    first heading wins); `b` each build log's B by `b_rows`; `sent` a B answered in critique-response.md, the task of
    the B whose first line in its log says `sent to` (the first such log in `cf.build_logs` order)."""
    ids: dict[str, str] = {}
    for name in ("critique.md", "verify.md"):
        for ident, task in fr.task_ids(cf.read(run / name)):
            ids.setdefault(ident, task)
    rows = b_rows(run)
    sent: dict[str, str] = {}
    for _, ident, task, was_sent in rows:
        if was_sent:
            sent.setdefault(ident, task)
    return {"ids": ids, "b": {(log, ident): task for log, ident, task, _ in rows}, "sent": sent}


def task_counts(run: pathlib.Path) -> dict[str, dict]:
    """Per task: C, A, R, V from the sections, V_plan and missed from verify.md's causes, B from the build logs, and
    rejected (R4, rule 5): the ids filed under the task with a `<id>: rejected` answer line in critique-response.md
    or a build log, each id once; a B by a line in its own log, or by one in critique-response.md when its first
    line in its log says `sent to`; an id filed under no task counts in `none`."""
    tasks: dict[str, dict] = {}

    def row(task: str) -> dict:
        return tasks.setdefault(task, dict(ROW))

    for name in ("critique.md", "verify.md"):
        counted: set[str] = set()
        for ident, task in fr.task_ids(cf.read(run / name)):
            kind = fr.kind(ident)
            if kind in KINDS and ident not in counted:
                counted.add(ident)
                row(task)[kind] += 1
    reviewed = set(re.findall(r"(?m)^## Task (\d+)\b", cf.read(run / "critique.md")))
    verify = cf.read(run / "verify.md")
    task_of = dict(fr.task_ids(verify))
    for ident, _, body in cf.sections(verify):
        if fr.kind(ident) == "V" and fr.cause(body) == "plan":
            task = task_of.get(ident, "none")
            row(task)["V_plan"] += 1
            row(task)["missed"] += task in reviewed
    where = filing(run)
    for _, _, task, _ in b_rows(run):
        row(task)["B"] += 1
    rejected: set[tuple] = set()
    answers = [("critique-response.md", cf.read(run / "critique-response.md"))]
    answers += [(log, cf.read(run / log)) for log in cf.build_logs(run)]
    for name, text in answers:
        for ident in REJECTED.findall(text):
            if fr.kind(ident) != "B":
                key, task = (ident,), where["ids"].get(ident, "none")
            elif name == "critique-response.md":
                key, task = ("sent", ident), where["sent"].get(ident, "none")
            else:
                key, task = (name, ident), where["b"].get((name, ident), "none")
            if key not in rejected:
                rejected.add(key)
                row(task)["rejected"] += 1
    return tasks


def edited(given: dict) -> str:
    """The lines an Edit (or each edit of a MultiEdit) adds: those of `new_string` that `old_string` does not have."""
    edits = given.get("edits") if isinstance(given.get("edits"), list) else [given]
    added = []
    for e in edits:
        if not isinstance(e, dict):
            continue
        old = set(str(e.get("old_string") or "").splitlines())
        added += [x for x in str(e.get("new_string") or "").splitlines() if x not in old]
    return "\n".join(added)


def tool_texts(path: str) -> list[dict]:
    """Every Bash, Edit, MultiEdit and Write call of a transcript, in file order: `tool`, `where` (the command, or the
    file path) and `text` (the command; a Write's content; the lines an Edit adds, Step 0 rule 1). A Read names a
    file without writing it, so it gives no call."""
    calls = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if '"tool_use"' not in line:
                continue
            try:
                blocks = json.loads(line)["message"]["content"]
            except (ValueError, KeyError, TypeError):
                continue
            for b in blocks if isinstance(blocks, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in TEXT_KEY:
                    given = b.get("input") or {}
                    where = str(given.get(TEXT_KEY[b["name"]]) or "")
                    if b["name"] == "Bash":
                        text = where
                    elif b["name"] == "Write":
                        text = str(given.get("content") or "")
                    else:
                        text = edited(given)
                    calls.append({"tool": b["name"], "where": where, "text": text})
    return calls


def writes_record(text: str) -> bool:
    """Whether a tool text writes a record file: an Edit or Write path (one word), or a Bash command whose stdout
    redirection, `tee` or `sed -i` names one outside quotes (`2>/dev/null`, `2>&1` and `>&2` write nothing)."""
    if not RECORD.search(text):
        return False
    if len(text.split()) == 1:
        return True
    return bool(bash_targets(text))


def bash_targets(command: str) -> list[str]:
    """The record files a Bash command writes: its stdout redirection, `tee` or `sed -i` targets outside quotes that
    name one, each as the file name `RECORD` matched."""
    bare = QUOTED.sub(lambda m: re.sub(r"[;|&<>()]", "_", m.group()), command)
    found = []
    for m in (*REDIRECT.finditer(bare), *SED_TEE.finditer(bare)):
        if r := RECORD.search(m.group(1)):
            found.append(r.group(0))
    return found


def record_of(call: dict) -> str | None:
    """The record file a call writes (its file name), or None: an Edit's or Write's path that names one, or a Bash
    command's first target (`bash_targets`)."""
    if call["tool"] == "Bash":
        targets = bash_targets(call["where"]) if len(call["where"].split()) > 1 else []
        if not targets and len(call["where"].split()) == 1 and (r := RECORD.search(call["where"])):
            return r.group(0)
        return targets[0] if targets else None
    r = RECORD.search(os.path.basename(call["where"]))
    return r.group(0) if r else None


def unit_lines(call: dict, where: dict) -> tuple[set[str], bool]:
    """The tasks a record write names (Step 0 rule 2) and whether it holds a unit line (rule 6): `Task N` as `TASK`
    finds it; an id as `ID_LINE` finds it, named for the task it is filed under (C, A, R and V by `filing`'s `ids`,
    a B by its own log, or by `sent` when written to critique-response.md; one filed under no task names none but
    is a unit line); a request line (`REQUEST_LINE`) is a unit line."""
    text, log = call["text"], record_of(call)
    tasks = set(TASK.findall(text))
    unit = bool(tasks) or bool(REQUEST_LINE.search(text))
    for ident in ID_LINE.findall(text):
        unit = True
        if fr.kind(ident) != "B":
            task = where["ids"].get(ident)
        elif log == "critique-response.md":
            task = where["sent"].get(ident)
        else:
            task = where["b"].get((log, ident))
        if task and task != "none":
            tasks.add(task)
    return tasks, unit


def session_stats(sid: str, seen: set) -> dict | None:
    """One session's calls: first-call context, context and cache-read sums, cost and its split (the dollars of the
    cache reads, the cache writes and the output, by `ur.dollars`), max context, tool texts. `seen` is shared across
    sessions, as usage_report.py shares it: a resumed copy's inherited calls count once."""
    paths = ur.transcripts(sid)
    if not paths:
        return None
    s = {
        "first": None,
        "context": 0,
        "cache": 0,
        "cost": 0.0,
        "cr_usd": 0.0,
        "cw_usd": 0.0,
        "out_usd": 0.0,
        "max": 0,
        "texts": [],
    }
    for path in paths:
        for d in ur.calls(path, seen):
            u = d["message"]["usage"]
            ctx = ur.context(u)
            paid_in, paid_out, paid_cr, paid_cw = ur.dollars(d["message"])
            s["first"] = ctx if s["first"] is None else s["first"]
            s["context"] += ctx
            s["cache"] += u.get("cache_read_input_tokens") or 0
            s["max"] = max(s["max"], ctx)
            s["cost"] += paid_in + paid_out + paid_cr + paid_cw
            s["cr_usd"] += paid_cr
            s["cw_usd"] += paid_cw
            s["out_usd"] += paid_out
        s["texts"] += tool_texts(path)
    return s


def watch_counts(run: pathlib.Path, prefix: str) -> tuple[dict[str, int], dict[str, int]] | None:
    """The `fresh <agent> after` and `cap <agent> N tokens` lines of `_watch.log` per role under the prefix; None
    without the file."""
    watch = run / "_watch.log"
    if not watch.exists():
        return None
    fresh: dict[str, int] = {}
    caps: dict[str, int] = {}
    for line in watch.read_text(encoding="utf-8", errors="ignore").splitlines():
        for pattern, counts in ((FRESH, fresh), (CAP_LINE, caps)):
            if (m := pattern.search(line)) and m.group(1).startswith(prefix):
                role = role_of(m.group(1), prefix)
                counts[role] = counts.get(role, 0) + 1
    return fresh, caps


def copy_orders(run: pathlib.Path, prefix: str) -> int | None:
    """The `cap` and `unit end` orders of `_watch.log` under the prefix, else of the older `_control/watch.out`: each
    started a copy of its session; None without either file."""
    for path in (run / "_watch.log", run / "_control" / "watch.out"):
        if path.exists():
            found = (COPY_LINE.search(line) for line in path.read_text(encoding="utf-8", errors="ignore").splitlines())
            return sum(1 for m in found if m and m.group(1).startswith(prefix))
    return None


def escaped(run: pathlib.Path) -> int | None:
    """The M, J and O ids of findings_report.py: what got past the verifier, the merge gate included; None when
    neither lessons.md (M, O) nor judge.md (J) exists."""
    if not any((run / name).exists() for name in ("lessons.md", "judge.md")):
        return None
    kinds = fr.report(run)["kinds"]
    return sum(kinds[k]["total"] for k in ("M", "J", "O"))


def economy(
    run: pathlib.Path, prefix: str, units: int, sessions, cost, cache_write, findings: int, missing: list[str]
) -> dict:
    """The economy row: per unit the cost, the cache write dollars, sessions, copies and findings, and the escaped
    count. A cell is None for a missing source, for a cost or a cache write total with a transcript missing (a partial
    total is no total) and for no unit."""
    copies = copy_orders(run, prefix)

    def per_unit(value):
        return None if value is None or not units else round(value / units, 4)

    return {
        "units": units,
        "cost_per_unit": per_unit(None if "transcripts" in missing else cost),
        "cache_write_per_unit": per_unit(None if "transcripts" in missing else cache_write),
        "sessions_per_unit": per_unit(sessions),
        "copies": copies,
        "copies_per_unit": per_unit(copies),
        "findings_per_unit": per_unit(findings),
        "escaped": escaped(run),
    }


def listed_rows(prefix: str, since: str | None) -> list[dict] | None:
    """The rows of `claude agents --json --all` under the prefix that started on or after `since`; None when the
    command fails."""
    try:
        rows = ur.agent_rows(prefix)
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None
    return [r for r in rows if not since or ur.started(r)[:10] >= since]


def session_entry(role: str, s: dict, where: dict) -> dict:
    """A session's attribution (Step 0): the tasks its record writes name (`unit_lines`), `by` `lines` or `none`
    (`next` is set by `role_stats`, rule 3), its cost split equally between its tasks, and whether it was idle (rule
    6: no record write holding a unit line, no `git commit`, no call at the cap)."""
    found, unit = set(), False
    for call in s["texts"]:
        if record_of(call):
            tasks, held = unit_lines(call, where)
            found |= tasks
            unit = unit or held
    tasks = sorted(found, key=int)
    committed = any(c["tool"] == "Bash" and "git commit" in c["text"] for c in s["texts"])
    return {
        "role": role,
        "tasks": tasks,
        "by": "lines" if tasks else "none",
        "cost": s["cost"],
        "per_task": s["cost"] / len(tasks) if tasks else s["cost"],
        "idle": not unit and not committed and s["max"] < CAP,
    }


def transcript_cells(read: list[tuple[dict, dict]]) -> dict:
    """A role's idle, first call, cache read, cost and its split into the dollars of the cache reads, the cache writes
    and the output, from the (attribution, stats) pairs of its sessions that have a transcript."""
    context = sum(s["context"] for _, s in read)
    return {
        "idle": sum(a["idle"] for a, _ in read),
        "first_call": int(statistics.median(s["first"] or 0 for _, s in read)),
        "cache_ratio": round(sum(s["cache"] for _, s in read) / context, 4) if context else 0.0,
        "cost": sum(s["cost"] for _, s in read),
        "cache_read_cost": sum(s["cr_usd"] for _, s in read),
        "cache_write_cost": sum(s["cw_usd"] for _, s in read),
        "output_cost": sum(s["out_usd"] for _, s in read),
    }


def role_stats(run: pathlib.Path, prefix: str, since: str | None) -> tuple[dict, dict, list[str]]:
    """Per role and per session; the third value lists the sources that were missing. A role's sessions come from
    the agent rows, fresh and cap from `_watch.log`, the other cells from the transcripts of its sessions; a missing
    source leaves the cells it fills None, and a session without a transcript still counts in `sessions`."""
    watch, rows = watch_counts(run, prefix), listed_rows(prefix, since)
    missing = [name for name, source in (("_watch.log", watch), ("claude agents", rows)) if source is None]
    fresh, caps = watch or ({}, {})
    names = [role_of(r.get("name") or "", prefix) for r in rows or []]
    roles = {
        role: {
            "sessions": None if rows is None else names.count(role),
            "fresh": None if watch is None else fresh.get(role, 0),
            "cap": None if watch is None else caps.get(role, 0),
            "idle": None,
            "first_call": None,
            "cache_ratio": None,
            "cost": None,
            "cache_read_cost": None,
            "cache_write_cost": None,
            "output_cost": None,
        }
        for role in {*names, *fresh, *caps}
    }
    sessions: dict[str, dict] = {}
    read: dict[str, list[tuple[dict, dict]]] = {}
    seen: set = set()
    unread = 0
    where = filing(run)
    order: dict[str, list[tuple[str, str]]] = {}
    for r, role in zip(rows or [], names):
        s = session_stats(r["sessionId"], seen)
        if s is None:
            unread += 1
            continue
        sessions[r["sessionId"]] = session_entry(role, s, where)
        read.setdefault(role, []).append((sessions[r["sessionId"]], s))
        order.setdefault(role, []).append((ur.started(r), r["sessionId"]))
    for pairs in order.values():  # rule 3: a session naming no task takes its role's next naming session's tasks
        later: list[str] = []
        for _, sid in sorted(pairs, reverse=True):
            e = sessions[sid]
            if e["tasks"]:
                later = e["tasks"]
            elif later:
                e["tasks"], e["by"], e["per_task"] = list(later), "next", e["cost"] / len(later)
    if unread:
        missing.append("transcripts")
    for role, pairs in read.items():
        roles[role].update(transcript_cells(pairs))
    return roles, sessions, missing


def attribute(tasks: dict[str, dict], sessions: dict[str, dict]) -> None:
    """Each session's cost to its tasks, equally; the row `none` always exists."""
    tasks.setdefault("none", dict(ROW))
    for s in sessions.values():
        for task in s["tasks"] or ["none"]:
            tasks.setdefault(task, dict(ROW))
            tasks[task]["cost"] += s["per_task"]


def minutes(a: str, b: str) -> int | None:
    """The minutes from the `YYYY-MM-DD HH:MM UTC` time of line a to that of line b; None when a line has none or its
    date does not exist."""
    ta, tb = TIME.search(a), TIME.search(b)
    if not ta or not tb:
        return None
    try:
        da, db = (datetime.datetime.strptime(f"{t.group(1)} +0000", "%Y-%m-%d %H:%M %z") for t in (ta, tb))
    except ValueError:
        return None
    return int((db - da).total_seconds()) // 60


def request_minutes(run: pathlib.Path) -> list[dict]:
    out = []
    for name in sorted(p.name for p in run.glob("*.md") if p.name in cf.RECORDS or p.name.startswith("build-log")):
        text = cf.read(run / name)
        replies = [(m.group(1), m.group(2)) for m in cf.REPLY.finditer(text)]
        for m in cf.REQUEST.finditer(text):
            kind, rest = m.group(1), m.group(2)
            key = rest.split(" — ")[0].strip()
            answer = next((r for k, r in replies if k == cf.REQUEST_KINDS.get(kind) and r.startswith(key)), None)
            out.append(
                {
                    "kind": kind,
                    "file": name,
                    "line": cf.line_of(text, m.start()),
                    "minutes": minutes(rest, answer) if answer else None,
                }
            )
    return out


def repeated(run: pathlib.Path) -> dict[str, list[str]]:
    """The findings whose `Checklist:` item is a line of lessons.md (a class that already had a lesson), by item: a
    citation is a line of the section that starts `Checklist:` and holds one `<file>:<line>` token, the rule of
    `measure_manager.py checklist` (judge J1 of the pipeline-fold run), so a mention in prose is none."""
    items: dict[str, list[str]] = {}
    for name in ("critique.md", "verify.md"):
        for ident, _, body in cf.sections(cf.read(run / name)):
            cited = set()
            for line in body.splitlines():
                if line.startswith("Checklist:"):
                    value = line.removeprefix("Checklist:").strip()
                    if mm.CITED.fullmatch(value) and LESSON.search(value):
                        cited.add(value)
            for value in sorted(cited):
                items.setdefault(value, []).append(ident)
    return items


def total(values) -> float | None:
    """The sum of the known values: None when every value is unknown, 0 when there is none."""
    values = list(values)
    known = [v for v in values if v is not None]
    return sum(known) if known or not values else None


def cell(value, form: str = "{}") -> str:
    """A cell of the line or of a table: `n/a` for an unknown value."""
    return "n/a" if value is None else form.format(value)


def score(run: pathlib.Path, prefix: str, since: str | None) -> dict:
    run = pathlib.Path(run)
    tasks = task_counts(run)
    roles, sessions, missing = role_stats(run, prefix, since)
    attribute(tasks, sessions)
    n_sessions, caps, idle, cost, cache_write = (
        total(e[k] for e in roles.values()) for k in ("sessions", "cap", "idle", "cost", "cache_write_cost")
    )
    if cost is None:  # agent rows, but no transcript on this machine: the task costs are unknown too
        for t in tasks.values():
            t["cost"] = None
    read_roles = [s["role"] for s in sessions.values()]
    weights = [(e["cache_ratio"], read_roles.count(r)) for r, e in roles.items() if e["cache_ratio"] is not None]
    ratio = sum(c * w for c, w in weights) / sum(w for _, w in weights) if weights else None
    numbered = [t for t in tasks if t != "none"]
    found = {k: sum(t[k] for t in tasks.values()) for k in (*KINDS, "V_plan", "missed", "rejected")}
    cost_cell, ratio_cell = cell(cost, "${:.2f}"), cell(ratio, "{:.0%}")
    line = (
        f"score {run.name}: tasks {len(numbered)}, findings C {found['C']} A {found['A']} R {found['R']} "
        f"V {found['V']} (plan {found['V_plan']}, missed {found['missed']}), rejected {found['rejected']}, "
        f"sessions {cell(n_sessions)} "
        f"(cap {cell(caps)}, idle {cell(idle)}), cost {cost_cell}, cache-read {ratio_cell}"
    )
    if missing:
        line += f" (n/a: {', '.join(missing)})"
    return {
        "run": run.name,
        "tasks": {k: tasks[k] for k in sorted(tasks, key=lambda t: (t == "none", int(t) if t != "none" else 0))},
        "roles": dict(sorted(roles.items())),
        "attribution": sessions,
        "requests": request_minutes(run),
        "repeated": repeated(run),
        "economy": economy(
            run, prefix, len(numbered), n_sessions, cost, cache_write, sum(found[k] for k in KINDS), missing
        ),
        "cost": cost,
        "missing": missing,
        "line": line,
    }


def table(d: dict) -> str:
    rows = [
        "| task | C | A | R | V | V plan | missed | B | rejected | cost |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for task, t in d["tasks"].items():
        cells = [str(t[k]) for k in (*KINDS, "V_plan", "missed", "B", "rejected")] + [cell(t["cost"], "{:.2f}")]
        rows.append(f"| {task} | {' | '.join(cells)} |")
    rows += [
        "",
        "| role | sessions | fresh | cap | idle | first call | cache read | cost | read $ | write $ | output $ |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for role, e in d["roles"].items():
        cells = [cell(e[k]) for k in ("sessions", "fresh", "cap", "idle")]
        cells += [cell(e["first_call"], "{:,}"), cell(e["cache_ratio"], "{:.0%}")]
        cells += [cell(e[k], "{:.2f}") for k in ("cost", "cache_read_cost", "cache_write_cost", "output_cost")]
        rows.append(f"| {role} | {' | '.join(cells)} |")
    rows += ["", "| request | file:line | minutes |", "|---|---|---:|"]
    for r in d["requests"]:
        rows.append(f"| {r['kind']} | {r['file']}:{r['line']} | {'n/a' if r['minutes'] is None else r['minutes']} |")
    rows += [
        "",
        "repeated lesson classes: " + (", ".join(f"{k} ({', '.join(v)})" for k, v in d["repeated"].items()) or "none"),
    ]
    e = d["economy"]
    cells = [cell(e[k], "${:.2f}") for k in ("cost_per_unit", "cache_write_per_unit")]
    cells += [*(cell(e[k], "{:.1f}") for k in ECONOMY_PER_UNIT), cell(e["escaped"])]
    head = (
        "| units | cost per unit | cache write $ per unit | sessions per unit | copies per unit | findings per unit "
        "| escaped |"
    )
    rows += ["", head, "|---:|---:|---:|---:|---:|---:|---:|", f"| {e['units']} | {' | '.join(cells)} |"]
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="one score per run folder")
    ap.add_argument("run")
    ap.add_argument("--prefix", default="")
    ap.add_argument("--since", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    d = score(pathlib.Path(args.run), args.prefix, args.since)
    if args.json:
        print(json.dumps(d, indent=1))
    else:
        print(d["line"])
        print(table(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
