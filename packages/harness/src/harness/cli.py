"""harness — command line entry point. Every command reads and writes only the run directory
(<runs root>/<run-id>/, outside the repository; see state.runs_root) and docs/generated/."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import (
    access,
    audit,
    cache_report,
    catalog,
    doctor,
    extensions,
    gates,
    intake,
    launch,
    leftovers,
    limits,
    loops,
    notify,
    pack,
    pause,
    plans,
    poll,
    resume,
    select,
    stagemap,
    state,
    wiki,
    work,
)


def root_dir() -> Path:
    import os

    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()).resolve()


# Every command that takes --run, and what it does to a run. A command that changes a run refuses an aborted one before
# it does anything (docs/decisions/0010); tests/test_abort.py takes the commands from the parser and fails on one that
# is not here. `poll` and `watch` read: an aborted run is reported, not polled. A second `abort` only reports.
RUN_COMMANDS = {
    "status": "reads",
    "assign": "changes",
    "launch": "changes",
    "poll": "reads",
    "resume": "changes",
    "gate": "changes",
    "approve": "changes",
    "refreeze": "changes",
    "integrate": "changes",
    "escalations": "reads",
    "handoff": "changes",
    "limits": "reads",
    "material": "changes",  # builds the inputs of a stage that has none yet
    "cache-report": "reads",
    "watch": "reads",
    "route": "reads",
    "abort": "reads",
    "steps": "reads",
}


# The commands a role session or one of its hooks runs, and where it is told to; with HARNESS_ROLE set every other
# command refuses, also one added later (docs/decisions/0019). `gate` only as the preview, `loop` only as `validate`.
ROLE_COMMANDS = {
    "gate": "--preview, by the stop hook before a session may end with complete (.claude/hooks/stop-gate.py)",
    "validate": "the checks of a writer's work (.github/workflows/ci.yml; the brief of a fix run)",
    "docs-check": "the checks of a writer's work (.github/workflows/docs-lint.yml; the brief of a fix run)",
    "plan-lint": "the checks of a writer's work, also inside docs-check (.github/workflows/docs-lint.yml)",
    "map": "the checks of a writer's work, and the maps of a stage table it changed (the brief of a fix run)",
    "version-check": "the checks of a writer's work (.github/workflows/evals.yml; the brief of a fix run)",
    "audit": "the checks of a writer's work (.github/workflows/ci.yml)",
    "loop": "`validate` only, the checks of a writer's work (.github/workflows/ci.yml)",
    "wiki-lint": "the librarian's check (.claude/agents/librarian.md)",
    "skill-usage": "the analyst's evidence (.claude/agents/analyst.md)",
    "steps": "reads a finished run and writes nothing (docs/roles/CHANGELOG.md, 1.6.0)",
}


def role_may_run(a: argparse.Namespace) -> bool:
    """Whether a role session may run the command it asked for (ROLE_COMMANDS)."""
    if a.cmd == "gate":
        return bool(a.preview)
    if a.cmd == "loop":
        return a.op == "validate"
    return a.cmd in ROLE_COMMANDS


def _refuse_role(a: argparse.Namespace) -> dict | None:
    """A role session does not steer its run: every session may run `uv run *`, and some of these commands run
    outside the sandbox. It asks through an escalation (docs/decisions/0010, docs/decisions/0019)."""
    role = os.environ.get("HARNESS_ROLE")
    if not role:
        return None
    why = (
        "a role session does not steer its run; it writes an escalation. A session that is not a role session and "
        "still has HARNESS_ROLE took it from the background service: see `harness doctor`"
    )
    return {"ok": False, "status": "role_session", "role": role, "command": a.cmd, "why": why}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="harness")
    sub = p.add_subparsers(dest="cmd", required=True)
    for add in (_parsers_run, _parsers_steer, _parsers_checks, _parsers_tools, _parsers_control, _parsers_report):
        add(sub)
    return p


def _parsers_run(sub: argparse._SubParsersAction) -> None:
    """The parsers of run, status, assign, launch and poll."""
    s = sub.add_parser("run", help="create <runs root>/<run-id>/ (outside the repository) from a brief")
    s.add_argument("--slug", required=True)
    s.add_argument("--brief", required=True)
    s.add_argument(
        "--context", action="append", default=[], help="material path relative to the repository; repeatable"
    )
    s.add_argument(
        "--pipeline",
        default="default",
        help="stage table: docs/roles/stages.yaml (default) or docs/roles/pipelines/<name>.yaml",
    )
    s.add_argument(
        "--effort",
        action="append",
        default=[],
        metavar="STAGE=LEVEL",
        help="the effort of one stage for this run (low, medium, high, xhigh, max); repeatable",
    )
    s = sub.add_parser("status")
    s.add_argument("--run", required=True)
    s.add_argument("--stage", required=True)
    s.add_argument("--shard", type=int)
    s = sub.add_parser(
        "assign", help="store the assignment of a stage: what you would write into the prompt of a subagent for the job"
    )
    s.add_argument("--run", required=True)
    s.add_argument("--stage", required=True)
    s.add_argument("--file", help="the text; default: <run>/assignments/drafts/<stage>.md")
    s = sub.add_parser(
        "launch", help="launch a stage; a `parallel: per_task` stage launches every shard unless --shard is given"
    )
    s.add_argument("--run", required=True)
    s.add_argument("--stage", required=True)
    s.add_argument("--shard", type=int)
    s = sub.add_parser("poll")
    s.add_argument("--run")
    s.add_argument("--all-active", action="store_true")


def _parsers_steer(sub: argparse._SubParsersAction) -> None:
    """The parsers of resume, gate, approve, refreeze, integrate, escalations, handoff and select."""
    s = sub.add_parser("resume")
    s.add_argument("--run", required=True)
    s.add_argument("--stage", required=True)
    s.add_argument("--shard", type=int)
    s.add_argument("--escalation")
    s.add_argument("--message")
    s.add_argument(
        "--rework",
        action="store_true",
        help="continue a unit a loop sent back (rework) or asks to check again (recheck)",
    )
    s = sub.add_parser("gate")
    s.add_argument("--run", required=True)
    s.add_argument("--stage", required=True)
    s.add_argument("--shard", type=int)
    s.add_argument(
        "--preview",
        action="store_true",
        help="print the checks that would fail now and record nothing; the stop hook of a role session asks this",
    )
    s = sub.add_parser("approve")
    s.add_argument("--run", required=True)
    s.add_argument("--stage", required=True)
    s.add_argument("--decision", choices=["approved", "rejected"], required=True)
    s = sub.add_parser(
        "refreeze",
        help="a human accepts a configuration change made during a run (settings, .mcp.json, agents, skills, hooks, rules)",
    )
    s.add_argument("--run", required=True)
    s = sub.add_parser(
        "integrate",
        help="after the last approval: one branch `run/<run-id>` with everything the run committed, for the human to merge; --clean also removes the run's checkouts",
    )
    s.add_argument("--run", required=True)
    s.add_argument("--clean", action="store_true")
    s = sub.add_parser("escalations")
    s.add_argument("--run", required=True)
    s.add_argument("--stage")
    s = sub.add_parser("handoff")
    s.add_argument("--run", required=True)
    s = sub.add_parser("select")
    s.add_argument("request")


def _parsers_checks(sub: argparse._SubParsersAction) -> None:
    """The parsers of catalog, validate, docs-check, plan-lint, map, eval, mcp-state and loop."""
    sub.add_parser("catalog", help="validate role types and write docs/generated/role-types.md")
    sub.add_parser("validate", help="repository self-check: schemas, role types, skills, settings, stages table")
    sub.add_parser(
        "docs-check",
        help="docs/llms.txt and the folder indexes it links, relative links outside code, index sizes, plan folders; "
        "missing summaries and specs that are not under 8,000 bytes as warnings",
    )
    sub.add_parser(
        "plan-lint",
        help="plan folders under docs/exec-plans/active/: each task the 00-index.md names exists, starts with "
        "'# Task N' and has at most 1,500 lines; no task file is outside the order; each task-NN.code.md has its "
        "task file and defines once every Block <id> its steps name, and no other",
    )
    s = sub.add_parser(
        "map",
        help="write one Mermaid flowchart per stage table to docs/generated/maps/<name>.md; --check compares",
    )
    s.add_argument("--check", action="store_true", help="list stale or missing maps; write nothing")
    s = sub.add_parser(
        "eval",
        help="run an eval suite headless (claude -p --agent <type>) in a temporary, trusted copy of the harness configuration, with the launcher's flags and environment, and grade the outcomes",
    )
    s.add_argument("--suite", choices=["capability", "regression"], required=True)
    s.add_argument("--case")
    s.add_argument("--threshold", type=float, default=0.9)
    s.add_argument("--baseline", action="store_true")
    s.add_argument(
        "--no-sessions",
        action="store_true",
        help="only the cases with session: false, graded by code without a model",
    )
    sub.add_parser("mcp-state", help="serve run state over MCP (stdio)")
    s = sub.add_parser("loop", help="loop layer: validate every docs/loops/*.yaml, show loop state, or run one tick")
    s.add_argument("op", choices=["validate", "status", "tick", "due"])
    s.add_argument("--name")
    s.add_argument("--plain", action="store_true", help="due: print only the message for the night session")


def _parsers_tools(sub: argparse._SubParsersAction) -> None:
    """The parsers of audit, skill-usage, version-check, limits, wiki-lint, pack, material, cache-report and steps."""
    s = sub.add_parser(
        "audit",
        help="context budget: always-loaded instructions, hook injections, skills, MCP servers against docs/quality/context-budget.yaml",
    )
    s.add_argument("--ci", action="store_true")
    s = sub.add_parser("skill-usage", help="skill activations per run from the skill-audit hook logs")
    s.add_argument("--runs", type=int, default=20)
    s = sub.add_parser(
        "version-check",
        help="instruction files changed since <base> require a docs/roles/VERSION bump and a CHANGELOG entry",
    )
    s.add_argument("--base", required=True)
    s = sub.add_parser("limits", help="units stopped by an API limit or error, with the time to wait")
    s.add_argument("--run")
    sub.add_parser(
        "wiki-lint", help="wiki/: index completeness, orphans, dead links, missing sources, expired or oversized pages"
    )
    s = sub.add_parser(
        "pack", help="the knowledge pack of a role type (harness/pack.py), or every pack against the budget"
    )
    s.add_argument("--type")
    s.add_argument("--check", action="store_true")
    s = sub.add_parser("material", help="the pieces a stage's session gets in its cached prompt, and why (no model)")
    s.add_argument("--run", required=True)
    s.add_argument("--stage", required=True)
    s = sub.add_parser(
        "cache-report",
        help="prompt cache hit ratio, misses and their likely cause: of every session of a run (--run), or of the session transcripts named",
    )
    s.add_argument("files", nargs="*")
    s.add_argument("--run")
    s.add_argument("--misses", type=int, default=8)
    s = sub.add_parser(
        "steps",
        help="the checks of the method's steps, of every path:line and of the evidence, on a finished run; reads the "
        "run's state, stage files and session transcripts, writes nothing (specs/001-chat-depth, part 7)",
    )
    where = s.add_mutually_exclusive_group(required=True)
    where.add_argument("--run", help="a run under this checkout's runs root")
    where.add_argument("--run-dir", help="a run directory anywhere, as a run of another checkout")
    s.add_argument("--repo", help="a checkout that holds the run's commits when this one does not")


def _parsers_control(sub: argparse._SubParsersAction) -> None:
    """The parsers of doctor, runs-root, watch, extensions, inbox, route, abort and pause."""
    sub.add_parser("doctor", help="what this machine needs before a role session can run; changes nothing")
    s = sub.add_parser("runs-root", help="where this checkout's runs live; --init makes ../runs/ that place")
    s.add_argument(
        "--init",
        action="store_true",
        help="create ../runs/ with its marker; moves nothing; refused beside another checkout",
    )
    s.add_argument("--plain", action="store_true", help="print the path only")
    s = sub.add_parser(
        "watch",
        help="wait until a run needs the manager (a gate passed, a question, a stopped unit) and print what happened; start it in the background after a launch",
    )
    s.add_argument("--run", required=True)
    s.add_argument("--every", type=int, default=20, help="seconds between polls")
    s.add_argument("--max-minutes", type=int, default=240)
    s = sub.add_parser(
        "extensions",
        help="plugins and MCP servers against docs/roles/extensions.yaml; --inspect lists what a plugin directory brings",
    )
    s.add_argument("--inspect")
    s = sub.add_parser(
        "inbox", help="copy an untrusted file into <runs root>/_inbox/<slug>/ without showing its content"
    )
    s.add_argument("--slug", required=True)
    s.add_argument("--file", required=True)
    s = sub.add_parser("route", help="map the classifier's label of an intake run to the next pipeline")
    s.add_argument("--run", required=True)
    s = sub.add_parser(
        "abort",
        help="end a run that will not be integrated: stop its sessions, save and remove its checkouts, keep its record",
    )
    s.add_argument("--run", required=True)
    s.add_argument("--reason", required=True, help="the human's words; the state keeps them")
    s = sub.add_parser(
        "pause",
        help="the one pause switch (ADR-0023): while set, launch, resume, loop tick, poll and the night path start "
        "and change nothing; only the human sets and lifts it",
    )
    s.add_argument("op", choices=["set", "lift", "status"])
    s.add_argument("--reason", help="set: the human's words; the switch keeps them")


def _parsers_report(sub: argparse._SubParsersAction) -> None:
    """The parser of pipeline-report: a run folder, not a run of this checkout, so no --run (RUN_COMMANDS)."""
    s = sub.add_parser(
        "pipeline-report",
        help="a pipeline run's findings per task by role and severity, and their rounds, from its record files, "
        "against a baseline; writes evals/results/<stamp>/ (docs/decisions/0028-pipeline-evals.md)",
    )
    s.add_argument("run_dir", metavar="RUN_DIR")
    s.add_argument(
        "--baseline", metavar="FILE", help="a baseline JSON file; default: evals/baseline/pipeline/earlier-run.json"
    )
    s.add_argument("--as-baseline", metavar="FILE", help="write this run's summary as a baseline to FILE instead")
    s.add_argument("--label", metavar="TEXT", help="the baseline's label; --as-baseline needs it")
    s.add_argument(
        "--prefix",
        metavar="NAME",
        help="agent names' prefix for the usage part; runs `claude agents` and reads the transcripts",
    )


def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    a = p.parse_args(argv)
    root = root_dir()
    refused = (None if role_may_run(a) else _refuse_role(a)) or (
        state.refuse_aborted(root, a.run) if RUN_COMMANDS.get(a.cmd) == "changes" and a.run else None
    )
    if refused:
        print(json.dumps(refused, indent=2, ensure_ascii=False))
        return 1
    for do in (_do_run, _do_checks, _do_loops, _do_inspect, _do_control):
        out = do(p, a, root)
        if out is not None:
            break
    else:  # pragma: no cover
        p.error("unknown command")
    if isinstance(out, int):  # loop due --plain, runs-root --plain and mcp-state print their own output
        return out
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if out.get("ok", True) else 1


def _do_run(p: argparse.ArgumentParser, a: argparse.Namespace, root: Path) -> dict | int | None:
    """run to select: create, launch and steer a run. None for a command of another group."""
    if a.cmd == "run":
        effort = dict(item.partition("=")[::2] for item in a.effort)
        out = state.create_run(
            root, a.slug, Path(a.brief), a.context, pipeline=a.pipeline, effort=effort, environ=os.environ
        )
        if out["ok"]:  # the manager asks the human about each before more work piles up (docs/decisions/0010)
            out["open_runs"] = leftovers.open_runs(root, but=out["run_id"])
    elif a.cmd == "status":
        out = launch.status(root, a.run, a.stage, a.shard)
    elif a.cmd == "assign":
        out = launch.assign(root, a.run, a.stage, Path(a.file).expanduser() if a.file else None)
    elif a.cmd == "launch":
        out = launch.launch(root, a.run, a.stage, a.shard)
    elif a.cmd == "poll":
        out = notify.after_poll(root, poll.poll_all(root) if a.all_active else poll.poll(root, a.run))
    elif a.cmd == "resume":
        out = resume.resume(
            root, a.run, a.stage, shard=a.shard, escalation=a.escalation, message=a.message, rework=a.rework
        )
    elif a.cmd == "gate":
        out = (
            gates.preview(root, a.run, a.stage, a.shard) if a.preview else poll.gate_now(root, a.run, a.stage, a.shard)
        )
    elif a.cmd == "approve":
        out = state.approve(root, a.run, a.stage, a.decision)
    elif a.cmd == "refreeze":
        out = state.refreeze(root, a.run)
    elif a.cmd == "integrate":
        out = work.integrate_run(root, a.run, clean=a.clean)
    elif a.cmd == "escalations":
        out = state.list_escalations(root, a.run, a.stage)
    elif a.cmd == "handoff":
        out = state.write_handoff(root, a.run)
    elif a.cmd == "select":
        out = select.select_type(root, a.request)
    else:
        return None
    return out


def _do_checks(p: argparse.ArgumentParser, a: argparse.Namespace, root: Path) -> dict | int | None:
    """catalog to eval, and pipeline-report: the repository's checks and evals. None for a command of another group."""
    if a.cmd == "catalog":
        out = catalog.write_catalog(root)
    elif a.cmd == "validate":
        out = catalog.validate_repository(root)
    elif a.cmd == "docs-check":
        out = catalog.docs_check(root)
    elif a.cmd == "plan-lint":
        out = plans.plan_lint(root)
    elif a.cmd == "map":
        out = stagemap.check_maps(root) if a.check else stagemap.write_maps(root)
    elif a.cmd == "eval":
        from . import evals

        out = evals.run_suite(
            root, a.suite, case=a.case, threshold=a.threshold, baseline=a.baseline, sessions=not a.no_sessions
        )
    elif a.cmd == "pipeline-report":
        from . import pipeline_report

        if a.as_baseline and not a.label:
            p.error("--as-baseline needs --label")
        out = pipeline_report.command(
            root,
            Path(a.run_dir).expanduser(),
            baseline=Path(a.baseline).expanduser() if a.baseline else None,
            as_baseline_file=a.as_baseline,
            label=a.label,
            prefix=a.prefix,
        )
    else:
        return None
    return out


def _do_loops(p: argparse.ArgumentParser, a: argparse.Namespace, root: Path) -> dict | int | None:
    """loop to wiki-lint: the loop layer, the audits and the limits. None for a command of another group."""
    if a.cmd == "loop" and a.op == "due":  # whether a night session has anything to do, without a tick (ADR-0022)
        if not a.name:
            p.error("loop due needs --name")
        out = loops.due(root, a.name)
        if a.plain:  # ops/night-tick.sh: the message alone, or why there is nothing to do as one line of its log
            print(out["message"] if out["ok"] else json.dumps(out, ensure_ascii=False))
            return 0 if out["ok"] else 1
    elif a.cmd == "loop":
        if a.op == "tick" and not a.name:
            p.error("loop tick needs --name")
        out = (
            loops.validate(root)
            if a.op == "validate"
            else (loops.tick(root, a.name) if a.op == "tick" else loops.status(root, a.name))
        )
    elif a.cmd == "audit":
        out = audit.context_audit(root, ci=a.ci)
    elif a.cmd == "skill-usage":
        out = audit.skill_usage(root, runs=a.runs)
    elif a.cmd == "version-check":
        out = audit.version_check(root, a.base)
    elif a.cmd == "limits":
        out = limits.report(root, a.run)
    elif a.cmd == "wiki-lint":
        out = wiki.lint(root)
    else:
        return None
    return out


def _do_inspect(p: argparse.ArgumentParser, a: argparse.Namespace, root: Path) -> dict | int | None:
    """pack to doctor: what a session gets, what a run did, what this machine has. None for another group's command."""
    if a.cmd == "pack":
        policy = access.load_policy(root)
        out = (
            pack.report(root, policy)
            if a.check or not a.type
            else {"ok": True, "role_type": a.type, "pack": pack.build(root, policy, a.type)}
        )
    elif a.cmd == "material":
        out = launch.preview_material(root, a.run, a.stage)
    elif a.cmd == "extensions":
        out = extensions.inspect(Path(a.inspect)) if a.inspect else extensions.check(root)
    elif a.cmd == "cache-report":
        if not a.run and not a.files:
            p.error("cache-report needs --run or transcript files")
        out = (
            cache_report.of_run(root, a.run, a.misses)
            if a.run
            else {"ok": True, "sessions": [cache_report.analyse(Path(f), a.misses) for f in a.files]}
        )
    elif a.cmd == "steps":
        run_dir = Path(a.run_dir).expanduser() if a.run_dir else state.runs_root(root) / a.run
        out = gates.review(root, run_dir, Path(a.repo).expanduser() if a.repo else None)
    elif a.cmd == "runs-root":
        out = state.init_runs_root(root) if a.init else {"ok": True}
        if out["ok"]:
            if a.plain:
                print(state.runs_root(root))
                return 0
            out = {"ok": True, "runs_root": str(state.runs_root(root))}
    elif a.cmd == "doctor":
        out = doctor.check(root)
    else:
        return None
    return out


def _do_control(p: argparse.ArgumentParser, a: argparse.Namespace, root: Path) -> dict | int | None:
    """watch to mcp-state: wait on a run, take in, route, abort, pause, serve. None for a command of another group."""
    if a.cmd == "watch":
        out = poll.watch(root, a.run, every=a.every, max_minutes=a.max_minutes)
    elif a.cmd == "inbox":
        out = intake.add(root, a.slug, Path(a.file))
    elif a.cmd == "route":
        out = intake.route(root, a.run)
    elif a.cmd == "abort":
        out = work.abort_run(root, a.run, a.reason)
    elif a.cmd == "pause":
        if a.op == "set" and not a.reason:
            p.error("pause set needs --reason")
        out = (
            pause.set_flag(root, a.reason)
            if a.op == "set"
            else (pause.lift(root) if a.op == "lift" else {"ok": True, "paused": pause.current(root)})
        )
    elif a.cmd == "mcp-state":
        from . import mcp_state

        return mcp_state.serve(root)
    else:
        return None
    return out


if __name__ == "__main__":
    sys.exit(main())
