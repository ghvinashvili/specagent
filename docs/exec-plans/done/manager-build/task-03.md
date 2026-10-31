# Task 3 — The record monitor, the claim race detector, the duty list, check_formats extended

planner: d
builder: b
depends_on: 2
files: `scripts/monitor_records.py` (new), `scripts/duty_list.py` (new), `scripts/check_formats.py`, `scripts/tests/test_monitor_records.py` (new), `scripts/tests/test_duty_list.py` (new), `scripts/tests/test_check_formats.py` (tests appended), `scripts/README.md` (the sections of the three scripts)
acceptance: 10.7, 10.10, 10.11, 10.19 (the monitor's re-arming), 10.8's third clause (a planted second `Task N: started by` line raises the alarm within one interval; need 6)
milestone: M1

Paths: `scripts/` is `.claude/skills/running-specagent-pipelines/scripts/` (the index's shorthand). Commands use
`W=/home/tite/Desktop/agentic-flow-template/manager-build-b` (builder B's worktree), `SK="${W:?}/.claude/skills/running-specagent-pipelines"`,
`PY="${W:?}/.venv/bin/python"` and `PLAN=/home/tite/Desktop/agentic-flow-template/manager-build-plan/docs/exec-plans/done/manager-build`.
The tree this task is built on: `feat/manager-build-b` after Task 2 (e32d413 plus Task 2's commit). Standard library only.

## Goal
The manager stops polling by hand. `duty_list.py` turns the plan into the duty list before the launch (spec 5.1.2): every
merge, request point and the judge's approval, with the task each one blocks. `monitor_records.py watch` runs as the
manager's background command and exits with one `WAKE` line per new event (a request line, an overdue request, a claim
race, a stalled claim, a due or overdue duty, a verdict, a failed merge check), so the exit re-invokes the manager, which
answers and re-arms it with the same command (5.1.3, 5.3, 5.4, needs 4 and 6). `check_formats.py` checks the request lines
against the bound, every `Merged:` line's sha, the waiters and the duty ticks (10.7, 10.10, 10.11).

## Spec carried
- 5.1.2 and 8.2.3: the duty list extracted from the plan and checked at every wake-up (`duty_list.py`, the monitor's duty round).
- 5.1.3 and 10.19: the monitor armed with the exact command, re-armed after every exit; its log shows `armed` after `expired`.
- 5.2 rule 1, 5.3, need 6 and 10.8's third clause: a second claim of one task wakes the manager in the first round that sees it.
- 5.4, need 4, 8.3.3 and 10.7: the request lines `SANDBOX:`, `COPY-REQUEST:`, `CHECKOUT-REQUEST:`, `FF-REQUEST:`, the
  `VERDICT:` and `Task N: done|written` lines and the `Merged:` duties are watched; `check_formats.py` checks the requests
  against the bound (8.3.3: today the watcher acts on no request line and `check_formats.py` checks none).
- 10.10: every `Merged:` line in `lessons.md` carries a hex sha that is an ancestor of the merged-into builder's HEAD; no
  waiter of the run folder counts the marker with `grep -c`.
- 10.11: the duty file `_control/duties.md` (written before the launch, its `Extracted <time> UTC` line dates it); every tick
  carries a `date -u` time; the monitor wakes on a duty open past the bound.

## Departures from the spec (with the reasons)
1. The monitor answers no request itself (need 4 lets it act). Every answer changes a worktree or the sandbox, and the
   manager's guards (5.5: the permission rules, the auto-mode classifier, never running project code) cover only the
   commands the manager runs. The monitor detects within one interval, records both times, wakes the manager with the
   file, line, requester and blocked task, and checks the bound; `monitor_records.py answer` writes the answer line with
   the clock time, so 5.1.5's clock rule holds by code.
2. Request lines carry no time. The asked time is the monitor's first sight (error at most one interval);
   `check_formats.py` takes it from the monitor's state and falls back to the file's mtime, a lower bound of the age, so the
   fallback can miss an overdue request but never reports a false one.
3. `Task N: done|written` lines are logged, not woken: each wake costs a manager turn, and a done line matters to the
   manager only through the merge duties it makes due (those wake).
4. COPY, CHECKOUT and FF points enter the duty list only from a task-file line `Request point: <KIND> — <why>`: a mention
   in a test or in prose is not a point, and the task files use the `scripts/` shorthand, so protected paths cannot be
   inferred from the `files:` cells.

## Contracts
Sent to `manager/plan-fixer` (msg 9466dc7e, 2026-10-29 20:30 UTC; carried into the index rows at b0db935); the last is in
row 4 since 3e38124, and its exact `not armed:` lines (Interfaces, `status`) went to the fixer with this task's commit.
- Task 2: `_control/registry.json` is `{"roles": {"<agent name as in _agents.json>": {"state": "running|stopped|blocked|done"}}}`;
  the monitor reads only `roles.<agent>.state`, a missing file or key is no state, and it never writes the file.
- Task 4: `example/common.md` holds, at a line start, `Request-line bound: 15 minutes` (regex
  `^Request-line bound: (\d+) minutes?\b`; 15 when absent) and names the forms `CHECKOUT-REQUEST: <sha>` and
  `FF-REQUEST: <branch> <sha> -> <branch> <sha>` and the answer lines, written in the requester's file below the request:
  `SUPPLIED:` (SANDBOX), `COPIED:` (COPY-REQUEST), `CHECKED-OUT:` (CHECKOUT-REQUEST), `FF-DONE:` (FF-REQUEST) and
  `REFUSED: <KIND> — <why>`; an answer closes the oldest open request of its kind in that file.
- Task 5: the surface reads `_control/monitor.json`: `"alarms"`, a list of `{id, kind, text, since, open}` with kind one of
  `claim-race`, `stalled-claim`, `overdue`, `overdue-duty`, `merge-check` and `since` as `YYYY-MM-DDTHH:MM:SSZ`, and
  `"requests"`, a list of `{id, kind, file, line, text, seen, answered}` (`answered` null while open); the monitor is the
  file's only writer.
- Task 1 (or 11): `example/planner-assignment.md` names the line `Request point: <KIND> — <why>`; Task 11: `SKILL.md`
  names `duty_list.py extract <plan-dir> --out <run-dir>/_control/duties.md` (after the index, before the launch) and
  `monitor_records.py watch <run-dir>` (a background command, re-armed after every exit) and adds the decision pages of
  `## For Task 11` below.
- Task 4 (critic C4, point 4; the pre-flight's armed check): `python3 -I scripts/monitor_records.py status <run-dir>`
  prints one line and exits 0 when a `watch` is armed (its heartbeat, `"watch"."last_round"` in `_control/monitor.json`,
  is at most 2 × interval + 5 seconds old and the watch has not ended): `armed since <YYYY-MM-DD HH:MM:SS> UTC, last round
  <YYYY-MM-DD HH:MM:SS> UTC, interval <s> s`; it exits 1 with `not armed: <reason>` when no watch is recorded, the last
  watch woke or expired (re-arm with the same command) or the heartbeat is stale; it exits 2 when the run folder is missing.
- Task 4 (task-04.md:52 at 668dfe5, carried by the fixer): the pre-flight runs `[sys.executable, "-I", <formats>,
  <run>]` and needs exit 0 on a clean run folder; `check_formats.py` reads the config at
  `<run-dir>/_control/_agents.json` when `<run-dir>/_agents.json` is absent (`CONFIGS`, Interfaces).

## Interfaces
The builder writes the code against the tests of Steps 2-4; these are the names and formats the tests and the other
tasks rely on. Every function stays under 50 lines (`.claude/rules/python.md:9`; the tests measure it), standard library only.

### `scripts/duty_list.py` (new)
- `python3 -I scripts/duty_list.py extract <plan-dir> [--out FILE]`: without `--out`, prints one line `- [ ] D<k> <text>`
  per duty, k from 1. With `--out`, creates FILE (and its folder) as `HEADER`, a blank line,
  `Extracted <YYYY-MM-DD HH:MM> UTC from <plan-dir>/00-index.md: <n> new duties.` and the duty lines; when FILE exists, it
  appends that `Extracted` line and only the duties whose `key` FILE lacks, numbered after FILE's highest `D`, and leaves
  FILE untouched when none is new; prints `<FILE>: <n> new duties`; exit 0. No task table: stderr
  `<plan-dir>/00-index.md: no task table with Task, builder and depends_on columns`, exit 2.
- `python3 -I scripts/duty_list.py tick <duty-file> <D-id> <evidence>`: the duty's line becomes
  `- [x] <YYYY-MM-DD HH:MM> UTC (<evidence>) D<n> <text>`; prints `ticked D<n>`; exit 0. Errors, exit 2: stderr
  `<duty-file>: no D<n>` or `<duty-file>: D<n> is ticked already (<when>)`.
- The duties, in this order:
  1. table merges, in row order: a dependency in another builder's lane gives, per other lane in the order of its first
     number, `Merged: <y>-><x> — blocks Task <T> (builder <x>) — due when <span> done — 00-index.md:<row line>` (x the
     row's builder, y the dependency's), over the cell's numbers in lane y; a `Merged: <m>` inside the depends_on cell
     replaces the implied ones, one duty per marker in cell order:
     `Merged: <m> — blocks Task <T> (builder <x>) — due when <span> done — 00-index.md:<row line>`, over the cell's
     numbers (every lower task when the cell has none); a marker `<y>-><x>` whose y is a builder of the table keeps only
     those in lane y (all of them when none is), any other marker (`a+b+c+d`, `main->plan`) keeps them all (critic C12:
     row 10's `a->b` waits for Task 1 only, its `c->b` for Tasks 6 and 8);
  2. prose markers: a backticked `Merged: <m> …` outside the task table whose marker (`→` read as `->`) the table does
     not place, once per marker: `Merged: <m> — blocks: see 00-index.md:<line> (a marker the task table does not place)`;
  3. request points: per `task-NN.md` (sorted by name), a line outside fenced code that starts `Request point: <KIND>`
     (COPY-REQUEST, CHECKOUT-REQUEST or FF-REQUEST), once per kind per task: `<KIND> point — blocks Task <N> (builder <x>) — task-NN.md:<line>`;
     a fence opens on a line of three or more backticks or tildes indented at most three spaces and closes on a line of
     that character alone, at least as long (CommonMark; a test's fixture in a task file is not a point, departure 4);
  4. last, `JUDGE`.
  `<span>`: `Task 2`, `Tasks 2, 3, 6, 8`, runs of three or more as a range, `Tasks 1-10`. The task table is the first
  Markdown table whose header has a cell starting `task`, a cell `builder` and a cell starting `depends_on` (case
  ignored); cells split on `|` outside code spans; depends_on numbers skip code spans and read `1-4` as 1, 2, 3, 4.
- Names the monitor imports (binding):
```python
DUTY = re.compile(
    r"^- \[(?P<mark>[ x])\] (?:(?P<when>(?:\d{4}-\d{2}-\d{2} )?\d{2}:\d{2} UTC)(?: \((?P<evidence>[^)]*)\))? )?"
    r"D(?P<n>\d+) (?P<text>.+)$"
)
MERGE = re.compile(
    r"^Merged: (?P<marker>\S+) — blocks Task (?P<task>\d+) \(builder (?P<lane>[\w-]+)\) — "
    r"due when Tasks? (?P<after>[\d, -]+) done — (?P<source>\S+)$"
)
JUDGE = "judge approval — blocks the judge — due when every record's STATUS is final"
HEADER = "# Duty list (spec 5.1.2): each duty is ticked with its date -u time when done; the monitor ticks the merges."
def clock(now: datetime.datetime | None = None) -> str: ...  # "YYYY-MM-DD HH:MM UTC", UTC
def norm(marker: str) -> str: ...  # "b→a" -> "b->a"
def numbers(cell: str) -> list[int]: ...  # sorted, each once: "1-3, 5 (`Merged: a+b at 90ab`)" -> [1, 2, 3, 5]; "—" -> []
def span(nums: list[int]) -> str: ...
def extract(plan: pathlib.Path) -> list[str]: ...  # the duty texts; ValueError(<the stderr text>) without a task table
def parse_duties(text: str) -> list[dict]: ...  # {"n", "done", "when", "evidence", "text", "line"} per DUTY line
def key(text: str) -> str: ...  # the text without its `<name>.md:<line>` sources, which move between extractions
def merge_into(existing: str, texts: list[str], when: str, source: str) -> tuple[str, int]: ...
def tick(text: str, n: int, evidence: str, when: str) -> str: ...  # KeyError("no D<n>"), ValueError("D<n> is ticked already (<when>)")
def write(path: pathlib.Path, text: str) -> None: ...  # the folder made; a temporary file, then os.replace
def main(argv: list[str] | None = None) -> int: ...
```

### `scripts/check_formats.py` (extended)
- Kept for the importers: `DONE`, `LESSON_ID`, `line_of`, `read`, `CAUSE`, `HEADING`, `ids`, `sections`; `ids` stays as it
  is (67 lines at e32d413; the length test allows it 67). `main` (80 lines at e32d413) splits into helpers so that it and
  every new function stay under 50 lines; `log_checkouts` reads `CONFIGS` in order (the base read only the two root names;
  this run and template-core keep the config at `_control/_agents.json`).
- CLI: `python3 -I scripts/check_formats.py <run-dir> [--repo DIR] [--state FILE] [--json]`; `--state` is the monitor's
  state, default `<run-dir>/_control/monitor.json`. The JSON keeps exactly the keys `open`, `done` and `errors`
  (`test_json_and_text_output` pins them): open requests go under `open` by kind, as `<file>:<line>`. The errors keep the
  base order and then add, in this order, the request, merge, waiter and duty errors. Exit 1 on any error.
```python
CONFIGS = ("_control/_agents.json", "_agents.json", "_agents-active.json")
REQUEST_KINDS = {"SANDBOX": "SUPPLIED", "COPY-REQUEST": "COPIED", "CHECKOUT-REQUEST": "CHECKED-OUT", "FF-REQUEST": "FF-DONE"}
REQUEST = re.compile(r"^(?:- )?(SANDBOX|COPY-REQUEST|CHECKOUT-REQUEST|FF-REQUEST): (.*)$", re.MULTILINE)
REPLY = re.compile(r"^(?:- )?(SUPPLIED|COPIED|CHECKED-OUT|FF-DONE|REFUSED): (.*)$", re.MULTILINE)
BOUND = re.compile(r"^Request-line bound: (\d+) minutes?\b", re.MULTILINE)
DEFAULT_BOUND = 15
MERGED = re.compile(r"Merged: (\S+) at ([0-9a-f]{7,40})\b")
CODE_SPAN = re.compile(r"`[^`\n]*`")
def epoch(iso: str) -> float: ...  # "YYYY-MM-DDTHH:MM:SSZ" -> seconds since the epoch
def agents(run: pathlib.Path) -> dict[str, dict]: ...  # the agents of every config in CONFIGS order; the first definition of a name wins
def records(run: pathlib.Path) -> list[pathlib.Path]: ...  # the run folder's *.md, no leading "_", line 1 starting "STATUS:", sorted
def bound_minutes(run: pathlib.Path) -> int: ...  # BOUND in <run>/_common.md, else DEFAULT_BOUND
def request_pairs(name: str, text: str) -> tuple[list[dict], list[str]]: ...
def request_errors(run: pathlib.Path, state: pathlib.Path, now: float) -> tuple[dict[str, list[str]], list[str]]: ...
def merged_errors(run: pathlib.Path, repo: str | None) -> list[str]: ...
def waiter_errors(run: pathlib.Path) -> list[str]: ...
def duty_errors(run: pathlib.Path) -> list[str]: ...
```
- `request_pairs`: the requests in file order, each `{"id": "<name>:<KIND>:<k>", "kind", "line", "text", "answer_line",
  "answer"}` (k counts the requests of that kind in that file from 1); an answer line closes the oldest open request of its
  kind above it; the kind of `REFUSED:` is the first word of its text. Errors: `<name>:<line>: <PREFIX>: answers no open
  <KIND> line above it` and `<name>:<line>: REFUSED: names no request kind`.
- `request_errors`: over `records(run)`; an open request whose age (from the state's `requests[].seen` of its id, else
  from the file's mtime) passes the bound gives `<file>:<line>: <KIND> open <m> min, past the bound of <b> min`, m whole minutes.
- `merged_errors`, over `lessons.md` with code spans removed: `lessons.md:<line>: a Merged: line without a hex sha`;
  `lessons.md:<line>: Merged: <marker> at <sha> is not an ancestor of HEAD in <cwd>[ or <cwd>]` (x->y or x→y: the cwd
  of the config agent whose name ends `builder-<y>`; a `+` marker (`a+b`, `a+b+c+d`): each named builder's, in the marker's order, one suffices;
  `git -C <cwd> merge-base --is-ancestor <sha> HEAD`); `lessons.md:<line>: Merged: <marker> at <sha> is not a commit of
  <place>[ or <place>]` for any other target (`main->plan`): `git -C <place> cat-file -e <sha>^{commit}` in `--repo`, else
  in every builder cwd, sorted; no place, no check.
- `waiter_errors`: `<file>:<line>: a waiter counts the Merged marker with grep -c; match the hex sha instead`, for each
  line of the run folder's `_*.py` and `*.sh` and each code span or fenced line of its `_*.md` that holds `grep`, a `-c`
  flag (alone or clustered, `-cE`) or `--count`, and `Merged`, but not `[0-9a-f]`.
- `duty_errors`: `_control/duties.md:<line>: D<n> is ticked without a UTC time` for a `- [x]` line whose mark is not
  followed by `[YYYY-MM-DD ]HH:MM UTC`.

### `scripts/monitor_records.py` (new)
Imports check_formats as `cf` and duty_list as `dl` (a sibling import under `python3 -I` needs
`sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))`, the precedent of `findings_report.py:28-30`, after `sys.dont_write_bytecode = True`, because `python3 -I` ignores
`PYTHONDONTWRITEBYTECODE` and the skill folder stays clean; the imports carry no `noqa`: E402 is not selected and
RUF100 flags an unused directive). No shebang line: each new script runs as
`python3 -I <path>` (EXE001, lessons.md 22:23 UTC: ruff flags a shebang on a file that is not executable, and a
builder cannot set a mode under `.claude/skills/`).
- CLI: `python3 -I scripts/monitor_records.py <command> <run-dir> [options]` with the commands `watch`, `once`,
  `answer <request-id> <text> [--refuse]`, `report` and `status`, and these options after the command (a parent parser):
  `--config FILE` (default: the agents of every `cf.CONFIGS` file, `cf.agents(run)`), `--registry FILE` (`_control/registry.json`),
  `--duties FILE` (`_control/duties.md`), `--state FILE` (`_control/monitor.json`), `--log FILE` (`_control/monitor.log`),
  `--interval S` (60, seconds, float), `--hours H` (8, float), `--bound M` (minutes, float; default `cf.bound_minutes(run)`),
  `--grace S` (`STALL_GRACE = 300`, float). Relative paths resolve against the run folder. Every command on a missing run
  folder: stderr `<run-dir>: no such run folder`, exit 2.
- `watch`: logs `armed <run-dir> interval=<s> s hours=<h> bound=<m> min` (numbers formatted with `:g`), runs a round at
  once and then one per interval, writing the heartbeat `watch.last_round` each round. The first round with WAKE lines
  prints them and `woke: <n>`, logs `woke: <n>`, sets `watch.ended` to `woke`; exit 0. After `--hours` with no wake it logs
  `expired after <h> h`, prints `expired after <h> h: re-arm with the same command`, sets `watch.ended` to `expired`;
  exit 1. A re-arm logs `armed …` again (10.19).
- `once`: one round with the same effects but no heartbeat; prints the WAKE lines and `woke: <n>`; exit 0.
- `answer <request-id> <text>`: appends `<PREFIX>: <text> — <YYYY-MM-DD HH:MM> UTC` (PREFIX `cf.REQUEST_KINDS[kind]`)
  or, with `--refuse`, `REFUSED: <KIND> — <text> — <YYYY-MM-DD HH:MM> UTC` to the request's file; sets the request's
  `answered` (an entry the monitor never made is made with `late: true`), closes its `overdue` alarm, logs
  `answered <id> (<file>:<line>)`, prints `answered <id>: <file>:<line>` (the new line); exit 0. Errors, exit 2: stderr
  `<id>: no such request`, `<id>: answered already (<file>:<answer line>)`, or, when an older request of the same kind
  in that file is open (the new line would close that one), `<id>: answer <older id> first (<file>:<its line>)`.
- `report`: prints `| kind | file:line | asked (UTC) | answered (UTC) | minutes |`, `|---|---|---|---|---|` and a row per
  state request, in state order: `| <KIND> | <file>:<line> | <seen, YYYY-MM-DD HH:MM> | <answered, YYYY-MM-DD HH:MM, or
  open> | <whole minutes from seen to answered, or to now> |`; a `late` request shows `—` in the last three cells. Exit 0.
- `status`: the contract under Contracts (Task 4), in these lines (times `YYYY-MM-DD HH:MM:SS`, `<s>` with `:g`): exit 0
  `armed since <armed> UTC, last round <last_round> UTC, interval <s> s`; exit 1 `not armed: no watch recorded`,
  `not armed: the last watch woke at <ended_at> UTC; re-arm with the same command` (`expired at` after an expiry), or
  `not armed: no round since <last_round> UTC (interval <s> s); re-arm with the same command` (heartbeat older than
  2 × interval + 5 s).
- A round, in this order; each WAKE line is given once, because the state entry made when it wakes survives re-arms:
  1. requests, over `cf.records(run)` with `cf.request_pairs`: a request the state lacks gets an entry (`seen` now) and
     wakes `WAKE request <id> <KIND> <file>:<line> (<agent>, <task>): <text>`, `<agent>` the config agent whose
     `status` is the file, `<task>` `Task <N>` from the first `Task <N>` of the file's line 1, each `-` when absent; a
     request first seen with its answer gets `seen` = `answered` = now and `late: true` and does not wake; an open request
     older than the bound wakes `WAKE overdue <id> <KIND> <file>:<line>: open <m> min, bound <b> min` and opens alarm
     `overdue:<id>`; when its answer appears, `answered` is set (unless `answer` set it) and the alarm closes.
  2. verdicts: a `^(?:- )?VERDICT: (.*)$` line of a record wakes `WAKE verdict <file>:<line>: <text>`.
  3. claims, from `plan-log.md`: `^(?:- )?Task (\d+): started by ([\w./-]+)` (the role is the name's last `/` part),
     `^(?:- )?Task (\d+): claim released by ([\w./-]+)`, `^(?:- )?Task (\d+): (?:index )?written — ([0-9a-f]{7,40})\b`.
     A task claimed by two roles, none released, wakes per later role
     `WAKE claim-race Task <N>: <first> (plan-log.md:<l1>) and <other> (plan-log.md:<l2>)` and opens alarm
     `claim-race:<N>:<other>`, closed by that role's release; one role claiming twice is no race. A claimed, unwritten task
     whose first unreleased claimant's registry state (`roles.<agent>.state` of the agent whose name's last `/` part is the role) has
     been `stopped`, `blocked` or `done` for `--grace` seconds (`stalls.<N>` holds the first sight) wakes
     `WAKE stalled-claim Task <N>: <role> is <state> and Task <N> is not written (plan-log.md:<l>)` and opens alarm
     `stalled-claim:<N>`, closed when the task is written or the role runs again.
  4. duties, from `--duties` (`dl.parse_duties`), unticked ones: a merge duty (`dl.MERGE`) is due when every task of its
     `after` (`dl.numbers`) has a `cf.DONE` line in a build log (`cf.build_logs`; a task's last line wins); the judge
     duty (`dl.JUDGE`) is due when every config agent that has `status` and `final`, except those named `*/judge`, has a
     status file whose line 1 starts with its `final` (no config: every record but `judge.md` starts `STATUS: done`). A
     duty that becomes due wakes `WAKE duty D<n> due: <its text before " — due when">` (`duties.D<n>.due` = now); a due
     duty unticked past the bound wakes `WAKE overdue-duty D<n>: open <m> min since due, bound <b> min` (alarm
     `overdue-duty:D<n>`). A due merge duty is checked against each `Merged:` of `lessons.md` (code spans removed,
     `cf.MERGED`) whose marker equals the duty's whole (`dl.norm`; `a+b` never ticks `a+b+c+d`, nor the reverse), in the
     cwd of the config agent named `*builder-<lane>`, the blocked builder, for a `+` marker too (main-duties.md D5
     fast-forwards the last task's builder branch to that merge): each
     `after` task's done sha must be an ancestor of the merged sha, and the merged sha an ancestor of HEAD. Then the duty
     is ticked (`dl.tick`, evidence `lessons.md:<l>, <sha7>`), `ticked D<n> (lessons.md:<l>, <sha7>)` is logged and its
     alarms close; else it wakes, once per line, `WAKE merge-check D<n>: lessons.md:<l> Merged: <marker> at <sha7> fails:
     <reason>` with reason `Task <t>'s <sha7> is not in it` or `not an ancestor of HEAD in <cwd>` (alarm
     `merge-check:D<n>:<l>`). No such cwd: no check and no tick. A merge duty ticked in the round it becomes due does not
     wake; otherwise its `duty` line comes before its `merge-check` lines. Point and prose duties are ticked by hand
     (`duty_list.py tick`).
  5. the `cf.DONE` lines of the build logs and the written lines of `plan-log.md` are logged once,
     `done Task <N> <sha7> (<file>:<line>)` and `written Task <N> <sha7> (plan-log.md:<line>)`; they never wake.
  6. the WAKE lines are logged; the state is saved (a temporary file, then `os.replace`).
- Log lines: `<YYYY-MM-DD HH:MM:SS> UTC <message>`. The monitor never runs `claude`, writes no record except through
  `answer`, and never writes the registry.
- State `_control/monitor.json`, the monitor its only writer; `<iso>` is `YYYY-MM-DDTHH:MM:SSZ`; an alarm's `text` is its
  WAKE line without `WAKE `; a field a test or an older version left out reads as absent:
```json
{"watch": {"armed": "<iso>", "last_round": "<iso>", "interval": 60.0, "ended": null, "ended_at": null},
 "requests": [{"id": "build-log-b.md:SANDBOX:1", "kind": "SANDBOX", "file": "build-log-b.md", "line": 3,
               "text": "allow writes to /x", "seen": "<iso>", "answered": null, "late": false}],
 "alarms": [{"id": "overdue:build-log-b.md:SANDBOX:1", "kind": "overdue", "text": "overdue build-log-b.md:SANDBOX:1 SANDBOX build-log-b.md:3: open 16 min, bound 15 min", "since": "<iso>", "open": true}],
 "duties": {"D1": {"due": "<iso>"}},
 "stalls": {"3": "<iso>"},
 "noted": ["verdict judge.md:2", "done build-log-b.md:2", "written plan-log.md:9"]}
```

## Steps
- [ ] **Step 1 — the baseline.** On builder B's tree after Task 2:
  ```bash
  W=/home/tite/Desktop/agentic-flow-template/manager-build-b; SK="${W:?}/.claude/skills/running-specagent-pipelines"; PY="${W:?}/.venv/bin/python"
  git -C "${W:?}" log --oneline -1
  (ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 600 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests" 2>&1 | tail -1)
  ```
  Expected: Task 2's commit on top of e32d413, and `<N0> passed`. Write N0 down: 146 tests were collected at e32d413
  (and at the plan's b0db935, same skill files) before Task 2, which adds its watcher tests. `test_check_formats.py` has 14.

- [ ] **Step 2 — the duty list: tests, red, code, green.** Write `scripts/tests/test_duty_list.py`:
````python
"""Tests of duty_list.py on a synthetic plan folder.

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests/test_duty_list.py
"""

import ast
import datetime
import importlib.util
import pathlib
import subprocess
import sys

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "duty_list.py"
HEADER = "# Duty list (spec 5.1.2): each duty is ticked with its date -u time when done; the monitor ticks the merges."
INDEX = """\
# Plan index
Prose: the main session merges `Merged: main->plan at <sha>` first.

## Task order
| Task | title | planner | builder | depends_on | files |
|---|---|---|---|---|---|
| 1 | `a|b` one | a | b | — | `x.py` |
| 2 | two | b | a | 1 | `y.py` |
| 3 | three | c | a | 2 | `z.py` |
| 4 | four | d | b | 2, 3 | `w.py` |
| 5 | five | a | a | 1-4 (`Merged: a+b`) | `v.py` |

Placed already: `Merged: a+b at <sha>`; not placed: `Merged: a→c at <sha>` and `Merged: a->c at <sha>`.
"""
TASK_02 = """\
# Task 2 — two
Steps:
Request point: COPY-REQUEST — copy the vault form from the main checkout
    assert "COPY-REQUEST: x" in out
- Request point: FF-REQUEST — not at a line start, so not a point
Request point: FF-REQUEST — fast-forward the plan branch
Request point: COPY-REQUEST — a second COPY point of the same task counts once
"""
DUTIES = [
    "Merged: b->a — blocks Task 2 (builder a) — due when Task 1 done — 00-index.md:8",
    "Merged: a->b — blocks Task 4 (builder b) — due when Tasks 2, 3 done — 00-index.md:10",
    "Merged: a+b — blocks Task 5 (builder a) — due when Tasks 1-4 done — 00-index.md:11",
    "Merged: main->plan — blocks: see 00-index.md:2 (a marker the task table does not place)",
    "Merged: a→c — blocks: see 00-index.md:13 (a marker the task table does not place)",
    "COPY-REQUEST point — blocks Task 2 (builder a) — task-02.md:3",
    "FF-REQUEST point — blocks Task 2 (builder a) — task-02.md:6",
    "CHECKOUT-REQUEST point — blocks Task 5 (builder a) — task-05.md:2",
    "judge approval — blocks the judge — due when every record's STATUS is final",
]
TABLE = """\
| Task | title | planner | builder | depends_on | files |
|---|---|---|---|---|---|
| 1 | one | a | a | — | x |
| 2 | two | b | b | — | y |
| 3 | three | c | c | — | z |
| 4 | four | b | b | {cell} | w |
"""
TWO_LANES = [
    "- [ ] D1 Merged: a->b — blocks Task 4 (builder b) — due when Task 1 done — 00-index.md:6",
    "- [ ] D2 Merged: c->b — blocks Task 4 (builder b) — due when Task 3 done — 00-index.md:6",
    f"- [ ] D3 {DUTIES[-1]}",
]


@pytest.fixture
def plan(tmp_path):
    path = tmp_path / "plan"
    path.mkdir()
    (path / "00-index.md").write_text(INDEX, encoding="utf-8")
    (path / "task-02.md").write_text(TASK_02, encoding="utf-8")
    (path / "task-04.md").write_text(
        "# Task 4 — four\nThe builder writes `COPY-REQUEST: <path>` on need.\n"
        "````python\nTASK = '''\n```bash\nRequest point: FF-REQUEST — a test's fixture, inside a fence\n'''\n````\n"
    )
    (path / "task-05.md").write_text("# Task 5 — five\nRequest point: CHECKOUT-REQUEST — check out the merge\n")
    return path


def dl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True, timeout=30, check=False
    )


def module():
    spec = importlib.util.spec_from_file_location("duty_list", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def minutes() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M UTC")


def test_extract_prints_merges_prose_markers_points_and_the_judge(plan):
    p = dl("extract", str(plan))
    assert (p.returncode, p.stderr) == (0, "")
    assert p.stdout.splitlines() == [f"- [ ] D{k} {text}" for k, text in enumerate(DUTIES, 1)]


def test_extract_out_creates_the_file_then_appends_only_new_duties(plan, tmp_path):
    out = tmp_path / "run" / "_control" / "duties.md"
    before = minutes()
    p = dl("extract", str(plan), "--out", str(out))
    after = minutes()
    assert (p.returncode, p.stdout, p.stderr) == (0, f"{out}: 9 new duties\n", "")
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[:2] == [HEADER, ""]
    assert lines[2] in {f"Extracted {t} from {plan / '00-index.md'}: 9 new duties." for t in (before, after)}
    assert lines[3:] == [f"- [ ] D{k} {text}" for k, text in enumerate(DUTIES, 1)]
    first = out.read_bytes()
    p = dl("extract", str(plan), "--out", str(out))
    assert (p.returncode, p.stdout, out.read_bytes()) == (0, f"{out}: 0 new duties\n", first)
    out.write_text(out.read_text(encoding="utf-8").replace("- [ ] D1 ", "- [x] 20:01 UTC (by hand) D1 "))
    moved = INDEX.replace("## Task order\n", "## Task order\n\n").replace(
        "| 5 | five | a | a | 1-4 (`Merged: a+b`) | `v.py` |\n",
        "| 5 | five | a | a | 1-4 (`Merged: a+b`) | `v.py` |\n| 6 | six | d | b | 5 | `u.py` |\n",
    )
    (plan / "00-index.md").write_text(moved, encoding="utf-8")
    p = dl("extract", str(plan), "--out", str(out))
    assert (p.returncode, p.stdout) == (0, f"{out}: 1 new duties\n")
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[3] == "- [x] 20:01 UTC (by hand) D1 " + DUTIES[0]
    assert lines[-2].startswith("Extracted ") and lines[-2].endswith(": 1 new duties.")
    assert lines[-1] == "- [ ] D10 Merged: a->b — blocks Task 6 (builder b) — due when Task 5 done — 00-index.md:13"
    assert len(lines) == 3 + 9 + 2


def test_tick_writes_the_utc_time_and_the_evidence(plan, tmp_path):
    out = tmp_path / "duties.md"
    assert dl("extract", str(plan), "--out", str(out)).returncode == 0
    before = minutes()
    p = dl("tick", str(out), "D2", "lessons.md:4, abc1234")
    after = minutes()
    assert (p.returncode, p.stdout, p.stderr) == (0, "ticked D2\n", "")
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[4] in {f"- [x] {t} (lessons.md:4, abc1234) D2 {DUTIES[1]}" for t in (before, after)}
    assert lines[3] == f"- [ ] D1 {DUTIES[0]}" and lines[5] == f"- [ ] D3 {DUTIES[2]}"
    when = lines[4][len("- [x] ") : lines[4].index(" UTC") + len(" UTC")]
    p = dl("tick", str(out), "D2", "again")
    assert (p.returncode, p.stdout, p.stderr) == (2, "", f"{out}: D2 is ticked already ({when})\n")
    p = dl("tick", str(out), "D99", "nothing")
    assert (p.returncode, p.stderr) == (2, f"{out}: no D99\n")


def test_a_plan_without_a_task_table_exits_2(tmp_path):
    (tmp_path / "00-index.md").write_text("# Plan\n| a | b |\n|---|---|\n| 1 | 2 |\n", encoding="utf-8")
    p = dl("extract", str(tmp_path))
    assert (p.returncode, p.stdout) == (2, "")
    assert p.stderr == f"{tmp_path / '00-index.md'}: no task table with Task, builder and depends_on columns\n"


def test_parse_duties_reads_hand_written_lines_too():
    text = "# Duties\n- [x] 19:54 UTC (merged by hand) D0 Merged: main->plan\n- [ ] D3 COPY-REQUEST point — x\n- [x] D4 y\n"
    assert module().parse_duties(text) == [
        {
            "n": 0,
            "done": True,
            "when": "19:54 UTC",
            "evidence": "merged by hand",
            "text": "Merged: main->plan",
            "line": 2,
        },
        {"n": 3, "done": False, "when": None, "evidence": None, "text": "COPY-REQUEST point — x", "line": 3},
        {"n": 4, "done": True, "when": None, "evidence": None, "text": "y", "line": 4},
    ]


def test_numbers_and_span():
    mod = module()
    assert mod.numbers("1-3, 5 (`Merged: a+b at 90ab`)") == [1, 2, 3, 5]
    assert mod.numbers("—") == []
    assert [mod.span(n) for n in ([2], [2, 3, 6, 8], list(range(1, 11)), [1, 2, 3, 5, 6])] == [
        "Task 2",
        "Tasks 2, 3, 6, 8",
        "Tasks 1-10",
        "Tasks 1-3, 5, 6",
    ]
    assert mod.norm("b→a") == "b->a"


def test_two_markers_in_one_cell_each_wait_for_the_tasks_of_their_own_lane(tmp_path):
    cell = "1, 2, 3 (`Merged: a->b` after 1, `Merged: c->b` after 3)"
    (tmp_path / "00-index.md").write_text(TABLE.format(cell=cell), encoding="utf-8")
    assert module().numbers(cell) == [1, 2, 3]
    p = dl("extract", str(tmp_path))
    assert (p.returncode, p.stdout.splitlines(), p.stderr) == (0, TWO_LANES, "")


def test_implied_merges_from_two_other_lanes_give_one_duty_per_lane(tmp_path):
    (tmp_path / "00-index.md").write_text(TABLE.format(cell="1, 2, 3"), encoding="utf-8")
    p = dl("extract", str(tmp_path))
    assert (p.returncode, p.stdout.splitlines(), p.stderr) == (0, TWO_LANES, "")


def test_every_function_is_under_50_lines():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    long = [
        (f.name, f.end_lineno - f.lineno + 1)
        for f in ast.walk(tree)
        if isinstance(f, ast.FunctionDef) and f.end_lineno - f.lineno + 1 >= 50
    ]
    assert long == []
````
  Run: `(ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 120 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests/test_duty_list.py" 2>&1 | tail -1)`
  Expected: `9 failed` (no `duty_list.py` yet). Write `scripts/duty_list.py` against the Interfaces, with no shebang line (EXE001,
  lessons.md 22:23 UTC). Run again.
  Expected: `9 passed`. The wrong versions the planner ran red once against these tests (each failed at least one test):
  a same-lane dependency giving a merge; the cell's marker added to the implied merges; `1-4` read as 1 and 4; any mention
  of a request kind taken as a point; new duties numbered from 1; cells split on every `|`; runs of two printed as a range;
  numbers read inside code spans; the key keeping the `00-index.md:<line>` source; a tick without its time; `→` not read as `->`;
  and, added by the fixer for C11-C12: each marker over the whole cell; a `+` marker filtered to its first lane; an
  implied merge over the whole cell; `numbers` keeping duplicates; fenced lines read as points; any fence line
  closing the fence.

- [ ] **Step 3 — check_formats: tests appended, red, code, green.** In `scripts/tests/test_check_formats.py` add
  `import ast`, `import datetime` (before `import json`) and `import time` (after `import textwrap`) to the imports, and
  append at the end of the file:
````python
def iso(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def aged(run: pathlib.Path, name: str, text: str, minutes: float) -> None:
    """A record written `minutes` ago by its mtime."""
    write(run, name, text)
    t = time.time() - minutes * 60
    os.utime(run / name, (t, t))


def test_an_open_request_past_the_bound_that_common_md_names_fails(run):
    aged(run, "plan-log.md", "STATUS: writing Task 3\nSANDBOX: allow writes to /x\n", 12)
    code, out = check(run)
    assert (code, out["errors"], out["open"]) == (0, [], {"SANDBOX": ["plan-log.md:2"]})
    write(run, "_common.md", "# Common\nRequest-line bound: 10 minutes (the monitor wakes the manager)\n")
    code, out = check(run)
    assert (code, out["open"]) == (1, {"SANDBOX": ["plan-log.md:2"]})
    assert out["errors"] == ["plan-log.md:2: SANDBOX open 12 min, past the bound of 10 min"]


def test_an_answer_closes_the_oldest_open_request_of_its_kind_above_it(run):
    write(
        run,
        "fixer-log.md",
        """
        STATUS: fixing
        COPIED: before any request
        COPY-REQUEST: templates/vault/a.md from the main checkout
        COPY-REQUEST: templates/vault/b.md from the main checkout
        FF-REQUEST: feat/x 1234567 -> main 89abcde
        COPIED: templates/vault/a.md — 2026-10-29 20:10 UTC
        SUPPLIED: nothing was asked
        REFUSED: FF-REQUEST — the branch moved
        - REFUSED: later, maybe
        ACK 1a2b3c4d
        """,
    )
    code, out = check(run)
    assert (code, out["open"]) == (1, {"COPY-REQUEST": ["fixer-log.md:4"]})
    assert out["errors"] == [
        "fixer-log.md:2: COPIED: answers no open COPY-REQUEST line above it",
        "fixer-log.md:7: SUPPLIED: answers no open SANDBOX line above it",
        "fixer-log.md:9: REFUSED: names no request kind",
    ]


def test_the_monitor_s_first_sight_wins_over_the_file_s_mtime(run):
    aged(run, "judge.md", "STATUS: judging\nCHECKOUT-REQUEST: 1234567\n", 30)
    state = run / "_control" / "monitor.json"
    state.parent.mkdir()
    state.write_text(json.dumps({"requests": [{"id": "judge.md:CHECKOUT-REQUEST:1", "seen": iso(time.time() - 120)}]}))
    code, out = check(run)
    assert (code, out["errors"], out["open"]) == (0, [], {"CHECKOUT-REQUEST": ["judge.md:2"]})
    state.write_text(json.dumps({"requests": [{"id": "judge.md:CHECKOUT-REQUEST:1", "seen": iso(time.time() - 1200)}]}))
    code, out = check(run)
    assert (code, out["errors"]) == (1, ["judge.md:2: CHECKOUT-REQUEST open 20 min, past the bound of 15 min"])
    other = run / "other.json"
    other.write_text(json.dumps({"requests": []}))
    code, out = check(run, "--state", str(other))
    assert (code, out["errors"]) == (1, ["judge.md:2: CHECKOUT-REQUEST open 30 min, past the bound of 15 min"])


def test_merged_lines_need_a_hex_sha_that_the_merged_into_checkout_holds(run, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    sha_a, _ = make_repo(a)
    make_repo(b)
    only_b = empty_commit(b, "b only")
    (run / "_control").mkdir()
    (run / "_control" / "_agents.json").write_text(
        json.dumps(
            {
                "agents": {
                    "manager/builder-a": {"cwd": str(a), "status": "build-log-a.md"},
                    "manager/builder-b": {"cwd": str(b), "status": "build-log-b.md"},
                }
            }
        )
    )
    write(
        run,
        "lessons.md",
        f"""
        # Lessons
        - 20:14 UTC (main session): Merged: b->a at {sha_a} — b merged into a
        - 20:15 UTC (main session): Merged: b→a at {only_b[:7]} — the recorded arrow, not in a
        - a waiter matches `Merged: a+b at [0-9a-f]{{7,}}`, never a bare count of `Merged: a+b`
        - 20:16 UTC (main session): Merged: b->a at {only_b} — not in a
        - 20:17 UTC (main session): Merged: a+b before the last task
        - 20:18 UTC (main session): Merged: main->plan at {"f" * 40}
        """,
    )
    code, out = check(run)
    assert code == 1
    assert out["errors"] == [
        f"lessons.md:3: Merged: b→a at {only_b[:7]} is not an ancestor of HEAD in {a}",
        f"lessons.md:5: Merged: b->a at {only_b} is not an ancestor of HEAD in {a}",
        "lessons.md:6: a Merged: line without a hex sha",
        f"lessons.md:7: Merged: main->plan at {'f' * 40} is not a commit of {a} or {b}",
    ]


def test_a_four_lane_marker_holds_when_any_named_builder_s_head_has_the_sha(run, tmp_path):
    repos = {lane: tmp_path / lane for lane in "abcd"}
    for repo in repos.values():
        make_repo(repo)
    only_c = empty_commit(repos["c"], "c only")
    agents = {f"manager/builder-{k}": {"cwd": str(v), "status": f"build-log-{k}.md"} for k, v in repos.items()}
    (run / "_control").mkdir()
    (run / "_control" / "_agents.json").write_text(json.dumps({"agents": agents}))
    write(
        run,
        "lessons.md",
        f"""
        # Lessons
        - 21:40 UTC (main session): Merged: a+b+c+d at {only_c} — the four lanes, in c's checkout only
        - 21:41 UTC (main session): Merged: a+b+c+d at {"e" * 40} — in none of the four
        """,
    )
    code, out = check(run)
    assert code == 1
    places = " or ".join(str(repos[k]) for k in "abcd")
    assert out["errors"] == [f"lessons.md:3: Merged: a+b+c+d at {'e' * 40} is not an ancestor of HEAD in {places}"]


def test_a_waiter_that_counts_the_merged_marker_with_grep_c_fails(run):
    write(
        run,
        "_wait.sh",
        "until grep -c 'Merged: a+b' lessons.md; do sleep 60; done\ngrep -cE 'Merged: a\\+b at [0-9a-f]{7,}' l.md\n",
    )
    write(
        run,
        "_builder-a-assignment.md",
        """
        Wait with `grep -qE 'Merged: a\\+b at [0-9a-f]{7,}' lessons.md`, never with a bare `grep -c`.
        A waiter never runs `grep -c 'x'` on the `Merged: a+b` marker.
        Old form: `n=$(grep -c "Merged: a+b" lessons.md)`
        ```
        grep --count 'Merged: b->a' lessons.md
        ```
        """,
    )
    code, out = check(run)
    tail = "a waiter counts the Merged marker with grep -c; match the hex sha instead"
    assert (code, out["errors"]) == (
        1,
        [f"_builder-a-assignment.md:3: {tail}", f"_builder-a-assignment.md:5: {tail}", f"_wait.sh:1: {tail}"],
    )


def test_a_ticked_duty_needs_its_utc_time(run):
    (run / "_control").mkdir()
    (run / "_control" / "duties.md").write_text(
        "# Duty list\n- [x] 2026-10-29 20:01 UTC (lessons.md:2, 960ca4e) D1 Merged: b->a — x\n"
        "- [x] 19:54 UTC (by hand) D2 Merged: main->plan\n- [x] (by hand) D3 judge approval\n- [ ] D4 COPY-REQUEST point\n",
        encoding="utf-8",
    )
    code, out = check(run)
    assert (code, out["errors"]) == (1, ["_control/duties.md:4: D3 is ticked without a UTC time"])


def test_the_config_under_control_gives_each_build_log_its_checkout(run, tmp_path):
    sha, _ = make_repo(tmp_path / "a")
    (run / "_control").mkdir()
    (run / "_control" / "_agents.json").write_text(
        json.dumps({"agents": {"manager/builder-a": {"cwd": str(tmp_path / "a"), "status": "build-log-a.md"}}})
    )
    write(run, "build-log-a.md", f"STATUS: building Task 2\nTask 1: done — {sha}\nTask 2: done — {'e' * 40}\n")
    code, out = check(run)
    assert out["done"] == [f"1:{sha[:7]}", "2:eeeeeee"]
    assert (code, out["errors"]) == (
        1,
        [f"build-log-a.md: Task 2: done — {'e' * 40} is not a commit of {tmp_path / 'a'}"],
    )


def test_every_function_is_under_50_lines_but_ids():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    sizes = {f.name: f.end_lineno - f.lineno + 1 for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)}
    assert sizes["ids"] <= 67
    assert {name: n for name, n in sizes.items() if name != "ids" and n >= 50} == {}
````
  Run: `(ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 120 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests/test_check_formats.py" 2>&1 | tail -1)`
  Expected: `9 failed, 14 passed`. Extend `scripts/check_formats.py` against the Interfaces (split `main`; keep `ids`). Run
  again. Expected: `23 passed`. Wrong versions run red once: the bound line ignored; answers paired newest first; an
  answer closing a request of another kind; answers paired regardless of their place; the mtime winning over the state's
  `seen`; code spans kept in `lessons.md`; x->y checked in x's checkout; `→` not read as `->`; the waiter check made line
  by line; fences ignored; a tick time that needs the date; the config read only at the run folder's root; `REFUSED:`
  closing a request of any kind; and, added by the fixer for C12: a `+` marker split into its first two lanes; a `+`
  marker split once. The appended tests against the base `check_formats.py` (e32d413): `9 failed, 14 passed`.
  The record of `test_an_answer_closes_the_oldest_open_request_of_its_kind_above_it` ends with `ACK 1a2b3c4d` (index
  row 3, K3 of Task 2: an `ACK <msg_id>` line is legal in every record and adds no error; the base `ids` ignores it too).

- [ ] **Step 4 — the monitor: tests, red, code, green.** Write `scripts/tests/test_monitor_records.py`. The run folder
  is built in `tmp_path`: two builders whose `cwd` are git checkouts made with `GIT_ENV` (the author and committer set
  by environment, no global config), a judge, `_common.md` with a 10-minute bound, a fake `claude` first on `PATH` that
  records its argv and is asserted never to run; past times are planted in `_control/monitor.json`; the two tests that
  start a `watch` poll the state every 0.05 s for at most 20 s. `git init -b` needs git 2.28 or later (2.43.0 here).
````python
"""Tests of monitor_records.py on a run folder in tmp_path; a fake `claude` first on PATH records its argv and must never run.

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests/test_monitor_records.py
"""

import ast
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import time

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = SCRIPTS / "monitor_records.py"
GIT_ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.org",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.org",
}
MINUTE = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}"
DUTIES = """\
# Duty list (spec 5.1.2): each duty is ticked with its date -u time when done; the monitor ticks the merges.

Extracted 2026-10-29 20:00 UTC from 00-index.md: 3 new duties.
- [ ] D1 Merged: a->b — blocks Task 3 (builder b) — due when Tasks 1, 2 done — 00-index.md:20
- [ ] D2 judge approval — blocks the judge — due when every record's STATUS is final
- [ ] D3 Merged: b→a — blocks Task 4 (builder a) — due when Task 5 done — 00-index.md:22
"""
D1 = "D1 Merged: a->b — blocks Task 3 (builder b) — due when Tasks 1, 2 done — 00-index.md:20"


def iso(seconds_ago: float) -> str:
    t = datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=seconds_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def shown(stamp: str, seconds: bool = True) -> str:
    return stamp[: 19 if seconds else 16].replace("T", " ")


def git(cwd: pathlib.Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(cwd), *args], check=True, env=GIT_ENV, capture_output=True, text=True)
    return out.stdout.strip()


def commit(repo: pathlib.Path, message: str) -> str:
    git(repo, "commit", "-q", "--allow-empty", "-m", message)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def run(tmp_path):
    """Two builders with a git checkout each, a judge, a plan log, `_common.md` with a 10-minute bound."""
    run = tmp_path / "run"
    (run / "_control").mkdir(parents=True)
    agents = {}
    for lane, task in (("a", 2), ("b", 3)):
        repo = tmp_path / f"repo-{lane}"
        git(tmp_path, "init", "-q", "-b", "main", str(repo))
        commit(repo, f"base {lane}")
        agents[f"manager/builder-{lane}"] = {
            "cwd": str(repo),
            "status": f"build-log-{lane}.md",
            "final": "STATUS: done",
        }
        (run / f"build-log-{lane}.md").write_text(f"STATUS: building Task {task}\n", encoding="utf-8")
    agents["manager/judge"] = {"cwd": str(tmp_path), "status": "judge.md", "final": "STATUS: done"}
    (run / "_control" / "_agents.json").write_text(json.dumps({"agents": agents}), encoding="utf-8")
    (run / "_common.md").write_text("# Common rules\nRequest-line bound: 10 minutes\n", encoding="utf-8")
    (run / "judge.md").write_text("STATUS: waiting\n", encoding="utf-8")
    (run / "plan-log.md").write_text("STATUS: writing Task 3\n", encoding="utf-8")
    fake = tmp_path / "bin" / "claude"
    fake.parent.mkdir()
    fake.write_text(f"#!/bin/sh\necho \"$@\" >> '{tmp_path / 'claude-argv.txt'}'\n", encoding="utf-8")
    fake.chmod(0o755)
    yield run
    assert not (tmp_path / "claude-argv.txt").exists(), "the monitor ran claude"


def env_of(run: pathlib.Path) -> dict:
    return {**GIT_ENV, "PATH": f"{run.parent / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}"}


def argv(run: pathlib.Path, command: str, *rest: str) -> list[str]:
    return [sys.executable, "-I", str(SCRIPT), command, str(run), *rest]


def mon(run: pathlib.Path, command: str, *rest: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv(run, command, *rest), capture_output=True, text=True, env=env_of(run), timeout=120, check=False
    )


def add(run: pathlib.Path, name: str, *lines: str) -> None:
    with (run / name).open("a", encoding="utf-8") as f:
        f.write("".join(line + "\n" for line in lines))


def state(run: pathlib.Path) -> dict:
    return json.loads((run / "_control" / "monitor.json").read_text(encoding="utf-8"))


def plant(run: pathlib.Path, **fields) -> None:
    (run / "_control" / "monitor.json").write_text(json.dumps(fields), encoding="utf-8")


def alarms(run: pathlib.Path) -> list[tuple[str, bool]]:
    return [(a["id"], a["open"]) for a in state(run)["alarms"]]


def logged(run: pathlib.Path) -> list[str]:
    """The monitor log's messages, each stripped of its `YYYY-MM-DD HH:MM:SS UTC ` stamp (checked)."""
    lines = (run / "_control" / "monitor.log").read_text(encoding="utf-8").splitlines()
    assert all(re.match(rf"{MINUTE}:\d\d UTC ", line) for line in lines), lines
    return [line[24:] for line in lines]


def wait_for(check, seconds: float = 20) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            if check():
                return
        except (OSError, ValueError, KeyError, TypeError):
            pass
        time.sleep(0.05)
    raise AssertionError("timed out")


def repo_of(run: pathlib.Path, lane: str) -> pathlib.Path:
    agents = json.loads((run / "_control" / "_agents.json").read_text(encoding="utf-8"))["agents"]
    return pathlib.Path(agents[f"manager/builder-{lane}"]["cwd"])


def test_once_wakes_each_new_request_with_its_requester_and_task_then_stays_silent(run):
    add(run, "build-log-b.md", "Working.", "SANDBOX: allow writes to /srv/x")
    add(
        run,
        "build-log-a.md",
        "- COPY-REQUEST: wiki/a.md from the main checkout",
        "COPIED: wiki/a.md — 2026-10-29 20:10 UTC",
    )
    (run / "extra.md").write_text("STATUS: open\nFF-REQUEST: feat/a 1234567 -> feat/b 89abcde\n", encoding="utf-8")
    before = {p.name: p.read_bytes() for p in run.glob("*.md")}
    r = mon(run, "once")
    assert (r.returncode, r.stdout) == (
        0,
        (
            "WAKE request build-log-b.md:SANDBOX:1 SANDBOX build-log-b.md:3 (manager/builder-b, Task 3): allow writes to /srv/x\n"
            "WAKE request extra.md:FF-REQUEST:1 FF-REQUEST extra.md:2 (-, -): feat/a 1234567 -> feat/b 89abcde\n"
            "woke: 2\n"
        ),
    ), r.stderr
    found = {e["id"]: e for e in state(run)["requests"]}
    late = found["build-log-a.md:COPY-REQUEST:1"]
    assert (late["late"], late["answered"]) == (True, late["seen"])
    sandbox = found["build-log-b.md:SANDBOX:1"]
    assert (sandbox["line"], sandbox["answered"], sandbox["late"]) == (3, None, False)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", sandbox["seen"])
    assert mon(run, "once").stdout == "woke: 0\n"
    assert {p.name: p.read_bytes() for p in run.glob("*.md")} == before


def test_watch_exits_0_on_the_first_wake_and_on_a_line_planted_after_it_started(run):
    add(run, "build-log-b.md", "SANDBOX: allow writes to /srv/x")
    r = mon(run, "watch", "--interval", "0.2", "--hours", "0.01")
    assert (r.returncode, r.stdout.splitlines()[-1]) == (0, "woke: 1"), r.stderr
    proc = subprocess.Popen(
        argv(run, "watch", "--interval", "0.2", "--hours", "0.05"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env_of(run),
    )
    try:
        wait_for(lambda: state(run)["watch"]["ended"] is None and state(run)["watch"]["last_round"])
        add(run, "build-log-a.md", "CHECKOUT-REQUEST: 1234567")
        out, err = proc.communicate(timeout=20)
    finally:
        proc.kill()
    assert (proc.returncode, out) == (
        0,
        (
            "WAKE request build-log-a.md:CHECKOUT-REQUEST:1 CHECKOUT-REQUEST build-log-a.md:2 (manager/builder-a, Task 2): 1234567\n"
            "woke: 1\n"
        ),
    ), err
    assert [m for m in logged(run) if not m.startswith("WAKE ")] == [
        f"armed {run} interval=0.2 s hours=0.01 bound=10 min",
        "woke: 1",
        f"armed {run} interval=0.2 s hours=0.05 bound=10 min",
        "woke: 1",
    ]
    assert state(run)["watch"]["ended"] == "woke"


def test_watch_expires_with_exit_1_and_a_re_arm_logs_armed_again(run):
    for _ in range(2):
        r = mon(run, "watch", "--interval", "0.2", "--hours", "0.0002")
        assert (r.returncode, r.stdout) == (1, "expired after 0.0002 h: re-arm with the same command\n"), r.stderr
    assert logged(run) == [f"armed {run} interval=0.2 s hours=0.0002 bound=10 min", "expired after 0.0002 h"] * 2
    assert state(run)["watch"]["ended"] == "expired"


def test_every_command_exits_2_on_a_missing_run_folder_and_writes_no_bytecode(tmp_path):
    missing, copy = tmp_path / "nowhere", tmp_path / "copy"
    copy.mkdir()
    for name in ("monitor_records.py", "check_formats.py", "duty_list.py"):
        (copy / name).write_bytes((SCRIPTS / name).read_bytes())
    for cmd in (["watch"], ["once"], ["answer", "x.md:SANDBOX:1", "ok"], ["report"], ["status"]):
        argv = [sys.executable, "-I", str(copy / "monitor_records.py"), cmd[0], str(missing), *cmd[1:]]
        r = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False)
        assert (r.returncode, r.stdout, r.stderr) == (2, "", f"{missing}: no such run folder\n"), cmd
    assert sorted(p.name for p in copy.iterdir()) == ["check_formats.py", "duty_list.py", "monitor_records.py"]


def test_an_open_request_past_the_bound_of_common_md_wakes_once_and_opens_an_alarm(run):
    add(run, "build-log-b.md", "SANDBOX: allow writes to /srv/x")
    seen = iso(12 * 60 + 30)
    entry = {"id": "build-log-b.md:SANDBOX:1", "kind": "SANDBOX", "file": "build-log-b.md", "line": 2}
    plant(run, requests=[{**entry, "text": "allow writes to /srv/x", "seen": seen, "answered": None, "late": False}])
    text = "overdue build-log-b.md:SANDBOX:1 SANDBOX build-log-b.md:2: open 12 min, bound 10 min"
    r = mon(run, "once")
    assert r.stdout == f"WAKE {text}\nwoke: 1\n", r.stderr
    [alarm] = state(run)["alarms"]
    assert (alarm["id"], alarm["kind"], alarm["text"], alarm["open"]) == (
        f"overdue:{entry['id']}",
        "overdue",
        text,
        True,
    )
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", alarm["since"])
    assert mon(run, "once").stdout == "woke: 0\n"
    assert logged(run) == [f"WAKE {text}"]


def test_answer_appends_the_answer_line_with_the_clock_time_and_closes_the_alarm(run):
    add(run, "build-log-b.md", "SANDBOX: allow writes to /srv/x", "SANDBOX: allow writes to /srv/y")
    entry = {"id": "build-log-b.md:SANDBOX:1", "kind": "SANDBOX", "file": "build-log-b.md", "line": 2}
    plant(
        run,
        requests=[{**entry, "text": "allow writes to /srv/x", "seen": iso(11 * 60), "answered": None, "late": False}],
    )
    assert mon(run, "once").stdout.startswith("WAKE overdue build-log-b.md:SANDBOX:1 ")
    r = mon(run, "answer", "build-log-b.md:SANDBOX:2", "added /srv/y")
    assert (r.returncode, r.stderr) == (
        2,
        "build-log-b.md:SANDBOX:2: answer build-log-b.md:SANDBOX:1 first (build-log-b.md:2)\n",
    )
    r = mon(run, "answer", "build-log-b.md:SANDBOX:1", "added /srv/x to the write allow list")
    assert (r.returncode, r.stdout) == (0, "answered build-log-b.md:SANDBOX:1: build-log-b.md:4\n"), r.stderr
    last = (run / "build-log-b.md").read_text(encoding="utf-8").splitlines()[-1]
    m = re.fullmatch(rf"SUPPLIED: added /srv/x to the write allow list — ({MINUTE}) UTC", last)
    assert m, last
    when = datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M").replace(tzinfo=datetime.UTC)
    assert abs((datetime.datetime.now(datetime.UTC) - when).total_seconds()) < 120
    first = next(e for e in state(run)["requests"] if e["id"] == entry["id"])
    assert first["answered"] is not None and first["late"] is False
    assert alarms(run) == [(f"overdue:{entry['id']}", False)]
    assert logged(run)[-1] == "answered build-log-b.md:SANDBOX:1 (build-log-b.md:4)"
    check = subprocess.run(
        [sys.executable, "-I", str(SCRIPTS / "check_formats.py"), str(run)],
        capture_output=True,
        text=True,
        env=env_of(run),
        check=False,
    )
    assert check.returncode == 0, check.stdout + check.stderr
    again = mon(run, "answer", "build-log-b.md:SANDBOX:1", "twice")
    assert (again.returncode, again.stderr) == (2, "build-log-b.md:SANDBOX:1: answered already (build-log-b.md:4)\n")


def test_refuse_writes_the_refused_line_and_an_unknown_id_exits_2(run):
    add(run, "build-log-a.md", "FF-REQUEST: feat/a 1234567 -> feat/b 89abcde")
    r = mon(run, "answer", "build-log-a.md:FF-REQUEST:1", "the plan branch moved; rebase first", "--refuse")
    assert (r.returncode, r.stdout) == (0, "answered build-log-a.md:FF-REQUEST:1: build-log-a.md:3\n"), r.stderr
    last = (run / "build-log-a.md").read_text(encoding="utf-8").splitlines()[-1]
    assert re.fullmatch(rf"REFUSED: FF-REQUEST — the plan branch moved; rebase first — {MINUTE} UTC", last), last
    [entry] = state(run)["requests"]
    assert (entry["id"], entry["late"], entry["answered"] is not None) == ("build-log-a.md:FF-REQUEST:1", True, True)
    assert mon(run, "once").stdout == "woke: 0\n"
    r = mon(run, "answer", "build-log-a.md:FF-REQUEST:2", "no such line")
    assert (r.returncode, r.stdout, r.stderr) == (2, "", "build-log-a.md:FF-REQUEST:2: no such request\n")


def test_report_gives_a_row_per_request_with_whole_minutes_and_dashes_for_late_ones(run):
    add(
        run,
        "build-log-b.md",
        "SANDBOX: allow writes to /srv/x",
        "SUPPLIED: added — 2026-10-29 20:08 UTC",
        "COPY-REQUEST: wiki/a.md",
    )
    add(run, "build-log-a.md", "CHECKOUT-REQUEST: 1234567", "CHECKED-OUT: 1234567 — 2026-10-29 20:01 UTC")
    sandbox = {"id": "build-log-b.md:SANDBOX:1", "kind": "SANDBOX", "file": "build-log-b.md", "line": 2, "text": "x"}
    copy = {
        "id": "build-log-b.md:COPY-REQUEST:1",
        "kind": "COPY-REQUEST",
        "file": "build-log-b.md",
        "line": 4,
        "text": "y",
    }
    seen = iso(3 * 60 + 30)
    plant(
        run,
        requests=[
            {**sandbox, "seen": "2026-10-29T20:00:00Z", "answered": "2026-10-29T20:07:59Z", "late": False},
            {**copy, "seen": seen, "answered": None, "late": False},
        ],
    )
    assert mon(run, "once").stdout == "woke: 0\n"
    r = mon(run, "report")
    assert (r.returncode, r.stdout.splitlines()) == (
        0,
        [
            "| kind | file:line | asked (UTC) | answered (UTC) | minutes |",
            "|---|---|---|---|---|",
            "| SANDBOX | build-log-b.md:2 | 2026-10-29 20:00 | 2026-10-29 20:07 | 7 |",
            f"| COPY-REQUEST | build-log-b.md:4 | {shown(seen, False)} | open | 3 |",
            "| CHECKOUT-REQUEST | build-log-a.md:2 | — | — | — |",
        ],
    ), r.stderr


def test_a_second_claim_of_one_task_wakes_in_the_first_round_and_its_release_closes_the_alarm(run):
    add(
        run,
        "plan-log.md",
        "Task 3: started by planner-d",
        "Task 3: started by manager/planner-d",
        "Task 4: started by planner",
        "- Task 4: started by manager/planner-b",
    )
    text = "claim-race Task 4: planner (plan-log.md:4) and planner-b (plan-log.md:5)"
    r = mon(run, "once")
    assert r.stdout == f"WAKE {text}\nwoke: 1\n", r.stderr
    assert alarms(run) == [("claim-race:4:planner-b", True)]
    assert mon(run, "once").stdout == "woke: 0\n"
    add(run, "plan-log.md", "Task 4: claim released by manager/planner-b")
    assert mon(run, "once").stdout == "woke: 0\n"
    assert alarms(run) == [("claim-race:4:planner-b", False)]


def test_a_claim_whose_claimant_stopped_wakes_after_the_grace_and_closes_when_written(run):
    add(run, "plan-log.md", "Task 7: started by planner-d")
    registry = run / "_control" / "registry.json"
    registry.write_text(json.dumps({"roles": {"manager/planner-d": {"state": "stopped"}}}), encoding="utf-8")
    kept = registry.read_bytes()
    assert mon(run, "once").stdout == "woke: 0\n"
    assert list(state(run)["stalls"]) == ["7"]
    text = "stalled-claim Task 7: planner-d is stopped and Task 7 is not written (plan-log.md:2)"
    assert mon(run, "once", "--grace", "0").stdout == f"WAKE {text}\nwoke: 1\n"
    assert mon(run, "once", "--grace", "0").stdout == "woke: 0\n"
    add(run, "plan-log.md", "Task 7: written — abc1234")
    assert mon(run, "once", "--grace", "0").stdout == "woke: 0\n"
    assert (alarms(run), state(run)["stalls"]) == ([("stalled-claim:7", False)], {})
    assert registry.read_bytes() == kept


def test_a_due_merge_duty_wakes_and_a_verified_merged_line_ticks_it_but_a_quoted_one_never(run):
    repo_a, repo_b = repo_of(run, "a"), repo_of(run, "b")
    t1, t2, merged = commit(repo_b, "task 1"), commit(repo_b, "task 2"), commit(repo_b, "merge a into b")
    t5, back = commit(repo_a, "task 5"), commit(repo_a, "merge b into a")
    (run / "_control" / "duties.md").write_text(DUTIES, encoding="utf-8")
    add(run, "build-log-a.md", f"Task 1: done — {t1}")
    add(run, "build-log-b.md", f"Task 5: done — {t5}")
    (run / "lessons.md").write_text(
        f"# Lessons\nMerged: b->a at {back}\nA waiter: `Merged: a->b at {merged}`.\n", encoding="utf-8"
    )
    assert mon(run, "once").stdout == "woke: 0\n"
    lines = (run / "_control" / "duties.md").read_text(encoding="utf-8").splitlines()
    assert re.fullmatch(rf"- \[x\] {MINUTE} UTC \(lessons\.md:2, {back[:7]}\) D3 Merged: b→a — .*", lines[5]), lines[5]
    add(run, "build-log-a.md", f"Task 2: done — {t2}")
    r = mon(run, "once")
    assert r.stdout == "WAKE duty D1 due: Merged: a->b — blocks Task 3 (builder b)\nwoke: 1\n", r.stderr
    add(run, "lessons.md", f"Merged: a->b at {merged[:9]}")
    assert mon(run, "once").stdout == "woke: 0\n"
    line = (run / "_control" / "duties.md").read_text(encoding="utf-8").splitlines()[3]
    assert re.fullmatch(rf"- \[x\] {MINUTE} UTC \(lessons\.md:4, {merged[:7]}\) {re.escape(D1)}", line), line
    assert [m for m in logged(run) if m.startswith("ticked ")] == [
        f"ticked D3 (lessons.md:2, {back[:7]})",
        f"ticked D1 (lessons.md:4, {merged[:7]})",
    ]


def test_a_merged_line_that_misses_a_done_task_or_head_wakes_with_the_reason(run):
    repo_b = repo_of(run, "b")
    t1 = commit(repo_b, "task 1")
    git(repo_b, "checkout", "-q", "-b", "side")
    side = commit(repo_b, "lacks task 2")
    git(repo_b, "checkout", "-q", "main")
    t2 = commit(repo_b, "task 2")
    git(repo_b, "checkout", "-q", "-b", "later")
    ahead = commit(repo_b, "holds both, not in HEAD")
    git(repo_b, "checkout", "-q", "main")
    (run / "_control" / "duties.md").write_text(DUTIES, encoding="utf-8")
    add(run, "build-log-a.md", f"Task 1: done — {t1}", f"Task 2: done — {t2}")
    (run / "lessons.md").write_text(f"# Lessons\nMerged: a->b at {side}\n- Merged: a→b at {ahead}\n", encoding="utf-8")
    r = mon(run, "once")
    assert r.stdout == (
        "WAKE duty D1 due: Merged: a->b — blocks Task 3 (builder b)\n"
        f"WAKE merge-check D1: lessons.md:2 Merged: a->b at {side[:7]} fails: Task 2's {t2[:7]} is not in it\n"
        f"WAKE merge-check D1: lessons.md:3 Merged: a→b at {ahead[:7]} fails: not an ancestor of HEAD in {repo_b}\n"
        "woke: 3\n"
    ), r.stderr
    assert mon(run, "once").stdout == "woke: 0\n"
    add(run, "lessons.md", f"Merged: a->b at {t2}")
    assert mon(run, "once").stdout == "woke: 0\n"
    assert alarms(run) == [("merge-check:D1:2", False), ("merge-check:D1:3", False)]


def test_a_merge_duty_ticks_on_its_own_marker_only_never_on_a_shorter_or_a_longer_one(run):
    repo_b = repo_of(run, "b")
    t1, t2, t5 = commit(repo_b, "task 1"), commit(repo_b, "task 2"), commit(repo_b, "task 5")
    merged = commit(repo_b, "merge the four lanes")
    duties = DUTIES.replace("a->b — blocks Task 3", "a+b+c+d — blocks Task 3")
    duties = duties.replace("b→a — blocks Task 4 (builder a)", "a+b — blocks Task 4 (builder b)")
    (run / "_control" / "duties.md").write_text(duties, encoding="utf-8")
    add(run, "build-log-b.md", f"Task 5: done — {t5}")
    (run / "lessons.md").write_text(f"# Lessons\nMerged: a+b+c+d at {merged}\n", encoding="utf-8")
    r = mon(run, "once")
    assert r.stdout == "WAKE duty D3 due: Merged: a+b — blocks Task 4 (builder b)\nwoke: 1\n", r.stderr
    add(run, "build-log-a.md", f"Task 1: done — {t1}", f"Task 2: done — {t2}")
    (run / "lessons.md").write_text(f"# Lessons\nMerged: a+b at {merged}\n", encoding="utf-8")
    r = mon(run, "once")
    assert r.stdout == "WAKE duty D1 due: Merged: a+b+c+d — blocks Task 3 (builder b)\nwoke: 1\n", r.stderr
    add(run, "lessons.md", f"Merged: a+b+c+d at {merged}")
    assert mon(run, "once").stdout == "woke: 0\n"
    assert [m for m in logged(run) if m.startswith("ticked ")] == [
        f"ticked D3 (lessons.md:2, {merged[:7]})",
        f"ticked D1 (lessons.md:3, {merged[:7]})",
    ]


def test_a_due_duty_left_unticked_past_the_bound_wakes_overdue_duty_once(run):
    (run / "_control" / "duties.md").write_text(DUTIES, encoding="utf-8")
    add(run, "build-log-a.md", "Task 1: done — 1111111", "Task 2: done — 2222222")
    plant(run, duties={"D1": {"due": iso(11 * 60 + 30)}})
    r = mon(run, "once")
    assert r.stdout == "WAKE overdue-duty D1: open 11 min since due, bound 10 min\nwoke: 1\n", r.stderr
    assert alarms(run) == [("overdue-duty:D1", True)]
    assert mon(run, "once").stdout == "woke: 0\n"


def test_a_verdict_wakes_once_and_the_judge_duty_waits_for_every_final_status_but_the_judge_s(run):
    (run / "_control" / "duties.md").write_text(DUTIES, encoding="utf-8")
    add(run, "judge.md", "VERDICT: approve the run")
    (run / "build-log-a.md").write_text("STATUS: done\n", encoding="utf-8")
    r = mon(run, "once")
    assert r.stdout == "WAKE verdict judge.md:2: approve the run\nwoke: 1\n", r.stderr
    (run / "build-log-b.md").write_text("STATUS: done — Tasks 3 and 10\n", encoding="utf-8")
    r = mon(run, "once")
    assert r.stdout == "WAKE duty D2 due: judge approval — blocks the judge\nwoke: 1\n", r.stderr
    assert mon(run, "once").stdout == "woke: 0\n"


def test_done_and_written_lines_are_logged_once_and_never_wake(run):
    add(run, "build-log-b.md", "Task 3: done — 89abcde0")
    add(run, "plan-log.md", "Task 0: index written — 7ffa2b7", "- Task 3: written — b997318")
    assert mon(run, "once").stdout == "woke: 0\n"
    assert mon(run, "once").stdout == "woke: 0\n"
    assert logged(run) == [
        "done Task 3 89abcde (build-log-b.md:2)",
        "written Task 0 7ffa2b7 (plan-log.md:2)",
        "written Task 3 b997318 (plan-log.md:3)",
    ]


def test_status_says_armed_only_while_a_watch_runs_with_a_fresh_heartbeat(run):
    r = mon(run, "status")
    assert (r.returncode, r.stdout) == (1, "not armed: no watch recorded\n")
    proc = subprocess.Popen(
        argv(run, "watch", "--interval", "0.2", "--hours", "0.02"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env_of(run),
    )
    try:
        wait_for(lambda: state(run)["watch"]["last_round"])
        first = state(run)["watch"]["last_round"]
        wait_for(lambda: state(run)["watch"]["last_round"] != first)
        r = mon(run, "status")
        assert r.returncode == 0, r.stdout
        assert re.fullmatch(
            rf"armed since {MINUTE}:\d\d UTC, last round {MINUTE}:\d\d UTC, interval 0\.2 s\n", r.stdout
        )
        add(run, "build-log-b.md", "SANDBOX: allow writes to /srv/x")
        proc.communicate(timeout=20)
    finally:
        proc.kill()
    assert proc.returncode == 0
    ended = state(run)["watch"]["ended_at"]
    r = mon(run, "status")
    assert (r.returncode, r.stdout) == (
        1,
        f"not armed: the last watch woke at {shown(ended)} UTC; re-arm with the same command\n",
    )
    last = iso(600)
    plant(run, watch={"armed": iso(3600), "last_round": last, "interval": 60.0, "ended": None, "ended_at": None})
    r = mon(run, "status")
    assert (r.returncode, r.stdout) == (
        1,
        f"not armed: no round since {shown(last)} UTC (interval 60 s); re-arm with the same command\n",
    )


def test_every_function_of_the_monitor_is_under_50_lines():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    sizes = {n.name: n.end_lineno - n.lineno + 1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert sizes and {name: size for name, size in sizes.items() if size >= 50} == {}
````
  Run: `(ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 300 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests/test_monitor_records.py" 2>&1 | tail -1)`
  Expected: `18 failed` (no `monitor_records.py` yet). Write `scripts/monitor_records.py` against the Interfaces:
  standard library only, `check_formats` and `duty_list` imported as siblings, the state written whole (a temporary
  file, then `os.replace`, as `duty_list.write` does), every function under 50 lines, no shebang (EXE001). Run again.
  Expected: `18 passed`, in about 5 s. Then the three test files of this task together:
  `(ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 300 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}"/scripts/tests/test_{duty_list,check_formats,monitor_records}.py 2>&1 | tail -1)`
  Expected: `50 passed`.
  The wrong versions the planner ran red once against these tests (each failed at least one test): the bound line of
  `_common.md` ignored; a tick on a `Merged:` line quoted in a code span; a tick without the ancestry check; the HEAD
  check without the done tasks' check; the check run in the other builder's checkout; an open alarm waking every round;
  a known request waking every round; a request first seen with its answer waking; no grace for a stalled claim; a
  written task still stalling; one role's two claims (`planner-d`, `manager/planner-d`) taken as a race; a release
  closing nothing; done lines logged every round; done lines woken; a verdict waking every round; a duty ticked in the
  round it becomes due waking; the judge's own status counted for the judge duty; the final status compared by
  equality; `answer` writing past an older open request of its kind; `answer` leaving the overdue alarm open; the
  answer time without its date; `report` rounding the minutes; the heartbeat written only once; `status` ignoring a
  stale heartbeat; `status` ignoring an ended watch; `sys.dont_write_bytecode` left unset (the copied scripts'
  folder gains `__pycache__`); and, added by the fixer for C12: a `Merged:` line ticking a duty whose marker
  holds it (`a+b` ticks `a+b+c+d`), the reverse, and markers compared on their first two lanes.

- [ ] **Step 5 — the README sections** (`scripts/README.md`; `test_docs.py:90-102` wants a `### \`<name>.py\``
  section per script with a `python3 -I scripts/<name>.py` usage line and every option the script parses; Task 10 moves
  the sections to `scripts/docs/`, TD-008). Under `## Watching`, after the `watch_agents.py` section, add:
  ````markdown
  ### `monitor_records.py` — the record monitor: request lines, claims, duties, verdicts
  ```
  python3 -I scripts/monitor_records.py watch <run-dir> [--interval 60] [--hours 8] [--bound <min>] [--grace 300]
  python3 -I scripts/monitor_records.py once|report|status <run-dir>
  python3 -I scripts/monitor_records.py answer <run-dir> <request-id> <text> [--refuse]
  ```
  The manager's background command (spec 5.1.3): it reads the records every interval and exits 0 with one `WAKE` line
  per new event (a `SANDBOX:`, `COPY-REQUEST:`, `CHECKOUT-REQUEST:` or `FF-REQUEST:` line, a request open past the
  bound, a second claim of one task, a stalled claim, a due or overdue duty, a `VERDICT:` line, a failed merge check),
  or exits 1 after `--hours`; the manager answers and re-arms it with the same command. It answers no request itself:
  `answer` writes `SUPPLIED:`, `COPIED:`, `CHECKED-OUT:`, `FF-DONE:` or `REFUSED: <KIND> — <why>` with the time into the
  requester's file. Files: `--state` (`_control/monitor.json`: requests with both times, alarms, the heartbeat), `--log`
  (`_control/monitor.log`), `--duties` (`_control/duties.md`, ticked when a verified `Merged:` line appears), `--registry`
  (`_control/registry.json`, read only), `--config` (default: the agents of `_control/_agents.json`, `_agents.json` and
  `_agents-active.json`, read as `check_formats.py` reads them). `report` prints the request table for the measurement
  page; `status` exits 0 while a watch is armed (its heartbeat at most 2 × interval + 5 s old), else 1 with the reason.

  ### `duty_list.py` — the manager's duty list from the plan
  ```
  python3 -I scripts/duty_list.py extract <plan-dir> [--out <run-dir>/_control/duties.md]
  python3 -I scripts/duty_list.py tick <duty-file> D<n> <evidence>
  ```
  Spec 5.1.2: after the index is written and before the launch, every merge the task table implies (a dependency in
  another builder's lane, or a `Merged:` marker in a depends_on cell), every marker the prose names, every
  `Request point: <KIND> — <why>` line of a task file and the judge's approval, each with the task it blocks. A second
  run appends only the new duties. `tick` writes the `date -u` time and the evidence.
  ````
  In the `check_formats.py` section: the usage line becomes
  `python3 -I scripts/check_formats.py <run-dir> [--repo <checkout>] [--state <monitor.json>] [--json]`, the config
  sentence names `_control/_agents.json` first, and this sentence is added after the hand-over note's: "a request line
  open past the bound `_common.md` names (`Request-line bound: <m> minutes`, default 15; the age from `--state`, else
  the file's mtime) or an answer line that closes none; a `Merged:` line of `lessons.md` without a hex sha or whose sha
  the merged-into checkout lacks; a waiter that counts the Merged marker with `grep -c`; a ticked duty in
  `_control/duties.md` without its UTC time. Open request lines are listed under `open` by kind."
  Run: `(ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 120 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests/test_docs.py" "${SK:?}/scripts/tests/test_skill_example.py" 2>&1 | tail -1)`
  Expected: every test passed, none failed (neither file is edited, lessons.md 20:36 C1-C3).

- [ ] **Step 6 — the real plan and the acceptance checks.**
  ```bash
  X=/home/tite/Desktop/agent-system-run/manager-build-2026-10-29/scratch/builder-b/plan-4f0c974; mkdir -p "${X:?}"
  git -C /home/tite/Desktop/agentic-flow-template/manager-build-plan archive 4f0c974 docs/exec-plans/done/manager-build | tar -x -C "${X:?}"
  python3 -I "${SK:?}/scripts/duty_list.py" extract "${X:?}/docs/exec-plans/done/manager-build"
  ```
  Expected, on this frozen copy of the plan at 4f0c974 (the live plan keeps moving; critic C11), exit 0 and exactly:
  ```
  - [ ] D1 Merged: b->d — blocks Task 5 (builder d) — due when Task 2 done — 00-index.md:105
  - [ ] D2 Merged: a->b — blocks Task 10 (builder b) — due when Task 1 done — 00-index.md:110
  - [ ] D3 Merged: c->b — blocks Task 10 (builder b) — due when Tasks 6, 8 done — 00-index.md:110
  - [ ] D4 Merged: a+b+c+d — blocks Task 11 (builder a) — due when Tasks 1-10 done — 00-index.md:111
  - [ ] D5 Merged: main->… — blocks: see 00-index.md:8 (a marker the task table does not place)
  - [ ] D6 Merged: b->a — blocks: see 00-index.md:115 (a marker the task table does not place)
  - [ ] D7 Merged: a+b — blocks: see 00-index.md:117 (a marker the task table does not place)
  - [ ] D8 judge approval — blocks the judge — due when every record's STATUS is final
  ```
  D2 and D3 are row 10's two markers, each over its own lane's tasks (C12); D6 and D7 are the Lane rule's sentences,
  which the table no longer places since 2fafaa3 (four lanes). No point line: the only `Request point:` lines at a line
  start in the plan's task files are this task's own test fixtures inside a fence (task-03.md:301 and :304 at 4f0c974),
  which rule 3 skips; without that rule they gave two false duties. The acceptance checks
  this task makes runnable, each covered by a test of Steps 2-4: 10.7 (planted `FF-REQUEST:`, `COPY-REQUEST:` and
  `SANDBOX:` lines wake the manager, `answer` writes each answer with its time, `report` gives both times;
  `check_formats.py` exits 0 on a clean run folder and 1 on a request open past the bound); 10.8's third clause (a planted
  second `Task N: started by` line wakes in the first round, so within one interval); 10.10 (`Merged:` lines and waiters
  in `check_formats.py`); 10.11 (`_control/duties.md` dated by its `Extracted` line, ticks with their times, the
  overdue-duty wake); 10.19 (the log shows `armed` after `expired`).

- [ ] **Step 7 — the full checks.**
  ```bash
  (ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 600 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests" 2>&1 | tail -1)
  uv --directory "${W:?}" run ruff check . && uv --directory "${W:?}" run ruff format --check .
  ```
  Expected: `<N0 + 36> passed` (9 + 9 + 18 new) for the skill; `All checks passed!` and no file to reformat. The
  project suite, `harness validate`, `harness docs-check` and `harness map --check` are the verifier's at M1
  (`_common.md:74-76`, Global Constraint 6; C503's rule, lessons.md 22:27 UTC), never this step's. `grep -nP '[\x{10A0}-\x{10FF}\x{1C90}-\x{1CBF}\x{2D00}-\x{2D2F}]' "${SK:?}"/scripts/{monitor_records,duty_list,check_formats}.py "${SK:?}"/scripts/tests/test_{monitor_records,duty_list,check_formats}.py`
  Expected: no output (no letter of a refused block, D1).

- [ ] **Step 8 — commit and log.**
  ```bash
  S=.claude/skills/running-specagent-pipelines/scripts
  git -C "${W:?}" add "$S/monitor_records.py" "$S/duty_list.py" "$S/check_formats.py" "$S/README.md" "$S/tests/test_monitor_records.py" "$S/tests/test_duty_list.py" "$S/tests/test_check_formats.py"
  git -C "${W:?}" commit -m "feat(manager): Task 3 — the record monitor, the claim race detector, the duty list, check_formats extended" -- "$S/monitor_records.py" "$S/duty_list.py" "$S/check_formats.py" "$S/README.md" "$S/tests/test_monitor_records.py" "$S/tests/test_duty_list.py" "$S/tests/test_check_formats.py"
  ```
  Then append `Task 3: done — <sha>` to `build-log-b.md`. Wiki pages, decision pages, `.summary.md` files and the
  `docs/llms.txt` and `wiki/index.md` lines: none in this commit (builder B writes no `wiki/` or `docs/` file, lessons.md
  20:36 C5, C8); the decisions are listed under `## For Task 11`.

## For Task 11
Task 11 adds these decision pages, each `wiki/decisions/<name>.md` with its `.summary.md`, a `wiki/index.md` line and a
`wiki/log.md` line (builder B writes no `wiki/` file); this task closes no tracker row.
- `monitor-answers-no-request`: the record monitor detects and wakes; the manager answers with
  `monitor_records.py answer` (departure 1; spec 5.5, need 4): every answer changes a worktree or the sandbox, and the
  manager's guards cover only the commands the manager runs.
- `request-answer-lines`: a request line is answered in the requester's own file, below it, by `SUPPLIED:`, `COPIED:`,
  `CHECKED-OUT:`, `FF-DONE:` or `REFUSED: <KIND> — <why>`, each ending with its `date -u` time; an answer closes the
  oldest open request of its kind (spec 5.4, 8.3.3, 10.7). Evidence: the template-core run answered a `COPY-REQUEST:`
  with `COPIED:` in the requester's file (`experiments/template-core/build-log-b.md:22` and `:24`), with its time inside
  the text rather than at a fixed place, so no script could read it.
- `duty-list-from-the-plan`: the manager's duties are extracted from the plan after the index and before the launch,
  checked at every wake-up, and the merges ticked by the monitor on a verified `Merged:` line (spec 5.1.2, 8.2.3, 10.11).

## Deferred
- The monitor answering a request itself (need 4 allows it): not until the manager's guards (spec 5.5) cover the
  commands the monitor would run; departure 1.
- Point duties (`COPY-REQUEST`, `CHECKOUT-REQUEST`, `FF-REQUEST` points) ticked by `answer`: ticked by hand with
  `duty_list.py tick` here; a point line names no request id, so `answer` cannot know which duty it settles.
- The vault measurement page with the request and answer times (`report`'s table): the main session's page (D6); the
  template ships the script.
- The owner's surface showing the monitor's alarms: Task 5, which reads `_control/monitor.json` (Contracts).
- The `SKILL.md` lines and the decision pages: Task 11 (Contracts, `## For Task 11`).
- The README sections moved to `scripts/docs/`: Task 10 (TD-008).

## Verified
- `scripts/check_formats.py` at b0db935 (the skill files of e32d413): `main` is lines 161-240 (80 lines) and `ids`
  92-158 (67 lines), so Step 3 splits `main` and its function-size test exempts `ids`; `CONFIGS` there is
  `("_agents.json", "_agents-active.json")`; `scripts/tests/test_check_formats.py` holds 14 tests, one of them pinning
  the whole error set (`set(out)`).
- `scripts/tests/test_docs.py:90-102`: every script needs a `### \`<name>.py\`` section in `scripts/README.md` with its
  `python3 -I scripts/<name>.py` usage line and every option it parses (Step 5).
- `scripts/README.md:9` is `## Watching` (the `watch_agents.py` section runs to :55) and `:138` is the `check_formats.py`
  section (Step 5).
- `scripts/findings_report.py:28-30`: `sys.dont_write_bytecode = True`, the `sys.path.insert(0, …)`, then the sibling
  import with no `noqa` (the precedent); the older scripts are mode 755 with a shebang (`ls -l scripts/*.py`), the
  three new ones have no shebang (lessons.md 22:23 UTC: ruff 0.16.10's EXE001 on a 644 file with one, measured by
  planner-b; the tests run them as `[sys.executable, "-I", ...]`).
- ruff 0.16.10 with the plan's `pyproject.toml` (line length 120): the three test files pass `ruff check` and
  `ruff format --check` as written here.
- `.claude/rules/python.md:9`: "Keep functions under 50 lines; extract before you nest a third level."
- 146 skill tests collected at b0db935 (the N0 of Step 1 before Task 2's tests).
- `uv --help`, line 57: `--directory` runs the command in that directory (Step 7).
- Step 6's duty lines: the scratch `duty_list.py extract` (the fixer's, with the C11-C12 rules) on
  `git archive 4f0c974 docs/exec-plans/done/manager-build`, 2026-10-29; without the fence rule it adds
  `COPY-REQUEST point — blocks Task 3 (builder b) — task-03.md:301` and `FF-REQUEST point … task-03.md:304`.
- CommonMark 0.31.2, 4.5 Fenced code blocks (https://spec.commonmark.org/0.31.2/#fenced-code-blocks): a fence is three
  or more backticks or tildes, indented up to three spaces; the closing fence is the same character, at least as long.
- The scratch implementations pass the tests as written here: `9 passed` (Step 2), `23 passed` with the `ACK 1a2b3c4d`
  line of K3 (Step 3), `18 passed` (Step 4), `50 passed` together; `9 failed` with `duty_list.py` absent, `18 failed`
  with `monitor_records.py` absent; the appended check_formats tests against the base script (the plan worktree's,
  a76caa9, the skill files of e32d413) give `9 failed, 14 passed` (re-measured by the fixer for C11-C12, A1-A3).
- Wrong versions run red once: 17 of `duty_list.py` (Step 2), 15 of `check_formats.py` (Step 3), 29 of
  `monitor_records.py` (Step 4), each listed in its step (the 11 of `duty_list.py` re-run red on the fixer's code).
- `git --version`: 2.43.0 (`git init -b` exists since 2.28). `git merge-base --is-ancestor A B` exits 0 when A is an
  ancestor of B or A itself (git-merge-base(1); the last check of the merge-check test ticks on the done sha itself).
- Python 3.12.3: `datetime.UTC` (3.11+); `argparse.ArgumentParser(parents=[…], add_help=False)` and
  `add_subparsers(dest=…, required=True)` (https://docs.python.org/3.12/library/argparse.html); `os.replace` is atomic
  on POSIX (https://docs.python.org/3.12/library/os.html#os.replace).
