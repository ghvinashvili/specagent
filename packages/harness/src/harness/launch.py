"""Launch one stage as Claude Code sessions: one session, or one per shard for a `parallel: per_task` stage.
A unit (stage or shard) is launched once; every later attempt goes through `resume`. A print session runs under the
session id the manifest fixed for it. A background session does not: `claude --bg` ignores `--session-id` and
assigns its own, so the launcher reads the real id from `claude agents --json` by the job id the command printed."""

from __future__ import annotations

import copy
import fnmatch
import json
import os
import re
import subprocess
import time
from pathlib import Path

import jsonschema

from . import access, doctor, otel, pack, pause, pieces, rounds, state, trust, work
from .gates import _common

BG_ID = re.compile(r"backgrounded\s+·\s+([0-9a-f]+)")
WARM_SECONDS = 90  # how long a wave waits for its first session's first response before it starts the others


def listing(root: Path) -> list[dict]:
    """Every background session started under the repository, finished ones included."""
    res = subprocess.run(
        ["claude", "agents", "--json", "--all", "--cwd", str(root)], capture_output=True, text=True, check=True
    )
    return json.loads(res.stdout)


def session_of(root: Path, job_id: str | None, tries: int = 10) -> str | None:
    """The session id of a background job. The row appears a moment after `claude --bg` returns."""
    for _ in range(tries if job_id else 0):
        row = next((r for r in listing(root) if r.get("id") == job_id), None)
        if row and row.get("sessionId"):
            return row["sessionId"]
        time.sleep(1)
    return None


def transcript_of(session_id: str) -> Path | None:
    """The session's own log under the Claude configuration directory, whatever directory the session runs in."""
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "projects"
    return next(iter(base.glob(f"*/{session_id}.jsonl")), None)


def wait_first_response(session_id: str | None, seconds: int = WARM_SECONDS) -> bool:
    """True once the session's log holds a model response. The prompt cache serves a prefix only after the request
    that wrote it has begun to answer, so sessions of one type started at the same instant each pay for the write."""
    deadline = time.monotonic() + seconds
    while session_id and time.monotonic() < deadline:
        log = transcript_of(session_id)
        if log and '"type":"assistant"' in log.read_text(encoding="utf-8", errors="replace").replace('": "', '":"'):
            return True
        time.sleep(2)
    return False


def _row(root: Path, stage_id: str, pipeline: str = "default") -> dict:
    table = state.load_table(root, pipeline)  # the table the manifest names: stages.yaml or pipelines/<name>.yaml
    return next(r for r in table["stages"] if r["id"] == stage_id)


def _stage_dir(run_dir: Path, stage_id: str, shard: int | None) -> Path:
    d = run_dir / "stages" / stage_id
    return d / f"{shard:02d}" if shard else d


# The headings every assignment has. The pieces of the repository a stage needs are cut and chosen by script
# (harness/pieces.py) and given in its cached system prompt; an optional section `Material` adds a piece by hand.
ASSIGNMENT_SECTIONS = ("deliver", "prove", "done when")
MIN_ASSIGNMENT_WORDS = 60
MIN_SECTION_WORDS = 8
ASSIGN_HINT = (
    "write for this stage what you would write into the prompt of a subagent doing the same job, under the headings "
    "of templates/stage-assignment.md (Deliver: every deliverable and how exact it has to be; Prove: what is shown "
    "by running it or by opening the source; Done when: what makes the stage finished), then "
    "`harness assign --run <id> --stage <stage> --file <path>`"
)


def assignment_problem(run_dir: Path, stage_id: str, text: str | None) -> str | None:
    """Why a text is no assignment, or None. A role session is never started on the brief and its type file alone:
    it gets every demand a subagent would get for the same job, written by the manager for this run and this stage.
    A program cannot tell whether the demands are the right ones; it can tell that they are there: the sections
    exist and say something, and the text is neither the brief nor the assignment of another stage."""
    if text is None:
        return "the stage has no assignment"
    found = _common.sections(text)
    body = {n: next((b for h, b in found.items() if h.startswith(n)), None) for n in ASSIGNMENT_SECTIONS}
    missing = [n for n, b in body.items() if b is None]
    if missing:
        return "the assignment has no section " + ", ".join(f"`{n.capitalize()}`" for n in missing)
    thin = [n for n, b in body.items() if len(b.split()) < MIN_SECTION_WORDS]
    if thin:
        return "too little is said under " + ", ".join(f"`{n.capitalize()}`" for n in thin)
    words = len(text.split())
    if words < MIN_ASSIGNMENT_WORDS:
        return (
            f"the assignment has {words} words; one that says what to deliver, how exactly and what to prove is longer"
        )
    brief = run_dir / "brief.md"
    if brief.is_file() and text.strip() == brief.read_text(encoding="utf-8").strip():
        return "the assignment repeats the brief; say what this stage owes in this run"
    others = (run_dir / "assignments").glob("*.md") if (run_dir / "assignments").is_dir() else []
    same = [p.stem for p in others if p.stem != stage_id and p.read_text(encoding="utf-8").strip() == text.strip()]
    if same:
        return f"the assignment is the text of stage {same[0]}; every stage owes something else"
    return None


def material_problem(root: Path, manifest: dict, stage_id: str, text: str) -> str | None:
    """Why the pieces the assignment lists cannot be given, or None: a path that does not exist, a range past the
    end of its file, or a file the stage's type may not read."""
    row = access.type_row(
        access.load_policy(root), next(s for s in manifest["stages"] if s["id"] == stage_id)["role_type"]
    )
    closed = access.unreadable(row, root)
    for item in pack.material_paths(text):
        problem = pack.piece_problem(root, item)
        if problem:
            return problem
        shut = [n for n, _, _ in pack.pieces(root, item) if any(fnmatch.fnmatch(n, pat) for pat in closed)]
        if shut:
            return f"material `{item}`: `{shut[0]}` is closed to the type of this stage"
    return None


def _assignment(run_dir: Path, stage_id: str) -> str | None:
    path = access.assignment_path(run_dir, stage_id)
    return path.read_text(encoding="utf-8") if path.is_file() else None


def assign(root: Path, run_id: str, stage_id: str, source: Path | None = None) -> dict:
    """`harness assign`: store the manager's assignment for a stage, before its first launch. The text is read from
    `source`, or from the draft the manager wrote at `<run>/assignments/drafts/<stage>.md`. A session that already
    runs takes more through `harness resume --message`."""
    run_dir = state.runs_root(root) / run_id
    source = source or access.assignment_path(run_dir, stage_id).parent / "drafts" / f"{stage_id}.md"
    manifest = state.load(root, run_dir / "manifest.json", "run-manifest")
    ids = [s["id"] for s in manifest["stages"]]
    if stage_id not in ids:
        return {"ok": False, "status": "unknown_stage", "stages": ids}
    ss = state.load(root, run_dir / "state.json", "run-state")["stages"][stage_id]
    if ss.get("attempts", 0) > 0 or ss.get("shards"):
        return {
            "ok": False,
            "status": "already_launched",
            "hint": "the session has its first message; what it still owes goes through `harness resume --message`",
        }
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return {"ok": False, "status": "unreadable", "why": str(exc)}
    problem = assignment_problem(run_dir, stage_id, text) or material_problem(root, manifest, stage_id, text)
    if problem:
        return {"ok": False, "status": "thin_assignment", "why": f"stage {stage_id}: {problem}", "hint": ASSIGN_HINT}
    path = access.assignment_path(run_dir, stage_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\n") + "\n", encoding="utf-8")
    return {"ok": True, "stage": stage_id, "assignment": str(path), "words": len(text.split())}


def lock_path(run_dir: Path, stage_id: str, shard: int | None) -> Path:
    return run_dir / "locks" / (f"{stage_id}-{shard:02d}.lock" if shard else f"{stage_id}.lock")


def unit(ss: dict, shard: int | None) -> dict:
    """The state record of one unit of work: the stage itself, or one shard of a sharded stage."""
    if shard is None:
        return ss
    return ss.setdefault("shards", {}).setdefault(
        f"{shard:02d}", {"status": "pending", "attempts": 0, "session_ids": [], "job_ids": [], "gate": "pending"}
    )


def round_attempts(u: dict) -> int:
    """The attempts of a unit in its current round: a loop resume starts a round (harness/rounds.py), and the
    retries after a failure count within it."""
    return u["attempts"] - u.get("round_start", 0)


def status(root: Path, run_id: str, stage_id: str, shard: int | None = None) -> dict:
    run_dir = state.runs_root(root) / run_id
    st = state.load(root, run_dir / "state.json", "run-state")
    manifest = state.load(root, run_dir / "manifest.json", "run-manifest")
    stage = next(s for s in manifest["stages"] if s["id"] == stage_id)
    for dep in stage.get("depends_on", []):
        d = st["stages"][dep]
        if d["status"] != "done" or d["gate"] != "pass" or d["approval"] in ("pending", "rejected"):
            return {"ok": False, "status": f"blocked-by:{dep}"}
    frozen = state.check_frozen(root, st)
    if frozen:
        return frozen
    lock = lock_path(run_dir, stage_id, shard)
    if lock.exists():
        return {"ok": False, "status": "locked", "lock": str(lock)}
    ss = st["stages"][stage_id]
    started = (ss.get("shards", {}).get(f"{shard:02d}", {}) if shard else ss).get("attempts", 0) > 0
    thin = None if started else assignment_problem(run_dir, stage_id, _assignment(run_dir, stage_id))
    if thin:  # a session never starts on the brief and its type file alone
        return {"ok": False, "status": "no_assignment", "why": f"stage {stage_id}: {thin}", "hint": ASSIGN_HINT}
    return {"ok": True, "status": "ready", "shards": stage.get("shards", 1)}


def components(tasks: list[dict]) -> list[list[dict]]:
    """Connected components of the `depends_on` graph, largest first. A component is the smallest set of tasks that
    can be finished on one worktree branch without waiting for another branch."""
    parent = {t["id"]: t["id"] for t in tasks}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for t in tasks:
        for dep in t.get("depends_on", []):
            if dep in parent:  # a dependency outside the list is already done elsewhere and does not bind shards
                parent[find(t["id"])] = find(dep)
    groups: dict[str, list[dict]] = {}
    for t in tasks:
        groups.setdefault(find(t["id"]), []).append(t)
    return sorted(groups.values(), key=lambda g: (-len(g), g[0]["id"]))


def split_tasks(root: Path, run_dir: Path, row: dict, stage: dict, st: dict) -> int:
    """One tasks.json per shard. A dependency component never crosses shards: each shard works on its own worktree
    branch and cannot see another shard's work. Components go largest-first to the least loaded shard; returns n."""
    source = next(item for item in row["inputs"] if item.endswith(":tasks.json"))
    dep, rel = source.split(":", 1)
    tasks = state.load(root, run_dir / "stages" / dep / rel, "tasks")["tasks"]
    groups = components(tasks)
    n = max(1, min(stage.get("shards", 1), len(groups)))
    buckets: list[list[dict]] = [[] for _ in range(n)]
    for group in groups:
        min(buckets, key=len).extend(group)
    for shard, bucket in enumerate(buckets, start=1):
        stage_dir = _stage_dir(run_dir, row["id"], shard)
        stage_dir.mkdir(parents=True, exist_ok=True)
        bucket.sort(key=lambda t: t["id"])  # waves inside the shard follow depends_on; ids stay in planner order
        state.save(root, stage_dir / "tasks.json", {"schema_version": 1, "stage": row["id"], "tasks": bucket}, "tasks")
        unit(st["stages"][row["id"]], shard)  # creates the shard's state record
    return n


def worktree_name(run_id: str, stage_id: str, shard: int | None) -> str:
    """The name a session passes to EnterWorktree: one checkout and one branch per unit, recognisable in
    `git worktree list`. Claude Code accepts letters, digits, dots, underscores and dashes, 64 characters at most."""
    tail = f"-{stage_id}" + (f"-{shard:02d}" if shard else "")
    return re.sub(r"[^A-Za-z0-9._-]", "-", run_id)[: 64 - len(tail)] + tail


def worktree_of(root: Path, policy: dict, run_id: str, row: dict, shard: int | None) -> str | None:
    """The checkout a unit works in, by name: its own for a type that changes the repository or builds a trial
    there (a planner), the prepared one for a unit that receives code work (work.prepare made it before the session
    starts). None for every other unit."""
    name = worktree_name(run_id, row["id"], shard)
    t = access.type_row(policy, row["role_type"])
    own = t["changes_repository"] or t["trial_checkout"]
    return name if own or (root / ".claude" / "worktrees" / name).is_dir() else None


def _demote(text: str) -> str:
    """Markdown with every heading one level down; lines inside a code fence are left as they are."""
    out, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        out.append("#" + line if not fenced and re.match(r"#{1,5} ", line) else line)
    return "\n".join(out)


def render_prompt(
    root: Path, policy: dict, manifest: dict, row: dict, stage_dir: Path, index: list[dict], shard: int | None
) -> str:
    """The first user message: the type's instruction and the role rules, the brief as the type may see it, the
    manager's assignment for this stage, then the stage and its inputs. The instruction and the rules are also in the
    system prompt; here they stand with the task, where a subagent receives its instruction: measured on one stage,
    a session that had them only in its system prompt did what its assignment asked and skipped the steps of its
    method (the checks before a change, the probes), and a subagent with the same text in its task did both. The
    assignment is what the manager would have written into the prompt of a subagent for this job; its headings are
    set one level down so that they stay inside its section. The knowledge pack and the material are not here; they
    follow the agent file in the system prompt (write_pack), where sessions of one type share them in the prompt
    cache. Inputs from earlier stages are the copies access.materialize_inputs made under
    `<stage dir>/input/`; no path outside the stage directory and the repository is named, and no attempt number
    or model; the run is visible only as part of the stage directory's own path."""
    inp = stage_dir / "input"
    agent = root / ".claude" / "agents" / f"{row['role_type']}.md"
    own = pack._front(agent.read_text(encoding="utf-8"))[1].strip() if agent.is_file() else ""
    rules = pack.rules(root, policy)
    parts = []
    if own or rules:
        parts += [
            "# Your instruction",
            "",
            (
                "Your type's instruction and the role rules, as your system prompt holds them. They stand here again "
                "with your task: work by them step by step, every step of the method, not only what the assignment names."
            ),
            "",
            *[_demote(t) + "\n" for t in (own, rules) if t],
        ]
    parts += [(inp / "brief.md").read_text(encoding="utf-8").rstrip("\n"), ""]
    assignment = inp / access.ASSIGNMENT
    if assignment.is_file():
        text = re.sub(r"\A# [^\n]*\n+", "", assignment.read_text(encoding="utf-8").strip("\n"))  # its own title
        parts += ["## Assignment (what this run needs from your stage; it is binding)", _demote(text), ""]
    parts += [
        "## Stage",
        f"stage: {row['id']}",
        f"role type: {row['role_type']}",
        f"stage directory: {stage_dir}",
    ]
    if shard:
        parts.append(
            f"shard: {shard:02d} — work only on the tasks listed in {stage_dir / 'tasks.json'}; they depend on nothing outside that file, and other shards own the rest"
        )
    name = worktree_of(root, policy, manifest["run_id"], row, shard)
    if name and any(e["as"].endswith("/changes.patch") for e in index):
        parts.append(
            f"worktree: {name} — a checkout of the work this stage receives; call EnterWorktree with this name "
            "before you read or run anything in the repository"
        )
    elif name and access.type_row(policy, row["role_type"])["trial_checkout"]:
        parts.append(
            f"worktree: {name} — a checkout of your own for the trial; call EnterWorktree with this name before "
            "you build or run anything; the checkout is not delivered and is removed when the next stage starts, "
            "what you built in it reaches the writer as output/trial/trial.patch"
        )
    elif name:
        parts.append(f"worktree: {name}")
    parts += ["", "## Inputs (their text is in your system prompt under Material, unless it names them as left out)"]
    parts += [f"- {inp / 'brief.md'}"]
    parts += [f"- {inp / e['as']}" for e in index if e["as"] != "brief.md"]
    if any(item in ("context", "spec") for item in row["inputs"]):
        paths = manifest.get("context_paths") or []
        parts += [f"- {p}" for p in paths] if paths else ["- see the Material section of the brief"]
    parts += [
        "",
        "## Output",
        f"- write to {stage_dir / 'output'}; result: {stage_dir / 'result.json'}; checkpoint: {stage_dir / 'progress.md'}",
    ]
    return "\n".join(parts) + "\n"


def stage_material(root: Path, policy: dict, row: dict, inp: Path) -> dict:
    """The arguments of pack.material for one stage: the pieces its brief and its assignment name, the pieces the
    harness chooses for it by script (pieces.select: what its texts cite and name, and what matches its brief), and
    its inputs. A type that cannot write a file (access.writes_files) gets no piece chosen by script: it could account
    for none, and the judge may not open the work or its sources. No model takes part and the manager spends no turn
    on it."""

    def read(name: str) -> str:
        return (inp / name).read_text(encoding="utf-8", errors="replace") if (inp / name).is_file() else ""

    t = access.type_row(policy, row["role_type"])
    context = "context" in t["may_receive"]
    brief, assignment = read("brief.md"), read(access.ASSIGNMENT)
    inputs = (
        [
            (p.relative_to(inp).as_posix(), p)
            for p in sorted(inp.rglob("*"))
            if p.is_file() and p.relative_to(inp).as_posix() not in ("brief.md", access.ASSIGNMENT)
        ]
        if inp.is_dir()
        else []
    )
    # what the stage holds: the lists under `## Material` are given as they are, the rest is searched for paths.
    # What the job is about is what the brief says beside its list: an assignment speaks mostly of how to work
    # (deliver, prove, quote), and those words would match the documents about working instead of the subject.
    texts = [pack.without_material(brief), pack.without_material(assignment)]
    texts += [p.read_text(encoding="utf-8", errors="replace") for _, p in inputs]
    closed = access.unreadable(t, root)
    skip = pack.in_prompt(root, policy, row["role_type"])
    receives = "context" in row.get("inputs", [])  # the stage receives the material of the run
    chosen = access.writes_files(root, row["role_type"])  # a type that cannot write gets no piece chosen by script
    return {
        "brief_items": pack.material_paths(brief) if receives else [],
        "own_items": pack.material_paths(assignment),
        "inputs": inputs,
        "context": context,
        "extra": pieces.select(root, closed, context, texts, texts[0], skip, receives) if chosen else [],
        "model": row.get("model"),
    }


def preview_material(root: Path, run_id: str, stage_id: str) -> dict:
    """`harness material`: what a stage's session will get in its cached prompt, piece by piece and why, without a
    model. Before the first launch the stage's inputs are built for it, as the launch would build them."""
    run_dir = state.runs_root(root) / run_id
    policy = access.load_policy(root)
    manifest = state.load(root, run_dir / "manifest.json", "run-manifest")
    ids = [s["id"] for s in manifest["stages"]]
    if stage_id not in ids:
        return {"ok": False, "status": "unknown_stage", "stages": ids}
    stages = {s["id"]: s for s in state.load_table(root, manifest.get("pipeline", "default"))["stages"]}
    row = stages[stage_id]
    stage_dir = _stage_dir(run_dir, stage_id, None)
    if not (stage_dir / "input").is_dir():
        try:
            access.materialize_inputs(policy, stages, run_dir, row, stage_dir)
        except access.AccessError as e:  # an earlier stage has not delivered yet
            return {"ok": False, "status": "access_refused", "why": str(e)}
    args = stage_material(root, policy, row, stage_dir / "input")
    parts = pack.material_parts(root, policy, row["role_type"], **args)
    return {
        "ok": True,
        "stage": stage_id,
        "given": parts["given"],
        "left_out": parts["left_out"],
        "does_not_fit": parts["does_not_fit"],
        "not_text": parts["not_text"],
        "chars": len(parts["text"]),
        "estimated_tokens": len(parts["text"]) // pack.CHARS_PER_TOKEN,
    }


def write_pack(root: Path, policy: dict, row: dict, stage_dir: Path, again: bool = False) -> Path | None:
    """Write what follows the agent file in the session's system prompt to `<stage dir>/pack.md`, once, at launch:
    the role rules, the type's knowledge pack (pack.supplement) and then what this stage needs (pack.material with
    the pieces stage_material chooses by script). What sessions of one type share comes first. The file is what
    `--append-system-prompt-file` reads on launch and on every resume, so the session's system prompt does not change
    when the rules or the wiki change during the run. `again` rewrites it: a stage that checks again after a round
    gets the Material of the new round (harness/rounds.py). Returns None when there is nothing to append."""
    text = pack.supplement(root, policy, row["role_type"])
    given = pack.material(root, policy, row["role_type"], **stage_material(root, policy, row, stage_dir / "input"))
    if given:
        text = "\n\n".join(t.strip() for t in (text, given) if t.strip()) + "\n"
    path = stage_dir / "pack.md"
    if not text:
        return None
    if again or not (path.exists() or path.is_symlink()):  # a rename replaces a link a session put there; a write
        state.write_atomic(path, text)  # would follow it out of the run (resume runs outside the sandbox)
    return path


def own_tasks(root: Path, run_dir: Path, row: dict) -> None:
    """A stage that changes the repository in one session takes the planner's whole task list as its own tasks.json,
    as each shard of a wave takes its part (split_tasks): its gate and the stages after it read the list there."""
    source = next((item for item in row["inputs"] if item.endswith(":tasks.json")), None)
    if source is None:
        return
    dep, rel = source.split(":", 1)
    tasks = state.load(root, run_dir / "stages" / dep / rel, "tasks")["tasks"]
    doc = {"schema_version": 1, "stage": row["id"], "tasks": tasks}
    state.save(root, _stage_dir(run_dir, row["id"], None) / "tasks.json", doc, "tasks")


def drop_trials(root: Path, policy: dict, stages: dict[str, dict], run_id: str, row: dict) -> None:
    """A planner's trial checkout is its author's working material: it goes when a stage that takes the plan starts,
    unless that stage returns to the planner (the critic of the stage `attack`), whose findings resume the planner in
    the same checkout (harness/rounds.py)."""
    named = {i.partition(":")[0] for i in row["inputs"] if ":" in i} | set(row.get("depends_on") or [])
    back = (row.get("returns_to") or {}).get("stage")
    for dep in sorted(named & set(stages)):
        if dep != back and access.type_row(policy, stages[dep]["role_type"])["trial_checkout"]:
            work.drop_checkout(root, worktree_name(run_id, dep, None))


def stage_inputs(
    root: Path, policy: dict, stages: dict[str, dict], run_dir: Path, row: dict, stage_dir: Path, name: str
) -> list[dict]:
    """What a unit is given before its session starts, at launch and when it checks again after a round
    (harness/rounds.py): input/ from the declared inputs, then the code work it reviews (prepare_work), whose patch
    joins the index. pack.md is written after this, so its Material holds the patch of the work as it is now. Raises
    access.AccessError, work.WorkConflict."""
    index = access.materialize_inputs(policy, stages, run_dir, row, stage_dir)
    return prepare_work(root, policy, stages, run_dir, row, stage_dir, name, index) or index


def prepare_work(
    root: Path,
    policy: dict,
    stages: dict[str, dict],
    run_dir: Path,
    row: dict,
    stage_dir: Path,
    name: str,
    index: list[dict] | None = None,
) -> list[dict] | None:
    """The code work a unit reviews, prepared and recorded: one commit with a checkout for a type that can enter one,
    the change as `changes.patch`, read-only (work.prepare), and its entry in the unit's index (record_work). None
    when the unit reviews no committed work. Launch, a recheck and a resume call this, so the index always names the
    patch the session has. Raises access.AccessError for a type that could run commands on the work but not enter it."""
    tools = (access.tools_flag(root, row["role_type"]) or "").split(",")
    prepared = work.prepare(root, policy, stages, run_dir, row, stage_dir, name, checkout="EnterWorktree" in tools)
    if not prepared:
        return None
    if "EnterWorktree" not in tools and "Bash" in tools:  # it could run commands on the work, not enter it
        raise access.AccessError(
            f"stage {row['id']} receives code work, and the agent file of {row['role_type']} lists no EnterWorktree"
        )
    return record_work(run_dir, stage_dir, prepared, index)


def record_work(run_dir: Path, stage_dir: Path, prepared: dict, index: list[dict] | None = None) -> list[dict]:
    """Record the change patch of a unit's work among its input copies: its entry (the diff it was made from, its name
    under input/, its sha256) takes the place of an earlier one of the same name in the unit's index (`index`, else the
    one on disk), the index is written again (access.write_index), and `<unit>.work.json` keeps what was prepared."""
    rel = Path(prepared["patch"]).relative_to(stage_dir / "input").as_posix()
    if index is None:
        path = access.unit_record(run_dir, stage_dir, "inputs")
        index = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    entry = {"source": f"git diff {prepared['base']} {prepared['commit']}", "as": rel, "sha256": prepared["sha256"]}
    index = [e for e in index if e.get("as") != rel] + [entry]
    access.write_index(run_dir, stage_dir, index)
    access.unit_record(run_dir, stage_dir, "work").write_text(json.dumps(prepared, indent=2), encoding="utf-8")
    return index


def session_flags(
    run_dir: Path,
    stage: dict,
    session_id: str | None = None,
    root: Path | None = None,
    row: dict | None = None,
    stage_dir: Path | None = None,
) -> list[str]:
    """Flags every role session gets, on launch and on resume (`--add-dir` and `--settings` are not restored by --resume).
    `--settings` carries what a role session needs beyond the project file: no inbound messages; commit trailers that tie
    a commit to its run and stage; the harness variables as an `env` block (state.harness_env), which a background
    session keeps when its process is restarted; for an `auto` stage only, the classifier environment, which Claude
    Code does not read from project settings; and the access rules of the type (access.stage_settings): what it may
    not read, which user-level instruction files it does not load, which project plugins and skills it keeps.
    `--tools` is the tool list of the type's agent file (access.tools_flag).
    `--append-system-prompt-file` is the role rules and the knowledge pack, written at launch (write_pack).
    `--no-chrome` keeps the browser integration, its tools and its instructions out of a role session.
    `--mcp-config` carries the MCP servers the type's row names (access.mcp_config); with `--strict-mcp-config` no other loads.
    `--add-dir` is the stage directory and what the type's row opens, never the run root (access.working_dirs).
    `--setting-sources project,local` keeps the user's own settings, plugins and hooks out of a role session.
    `--model` and `--effort` are the stage's, also on a resume, which would otherwise take the user's defaults."""
    shard = int(stage_dir.name) if access.SHARD.match(stage_dir.name) else None
    policy = access.load_policy(root)
    settings: dict = {
        "crossSessionInbound": "refuse",
        "env": {
            **state.harness_env(run_dir, stage["id"], stage["role_type"], stage["mode"], shard),
            **access.env_extra(policy, row, stage_dir),
        },
    }
    checkout = worktree_of(root, policy, run_dir.name, row, shard)
    if checkout:  # guard-bash refuses every command until the session has entered this checkout
        settings["env"]["HARNESS_WORKTREE"] = checkout
    if session_id:
        trailer = f"Harness-Run: {run_dir.name}\nHarness-Stage: {stage['id']}\n"
        if shard:
            trailer += f"Harness-Shard: {shard:02d}\n"
        if stage["mode"] == "print":  # only a print session runs under the id the manifest fixed
            trailer += f"Claude-Session-Id: {session_id}\n"
        settings["attribution"] = {"commit": trailer + "Co-Authored-By: Claude <noreply@anthropic.com>"}
    if stage["permission_mode"] == "auto" and root:
        settings.update(json.loads((root / "docs" / "roles" / "auto-mode.json").read_text(encoding="utf-8")))
    settings.update(access.stage_settings(policy, run_dir, row, stage_dir, root, checkout))
    # The model is pinned twice, by flag and by setting, on every start and every resume. `claude --resume` does not
    # restore the model of the session it continues: seen live, a resumed planner and a resumed writer ran on the
    # user's default model, which the policy forbids for role sessions.
    settings["model"] = stage["model"]
    dirs = access.working_dirs(policy, run_dir, row, stage_dir)
    mcp = access.mcp_config(root, policy, row)  # only the servers the type's row names; nothing else is loaded
    tools = access.tools_flag(root, row["role_type"])
    knowledge = stage_dir / "pack.md"
    return [
        "--add-dir",
        *dirs,
        "--permission-mode",
        stage["permission_mode"],
        "--settings",
        json.dumps(settings, sort_keys=True),
        "--setting-sources",
        "project,local",
        *(["--tools", tools] if tools is not None else []),  # "": no built-in tool (access.tools_flag)
        *(["--append-system-prompt-file", str(knowledge)] if knowledge.is_file() else []),
        "--no-chrome",
        "--strict-mcp-config",  # fixed tool set per type, no approval prompt
        *(["--mcp-config", json.dumps(mcp, sort_keys=True)] if mcp else []),
        "--model",
        stage["model"],
        "--effort",
        stage["effort"],
    ]


def print_flags(root: Path, row: dict, stage: dict, manifest: dict) -> list[str]:
    """Flags of a `mode: print` call: the API copy of the result schema, budget and turn limits."""
    full = state.schema(root, row["json_schema"].removesuffix(".schema.json"))
    return [
        "--permission-prompts",
        "none",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(state.api_schema(full)),  # the API copy; the result is validated locally against the full schema
        "--max-turns",
        str(row.get("max_turns", 60)),
        "--max-budget-usd",
        str(stage.get("max_budget_usd", manifest["limits"].get("max_budget_usd_print", 5))),
    ]


def own_logs(stage_dir: Path) -> Path:
    """The stage's `logs/`, a folder of the harness: a link or a file a session put in its place goes first, since
    launch, resume and poll write there outside the sandbox and a write would follow the link out of the run."""
    logs = stage_dir / "logs"
    if logs.is_symlink() or (logs.exists() and not logs.is_dir()):
        logs.unlink()
    logs.mkdir(parents=True, exist_ok=True)
    for f in logs.iterdir():  # a log the harness appends to or writes over is never a link
        if f.is_symlink():
            f.unlink()
    return logs


def run_print(root: Path, cmd: list[str], env: dict, stage_dir: Path, st: dict, u: dict) -> dict:
    """Run a print-mode command to completion and record the outcome on the unit: `checkpointed` with result.json,
    or `failed` with `last_error` (exit code, stderr tail) so that poll reports it and resume can retry."""
    res = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True, check=False)
    state.write_atomic(own_logs(stage_dir) / "print.json", res.stdout)
    try:
        out = json.loads(res.stdout)
    except json.JSONDecodeError:
        out = {}
    return record_print(root, stage_dir, st, u, out, res.returncode, res.stderr)


def structured_result(out: dict) -> dict | None:
    """The stage result in the output of a print run: `structured_output`, or the final message when it is the same
    JSON written as text (seen live: an agent file that did not list the StructuredOutput tool left the judge no way
    to return its verdict except as text, and a paid run was thrown away). The schema decides either way."""
    if isinstance(out.get("structured_output"), dict):
        return out["structured_output"]
    text = str(out.get("result") or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    try:
        doc = json.loads(fenced.group(1) if fenced else text)
    except ValueError:
        return None
    return doc if isinstance(doc, dict) else None


def record_print(root: Path, stage_dir: Path, st: dict, u: dict, out: dict, exit_code: int, stderr: str) -> dict:
    """Record what a print run returned on its unit. The run is paid for whether its result is usable or not."""
    st.setdefault("cost", {"print_total_usd": 0.0, "note": ""})["print_total_usd"] += float(
        out.get("total_cost_usd") or 0.0
    )
    structured = structured_result(out) if exit_code == 0 else None
    note = "print run produced no structured_output"
    if structured is not None:
        try:
            state.save(root, stage_dir / "result.json", structured, "stage-result")
        except jsonschema.ValidationError as e:
            structured, note = None, f"the result does not match stage-result.schema.json: {e.message[:300]}"
    if structured is None:
        u["status"] = "failed"
        u["last_error"] = {
            "at": state.now(),
            "exit_code": exit_code,
            "stderr": (stderr or str(out.get("result", "")))[-2000:],
            "note": note,
        }
        return {
            "ok": False,
            "status": "print_failed",
            "exit_code": exit_code,
            "why": note,
            "stderr": u["last_error"]["stderr"][-500:],
        }
    u["status"] = "checkpointed"
    u.pop("last_error", None)
    return {"ok": True, "status": "checkpointed", "total_cost_usd": out.get("total_cost_usd")}


def sandbox_problem(root: Path, mode: str = "bg") -> str | None:
    """Why a role session would end at its start: its settings hold `sandbox.failIfUnavailable` (harness/access.py).
    A background session runs with the PATH of Claude Code's background service when one runs, a print session with
    this process's."""
    return doctor.sandbox_problem(root, doctor.service_path() if mode == "bg" else None)


def before_start(root: Path, mode: str = "bg") -> dict:
    """What launch and resume check and record before `claude` starts a role session: the sandbox it needs, and the
    trust record `claude --bg` needs (harness/trust.py). An answer with `ok` false is returned as it is."""
    problem = sandbox_problem(root, mode)
    if problem:
        return {"ok": False, "status": "no_sandbox", "why": problem, "fix": doctor.SANDBOX_FIX}
    note = trust.ensure(root)
    return {"ok": True, **({"trust": note} if note else {})}


def launch(root: Path, run_id: str, stage_id: str, shard: int | None = None) -> dict:
    held = pause.refusal(root)
    if held:  # the pause switch: no session starts (ADR-0023)
        return held
    run_dir = state.runs_root(root) / run_id
    manifest = state.load(root, run_dir / "manifest.json", "run-manifest")
    st = state.load(root, run_dir / "state.json", "run-state")
    before = copy.deepcopy(st)  # what this launch read; commit() carries its own changes into the file as it is then
    stage = next(s for s in manifest["stages"] if s["id"] == stage_id)
    row = _row(root, stage_id, manifest.get("pipeline", "default"))
    ss = st["stages"][stage_id]
    if row.get("parallel") == "per_task" and shard is None:
        # One call launches the whole wave: split the planner's tasks, then one session per shard, each with its own lock.
        ready = status(root, run_id, stage_id, None)
        if not ready["ok"]:
            return ready
        if ss.get("shards"):
            return {
                "ok": False,
                "status": "already_launched",
                "hint": "the wave exists; resume a shard with `harness resume --shard N`",
            }
        start = before_start(root, stage["mode"])  # before the split: a refused wave leaves no shard to resume
        if not start["ok"]:
            return start
        with state.locked(run_dir / "state.json"):  # the shard records go into the file as it is now (ADR-0021)
            fresh = state.load(root, run_dir / "state.json", "run-state")
            n = split_tasks(root, run_dir, row, stage, fresh)
            state.save(root, run_dir / "state.json", fresh, "run-state")
        # The first shard goes alone and the rest wait for its first response: the prompt cache then serves them the
        # tools, the agent file and the pack instead of charging every shard for the same write.
        launched = [launch(root, run_id, stage_id, 1)]
        warm = n > 1 and launched[0]["ok"] and wait_first_response(launched[0].get("session_id"))
        launched += [launch(root, run_id, stage_id, s) for s in range(2, n + 1)]
        return {
            "ok": all(item["ok"] for item in launched),
            "stage": stage_id,
            "shards": n,
            "cache_warm": warm,
            "launched": launched,
        }

    ready = status(root, run_id, stage_id, shard)
    if not ready["ok"]:
        return ready
    if shard and shard > stage.get("shards", 1):
        return {"ok": False, "status": "shard_out_of_range", "max_shards": stage.get("shards", 1)}
    wrong = access.model_problem(access.load_policy(root), stage["model"])
    if wrong:  # the manifest fixed the model when the run was created; the policy may have changed since
        return {"ok": False, "status": "access_refused", "why": f"stage {stage_id}: {wrong}"}
    u = unit(ss, shard)
    if u["status"] in rounds.LOOPING:  # a round of a loop is continued with its findings, never started again
        hint = f"uv run harness resume --run {run_id} --stage {stage_id} --rework"
        return {"ok": False, "status": "in_rework", "unit_status": u["status"], "hint": hint}
    if u["attempts"] > 0:  # the fixed --session-id is used once; every later attempt continues the session
        return {"ok": False, "status": "already_launched", "attempts": u["attempts"], "hint": "use `harness resume`"}
    start = before_start(root, stage["mode"])
    if not start["ok"]:
        return start

    stage_dir = _stage_dir(run_dir, stage_id, shard)
    (stage_dir / "output").mkdir(parents=True, exist_ok=True)
    own_logs(stage_dir)
    policy = access.load_policy(root)
    table = state.load_table(root, manifest.get("pipeline", "default"))
    stages = {s["id"]: s for s in table["stages"]}
    drop_trials(root, policy, stages, run_id, row)
    if row.get("parallel") != "per_task" and access.type_row(policy, row["role_type"])["changes_repository"]:
        own_tasks(root, run_dir, row)
    try:  # what the stage may receive is decided by docs/roles/need-to-know.yaml, not by the caller
        index = stage_inputs(root, policy, stages, run_dir, row, stage_dir, worktree_name(run_id, stage_id, shard))
    except work.WorkConflict as e:
        return {"ok": False, "status": "work_conflict", "files": e.files, "branches": e.branches, "why": str(e)}
    except access.AccessError as e:
        return {"ok": False, "status": "access_refused", "why": str(e)}
    # nothing the stage's texts list is left for the session to search for: a stage whose material does not fit is
    # split or narrowed by the manager before it starts (ADR-0008)
    parts = pack.material_parts(
        root, policy, row["role_type"], **stage_material(root, policy, row, stage_dir / "input")
    )
    if parts["does_not_fit"]:
        return {
            "ok": False,
            "status": "material_does_not_fit",
            "pieces": parts["does_not_fit"],
            "hint": "split the stage or narrow its assignment; `harness material` shows what fits",
        }
    prompt = render_prompt(root, policy, manifest, row, stage_dir, index, shard)
    (stage_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    try:
        write_pack(root, policy, row, stage_dir)
    except access.AccessError as e:  # a pack file the type's row names is missing
        return {"ok": False, "status": "access_refused", "why": str(e)}

    session_id = stage["session_ids"][(shard or 1) - 1]
    env = state.session_env(run_dir, stage_id, stage["role_type"], stage["mode"], shard)
    if stage["mode"] != "bg":  # a background session reads these from its settings, never from the process
        env.update(access.env_extra(policy, row, stage_dir))
    name = f"{run_id}/{stage_id}" + (f"/{shard:02d}" if shard else "")
    common = [
        "--agent",
        stage["role_type"],
        "--name",
        name,
        *session_flags(run_dir, stage, session_id, root, row, stage_dir),
    ]

    with otel.span("invoke_agent", agent_name=stage["role_type"], run_id=run_id, stage=stage_id, model=stage["model"]):
        if stage["mode"] == "bg":
            cmd = ["claude", *common, "--bg", prompt]
            res = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True, check=False)
            (stage_dir / "logs" / "launch.txt").write_text(res.stdout + res.stderr, encoding="utf-8")
            if res.returncode != 0:
                return {"ok": False, "status": "launch_failed", "stderr": res.stderr[-2000:]}
            m = BG_ID.search(res.stdout)
            job_id = m.group(1) if m else None
            # `claude --bg` assigns the session id itself; the one in the manifest is not used for this unit
            session_id = session_of(root, job_id) or session_id
            u["status"] = "launched"
            outcome = {"ok": True}
        else:
            job_id = None
            outcome = run_print(
                root,
                ["claude", "-p", "--session-id", session_id, *common, *print_flags(root, row, stage, manifest), prompt],
                env,
                stage_dir,
                st,
                u,
            )

    u["attempts"] += 1
    if session_id not in u["session_ids"]:
        u["session_ids"].append(session_id)
    if job_id:
        u.setdefault("job_ids", []).append(job_id)
    u["started_at"] = state.now()
    if shard:  # the stage row mirrors its shards; poll recomputes the aggregate
        ss["status"] = u["status"]
        ss["attempts"] = max(x["attempts"] for x in ss["shards"].values())
        if session_id not in ss["session_ids"]:
            ss["session_ids"].append(session_id)
        if job_id:
            ss.setdefault("job_ids", []).append(job_id)
    st["status"], st["current_stage"], st["updated_at"] = "running", stage_id, state.now()
    if commit(root, run_dir, before, st, stage_id, shard) is None:
        return aborted_meanwhile(run_id, session_id, job_id)
    if outcome["ok"]:  # a failed print run holds no process, so it leaves no lock
        lock_path(run_dir, stage_id, shard).write_text(
            json.dumps({"session_id": session_id, "pid": os.getpid(), "started_at": state.now()}), encoding="utf-8"
        )
    return {
        **outcome,
        **({"trust": start["trust"]} if "trust" in start else {}),
        "stage": stage_id,
        "shard": shard,
        "mode": stage["mode"],
        "session_id": session_id,
        "job_id": job_id,
        "attempts": u["attempts"],
    }


def _carry(seen: dict, done: dict, now: dict, skip: tuple[str, ...] = ()) -> None:
    """Put into `now` what changed from `seen` to `done`: a changed or new field takes `done`'s value, a field `done`
    dropped goes, and a list keeps `now`'s items and gains the ones `done` added."""
    for key in (seen.keys() | done.keys()) - set(skip):
        if key in seen and key in done and seen[key] == done[key]:
            continue
        if key not in done:
            now.pop(key, None)
        elif isinstance(done[key], list):
            added = [x for x in done[key] if x not in seen.get(key, [])]
            now[key] = [*now.get(key, []), *(x for x in added if x not in now.get(key, []))]
        else:
            now[key] = copy.deepcopy(done[key])


def commit(root: Path, run_dir: Path, before: dict, after: dict, stage_id: str, shard: int | None) -> dict | None:
    """Record what a launch or a resume did to one unit, which it did on a copy of state.json read before `claude`
    ran (ADR-0021). Under the file's one lock the file is read again and only that work is carried over: the fields of
    the unit and of its stage row that changed, the ids it added, the escalations it marked answered, the print cost
    it added, and the run's status, current stage and time. Everything else stays as the file has it now, an approval
    recorded meanwhile among it. Nothing is written to a run aborted meanwhile: returns None then, else the state."""
    path = run_dir / "state.json"
    with state.locked(path):
        fresh = state.load(root, path, "run-state")
        if fresh["status"] == "aborted":
            return None
        b_ss, a_ss, f_ss = (doc["stages"][stage_id] for doc in (copy.deepcopy(before), after, fresh))
        if shard:
            _carry(unit(b_ss, shard), unit(a_ss, shard), unit(f_ss, shard))
        _carry(b_ss, a_ss, f_ss, skip=("shards",))
        was = {e["id"]: e["status"] for e in before["escalations"]}
        marked = {e["id"]: e["status"] for e in after["escalations"] if was.get(e["id"]) != e["status"]}
        for e in fresh["escalations"]:
            e["status"] = marked.get(e["id"], e["status"])
        added = after.get("cost", {}).get("print_total_usd", 0.0) - before.get("cost", {}).get("print_total_usd", 0.0)
        if added:
            fresh.setdefault("cost", {"print_total_usd": 0.0, "note": ""})["print_total_usd"] += added
        _carry(before, after, fresh, skip=("stages", "escalations", "cost", "changed_at"))
        state.save(root, path, fresh, "run-state")
    return fresh


def aborted_meanwhile(run_id: str, session_id: str | None, job_id: str | None) -> dict:
    """The answer of a launch or a resume whose run was aborted while `claude` ran: nothing was recorded, and the
    session it started is named so that the human can stop it (`claude stop <job>`)."""
    why = "the run was aborted while the session started; an aborted run is a record and nothing was written to it"
    return {
        "ok": False,
        "status": "run_aborted",
        "run_id": run_id,
        "session_id": session_id,
        "job_id": job_id,
        "why": why,
    }
