#!/usr/bin/env python3
"""Findings report of a pipeline's run folder: the stage that caught each defect, and what escaped the gates.

  python3 findings_report.py <run-dir> [--json]

Markdown to stdout: per kind (C, A, B, BK, V, VK, M, O, J, P) the ids defined, answered and open, read as
check_formats.py reads them; V and VK by cause and severity; J by severity; per task (the `## Task N` and
`### Task N` sections of critique.md and verify.md) the C, A and V counts; the escape table, one row per stage that
caught a defect (critic C+A, builder's own B+BK, verifier V+VK, main session M, judge J, owner after the build O)
with its count and share, and the line "escapes past the pipeline's gates: J + O = <n> of <all>". P, the planner's
own findings, comes before the critic and stays out of the table.

An id counts once (a reused heading, `#### V29, round 2`, is the same finding) with its first section's severity and
cause. Severity: `Severity: <word>` in the section's first lines, or an item of a parenthesis in its heading
(`(minor, plan)`, `(code, minor)`, `(major, (plan))`); a word in prose (`is a major change`) is none; `unknown` when
absent. Cause: `(code)`, `(plan)`, `(spec)` or `(brief)` in the heading, else after the body's `Cause`, else anywhere in
the body; `none` when absent. A `### Task M` inside `## Task N` is Task M, another `###` stays in its `## Task N`, a `##`
that names no task is outside one, a `# ` line is no heading (a wrapped comment). The verifier's `#### B<n>` re-checks
are the builder's ids, no V finding. Read-only.
"""

import argparse
import json
import pathlib
import re
import sys

sys.dont_write_bytecode = True  # `python3 -I` ignores PYTHONDONTWRITEBYTECODE; the skill folder stays clean
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_formats as cf

KINDS = ("C", "A", "R", "B", "BK", "V", "VK", "M", "O", "J", "P")
SEVERITIES = ("blocker", "major", "minor", "unknown")
CAUSES = ("code", "plan", "spec", "brief", "none")
STAGES = (
    ("critic", ("C", "A", "R")),
    ("builder's own", ("B", "BK")),
    ("verifier", ("V", "VK")),
    ("main session", ("M",)),
    ("judge", ("J",)),
    ("owner after the build", ("O",)),
)
TASK_KINDS = ("C", "A", "R", "V")
FIRST_LINES = 5  # the lines after the heading that may carry `Severity:`
SEVERITY_LINE = re.compile(r"^[-*\s]*Severity\**\s*:?\**\s*(blocker|major|minor)\b", re.IGNORECASE | re.MULTILINE)
SEVERITY_ITEM = re.compile(r"\((?:[^()]*[,;]\s*)?(blocker|major|minor)\s*[,;)]", re.IGNORECASE)
HEADING_LINE = re.compile(r"^(#{2,4}) ")  # as in check_formats.sections(): a `# ` line (a wrapped comment) is none
TASK_HEADING = re.compile(r"^#{2,3} Task (\d+)\b")
DUPLICATE = re.compile(r"^(\S+?):(\d+): #### (\S+) twice$")


def kind(ident: str) -> str:
    return re.match(r"[A-Z]+", ident).group(0)


def severity(body: str) -> str:
    head, _, rest = body.partition("\n")
    m = SEVERITY_ITEM.search(head) or SEVERITY_LINE.search("\n".join(rest.split("\n")[:FIRST_LINES]))
    return m.group(1).lower() if m else "unknown"


def cause(body: str) -> str:
    head, _, rest = body.partition("\n")
    at = rest.find("Cause")
    for text in (head, rest[at:] if at >= 0 else "", rest):
        m = cf.CAUSE.search(text)
        if m:
            return m.group(1)
    return "none"


def task_ids(text: str) -> list[tuple[str, str]]:
    """Each `#### <id>` heading's id and the task of the section it stands in ("none" outside one)."""
    out: list[tuple[str, str]] = []
    outer = inner = "none"
    for line in text.splitlines():
        m = HEADING_LINE.match(line)
        if not m:
            continue
        task = TASK_HEADING.match(line)
        if len(m.group(1)) == 2:
            outer = inner = task.group(1) if task else "none"
        elif len(m.group(1)) == 3:
            inner = task.group(1) if task else outer
        elif h := cf.HEADING.match(line):
            out.append((h.group(1) + h.group(2), inner))
    return out


def report(run: pathlib.Path) -> dict:
    found = cf.ids(run)
    waiting = {i for ids in found["open"].values() for i in ids}
    extra = tuple(sorted({kind(i) for i in found["defined"]} - set(KINDS)))
    kinds = {k: {"total": 0, "answered": 0, "open": 0} for k in KINDS + extra}
    for ident in found["defined"]:
        row = kinds[kind(ident)]
        row["total"] += 1
        row["open" if ident in waiting else "answered"] += 1

    findings: dict[str, dict] = {}
    for name in ("verify.md", "verify-kb.md", "judge.md"):
        for ident, line, body in cf.sections(cf.read(run / name)):
            if kind(ident) in ("V", "VK", "J") and ident not in findings:
                findings[ident] = {"file": name, "line": line, "severity": severity(body), "cause": cause(body)}
    causes = {k: {c: {s: 0 for s in SEVERITIES} for c in CAUSES} for k in ("V", "VK")}
    by_severity = {"J": {s: 0 for s in SEVERITIES}}
    for ident, f in findings.items():
        if kind(ident) == "J":
            by_severity["J"][f["severity"]] += 1
        else:
            causes[kind(ident)][f["cause"]][f["severity"]] += 1

    tasks: dict[str, dict] = {}
    counted: set[str] = set()
    for name in ("critique.md", "verify.md"):
        for ident, task in task_ids(cf.read(run / name)):
            if kind(ident) not in TASK_KINDS or ident in counted:
                continue
            counted.add(ident)
            row = tasks.setdefault(task, {**{k: 0 for k in TASK_KINDS}, "open": 0})
            row[kind(ident)] += 1
            row["open"] += ident in waiting
    order = sorted((t for t in tasks if t != "none"), key=int) + ["none"] * ("none" in tasks)

    def count(ks: tuple[str, ...]) -> int:
        return sum(kinds[k]["total"] for k in ks)

    everything = sum(count(ks) for _, ks in STAGES)
    escape = [
        {
            "stage": stage,
            "kinds": list(ks),
            "count": count(ks),
            "share": round(100 * count(ks) / everything, 1) if everything else 0.0,
        }
        for stage, ks in STAGES
    ]
    return {
        "run": str(run),
        "kinds": kinds,
        "causes": causes,
        "severity": by_severity,
        "findings": findings,
        "tasks": {t: tasks[t] for t in order},
        "escape": escape,
        "escapes": {"count": count(("J", "O")), "all": everything},
        "not_in_table": {k: kinds[k]["total"] for k in ("P",) + extra},
        "reused": [i for i, n in found["defined"].items() if n > 1],
        "reused_at": [
            f"{m.group(3)} ({m.group(1)}:{m.group(2)})" for m in map(DUPLICATE.match, found["duplicates"]) if m
        ],
    }


def row(*cells: object) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def unknowns(d: dict, ks: tuple[str, ...]) -> list[str]:
    out = []
    for field, missing, label in (("severity", "unknown", "unknown severity"), ("cause", "none", "no cause")):
        ids = [
            f"{i} ({f['file']}:{f['line']})"
            for i, f in d["findings"].items()
            if kind(i) in ks and f[field] == missing and not (field == "cause" and kind(i) == "J")
        ]
        if ids:
            out.append(f"{label}: " + ", ".join(ids))
    return out


def markdown(d: dict) -> str:
    out = [
        f"# Findings report: {d['run']}",
        "",
        "## Per kind",
        "",
        row("kind", "total", "answered", "open"),
        "|---|---:|---:|---:|",
    ]
    out += [row(k, r["total"], r["answered"], r["open"]) for k, r in d["kinds"].items()]
    out.append(row("all", *(sum(r[c] for r in d["kinds"].values()) for c in ("total", "answered", "open"))))
    if d["reused_at"]:
        out += ["", "reused headings, counted once: " + ", ".join(d["reused_at"])]
    for k in ("V", "VK"):
        if k == "VK" and not d["kinds"]["VK"]["total"]:
            continue
        table = d["causes"][k]
        out += ["", f"## {k} by cause and severity", "", row("cause", *SEVERITIES, "total"), "|---" + "|---:" * 5 + "|"]
        out += [row(c, *(table[c][s] for s in SEVERITIES), sum(table[c].values())) for c in CAUSES]
        totals = [sum(table[c][s] for c in CAUSES) for s in SEVERITIES]
        out.append(row("total", *totals, sum(totals)))
        out += [""] * bool(unknowns(d, (k,))) + unknowns(d, (k,))
    j = d["severity"]["J"]
    out += [
        "",
        "## J by severity",
        "",
        row("kind", *SEVERITIES, "total"),
        "|---" + "|---:" * 5 + "|",
        row("J", *(j[s] for s in SEVERITIES), sum(j.values())),
    ]
    out += [""] * bool(unknowns(d, ("J",))) + unknowns(d, ("J",))
    out += [
        "",
        "## Per task (sections of critique.md and verify.md)",
        "",
        row("task", *TASK_KINDS, "open"),
        "|---" + "|---:" * (len(TASK_KINDS) + 1) + "|",
    ]
    for t, r in d["tasks"].items():
        out.append(row("no task section" if t == "none" else f"Task {t}", *(r[k] for k in TASK_KINDS), r["open"]))
    out.append(row("total", *(sum(r[k] for r in d["tasks"].values()) for k in TASK_KINDS + ("open",))))
    out += [
        "",
        "## Escape table: the stage that caught each defect",
        "",
        row("stage", "kinds", "count", "share"),
        "|---|---|---:|---:|",
    ]
    out += [row(e["stage"], " + ".join(e["kinds"]), e["count"], f"{e['share']}%") for e in d["escape"]]
    everything = d["escapes"]["all"]
    out += [
        f"| all | | {everything} | {100 if everything else 0}% |",
        "",
        f"escapes past the pipeline's gates: J + O = {d['escapes']['count']} of {everything}",
        "",
        "not in the table: "
        + ", ".join(f"{k} = {n}" for k, n in d["not_in_table"].items())
        + " (P: the planner's own findings, before the critic)",
    ]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    run = pathlib.Path(args.run_dir)
    if not run.is_dir():
        print(f"findings_report.py: no such folder: {run}", file=sys.stderr)
        return 2
    d = report(run)
    print(json.dumps(d, ensure_ascii=False, indent=1) if args.json else markdown(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
