"""The manager's checks before a launch (`check`, `timeout`) and two audits of a run's practice (`polls`, `clock`);
references/preflight-and-capacity.md says when each runs. `check` writes `<run-dir>/_control/preflight.json`.

  python3 -I scripts/manager/preflight.py check <run-dir> --checkout <checkout> [options]
  python3 -I scripts/manager/preflight.py timeout <dir>... [--check MIN]
  python3 -I scripts/manager/preflight.py polls <transcript>...
  python3 -I scripts/manager/preflight.py clock <record>... [--transcript JSONL]... [--slack MIN]

Exit codes: 0 nothing failed; 1 a check failed or a problem was found; 2 a usage error (argparse's own).
"""

import argparse
import contextlib
import itertools
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2]
# Built from parts, so that no skill file spells a model name (Global Constraint 10).
MODELS = ("fa" + "ble", "op" + "us", "son" + "net", "hai" + "ku")
MODEL = re.compile(r"\b(?:" + "|".join(MODELS) + r")\b|--model\b", re.IGNORECASE)
TEN = (
    "Read(~/.claude/projects/**)",
    "Read(/<run-dir>/_control/**)",
    "Read(/<checkout>/docs/handoff/**)",
    "Read(//proc/**)",
    "Bash(claude agents:*)",
    "Bash(claude logs:*)",
    "Bash(claude attach:*)",
    "Bash(ps:*)",
    "Bash(pgrep:*)",
    "Read(~/.claude/.credentials.json)",
)
SANDBOX_FLAGS = (("enabled", True), ("failIfUnavailable", True), ("allowUnsandboxedCommands", False))
SINGLE_SLASH = re.compile(r"(?:Edit|Write)\(/(?!/)")  # J8: `Edit(/x)` is read as the root or the cwd, two ways
WAITER = re.compile(r"[\w./<>~-]*wait_for_[a-z_]+\.py")
KEYS = ("Purpose:", "Size:", "Model rule:", "Estimate:", "Budget:", "Usage:")  # the launch table's key lines
ESTIMATE = (
    ("the number of roles", r"\b\d+ roles?\b"),
    ("the number of sessions", r"\b\d+(?:-\d+)? sessions?\b"),
    ("a dollar amount", r"\$\d"),
    ("fresh sessions per unit", r"\bsessions? per unit\b"),
    ("measurement page", r"measurements/\S+\.md"),  # R5: the dollars come from the last run's page, not a guess
    ("cost per session", r"\$\d[\d.]*(?:-\$?\d[\d.]*)? per session"),
    ("start-up read", r"\bstart-up read \d[\d.]*k tokens\b"),  # lessons.md: startup_report.py's median, measured
)
CELLS = ("role", "lane", "settings", "skills", "ECC texts", "cost estimate")
# a role whose work another role answers: the table holds both from the start, or the manager ends up doing the
# missing role's work itself (2026-10-31: a critic launched with no planner; the manager wrote the answers)
PAIRS = (("critic", "planner", "nobody answers its findings, and the manager never does"),)
YES = re.compile(r"(?m)^Yes: (\d{4}-\d\d-\d\dT\d\d:\d\dZ) — (.*)$")
MINUTE = "%Y-%m-%dT%H:%MZ"
SCRIPT_TIMEOUT = 120  # seconds, for the probe and each script the pre-flight runs
SESSIONS = ("claude", "agents", "--json", "--all")  # a row per session on the machine; a row with a pid is live
LISTING_TIMEOUT = 300  # seconds, as clean_jobs_tmp.py and collect_run.py allow the listing
LIVE = re.compile(r"(?m)^Live: ([^\n—]*)")  # `Live: <name>, <name> — <why>`: sessions the manager read in the list
LOOP_WORD = re.compile(r"\b(do|done|sleep)\b")
STAMP = re.compile(
    r"\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d)?Z|\d{4}-\d\d-\d\d \d\d:\d\d(?::\d\d)?(?: UTC)?|\b\d\d:\d\d(?::\d\d)? UTC"
)
LOOSE = re.compile(r"(?<![\w:.])\d{1,2}:[0-5x][0-9x](?::[0-5][0-9])?(?![\w:])")  # a time left after the stamps
WRITTEN = {"Write": "content", "Edit": "new_string", "Bash": "command"}  # the input that holds a tool's new text


@dataclass
class Result:
    status: str  # PASS, FAIL or SKIP
    check: str
    agent: str | None  # None for a run-wide check
    detail: str


@dataclass
class State:
    """What `check` reads once: the paths, the config's agents and the settings of every checked role."""

    args: argparse.Namespace
    run: str
    checkout: str
    control: str
    now: datetime
    config: str = ""
    agents: dict = field(default_factory=dict)
    roles: list = field(default_factory=list)
    settings: dict = field(default_factory=dict)


def parse_time(text: str) -> datetime:
    """An ISO time (`2026-10-29T18:24Z` too); a time without a zone is UTC."""
    t = datetime.fromisoformat(text.strip())
    return t.replace(tzinfo=UTC) if t.tzinfo is None else t.astimezone(UTC)


def verdict(check: str, agent: str | None, problems: list[str], passed: str) -> Result:
    """FAIL with the problems joined, else PASS with `passed`."""
    return Result("FAIL", check, agent, "; ".join(problems)) if problems else Result("PASS", check, agent, passed)


def inside(path: str, folder: str) -> bool:
    return path.startswith(folder.rstrip("/") + "/")


def trim(path: str) -> str:
    return re.sub(r"/\*\*$", "", path).rstrip("/") or "/"


def rule_path(rule: str, cwd: str) -> str:
    """An Edit(...) or Write(...) rule's path: //x is /x, ~/x is $HOME/x, /x and x lie under the cwd."""
    p = rule[rule.index("(") + 1 : -1]
    if p.startswith("//"):
        return trim(p[1:])
    if p.startswith("~/"):
        return trim(os.path.expanduser(p))
    return trim(os.path.join(cwd, p.lstrip("/")))


def fs_path(entry: str, cwd: str) -> str:
    """A sandbox.filesystem entry: ~/x is $HOME/x, an absolute path is kept, a relative one lies under the cwd."""
    return trim(os.path.join(cwd, os.path.expanduser(entry) if entry.startswith("~/") else entry))


def last_line(out: str, err: str) -> str:
    """The last line of stdout, or of stderr when stdout is empty."""
    for text in (out, err):
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            return lines[-1]
    return "no output"


def script(*argv: str) -> tuple[int, str, str]:
    """Run a script as `python3 -I`: its exit, stdout and stderr."""
    try:
        p = subprocess.run(
            [sys.executable, "-I", *argv], capture_output=True, text=True, timeout=SCRIPT_TIMEOUT, check=False
        )
    except subprocess.TimeoutExpired:
        return -1, "", f"timed out after {SCRIPT_TIMEOUT} s"
    return p.returncode, p.stdout, p.stderr


def script_result(check: str, path: str, *argv: str) -> Result:
    if not os.path.isfile(path):
        return Result("FAIL", check, None, f"{path}: no such file")
    code, out, err = script(path, *argv)
    return Result("PASS" if code == 0 else "FAIL", check, None, f"exit {code}: {last_line(out, err)}")


def load_settings(st: State) -> list[str]:
    """Read every checked role's settings into `st.settings`; the problems found."""
    problems = []
    for role in st.roles:
        rel = str(st.agents[role].get("settings", ""))
        path = os.path.abspath(os.path.join(st.run, rel))  # an absolute path is kept
        if not rel or not inside(path, st.control):
            problems.append(f"{role}: settings {path} is not inside {st.control}/")
            continue
        try:
            st.settings[role] = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problems.append(f"{role}: settings {path} does not parse: {exc}")
            continue
        if not isinstance(st.settings[role], dict):
            problems.append(f"{role}: settings {path} is not an object")
    return problems


def check_config(st: State) -> Result:
    a = st.args
    st.config = os.path.abspath(a.config or os.path.join(st.control, "_agents.json"))
    st.roles = [r.strip() for r in a.roles.split(",") if r.strip()] if a.roles else []
    if not inside(st.config, st.control):
        return Result("FAIL", "config", None, f"{st.config} is not inside {st.control}/")
    try:
        agents = json.loads(Path(st.config).read_text(encoding="utf-8"))["agents"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return Result("FAIL", "config", None, f"{st.config} does not parse with an agents object: {exc}")
    if not isinstance(agents, dict) or not all(isinstance(v, dict) for v in agents.values()):
        return Result("FAIL", "config", None, f"{st.config}: agents is not an object of objects")
    st.agents, st.roles = agents, st.roles or list(agents)
    problems = [f"{role} is not an agent of {st.config}" for role in st.roles if role not in agents]
    problems = problems or load_settings(st)
    return verdict("config", None, problems, f"{st.config}: {len(agents)} agents; checked {', '.join(st.roles)}")


def check_model(st: State) -> Result:
    run = Path(st.run)
    files = [Path(st.config), *sorted(run.glob("_control/_agents*.json")), *sorted(run.glob("_*.md"))]
    read = [p for p in dict.fromkeys([*files, run / "lessons.md"]) if p.is_file()]
    hits = []
    for path in read:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        hits += [f"{os.path.relpath(path, st.run)}:{n}" for n, line in enumerate(lines, 1) if MODEL.search(line)]
    problems = [f"a model is named at {', '.join(hits)}"] if hits else []
    return verdict("model", None, problems, f"no model named in {len(read)} files")


def check_blind(st: State, role: str) -> Result:
    s = st.settings[role]
    deny = s.get("permissions", {}).get("deny", [])
    want = [x.replace("<run-dir>", st.run).replace("<checkout>", st.checkout) for x in TEN]
    missing = [r for r in want if r not in deny]
    if s.get("includeCoAuthoredBy") is not False:  # a commit trailer names the model; only the boolean false blanks it
        missing.append("includeCoAuthoredBy false")
    single = [r for r in deny if SINGLE_SLASH.match(r)]
    if role not in st.args.unsandboxed:
        box = s.get("sandbox", {})
        missing += [f"sandbox.{k} {str(v).lower()}" for k, v in SANDBOX_FLAGS if box.get(k) is not v]
        have = {str(d).rstrip("/") for d in box.get("filesystem", {}).get("denyRead", [])}
        need = (
            "~/.claude/projects",
            f"{st.run}/_control",
            f"{st.checkout}/docs/handoff",
            "~/.claude/.credentials.json",
        )
        missing += [f"sandbox.filesystem.denyRead {d}" for d in need if d not in have]
    problems = [f"missing {', '.join(missing)}"] if missing else []
    problems += [f"single-slash {', '.join(single)}: write //<path> for the root, <path> for the cwd"] if single else []
    if "attribution" in s:  # V1: a valid object (a `commit` or a `pr`) wins over includeCoAuthoredBy, whatever it holds
        problems.append("attribution is set: it can bring the model's trailer back; remove the key")
    return verdict("blind", role, problems, "the ten deny rules are set")


def check_cache(st: State, role: str) -> Result:
    """The cache and context rules of 2026-11-01 (owner): the config compacts at `--autocompact 235000` with `cap` and
    `handoff_at` above that point, keeps the per-machine sections (git status, cwd, date) out of the system prompt and
    snapshots it; the lane has its own frozen pack in the run folder that holds its mark; its settings keep the 5-minute
    TTL, clear the 60% override and set the lane's one model."""
    try:
        config = json.loads(Path(st.config).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        config = {}
    common = config.get("common", []) if isinstance(config, dict) else []
    common = common if isinstance(common, list) else []
    agent, env = st.agents[role], st.settings[role].get("env", {})
    problems = []

    def after(flag: str) -> str | None:
        return common[common.index(flag) + 1] if flag in common and common.index(flag) + 1 < len(common) else None

    if after("--autocompact") != "235000":
        problems.append("common has no --autocompact 235000")
    if "--exclude-dynamic-system-prompt-sections" not in common:  # git status, cwd and date would change the prefix
        problems.append("common has no --exclude-dynamic-system-prompt-sections")
    if after("--system-prompt-snapshot") != "on":
        problems.append("common has no --system-prompt-snapshot on")
    cap, handoff_at = config.get("cap", 260000), config.get("handoff_at", 250000)
    if not (isinstance(cap, int) and isinstance(handoff_at, int) and 197_000 < handoff_at < cap):
        problems.append(f"handoff_at {handoff_at} and cap {cap} must lie above the compaction point (about 197k)")
    extra = agent.get("extra_prompt")
    pack = extra.get("file") if isinstance(extra, dict) else None
    path = Path(st.run, pack).resolve() if isinstance(pack, str) else None
    if not pack:
        problems.append("no extra_prompt of its own (the lane's pack)")
    elif not path.is_relative_to(Path(st.run).resolve()) or not path.is_file():
        problems.append(f"its pack {pack} is not a file of the run folder")
    elif str(extra.get("mark", "")) not in path.read_text(encoding="utf-8", errors="replace") or not extra.get("mark"):
        problems.append(f"its pack {pack} does not hold its mark")
    if env.get("CLAUDE_CODE_PROMPT_CACHE_TTL") != "5m":
        problems.append("env CLAUDE_CODE_PROMPT_CACHE_TTL is not 5m")
    if env.get("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE") != "":
        problems.append("env CLAUDE_AUTOCOMPACT_PCT_OVERRIDE is not empty")
    if not st.settings[role].get("model"):
        problems.append("no model in its settings (one model per lane)")
    problems += class_problems(role, str(st.settings[role].get("model", "")))
    problems += warm_hook_problems(st.settings[role].get("hooks"), str(agent.get("status", "")))
    return verdict("cache", role, problems, f"compaction, its pack {pack}, 5m TTL, one model, the warm-cache hooks")


CLASSES = (  # a role name's start and its class (vault models-per-role; the builder mid-size, owner 2026-11-01)
    ("spec-writer", "top", MODELS[0]),
    ("builder", "mid-size", MODELS[2]),
    ("plan-fixer", "large", MODELS[1]),
    ("planner", "large", MODELS[1]),
    ("critic", "large", MODELS[1]),
    ("verifier", "large", MODELS[1]),
    ("judge", "large", MODELS[1]),
)


def class_problems(agent: str, model: str) -> list[str]:
    """The role's settings name the model of its class (a run of 2026-11-01 launched roles on a class its notes misread
    and nothing caught it); a role of no listed kind is not checked."""
    role = agent.rsplit("/", 1)[-1]
    found = next(((cls, name) for start, cls, name in CLASSES if role.startswith(start)), None)
    if found is None or not model or found[1] in model.lower():
        return []
    return [f"its model is not of the {found[0]} class its role needs (models-per-role)"]


def warm_hook_problems(hooks: object, record: str) -> list[str]:
    """The settings register keep-cache-warm.py: `pretool` on Bash, `stop` on the agent's record (owner, 2026-11-01:
    the cache is kept warm by rule, not by the role)."""
    hooks = hooks if isinstance(hooks, dict) else {}

    def commands(event: str, matcher: str | None = None) -> list[str]:
        entries = hooks.get(event) if isinstance(hooks.get(event), list) else []
        return [
            str(h.get("command", ""))
            for e in entries
            if isinstance(e, dict) and (matcher is None or matcher in str(e.get("matcher", "")).split("|"))
            for h in (e.get("hooks") if isinstance(e.get("hooks"), list) else [])
            if isinstance(h, dict)
        ]

    problems = []
    if not any("keep-cache-warm.py" in c and "pretool" in c for c in commands("PreToolUse", "Bash")):
        problems.append("no keep-cache-warm.py pretool hook on Bash (a foreground call past 210 s)")
    if not any("keep-cache-warm.py" in c and " stop " in c and record in c for c in commands("Stop")):
        problems.append(f"no keep-cache-warm.py stop hook on its record {record or '(any)'}")
    return problems


def check_ancestor(st: State, role: str) -> Result:
    if role in st.args.unsandboxed:
        return Result("SKIP", "ancestor", role, "an unsandboxed role")
    s, cwd = st.settings[role], str(st.agents[role].get("cwd", ""))
    fs = s.get("sandbox", {}).get("filesystem", {})
    rules = [r for r in s.get("permissions", {}).get("deny", []) if re.fullmatch(r"(?:Edit|Write)\(.+\)", r)]
    denied = [(r, rule_path(r, cwd)) for r in rules]
    denied += [(f"denyWrite {d}", fs_path(d, cwd)) for d in fs.get("denyWrite", [])]
    writes = [fs_path(w, cwd) for w in fs.get("allowWrite", [])]
    bad = [f"{r} covers allowWrite {w}" for r, d in denied for w in writes if w == d or w.startswith(d + "/")]
    return verdict("ancestor", role, bad, f"no deny rule covers an allowWrite path ({len(denied)} rules)")


def probe_text(marks: list[str], config: str) -> str:
    touches = [f"touch {shlex.quote(m)} 2>/dev/null" for m in marks]
    read = f"if cat {shlex.quote(config)} >/dev/null 2>&1; then r=OK; else r=REFUSED; fi; echo PREFLIGHT-READ-$r"
    return "; ".join([*touches, read])


def check_probe(st: State, role: str) -> Result:
    a = st.args
    if role in a.unsandboxed or a.no_sim:
        return Result("SKIP", "probe", role, "an unsandboxed role" if role in a.unsandboxed else "the probe is off")
    if a.sim is None and shutil.which("bwrap") is None:
        return Result("FAIL", "probe", role, "bwrap not on PATH")
    cwd, fs = str(st.agents[role].get("cwd", "")), st.settings[role].get("sandbox", {}).get("filesystem", {})
    dirs = [d for d in dict.fromkeys(fs_path(w, cwd) for w in fs.get("allowWrite", [])) if os.path.isdir(d)]
    sim, mark = a.sim or str(SKILL / "example" / "sim_bwrap.py"), ".preflight-" + secrets.token_hex(4)
    marks = [os.path.join(d, mark) for d in [*dirs, st.control]]
    try:
        code, out, err = script(sim, st.config, role, probe_text(marks, st.config))
        refused = [d for d in dirs if not os.path.exists(os.path.join(d, mark))]
        problems = [f"write refused in {', '.join(refused)}"] if refused else []
        if os.path.exists(os.path.join(st.control, mark)):
            problems.append(f"write into {st.control}/ allowed")
        if "PREFLIGHT-READ-OK" in out + err:
            problems.append(f"read of {st.config} allowed")
        elif "PREFLIGHT-READ-REFUSED" not in out + err:
            problems.append(f"the probe printed no result (exit {code}: {last_line(out, err)})")
    finally:
        for m in marks:
            with contextlib.suppress(OSError):
                os.unlink(m)
    return verdict("probe", role, problems, f"writes land in {len(dirs)} folders; {st.control}/ stays shut")


def check_worktree(st: State, role: str) -> Result:
    cwd = str(st.agents[role].get("cwd", ""))
    if not os.path.isdir(cwd):
        return Result("FAIL", "worktree", role, f"{cwd or 'the cwd'} is not a directory")
    missing = [] if os.path.exists(os.path.join(cwd, ".git")) else [".git"]
    venv = os.path.isfile(os.path.join(cwd, "pyproject.toml"))
    if venv and not os.path.isdir(os.path.join(cwd, ".venv")):
        missing.append(".venv/ (uv sync once per worktree)")
    problems = [f"{cwd} has no {' and no '.join(missing)}"] if missing else []
    return verdict("worktree", role, problems, f"{cwd} has .git" + (" and .venv/" if venv else ""))


def check_waiters(st: State) -> Result:
    bad, count = [], 0
    for brief in sorted(Path(st.run).glob("_*.md")):
        for token in dict.fromkeys(WAITER.findall(brief.read_text(encoding="utf-8", errors="replace"))):
            count += 1
            path = os.path.normpath(token if os.path.isabs(token) else os.path.join(st.run, os.path.basename(token)))
            if "<" in token or ">" in token or os.path.dirname(path) != st.run or not os.path.isfile(path):
                bad.append(f"{brief.name}: {token}")
    return verdict("waiters", None, bad, f"{count} waiters named in the briefs are files in the run folder")


def check_briefs(st: State) -> Result:
    """Every run brief's domain section holds its Spec ranges pasted, not the launch slot (owner, 2026-11-01)."""
    catalogue = str(SKILL / "scripts" / "manager" / "catalogue.py")
    return script_result("briefs", catalogue, "briefs", st.run, "--checkout", st.checkout)


def check_formats(st: State) -> Result:
    return script_result("formats", st.args.formats or str(SKILL / "scripts" / "check_formats.py"), st.run)


def check_monitor(st: State) -> Result:
    if st.args.no_monitor:
        return Result("SKIP", "monitor", None, "the monitor check is off")
    return script_result("monitor", st.args.monitor or str(SKILL / "scripts" / "monitor_records.py"), "status", st.run)


def check_disk(st: State) -> Result:
    paths = [st.run, tempfile.gettempdir(), *(str(st.agents[r].get("cwd", "")) for r in st.roles)]
    free = {p: shutil.disk_usage(p).free // 2**20 for p in dict.fromkeys(paths) if os.path.isdir(p)}
    low = [f"{p} has {mb} MB" for p, mb in free.items() if mb < st.args.min_free_mb]
    problems = [f"under {st.args.min_free_mb} MB free: {', '.join(low)}"] if low else []
    return verdict("disk", None, problems, f"at least {st.args.min_free_mb} MB free in {len(free)} folders")


def rise_rate(readings: list, name: str, used: float, resets: datetime) -> float:
    """Percent per hour from the latest earlier reading of the same limit and reset to the newest; 0 when not rising."""
    taken = readings[-1][0]
    for when, limits in reversed(readings[:-1]):
        same = [x for x in limits if x["name"] == name and parse_time(x["resets_at"]) == resets]
        if same and when < taken:
            rise = used - float(same[0]["used_pct"])
            return rise / ((taken - when).total_seconds() / 3600) if rise > 0 else 0.0
    return 0.0


def usage_problems(st: State, readings: list) -> list[str]:
    a, (taken, limits) = st.args, readings[-1]
    age = (st.now - taken).total_seconds() / 60
    problems = [f"the newest reading ({taken:{MINUTE}}) is {age:g} min old"] if age > a.usage_age else []
    for lim in limits:
        name, used, resets = lim["name"], float(lim["used_pct"]), parse_time(lim["resets_at"])
        if used >= a.max_pct:
            problems.append(f"{name} at {used:g}% (at most {a.max_pct:g}%)")
        rate = a.scale * rise_rate(readings, name, used, resets)
        end = min(resets, st.now + timedelta(hours=a.hours))
        full = taken + timedelta(hours=(100 - used) / rate) if rate > 0 else None
        if full is not None and full < end:
            problems.append(f"{name} reaches 100% at {full:{MINUTE}}, before {end:{MINUTE}}")
    return problems


def check_usage(st: State) -> Result:
    path = os.path.join(st.control, "usage.json")
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        readings = sorted(((parse_time(r["taken_at"]), r["limits"]) for r in data["readings"]), key=lambda r: r[0])
        problems = usage_problems(st, readings)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        return Result("FAIL", "usage", None, f"{path} is missing or does not parse: {exc}")
    taken, limits = readings[-1]
    seen = ", ".join(f"{x['name']} {float(x['used_pct']):g}% (resets {x['resets_at']})" for x in limits)
    return verdict("usage", None, problems, f"read at {taken:{MINUTE}}: {seen}")


def launch_path(st: State) -> str:
    return os.path.abspath(st.args.launch or os.path.join(st.run, "_launch.md"))


def listing() -> tuple[list[dict] | None, str]:
    """The rows of `claude agents --json --all`, or None and why not."""
    cmd = " ".join(SESSIONS)
    try:
        p = subprocess.run(SESSIONS, capture_output=True, text=True, timeout=LISTING_TIMEOUT, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"{cmd} did not run: {exc}"
    try:
        rows = json.loads(p.stdout) if p.returncode == 0 else None
    except ValueError:
        rows = None
    if not isinstance(rows, list):
        return None, f"{cmd} exit {p.returncode}, no JSON list: {last_line(p.stdout, p.stderr)}"
    return [r for r in rows if isinstance(r, dict)], ""


def checkout_dirs(st: State) -> list[str]:
    """The checkout and its worktrees, as `git worktree add` records them in `<checkout>/.git/worktrees/*/gitdir`."""
    dirs = [st.checkout]
    for gitdir in sorted(Path(st.checkout, ".git", "worktrees").glob("*/gitdir")):
        with contextlib.suppress(OSError):
            dirs.append(os.path.dirname(gitdir.read_text(encoding="utf-8").strip()))
    return [os.path.realpath(d) for d in dirs]


def in_checkout(cwd: object, dirs: list[str]) -> bool:
    """Whether a session's cwd is one of the folders or below one; a row with no cwd cannot be placed elsewhere."""
    if not isinstance(cwd, str) or not cwd:
        return True
    real = os.path.realpath(cwd)
    return any(real == d or inside(real, d) for d in dirs)


def check_live(st: State) -> Result:
    """Manager-lessons 14: no busy session outside the run works in the checkout or its worktrees unseen. It fails
    on one that is neither an agent of the run's configs, nor under their `<project>/` prefix, nor named in a `Live:`
    line of the launch file (which the manager writes after reading the list this check prints)."""
    rows, why = listing()
    if rows is None:
        return Result("FAIL", "live", None, why)
    names = set(all_agents(st))
    prefixes = tuple(n.split("/")[0] + "/" for n in names if "/" in n)
    live = sorted((r for r in rows if r.get("pid")), key=lambda r: str(r.get("name")))
    path = launch_path(st)
    text = Path(path).read_text(encoding="utf-8", errors="replace") if os.path.isfile(path) else ""
    known = names | {n.strip() for m in LIVE.finditer(text) for n in m.group(1).split(",")}
    dirs = checkout_dirs(st)
    stray = [
        f"{r.get('name')} ({r.get('cwd') or 'no cwd'})"
        for r in live
        if r.get("status") == "busy"
        and str(r.get("name")) not in known
        and not str(r.get("name")).startswith(prefixes)
        and in_checkout(r.get("cwd"), dirs)
    ]
    seen = ", ".join(f"{r.get('name')} {r.get('status')}" for r in live) or "none"
    listed = f"{len(live)} live session{'' if len(live) == 1 else 's'} ({seen})"
    where = "in the checkout or its worktrees"
    problems = [f"busy outside the run {where}, named in no Live: line: {', '.join(stray)}; {listed}"] if stray else []
    return verdict("live", None, problems, f"{listed}; none outside the run is busy {where}")


def key_problems(text: str) -> list[str]:
    values = {k: m.group(1).strip() for k in KEYS if (m := re.search(rf"(?m)^{re.escape(k)}(.*)$", text))}
    problems = [f"no {k} line" for k in KEYS if not values.get(k)]
    if values.get("Size:") and not re.search(r"\d", values["Size:"]):
        problems.append("Size: names no number")
    if values.get("Estimate:"):
        problems += [f"Estimate: names no {what}" for what, p in ESTIMATE if not re.search(p, values["Estimate:"])]
    return problems


def cells_of(line: str) -> list[str]:
    return [c.strip(" `") for c in line.strip().strip("|").split("|")]


def launch_table(text: str) -> tuple[list[str] | None, list[list[str]]]:
    """The header cells and the rows of the first table whose header names role, lane and settings."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("|") and {"role", "lane", "settings"} <= set(cells_of(line)):
            rows = itertools.takewhile(lambda r: r.lstrip().startswith("|"), lines[i + 2 :])
            return cells_of(line), [cells_of(r) for r in rows]
    return None, []


def all_agents(st: State) -> dict[str, str]:
    """Every agent of `<run>/_control/_agents*.json` with its settings path."""
    agents = {}
    for path in sorted(Path(st.control).glob("_agents*.json")):
        with contextlib.suppress(OSError, ValueError, KeyError, TypeError, AttributeError):
            found = json.loads(path.read_text(encoding="utf-8"))["agents"]
            agents |= {name: str(agent.get("settings", "")) for name, agent in found.items()}
    return agents


def table_problems(st: State, text: str) -> list[str]:
    header, rows = launch_table(text)
    if header is None:
        return ["no table with the cells role, lane and settings"]
    problems = [f"the table has no {c} cell" for c in CELLS if c not in header]
    agents = all_agents(st)
    named = {r.get("role", ""): r.get("settings", "") for r in (dict(zip(header, row, strict=False)) for row in rows)}
    problems += [f"no row for {name}" for name in agents if name not in named]
    for role, settings in named.items():
        if role not in agents:
            problems.append(f"{role} is not an agent of _control/_agents*.json")
        elif settings != agents[role]:
            problems.append(f"{role}: settings {settings} is not {agents[role]}")
    return problems + pair_problems(list(named))


def role_kind(role: str) -> str:
    """`<project>/builder-a` -> `builder`; `<project>/plan-fixer` -> `plan`."""
    return role.rsplit("/", 1)[-1].split("-")[0]


def pair_problems(roles: list[str]) -> list[str]:
    kinds = {role_kind(r) for r in roles}
    return [f"a {a} with no {b}: {why}" for a, b, why in PAIRS if a in kinds and b not in kinds]


def yes_problems(st: State, text: str) -> list[str]:
    stamped, problems = [], []
    for m in YES.finditer(text):
        try:
            stamped.append((parse_time(m.group(1)), m.group(0), m.group(2)))
        except ValueError:  # the pattern takes 2026-10-32T10:00Z; the calendar does not
            problems.append(f"a Yes: line has an impossible time: {m.group(0)}")
    problems += [f"a Yes: line is stamped after now: {line}" for when, line, _ in stamped if when > st.now]
    said = [rest for when, _, rest in stamped if when <= st.now]
    missing = [r for r in st.roles if not any(re.search(rf"(?<![\w-]){re.escape(r)}(?![\w-])", s) for s in said)]
    return problems + ([f"no Yes: line names {', '.join(missing)}"] if missing else [])


def check_launch(st: State) -> Result:
    path = launch_path(st)
    if not os.path.isfile(path):
        return Result("FAIL", "launch", None, f"{path}: no such file")
    text = Path(path).read_text(encoding="utf-8")
    problems = key_problems(text) + table_problems(st, text) + (yes_problems(st, text) if st.args.yes else [])
    passed = f"{path}: the key lines and one row per agent" + (", each with a yes" if st.args.yes else "")
    return verdict("launch", None, problems, passed)


def emit(r: Result) -> Result:
    r.detail = r.detail.replace("\n", " ")
    print(f"{r.status} {r.check}{' ' + r.agent if r.agent else ''}: {r.detail}", flush=True)
    return r


def save(st: State, results: list[Result]) -> int:
    count = {s: sum(r.status == s for r in results) for s in ("PASS", "FAIL", "SKIP")}
    path = os.path.join(st.control, "preflight.json")
    os.makedirs(st.control, exist_ok=True)
    doc = {
        "written_at": st.now.strftime(MINUTE),
        "run_dir": st.run,
        "roles": st.roles,
        "results": [{"check": r.check, "agent": r.agent, "status": r.status, "detail": r.detail} for r in results],
        "passed": count["FAIL"] == 0,
    }
    Path(path).write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(f"preflight: {count['PASS']} passed, {count['FAIL']} failed, {count['SKIP']} skipped — {path}")
    return 1 if count["FAIL"] else 0


def run_check(a: argparse.Namespace) -> int:
    run = os.path.abspath(a.run_dir)
    st = State(a, run, os.path.abspath(a.checkout), os.path.join(run, "_control"), a.now or datetime.now(UTC))
    results = [emit(check_config(st))]
    if results[0].status != "FAIL":
        results.append(emit(check_model(st)))
        for role in st.roles:
            results += [
                emit(f(st, role)) for f in (check_blind, check_cache, check_ancestor, check_probe, check_worktree)
            ]
        run_wide = (
            check_waiters,
            check_briefs,
            check_formats,
            check_monitor,
            check_disk,
            check_usage,
            check_live,
            check_launch,
        )
        results += [emit(f(st)) for f in run_wide]
    return save(st, results)


def number(text: str, key: str) -> float | None:
    m = re.search(rf"(?m)^{key}:[ \t]*([0-9]+(?:\.[0-9]+)?)", text)
    return float(m.group(1)) if m else None


def num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


def eval_cases(dirs: list[str]) -> list[Path]:
    """A DIR holding task.yaml is one case, else each DIR/*/task.yaml in order."""
    found = []
    for d in map(Path, dirs):
        found += [d] if (d / "task.yaml").is_file() else sorted(p.parent for p in d.glob("*/task.yaml"))
    return found


def run_timeout(a: argparse.Namespace) -> int:
    total, counted, skipped, failed = 0.0, 0, 0, False
    for case in eval_cases(a.dirs):
        text, name = (case / "task.yaml").read_text(encoding="utf-8"), f"{case.parent.name}/{case.name}"
        if re.search(r"(?m)^session:[ \t]*false", text):
            skipped += 1
            continue
        minutes = number(text, "timeout_minutes")
        if minutes is None:
            print(f"FAIL {name}: a session case without timeout_minutes")
            failed = True
            continue
        trials, sessions = (1.0 if n is None else n for n in (number(text, "trials"), number(text, "sessions")))
        product = trials * sessions * minutes
        print(f"{name}: {num(trials)} x {num(sessions)} x {num(minutes)} min = {num(product)} min")
        total, counted = total + product, counted + 1
    print(f"total: {num(total)} min over {counted} session cases ({skipped} code-only skipped)")
    if a.check is not None:
        word = "FAIL" if a.check < total else "PASS"
        print(f"{word} timeout: the session cases can take {num(total)} min; the run allows {num(a.check)}")
        failed = failed or a.check < total
    return 1 if failed else 0


def tool_uses(path: str) -> list[tuple[int, str, dict]]:
    """(line, timestamp, tool_use) of every tool call in the assistant lines of a JSONL transcript."""
    found = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict) or entry.get("type") != "assistant":
            continue
        content = (entry.get("message") or {}).get("content")
        if isinstance(content, list):
            stamp = str(entry.get("timestamp", ""))
            found += [(n, stamp, c) for c in content if isinstance(c, dict) and c.get("type") == "tool_use"]
    return found


def sleep_loop(command: str) -> bool:
    """A `sleep` between a `do` and its `done` (nesting counted; a `done` before any `do` ignored), or Python's
    `while` with `time.sleep(`."""
    if re.search(r"\bwhile\b", command) and re.search(r"\btime\.sleep\(", command):
        return True
    depth = 0
    for m in LOOP_WORD.finditer(command):
        if m.group(1) == "do":
            depth += 1
        elif m.group(1) == "done":
            depth = max(depth - 1, 0)
        elif depth:
            return True
    return False


def run_polls(a: argparse.Namespace) -> int:
    commands = [
        (path, n, str((tool.get("input") or {}).get("command", "")))
        for path in a.transcripts
        for n, _, tool in tool_uses(path)
        if tool.get("name") == "Bash"
    ]
    hits = [(path, n, command) for path, n, command in commands if sleep_loop(command)]
    for path, n, command in hits:
        print(f"sleep loop: {path}:{n}: {command.replace(chr(10), ' ')[:80]}")
    print(f"polls: {len(commands)} Bash commands, {len(hits)} sleep loops")
    return 1 if hits else 0


def stamp_time(stamp: str, writer: datetime) -> datetime:
    """A stamp's time; one without a date takes the writer's day, the day before or after, whichever is nearest."""
    if re.match(r"\d{4}-", stamp):
        return parse_time(stamp.removesuffix(" UTC"))
    hour, minute, *second = (int(x) for x in stamp.removesuffix(" UTC").split(":"))
    days = (writer + timedelta(days=k) for k in (-1, 0, 1))
    times = (d.replace(hour=hour, minute=minute, second=second[0] if second else 0, microsecond=0) for d in days)
    return min(times, key=lambda t: abs(t - writer))


def writers(transcripts: list[str]) -> list[tuple[datetime, str]]:
    """(time, new text) of every Write, Edit and Bash call of the transcripts, earliest first."""
    found = [
        (parse_time(stamp), str((tool.get("input") or {}).get(WRITTEN[str(tool.get("name"))], "")))
        for path in transcripts
        for _, stamp, tool in tool_uses(path)
        if tool.get("name") in WRITTEN and stamp
    ]
    return sorted(found, key=lambda w: w[0])


def run_clock(a: argparse.Namespace) -> int:
    tools, problems, stamped, matched = writers(a.transcript), [], 0, 0
    for record in a.records:
        for n, line in enumerate(Path(record).read_text(encoding="utf-8").splitlines(), 1):
            stamps = STAMP.findall(line)
            problems += [f"{record}:{n}: not in date -u form: {t}" for t in LOOSE.findall(STAMP.sub(" ", line))]
            if not stamps:
                continue
            stamped += 1
            when = next((t for t, text in tools if line.strip() in text), None)
            if when is None:
                continue
            matched += 1
            try:
                gap = int(abs((when - stamp_time(stamps[0], when)).total_seconds()) // 60)
            except ValueError:
                problems.append(f"{record}:{n}: not in date -u form: {stamps[0]}")
                continue
            if gap > a.slack:
                problems.append(f"{record}:{n}: {stamps[0]} was written at {when:%Y-%m-%dT%H:%M:%SZ}, {gap} min apart")
    for problem in problems:
        print(problem)
    print(f"clock: {stamped} stamped lines, {matched} matched a writer, {len(problems)} problems")
    return 1 if problems else 0


def check_parser(sub: argparse._SubParsersAction) -> None:
    c = sub.add_parser("check", help="the pre-flight of a run folder", description="The pre-flight of a run folder.")
    c.add_argument("run_dir", metavar="run-dir")
    c.add_argument("--checkout", required=True, help="the project's main checkout")
    c.add_argument("--config", metavar="P", help="default <run-dir>/_control/_agents.json")
    c.add_argument("--launch", metavar="P", help="default <run-dir>/_launch.md")
    c.add_argument("--roles", metavar="A,B", help="default every agent of the config, in its order")
    c.add_argument("--unsandboxed", action="append", default=[], metavar="ROLE", help="no ancestor or probe check")
    sim = c.add_mutually_exclusive_group()
    sim.add_argument("--sim", metavar="P", help="default the skill's example/sim_bwrap.py, when bwrap is on PATH")
    sim.add_argument("--no-sim", action="store_true", help="skip the probe")
    c.add_argument("--formats", metavar="P", help="default the skill's scripts/check_formats.py")
    monitor = c.add_mutually_exclusive_group()
    monitor.add_argument("--monitor", metavar="P", help="default the skill's scripts/monitor_records.py")
    monitor.add_argument("--no-monitor", action="store_true", help="skip the monitor check")
    c.add_argument("--min-free-mb", type=int, default=512, metavar="N", help="default 512")
    c.add_argument("--usage-age", type=float, default=30, metavar="MIN", help="the newest reading's age; default 30")
    c.add_argument("--max-pct", type=float, default=80, metavar="PCT", help="the highest used_pct; default 80")
    c.add_argument("--scale", type=float, default=1.0, metavar="X", help="the run's rate against the measured one")
    c.add_argument("--hours", type=float, default=5.0, metavar="H", help="the run's expected length; default 5")
    c.add_argument("--yes", action="store_true", help="a Yes: line for every checked role")
    c.add_argument("--now", type=parse_time, metavar="ISO", help="default the current UTC time")


def parser() -> argparse.ArgumentParser:
    """The command line; every option is in scripts/manager/README.md (test_preflight.py checks it)."""
    ap = argparse.ArgumentParser(prog="preflight.py", description="The manager's checks before a launch.")
    sub = ap.add_subparsers(dest="command", required=True)
    check_parser(sub)
    t = sub.add_parser("timeout", help="what a suite of eval cases can take", description="Sum the session cases.")
    t.add_argument("dirs", nargs="+", metavar="dir")
    t.add_argument("--check", type=float, metavar="MIN", help="fail when MIN is below the total")
    p = sub.add_parser("polls", help="sleep loops in Bash commands", description="Find sleep loops.")
    p.add_argument("transcripts", nargs="+", metavar="transcript")
    k = sub.add_parser("clock", help="stamps not in date -u form or far from their writer", description="Check stamps.")
    k.add_argument("records", nargs="+", metavar="record")
    k.add_argument("--transcript", action="append", default=[], metavar="JSONL", help="a transcript to match")
    k.add_argument("--slack", type=float, default=10, metavar="MIN", help="whole minutes allowed; default 10")
    return ap


def main(argv: list[str] | None = None) -> int:
    a = parser().parse_args(argv)
    return {"check": run_check, "timeout": run_timeout, "polls": run_polls, "clock": run_clock}[a.command](a)


if __name__ == "__main__":
    sys.exit(main())
