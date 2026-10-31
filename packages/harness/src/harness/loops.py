"""Loop layer: one declared loop is docs/loops/<name>.yaml; its state is <runs root>/_loops/<name>/state.json.
`harness loop tick` decides without a model whether one more iteration may start: readiness, the exit rule,
progress and the hard stops are checked here; only then a run is created (pipeline) or a command is executed.
One tick of a loop runs at a time: it holds the loop state's one lock from its read to its write (ADR-0021)."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shlex
import subprocess
from pathlib import Path

import jsonschema
import yaml

from . import notify, pause, poll, state

RUN_ACTIVE = {"created", "running", "waiting_human", "paused"}
RUNS_ENTRY = re.compile(r"^runs:(\d+)$")  # a context entry that stands for the finished runs of the last <days>
# The conditions a loop file may name as `exit.check`, the success code checks at every tick of a prompt loop
# (docs/decisions/0022-a-prompt-loop-is-judged-by-code.md); schemas/loop.schema.json lists the same names.
CHECKS = {"no_active_runs": "no run has the status created, running, waiting_human or paused"}
# The actions of `harness poll` the manager carries out; the others wait or need the human.
MANAGER_ACTIONS = {"resume", "gate", "rework", "recheck"}


def load_loop(root: Path, name: str) -> dict:
    spec = yaml.safe_load((root / "docs" / "loops" / f"{name}.yaml").read_text(encoding="utf-8"))
    jsonschema.validate(spec, state.schema(root, "loop"))
    return spec


def _state_path(root: Path, name: str) -> Path:
    return state.runs_root(root) / "_loops" / name / "state.json"


def load_state(root: Path, name: str) -> dict:
    path = _state_path(root, name)
    if path.exists():
        return state.load(root, path, "loop-state")
    return {
        "schema_version": 1,
        "name": name,
        "status": "idle",
        "episode": 0,
        "iterations": 0,
        "episode_started_at": None,
        "last_tick_at": None,
        "last_run_id": None,
        "last_exit": None,
        "progress_keys": [],
        "spent_usd": 0.0,
        "escalated": [],
    }


def _save_state(root: Path, name: str, st: dict) -> None:
    path = _state_path(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    st["last_tick_at"] = state.now()
    state.save(root, path, st, "loop-state")


def context_problems(root: Path, spec: dict) -> list[str]:
    """The context entries of a loop's action that a tick cannot read: a `runs:` entry that is not `runs:<days>`,
    and a path that names nothing in the repository. `harness loop validate` names them, and a tick prints `exit`
    with the rule `invalid` before anything starts (05/F29)."""
    problems = []
    for item in spec["action"].get("context", []):
        if item.startswith("runs:"):
            if not RUNS_ENTRY.match(item):
                problems.append(f"context entry {item!r} is not runs:<days>")
        elif not _names_something(root / item):
            problems.append(f"context entry {item!r} names nothing in the repository")
    return problems


def _names_something(path: Path) -> bool:
    """Whether a path exists; one the file system cannot even look up (a name longer than a name may be) does not."""
    try:
        return path.exists()
    except OSError:
        return False


def validate(root: Path) -> dict:
    """`harness loop validate`: every loop file matches the schema, is ready (four conditions met, with evidence),
    names an existing pipeline, prompt or workflow file and context a tick can read, and a pipeline action has a
    checker that is not the maker."""
    problems = []
    for path in sorted((root / "docs" / "loops").glob("*.yaml")):
        try:
            spec = load_loop(root, path.stem)
        except (jsonschema.ValidationError, yaml.YAMLError) as exc:
            problems.append(f"{path.name}: {str(exc)[:200]}")
            continue
        if spec["name"] != path.stem:
            problems.append(f"{path.name}: name {spec['name']!r} must equal the file name")
        problems += [f"{path.name}: readiness.{k} is not met" for k, v in spec["readiness"].items() if not v["met"]]
        problems += [f"{path.name}: {p}" for p in context_problems(root, spec)]
        action = spec["action"]
        if action["kind"] == "pipeline":
            table_path = state.table_path(root, action.get("pipeline", ""))
            if not table_path.exists():
                problems.append(f"{path.name}: pipeline {action.get('pipeline')!r} does not exist")
            elif len({row["role_type"] for row in state.load_table(root, action["pipeline"])["stages"]}) < 2:
                problems.append(f"{path.name}: the pipeline has one role type, so nothing checks the maker")
        elif action["kind"] == "command" and not action.get("command"):
            problems.append(f"{path.name}: a command action needs `command`")
        elif action["kind"] in ("prompt", "ci") and not (root / action.get("file", "")).is_file():
            problems.append(f"{path.name}: file {action.get('file')!r} does not exist")
        if "rubric" in spec and not (root / spec["rubric"]).is_file():
            problems.append(f"{path.name}: rubric {spec['rubric']} does not exist")
    return {"ok": not problems, "problems": problems}


def _run_states(root: Path) -> list[tuple[str, dict]]:
    """(run id, state) of every run under the runs root whose state.json reads as a JSON object with a status in text.
    A run whose state cannot be read is left out, as leftovers does (refute#148): one cut file never stops a tick."""
    found = []
    for path in sorted(state.runs_root(root).glob("*-*/state.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(doc, dict) and isinstance(doc.get("status"), str):
            found.append((path.parent.name, doc))
    return found


def _outcome(root: Path, run_id: str) -> tuple[str, str, float, list[str]]:
    """The last run as the loop sees it: active, success or failure; a progress key; print cost; open escalations.
    A run whose folder is gone or whose state cannot be read is a failure (05/F28), as an aborted run is."""
    run_dir = state.runs_root(root) / run_id
    try:
        st = state.load(root, run_dir / "state.json", "run-state")
    except (OSError, ValueError, jsonschema.ValidationError):
        return "failure", hashlib.sha256(f"unreadable:{run_id}".encode()).hexdigest(), 0.0, []
    if st["status"] in RUN_ACTIVE:
        return "active", "", 0.0, []
    facts = sorted(f"{sid}:{ss['status']}:{ss['gate']}" for sid, ss in st["stages"].items())
    for gate in sorted(run_dir.glob("stages/**/gate.json")):
        doc = json.loads(gate.read_text(encoding="utf-8"))
        facts += [f"{doc['stage']}:{c['name']}" for c in doc["checks"] if not c["passed"]]
    key = hashlib.sha256("\n".join(facts).encode("utf-8")).hexdigest()
    done = st["status"] == "done" and all(ss["gate"] == "pass" for ss in st["stages"].values())
    open_escalations = [f"{run_id}/{e['id']}" for e in st["escalations"] if e["status"] == "open"]
    return (
        ("success" if done else "failure"),
        key,
        float(st.get("cost", {}).get("print_total_usd", 0.0)),
        open_escalations,
    )


def _expand(root: Path, items: list[str]) -> list[str]:
    """Context entries as paths. `runs:<days>` stands for the finished runs updated within that many days, so a loop
    over past runs (learning-review) names its material in code and no model chooses which runs to read."""
    out: list[str] = []
    for item in items:
        m = RUNS_ENTRY.match(item)
        if not m:
            out.append(item)
            continue
        try:
            since = dt.datetime.now(dt.UTC) - dt.timedelta(days=int(m.group(1)))
        except (OverflowError, ValueError):  # more days than a date can go back: every finished run
            since = dt.datetime.min.replace(tzinfo=dt.UTC)
        for run_id, run_state in _run_states(root):
            try:
                recent = dt.datetime.fromisoformat(run_state["updated_at"]) >= since
            except (KeyError, TypeError, ValueError):
                continue
            if run_state.get("status") not in RUN_ACTIVE and recent:
                out.append(str(state.runs_root(root) / run_id))
    return out


def _holds(root: Path, check: str) -> bool:
    """Whether the condition a loop file names as its `exit.check` holds now (CHECKS)."""
    if check == "no_active_runs":
        return not any(doc.get("status") in RUN_ACTIVE for _, doc in _run_states(root))
    raise ValueError(f"unknown exit check {check!r}; schemas/loop.schema.json allows {sorted(CHECKS)}")


def _runs_key(root: Path) -> str:
    """The progress key of a prompt iteration. What it leaves on disk is the state of the runs it acted on, and a run's
    `changed_at` moves only when one of its statuses, gates, approvals, attempts or escalations changed (ADR-0010)."""
    facts = sorted(
        f"{rid}:{doc.get('status')}:{doc.get('changed_at') or doc.get('updated_at')}" for rid, doc in _run_states(root)
    )
    return hashlib.sha256("\n".join(facts).encode("utf-8")).hexdigest()


NIGHT = "night-tick"  # <runs root>/_audit/night-tick/<loop>-<UTC time>.json: one per fire, written by ops/night-tick.sh


def night_spend(root: Path, name: str, since: str | None) -> float:
    """What the night path's sessions of a loop cost since `since`: the `total_cost_usd` of every file
    `<runs root>/_audit/night-tick/<name>-<YYYYmmddTHHMMSSZ>.json` that ops/night-tick.sh wrote when its session ended.
    A file whose time or cost cannot be read, or whose cost is below zero or no finite number, counts nothing. The
    spend of an iteration run in the open manager session is written nowhere the harness reads (ADR-0022)."""
    start = dt.datetime.fromisoformat(since) if since else None
    total = 0.0
    for path in sorted((state.runs_root(root) / "_audit" / NIGHT).glob(f"{name}-*.json")):
        try:
            at = dt.datetime.strptime(path.stem[len(name) + 1 :], "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.UTC)
            usd = float(json.loads(path.read_text(encoding="utf-8")).get("total_cost_usd") or 0.0)
        except (OSError, ValueError, AttributeError, TypeError):
            continue
        if (start is None or at >= start) and 0.0 <= usd < float("inf"):  # NaN fails both comparisons
            total += usd
    return total


def render_brief(spec: dict, st: dict, context: list[str]) -> str:
    """The brief of one iteration, in the sections of templates/project-brief.md. The goal comes from the loop file."""
    done = "\n".join(f"- {item}" for item in spec["goal"]["done_when"])
    material = "\n".join(f"- `{p}`" for p in context) or "- none"
    return (
        f"# Project brief — loop {spec['name']}, episode {st['episode']}, iteration {st['iterations']}\n\n"
        f"## Project\n{spec['purpose']}\n\n## Goal of this run\n{spec['goal']['statement']}\nDone when:\n{done}\n\n"
        f"## Material\n{material}\n\n## Constraints\n- Limits of this loop: {json.dumps(spec['stops'])}\n"
        f"- Rubric: {spec.get('rubric', 'none')}\n\n## Known decisions\n- none\n\n## Out of scope\n- anything the goal does not name\n\n"
        "## Escalation policy\n- Blocking questions: write an escalation and stop. Non-blocking: list them in result.json open_questions.\n"
    )


def _exit(st: dict, rule: str, detail: str = "") -> dict:
    st["status"], st["last_exit"] = "idle", {"rule": rule, "at": state.now(), "detail": detail[:500]}
    return {"ok": rule == "success", "action": "exit", "rule": rule, "detail": detail[:500]}


def _progress(st: dict, key: str, stops: dict, detail: str) -> dict | None:
    """Keep the progress key of a judged iteration (the last `no_progress_after` of them); the same key that many times
    in a row ends the episode with `no_progress`."""
    st["progress_keys"] = [*st["progress_keys"], key][-stops["no_progress_after"] :]
    if len(st["progress_keys"]) == stops["no_progress_after"] and len(set(st["progress_keys"])) == 1:
        return _exit(st, "no_progress", detail)
    return None


def tick(root: Path, name: str) -> dict:
    """`harness loop tick`: one action (`wait`, `launch`, `prompt`, `external`, `exit`). While the pause switch is set
    it answers `wait` with `paused` and the loop state stays as it is (ADR-0023)."""
    spec = load_loop(root, name)
    held = pause.current(root)
    if held:
        return {"ok": True, "action": "wait", "paused": held}
    if not spec["enabled"]:
        return {"ok": True, "action": "exit", "rule": "disabled"}
    unmet = [k for k, v in spec["readiness"].items() if not v["met"]]
    if unmet:
        return {"ok": False, "action": "exit", "rule": "not_ready", "detail": ", ".join(unmet)}
    bad = context_problems(root, spec)
    if bad:
        return {"ok": False, "action": "exit", "rule": "invalid", "detail": "; ".join(bad)[:500]}
    if spec["action"]["kind"] == "ci":
        return {"ok": True, "action": "external", "file": spec["action"]["file"]}
    with state.locked(_state_path(root, name)):  # one tick of a loop at a time, from its read to its write (05/F30)
        st = load_state(root, name)
        out = _step(root, name, spec, st)
        _save_state(root, name, st)
    return out


def _judge(root: Path, name: str, spec: dict, st: dict) -> dict | None:
    """Judge what the previous iteration left: the run of a pipeline iteration; for a prompt iteration, the exit check
    of the loop file, the runs it acted on and what the night path's sessions cost (ADR-0022). Returns the action
    that ends here (`wait`, or `exit`), or None when the tick goes on."""
    stops = spec["stops"]
    if st["status"] == "running" and st["last_run_id"]:
        result, key, usd, escalations = _outcome(root, st["last_run_id"])
        if result == "active":
            st["escalated"] = escalations
            return {"ok": True, "action": "wait", "run_id": st["last_run_id"], "escalated": escalations}
        st["spent_usd"] += usd
        if result == "success":
            return _exit(st, "success", st["last_run_id"])
        return _progress(st, key, stops, st["last_run_id"])
    if spec["action"]["kind"] != "prompt":
        return None
    if st["status"] == "running":
        st["spent_usd"] = night_spend(root, name, st["episode_started_at"])
    check = spec["exit"].get("check")
    if check and _holds(root, check):
        return _exit(st, "success", CHECKS[check])
    if st["status"] == "running" and st["iterations"]:
        return _progress(
            st, _runs_key(root), stops, f"the runs did not change in {stops['no_progress_after']} iterations"
        )
    return None


def _step(root: Path, name: str, spec: dict, st: dict) -> dict:
    """The body of one tick, under the loop state's lock: judge, open an episode, check the hard stops, start."""
    action, stops = spec["action"], spec["stops"]
    out = _judge(root, name, spec, st)
    if out is None and st["status"] == "idle":  # a trigger opens a new episode
        st.update(
            {
                "status": "running",
                "episode": st["episode"] + 1,
                "iterations": 0,
                "episode_started_at": state.now(),
                "progress_keys": [],
                "spent_usd": 0.0,
                "last_run_id": None,
                "escalated": [],
            }
        )
    if out is None:
        minutes = (dt.datetime.now(dt.UTC) - dt.datetime.fromisoformat(st["episode_started_at"])).total_seconds() / 60
        if st["iterations"] >= stops["max_iterations"]:
            out = _exit(st, "max_iterations", str(st["iterations"]))
        elif minutes > stops["max_minutes"]:
            out = _exit(st, "max_minutes", f"{minutes:.0f}")
        elif "max_usd" in stops and st["spent_usd"] >= stops["max_usd"]:
            out = _exit(st, "max_usd", f"{st['spent_usd']:.2f}")
    if out is None:
        st["iterations"] += 1
        if action["kind"] == "prompt":
            out = {"ok": True, "action": "prompt", "file": action["file"], "iteration": st["iterations"]}
        elif action["kind"] == "command":
            try:
                res = subprocess.run(
                    shlex.split(action["command"]), cwd=root, capture_output=True, text=True, check=False
                )
                out = _exit(st, "success" if res.returncode == 0 else "failure", (res.stdout + res.stderr)[-500:])
            except OSError as exc:  # the command itself could not start
                out = _exit(st, "failure", str(exc))
        else:
            brief = state.runs_root(root) / "_briefs" / f"loop-{name}-{st['episode']:04d}-{st['iterations']:02d}.md"
            brief.parent.mkdir(parents=True, exist_ok=True)
            context = _expand(root, action.get("context", []))
            brief.write_text(render_brief(spec, st, context), encoding="utf-8")
            run = state.create_run(root, f"loop-{name}", brief, context, pipeline=action["pipeline"])
            st["last_run_id"] = run["run_id"]
            out = {
                "ok": True,
                "action": "launch",
                "run_id": run["run_id"],
                "pipeline": action["pipeline"],
                "iteration": st["iterations"],
            }
    return out


def due(root: Path, name: str) -> dict:
    """`harness loop due`: whether a night session of the loop has anything to do now, decided without a model and
    without a tick: the loop state is neither written nor counted (ADR-0022). Not due while the pause switch is set;
    for a loop that is disabled, not ready, invalid or run by CI; for a prompt loop whose exit check holds; and for a
    loop that acts on runs (exit check `no_active_runs`) when `harness poll --all-active`, run here without a model,
    printed no action the manager carries out (MANAGER_ACTIONS). When due, `message` is what ops/night-tick.sh tells
    the session: a prompt loop's file, which ticks by itself, and the loop-tick skill for any other loop, so that one
    fire ticks once."""
    spec = load_loop(root, name)
    held = pause.current(root)
    if held:
        return {"ok": False, "due": False, "why": "paused", "paused": held}
    if not spec["enabled"]:
        return {"ok": False, "due": False, "why": "disabled"}
    unmet = [k for k, v in spec["readiness"].items() if not v["met"]]
    bad = context_problems(root, spec)
    if unmet or bad:
        return {"ok": False, "due": False, "why": "not_ready" if unmet else "invalid", "detail": "; ".join(unmet + bad)}
    action = spec["action"]
    if action["kind"] == "ci":
        return {"ok": False, "due": False, "why": "external"}
    if action["kind"] != "prompt":
        return {"ok": True, "due": True, "message": f"/loop-tick {name}"}
    check = spec["exit"].get("check")
    if check and _holds(root, check):
        return {"ok": False, "due": False, "why": "success", "detail": CHECKS[check]}
    message = f"Read `{action['file']}` and do exactly what it says in this turn."
    if check != "no_active_runs":
        return {"ok": True, "due": True, "message": message}
    polled = notify.after_poll(root, poll.poll_all(root))
    actions = [{"run_id": r["run_id"], **a} for r in polled["runs"] for a in r["actions"]]
    names = [a["action"] for a in actions]
    if not any(a["action"] in MANAGER_ACTIONS for a in actions):
        return {"ok": False, "due": False, "why": "nothing for the manager", "actions": names}
    once = [a for a in actions if a["action"] == "gate"]  # a later poll does not print a passed gate again
    if once:
        message += (
            " Before this session `harness poll --all-active` ran without a model and printed these actions, which"
            f" your own poll will not print again; act on them as on the ones it prints: {json.dumps(once)}"
        )
    return {"ok": True, "due": True, "message": message, "actions": names}


def status(root: Path, name: str | None = None) -> dict:
    names = [name] if name else sorted(p.stem for p in (root / "docs" / "loops").glob("*.yaml"))
    return {
        "ok": True,
        "loops": [{"name": n, "enabled": load_loop(root, n)["enabled"], **load_state(root, n)} for n in names],
    }
