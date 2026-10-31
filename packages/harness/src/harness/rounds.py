"""harness/rounds.py — the loops inside a run (docs/decisions/0024-a-run-loops-until-its-reviewers-pass.md).

A stage whose row has `returns_to` reviews the work of an earlier stage. When its gate passed and its verdict is
`revise`, its proven findings go back to that stage in `stages/<stage>/rework.md`, and every launched stage after
that stage checks again once the rework passed its gate. The table's `loop` block bounds the rounds per counter and
the starts of a stage. The loop stops for the human when a bound is reached, when a round brings back the findings of
the round before, and when the last stage says `replan` or `reject`; the human answers with `harness approve`.

`process` runs under the lock of state.json (poll._commit). It records a round in the state and moves no file; the
files move once that state is saved (move_round), and a round a crash left half moved is finished by the next poll.
So one verdict is taken once, and no round is lost. Poll runs outside the sandbox: nothing here follows a link a
session put into its stage directory."""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

from . import state
from .gates._common import critique_rows, report_entries, result, text

DEFAULT_CAP = 3
REWORK = "rework.md"
LOOPING = ("rework", "recheck")
STOP_ACTIONS = ("loop_cap", "no_progress", "rejected", "replan")  # the loop waits for the human
BLOCKING_ROWS = {"blocks", "must fix"}
STOPS = {"reject": "rejected", "replan": "replan"}  # a verdict of the last stage that ends the loop
ANSWERED = ("approved", "rejected")  # a human's answer: no verdict of that stage is taken again
CITE = re.compile(r"\b([a-z][a-z0-9_-]*)#(\d+)\b")
LEAD = re.compile(r"^(?:#{1,6}\s*)?\d+[.)]\s*|^\|[^|]*\|")  # an entry's number, or a row's first cell


def downstream(stages: list[dict], target: str) -> list[str]:
    """The stages that depend on `target`, directly or through others, in table order."""
    after, grew = {target}, True
    while grew:
        grew = False
        for s in stages:
            if s["id"] not in after and after & set(s.get("depends_on") or []):
                after.add(s["id"])
                grew = True
    return [s["id"] for s in stages if s["id"] in after and s["id"] != target]


def loop_problems(table: dict) -> list[str]:
    """What is wrong with the loops of a stage table: `returns_to` names no stage this one depends on, a counter the
    `loop` block does not bound, or a stage of the loop (the one that reworks, or any after it, the reviewer too)
    that runs per task: a loop sends work back to one session, and a sharded stage cannot hold a round."""
    stages = table["stages"]
    by_id = {s["id"]: s for s in stages}
    counters = (table.get("loop") or {}).get("counters") or {}
    out = []
    for s in [s for s in stages if s.get("returns_to")]:
        target, counter = s["returns_to"]["stage"], s["returns_to"]["counter"]
        if target not in by_id or s["id"] not in downstream(stages, target):
            out.append(f"stage {s['id']} returns to {target!r}, which is not a stage it depends on")
        else:
            for sid in [target, *downstream(stages, target)]:
                if by_id[sid].get("parallel") == "per_task":
                    out.append(
                        f"stage {s['id']} returns to {target}, and {sid} runs per task: a loop needs one session"
                    )
        if counter not in counters:
            out.append(f"stage {s['id']} counts its rounds on {counter!r}, which the loop block does not bound")
    return out


def entries(report: str) -> list[tuple[int, str, str]]:
    """(number, result, text) of every numbered entry of a verifier's report.md that states a result, read as its gate
    and the judge's read it (_common.report_entries)."""
    return [(n, found, body) for n, found, body in report_entries(report) if found]


def blocking_items(run_dir: Path, stage: dict) -> list[str]:
    """The proven findings a reviewer sends back, whole: a verifier's refuted entries, a critic's blocks and must fix
    rows, a judge's reasons. The stage that reworks cannot open the reviewer's directory. A file that is a link is
    not read (_common.stage_file)."""
    stage_dir = run_dir / "stages" / stage["id"]
    if stage["role_type"] == "verifier":
        return [body for _, res, body in entries(text(stage_dir, "output/report.md")) if res == "refuted"]
    if stage["role_type"] == "critic":
        rows = critique_rows(text(stage_dir, "output/critique.md")) or []
        return [line for finding, line in rows if finding["severity"] in BLOCKING_ROWS]
    return [str(r) for r in (result(stage_dir).get("verdict") or {}).get("reasons", [])]


def cited(run_dir: Path, stage: dict, items: list[str]) -> list[str]:
    """The entries of the reports a judge's reasons cite as `<stage>#<n>`, whole, for the stage that reworks."""
    if stage["role_type"] != "judge":
        return []
    named = {(s, int(n)) for item in items for s, n in CITE.findall(item)}
    out: list[str] = []
    for dep in stage.get("depends_on") or []:
        report = text(run_dir / "stages" / dep, "output/report.md")
        out += [body for n, _, body in entries(report) if (dep, n) in named]
    return out


def signature(items: list[str]) -> str:
    """The same findings in another round give the same signature: numbers, case and spacing do not count."""
    norm = sorted({" ".join(LEAD.sub("", i.strip().splitlines()[0]).lower().split()) for i in items if i.strip()})
    return hashlib.sha256("\n".join(norm).encode("utf-8")).hexdigest()


def _clear(path: Path) -> None:
    """Remove what stands at a name the harness writes: a link (never followed), a file or a folder."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _own_dir(path: Path) -> Path:
    """`path` as a folder of the harness: a link or a file a session put there goes first."""
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        path.unlink()
    path.mkdir(exist_ok=True)
    return path


def archive(run_dir: Path, stage_id: str, n: int, reviewer: bool) -> Path:
    """Keep what a unit made in round n under `rounds/<n>/` and clear the place for the next round. result.json and
    gate.json move; a reviewer's output/ moves too and starts empty; the stage that reworks keeps report.md,
    tasks.json and checks.json in place, with a copy in the round. Running it again moves nothing twice (move_round
    finishes a round a crash left half moved). A rename moves a link itself; a link is never copied or entered."""
    stage_dir = run_dir / "stages" / stage_id
    dest = _own_dir(_own_dir(stage_dir / "rounds") / str(n))
    for name in ("result.json", "gate.json"):
        src = stage_dir / name
        if src.is_symlink() or src.exists():
            _clear(dest / name)
            src.rename(dest / name)
    out, kept = stage_dir / "output", dest / "output"
    if reviewer:
        if kept.is_symlink() or (kept.exists() and not kept.is_dir()):
            kept.unlink()
        if not kept.exists() and out.is_dir() and not out.is_symlink():
            out.rename(kept)
        _own_dir(out)
    for name in () if reviewer else ("report.md", "tasks.json", "checks.json"):
        src = stage_dir / name
        if src.is_file() and not src.is_symlink():
            _clear(dest / name)
            shutil.copy2(src, dest / name)
    return dest


def last_round(stage_dir: Path) -> int:
    """The newest round kept under `rounds/` of a stage directory, 0 when none is."""
    kept = stage_dir / "rounds"
    if not kept.is_dir() or kept.is_symlink():
        return 0
    return max((int(p.name) for p in kept.iterdir() if p.name.isdigit()), default=0)


def runs_left(manifest: dict, stage_id: str, u: dict) -> bool:
    """Whether a unit may start once more: the table's `loop.max_runs` bounds every start and resume of a stage in
    one run, retries and rounds together (its attempts count them)."""
    runs = ((manifest.get("loop") or {}).get("max_runs") or {}).get(stage_id)
    return not runs or u["attempts"] < runs


def rework_message(stage: dict, n: int, items: list[str], context: list[str]) -> str:
    """The message the reworking stage is resumed with: what came back, from which stage, and how the round ends."""
    found = "\n\n".join(f"### Finding {i}\n\n{body}" for i, body in enumerate(items, 1))
    cites = ("\n\n## What the findings cite\n\n" + "\n\n".join(context)) if context else ""
    return (
        f"Round {n + 1}. Stage {stage['id']} ({stage['role_type']}) sent the work back with {len(items)} finding(s), "
        "each shown by a command it ran. Answer every one of them and change nothing that no finding names.\n\n"
        f"## Findings\n\n{found}{cites}\n\n"
        f"Your result of round {n} is under rounds/{n}/ in your stage directory. Write a section `Round {n + 1}` "
        "in your report with one entry per finding (what you changed, the command that shows it, its exit code), "
        "run your checks again, and rewrite result.json.\n"
    )


def send_back(run_dir: Path, manifest: dict, st: dict, stage: dict, items: list[str], n: int) -> None:
    """Round n ends: the reworking stage and every launched stage after it keep their round and wait, each with the
    approval its row asks for; the message goes to `rework.md` of the reworking stage. The state records the round and
    the units whose files move_round keeps under rounds/<n>/ once the state is saved: nothing is moved here."""
    target, counter = stage["returns_to"]["stage"], stage["returns_to"]["counter"]
    by_id = {s["id"]: s for s in manifest["stages"]}
    units = [sid for sid in [target, *downstream(manifest["stages"], target)] if st["stages"][sid]["attempts"]]
    for sid in units:  # a stage never launched starts in its turn
        unit = st["stages"][sid]
        unit.update(status="rework" if sid == target else "recheck", gate="pending")
        unit["approval"] = "pending" if by_id[sid]["approval"] == "human" else "not_required"
        unit.pop("finished_at", None)
        (run_dir / "locks" / f"{sid}.lock").unlink(missing_ok=True)
    rework = run_dir / "stages" / target / REWORK
    _clear(rework)
    state.write_atomic(rework, rework_message(stage, n, items, cited(run_dir, stage, items)))
    st["loop"]["rounds"][counter] = n
    st["loop"]["history"].append({"round": n, "counter": counter, "from": stage["id"], "to": target,
                                  "items": len(items), "signature": signature(items), "at": state.now()})  # fmt: skip
    st["loop"]["moving"] = {"round": n, "target": target, "units": units}
    st["loop"].pop("stop", None)


def move_round(run_dir: Path, st: dict) -> bool:
    """Keep the files of the round the state recorded (`loop.moving`) under rounds/<n>/ of each unit, then drop the
    record. Called once the state that holds the round is saved; True when it changed `st`, which is saved again."""
    moving = st.get("loop", {}).get("moving")
    if not moving:
        return False
    for sid in moving["units"]:
        archive(run_dir, sid, moving["round"], reviewer=sid != moving["target"])
    del st["loop"]["moving"]
    return True


def take_round(run_dir: Path, manifest: dict, st: dict, stage: dict) -> dict | None:
    """Send the findings of `stage` back to its `returns_to`, or say why the loop stops (an action for the human).
    Nothing while a unit the round would send back is still running: a later poll takes the round."""
    from .poll import ACTIVE  # poll imports this module

    target, counter = stage["returns_to"]["stage"], stage["returns_to"]["counter"]
    if any(st["stages"][sid]["status"] in ACTIVE for sid in [target, *downstream(manifest["stages"], target)]):
        return None
    cap = ((manifest.get("loop") or {}).get("counters") or {}).get(counter, DEFAULT_CAP)
    done = st["loop"]["rounds"].get(counter, 0)
    items = blocking_items(run_dir, stage)
    where = {"stage": stage["id"], "returns_to": target, "counter": counter, "rounds": done, "items": len(items)}
    last = next((h for h in reversed(st["loop"]["history"]) if h["from"] == stage["id"]), None)
    if done >= cap:
        return {"action": "loop_cap", **where, "cap": cap}
    if not runs_left(manifest, target, st["stages"][target]):
        runs = manifest["loop"]["max_runs"][target]
        return {"action": "loop_cap", **where, "max_runs": runs}
    if not items or (last and last["signature"] == signature(items)):
        return {"action": "no_progress", **where}
    send_back(run_dir, manifest, st, stage, items, done + 1)
    return None


def _hold(st: dict, ss: dict, stop: dict) -> None:
    """A stop waits for the human's answer on the reviewer: its approval is asked (`harness approve`), and the state
    names the stop until then. The first time it was seen is kept."""
    ss["approval"] = "pending"
    seen = st["loop"].get("stop") or {}
    if (seen.get("action"), seen.get("stage")) != (stop["action"], stop["stage"]):
        detail = ", ".join(f"{k} {v}" for k, v in stop.items() if k not in ("action", "stage"))
        st["loop"]["stop"] = {"action": stop["action"], "stage": stop["stage"], "at": state.now(), "detail": detail}


def _passed(ss: dict) -> bool:
    return ss["status"] == "done" and ss.get("gate") == "pass" and ss.get("approval") not in ("pending", "rejected")


def pending(run_dir: Path, manifest: dict, st: dict) -> list[dict]:
    """`rework` for every unit with findings to answer; `recheck` for every unit to check again whose stages before it
    passed again. Derived from the state on every poll, like an approval."""
    out = []
    for stage in manifest["stages"]:
        ss = st["stages"][stage["id"]]
        if ss["status"] == "rework":
            out.append(
                {"action": "rework", "stage": stage["id"], "file": str(run_dir / "stages" / stage["id"] / REWORK)}
            )
        elif ss["status"] == "recheck" and all(_passed(st["stages"][d]) for d in stage.get("depends_on") or []):
            out.append({"action": "recheck", "stage": stage["id"]})
    return out


def process(run_dir: Path, manifest: dict, st: dict) -> list[dict]:
    """Take every verdict that sends work back, once, and return the loop's actions now: `rework` and `recheck` for
    the manager; `loop_cap`, `no_progress`, `rejected` and `replan` for the human. Only the last stage (no stage
    depends on it) stops the run with `replan` or `reject`; an earlier reviewer's `reject` is a proposal for it. A
    reviewer whose approval the human answered gives no round. Changes `st`; a round a crash left half moved is
    finished first."""
    st.setdefault("loop", {"rounds": {}, "history": []})
    move_round(run_dir, st)
    actions = []
    for stage in [s for s in manifest["stages"] if s.get("returns_to")]:
        ss = st["stages"][stage["id"]]
        if ss["status"] != "done" or ss.get("gate") != "pass" or ss.get("approval") in ANSWERED:
            continue
        decision = (result(run_dir / "stages" / stage["id"]).get("verdict") or {}).get("decision")
        stop = None
        if decision in STOPS and not downstream(manifest["stages"], stage["id"]):
            stop = {"action": STOPS[decision], "stage": stage["id"]}
        elif decision == "revise":
            stop = take_round(run_dir, manifest, st, stage)
        if stop:
            _hold(st, ss, stop)
            actions.append(stop)
    return actions + pending(run_dir, manifest, st)
