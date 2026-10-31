# Task 4 — The planner answers its findings; the fixer on demand

builder: a
depends_on: 2, 3
milestone: M2

## Goal
The planner answers every open id of its own tasks after each part it writes, so the file it just wrote is answered
from the context that holds it. The plan fixer stays a role but is launched by the watcher only when the open ids of
its parity pass a count or an age, is stopped when none is open, and is not revived when its STATUS is done.

**Files (under `.claude/skills/running-specagent-pipelines/`):**
- Modify: `scripts/watch_agents.py` (`AGENT_TYPES` and two new constants, `read_config`, `blank`, `agent`, a new
  `demand`, `final`, `handoff_note`, `revive`, `act`, `entry`, `restore`, the module docstring),
  `scripts/check_formats.py` (a new `twice_errors`, `main`, the docstring), `scripts/tests/test_watch_agents.py`,
  `scripts/tests/test_check_formats.py`, `scripts/tests/test_skill_example.py` (the pin at `:48`, `WAITERS` at `:249-252`)
- Modify: `SKILL.md` (`:44-46`), `example/agents.json`, `example/README.md`, `example/planner-assignment.md`,
  `example/plan-fixer-assignment.md`, `example/common.md` (`:34-35`, "Waiting"), `example/launch.md` (one line under
  the table), `scripts/README.md`, `scripts/docs/watch_agents.md`, `scripts/docs/check_formats.md`
- Create (repository): `wiki/decisions/planner-answers-its-findings-fixer-on-demand.md`,
  `wiki/decisions/planner-answers-its-findings-fixer-on-demand.summary.md`
- Modify (repository): `wiki/index.md` (one line at the end of `## Decisions`), `wiki/log.md` (one section at the end)

**Interfaces** (lines are lane a's at 30c7ad5, whose skill folder is 678b187's):
- Consumes: Task 2's `open_ids.open_ids(run, kinds, parity=None, task=None, cause=None)` (`open_ids.py:42-59`, a list;
  `cause="plan"` drops a `(code)` V or R); in `watch_agents.py`: `launch_fresh` (`:984-995`), `act` (`:1001-1031`),
  `stop` (`:1033-1036`), `revive` (`:890-900`), `handoff_note` (`:802-821`, its exit-3 branch `:812-817`), `agent`
  (`:714-732`), `final` (`:734-736`), the registry entry (`blank` `:396-406`, `entry` `:1153-1184`, `restore`
  `:1208-1234`), `AGENT_TYPES` (`:302-310`), `check_types` (`:323-327`), `NUMBER` (`:276`).
- Produces: the optional agent fields `on_demand` (a boolean, default false) and `demand` (an object; `demand` needs
  `on_demand`): `kinds` (a list of `C`, `A`, `B`, `V`, `R`), `cause` (`"plan"` or `"any"`; `"any"` is `cause=None`),
  `parity` (`"odd"`, `"even"` or `"all"`; `"all"` is `parity=None`), `queue` (a positive integer), `wait_minutes` (a
  non-negative number); a key left out takes `DEMAND_DEFAULTS = {"kinds": ["C", "A", "B", "V", "R"], "cause": "plan",
  "parity": "all", "queue": 6, "wait_minutes": 45}`; the agent's own `first_seen` in its registry entry (`{id: UTC
  time}`); the log lines `demand <agent>: <n> open ids, oldest <m> min; launched`, `demand <agent>: queue empty,
  stopped` and `demand <agent>: done, not revived`; `check_formats.py`'s error `critique-response.md:<line>: <id>
  answered twice`.

## The rule
An agent with `on_demand` is launched by the watcher alone, never by the manager at the start (`example/launch.md`
says so under its table; the watcher's `start`, `:1236-1240`, launches nothing and stays as it is). The spec's
`fixer_queue` and `fixer_wait_minutes` (`docs/design-docs/pipeline-fold.md:85-88`) are its `demand.queue` and
`demand.wait_minutes`, per agent, so two fixers by parity keep their own (A12). Each round, in `agent` before its
`if row is None` branch (`:722`), `demand(name, row, events)`:
1. `open_ids(run, kinds, parity, cause)` gives the open ids; the agent's own `first_seen` gains each new one at now
   and drops each one no longer open.
2. Busy (the row has a pid and the agent is not final): nothing more; the cap, the note and the budget apply to it as
   to any role.
3. Not busy, ids open, and `len(open) >= queue` or the oldest first seen `wait_minutes` ago or earlier:
   `launch_fresh` with the role's `fresh` text and the why `demand <agent>: <n> open ids, oldest <m> min; launched`
   (`<m>` whole minutes, rounded down); a row with an id is stopped first, as `act` does; no row stops nothing. The
   turn ends.
4. Not busy, nothing open, and a row with a pid (a final session at its prompt): stop its job and log
   `demand <agent>: queue empty, stopped` (spec `:88`: the watcher "stops it when the queue is empty"). The turn ends.

Final, for an on-demand agent: line 1 starts with its `final` and the status file was written at or after the
session's launch (`launched_at`, `:1043`); with no `launched_at` (a session this watcher did not launch) line 1 alone
decides, as today. A relaunched fixer whose line 1 still says the last session's `STATUS: done` is live until it
writes (C19). An on-demand agent is never revived: `revive` launches nothing and logs `demand <agent>: done, not
revived` once per session. A note whose `work_check` exits 3 stops the session, for every role (R6 of Task 2's diff:
a session left live at its note wakes on a waiter or a message in its old context, past any cap, and an on-demand
agent with a live row is never "not busy"); an on-demand agent's note is not kept as `idle` either, so the idle
re-check (`:779-782`) never relaunches it below its queue: only `demand` launches it (C20). Under `--check` both
stops are said, not done (`would stop <id>`). An agent without `on_demand` (also one a reload stripped of it,
`RUN_STATE` `:242-258`, lesson 07:07Z B2) keeps an empty `first_seen`.

- [ ] **Step 1: Write the failing tests**

Append to `scripts/tests/test_watch_agents.py`, after its last test (it imports `json` `:11`, `time` `:17` and
`pytest` `:19`, and defines `SID2` `:23`, `ORDER` `:25`, `row` `:73`, `Pipeline` `:96`, `utc` `:250`, `seconds`
`:254` and `registry` `:258`):

```python
def fixer(p: Pipeline, **fields) -> None:
    """t/plan-fixer on demand, `fields` added to its entry, with a fresh text of its own and line 1 `STATUS: fixing`."""
    p.config["agents"]["t/plan-fixer"] = {**p.agent("plan-fixer", "fixer-log.md"), "on_demand": True, **fields}
    p.config["fresh"] = {"plan-fixer": "Fixer: answer the open ids. {run}"}
    p.write("fixer-log.md", "STATUS: fixing\n")


def bump(p: Pipeline, name: str, ident: str, ago: int) -> None:
    """The registry as a watcher that first saw `ident` `ago` seconds earlier left it."""
    data = registry(p)
    seen = data["roles"][name]["first_seen"]
    seen[ident] = utc(seconds(seen[ident]) - ago)
    (p.run / "_control" / "registry.json").write_text(json.dumps(data), encoding="utf-8")


def critique(*idents: str, task: int = 1) -> str:
    """critique.md with `idents` filed under `## Task <task>`."""
    return f"STATUS: reviewed through Task {task}\n## Task {task}\n" + "".join(f"#### {i} — t\n" for i in idents)


def test_an_on_demand_agent_is_not_launched_at_start_or_revived(p):
    fixer(p)
    stopped = row(name="t/plan-fixer", sid=SID2, state="stopped", status=None, pid=None)
    p.rounds([row()], [row(), stopped])
    r = p.watch(rounds=2)
    assert p.launches() == [] and "demand t/plan-fixer: done, not revived" in r.stdout


def test_the_demand_queue_launches_the_fixer_once_with_its_fresh_text(p):
    fixer(p, demand={"kinds": ["C", "A"], "parity": "all", "queue": 2, "wait_minutes": 45})
    p.write("critique.md", critique("C1", "C2"))
    p.write("critique-response.md", "STATUS: writing Task 2\n")
    p.rounds([row()], [row(), row(name="t/plan-fixer", sid=SID2, age=0)])
    r = p.watch(rounds=2)
    [launch] = p.launches()
    assert "demand t/plan-fixer: 2 open ids, oldest 0 min; launched" in r.stdout and p.stops() == []
    assert launch["argv"][-1].startswith("Fixer: answer the open ids. ") and "{run}" not in launch["argv"][-1]


def test_the_demand_age_launches_the_fixer_after_wait_minutes(p):
    fixer(p, demand={"kinds": ["C"], "queue": 10, "wait_minutes": 1})
    p.write("critique.md", critique("C1"))
    p.watch(rounds=1)
    assert p.launches() == []
    bump(p, "t/plan-fixer", "C1", 120)
    r = p.watch(rounds=1)
    assert len(p.launches()) == 1 and "demand t/plan-fixer: 1 open ids, oldest 2 min; launched" in r.stdout


def test_answered_ids_leave_the_demand_queue_and_first_seen(p):
    fixer(p, demand={"kinds": ["C"], "queue": 3})
    p.write("critique.md", critique("C1", "C2"))
    p.watch(rounds=1)
    assert sorted(registry(p)["roles"]["t/plan-fixer"]["first_seen"]) == ["C1", "C2"]
    p.write("critique-response.md", "STATUS: writing Task 2\nC1: applied — x\nC2: rejected — y\n")
    p.watch(rounds=1)
    assert registry(p)["roles"]["t/plan-fixer"]["first_seen"] == {} and p.launches() == []


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"demand": {"queue": 1}}, "t/plan-fixer: demand needs on_demand"),
        ({"on_demand": True, "demand": {"queue": "6"}}, "t/plan-fixer: demand.queue is not a positive integer"),
        ({"on_demand": True, "demand": {"size": 6}}, "t/plan-fixer: unknown demand fields size"),
    ],
)
def test_the_demand_fields_are_checked_before_any_claude_command(p, fields, message):
    p.config["agents"]["t/plan-fixer"] = {**p.agent("plan-fixer", "fixer-log.md"), **fields}
    r = p.watch(rounds=1)
    assert r.returncode == 2 and f"config error: {message}" in r.stdout and p.calls() == []


def test_the_demand_defaults_count_every_kind_and_drop_code_findings(p):
    fixer(p)
    p.write("critique.md", critique("C1", "C2", "A1"))
    p.write("build-log.md", "STATUS: building Task 3\nB1: sent to plan-fixer — the plan names a missing file\n")
    p.write("verify.md", "STATUS: verifying Task 2\n## Task 1\n#### V1 — (plan) major: x\n#### V2 — (code) minor: y\n")
    sixth = {str(p.run / "critique.md"): critique("C1", "C2", "C3", "A1")}
    p.rounds([row()], {"rows": [row()], "write": sixth})
    r = p.watch(rounds=2)
    assert len(p.launches()) == 1 and "demand t/plan-fixer: 6 open ids, oldest 0 min; launched" in r.stdout


def test_an_idle_on_demand_fixer_is_stopped_and_not_relaunched_below_the_demand_queue(p):
    check = ["python3", "{skill}/open_ids.py", "{run}", "--kind", "C,A", "--cause", "plan"]
    fixer(p, demand={"kinds": ["C", "A"], "queue": 6, "wait_minutes": 45}, work_check=check)
    p.transcript(sid=SID2)
    p.write("handoff-plan-fixer.md", "HANDOFF plan-fixer after Task 1 — 2026-10-30 07:00\n", mtime=time.time() - 120)
    live = row(name="t/plan-fixer", sid=SID2)
    stopped = row(name="t/plan-fixer", sid=SID2, state="stopped", status=None, pid=None)
    p.rounds([row(), live], {"rows": [row(), stopped], "write": {str(p.run / "critique.md"): critique("C1")}})
    r = p.watch(rounds=2)
    assert "idle t/plan-fixer: nothing to take" in r.stdout and p.stops() == [SID2[:8]]
    assert p.launches() == [] and "fresh t/plan-fixer after idle" not in r.stdout


def test_two_on_demand_fixers_by_parity_keep_their_own_first_seen(p):
    fixer(p, demand={"kinds": ["C"], "parity": "odd"})
    p.config["agents"]["t/plan-fixer-b"] = {
        **p.agent("plan-fixer-b", "fixer-log-b.md"),
        "on_demand": True,
        "demand": {"kinds": ["C"], "parity": "even"},
    }
    p.config["fresh"]["plan-fixer-b"] = "Fixer b: answer the open ids."
    p.write("fixer-log-b.md", "STATUS: fixing\n")
    p.write("critique.md", critique("C1", task=2))
    p.watch(rounds=1)
    bump(p, "t/plan-fixer-b", "C1", 50 * 60)
    r = p.watch(rounds=1)
    [launch] = p.launches()
    assert launch["argv"][launch["argv"].index("--name") + 1] == "t/plan-fixer-b"
    assert "demand t/plan-fixer-b: 1 open ids, oldest 50 min; launched" in r.stdout
    assert registry(p)["roles"]["t/plan-fixer"]["first_seen"] == {}


def test_an_on_demand_fixer_launched_after_done_is_capped_like_any_role(p):
    fixer(p, demand={"kinds": ["C"], "queue": 1})
    p.write("fixer-log.md", "STATUS: done\n", mtime=time.time() - 600)
    p.write("critique.md", critique("C1"))
    p.transcript(sid=SID2, context=250_000)
    p.rounds([row()], [row(), row(name="t/plan-fixer", sid=SID2, age=0)])
    r = p.watch(rounds=2)
    fresh, order = p.launches()
    assert fresh["argv"][-1].startswith("Fixer: answer the open ids. ")
    assert order["argv"][:2] == ["--resume", SID2] and order["argv"][-1].startswith(ORDER)
    assert "cap t/plan-fixer 250,000 tokens; ordered to hand over" in r.stdout


def test_a_done_on_demand_fixer_is_stopped_when_its_demand_queue_is_empty(p):
    fixer(p)
    p.write("fixer-log.md", "STATUS: done\n")
    p.rounds([row(), row(name="t/plan-fixer", sid=SID2)])
    r = p.watch(rounds=1)
    assert p.stops() == [SID2[:8]] and p.launches() == []
    assert "demand t/plan-fixer: queue empty, stopped" in r.stdout
```

Append to `scripts/tests/test_check_formats.py`, after its last test (fixture `run` `:22-26`, `write` `:29`, `check`
`:33`):

```python
def test_an_id_answered_twice_in_the_response_file_is_an_error(run):
    write(run, "critique.md", "STATUS: x\n## Task 1\n#### C1 — t\n")
    write(run, "critique-response.md", "STATUS: x\nC1: applied — a\nC1: applied — b\n")
    code, out = check(run)
    assert code == 1 and "critique-response.md:3: C1 answered twice" in out["errors"]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `(cd .claude/skills/running-specagent-pipelines/scripts && python3 -m pytest -q tests/test_watch_agents.py tests/test_check_formats.py -k "demand or answered_twice")`
Expected: 13 failed, 114 deselected (measured on a copy of lane a's skill folder at 678b187 = 30c7ad5; each test a fix
commit on lane a has added since, R6's for one, is one more deselected). Each fails for its own reason: the first, the
base revives the stopped fixer (`p.launches()` is not `[]`); the queue and the defaults tests, no launch (`ValueError`
unpacking `[launch]`; `0 == 1`); the age, answered and parity tests, `KeyError: 'first_seen'`; the three config cases,
no config error (exit 1, not 2); the idle test, the idle re-check relaunches the fixer (with R6's stop already on the
base, its second stop); the cap test, no launch (`ValueError`, 2 expected); the queue-empty test, `p.stops() == []`;
the check_formats test, exit 0.

- [ ] **Step 3: Implement the rule**

`watch_agents.py`:
- `AGENT_TYPES` gains `"on_demand": ("a boolean", lambda v: isinstance(v, bool))` and `"demand": ("an object",
  lambda v: isinstance(v, dict))`, each a `(kind, test)` pair as `check_types` unpacks it (`:323-327`; a bare `bool`
  or `dict` raises `TypeError` on every config load, C9 of Task 2). New `DEMAND_DEFAULTS` (Produces) and
  `DEMAND_TYPES` in the same form: `kinds` `("a list of C, A, B, V or R", ...)` (a non-empty list whose items are
  among the five), `cause` `("plan or any", ...)`, `parity` `("odd, even or all", ...)`, `queue` `("a positive
  integer", ...)` (an `int` that is not a `bool`, above 0), `wait_minutes` `NUMBER`.
- `read_config`, after `check_types(agent, AGENT_TYPES, f"{name}: ")` (`:389`): a `demand` without `on_demand` true
  raises `ConfigError(f"{name}: demand needs on_demand")`; keys outside `DEMAND_DEFAULTS` raise
  `f"{name}: unknown demand fields {', '.join(sorted(keys))}"`; then `check_types(agent.get("demand", {}),
  DEMAND_TYPES, f"{name}: demand.")`. `main` prints them as every config error (`config error: …`, exit 2).
- `blank` (`:396-406`) gains `"first_seen": {}`; `entry` (`:1153-1184`) writes it as `{id: utc(t)}`; `restore`
  (`:1208-1234`) reads it back through `stamp` (`:354`), dropping a value that is not a UTC string; a registry
  without it (an older watcher's, `seed_registry` in the tests) restores `{}`.
- A method `demand(self, name, row, events) -> bool`, called in `agent` before the `if row is None` branch (`:722`):
  a True return skips the branches below it (`track_unit`, `:731-732`, runs as in every turn). It does the rule's
  parts 1-4; for an agent without `on_demand` it only empties `first_seen` and returns False. `import open_ids` at the
  top (`:122` puts the script's folder on `sys.path`, as `check_formats` is imported); the role is
  `name.split("/")[-1]` (`:769`) and its text `self.fresh_text(role)`, as `handoff_note` launches it; the stop of
  part 4 goes through `self.stop` and is said under `--check`, as `act` does.
- `act` (`:1001-1031`) takes `row=None` (a fixer never launched has no row; nothing to stop): `stop and row and
  row.get("id")` at `:1017` and `:1021`.
- `final` (`:734-736`): for an on-demand agent, also the status file's mtime at or after the entry's `launched_at`;
  with `launched_at` None, line 1 alone.
- `handoff_note`'s exit-3 branch (`:812-817`): after the `idle` line, stop the session when its row has an id, as
  `act` does (`self.say(name, f"would stop {row['id']}")` under `--check`, else `self.stop(row["id"])`), for every
  role (R6 of Task 2's diff; when lane a's base already holds R6's fix, this part is in place); for an on-demand agent
  `self.idle[name]` is not set.
- `revive` (`:890-900`): for an on-demand agent, no launch; `self.tell(name, f"demand {name}: done, not revived")`
  once per session id; it returns True.
- The module docstring: after its hand-over bullet (`:30-39`), a bullet `on demand:` with the rule in three lines;
  the hand-over bullet says that exit 3 stops the session (when R6's fix has not said it yet).

`check_formats.py`: a new function `twice_errors(run)` beside `handoff_errors` (`:251`): for each `<id>:` answer line
of `critique-response.md` (`P` lines left out, as `ids` leaves them out at `:191`) whose id was answered on an
earlier line, the error `critique-response.md:<line>: <id> answered twice` (the line from `line_of`, `:135`); `main`
(`:433-467`) lists its errors after `*found["errors"]` (`:453`). `ids` stays as it is: it is 67 lines, the cap its size
test sets (`test_check_formats.py:537`). `findings_report.py` is unchanged (the first answer stands). The docstring's
error list (`:6-14`) gains "an id answered twice in critique-response.md (the first answer stands)".

- [ ] **Step 4: Run them to verify they pass**

Run: `(cd .claude/skills/running-specagent-pipelines/scripts && python3 -m pytest -q tests/test_watch_agents.py tests/test_check_formats.py)`
Expected: 127 passed (`test_watch_agents.py` 91 at 30c7ad5 and Step 1's 12, `test_check_formats.py` 23 and Step 1's 1;
each test a fix commit on lane a has added since, R6's for one, is one more).

- [ ] **Step 5: The briefs and configs**

`example/planner-assignment.md`, "How to work", the bullet at `:45-51`: replace only its first two sentences ("You
only write new tasks (owner, 2026-10-28). `<project>/plan-fixer` answers every C, A, B, R and V id on written tasks
and edits their files; you do not, even when a message asks you.") with: "You write new tasks and answer the open ids
of your own tasks (owner, 2026-10-30): after every `Task N: part <k>` or `Task N: written — <sha>` line, before the
next part, run `python3 -I <skill-dir>/scripts/open_ids.py <run-dir> --kind C,A,B,V,R --cause plan` (with two
planners add `--parity odd|even`, your lane's) and answer each id it prints that is filed under a task of yours: fix
the task file (unbuilt tasks only; a built task's code is the truth: fix the later tasks it touches), append
`<id>: applied|rejected|decided by rule — …` to `critique-response.md` with `printf … >>`, commit with a pathspec and
message the asker. `<project>/plan-fixer` is launched by the watcher only when the open ids pass `demand.queue` or
`demand.wait_minutes` of `_agents.json`; while it runs it answers the ids of its parity and you write on." The next
sentence keeps its carry rule (C21) with three words added: "for answer lines added since your last task (the
fixer's too)"; the commit sentence stays. The bullet at `:57-58` becomes (C18): "When the last task file is written
and committed: line 1 of `critique-response.md` = `STATUS: plan complete`. Then wait in the background with
`python3 <run-dir>/wait_for_log.py <run-dir>/critique.md <lines>` (its line count; again after each exit) until its
line 1 says `STATUS: reviewed through Task <last>` or `STATUS: done`, answer what `open_ids.py` prints for your tasks
as above, set line 1 of `critique-response.md` to `STATUS: done` and end; later B, `(plan)` V and R ids are the plan
fixer's, launched on demand." "Done when" (`:64-68`): "every task is written (the fixer closes the ids),
`critique-response.md` line 1 says `STATUS: plan complete`" becomes "every task is written and its open ids are
answered, `critique-response.md` line 1 says `STATUS: done`".

`example/plan-fixer-assignment.md`: "## Why you exist (owner, 2026-10-28)" and its paragraph (`:6-9`) become "## Why
you are launched (owner, 2026-10-30)" with: "The planner answers the open ids of its own tasks after each part it
writes. The watcher launches you only when the open ids of your parity reach `demand.queue` (6) or the oldest is
`demand.wait_minutes` (45) old, in `_agents.json`, and stops you when none is open." Step 1 (`:15-20`): its first
sentence (the four waiters, "one waiter each; you are woken by the first that exits") becomes "First set line 1 of
`<run-dir>/fixer-log.md` to `STATUS: fixing`. You are launched when ids wait, so start no waiter: collect them with
`python3 -I <skill-dir>/scripts/open_ids.py <run-dir> --kind C,A,B,V,R --cause plan` (with `--parity odd|even` when
your `demand.parity` is set)"; the list of where ids are filed stays. Step 4 (`:35-37`) becomes (C20): "One batch
(every id waiting when you were launched) per session. Then run `open_ids.py` again: when it prints nothing for your
parity, set line 1 of `fixer-log.md` to `STATUS: done` and end, with no hand-over note (the watcher stops you and
launches you again when the queue or the age passes); else hand over (`_handoff-rule.md`, role `plan-fixer`)."
`scripts/tests/test_skill_example.py`'s `WAITERS` (`:249-252`) drops its `"plan-fixer-assignment.md"` entry: the test
fullmatches each listed command against a waiter span of the brief (`:260-273`), and the fixer's brief names none now.
It gains the planner's new waiter (C18): `"planner-assignment.md": ["python3 /r/wait_for_log.py /r/critique.md 13"]`.

`example/common.md` (C17): `:34-35`'s "a planner that only writes new tasks and a plan fixer that answers every
finding on written tasks" becomes "a planner that writes new tasks and answers the open ids of its own tasks after
each part, and a plan fixer that the watcher launches on demand, by queue or age", and the pin at
`scripts/tests/test_skill_example.py:48` the same new words (the test joins the brief's whitespace, `:78`).
"Waiting" (`:77-80`) gains: "The planner and the plan fixer find open ids with `python3 -I
<skill-dir>/scripts/open_ids.py <run-dir> --kind C,A,B,V,R --cause plan` (exit 0 and the ids when some wait, exit 3
when none) instead of a waiter." `SKILL.md` `:44-46` becomes: "The planner writes new tasks (files, signatures, the
tests in full, the commands with `Expected:` lines) and answers the open ids of its own tasks after each part. The
plan fixer, launched by the watcher on demand (by queue or age), answers every C, A, B and `(plan)` V id on written
tasks in `critique-response.md` and edits unbuilt task files; the code of a built task is the truth."
`example/README.md` `:41-42`: "the planner, who writes new tasks and answers the open ids of its own tasks after each
part (optional lanes)" and "the plan fixer, launched by the watcher on demand when the open ids pass a count or an
age"; after the `work_check` paragraph (`:28-30`) one sentence on the plan fixer's `on_demand` and `demand` (the
defaults 6 and 45; stopped when none is open). `example/launch.md` (C16), after the table (`:25`) and its blank line,
before `Yes:`: "The plan fixer's row is launched by the watcher on demand (`on_demand` in `_agents.json`), never at
the start: the manager launches every other row." (preflight reads the table up to its first non-`|` line, and the
three example tests of `test_preflight.py` pass with it). `example/agents.json`, the plan-fixer entry (`:58`): gains
`"on_demand": true, "demand": {"kinds": ["C", "A", "B", "V", "R"], "cause": "plan", "parity": "all", "queue": 6,
"wait_minutes": 45}`, its `work_check` kept. `scripts/README.md`: after the `work_check` row (`:94`), the rows
`on_demand` and `demand` (the defaults; `demand` needs `on_demand`; see the watcher's page).
`scripts/docs/watch_agents.md`: after the hand-over paragraph (`:15-19`, which says exit 3 stops the session when
R6's fix has not said it yet), the rule. `scripts/docs/check_formats.md` (`:6-8`): an id answered twice in
`critique-response.md` (the first answer stands).

The decision page (spec Decided 2, `docs/design-docs/pipeline-fold.md:78-89`; one decision per page, in the commit
with its code, `_common.md`, "Documentation with the code"): `wiki/decisions/planner-answers-its-findings-fixer-on-demand.md`,
titled "The planner answers its own findings; the fixer is launched on demand", front matter with the keys of
`wiki/decisions/skill-script-pages.md:1-13` (`type: decision`, `status: draft`, `decided: 2026-10-30`, `by: owner`,
`decision_status: decided`, `scope: global`); the decision: the planner answers the open ids of its own tasks after
each part it writes, and the watcher launches the plan fixer only when the open ids pass `demand.queue` or
`demand.wait_minutes`, stops it when its queue is empty, and never revives it; `why` from the spec's Intent (`:8-25`);
`would_change_if` from Measurement 3 (`:147-148`: the measurement run loses quality and this pair is unfolded); under
12,000 bytes. Its `.summary.md`: four lines, the first `Decision (owner, 2026-10-30): ...`. `wiki/index.md`: one line
at the end of `## Decisions` (after `:43`), in its form. `wiki/log.md`: a section at the end in the form of
`wiki/log.md:73-76`: `## 2026-10-30 pages written with Task 4 of the pipeline-fold run`, `- commit: Task 4 of the
pipeline-fold run`, `- created: decisions/planner-answers-its-findings-fixer-on-demand.md`, `- updated: index.md`.
Both files are index-like: a task appends its own lines at the end and never reorders another task's (the rule of the
manager-build run, `lessons.md`, 22:45 UTC).

Run: `(cd .claude/skills/running-specagent-pipelines/scripts && python3 -m pytest -q tests/test_docs.py tests/test_skill_example.py tests/test_preflight.py)`; then at the repository
root `wc -c wiki/decisions/planner-answers-its-findings-fixer-on-demand*.md`;
`grep -c 'decisions/planner-answers-its-findings-fixer-on-demand.md' wiki/index.md wiki/log.md`
Expected: 64 passed (8 + 12 + 44 at 30c7ad5: the pin at `:48` and `WAITERS` change, no test is added); each page under 12,000
bytes; `wiki/index.md:1`, `wiki/log.md:1`.

- [ ] **Step 6: Ruff, once, and commit**

Run: `uv run ruff check .`; `uv run ruff format --check .`
Expected: clean.
Checks once each (`_common.md`, "Checks once each"): the full suites (`uv run pytest -q`, `just validate`, `uv run harness
docs-check`, `uv run harness wiki-lint`) are the verifier's at M2, not this task's; for this task this replaces the
index's Global Constraints line on them (`00-index.md:28-29`).

```bash
git add .claude/skills/running-specagent-pipelines wiki/decisions/planner-answers-its-findings-fixer-on-demand.md \
  wiki/decisions/planner-answers-its-findings-fixer-on-demand.summary.md wiki/index.md wiki/log.md
git commit -m "feat(template): Task 4 — The planner answers its findings; the fixer on demand"
```
(the commit form of the builder's assignment, B1 of `build-log.md`)

## Verified (plan fixer, C15-C21, A10-A13, R6; lane a at 30c7ad5, skill folder = 678b187)
- Step 1's 13 tests spliced into a copy of the skill's `scripts/`: `-k "demand or answered_twice"` 13 failed, 114
  deselected, each for the reason Step 2 names; `ruff format --check` and `ruff check` clean on both files.
- With R6's exit-3 stop for every role in that copy, `test_watch_agents.py`'s 91 tests pass (one only lacks
  `example/` in a scripts-only copy); `test_a_note_with_nothing_to_take_logs_idle_and_launches_nothing`
  (`test_watch_agents.py:1191`) asserts nothing on `p.stops()`.
- `twice_errors` prototyped: `test_check_formats`, `test_open_ids`, `test_findings_report`, `test_score_run`,
  `test_monitor_records`, `test_preflight`, `test_collect_run` pass bar 4 that read `example/` and `references/`,
  missing in that copy; no `critique-response.md` under the skill folder for the new error to flag.
- The `launch.md` line: `test_preflight.py` 44 passed, `test_docs.py` 8, on a full copy with it.
- `WAITERS` (`test_skill_example.py:249-252` at 9bf3542): with Step 5's fixer brief and the old entry, the waiter test
  fails (1 failed, 17 passed, with `test_skill_md.py`); with the planner's entry in its place (lane a's working tree
  at 4b517dd, 08:21Z), 18 passed.
- `agent` reads `final` (`:716`) before `if row is None` (`:722`); `act` dereferences `row` at `:1017` and `:1021`;
  `self.stop` (`:1033-1036`) does not look at `--check`, `act` does (`:1016-1020`).
- No other script checks agent fields (`grep AGENT_TYPES\|read_config` in `manager/preflight.py`, `collect_run.py`,
  `check_formats.py`, `monitor_records.py`: none); registry tests check subsets of an entry (`:776-777`).
- `check_formats.ids` is `:149-215`, 67 lines, capped by `test_check_formats.py:537`; `P` at `:180-191`.
- Rule 2 of the plan split applies only to a plan folder holding a `task-NN.code.md` (`plans.py:106` at 30c7ad5):
  this plan has none, so its test blocks stay in the task file.
- Spec: Decided 2 `pipeline-fold.md:78-89`, the two fields and the stop `:85-88`, Intent `:8-25`, Measurement 3
  `:147-148`. Wiki at 30c7ad5: `wiki/index.md:43` the last `## Decisions` line, `wiki/log.md:73-76` the last section.

## Deferred
- Two planners of one parity both answering (the lane claim line `Task N: started by <role>` decides who owns a
  task today; an id belongs to the task's lane).
