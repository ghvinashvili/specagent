"""`harness pipeline-report`: findings per task from a run folder's record files, against a baseline."""

from __future__ import annotations

import ast
import json
import shutil
from pathlib import Path

import pytest
from harness import cli, pipeline_report

ROOT = Path(__file__).resolve().parents[3]
CRITIQUE = """STATUS: reviewed through Task 2

## Task 1
#### C1 — major — the parser drops the last line
- Plan: the step reads the file without its last line.
#### A1 — added test
- Input: a file of one line.

## Task 2
#### C2 — blocker — the build step names no output
- Plan: the step writes nothing.
#### C2, round 2 — blocker — the fix names an output that nothing reads
- Plan: the second version.
"""
VERIFY = """STATUS: verified through Task 2

## Task 2
#### V1 (code, minor) — a flag is not documented
- Found: `--fast` is missing from the README.
"""
BUILD_LOG = "STATUS: done\nTask 1: done — abc1234\nTask 2: done — def5678\nTask 2: done — 0123abc\n"
RECORDS = {"critique.md": CRITIQUE, "verify.md": VERIFY, "build-log-a.md": BUILD_LOG}
ZERO = dict.fromkeys(("blocker", "major", "minor", "unknown"), 0)


@pytest.fixture()
def run(tmp_path):
    """Two done tasks and the critic's and the verifier's findings; no transcript and no _agents.json."""
    r = tmp_path / "run"
    r.mkdir()
    for name, text in RECORDS.items():
        (r / name).write_text(text, encoding="utf-8")
    return r


def test_findings_per_task_by_role_and_severity_with_their_rounds(run):
    assert sorted(vars(pipeline_report.skill(ROOT))) == ["findings", "formats", "startup", "usage"]
    assert pipeline_report.build(ROOT, run)["tasks"] == {
        "1": {"critic": {**ZERO, "major": 1, "unknown": 1}, "verifier": ZERO, "rounds": {"C1": 1, "A1": 1}},
        "2": {"critic": {**ZERO, "blocker": 1}, "verifier": {**ZERO, "minor": 1}, "rounds": {"C2": 2, "V1": 1}},
    }


def test_the_summary_and_its_values_per_done_task(run):
    summary = {"tasks": 2, "findings": 4, "rounds_per_finding": 1.25, "per_task": {"findings": 2.0}}
    assert pipeline_report.build(ROOT, run)["summary"] == summary
    (run / "build-log-a.md").write_text("STATUS: building\n", encoding="utf-8")
    assert pipeline_report.build(ROOT, run)["summary"] == {**summary, "tasks": 0, "per_task": {"findings": None}}


def test_the_ratios_to_a_baseline(run):
    base = json.loads(json.dumps(pipeline_report.as_baseline(pipeline_report.build(ROOT, run), "twice")))
    s = base["summary"]
    s["per_task"]["findings"], s["rounds_per_finding"] = 4.0, 2.5
    ratio = pipeline_report.build(ROOT, run, baseline=base)["baseline"]
    assert ratio == {"label": "twice", "ratio": {"findings": 0.5, "rounds_per_finding": 0.5}}
    s["per_task"]["findings"], s["rounds_per_finding"] = 0, None
    again = pipeline_report.build(ROOT, run, baseline=base)["baseline"]["ratio"]
    assert again == {"findings": None, "rounds_per_finding": None}


def test_write_puts_three_files_under_evals_results_and_a_baseline_holds_no_path(run, tmp_path):
    report = pipeline_report.build(ROOT, run)
    out = pipeline_report.write(tmp_path, report)
    md = (out / "pipeline-report.md").read_text(encoding="utf-8")
    assert out.parent == tmp_path / "evals" / "results"
    assert json.loads((out / "pipeline-report.json").read_text(encoding="utf-8")) == report
    assert "| Task | critic | verifier | rounds |" in md
    assert "| 1 | major 1, unknown 1 | — | 2 |" in md
    assert "| 2 | blocker 1 | minor 1 | 3 |" in md
    assert len((out / "pipeline-report.summary.md").read_text(encoding="utf-8").splitlines()) <= 12
    assert "Usage: not available — no --prefix given" in md
    base = pipeline_report.as_baseline(report, "demo run")
    assert (sorted(base), base["label"], base["summary"]) == (
        ["label", "schema_version", "summary"],
        "demo run",
        report["summary"],
    )
    assert "/" not in json.dumps(base["summary"])


def test_the_committed_baseline_comes_from_an_earlier_run_and_names_no_path_or_project():
    text = (ROOT / pipeline_report.BASELINE).read_text(encoding="utf-8")
    base = json.loads(text)
    assert (base["schema_version"], base["label"]) == (1, "an earlier run of the owner's pipeline, 2026-10")
    assert sorted(base["summary"]) == ["findings", "per_task", "rounds_per_finding", "tasks"]
    assert base["summary"]["tasks"] > 0
    assert "/" not in text
    words = ["grants" + "daily", "DD" + "EV", "PHP" + "Unit", "Dru" + "pal"]
    assert [w for w in words if w.lower() in text.lower()] == []


def test_the_cli_writes_a_report_and_a_baseline_and_refuses_an_empty_folder(run, tmp_path, monkeypatch, capsys):
    root = tmp_path / "root"
    (root / pipeline_report.SKILL_SCRIPTS).mkdir(parents=True)
    for name in ("findings_report.py", "check_formats.py", "usage_report.py", "startup_report.py"):
        shutil.copy2(ROOT / pipeline_report.SKILL_SCRIPTS / name, root / pipeline_report.SKILL_SCRIPTS / name)
    monkeypatch.chdir(root)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))  # no `claude` here: the prefix reaches `agent_rows`, which raises
    assert cli.main(["pipeline-report", str(run), "--prefix", "demo/"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert (out["ok"], out["baseline"], out["summary"]["tasks"], out["usage"]["available"]) == (True, None, 2, False)
    assert out["usage"]["detail"] == "claude agents: [Errno 2] No such file or directory: 'claude'"
    assert (root / out["results"] / "pipeline-report.json").is_file()
    assert cli.main(["pipeline-report", str(run), "--as-baseline", "base.json", "--label", "demo run"]) == 0
    assert json.loads(capsys.readouterr().out)["written"] == "base.json"
    assert json.loads((root / "base.json").read_text(encoding="utf-8"))["label"] == "demo run"
    with pytest.raises(SystemExit):
        cli.main(["pipeline-report", str(run), "--as-baseline", "base.json"])
    empty = tmp_path / "empty"
    empty.mkdir()
    assert cli.main(["pipeline-report", str(empty)]) == 1
    problem = f"{empty}: no critique.md, verify.md or build-log*.md"
    assert json.loads(capsys.readouterr().out) == {"ok": False, "problems": [problem]}


def test_a_diff_finding_counts_as_the_critics(run):
    with (run / "critique.md").open("a", encoding="utf-8") as f:
        f.write("\n## Task 2 (diff)\n#### R1 — (code, major) the new flag is never read\n- Diff: `--fast` is unread.\n")
    report = pipeline_report.build(ROOT, run)
    assert report["tasks"]["2"] == {
        "critic": {**ZERO, "blocker": 1, "major": 1},
        "verifier": {**ZERO, "minor": 1},
        "rounds": {"C2": 2, "V1": 1, "R1": 1},
    }
    assert report["summary"] == {"tasks": 2, "findings": 5, "rounds_per_finding": 1.2, "per_task": {"findings": 2.5}}


def test_the_usage_part_needs_a_prefix_counts_a_roles_calls_and_says_when_it_cannot(run, tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))  # no `claude` here: a call raises FileNotFoundError
    assert pipeline_report.build(ROOT, run)["usage"] == {"available": False, "detail": "no --prefix given"}
    sk, write = pipeline_report.skill(ROOT), [{"type": "tool_use", "name": "Write", "input": {}}]
    rows, m1 = sk.usage.agent_rows, ("m1", [], 9000)
    calls = [("s1", *m1, "00:00"), ("s1", *m1, "00:01"), ("s1", "m2", write, 19000, "00:02"), ("s2", *m1, "00:00")]
    for s, i, c, r, t in [*calls, ("s2", "m3", [], 59000, "10:01"), ("s3", "m4", write, 29000, "20:01")]:
        m = {"id": i, "content": c, "usage": {"input_tokens": 1000, "cache_read_input_tokens": r, "output_tokens": 500}}
        with (tmp_path / f"{s}.jsonl").open("a", encoding="utf-8") as f:  # no "model" key; s2 begins with s1's m1
            f.write(json.dumps({"timestamp": f"2026-10-29T06:{t}.000Z", "message": m}) + "\n")
    listed = [{"name": "demo/builder", "sessionId": s} for s in ("s1", "s2", "s3")]
    listed[1]["startedAt"] = 1793254200000  # 06:10:00Z, after s2's first call: s2 is resumed, not a hand-over
    monkeypatch.setattr(sk.usage, "agent_rows", lambda prefix: listed)
    monkeypatch.setattr(sk.usage, "transcripts", lambda sid: [str(tmp_path / f"{sid}.jsonl")])
    part = pipeline_report.usage(sk, "demo/")
    role = part["roles"]["demo/builder"]
    assert part == {"available": True, "prefix": "demo/", "roles": {"demo/builder": role}} and role["cost"] > 0
    counts = {"sessions": 3, "handovers": 1, "calls": 4, "context_per_call": 30000, "startup_median": 25000.0}
    assert role == {**counts, "wall_seconds": 1201.0, "cost": pytest.approx(0.0792)}
    md = pipeline_report.write(tmp_path, {**pipeline_report.build(ROOT, run), "usage": part}) / "pipeline-report.md"
    assert f"| demo/builder | 3 | 1 | 4 | 30000 | 25000.0 | 1201.0 | {role['cost']} |" in md.read_text(encoding="utf-8")
    monkeypatch.setattr(sk.usage, "transcripts", lambda sid: [])
    assert pipeline_report.usage(sk, "demo/")["detail"] == "sessions listed: 3, readable transcripts: 0"
    monkeypatch.setattr(sk.usage, "agent_rows", rows)
    no_claude = "claude agents: [Errno 2] No such file or directory: 'claude'"
    assert pipeline_report.usage(sk, "demo/") == {"available": False, "detail": no_claude}


def test_no_function_this_task_writes_or_changes_reaches_50_lines():
    paths = [ROOT / "packages/harness/src/harness" / n for n in ("cli.py", "evals.py", "pipeline_report.py")]
    paths += [ROOT / "evals/graders" / n for n in ("pipeline_plan.py", "pipeline_note.py")]
    nodes = [(p.name, n) for p in paths for n in ast.walk(ast.parse(p.read_text(encoding="utf-8")))]
    sizes = [(name, n.name, n.end_lineno - n.lineno + 1) for name, n in nodes if isinstance(n, ast.FunctionDef)]
    assert [s for s in sorted(sizes) if s[2] >= 50] == [("evals.py", "grade", 61), ("evals.py", "run_session", 104)]
