#!/usr/bin/env python3
"""Format check of a pipeline's run folder: the lines the waiters and the watcher parse.

  python3 check_formats.py <run-dir> [--repo <checkout>] [--state <monitor.json>] [--json]

Errors (exit 1): a record file whose first line is not `STATUS: …`; a finding heading (`#### C<n>`, `A<n>`, `V<n>`,
`J<n>`, …) used twice, because a reused id already counts as answered (`#### V29, round 2` reuses V29); an answer
line (`<id>: …`) for an id that no file defines (a typo answers nothing); an id answered twice in critique-response.md
(the first answer stands); an answer in critique-response.md written as a list item (`- C5: …`), which the waiters do
not read (the build logs may use list items: a builder may write `- B1: …`, `- V12: fixed — …`); a `#### V<n>` section, a reused id's second one too, without its `(code)`, `(plan)`,
`(spec)` or `(brief)` cause (alone or an item of a list: `(minor, plan)`, `(major, code; fixed in <sha>)`; a
parenthesis of prose is no cause); a
`Task N: done — <sha>` line whose sha is not a commit of the checkout; a hand-over note whose line 1 is not
`HANDOFF <role> after Task <N> — <YYYY-MM-DD HH:MM>` with the note's own role, a task number and a real time.
The request lines of every record (a `*.md` without a leading `_` whose line 1 starts `STATUS:`): `SANDBOX:`,
`COPY-REQUEST:`, `CHECKOUT-REQUEST:` and `FF-REQUEST:`, each closed by the first answer of its kind below it
(`SUPPLIED:`, `COPIED:`, `CHECKED-OUT:`, `FF-DONE:` or `REFUSED: <KIND> — <why>`; the oldest open request first): an
answer with no open request of its kind above it, a `REFUSED:` that names no kind, and a request open past the bound
of `_common.md` (`Request-line bound: <m> minutes`, 15 when absent; the age from the monitor's first sight in
`--state`, else from the file's mtime, a lower bound) are errors. A `Merged: <marker> at <sha>` line of lessons.md
(code spans skipped) needs a hex sha that is an ancestor of HEAD in the merged-into builder's checkout (`x->y`:
builder-y's; `a+b+c+d`: any named builder's), or for another target (`main->plan`) a commit of `--repo` or of a builder
checkout; with `--repo`, a lane marker whose named checkouts are all gone needs a commit of `--repo`. A finding's
`Lesson: <file>:<line>` (the lesson it breaks; lessons.md and other relative paths from the run folder) names a line
that exists. A waiter (each
line of the run folder's `_*.py` and `*.sh`, each code span and fenced line of its `_*.md`)
may not count the marker with `grep -c`. A ticked duty of `_control/duties.md` carries its UTC time. The agents come
from the configs in `CONFIGS` order: `_control/_agents.json`, `_agents.json`, `_agents-active.json`.
The build logs are build-log.md, build-log-kb.md and every other `build-log*.md` of the run folder (one per
builder): each needs its STATUS line, defines its `B<n>:` ids, may answer in list items, and its done lines are
looked up in the checkout of the agent whose `status` it is. A builder's `B<n>: sent to planner` or
`B<n>: sent to plan-fixer` line waits for its answer in critique-response.md.
Information (exit 0): the open ids and the open requests per kind, the done tasks. Read-only; a run folder is never
written.
"""

import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys
import time

RECORDS = (
    "critique.md",
    "critique-response.md",
    "verify.md",
    "build-log.md",
    "judge.md",
    "verify-kb.md",
    "build-log-kb.md",
)
HEADING = re.compile(r"^#### ([A-Z]{1,2})(\d+)\b", re.MULTILINE)
ANSWER = re.compile(r"^([A-Z]{1,2})(\d+):", re.MULTILINE)
LIST_ANSWER = re.compile(r"^- ([A-Z]{1,2})(\d+):", re.MULTILINE)
LOG_LINE = re.compile(r"^(?:- )?([A-Z]{1,2})(\d+):", re.MULTILINE)
DONE = re.compile(r"^(?:- )?Task (\d+): done — ([0-9a-f]{7,40})\b", re.MULTILINE)
SENT = re.compile(r"^(?:- )?(B|BK)(\d+): sent to (?:planner|plan-fixer)", re.MULTILINE)
LESSON_ID = re.compile(r"\b([MO])(\d+)\b")
HANDOFF = re.compile(r"^HANDOFF (\S+) after Task \d+\b[^—]* — (\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*$")
CAUSE = re.compile(r"\((?:[^()]*[,;]\s*)?(code|plan|spec|brief)\s*(?:[,;][^()]*)?\)")
CONFIGS = ("_control/_agents.json", "_agents.json", "_agents-active.json")
REQUEST_KINDS = {
    "SANDBOX": "SUPPLIED",
    "COPY-REQUEST": "COPIED",
    "CHECKOUT-REQUEST": "CHECKED-OUT",
    "FF-REQUEST": "FF-DONE",
}
REQUEST = re.compile(r"^(?:- )?(SANDBOX|COPY-REQUEST|CHECKOUT-REQUEST|FF-REQUEST): (.*)$", re.MULTILINE)
REPLY = re.compile(r"^(?:- )?(SUPPLIED|COPIED|CHECKED-OUT|FF-DONE|REFUSED): (.*)$", re.MULTILINE)
BOUND = re.compile(r"^Request-line bound: (\d+) minutes?\b", re.MULTILINE)
DEFAULT_BOUND = 15
MERGED = re.compile(r"Merged: (\S+) at ([0-9a-f]{7,40})\b")
CODE_SPAN = re.compile(r"`[^`\n]*`")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
COUNT_FLAG = re.compile(r"(?<![\w-])-[A-Za-z]*c[A-Za-z]*\b|--count\b")
TICK_TIME = re.compile(r"^- \[x\] (?:\d{4}-\d{2}-\d{2} )?\d{2}:\d{2} UTC\b")


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def build_logs(run: pathlib.Path) -> list[str]:
    """build-log.md, build-log-kb.md, then the run folder's other `build-log*.md` names, sorted."""
    first = ["build-log.md", "build-log-kb.md"]
    return first + sorted(p.name for p in run.glob("build-log*.md") if p.name not in first)


def agents(run: pathlib.Path) -> dict[str, dict]:
    """The agents of every config in CONFIGS order; the first definition of a name wins."""
    found: dict[str, dict] = {}
    for cfg in CONFIGS:
        try:
            for agent_name, agent in json.loads(read(run / cfg) or "{}").get("agents", {}).items():
                if isinstance(agent, dict):
                    found.setdefault(agent_name, agent)
        except (ValueError, AttributeError, TypeError):
            pass
    return found


def log_checkouts(run: pathlib.Path) -> tuple[dict[str, str], str | None]:
    """Each build log's checkout, the `cwd` of the agent whose `status` it is (the configs in CONFIGS order), and the
    old rule's: the `cwd` of the last agent whose name ends in `/builder`."""
    by_log: dict[str, str] = {}
    builder = None
    for agent_name, agent in agents(run).items():
        if isinstance(agent.get("status"), str) and agent.get("cwd"):
            by_log.setdefault(agent["status"], agent["cwd"])
        if agent_name.endswith("/builder"):
            builder = agent.get("cwd")
    return by_log, builder


def records(run: pathlib.Path) -> list[pathlib.Path]:
    """The run folder's record files: each `*.md` without a leading `_` whose line 1 starts `STATUS:`, sorted."""
    return sorted(p for p in run.glob("*.md") if not p.name.startswith("_") and read(p).startswith("STATUS:"))


def epoch(iso: str) -> float:
    """`YYYY-MM-DDTHH:MM:SSZ` -> seconds since the epoch."""
    return datetime.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.UTC).timestamp()


def bound_minutes(run: pathlib.Path) -> int:
    """The request-line bound that `_common.md` names (`Request-line bound: <m> minutes`), else DEFAULT_BOUND."""
    m = BOUND.search(read(run / "_common.md"))
    return int(m.group(1)) if m else DEFAULT_BOUND


def git_ok(place: str, *args: str) -> bool:
    return subprocess.run(["git", "-C", place, *args], capture_output=True, check=False).returncode == 0


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def sections(text: str) -> list[tuple[str, int, str]]:
    """Each `#### <id>` heading's id, line and body up to the next `##`–`####` heading, a repeated id each time."""
    out: list[tuple[str, int, str]] = []
    for m in re.finditer(r"^#{2,4} .*?(?=^#{2,4} |\Z)", text, flags=re.MULTILINE | re.DOTALL):
        h = HEADING.match(m.group(0))
        if h:
            out.append((h.group(1) + h.group(2), line_of(text, m.start()), m.group(0)))
    return out


def ids(run: pathlib.Path) -> dict:
    """The finding ids of a run folder as the waiters read them: `defined` (id -> times, in reading order),
    `duplicates` (reused headings), `errors` (answer lines for no id, list items in the response file), `answered`
    (every id with an answer line) and `open` (kind -> ids waiting; a B or BK only when sent to the planner or the
    plan fixer and not answered in critique-response.md)."""
    # Defined ids: headings in the review files, B lines in the build logs, M/O in lessons, P in the response file.
    defined: dict[str, int] = {}
    duplicates: list[str] = []
    for name in ("critique.md", "verify.md", "judge.md", "verify-kb.md"):
        text = read(run / name)
        seen: set[str] = set()
        for m in HEADING.finditer(text):
            ident = m.group(1) + m.group(2)
            if ident in seen:
                duplicates.append(f"{name}:{line_of(text, m.start())}: #### {ident} twice")
            seen.add(ident)
            defined[ident] = defined.get(ident, 0) + 1
    # A builder's `B<n>:` line defines the id (its own finding, fixed by itself or sent to the planner or the
    # plan fixer); only the ones sent wait for an answer in critique-response.md.
    sent: set[str] = set()
    for name in build_logs(run):
        text = read(run / name)
        for m in LOG_LINE.finditer(text):
            if m.group(1) in ("B", "BK"):
                defined.setdefault(m.group(1) + m.group(2), 1)
        for m in SENT.finditer(text):
            sent.add(m.group(1) + m.group(2))
    lessons = read(run / "lessons.md")
    for m in LESSON_ID.finditer(lessons):
        defined.setdefault(m.group(1) + m.group(2), 1)
    for m in ANSWER.finditer(read(run / "critique-response.md")):
        if m.group(1) == "P":
            defined.setdefault("P" + m.group(2), 1)

    # Answer lines against the defined ids: at line start in the response file (the waiters read `^<id>:`), also
    # as list items in the build logs.
    errors: list[str] = []
    answered: set[str] = set()
    for name, pattern in (("critique-response.md", ANSWER), *((log, LOG_LINE) for log in build_logs(run))):
        for m in pattern.finditer(read(run / name)):
            ident = m.group(1) + m.group(2)
            answered.add(ident)
            if ident not in defined and m.group(1) not in ("P",):
                errors.append(f"{name}: `{ident}:` answers an id no file defines")
    response = read(run / "critique-response.md")
    for m in LIST_ANSWER.finditer(response):
        ident = m.group(1) + m.group(2)
        errors.append(
            f"critique-response.md:{line_of(response, m.start())}: `- {ident}:` is a list item; "
            f"the waiters read `{ident}:` at line start"
        )
    answered_by_planner = {m.group(1) + m.group(2) for m in ANSWER.finditer(response)}
    open_ids: dict[str, list[str]] = {}
    for ident in defined:
        kind = re.match(r"[A-Z]+", ident).group(0)
        if kind in ("B", "BK"):
            if ident in sent and ident not in answered_by_planner:
                open_ids.setdefault(kind, []).append(ident)
        elif ident not in answered:
            open_ids.setdefault(kind, []).append(ident)
    return {
        "defined": defined,
        "duplicates": duplicates,
        "errors": errors,
        "answered": answered,
        "open": {k: v for k, v in sorted(open_ids.items())},
    }


def status_errors(run: pathlib.Path) -> list[str]:
    """1. A record or build log whose line 1 is not `STATUS: …`."""
    return [
        f"{name}: line 1 is not `STATUS: …`"
        for name in dict.fromkeys([*RECORDS, *build_logs(run)])
        if (run / name).exists() and not read(run / name).startswith("STATUS: ")
    ]


def cause_errors(run: pathlib.Path) -> list[str]:
    """4. A verifier section without its (code), (plan), (spec) or (brief) cause."""
    return [
        f"{name}:{line}: #### {ident} has no (code), (plan), (spec) or (brief) cause"
        for name in ("verify.md", "verify-kb.md")
        for ident, line, body in sections(read(run / name))
        if ident.startswith("V") and not CAUSE.search(body)
    ]


LESSON = re.compile(r"^Lesson:\s*`?([^`\s]+):(\d+)", re.MULTILINE)


def lesson_errors(run: pathlib.Path) -> list[str]:
    """4b. A finding's `Lesson: <file>:<line>` that names no line of an existing file (owner, 2026-11-02: each finding
    names the lesson it breaks, so the lesson's recurrences are counted, lessons_report.py)."""
    out = []
    for name in ("critique.md", "verify.md", "verify-kb.md", "judge.md"):
        for ident, line, body in sections(read(run / name)):
            for path, n in LESSON.findall(body):
                file = pathlib.Path(path).expanduser()
                file = file if file.is_absolute() else run / file
                count = len(read(file).splitlines()) if file.is_file() else 0
                if not 1 <= int(n) <= count:
                    out.append(f"{name}:{line}: #### {ident} names Lesson {path}:{n}, which is no line of a file")
    return out


def done_lines(run: pathlib.Path, repo: str | None) -> tuple[list[str], list[str]]:
    """5. The done tasks as `<N>:<sha7>`, and an error for each done line whose sha its log's checkout lacks."""
    by_log, builder = log_checkouts(run)
    done: list[str] = []
    errors: list[str] = []
    for name in build_logs(run):
        place = repo or by_log.get(name) or builder
        for m in DONE.finditer(read(run / name)):
            done.append(f"{m.group(1)}:{m.group(2)[:7]}")
            if place and not git_ok(place, "cat-file", "-e", m.group(2) + "^{commit}"):
                errors.append(f"{name}: Task {m.group(1)}: done — {m.group(2)} is not a commit of {place}")
    return done, errors


def twice_errors(run: pathlib.Path) -> list[str]:
    """An id answered on two lines of critique-response.md: the first answer stands (findings_report.py reads it)."""
    errors: list[str] = []
    text, answered = read(run / "critique-response.md"), set()
    for m in ANSWER.finditer(text):
        ident = m.group(1) + m.group(2)
        if m.group(1) == "P":  # as ids() leaves P lines out
            continue
        if ident in answered:
            errors.append(f"critique-response.md:{line_of(text, m.start())}: {ident} answered twice")
        answered.add(ident)
    return errors


def handoff_errors(run: pathlib.Path) -> list[str]:
    """6. A hand-over note whose line 1 is not `HANDOFF <its role> after Task <N> — <YYYY-MM-DD HH:MM>`."""
    errors: list[str] = []
    for path in sorted(run.glob("handoff-*.md")):
        first = read(path).splitlines()[0] if read(path) else ""
        m = HANDOFF.match(first)
        role = path.stem[len("handoff-") :]
        if not m:
            errors.append(f"{path.name}: line 1 `{first[:60]}` is not `HANDOFF <role> after Task <N> — <date time>`")
        elif m.group(1) != role:
            errors.append(f"{path.name}: line 1 is `HANDOFF {m.group(1)} …`; the note is {role}'s")
        else:
            try:
                datetime.datetime.strptime(m.group(2), "%Y-%m-%d %H:%M")  # noqa: DTZ007 - checks the form only
            except ValueError:
                errors.append(f"{path.name}: line 1's `{m.group(2)}` is not a date and time")
    return errors


def request_pairs(name: str, text: str) -> tuple[list[dict], list[str]]:
    """The requests of one record in file order, each closed by the first answer of its kind below it (the oldest
    open request first; a `REFUSED:` names its kind as the first word), and the answers that close nothing."""
    found: list[dict] = []
    errors: list[str] = []
    kinds = {answer: kind for kind, answer in REQUEST_KINDS.items()}
    for number, line in enumerate(text.splitlines(), 1):
        if m := REQUEST.match(line):
            k = 1 + sum(r["kind"] == m.group(1) for r in found)
            found.append(
                {"id": f"{name}:{m.group(1)}:{k}", "kind": m.group(1), "line": number, "text": m.group(2)}
                | {"answer_line": None, "answer": None}
            )
        elif m := REPLY.match(line):
            kind = kinds.get(m.group(1)) or (m.group(2).split() or [""])[0].rstrip(":,;.")
            if kind not in REQUEST_KINDS:
                errors.append(f"{name}:{number}: REFUSED: names no request kind")
                continue
            request = next((r for r in found if r["kind"] == kind and r["answer"] is None), None)
            if request is None:
                errors.append(f"{name}:{number}: {m.group(1)}: answers no open {kind} line above it")
            else:
                request["answer_line"], request["answer"] = number, m.group(2)
    return found, errors


def seen_times(state: pathlib.Path) -> dict[str, float]:
    """The monitor's first sight of each request id, from its state file; a missing or broken entry gives none."""
    try:
        entries = json.loads(read(state) or "{}").get("requests", [])
    except (ValueError, AttributeError):
        return {}
    seen: dict[str, float] = {}
    for entry in entries if isinstance(entries, list) else []:
        try:
            seen[entry["id"]] = epoch(entry["seen"])
        except (KeyError, TypeError, ValueError):
            pass
    return seen


def request_errors(run: pathlib.Path, state: pathlib.Path, now: float) -> tuple[dict[str, list[str]], list[str]]:
    """The open requests by kind as `<file>:<line>`, and the request errors: answers that close nothing, then the
    requests open past the bound (the age from the monitor's first sight, else from the file's mtime)."""
    seen, bound = seen_times(state), bound_minutes(run)
    open_requests: dict[str, list[str]] = {}
    errors: list[str] = []
    for path in records(run):
        found, pair_errors = request_pairs(path.name, read(path))
        errors += pair_errors
        for request in (r for r in found if r["answer"] is None):
            open_requests.setdefault(request["kind"], []).append(f"{path.name}:{request['line']}")
            age = now - seen.get(request["id"], path.stat().st_mtime)
            if age > bound * 60:
                errors.append(
                    f"{path.name}:{request['line']}: {request['kind']} open {int(age // 60)} min, "
                    f"past the bound of {bound} min"
                )
    return open_requests, errors


def builder_cwd(config: dict[str, dict], lane: str) -> str | None:
    """The cwd of the config agent whose name ends `builder-<lane>`."""
    return next((a["cwd"] for n, a in config.items() if n.endswith(f"builder-{lane}") and a.get("cwd")), None)


def merged_error(marker: str, sha: str, config: dict[str, dict], repo: str | None) -> str | None:
    """Why `Merged: <marker> at <sha>` fails, or None: `x->y` (or `x→y`) needs the sha in builder-y's HEAD, a `+`
    marker in any named builder's HEAD; any other target, or a lane marker whose checkouts are all gone while `--repo`
    is given (an apply removed them), needs a commit of `--repo`, else of a builder checkout."""
    arrow = marker.replace("→", "->")
    if "+" in marker:
        places = [cwd for lane in marker.split("+") if (cwd := builder_cwd(config, lane))]
    else:
        places = [cwd] if "->" in arrow and (cwd := builder_cwd(config, arrow.rpartition("->")[2])) else []
    if places and repo and not any(pathlib.Path(p).is_dir() for p in places):
        places = []
    if places:
        if any(git_ok(place, "merge-base", "--is-ancestor", sha, "HEAD") for place in places):
            return None
        return "is not an ancestor of HEAD in " + " or ".join(places)
    builders = {a["cwd"] for n, a in config.items() if n.rpartition("/")[2].startswith("builder") and a.get("cwd")}
    places = [repo] if repo else sorted(builders)
    if not places or any(git_ok(place, "cat-file", "-e", sha + "^{commit}") for place in places):
        return None
    return "is not a commit of " + " or ".join(places)


def merged_errors(run: pathlib.Path, repo: str | None) -> list[str]:
    """Each `Merged:` line of lessons.md (code spans removed) needs a hex sha that its place holds."""
    config = agents(run)
    errors: list[str] = []
    for number, line in enumerate(CODE_SPAN.sub("", read(run / "lessons.md")).splitlines(), 1):
        if "Merged:" not in line:
            continue
        found = list(MERGED.finditer(line))
        if not found:
            errors.append(f"lessons.md:{number}: a Merged: line without a hex sha")
        for m in found:
            if why := merged_error(m.group(1), m.group(2), config, repo):
                errors.append(f"lessons.md:{number}: Merged: {m.group(1)} at {m.group(2)} {why}")
    return errors


def waiter_pieces(path: pathlib.Path) -> list[tuple[int, str]]:
    """Where a waiter's command can be: each line of a script; each code span and fenced line of a Markdown file."""
    lines = read(path).splitlines()
    if path.suffix != ".md":
        return list(enumerate(lines, 1))
    pieces: list[tuple[int, str]] = []
    fence = ""
    for number, line in enumerate(lines, 1):
        if fence:
            bare = line.strip()
            if len(line) - len(line.lstrip(" ")) <= 3 and len(bare) >= len(fence) and set(bare) == {fence[0]}:
                fence = ""
            else:
                pieces.append((number, line))
        elif m := FENCE.match(line):
            fence = m.group(1)
        else:
            pieces += [(number, code.group()) for code in CODE_SPAN.finditer(line)]
    return pieces


def waiter_errors(run: pathlib.Path) -> list[str]:
    """A waiter that counts the `Merged` marker with `grep -c` (or `--count`) instead of matching its hex sha."""
    errors: list[str] = []
    paths = sorted([*run.glob("_*.py"), *run.glob("*.sh"), *run.glob("_*.md")], key=lambda p: p.name)
    for path in paths:
        for number, piece in waiter_pieces(path):
            if "grep" in piece and COUNT_FLAG.search(piece) and "Merged" in piece and "[0-9a-f]" not in piece:
                errors.append(
                    f"{path.name}:{number}: a waiter counts the Merged marker with grep -c; match the hex sha instead"
                )
    return list(dict.fromkeys(errors))


def duty_errors(run: pathlib.Path) -> list[str]:
    """A ticked duty of `_control/duties.md` whose mark is not followed by `[YYYY-MM-DD ]HH:MM UTC`."""
    errors: list[str] = []
    for number, line in enumerate(read(run / "_control" / "duties.md").splitlines(), 1):
        if line.startswith("- [x]") and not TICK_TIME.match(line):
            duty = re.search(r"\bD\d+\b", line)
            errors.append(
                f"_control/duties.md:{number}: {duty.group() if duty else 'a duty'} is ticked without a UTC time"
            )
    return errors


def report(info: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(info, ensure_ascii=False, indent=1))
        return
    for e in info["errors"]:
        print("ERROR", e)
    print(
        "open:",
        {k: len(v) for k, v in info["open"].items()} or "none",
        "| done tasks:",
        len(info["done"]),
        "| errors:",
        len(info["errors"]),
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument(
        "--repo",
        help="the builder's checkout, for the done lines' shas (default: the cwd of the agent whose status is that build log, in _agents.json)",
    )
    ap.add_argument(
        "--state", help="the monitor's state, for the requests' first sight (default: <run-dir>/_control/monitor.json)"
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    run = pathlib.Path(args.run_dir)
    found = ids(run)  # 2-3. Defined ids, answer lines, open ids.
    done, done_errors = done_lines(run, args.repo)
    state = pathlib.Path(args.state) if args.state else run / "_control" / "monitor.json"
    requests, request_errs = request_errors(run, state, time.time())
    errors = [
        *status_errors(run),
        *found["duplicates"],
        *found["errors"],
        *twice_errors(run),
        *cause_errors(run),
        *lesson_errors(run),
        *done_errors,
        *handoff_errors(run),
        *request_errs,
        *merged_errors(run, args.repo),
        *waiter_errors(run),
        *duty_errors(run),
    ]
    report({"open": {**found["open"], **requests}, "done": done, "errors": errors}, args.json)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
