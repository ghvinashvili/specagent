# Task 2 — The watcher v3: reload, id match, ACK lines, the registry, restart without loss, one session per role

planner: c
builder: b
depends_on: —
files: `S/scripts/watch_agents.py`, `S/scripts/tests/test_watch_agents.py` (extended), `S/example/agents.json`, `S/example/agents-judge.json`, `S/scripts/README.md` (the watcher section and the Config v2 tables); S = `.claude/skills/running-specagent-pipelines`
acceptance: 10.5 (the registry file within one round of a planted STATUS change; its second clause, the manager reading it first, is Task 7's), 10.8 (its first two clauses; the third, the claim race, is Task 3's), 10.15 (the example configs name no model), 10.20 (the watcher's log times are UTC)

All paths below are relative to the checkout; `S` is the skill folder above. Measured at ff3354a (the plan branch); the
skill's files are identical at 0693a08 and ff3354a (`git diff --stat 0693a08 ff3354a -- .claude/skills/running-specagent-pipelines`
prints nothing) and builder B's branch got the same merge (`Merged: main->b at e32d413`, no common file).

## Goal

The watcher stops exiting when a brief is edited: it reloads the brief and tells the roles that read it, by an order
they must acknowledge with an `ACK <msg_id>` line in their own record file; it resends an order by stop and resume when
the line does not come. It matches sessions by the job id and session id recorded at launch instead of by name, stops a
copy that a resume started, and raises an event when a role has two running sessions. It keeps a registry
(`<run>/_control/registry.json`) with the need-1 fields of every role, written each round and restored at start, so a
restart keeps the pending orders and the revival counts. It orders a hand-over at a unit's end once the context is past
150k (never in the middle of a unit) and logs in UTC. The manager gives its own orders through `--order`.

## Departures (from the index and the spec, with the reason)

1. `scripts/tests/test_watch_agents.py` exists (21 test functions, 41 cases at ff3354a with a stub `claude` on PATH):
   it is extended; one test is changed by name (Step 3), every other kept test stays green unedited.
2. `scripts/migrate_agents_json.py` is unchanged: every v3 key is optional with a default, so a v2 config is a valid
   v3 config (no new config version).
3. No `--session-id` at launch: it is not verified together with `--bg`, and it would change the fresh argv that
   `test_handoff_launches_a_fresh_session_with_the_flags_and_bg_last` pins. The session id is learned from the job id
   that `--bg` prints (`claude stop <8 hex>`) and the row that carries it.
4. Fresh, nudge and unblock prompts carry no Order line (a fresh start shows in its row and transcript; the pinned fresh
   prompt stays equal); the orders that need an ACK are the cap hand-over, the unit-end hand-over, the reload and the
   manager's orders. A fresh prompt carries the Order lines of the manager's open orders only.
5. Exit 4 stays for a changed settings file (spec 8.1.4; 10.8 restarts a watcher that ended with exit 4) and for a
   control file that was removed; a brief whose content changed, or that was created, is reloaded (index, 8.1 row).
6. A manager order is sent by the manager itself (`SendMessage` with the text `--order` prints); the watcher records it,
   waits `ack_wait` seconds for the ACK and only then resends it by stop and resume (the owner's "resending by
   stop/resume when it is missing").
7. No wiki or decision page and no `docs/llms.txt` line in this commit: `wiki/` and `docs/` are builder A's; decision
   10a goes to Task 11 under `## For Task 11` (lessons.md, 20:36 UTC, C5, C8).
8. `scripts/tests/test_docs.py`, `scripts/tests/test_skill_example.py` and `example/README.md` are not edited: the
   example configs gain no `<placeholder>` and no `{run}/_<dir>/…` string, `--check` still calls only
   `claude agents --json --all` and still ends with `would sleep <interval> s and go on` on a run folder that holds
   only the settings and status files (no registry, no `_launch.md`), and every new key is documented in the README
   rows those tests read (Step 9).
9. The acceptance line claims two clauses beyond the index's cell (10.5, 10.8): 10.15's "no `_agents.json` flag names
   a model" for the two example configs (the index's row 2 contract; Task 1 claims the settings files, Task 4 the
   check) and 10.20's "every time in the records is in `date -u` form" for the watcher's log (K5; Task 4 claims the
   rest). The verifier checks those two clauses on this commit; Tasks 1 and 4 keep their claims.

## Contracts (what Task 2 provides; `manager/plan-fixer` carries them into the tasks named)

- K1 (Tasks 3, 5, 7, 11) The registry file is `<run_dir>/<registry>`, `registry` a config value relative to `run_dir`,
  default `"_control/registry.json"`. Schema version 1, one JSON object, written whole (tmp file + `os.replace`) at the
  end of every round and once more when the watcher exits with 0, 1, 3 or 4, never with `--check` or on exit 2:
  ```json
  {"version": 1, "run_dir": "<absolute run_dir>", "written_at": "2026-10-29T20:41:07Z",
   "watcher": {"pid": 12345, "started_at": "2026-10-29T20:30:00Z", "round": 7, "interval": 120},
   "roles": {"manager/planner-d": {
     "role": "planner-d", "lane": "d", "settings": "_control/planner-d-settings.json",
     "record": "<absolute path of the status file>", "unit": "STATUS: writing Task 3", "unit_since": "2026-10-29T20:13:00Z",
     "state": "running", "row_state": "working", "waiting_for": null,
     "job_id": "4d07d9c0", "session_id": "<uuid>", "session_ids": ["<uuid>", "<uuid>"], "launched_at": "2026-10-29T20:34:00Z",
     "context": 61234, "calls": 88, "cost_usd": 3.141593, "revivals": 0, "handoff_since": null,
     "orders": [{"msg_id": "c0ffee01", "kind": "manager", "text": "…", "sent_at": "2026-10-29T20:40:00Z",
                 "resends": 0, "acked_at": null, "closed": null}]}}}
  ```
  `roles` has one key per agent of the config, the name exactly as the config (`_agents.json`) writes it. `role` is
  the name's last `/` part. Times are UTC, `%Y-%m-%dT%H:%M:%SZ`. `state` is one of `running`, `stopped`, `blocked`,
  `done` (Task 3 reads only `roles.<agent>.state`; a missing file or key is no state): `done` when the agent is
  final, that is line 1 of the record starts with the agent's `final` (v2's test, `watch_agents.py:514` and `:521` at
  ff3354a); else `blocked` when the matched row's `state` is `blocked` or line 1 contains `blocked` (any case); else
  `running` when a matched row has a `pid`; else `stopped` (no matched row, or no `pid`).
  `row_state`, `waiting_for`: the matched row's `state` and `waitingFor`, or null. `unit`: line 1 of the record (null
  when it does not exist); `unit_since`: when the watcher first saw that line 1. `context`: the context of the current
  session's last call (input + cache write + cache read); `calls`, `cost_usd`: every call of every session in
  `session_ids`, each message id once (`usage_report.calls(path, seen)` with one shared `seen`), priced by
  `usage_report.PRICE[usage_report.family(model)]`, rounded to 6 decimals. `orders[].kind`: `handoff` (the cap),
  `unit-end`, `reload`, `manager`; `closed`: null while open, else `acked`, `superseded`, `final` or `no ack`.
  Restored at start: `job_id`, `session_id`, `session_ids`, `launched_at`, `unit`, `unit_since`, `revivals`,
  `handoff_since`, `orders`; every other field is recomputed each round.
- K2 (Task 4) The launch table: when `<run_dir>/_launch.md` exists, the watcher reads its first Markdown table whose
  header cells (spaces and backticks stripped) include `role`, `lane` and `settings`, in any order, more cells
  allowed. A row's `role` cell, backticks stripped, is an agent name; for an agent of the config the registry's `lane`
  and `settings` are that row's cells, stripped of spaces and backticks; without a row, `lane` is null and `settings`
  is the config's `settings` value. A row naming no agent of the config is logged once at start:
  `launch table: <name> is not watched`. The table is read at start and at each config reload.
- K3 (Tasks 1, 3, 4) The Order line, always the last line(s) of an order's prompt, one per order:
  `Order <msg_id>: append the line ` + "`ACK <msg_id>`" + ` to <absolute record path> before anything else.`
  (`msg_id` = `secrets.token_hex(4)`, 8 lowercase hex). The answer is a line `ACK <msg_id>` at the start of a line,
  appended by the role to its own record file (the agent's `status` file), matched by `(?m)^ACK ([0-9a-f]{8})\b`;
  a quoted ACK in the middle of a line is no answer. ACK lines are legal in every record (Task 3's `check_formats.py`
  accepts them); `example/common.md` (Task 1 or 4) tells every role: a prompt that ends with an Order line is
  acknowledged first.
- K4 (Task 7, Task 11's SKILL.md lines) The manager's orders:
  `python3 -I <skill>/scripts/watch_agents.py --order <agent> <text> <config>` appends one line
  `{"msg_id", "agent", "text", "at"}` to `<registry folder>/orders.jsonl`, prints `order <msg_id> <agent>` and then
  the prompt to send (the text, a blank line, the Order line), starts no `claude` command and exits 0; exit 2 with
  `config error: no agent <name>` or `config error: empty order`. The manager sends the printed prompt with
  `SendMessage`; the watcher merges the line in its next round with `sent_at` = `at`, waits for the ACK and resends.
  A fresh manager reads `_control/registry.json` before any record (10.5's second clause, Task 7's page).
- K5 (Tasks 3, 5) Log lines, each prefixed `YYYY-MM-DDTHH:MMZ ` (UTC, `time.gmtime`), the text exactly:
  `registry: <agent> revivals=<n> orders=<open msg ids joined by "," or ->` (once per agent at start when a registry
  was restored), `adopted <agent> <row id> by name`, `control file reloaded: <name>`, `control file changed: <name>`
  (exit 4), `reload <agent> <name>`, `unit end <agent> <context with commas> tokens; ordered to hand over`,
  `ack <agent> <msg_id>`, `resent <msg_id> to <agent> (<n> of <ack_resends>)`,
  `no ack <agent> <msg_id> after <n> resends` (an exit-0 event), `copy <agent> <id> kept`,
  `copies <agent>: <row ids sorted, joined by ", ">` (an exit-0 event), `launch table: <name> is not watched`.
  `--check` and `--order` print without the prefix, as `--check` does at ff3354a.
- K6 (Task 10) The watcher imports `usage_report` as `startup_report.py:27-28` does and uses `PRICE` (name -> a tuple
  of four $/1M prices: input, output, cache read, cache write), `family(model)` and `calls(path, seen=None)`; Task 10
  keeps those names, the tuple's order and the signatures (its prices may change: Task 2's test reads them).
- K7 (Tasks 4, 11; the contract of planner-b and lane A, task-04.md:54-55) No model in a config: Step 7 takes
  `"--model", "opus"` out of `common` in `S/example/agents.json` and `agents-judge.json`. `common` is the config's only
  flag list (`watch_agents.py:44`), so the test
  `test_the_example_configs_name_no_model_and_set_the_hand_over_mark_and_the_ack_rules` (`--model` in neither `common`)
  covers every flag of both; the README's `common` row names no model (Step 9); the model is set in the settings file
  (`references/sandbox-and-blindness.md:5`), and Task 4's pre-flight check `model` fails a model named in a config or a
  brief (task-04.md:73-74, :97). The `settings` values stay `_<role>-settings.json` in this task
  (`test_docs.py:126-127` writes each file at `run / agent["settings"]` in a flat run folder); Task 11 moves them to
  `_control/<role>-settings.json`, with the tests that read them, after `Merged: a+b+c+d` (For Task 11).

## Interfaces

`S/scripts/watch_agents.py` (v3; standard library only; every function under 50 lines, `.claude/rules/python.md:9`):

- CLI: `python3 -I watch_agents.py [--check] [--order AGENT TEXT] <config> [rounds]`. `--order` (argparse
  `nargs=2`, `metavar=("AGENT", "TEXT")`) is K4 and ignores `rounds`; `--check` is unchanged.
- `DEFAULTS` gains `"handoff_at": 150000`, `"ack_wait": 900`, `"ack_resends": 2`, `"registry": "_control/registry.json"`,
  `"unit_end_order": UNIT_END_ORDER`, `"reload_order": RELOAD_ORDER`; `TYPES` gains the non-negative number type for the
  three numbers and the string type for the other three, so a wrong type is `config error: <key> is not a non-negative
  number` or `config error: <key> is not a string` (the forms of `cap` and `nudge` at ff3354a), exit 2 at start, kept
  out by a reload. More checks at start (exit 2) and at a reload (kept out): `config error: handoff_at <v> is not below
  cap <cap>` when `handoff_at >= cap`; `config error: registry <value> leaves run_dir` (the `settings` check's form).
- Texts (filled by the same `fill()` as the other texts; `{at}` = `f"{handoff_at:,}"`, `{file}` = the file's absolute
  path, `{time}` = `time.strftime("%Y-%m-%d %H:%M", time.gmtime())`):
  `UNIT_END_ORDER = "Orders from the owner: your context has passed the hand-over mark ({at} tokens) and your unit of
  work has ended. Do not start the next unit: write your hand-over note now, as {run}/_handoff-rule.md says, and end
  your turn."` (its first 50 characters equal `HANDOFF_ORDER`'s on purpose: the transcript check of an order already
  given finds both); `RELOAD_ORDER = "Orders from the main session: {file} was changed at {time} UTC and you were
  restarted so that the change applies. If it is a brief, read it again before your next step; it wins over what you
  remembered. Then continue where you were."`; `ORDER_LINE = "Order {msg_id}: append the line ` + "`ACK {msg_id}`" +
  ` to {record} before anything else."`.
- Patterns: `ACK = re.compile(r"(?m)^ACK ([0-9a-f]{8})\b")`, `JOB = re.compile(r"claude stop ([0-9a-f]{8})\b")`,
  `COPY = re.compile(r"a copy as ([0-9a-f]{8})\b")`,
  `ORIGINAL = re.compile(r"claude attach ([0-9a-f]{8})\W+opens the original")`.
- `log(*parts)` prefixes `time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime())`.
- The rules each round, in this order (Step 6 gives each one's details): read the rows; match every agent's row by id
  (a reload order goes only to a role with a session); reload the briefs; merge the order inbox; per agent: read its
  ACK lines, then act (the copies check, v2's decisions, the unit end, the due orders); write the registry. Every v2
  rule not named here is unchanged.

`S/scripts/tests/test_watch_agents.py`: the stub `claude` and the helpers of Step 2, the changed test of Step 3, the new
tests of Steps 4-5 (no test starts a real session; each runs the watcher against a run folder in `tmp_path`).

`S/example/agents.json`: `common` without `"--model", "opus"`; `"handoff_at": 150000`, `"ack_wait": 900`,
`"ack_resends": 2`. `S/example/agents-judge.json`: `common` without `"--model", "opus"` (10.15; the model is set in the
settings file, `references/sandbox-and-blindness.md:5`).

## Steps

- [ ] Step 1: Check the base (in the builder's worktree, after `uv sync` once).

```bash
(ulimit -v 8388608; timeout -k 10 300 uv run pytest -q -p no:cacheprovider .claude/skills/running-specagent-pipelines/scripts/tests)
```
Expected: `146 passed` (ff3354a).

```bash
(ulimit -v 8388608; timeout -k 10 120 uv run pytest -q -p no:cacheprovider .claude/skills/running-specagent-pipelines/scripts/tests/test_watch_agents.py)
```
Expected: `41 passed` (ff3354a).

```bash
python3 -I .claude/skills/running-specagent-pipelines/scripts/watch_agents.py --help | grep -c -- '--order'
```
Expected: `0` (ff3354a; Step 10 counts the lines with `--order AGENT TEXT` and expects `2`).

- [ ] Step 2: The stub and the helpers of `S/scripts/tests/test_watch_agents.py` (five edits; nothing else of the
  ff3354a text changes).

2a. The imports become (three added: `ast`, `importlib.util`, `re`):

```python
import ast
import datetime
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import time
```

2b. `STUB` is replaced whole. New against ff3354a: a `write` or `on-stop.json` value `null` removes the file; a `stop`
exits after `on-stop.json` (it never reads `launch-out.json`); a launch prints the next text of `stub/launch-out.json`
when that file exists (the last one repeats), else the ff3354a line.

```python
STUB = """#!{python} -I
import json, os, pathlib, sys
state = pathlib.Path(os.environ["STUB_DIR"])


def apply(changes):
    for path, text in changes.items():
        if text is None:
            pathlib.Path(path).unlink(missing_ok=True)
        else:
            pathlib.Path(path).write_text(text)


def count(name):
    counter = state / name
    n = int(counter.read_text()) if counter.exists() else 0
    counter.write_text(str(n + 1))
    return n


if sys.argv[1:] == ["agents", "--json", "--all"]:
    rounds = json.loads((state / "rounds.json").read_text())
    answer = rounds[min(count("agents-calls"), len(rounds) - 1)]
    apply(answer.get("write", {}))
    print(json.dumps(answer["rows"]))
    sys.exit(0)
with open(state / "calls.jsonl", "a") as f:
    f.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd()}) + "\\n")
if sys.argv[1:2] == ["stop"]:
    if (state / "on-stop.json").exists():
        apply(json.loads((state / "on-stop.json").read_text()))
    print("s 12345678      show recent output")
    sys.exit(0)
out = state / "launch-out.json"
if out.exists():
    texts = json.loads(out.read_text())
    print(texts[min(count("launch-calls"), len(texts) - 1)])
else:
    print("s 12345678      show recent output")
"""
```

2c. `Pipeline.transcript` gains a last parameter `first=0`, the number of the first call, so two transcripts can share
some message ids and not others: the signature becomes
`def transcript(self, sid=SID, start=None, end=None, calls=1, context=1_000, output=10, prompts=(), first=0):` and in
its loop `"requestId": f"req_{i}"` becomes `"requestId": f"req_{first + i}"` and `"id": f"msg_{i}"` becomes
`"id": f"msg_{first + i}"` (the timestamps stay `iso(start + 1 + i)`).

2d. `Pipeline.watch`: the line `tail = [] if "--check" in args else [str(rounds)]` becomes
`tail = [] if "--check" in args or "--order" in args else [str(rounds)]`.

2e. After `def flags(...)` (before the first test), add:

```python
ORDER_LINE = re.compile(r"^Order ([0-9a-f]{8}): append the line `ACK \1` to (\S+) before anything else\.$")
RELOAD = "Orders from the main session:"
UNIT_END = "Orders from the owner: your context has passed the hand-over mark (150,000 tokens) and your unit of work"
MID, MID2 = "c0ffee01", "c0ffee02"


def utc(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def seconds(stamp: str) -> float:
    return datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.UTC).timestamp()


def registry(p: Pipeline) -> dict:
    return json.loads((p.run / "_control" / "registry.json").read_text(encoding="utf-8"))


def order(msg_id: str = MID, kind: str = "manager", text: str = "Read critique.md again.", ago: int = 60) -> dict:
    """An open order as the registry keeps it, sent `ago` seconds before now."""
    return {
        "msg_id": msg_id,
        "kind": kind,
        "text": text,
        "sent_at": utc(time.time() - ago),
        "resends": 0,
        "acked_at": None,
        "closed": None,
    }


def seed_registry(p: Pipeline, **fields) -> None:
    """The registry an earlier watcher of this run left: t/builder on session SID, with `fields` changed."""
    entry = {
        "job_id": SID[:8],
        "session_id": SID,
        "session_ids": [SID],
        "launched_at": None,
        "unit": "STATUS: building Task 3",
        "unit_since": utc(time.time() - 600),
        "revivals": 0,
        "handoff_since": None,
        "orders": [],
    }
    data = {
        "version": 1,
        "run_dir": str(p.run),
        "written_at": utc(time.time() - 60),
        "watcher": {"pid": 1, "started_at": utc(time.time() - 900), "round": 3, "interval": 0},
        "roles": {"t/builder": {**entry, **fields}},
    }
    path = p.run / "_control" / "registry.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def launch_out(p: Pipeline, *texts: str) -> None:
    """What the stub prints for each launch, in order (the last repeats)."""
    (p.stub / "launch-out.json").write_text(json.dumps(texts), encoding="utf-8")


def order_line(p: Pipeline, msg_id: str) -> str:
    return f"Order {msg_id}: append the line `ACK {msg_id}` to {p.run / 'build-log.md'} before anything else."


def usage_report():
    """The skill's usage_report module, for its prices (Task 10 may change them; the tests follow)."""
    spec = importlib.util.spec_from_file_location("usage_report", SCRIPT.parent / "usage_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
```

- [ ] Step 3: The changed test. Replace `test_a_changed_control_file_exits_4_instead_of_launching` (ff3354a, the
  parametrized test whose parameters are `_builder-settings.json` and `_builder-assignment.md`) with the test below:
  the settings case is unchanged, the brief case becomes a removed brief (a changed brief is reloaded, Step 4).
  `test_a_control_file_changed_during_the_stop_exits_4_before_the_launch` (a settings file) stays as it is.

```python
@pytest.mark.parametrize(
    "name, text", [("_builder-settings.json", "changed after the watcher started\n"), ("_builder-assignment.md", None)]
)
def test_a_changed_control_file_exits_4_instead_of_launching(p, name, text):
    """A changed settings file and a removed brief still exit 4 (spec 8.1.4); a brief whose content changed is
    reloaded instead (test_a_changed_brief_is_reloaded_with_an_order_instead_of_exit_4)."""
    p.transcript()
    note(p)
    p.rounds({"rows": [row()], "write": {str(p.run / name): text}})
    r = p.watch(rounds=2)
    assert r.returncode == 4, r.stdout + r.stderr
    assert f"control file changed: {name}" in r.stdout
    assert p.calls() == []  # not even the stop
```
- [ ] Step 4: The registry, the id match, the copies, the reload and the unit end tests. Append to the test file:

```python
def test_the_registry_lists_the_need_1_fields_of_every_role_and_follows_a_planted_status_change(p):
    p.config["agents"]["t/verifier"] = p.agent("verifier", "verify.md")
    p.config["agents"]["t/critic"] = p.agent("critic", "critique.md")
    p.write("verify.md", "STATUS: done after Task 2\n")  # final by its start, as v2 reads it; equality: "stopped"
    p.transcript(context=42_000, calls=2)
    rows = [row(), row(name="t/verifier", sid=SID2, state="stopped", status=None, pid=None)]
    p.rounds(rows, {"rows": rows, "write": {str(p.run / "build-log.md"): "STATUS: building Task 4\n"}})
    start = time.time()
    r = p.watch(rounds=2)
    assert r.returncode == 1, r.stdout + r.stderr
    data = registry(p)
    assert (data["version"], data["run_dir"], data["watcher"]["round"]) == (1, str(p.run), 2)
    assert start - 1 <= seconds(data["written_at"]) <= time.time() + 1  # written in the round that saw the change
    roles = data["roles"]
    assert set(roles) == {"t/builder", "t/verifier", "t/critic"}
    need_1 = {"role", "lane", "job_id", "session_id", "state", "unit", "context", "calls", "cost_usd", "revivals"}
    assert all(need_1 | {"orders"} <= set(entry) for entry in roles.values())
    b, v, c = roles["t/builder"], roles["t/verifier"], roles["t/critic"]
    assert (b["state"], b["unit"], b["job_id"], b["session_id"]) == ("running", "STATUS: building Task 4", SID[:8], SID)
    assert (b["context"], b["calls"], b["revivals"], b["orders"]) == (42_000, 2, 0, [])
    assert (b["role"], b["lane"], b["settings"]) == ("builder", None, "_builder-settings.json")
    assert b["record"] == str(p.run / "build-log.md")
    assert (v["state"], v["unit"], v["session_id"]) == ("done", "STATUS: done after Task 2", SID2)
    assert (c["state"], c["unit"], c["session_id"], c["job_id"]) == ("stopped", "STATUS: reviewing Task 4", None, None)
    assert "adopted t/builder 11111111 by name" in r.stdout


def test_calls_and_cost_count_each_call_once_over_every_session_of_the_role(p):
    seed_registry(p, session_id=SID2, session_ids=[SID, SID2], job_id=SID2[:8])
    p.transcript(sid=SID, calls=3)  # msg_0 .. msg_2
    p.transcript(sid=SID2, calls=4, first=2)  # msg_2 .. msg_5: a resumed session repeats the call it continues
    p.rounds([row(sid=SID2)])
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    entry = registry(p)["roles"]["t/builder"]
    ur = usage_report()
    p0, p1, p2, p3 = ur.PRICE[ur.family(None)]
    # six calls, msg_0 .. msg_5: the current session alone gives 4, msg_2 twice gives 7, the lines give 14
    assert entry["calls"] == 6
    assert entry["cost_usd"] == round(6 * (3 * p0 + 10 * p1 + 990 * p2 + 7 * p3) / 1e6, 6)  # 0.002796 at ff3354a
    assert (entry["context"], entry["session_id"], entry["session_ids"]) == (1_000, SID2, [SID, SID2])


def test_a_renamed_session_stays_matched_by_its_id_and_a_stopped_namesake_is_ignored(p):
    p.rounds([row()], [row(name="t/renamed"), row(sid=SID2, state="stopped", status=None, pid=None, age=7200)])
    r = p.watch(rounds=2)
    assert r.returncode == 1, r.stdout + r.stderr
    assert p.calls() == []  # by name, the stopped namesake SID2 would be revived
    entry = registry(p)["roles"]["t/builder"]
    assert (entry["session_id"], entry["session_ids"], entry["state"]) == (SID, [SID], "running")


def test_a_fresh_session_is_matched_by_the_job_id_its_launch_printed(p):
    p.transcript()
    note(p)
    launch_out(p, "fresh | s aaaaaaaa      show recent output\n  claude stop aaaaaaaa      stop this session")
    stopped = row(state="stopped", status=None, pid=None)
    p.rounds([row()], [stopped, row(name="t/other", sid=SID3, age=0)])
    r = p.watch(rounds=2)
    assert r.returncode == 1, r.stdout + r.stderr
    assert p.stops() == [SID[:8]] and len(p.launches()) == 1
    entry = registry(p)["roles"]["t/builder"]
    assert (entry["job_id"], entry["session_id"], entry["session_ids"]) == ("aaaaaaaa", SID3, [SID, SID3])
    assert entry["state"] == "running" and entry["launched_at"] is not None


def test_a_copy_that_a_revival_started_is_kept_as_the_role_s_session(p):
    """The copy carries the conversation and the prompt, so it is the role's session. The text is the tail v2 logged on
    2026-10-25 (vault, measurements/2026-10-25-jobs-tmp-and-run-logs.md:29): no process ran, so nothing is stopped."""
    launch_out(p, "d a copy as 28319368. Without flags, the same command continues 11111111 itself.")
    p.rounds([row(state="stopped", status=None, pid=None)])
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    [launch] = p.launches()
    assert launch["argv"][:2] == ["--resume", SID] and launch["argv"][-1].startswith("Your process was stopped")
    assert p.stops() == []
    assert "copy t/builder 28319368 kept" in r.stdout
    entry = registry(p)["roles"]["t/builder"]
    assert (entry["job_id"], entry["session_id"], entry["session_ids"]) == ("28319368", None, [SID])


def test_a_resume_that_starts_a_copy_keeps_the_copy_and_the_order_and_stops_the_original_again(p):
    """The text of claude 2.1.289 when the stop before the resume is still running. The next round matches the copy by
    its job id (6e rule 2), and the original, stopped the round before, is no second session (6i.1)."""
    copy = "28319368-0000-0000-0000-000000000000"
    p.config["ack_wait"] = 0
    seed_registry(p, orders=[order()])
    launch_out(
        p,
        "note: session 11111111 is already running in the background, so this started a copy as 28319368."
        " `claude attach 11111111` opens the original.",
    )
    ack = {str(p.run / "build-log.md"): f"STATUS: building Task 3\nACK {MID}\n"}
    p.rounds([row()], {"rows": [row(), row(sid=copy, age=0)], "write": ack})
    r = p.watch(rounds=2)
    assert r.returncode == 1, r.stdout + r.stderr
    [launch] = p.launches()
    assert launch["argv"][:2] == ["--resume", SID]
    assert launch["argv"][-1] == f"Read critique.md again.\n\n{order_line(p, MID)}"
    assert p.stops() == [SID[:8], SID[:8]]  # before the resume and after it; never the copy's 28319368
    assert "copy t/builder 28319368 kept" in r.stdout and f"ack t/builder {MID}" in r.stdout
    assert "adopted t/builder" not in r.stdout and "copies t/builder" not in r.stdout
    entry = registry(p)["roles"]["t/builder"]
    assert (entry["job_id"], entry["session_id"], entry["session_ids"]) == ("28319368", copy, [SID, copy])
    [o] = entry["orders"]
    assert (o["resends"], o["closed"]) == (1, "acked")


def test_two_running_sessions_of_one_role_end_the_watch_with_exit_0(p):
    p.rounds([row(), row(sid=SID2, age=10)])
    r = p.watch(rounds=2)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "copies t/builder: 11111111, 66666666" in r.stdout
    assert p.calls() == []


def test_a_changed_brief_is_reloaded_with_an_order_instead_of_exit_4(p):
    brief = p.run / "_builder-assignment.md"
    p.rounds({"rows": [row()], "write": {str(brief): "# the builder's brief, changed\n"}})
    r = p.watch(rounds=2)
    assert r.returncode == 1, r.stdout + r.stderr
    assert r.stdout.count("control file reloaded: _builder-assignment.md") == 1
    assert p.stops() == [SID[:8]]
    [launch] = p.launches()
    assert launch["argv"][:2] == ["--resume", SID] and launch["argv"][2:-2] == flags(p)
    prompt = launch["argv"][-1]
    assert prompt.startswith(f"{RELOAD} {brief} was changed at ")
    m = ORDER_LINE.match(prompt.splitlines()[-1])
    assert m and m.group(2) == str(p.run / "build-log.md")
    [o] = registry(p)["roles"]["t/builder"]["orders"]
    assert (o["msg_id"], o["kind"], o["resends"], o["closed"]) == (m.group(1), "reload", 0, None) and o["sent_at"]


@pytest.mark.parametrize(
    "name, stopped", [("_builder-assignment.md", [SID[:8]]), ("_handoff-rule.md", sorted([SID[:8], SID2[:8]]))]
)
def test_a_reload_order_goes_to_the_roles_whose_texts_name_the_file(p, name, stopped):
    """The builder's fresh text names its brief; the hand-over order, common to every role, names _handoff-rule.md,
    which does not exist when the watcher starts: a brief created later is reloaded too."""
    p.config["agents"]["t/verifier"] = p.agent("verifier", "verify.md")
    p.rounds({"rows": [row(), row(name="t/verifier", sid=SID2)], "write": {str(p.run / name): "# changed\n"}})
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    assert r.stdout.count(f"control file reloaded: {name}") == 1
    assert sorted(p.stops()) == stopped and len(p.launches()) == len(stopped)
    assert all(c["argv"][-1].startswith(f"{RELOAD} {p.run / name} was changed at ") for c in p.launches())


@pytest.mark.parametrize("text, code, launches", [("# changed during the stop\n", 1, 1), (None, 4, 0)])
def test_a_brief_changed_during_the_stop_is_launched_and_a_removed_one_exits_4(p, text, code, launches):
    """A fresh session reads its brief when it starts, so a brief changed during the stop needs no exit; a removed
    one would leave the session a brief it cannot read."""
    p.transcript()
    note(p)
    (p.stub / "on-stop.json").write_text(json.dumps({str(p.run / "_builder-assignment.md"): text}))
    r = p.watch(rounds=1)
    assert r.returncode == code, r.stdout + r.stderr
    assert p.stops() == [SID[:8]] and len(p.launches()) == launches
    assert ("control file changed: _builder-assignment.md" in r.stdout) == (code == 4)


@pytest.mark.parametrize(
    "context, line, ordered",
    [
        (160_000, "STATUS: building Task 4\n", True),
        (100_000, "STATUS: building Task 4\n", False),
        (160_000, "STATUS: building Task 3\n", False),
    ],
)
def test_a_unit_end_past_the_mark_orders_a_hand_over_and_the_middle_of_a_unit_never(p, context, line, ordered):
    p.transcript(context=context)
    p.rounds([row()], {"rows": [row()], "write": {str(p.run / "build-log.md"): line}})
    r = p.watch(rounds=3)
    assert r.returncode == 1, r.stdout + r.stderr
    assert (f"unit end t/builder {context:,} tokens; ordered to hand over" in r.stdout) == ordered
    if not ordered:
        assert p.calls() == []
        return
    assert p.stops() == [SID[:8]]
    [launch] = p.launches()  # once: the hand-over is pending in round 3
    assert launch["argv"][:2] == ["--resume", SID]
    prompt = launch["argv"][-1]
    assert prompt.startswith(UNIT_END) and f"{p.run}/_handoff-rule.md" in prompt
    assert ORDER_LINE.match(prompt.splitlines()[-1])
    entry = registry(p)["roles"]["t/builder"]
    assert entry["handoff_since"] is not None and [o["kind"] for o in entry["orders"]] == ["unit-end"]
```
- [ ] Step 5: The order, ACK, restart, config, clock and shape tests. Append to the test file:

```python
def test_an_order_goes_to_the_inbox_and_is_resent_by_stop_and_resume_when_no_ack_comes(p):
    p.config["ack_wait"] = 0
    o = p.watch("--order", "t/builder", "Read critique.md again.")
    assert o.returncode == 0, o.stdout + o.stderr
    assert p.calls() == [] and not (p.stub / "agents-calls").exists()
    first, *rest = o.stdout.splitlines()
    mid = re.fullmatch(r"order ([0-9a-f]{8}) t/builder", first).group(1)
    prompt = f"Read critique.md again.\n\n{order_line(p, mid)}"
    assert "\n".join(rest) == prompt
    [line] = (p.run / "_control" / "orders.jsonl").read_text(encoding="utf-8").splitlines()
    sent = json.loads(line)
    assert (sent["msg_id"], sent["agent"], sent["text"]) == (mid, "t/builder", "Read critique.md again.")
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"resent {mid} to t/builder (1 of 2)" in r.stdout
    assert p.stops() == [SID[:8]]
    [launch] = p.launches()
    assert launch["argv"][:2] == ["--resume", SID] and launch["argv"][-1] == prompt
    [entry] = registry(p)["roles"]["t/builder"]["orders"]
    assert (entry["msg_id"], entry["kind"], entry["resends"], entry["closed"]) == (mid, "manager", 1, None)


@pytest.mark.parametrize(
    "answer, acked", [(f"ACK {MID}\n", True), (f"I will append the line `ACK {MID}` later\n", False)]
)
def test_an_ack_line_closes_the_order_and_a_quoted_one_does_not(p, answer, acked):
    p.config["ack_wait"] = 0
    seed_registry(p, orders=[order()])
    p.write("build-log.md", "STATUS: building Task 3\n" + answer)
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    assert (f"ack t/builder {MID}" in r.stdout) == acked
    assert (f"resent {MID} to t/builder (1 of 2)" in r.stdout) == (not acked)
    assert len(p.launches()) == (0 if acked else 1)
    [o] = registry(p)["roles"]["t/builder"]["orders"]
    assert (o["closed"], o["acked_at"] is not None) == (("acked", True) if acked else (None, False))


def test_an_order_still_without_ack_after_the_last_resend_ends_the_watch_with_exit_0(p):
    p.config.update(ack_wait=0, ack_resends=1)
    seed_registry(p, orders=[order()])
    r = p.watch(rounds=3)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"resent {MID} to t/builder (1 of 1)" in r.stdout
    assert f"no ack t/builder {MID} after 1 resends" in r.stdout
    assert len(p.launches()) == 1
    [o] = registry(p)["roles"]["t/builder"]["orders"]
    assert (o["resends"], o["closed"]) == (1, "no ack")


def test_a_final_line_with_a_suffix_is_done_and_closes_the_open_orders(p):
    p.config["agents"]["t/verifier"] = p.agent("verifier", "verify.md")
    p.write("verify.md", "STATUS: done after Task 2\n")
    o = p.watch("--order", "t/verifier", "Verify Task 3 again.")
    assert o.returncode == 0, o.stdout + o.stderr
    p.rounds([row(), row(name="t/verifier", sid=SID2, state="stopped", status=None, pid=None)])
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    v = registry(p)["roles"]["t/verifier"]
    assert (v["state"], v["unit"]) == ("done", "STATUS: done after Task 2")  # equality gives "stopped"
    [closed] = v["orders"]
    assert closed["closed"] == "final"  # equality leaves it open
    assert p.launches() == []


def test_a_watcher_restarted_after_exit_4_logs_the_same_pending_orders_and_revival_counts(p):
    """10.8, second clause: the first watcher ends with exit 4 (a settings file changed before the resend), the second
    restores the order and the revival count, the third resends the order once it is due."""
    seed_registry(p, revivals=1, orders=[order()])
    settings = str(p.run / "_builder-settings.json")
    p.rounds({"rows": [row()], "write": {settings: "changed after the watcher started\n"}})
    restored = f"registry: t/builder revivals=1 orders={MID}"
    p.config["ack_wait"] = 0
    first = p.watch(rounds=1)
    assert first.returncode == 4 and restored in first.stdout, first.stdout + first.stderr
    assert p.calls() == []
    p.config["ack_wait"] = 3600
    second = p.watch(rounds=1)
    assert second.returncode == 1 and restored in second.stdout, second.stdout + second.stderr
    assert p.calls() == []
    p.config["ack_wait"] = 0
    third = p.watch(rounds=1)
    assert f"resent {MID} to t/builder (1 of 2)" in third.stdout, third.stdout + third.stderr
    assert len(p.launches()) == 1


def test_revivals_count_across_restarts(p):
    p.config["nudges"] = 2
    p.rounds([row(state="stopped", status=None, pid=None)])
    runs = [p.watch(rounds=1) for _ in range(3)]
    assert [r.returncode for r in runs] == [1, 1, 0], [r.stdout for r in runs]
    assert "registry: t/builder revivals=1 orders=-" in runs[1].stdout
    assert "registry: t/builder revivals=2 orders=-" in runs[2].stdout
    assert runs[2].stdout.strip().endswith("t/builder was revived 2 times; check it")
    assert len(p.launches()) == 2


def test_a_note_acted_on_before_a_restart_is_not_acted_on_again(p):
    p.transcript()
    note(p)
    first, second = p.watch(rounds=1), p.watch(rounds=1)
    assert (first.returncode, second.returncode) == (1, 1), first.stdout + second.stdout
    assert len(p.launches()) == 1 and p.stops() == [SID[:8]]


def test_the_cap_order_ends_with_an_order_line_and_is_recorded_as_a_pending_hand_over(p):
    p.transcript(context=250_000)
    r = p.watch(rounds=2)
    assert r.returncode == 1, r.stdout + r.stderr
    [launch] = p.launches()
    prompt = launch["argv"][-1]
    assert prompt.startswith(ORDER)
    m = ORDER_LINE.match(prompt.splitlines()[-1])
    assert m and m.group(2) == str(p.run / "build-log.md")
    entry = registry(p)["roles"]["t/builder"]
    [o] = entry["orders"]
    assert (o["msg_id"], o["kind"], o["resends"], o["acked_at"], o["closed"]) == (m.group(1), "handoff", 0, None, None)
    assert entry["handoff_since"] is not None and entry["context"] == 250_000


def test_a_fresh_session_gets_the_open_manager_orders_and_the_watcher_s_are_superseded(p):
    seed_registry(p, orders=[order(), order(MID2, "reload", "Orders from the main session: an old reload.")])
    p.transcript()
    note(p)
    start = time.time()
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    [launch] = p.launches()
    prompt = launch["argv"][-1]
    assert prompt.startswith("You are a fresh builder session; the previous one handed over")
    assert prompt.endswith(f"\n\nRead critique.md again.\n\n{order_line(p, MID)}") and MID2 not in prompt
    manager, reload = registry(p)["roles"]["t/builder"]["orders"]
    assert seconds(manager["sent_at"]) >= start - 1 and (manager["resends"], manager["closed"]) == (0, None)
    assert reload["closed"] == "superseded"


@pytest.mark.parametrize(
    "change, message",
    [
        ({"handoff_at": 250_000}, "config error: handoff_at 250000 is not below cap 200000"),
        ({"registry": "../registry.json"}, "config error: registry ../registry.json leaves run_dir"),
        ({"ack_resends": -1}, "config error: ack_resends is not a non-negative number"),
        ({"ack_wait": "15m"}, "config error: ack_wait is not a non-negative number"),
        ({"unit_end_order": 7}, "config error: unit_end_order is not a string"),
    ],
)
def test_v3_config_errors_exit_2_before_any_claude_command(p, change, message):
    p.config.update(change)
    r = p.watch(rounds=1)
    assert r.returncode == 2, r.stdout + r.stderr
    assert message in r.stdout
    assert not (p.stub / "agents-calls").exists() and p.calls() == []


@pytest.mark.parametrize(
    "agent, text, message",
    [("t/nobody", "Read it.", "config error: no agent t/nobody"), ("t/builder", "   ", "config error: empty order")],
)
def test_an_order_for_no_agent_or_without_text_exits_2_and_writes_nothing(p, agent, text, message):
    r = p.watch("--order", agent, text)
    assert r.returncode == 2, r.stdout + r.stderr
    assert message in r.stdout
    assert not (p.run / "_control" / "orders.jsonl").exists() and p.calls() == []


def test_log_lines_carry_the_utc_time(p, monkeypatch):
    monkeypatch.setenv("TZ", "XXX+4")  # local time 4 hours behind UTC: a local stamp cannot pass
    p.transcript(context=250_000)
    before = time.time()
    r = p.watch(rounds=1)
    after = time.time()
    [line] = [x for x in r.stdout.splitlines() if "cap t/builder" in x]
    assert line.split(" ", 1)[0] in {time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(t)) for t in (before, after)}, line


def test_every_function_of_the_watcher_is_under_50_lines():
    """`.claude/rules/python.md:9` (at ff3354a: Watcher.agent 83 lines, Transcripts.stats 55, Watcher.__init__ 50)."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    sizes = {
        f"{n.name}:{n.lineno}": n.end_lineno - n.lineno + 1
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    assert {name: size for name, size in sizes.items() if size >= 50} == {}


def test_the_example_configs_name_no_model_and_set_the_hand_over_mark_and_the_ack_rules():
    example = SCRIPT.parents[1] / "example"
    for name in ("agents.json", "agents-judge.json"):
        assert "--model" not in json.loads((example / name).read_text(encoding="utf-8"))["common"], name
    config = json.loads((example / "agents.json").read_text(encoding="utf-8"))
    assert (config["handoff_at"], config["ack_wait"], config["ack_resends"]) == (150_000, 900, 2)


LAUNCH = """# Launch table of a run

| lane | role | skills | settings | ECC texts | cost estimate |
| --- | --- | --- | --- | --- | --- |
| b | `t/builder` | none | `_control/_builder-settings.json` | none | $40 |
| v | `t/ghost` | none | `_control/_ghost-settings.json` | none | $5 |
"""


@pytest.mark.parametrize(
    "table, lane, settings", [(LAUNCH, "b", "_control/_builder-settings.json"), (None, None, "_builder-settings.json")]
)
def test_the_registry_takes_lane_and_settings_from_the_launch_table(p, table, lane, settings):
    if table:
        p.write("_launch.md", table)
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    roles = registry(p)["roles"]
    assert set(roles) == {"t/builder"}
    assert (roles["t/builder"]["lane"], roles["t/builder"]["settings"]) == (lane, settings)
    assert ("launch table: t/ghost is not watched" in r.stdout) == bool(table)
```
- [ ] Step 6: Run the new tests red on v2, then implement v3.

```bash
(ulimit -v 8388608; timeout -k 10 300 uv run pytest -q -p no:cacheprovider .claude/skills/running-specagent-pipelines/scripts/tests/test_watch_agents.py)
```
Expected before any change to `watch_agents.py`: `34 failed, 44 passed`. The 78 cases are the 41 of ff3354a (the test
of Step 3 keeps its two cases) and the 37 of Steps 4-5. Three new cases pass on v2, as they should: the removed brief
of `test_a_brief_changed_during_the_stop_is_launched_and_a_removed_one_exits_4` and the two cases of
`test_a_unit_end_past_the_mark_orders_a_hand_over_and_the_middle_of_a_unit_never` that order nothing. Measured by the
planner on a copy of the skill at ff3354a with Steps 2-5 applied, `ruff check` and `ruff format --check` clean on it.
Another count means a step went in wrongly: compare the test file with Steps 2-5 before you write code.

The planner ran each plausible wrong version once on that copy (`scratch/planner-c/wrong_versions.py`), red under the
test named:
- `calls` and `cost_usd` over the current session only: 4 calls, not 6; a new `seen` per session: 7; one per transcript
  line: 14 (`test_calls_and_cost_count_each_call_once_over_every_session_of_the_role`; the cost at ff3354a's prices is
  0.002796, and the test computes it from `usage_report.PRICE`, so Task 10's new prices keep it green).
- the ACK searched anywhere in a line: `['c0ffee01']` for the quoted line, where `ACK` finds `[]`
  (`test_an_ack_line_closes_the_order_and_a_quoted_one_does_not`).
- the copy's id taken as the first 8 hex digits of the resume's output: `11111111`, not `28319368`
  (`test_a_resume_that_starts_a_copy_keeps_the_copy_and_the_order_and_stops_the_original_again`; run on both texts
  by the plan fixer, `scratch/plan-fixer/t2/regex_check.py`).
- Computed from the fixtures, not run (there is no v3 code to run them on): the copy stopped at once (the rule before
  C500): `p.stops()` ends with `28319368`, and the next round has two live rows, exit 0 with `copies t/builder:
  11111111, 28319368`; the original that was stopped the round before counted by 6i.1: the same exit 0; the copy kept
  without the second stop: `p.stops() == ["11111111"]`; `session_id` kept instead of null: the next round matches the
  original by rule 1, `session_id` `SID`; a final line by equality: the verifier `stopped` and its order open
  (`test_a_final_line_with_a_suffix_is_done_and_closes_the_open_orders`, and the registry test).

Then implement v3. The rules below are what the tests pin and what they leave for you to keep; every v2 rule not named
here stays as at ff3354a. The code is yours: standard library only, every function under 50 lines
(`test_every_function_of_the_watcher_is_under_50_lines`; at ff3354a `Watcher.agent` has 83 lines, `Transcripts.stats`
55 and `Watcher.__init__` 50, so all three are split).

6a. Command line (K4). `main()` puts `--check` and `--order` (`nargs=2`, `metavar=("AGENT", "TEXT")`) in one
    `add_mutually_exclusive_group()`; both given is argparse's exit 2 (`argument --order: not allowed with argument
    --check`). With `--order` the config is loaded and checked as at start (`config error: …`, exit 2), then `config
    error: no agent <agent>` when the config has no such agent and `config error: empty order` when the text is blank
    after `strip()`, both exit 2 with nothing written. Otherwise it makes the registry's folder
    (`mkdir(parents=True, exist_ok=True)`), appends `json.dumps({"msg_id": m, "agent": agent, "text": text, "at": now})`
    and a newline to `orders.jsonl` in that folder (`m = secrets.token_hex(4)`, `now` UTC as in K1), prints
    `order <m> <agent>` and then the prompt (the text as given, a blank line, the Order line of K3 with the agent's
    `status` file as an absolute path), runs no `claude` command and exits 0; `rounds` is ignored.
6b. Config. `DEFAULTS` and `TYPES` gain the six keys of the Interfaces; `check_types` gives their type errors. After the
    type checks, `config error: handoff_at <handoff_at> is not below cap <cap>` when `handoff_at >= cap`, and `config
    error: registry <value> leaves run_dir` in the form of the `settings` check (`watch_agents.py:386`). At start each
    is exit 2 before any `claude` command; a reloaded config that fails one is kept out with v2's `config invalid, kept
    the previous one: <error>`. `control_files()` scans `unit_end_order` with the other texts (its `_handoff-rule.md`).
6c. Start (not with `--check` or `--order`). `<run_dir>/<registry>` is read once. When it parses to a JSON object with
    `"version": 1`, each agent of the config that its `roles` holds gets back the fields K1 restores (a missing one
    takes its fresh value: null, `[]` or 0) and the line `registry: <agent> revivals=<n> orders=<open msg ids joined by
    "," or ->`, in config order. A missing file, or one that is not a version 1 object, restores nothing and is replaced
    by the first write. `revivals` is v2's `self.revived` count and `handoff_since` v2's `self.pending` time, so v2's
    revival limit and hand-over timeout see the restored values; the other `RUN_STATE` entries start empty as at
    ff3354a. The launch table (K2) is read here and at each config reload; its `launch table: <name> is not watched`
    lines are logged at start only.
6d. A round, in this order: v2's config reload and `blocked_files` lines; the rows of `claude agents --json --all`, all
    of them (v2's `latest_rows` kept the newest per name; a failed call as at ff3354a); the match of every agent (6e),
    and in the first round v2's `seed()` with the matched rows; the briefs (6f); the inbox (6g); per agent in config
    order: its ACK lines (6h), then its acts (6i) when it has a matched row, else v2's `no session`, then `unit` = line
    1 of its record and, when that changed, `unit_since` = now; v2's final check; the registry write (6l).
6e. The match, per agent. The first rule that finds a row wins; a known id whose row is gone falls through:
    (1) a known `session_id`: the row whose `sessionId` equals it, whatever its name or state (a renamed session stays
    the agent's; a namesake with another id is not);
    (2) a known `job_id`: the row whose `id` equals it (the id `--bg` printed as `claude stop <id>`); `session_id` = its
    `sessionId`, added to `session_ids`;
    (3) by name: of the rows named exactly as the agent, the newest by `startedAt` that is at least `launched_at` minus
    5 seconds (any age when `launched_at` is null); `job_id` = its `id`, `session_id` = its `sessionId`, added to
    `session_ids`, and the line `adopted <agent> <row id> by name`.
6f. The briefs. A brief is a control file other than the config, the settings files and the `extra_prompt` file. A
    brief whose SHA-256 is not None and differs from the stored one (changed, or created after the start) gets its new
    hash stored, the line `control file reloaded: <name>` and a `reload` order (6j; its text the filled `reload_order`
    with `lang`) for every agent that is not final, has a matched row with a `sessionId`, and whose texts name the
    file: the texts `control_files()` scans for that agent (its role's fresh text, its role's milestone text when
    `milestones` is set, the nudge, the hand-over order, the unblock text and `unit_end_order`), with `BRIEF`.
    `changed()`, which `act()` calls before the stop and after it, now names a settings file or the `extra_prompt` file
    whose hash changed, or a brief whose stored hash is not None and whose file is gone; then the watcher logs `control
    file changed: <name>` and exits 4 as at ff3354a. A brief changed during the stop is no change there: the session
    reads it, and the next round reloads it (Deferred 5).
6g. The inbox. `orders.jsonl` beside the registry (missing: empty) is read each round; a line that parses to an object
    whose `msg_id` no order of the registry has and whose `agent` is an agent of the config becomes an open order of
    that agent: kind `manager`, its `text`, `sent_at` = its `at` (the manager has sent it), `resends` 0, `acked_at` and
    `closed` null. Other lines are skipped. The watcher never rewrites the file; the manager only appends to it.
6h. ACK lines. For an agent with open orders, its record (the `status` file) is read, and every `ACK` match that names
    one of them closes it: `closed` = `acked`, `acked_at` = now, the line `ack <agent> <msg_id>`. A quoted
    `ACK <msg_id>` inside a line is no answer (the pattern's `^`).
6i. The acts of an agent with a matched row; at most one launch per agent per round:
    1. Copies: the rows with a `pid` that carry the agent's name, its `job_id` as `id` or a `sessionId` of
       `session_ids`, except a row whose `id` the watcher sent `claude stop` in this round or the round before (that
       stop may still be running: the original of a kept copy, 6k, or the session a fresh launch replaced); two or
       more give the exit-0 event `copies <agent>: <their ids sorted, joined by ", ">` and no other act for the agent.
    2. v2's decisions on the matched row (budget, the note, milestones, the cap, blocked, revival), unchanged but for
       the cap: its hand-over becomes an order of kind `handoff` (its text the filled `handoff_order` with `lang`), sent
       by 4, and `handoff_since` takes v2's `self.pending` place. A decision that launches ends the agent's acts.
    3. The unit end: line 1 of the record differs from `unit`, `unit` is not null, the agent is not final (K1),
       the current session's last call is over `handoff_at` (the context the cap rule reads), and `handoff_since` is
       null. Then a `unit-end` order (its text the filled `unit_end_order` with `lang`) and `handoff_since` = now; it
       is sent by 4 with the line `unit end <agent> <context with commas> tokens; ordered to hand over`.
    4. The due orders (6j).
6j. Orders. An agent's orders move only while it is deliverable: a matched row with a `sessionId`, the agent not
    final (K1), the row's `state` not `blocked`, and no hand-over pending, except that the pending hand-over's own order
    (kind `handoff` or `unit-end`) may still be resent. An open order is due when its `sent_at` is null (a new
    `handoff`, `unit-end` or `reload` order), or when `now - sent_at >= ack_wait` and `resends < ack_resends` (a
    resend: `resends` + 1). When `now - sent_at >= ack_wait` and `resends >= ack_resends`, the order is closed `no ack`
    with the exit-0 event `no ack <agent> <msg_id> after <resends> resends`. Every due order of the agent goes in one
    launch: v2's `act()` (the control files checked, the stop only when the row has a `pid`, the check again), then
    `--resume <sessionId>` with a prompt of the due orders in registry order joined by a blank line, each its `text`, a
    blank line and its Order line (K3). Each sent order gets `sent_at` = now. One log line per order, a new one's own
    (`cap …`, `unit end …`, `reload <agent> <name>`) and a resend's `resent <msg_id> to <agent> (<resends> of
    <ack_resends>)`; the first carries the launch's ` | <tail>` as v2's lines do, the others are logged without it.
    When the agent is final (K1: line 1 starts with its `final`), its open orders are closed `final`.
6k. Fresh launches and resumes. v2's fresh rules (the note, the hand-over timeout, the milestones) launch as at ff3354a
    and now also: the agent's open `handoff`, `unit-end` and `reload` orders are closed `superseded`; each open
    `manager` order is added to the fresh prompt (a blank line, its text, a blank line, its Order line) with `sent_at`
    = now and `resends` = 0; after the launch `job_id` = the `JOB` match in its output (null without one), `session_id`
    = null, `launched_at` = now and `handoff_since` = null, while `session_ids` keeps the earlier ids. After a resume, a
    `JOB` match in its output replaces `job_id`. A `COPY` match is the resumed session and is never stopped: the CLI
    starts a copy when the session is still running or open in another process, and the copy carries the conversation
    and the prompt (all 17 cap orders in this run's `_watch.log` started one, and each role then wrote its note and got
    its fresh session). Then `job_id` = the copy's id, `session_id` = null (rule 2 of 6e matches its row the next
    round), and the line `copy <agent> <id> kept`; when the output also has an `ORIGINAL` match, `claude stop <that
    id>` is sent once more (the stop before the resume may still be running; 6i.1 skips that row meanwhile).
6l. The registry. K1's object, written whole to a temporary file in the registry's folder (made when missing) and moved
    over the old one with `os.replace`: at the end of every round, and once more when the watcher returns 0, 3 or 4 and
    after its last round (1); never with `--check`, `--order` or on exit 2. `roles` has one entry per agent of the
    config: `state` by K1's order, `lane` and `settings` by K2, `context` from the current session's last call (null
    without a current session), `calls` and `cost_usd` over every session of `session_ids` with one shared `seen` (K6);
    `watcher` = `{"pid": os.getpid(), "started_at": …, "round": <rounds done>, "interval": …}`.
6m. Log and `--check`. `log()` prefixes `time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime())`
    (`test_log_lines_carry_the_utc_time` sets `TZ`), and `{time}` in the texts is UTC too. `--check` reads no registry,
    merges no inbox, writes nothing, matches by rule (3) alone and prints no `adopted` line, so its output for the same
    rows is v2's (`test_docs.py:118-137`).

```bash
(ulimit -v 8388608; timeout -k 10 120 uv run pytest -q -p no:cacheprovider .claude/skills/running-specagent-pipelines/scripts/tests/test_watch_agents.py -k 'not example_configs_name_no_model')
```
Expected: `77 passed, 1 deselected`. The deselected test reads the example configs, which Step 7 changes once the code
knows the new keys (measured on the scratch copy with v2's code, this command gives
`33 failed, 44 passed, 1 deselected`: the filter takes exactly that test); Step 7 runs it and Step 10 runs all 78.
A kept test that fails names a v2 rule this step changed by mistake: fix the code, never the test
(lessons.md "Read first" 11); a new test you believe wrong goes to `manager/plan-fixer` with the proof (first-pass
rule 1).
- [ ] Step 7: The example configs. After Step 6, not before: v2 refuses the new keys (`config error: unknown fields
  ack_resends, ack_wait, handoff_at`, measured with this step's edits on a scratch copy that still had v2's code).

In `S/example/agents.json` (lines at ff3354a): delete lines 5-6 of `common` (`    "--model",` and `    "opus",`);
after `  "cap": 200000,` (line 23) insert `  "handoff_at": 150000,`; after `  "nudges": 6,` (line 27) insert
`  "ack_wait": 900,` and `  "ack_resends": 2,`, in this order. In `S/example/agents-judge.json`: delete lines 5-6
(`    "--model",` and `    "opus",`) and nothing else (the judge runs once; the defaults hold). The model is set in
the settings file (`references/sandbox-and-blindness.md:5`; 10.15). Nothing else changes in either file: `agents`,
the `settings` values, the texts and `blocked_files` stay as at ff3354a (the `settings` values move in Task 11,
lessons.md 20:53 UTC; no new placeholder and no `{run}/_<dir>/` string, C3). Two-space indent, as the files have.
`common` then reads, and the numbers from `cap` to `nudges`:

```json
  "common": [
    "--strict-mcp-config",
    "--effort",
    "max",
    "--permission-mode",
    "auto",
    "--setting-sources",
    "local"
  ],
```

```json
  "cap": 200000,
  "handoff_at": 150000,
  "handoff_wait": 1200,
  "permission_wait": 600,
  "interval": 120,
  "nudges": 6,
  "ack_wait": 900,
  "ack_resends": 2,
```

```bash
grep -c -e '"--model"' -e '"opus"' .claude/skills/running-specagent-pipelines/example/agents.json .claude/skills/running-specagent-pipelines/example/agents-judge.json; echo "exit $?"
```
Expected: `.claude/skills/running-specagent-pipelines/example/agents.json:0` and
`.claude/skills/running-specagent-pipelines/example/agents-judge.json:0`, then `exit 1` (grep matched nothing; at
ff3354a both counts are `2` and the exit is 0).

```bash
python3 -I -c "import json, sys; [json.load(open(f, encoding='utf-8')) for f in sys.argv[1:]]; print('json ok')" .claude/skills/running-specagent-pipelines/example/agents.json .claude/skills/running-specagent-pipelines/example/agents-judge.json
```
Expected: `json ok`.

```bash
(ulimit -v 8388608; timeout -k 10 120 uv run pytest -q -p no:cacheprovider .claude/skills/running-specagent-pipelines/scripts/tests/test_skill_example.py ".claude/skills/running-specagent-pipelines/scripts/tests/test_docs.py::test_the_example_config_is_v2_and_check_accepts_it" ".claude/skills/running-specagent-pipelines/scripts/tests/test_watch_agents.py::test_the_example_configs_name_no_model_and_set_the_hand_over_mark_and_the_ack_rules")
```
Expected: `11 passed`: the 9 of `test_skill_example.py`, `test_docs.py`'s example test (v3's `--check` accepts the
new keys, `handoff_at` below `cap`) and the test Step 6 deselected. On the scratch copy with v2's code the 9 and the
last one passed (`10 passed`); the `test_docs.py` one needs Step 6's `DEFAULTS`.

- [ ] Step 8: The module docstring (`S/scripts/watch_agents.py:2-62` at ff3354a). No test reads its prose; the command
  below checks five facts in it. Keep v2's text where this list does not change it; lines at most 120 characters
  (ruff, Step 10).
  1. Line 2: `version 2` becomes `version 3`.
  2. The usage block (lines 6-8) gains a third command, aligned as the two above it:
     `python3 watch_agents.py --order <agent> <text> <config>` with `(appends one order to orders.jsonl beside the
     registry and prints the prompt to send; runs no claude command; rounds is ignored)`.
  3. Before `Each round, for every agent …` (line 10), a paragraph on the round of version 3, in its order (6d): the
     rows of `claude agents --json --all`; each agent's row matched by the session id recorded at its launch, then by
     the job id `--bg` printed, then by name (6e); the briefs, a changed one reloaded with a reload order to the
     sessions whose texts name it (6f); the inbox `orders.jsonl` (6g); per agent its `ACK <msg_id>` lines (6h), then
     its acts (6i); the registry last (6l).
  4. After the `- revival:` bullet, four bullets: `- copies:` (6i.1, 6k: two or more live rows of one agent are an
     exit event and nothing else is done for it; a row the watcher stopped in this round or the one before is not
     counted; a resume that started a copy keeps the copy as the agent's session and stops the original again);
     `- unit end:` (6i.3: line 1 of the record changed and the last call is
     over `handoff_at`: the `unit_end_order`, never in the middle of a unit); `- orders:` (6j, K3: every order ends with
     its Order line and goes by stop and resume; without its `ACK <msg_id>` line after `ack_wait` seconds it is
     resent, at most `ack_resends` times, then the exit event `no ack …`; a fresh session takes the open manager orders
     and supersedes the others, 6k); `- registry:` (6l, 6c: the `registry` file written whole with `os.replace` each
     round and when the watcher returns, read once at start, so a restarted watcher keeps the orders, the revivals
     and the session ids).
  5. `Exit codes:` 0 gains `two live copies of one agent` and `an order with no ACK line after its resends`; 4 becomes
     `a settings file or the extra prompt file changed, or a brief was removed (a changed brief is reloaded)`.
  6. The `Safety:` paragraph: a changed brief is re-hashed and reloaded each round (`control file reloaded: <name>`,
     6f); before each stop and launch the settings files and the extra prompt file are checked again and every brief
     must still exist, else `control file changed: <name>` and exit 4. In the last paragraph, `exits 4 when one
     changed` becomes `exits 4 when a settings file or the extra prompt file changed or a brief is gone`.
  7. One sentence: every log line starts with the UTC minute (`2026-10-29T20:41Z`), and `{time}` in the texts is UTC
     too (6m).

```bash
python3 -I -c "import ast, pathlib, sys; d = ast.get_docstring(ast.parse(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))); print('version 3' in d, '--order' in d, 'ACK <msg_id>' in d, 'registry' in d, 'version 2' in d)" .claude/skills/running-specagent-pipelines/scripts/watch_agents.py
```
Expected: `True True True True False` (ff3354a: `False False False False True`).

- [ ] Step 9: `S/scripts/README.md`: the watcher section and the Config v2 tables (lines at ff3354a). Builder B's file
  (D4) and index-like (Global Constraint 14 at 2fafaa3): a new table row goes at the end of its table, so a merge with
  another lane's rows stays a clean append. The edits, in file order:
  1. Line 11: ``### `watch_agents.py` — the watcher, version 2`` becomes
     ``### `watch_agents.py` — the watcher, version 3`` (`test_docs.py` finds the section by its start).
  2. Line 13: the words ``to stdout, `HH:MM` first.`` become ``to stdout, the UTC minute first (`2026-10-29T20:41Z`).``
  3. After line 16 (the `--check` usage line), inside the code block:
     `python3 -I scripts/watch_agents.py --order <agent> <text> <config>   appends an order to the inbox; runs nothing`
  4. After line 30 (the `- revival:` bullet), these bullets:

```markdown
- the match: an agent's row is the one whose `sessionId` is the session id recorded at its launch, else the one whose
  `id` is the job id `--bg` printed (`claude stop <id>`), else the newest row with its name started at or after its
  launch (`adopted <agent> <id> by name`); a renamed session stays the agent's, a namesake with another id is not.
- copies: two or more live rows of one agent (its name, its job id or one of its session ids) give
  `copies <agent>: <ids>` and exit code 0; nothing else is done for that agent in that round. A row the watcher
  stopped in this round or the one before is not counted (its stop may still be running). A resume the CLI answers
  with `started a copy as <id>` keeps the copy as the agent's session (`copy <agent> <id> kept`; the next round
  matches it by that job id) and stops the original again when the output names it (`claude attach <id>`).
- a changed brief: its new SHA-256 is stored and logged as `control file reloaded: <name>`, and every agent with a
  session whose texts name the file is stopped and resumed with the `reload_order` text (`reload <agent> <name>`);
  the watcher goes on.
- unit end: when line 1 of the record changed (a unit ended) and the last call is over `handoff_at` tokens, the
  `unit_end_order` text orders the hand-over (`unit end <agent> <tokens> tokens; ordered to hand over`); a session in
  the middle of a unit gets no such order (the context cap above still holds).
- orders: every order (the cap's hand-over, the unit end, a reload, the manager's `--order`) ends with the line
  ``Order <msg_id>: append the line `ACK <msg_id>` to <record> before anything else.`` and is sent by stop and resume.
  A line of the record that starts with `ACK <msg_id>` closes it (`ack <agent> <msg_id>`); without one after
  `ack_wait` seconds it is resent (`resent <msg_id> to <agent> (<n> of <ack_resends>)`), and after `ack_resends`
  resends it gives `no ack <agent> <msg_id> after <n> resends` and exit code 0. A fresh session gets the open
  `--order` orders in its prompt; it supersedes the cap's, the unit end's and the reload orders.
- the registry: the `registry` file (default `_control/registry.json`) is written whole at the end of every round and
  when the watcher returns: per agent its `state` (`running`, `stopped`, `blocked`, `done`), lane and settings (from
  `_launch.md` when the run folder has one), line 1 of its record, its session ids, context, calls, cost and orders.
  A restarted watcher reads it once and keeps the orders, the revivals and the session ids
  (`registry: <agent> revivals=<n> orders=<ids>`).
```

  5. The `Safety:` paragraph (lines 32-39). Its first sentence now ends at `the briefs).`: the rest of it, from
     `and checks them again before each stop and launch` to `exits with code 4 instead.`, gives way to the first three
     lines below, and its last sentence, `Code 4 is left for the other control files.`, becomes the last line below:

```markdown
A brief whose hash changed, or one created after the start, is reloaded each round (above). Before each stop and launch
it checks the settings files and the `extra_prompt` file again, and that every brief still exists; on a change it logs
`control file changed: <name>` and exits with code 4 instead.
Code 4 is left for a settings file, the `extra_prompt` file and a removed brief.
```

  6. The `--check` paragraph (lines 41-45) ends with one more sentence: `It reads no registry, merges no inbox, writes
     nothing and matches rows by name only, so its output for the same rows is version 2's.` Then, before the exit
     table, a paragraph of its own (K4):

```markdown
`--order <agent> <text>` is how the manager gives an order: it checks the config as a start does (a config error,
`config error: no agent <agent>` or `config error: empty order`: exit 2, nothing written), appends one line
`{"msg_id", "agent", "text", "at"}` to `orders.jsonl` beside the registry, prints `order <msg_id> <agent>` and the
prompt to send (the text, a blank line, its Order line), runs no `claude` command and exits 0. The manager sends that
prompt itself; the running watcher merges the line in its next round as sent at `at`, waits `ack_wait` seconds for
the `ACK <msg_id>` line and resends by stop and resume.
```

  7. The exit table: row 0 (line 49) and row 4 (lines 53-54, one line from now on) become

```markdown
| 0 | an event: an agent failed or is blocked, `blocked` on line 1 of a `blocked_files` file, every STATUS is final, two live copies of one agent (`copies …`), an order with no `ACK` line after its resends (`no ack …`) |
| 4 | a settings file or the `extra_prompt` file changed, or a brief was removed (a changed brief is reloaded, above); check the change, then restart the watcher: the registry keeps the orders, the revivals and the session ids |
```

  8. `## Config v2`: line 215 (the end of the intro's list of config errors) becomes the first line below and the
     `common` row (line 221) the second; in the `lang` row (line 230) the words `the nudge and the hand-over order`
     become `the nudge, the hand-over, unit-end and reload orders`:

```markdown
`pack: true`, an agent without one of its fields, a role without a fresh text, a `handoff_at` not below `cap` or a `registry` that leaves `run_dir` is a config error (exit 2 at start; a reload keeps such a config out).
| `common` | `[]` | flags for every launch and resume (`--effort max --setting-sources local …`; the model is set in the settings file) |
```

After the `pack` row (line 236, the table's last), these six rows, in this order:

```markdown
| `handoff_at` | `150000` | context tokens of the last call past which the end of a unit orders a hand-over; below `cap` |
| `ack_wait` | `900` | seconds an order waits for its `ACK <msg_id>` line before it is resent |
| `ack_resends` | `2` | resends of an order without its `ACK` line; then `no ack …` and exit code 0 |
| `registry` | `"_control/registry.json"` | the registry file in `run_dir`; `orders.jsonl`, the inbox of `--order`, lies beside it; a path that leaves `run_dir` is a config error |
| `unit_end_order` | the code's text | the prompt that resumes a session at a unit's end past `handoff_at`; `{run}` and `{at}` filled in |
| `reload_order` | the code's text | the prompt that resumes a session after a brief its texts name changed; `{file}` and `{time}` (UTC) filled in |
```

`test_docs.py` pins: the section by its heading's start, a `python3 -I scripts/watch_agents.py` line, `--order` in the
section (`options()` reads every `add_argument` call, a group's too, `test_docs.py:76-88`), the rows `| 0 |` to
`| 4 |`, and under `## Config v2` every key of `DEFAULTS` in backticks, with the row form ``| `<key>` | `<json>` |``
for a default of at most 60 JSON characters (`test_docs.py:110-116`): the first four rows above.

```bash
(ulimit -v 8388608; timeout -k 10 120 uv run pytest -q -p no:cacheprovider .claude/skills/running-specagent-pipelines/scripts/tests/test_docs.py)
```
Expected: `9 passed`. Before this step (after Steps 6-7) `2 failed, 7 passed`, computed from the tests' code:
`test_every_option_a_script_parses_is_in_its_section` (`--order`) and
`test_the_readme_documents_every_field_of_a_v2_config_and_the_short_defaults` (the six keys).

- [ ] Step 10: The full checks, in builder B's worktree.

```bash
(ulimit -v 8388608; timeout -k 10 300 uv run pytest -q -p no:cacheprovider .claude/skills/running-specagent-pipelines/scripts/tests)
```
Expected: `183 passed` (the 146 of ff3354a and the 37 new cases of Steps 4-5; the test of Step 3 keeps its two cases).

```bash
COLUMNS=100 python3 -I .claude/skills/running-specagent-pipelines/scripts/watch_agents.py --help | grep -c -- '--order AGENT TEXT'
```
Expected: `2`: the usage line `usage: watch_agents.py [-h] [--check | --order AGENT TEXT] config [rounds]` and the
option's own line. The help text of `--order` is `append an order for AGENT to the inbox and print its prompt; runs
no session`; `--check` keeps its text (ff3354a :700). Measured on an argparse copy of rule 6a with these texts
(`scratch/planner-c/argparse_v3.py`, Python 3.12.3): `2` at `COLUMNS=100` and at `COLUMNS=40`.

```bash
command -v just && just lint
```
Expected: `/home/tite/.local/bin/just` (lessons.md "Read first" 4); just echoes the recipe line
`uv run ruff check . && uv run ruff format --check .` (`justfile:9-10`); then `All checks passed!` and
`196 files already formatted` (measured on the plan branch, whose Python files are ff3354a's; Task 2 adds no Python
file; no `Would reformat`).

```bash
LC_ALL=C.UTF-8 grep -nP '[\x{10A0}-\x{10FF}\x{1C90}-\x{1CBF}\x{2D00}-\x{2D2F}]' .claude/skills/running-specagent-pipelines/scripts/watch_agents.py .claude/skills/running-specagent-pipelines/scripts/tests/test_watch_agents.py .claude/skills/running-specagent-pipelines/example/agents.json .claude/skills/running-specagent-pipelines/example/agents-judge.json .claude/skills/running-specagent-pipelines/scripts/README.md; echo "exit $?"
```
Expected: `exit 1` and no line before it (D1; a test that needs a letter of a refused block builds it with `chr()`). The same
pattern counts 1 on a scratch line built with `chr(0x10D0)`, so it can find one.

```bash
git -C /home/tite/Desktop/agentic-flow-template/manager-build-b grep -ln -e 'watch_agents' -e 'agents-judge' -e 'agents\.json' -- packages ops; echo "exit $?"
```
Expected: `packages/harness/tests/test_pipeline_report.py` and `exit 0`: that file's line 41 is a docstring naming a
run folder's `_agents.json`; no test outside the skill reads the five files, so the repository's whole suite
(`just test`) is left to the milestone run (D5, the verifier).

```bash
git -C /home/tite/Desktop/agentic-flow-template/manager-build-b status --short
```
Expected: the five files and nothing else:
```
 M .claude/skills/running-specagent-pipelines/example/agents-judge.json
 M .claude/skills/running-specagent-pipelines/example/agents.json
 M .claude/skills/running-specagent-pipelines/scripts/README.md
 M .claude/skills/running-specagent-pipelines/scripts/tests/test_watch_agents.py
 M .claude/skills/running-specagent-pipelines/scripts/watch_agents.py
```
Before the commit, go through `lessons.md` "Known error classes" and "Lessons from this run" (first-pass rule 2): the
watcher class (the last line of "Known error classes") is what this task's tests pin, and the 50-line class is
`test_every_function_of_the_watcher_is_under_50_lines`.

- [ ] Step 11: Commit, in `/home/tite/Desktop/agentic-flow-template/manager-build-b` on `feat/manager-build-b`, with the
  pathspec (Global Constraint 12: one commit per task, the body naming the spec items and the acceptance checks).

```bash
git -C /home/tite/Desktop/agentic-flow-template/manager-build-b add -- .claude/skills/running-specagent-pipelines/scripts/watch_agents.py .claude/skills/running-specagent-pipelines/scripts/tests/test_watch_agents.py .claude/skills/running-specagent-pipelines/example/agents.json .claude/skills/running-specagent-pipelines/example/agents-judge.json .claude/skills/running-specagent-pipelines/scripts/README.md
git -C /home/tite/Desktop/agentic-flow-template/manager-build-b commit -m "feat(manager): Task 2 — the watcher v3: reload, id match, ACK lines, the registry, restart without loss, one session per role" -m "Spec section 6, needs 1 (the registry), 3 (a restart without losing orders) and 5 (one session per role after a stop and resume); 8.1.4; the owner's plan of 2026-10-29: briefs reloaded instead of exit 4, sessions matched by the id recorded at launch, an ACK <msg_id> line for every order with resends by stop and resume, the hand-over at a unit's end past 150k and never in the middle of one. Acceptance: 10.5 (first clause), 10.8 (first two clauses), 10.15, 10.20 (the watcher's log)." -- .claude/skills/running-specagent-pipelines/scripts/watch_agents.py .claude/skills/running-specagent-pipelines/scripts/tests/test_watch_agents.py .claude/skills/running-specagent-pipelines/example/agents.json .claude/skills/running-specagent-pipelines/example/agents-judge.json .claude/skills/running-specagent-pipelines/scripts/README.md
git -C /home/tite/Desktop/agentic-flow-template/manager-build-b show --stat --format=%s HEAD
```
Expected: the subject line, then the five files and `5 files changed`; nothing else in the commit. Then append
`Task 2: done — <sha>` to `/home/tite/Desktop/agent-system-run/manager-build-2026-10-29/build-log-b.md`; the main
session merges lane b where the index says (Task 5 depends on Task 2). Task 2 adds no wiki page, decision page,
`.summary.md`, `docs/llms.txt` or `wiki/index.md` line: builder B does not write `wiki/` or `docs/` (lessons.md
20:36 UTC, C5, C8); its decision goes to Task 11 below.

## For Task 11

- Decision 10a: slug `control-plane-in-the-skill`, title "The control plane lives in the skill". Decision: the
  registry, the record monitor and the owner's surface are files in the run folder (`_control/registry.json`,
  `_control/orders.jsonl`, `_control/monitor.json`) written by the skill's scripts (standard library only); the
  harness's `state.json`, `harness poll` and `statusline.py` are not extended to skill runs. Evidence: spec question 10
  (decided (a), owner, 17:03 UTC; (b) fell with question 1, which chose the skill), spec section 6 needs 1, 3, 5,
  `S/scripts/watch_agents.py` v3 (the registry, `--order`) and `S/scripts/tests/test_watch_agents.py`. Its task: 2.
- K7: the example configs' `settings` values move to `_control/<role>-settings.json` in Task 11, after
  `Merged: a+b+c+d`, with the tests that read them (`test_docs.py:126-127` writes each file at
  `run / agent["settings"]`, so a `_control/` value needs that folder made first) and the README's `settings` row.
- Tracker rows: Task 2 closes none. Its Deferred items below become rows (index, the tracker row of the Coverage table).

## Deferred

1. A live check of the `--bg` output forms the watcher parses (`claude stop <id>`, `a copy as <id>`, `claude attach
   <id>` … `opens the original`): v2 logs only the last 80 characters of a launch's output (`watch_agents.py:665`), so
   the tests use the logged tails (`/home/tite/vault/context/measurements/2026-10-25-jobs-tmp-and-run-logs.md:26-29`;
   this run's `_watch.log`, 2026-10-29) and the CLI binary's text quoted in template-core's CLI facts; a planner
   cannot start a session, and the next run's watcher log shows the whole outputs.
2. 10.5 and 10.8 live, on the next run: the stub tests here prove the rules; the verifier's milestone run and the next
   run's `claude agents --json --all` show one running session per role name after a stop and resume.
3. `--session-id` at launch (Departure 3).
4. The registry fields beyond need 1 that Task 5's surface may want (for example the budget left per agent): Task 5
   reads what K1 gives and lists what it lacks under its own Deferred.
5. A brief changed while a fresh launch's stop runs: the fresh session reads the new text at start, and the next round
   still gives it a reload order (one redundant re-read: a stop and a resume). Skipping a session launched after the
   file's mtime needs a test of its own; a later version may add it.

## Verified

At ff3354a unless a line names another tree; the skill's files are the same blobs on e32d413, builder B's base, and
the plan branch's Python files are ff3354a's.

- `S/scripts/watch_agents.py`, 739 lines: the docstring :2-62 (usage :6-8, `Exit codes:` :31-33, `Safety:` :34-39),
  `DEFAULTS` :152, `RUN_STATE` :176, `BRIEF` :177, `STRING`/`NUMBER` :187-188, `TYPES` :191, `check_types` :228, `log`
  :235, `sha256` :247-251 (None on `OSError`), the `leaves run_dir` check :386, `control_files` :403-411, `changed`
  :413-418, `reload` :420-438, `latest_rows` :450-468, `note_from` :470-477, `seed` :479-491, `round` :493-516, `agent`
  :518-600 (83 lines), `act` :639-665 (`Exit(4)` :645, :663), `command` :667-686, `main` :698 (argparse :699-702:
  `--check`, `config`, `rounds` default 240).
- `.claude/rules/python.md:9`: every function under 50 lines.
- `S/scripts/tests/test_watch_agents.py`: 41 cases, `41 passed`; `row()` :50 (`id` = `sid[:8]`), the stub's launch
  output :41 (`s 12345678      show recent output`), the cap tests :462 (300k) and :468 (200k only), the `lang` ending
  :247.
- `S/scripts/tests/test_docs.py`: 9 tests, `9 passed`; `options()` :76-88 (ast: every `.add_argument` call, a group's
  too), :90-94 (a section and a `python3 -I scripts/<name>` line per script), :96-102 (every option in its section),
  :105-107 (rows `| 0 |` to `| 4 |`), :110-116 (every field in backticks under `## Config v2`; the row form for a
  default of at most 60 JSON characters), :118-137 (the example config under `--check`).
- `S/scripts/tests/test_skill_example.py`: 9 tests, `9 passed`. The skill suite: `146 passed` (Step 1).
- `S/scripts/README.md`: the heading :11, `` `HH:MM` first `` :13, usage :15-16, `- revival:` :30, `Safety:` :32-39,
  `--check` :41-45, the exit table :47-54 (row 4 over :53-54), `## Config v2` :212, the config errors :214-215,
  `common` :221, `lang` :230, `handoff_order` :232, `pack` :236 (the table's last row).
- `S/example/agents.json`: `"--model"` and `"opus"` :5-6, `"cap": 200000,` :23, `"nudges": 6,` :27;
  `S/example/agents-judge.json` :5-6; the `grep -c` of Step 7 gives 2 and 2.
- `S/references/sandbox-and-blindness.md:5`: the model is set in the settings file.
- The spec: 10.5 :1099, 10.8 :1106, 10.15 :1123-1125, 10.20 :1135-1136. The index: Global Constraint 12
  (`00-index.md:64-65`), Task 2's row :102 (`scripts/migrate_agents_json.py` only if the config form changes:
  Departure 2).
- `justfile:9-10`: `lint` = `uv run ruff check . && uv run ruff format --check .`; `command -v just` =
  `/home/tite/.local/bin/just`; `just lint` on the plan branch at 4811358: `All checks passed!`,
  `196 files already formatted`. `pyproject.toml:25`: `testpaths` = `packages`, the skill's tests, `ops/tests`.
- No test outside the skill reads the five files: `git grep -ln -e 'watch_agents' -e 'agents-judge' -e 'agents\.json'
  -- packages ops` prints only `packages/harness/tests/test_pipeline_report.py`, whose :41 is a docstring naming a run
  folder's `_agents.json`; `ops/tests/test_ecc_pins.py:288-300` reads `SKILL.md` and `example/common.md` only.
- The scratch copy (`scratch/planner-c/skill-copy`, built by `build_copy.py` from the plan's HEAD with Steps 2-5): on
  v2, `32 failed, 44 passed` before C500/C501; after them (`scratch/plan-fixer/t2/skill-copy`, the same script),
  `34 failed, 44 passed`; with `-k 'not example_configs_name_no_model'`, `33 failed, 44 passed, 1 deselected`;
  the wrong versions of Step 6 red (`wrong_versions.py`); `ruff check` and `ruff format --check` clean (28 files).
- Step 7's edits on a copy with v2's code (`scratch/planner-c/step7_copy.py`, `skill-copy7`): both files parse; the
  `grep -c` gives 0 and 0 with exit 1; `test_skill_example.py` and the example-configs test give `10 passed`;
  `test_docs.py`'s example test fails with `config error: unknown fields ack_resends, ack_wait, handoff_at`.
- argparse, Python 3.12.3 (`scratch/planner-c/argparse_v3.py`): a mutually exclusive group gives exit 2 and
  `argument --order: not allowed with argument --check`; `--order AGENT TEXT` is on two lines of `--help` at
  `COLUMNS=100` and at `COLUMNS=40` (argparse takes its width from `shutil.get_terminal_size()`, which reads
  `COLUMNS`; Python 3.12 docs, `shutil.get_terminal_size`).
- Step 8's docstring check at ff3354a prints `False False False False True`.
- `secrets.token_hex(4)`: 8 lowercase hex digits (run); `os.replace` replaces the target atomically on POSIX
  (Python 3.12 docs, `os.replace`).
- `LC_ALL=C.UTF-8 grep -nP '[\x{10A0}-\x{10FF}\x{1C90}-\x{1CBF}\x{2D00}-\x{2D2F}]'` on the five files: exit 1; on
  `scratch/planner-c/geo.txt` (a line built with `chr(0x10D0)`): count 1.
- pytest's `-k` filter: the summary counts the filtered test as `1 deselected` (measured above).
- C500 (plan fixer): this run's `_watch.log` (`:1` to `:69`, 2026-10-29): all 17 cap orders logged
  ``so this started a copy as <id>. `claude attach <id>` opens the original.``, each followed by the role's note and
  its fresh session; the CLI's text, template-core
  `scratch/critic/t04/ctx/context/fix-20261004/claude-code-facts/01-claude-code-behaviour-the-fix-waves-rely-on-2-1.md:25-27`
  (``note: session <id> is already running in the background, so this started a copy as <new id>. `claude attach <id>`
  opens the original.`` and ``<id> is open in another Claude Code process, so this started a copy as <new id>.``);
  v2 stops with `check=False` and ignores the output (`watch_agents.py:659`), so a second stop of a stopping session
  changes nothing for the watcher; `S/SKILL.md:104-105`: "The conversation is kept; the job id may change."
- C501 (plan fixer): v2 reads a final line by its start, `watch_agents.py:514` (every STATUS final) and `:521` (no
  action for a final agent).
