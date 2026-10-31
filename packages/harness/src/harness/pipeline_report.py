"""`harness pipeline-report`: a pipeline run's findings per task by role and severity, and their rounds, from the run
folder's record files (critique.md, verify.md, build-log*.md) read through the pipelines skill's report scripts, against
a baseline of an earlier run. With --prefix also each role's usage from the session transcripts, which only the main
session can read (docs/decisions/0028-pipeline-evals.md)."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

SKILL_SCRIPTS = ".claude/skills/running-specagent-pipelines/scripts"
BASELINE = "evals/baseline/pipeline/earlier-run.json"
SEVERITIES = ("blocker", "major", "minor", "unknown")
ROLES = {"C": "critic", "A": "critic", "R": "critic", "V": "verifier"}  # R<n>: the critic's findings on a diff
HEADING_SEVERITY = re.compile(r"^#### [A-Z]{1,2}\d+ — (blocker|major|minor) —", re.IGNORECASE)
USAGE = ("sessions", "handovers", "calls", "context_per_call", "startup_median", "wall_seconds", "cost")


def skill(root: Path) -> SimpleNamespace:
    """The skill's four report scripts from root / SKILL_SCRIPTS. Each goes into sys.modules under its own name before
    the next, so findings_report's `import check_formats` and startup_report's `import usage_report` take these
    copies; no bytecode is written into the skill's folder, and sys.path is left as it was."""
    saved = sys.path[:], sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    loaded = {}
    try:
        for name in ("check_formats", "findings_report", "usage_report", "startup_report"):
            spec = importlib.util.spec_from_file_location(name, root / SKILL_SCRIPTS / f"{name}.py")
            loaded[name] = sys.modules[name] = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(loaded[name])
    finally:
        sys.path[:], sys.dont_write_bytecode = saved
    return SimpleNamespace(
        findings=loaded["findings_report"],
        formats=loaded["check_formats"],
        usage=loaded["usage_report"],
        startup=loaded["startup_report"],
    )


def _severity(sk: SimpleNamespace, body: str) -> str:
    """The skill's severity of a finding's section; for `unknown` the word of a heading `#### <id> — <word> —`."""
    word = sk.findings.severity(body)
    m = HEADING_SEVERITY.match(body) if word == "unknown" else None
    return m.group(1).lower() if m else word


def findings(run: Path, sk: SimpleNamespace) -> dict:
    """Per task the critic's and the verifier's finding ids by severity, and each id's rounds (the times its heading
    is written). An id counts once, in the task of its first heading in critique.md, then verify.md; C, A and R are
    the critic's, V the verifier's, and the other kinds are left out."""
    rounds = sk.formats.ids(run)["defined"]
    tasks: dict[str, dict] = {}
    counted: set[str] = set()
    for name in ("critique.md", "verify.md"):
        text = sk.formats.read(run / name)
        bodies: dict[str, str] = {}
        for ident, _, body in sk.formats.sections(text):
            bodies.setdefault(ident, body)
        for ident, task in sk.findings.task_ids(text):
            role = ROLES.get(sk.findings.kind(ident))
            if role is None or ident in counted:
                continue
            counted.add(ident)
            entry = tasks.setdefault(
                task, {"critic": dict.fromkeys(SEVERITIES, 0), "verifier": dict.fromkeys(SEVERITIES, 0), "rounds": {}}
            )
            entry[role][_severity(sk, bodies.get(ident, ""))] += 1
            entry["rounds"][ident] = rounds.get(ident, 1)
    return tasks


def done_tasks(run: Path, sk: SimpleNamespace) -> int:
    """The number of distinct tasks that a `Task N: done — <sha>` line of any build-log*.md names."""
    return len(
        {int(m.group(1)) for p in run.glob("build-log*.md") for m in sk.formats.DONE.finditer(sk.formats.read(p))}
    )


def summary(tasks: dict, done: int) -> dict:
    """The run's figures: done tasks, the findings counted, rounds per finding and findings per done task."""
    rounds = [n for entry in tasks.values() for n in entry["rounds"].values()]
    return {
        "tasks": done,
        "findings": len(rounds),
        "rounds_per_finding": round(sum(rounds) / len(rounds), 4) if rounds else None,
        "per_task": {"findings": round(len(rounds) / done, 4) if done else None},
    }


def _price(sk: SimpleNamespace, message: dict) -> float:
    """A call's API-equivalent cost, as usage_report.py prices it (by the model's family, opus without a model)."""
    u, p = message["usage"], sk.usage.PRICE[sk.usage.family(message.get("model"))]
    keys = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
    i, cw, cr, o = (u.get(k) or 0 for k in keys)
    return (i * p[0] + o * p[1] + cr * p[2] + cw * p[3]) / 1e6


def _role(sk: SimpleNamespace, sessions: list[tuple[list[dict], dict | None]]) -> dict:
    """One role's figures from its sessions, each its calls and its start-up (startup_report.startup)."""
    calls = [d for made, _ in sessions for d in made]
    costs = [s["cost"] for _, s in sessions if s and s.get("cost") is not None]
    fresh = sum(1 for _, s in sessions if s != {"resumed": True})
    times = sorted(dt.datetime.fromisoformat(d["timestamp"]) for d in calls if d.get("timestamp"))
    return {
        "sessions": len(sessions),
        "handovers": max(fresh - 1, 0),
        "calls": len(calls),
        "context_per_call": sum(sk.usage.context(d["message"]["usage"]) for d in calls) // len(calls),
        "startup_median": round(statistics.median(costs), 4) if costs else None,
        "wall_seconds": round((times[-1] - times[0]).total_seconds(), 4) if times else None,
        "cost": round(sum(_price(sk, d["message"]) for d in calls), 4),
    }


def usage(sk: SimpleNamespace, prefix: str | None) -> dict:
    """Each role's sessions, hand-overs, calls, context per call, start-up, wall time and cost, from the transcripts
    of the agents whose names start with prefix. Only with a prefix: it runs `claude agents` and reads
    ~/.claude/projects, which only the main session can; it says why when it cannot, never zeros."""
    if prefix is None:
        return {"available": False, "detail": "no --prefix given"}
    try:
        rows = sk.usage.agent_rows(prefix)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return {"available": False, "detail": f"claude agents: {exc}"}
    seen: set = set()  # one for every row: a resumed session's transcript begins with the calls it resumes
    per: dict[str, list] = {}
    for row in rows:
        paths = sorted(sk.usage.transcripts(row["sessionId"]))
        made = [d for path in paths for d in sk.usage.calls(path, seen)]
        if made:
            per.setdefault(row.get("name") or "", []).append((made, sk.startup.startup(paths, sk.usage.started(row))))
    if not per:
        return {"available": False, "detail": f"sessions listed: {len(rows)}, readable transcripts: 0"}
    return {"available": True, "prefix": prefix, "roles": {name: _role(sk, s) for name, s in per.items()}}


def _ratio(mine: float | None, base: float | None) -> float | None:
    return None if mine is None or not base else round(mine / base, 4)


def build(root: Path, run: Path, baseline: dict | None = None, prefix: str | None = None) -> dict:
    """The report of a run folder from its record files, and its ratios to a baseline's summary."""
    if not (run / "critique.md").is_file() and not (run / "verify.md").is_file() and not any(run.glob("build-log*.md")):
        return {"ok": False, "problems": [f"{run}: no critique.md, verify.md or build-log*.md"]}
    sk = skill(root)
    tasks = findings(run, sk)
    mine = summary(tasks, done_tasks(run, sk))
    ratio = None
    if baseline is not None:
        base = baseline["summary"]
        ratio = {
            "label": baseline["label"],
            "ratio": {
                "findings": _ratio(mine["per_task"]["findings"], base["per_task"]["findings"]),
                "rounds_per_finding": _ratio(mine["rounds_per_finding"], base["rounds_per_finding"]),
            },
        }
    name = run.resolve().name
    return {"ok": True, "run": name, "tasks": tasks, "summary": mine, "baseline": ratio, "usage": usage(sk, prefix)}


def _text(value: object) -> str:
    return "—" if value is None else str(value)


def _cell(counts: dict) -> str:
    return ", ".join(f"{s} {counts[s]}" for s in SEVERITIES if counts.get(s)) or "—"


def _task_order(task: str) -> tuple:
    return (not task.isdigit(), int(task) if task.isdigit() else 0, task)


def _markdown(report: dict) -> str:
    """The task table, the summary and the ratios, then the usage part."""
    s, b, u = report["summary"], report["baseline"], report["usage"]
    lines = [f"# Pipeline report: {report['run']}", "", "| Task | critic | verifier | rounds |", "|---|---|---|---|"]
    for task in sorted(report["tasks"], key=_task_order):
        t = report["tasks"][task]
        lines.append(f"| {task} | {_cell(t['critic'])} | {_cell(t['verifier'])} | {sum(t['rounds'].values())} |")
    lines += [
        "",
        (
            f"Done tasks: {s['tasks']}. Findings: {s['findings']}. Rounds per finding: {_text(s['rounds_per_finding'])}. "
            f"Findings per done task: {_text(s['per_task']['findings'])}."
        ),
        "",
        "Baseline: none."
        if b is None
        else f'Against the baseline "{b["label"]}": findings per done task x{_text(b["ratio"]["findings"])}, '
        f"rounds per finding x{_text(b['ratio']['rounds_per_finding'])}.",
        "",
    ]
    if not u["available"]:
        return "\n".join([*lines, f"Usage: not available — {u['detail']}", ""])
    header = "| Role | sessions | hand-overs | calls | context per call | start-up | wall s | cost |"
    rows = [f"| {name} | " + " | ".join(_text(r[k]) for k in USAGE) + " |" for name, r in u["roles"].items()]
    return "\n".join([*lines, f"Usage of the agents named {u['prefix']}*:", "", header, "|---" * 8 + "|", *rows, ""])


def _words(report: dict) -> str:
    """The summary, the ratios and the usage part in words, in at most 12 lines."""
    s, b, u = report["summary"], report["baseline"], report["usage"]
    lines = [
        f"# Pipeline report: {report['run']}",
        "",
        (
            f"{s['tasks']} tasks done, {s['findings']} findings ({_text(s['per_task']['findings'])} per done task), "
            f"{_text(s['rounds_per_finding'])} rounds per finding."
        ),
        "No baseline to compare with."
        if b is None
        else f'Against the baseline "{b["label"]}": findings per done task x{_text(b["ratio"]["findings"])}, '
        f"rounds per finding x{_text(b['ratio']['rounds_per_finding'])}.",
    ]
    if not u["available"]:
        return "\n".join([*lines, f"Usage: not available — {u['detail']}.", ""])
    roles = u["roles"]
    top = max(roles, key=lambda name: roles[name]["cost"])
    total = round(sum(r["cost"] for r in roles.values()), 4)
    lines.append(
        f"Usage of the {len(roles)} roles named {u['prefix']}*: {sum(r['sessions'] for r in roles.values())} sessions, "
        f"{sum(r['handovers'] for r in roles.values())} hand-overs, {sum(r['calls'] for r in roles.values())} calls, "
        f"{total} dollars at API list prices; the costliest role is {top} ({roles[top]['cost']})."
    )
    return "\n".join([*lines, ""])


def write(root: Path, report: dict) -> Path:
    """evals/results/<stamp>/ with pipeline-report.json, .md and .summary.md (git-ignored); returns the folder."""
    out = root / "evals" / "results" / dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    (out / "pipeline-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "pipeline-report.md").write_text(_markdown(report), encoding="utf-8")
    (out / "pipeline-report.summary.md").write_text(_words(report), encoding="utf-8")
    return out


def as_baseline(report: dict, label: str) -> dict:
    """A baseline file's content: the run's summary under a label, and no path."""
    return {"schema_version": 1, "label": label, "summary": report["summary"]}


def command(
    root: Path,
    run: Path,
    baseline: Path | None = None,
    as_baseline_file: str | None = None,
    label: str | None = None,
    prefix: str | None = None,
) -> dict:
    """`harness pipeline-report`: the report against the baseline given, else BASELINE when it exists, written under
    evals/results/<stamp>/; with `as_baseline_file` this run's summary written there as a baseline instead."""
    given = root / baseline if baseline else root / BASELINE if (root / BASELINE).is_file() else None
    report = build(root, run, json.loads(given.read_text(encoding="utf-8")) if given else None, prefix)
    if not report["ok"]:
        return report
    if as_baseline_file:
        target = root / as_baseline_file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(as_baseline(report, label), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return {"ok": True, "written": as_baseline_file, "summary": report["summary"]}
    out = write(root, report)
    keys = ("summary", "baseline", "usage")
    return {"ok": True, "results": str(out.relative_to(root)), **{k: report[k] for k in keys}}
