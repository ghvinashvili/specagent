# Task 4 — Pre-flight, the launch table, the clock rule, timeouts from the cases, capacity around the five-hour window, the size rule

planner: a
builder: a
depends_on: —
files: `<skill>/scripts/manager/preflight.py` (new), `<skill>/scripts/tests/test_preflight.py` (new), `<skill>/example/launch.md` (new), `<skill>/scripts/tests/test_skill_example.py` (`FILES` gains `launch.md`), `<skill>/example/README.md` (steps 1 and 4, the launch step, `launch.md`), `<skill>/example/common.md` (the clock rule, the request lines and their bound, the ACK rule), `<skill>/example/sim_bwrap.py` (`~/` expanded in its sandbox paths, C502), `<skill>/references/preflight-and-capacity.md` (new), `<skill>/scripts/tests/test_skill_md.py` (`MOVED` gains it), `<skill>/SKILL.md` (a link line; three rows shortened), `<skill>/references/launch.md` (departure 1), `<skill>/scripts/manager/README.md` (`## preflight.py` with its `Usage:` lines), `wiki/decisions/the-launch-table-and-one-yes.md` and its `.summary.md`, `wiki/index.md`, `wiki/log.md`
acceptance: 10.12, 10.15, 10.16, 10.19 (no `sleep` loop), 10.20

`<skill>` is `.claude/skills/running-specagent-pipelines` in builder A's worktree. Builder A builds Tasks 1, 4 and 11
in that order (Global Constraint 14), so this task lands on Task 1's tree: `scripts/manager/README.md` and `scripts/tests/test_skill_md.py`
exist (Task 1 creates them), `SKILL.md`, `example/common.md` and `example/README.md` carry Task 1's edits. Every figure
below was measured on ff3354a (the plan worktree), whose tree outside `docs/exec-plans/done/manager-build/` equals
builder A's 960ca4e (`git diff --stat ff3354a 960ca4e` lists only the plan's files).

Spec carried: 5.1.1 (the launch message and its table), 5.1.3 (pre-flight), 5.1.4 (capacity), 5.1.5 (the clock), 5.5
(the deny checks and the refusal of a `_control/` read), 5.9.1 (a suite's timeout from its cases), 8.2.4, 8.2.5, 8.2.8,
8.2.14 (asks only before a launch, a destructive action, a merge into `main` or spending; numbers and a record path in
every status), 8.3.4 (the clock rule and the simulation duty), question 6 (answer 6a: the `_launch.md` table).

## Contracts
Fixed by this task (other tasks read them; the plan fixer carries each into the task that has not been written):
- `example/launch.md` (the run's `_launch.md`): the lines `Purpose:`, `Size:`, `Model rule:`, `Estimate:`, `Budget:`,
  `Usage:` at line start, one table whose header has the cells `role`, `lane`, `settings`, `skills`, `ECC texts`,
  `cost estimate` (read by name, in any order, more cells allowed; spec :558), one row per role with the settings path
  in backticks, and `Yes: <YYYY-MM-DDTHH:MMZ> — <roles> — <what the owner approved>` lines appended after each yes.
  Task 2's registry reads `role`, `lane` and `settings` from that table.
- `Budget:` (planner-b, for Task 5): `$<amount>`, e.g. `Budget: $40 for the run; at $40 the manager launches nothing new
  and asks the owner`; Task 5 compares the run's cost with the first `$<amount>` of `_launch.md`'s first `Budget:` line.
- `Launched:` (plan-fixer, for Task 5, C17): when the first role starts, the manager appends `Launched: ` and the UTC
  time as `date -u +%Y-%m-%dT%H:%M:%SZ` prints it to `_launch.md`, once (no relaunch, resume or hand-over changes it).
  No key line: the `launch` check neither requires nor reads it, and `example/launch.md` names it in its prose, never at
  a line start. Task 5 takes the run's start from the first `Launched:` line, else the earliest `launched_at`.
- `_control/usage.json` (Task 5 reads only these fields): `{"readings": [{"taken_at": "<YYYY-MM-DDTHH:MMZ>",
  "source": "get_usage", "extra_usage": <bool>, "limits": [{"name": "<five-hour|weekly|...>", "used_pct": <number>,
  "resets_at": "<YYYY-MM-DDTHH:MMZ>"}]}]}`; the newest reading is the one with the latest `taken_at`; the manager
  appends a reading before each launch and never edits an old one. Times as `date -u +%Y-%m-%dT%H:%MZ` prints them.
- `_control/preflight.json` (written by `check`): `{"written_at", "run_dir", "roles", "results": [{"check", "agent",
  "status", "detail"}], "passed"}`.
- `example/common.md` carries `Request-line bound: 15 minutes` at line start (Task 3 parses
  `^Request-line bound: (\d+) minutes?\b`), the four request lines `SANDBOX: <what was refused> — <why the step needs it>`,
  `COPY-REQUEST: <stage> -> <worktree>`, `CHECKOUT-REQUEST: <sha>`, `FF-REQUEST: <branch> <sha> -> <branch> <sha>`, and
  the answers the main session appends below a request in the requester's own record file: `SUPPLIED:` (SANDBOX),
  `COPIED:` (COPY-REQUEST), `CHECKED-OUT:` (CHECKOUT-REQUEST), `FF-DONE:` (FF-REQUEST) or `REFUSED: <KIND> — <why>`
  (`<KIND>` is the request's prefix); each answer closes the oldest open request of its kind (Task 3's REQUEST and REPLY
  patterns). Task 3's `monitor_records.py answer <id> <text>` refuses, exit 2, while an older request of that kind in
  that file is open: stderr `<id>: answer <older id> first (<file>:<its line>)`, ids `<file>:<KIND>:<n>`
  (`task-03.md:192-197`, 8d86fb3), so `example/common.md` may say to answer the oldest request first.
- `example/common.md` carries the ACK rule in Task 2's order form: an order ends with
  `Order <msg_id>: append the line `ACK <msg_id>` to <record> before anything else.` (`<msg_id>` 8 lowercase hex).
Read from other tasks (stubbed in the tests):
- Task 3 (planner-d's contract; `task-03.md:66-72`, `:185`, `:201-205` at 8d86fb3): the pre-flight runs
  `python3 -I <skill>/scripts/monitor_records.py status <run-dir>` and reports its exit and its one line, which is:
  exit 0 `armed since <armed> UTC, last round <last_round> UTC, interval <s> s`; exit 1 `not armed: no watch recorded`,
  `not armed: the last watch woke at <ended_at> UTC; re-arm with the same command` (`expired at` for `woke at` after
  an expiry) or `not armed: no round since <last_round> UTC (interval <s> s); re-arm with the same command` (the
  heartbeat older than 2 × interval + 5 s); exit 2 stderr `<run-dir>: no such run folder` with stdout empty, so the
  detail then comes from stderr. Times are `YYYY-MM-DD HH:MM:SS`; `<s>` is formatted with `:g`.
- Task 3: `scripts/check_formats.py <run-dir>` finds the config at `<run-dir>/_control/_agents.json` when
  `<run-dir>/_agents.json` is absent (today it reads only the run folder's root, `check_formats.py:61-65`).
- Task 2: `example/agents.json` and `agents-judge.json` lose `--model opus` from `common` (Global Constraint 10); a run's
  `_control/_agents.json` names each settings file as `_control/<role>-settings.json` (relative to the run folder; index row 4 at 3e38124).
- Task 1: `scripts/manager/README.md` has `## <script>` with a `Usage:` line per tool (Task 1's `test_catalogue.py`, task-01.md:584 at 4f0c974); `scripts/tests/test_skill_md.py` keeps
  `MOVED` as the dict `{"<file>.md": "<title>"}` of `test_docs.py:27-33`; Task 1 leaves `SKILL.md` at most 12,000 bytes
  and does not edit the rows `Ask before launching any agent`, `No early compaction in SpecAgent sessions` or
  `Only the plugins and MCP a role needs`; its step 5c (task-01.md:1072-1076 at 4f0c974) already drops `--model opus` from
  `references/launch.md`'s launch command and reads the settings from `<run-dir>/_control/<role>-settings.json`.

## Departures
1. One file beyond the index cell: `references/launch.md`, which takes the How text of the `SKILL.md` rows
   `No early compaction in SpecAgent sessions` and `Only the plugins and MCP a role needs` (bytes for the link line). Its
   launch command is Task 1's (task-01.md:1053-1057, step 5c: no `--model`, the settings read from
   `<run-dir>/_control/<role>-settings.json`); this task's test 18 only guards that state.
2. A suite's timeout counts `trials x sessions x timeout_minutes` per case, not the plain sum of `timeout_minutes` that
   10.20 names: the runner applies `timeout_minutes` to each session run (`evals.py:215`), runs `sessions` of them per
   trial (`evals.py:251`) and `trials` trials per case (`evals.py:476`). At ff3354a the plain sum is 100 minutes; the
   two suites can take 175.
3. The capacity projection ends at the earlier of the window's reset and the run's expected end (`--hours`, default 5):
   an hour's rate projected to a weekly reset days away would fail every launch.
4. `_launch.md` names no model (spec :558 has the message name the models): the roles can read the run folder's
   `_*.md`, so the models go in the manager's chat message only and the model check reads `_launch.md` like any brief.

## Interfaces
`<skill>/scripts/manager/preflight.py`, standard library only, run as `python3 -I`; argparse subcommands; exit 2 on a
usage error (argparse's own). Times are parsed with `datetime.fromisoformat` (Python 3.12 takes `2026-10-29T18:24Z`);
a time without a zone is UTC.

`check <run-dir> --checkout DIR [--config P] [--launch P] [--roles A,B] [--unsandboxed ROLE]... [--sim P | --no-sim]
[--formats P] [--monitor P | --no-monitor] [--min-free-mb N] [--usage-age MIN] [--max-pct PCT] [--scale X] [--hours H]
[--yes] [--now ISO]`
- Defaults: `--config <run>/_control/_agents.json`, `--launch <run>/_launch.md`, `--roles` every agent of the config in
  its order, `--sim <skill>/example/sim_bwrap.py`, `--formats <skill>/scripts/check_formats.py`,
  `--monitor <skill>/scripts/monitor_records.py`, `--min-free-mb 512`, `--usage-age 30`, `--max-pct 80`, `--scale 1`,
  `--hours 5`, `--now` the current UTC time. `<run>` and `--checkout` are resolved to absolute paths.
- Prints one line per result, `PASS|FAIL|SKIP <check>[ <agent>]: <detail>`, in this order: `config`, `model`, then per
  role `blind`, `ancestor`, `probe`, `worktree`, then `waiters`, `formats`, `monitor`, `disk`, `usage`, `launch`; a
  `config` FAIL stops the rest. Last line `preflight: <p> passed, <f> failed, <s> skipped — <run>/_control/preflight.json`;
  writes that file (creating `_control/` if needed) with `written_at` = `--now` as `%Y-%m-%dT%H:%MZ`, `roles` the list
  checked, `results` in print order (`agent` null for run-wide checks), `passed` true when no FAIL. Exit 0 when no FAIL,
  else 1.
- `config`: the config lies inside `<run>/_control/` and parses with an `agents` object; every `--roles` name is an agent;
  every checked agent's `settings` (relative to `<run>` unless absolute) lies inside `<run>/_control/` and parses. FAIL
  names the file and the role.
- `model`: `(?i)\b(?:fable|opus|sonnet|haiku)\b|--model\b` (the source builds the four words from parts, as the tests
  do) over the config, every `<run>/_control/_agents*.json`, every `<run>/_*.md` and `<run>/lessons.md`; settings files
  are not read (the `model` key belongs there). FAIL lists `<path relative to run>:<line>` for each hit.
- `blind <role>`: the settings' `permissions.deny` holds the nine rules `Read(~/.claude/projects/**)`,
  `Read(/<run-dir>/_control/**)`, `Read(/<checkout>/docs/handoff/**)`, `Read(//proc/**)`, `Bash(claude agents:*)`,
  `Bash(claude logs:*)`, `Bash(claude attach:*)`, `Bash(ps:*)`, `Bash(pgrep:*)` with `<run-dir>` and `<checkout>`
  replaced by the absolute paths (so `Read(//abs/run/_control/**)`), compared as strings; a sandboxed role also has
  `sandbox.enabled` true, `sandbox.failIfUnavailable` true, `sandbox.allowUnsandboxedCommands` false and
  `sandbox.filesystem.denyRead` holding `~/.claude/projects`, `<run>/_control` and `<checkout>/docs/handoff` (trailing
  `/` ignored). FAIL lists every missing item.
- `ancestor <role>` (SKIP for an `--unsandboxed` role): each `Edit(...)` and `Write(...)` deny rule is resolved (`//x` to
  `/x`, `~/x` to `$HOME/x`, `/x` to `<cwd>/x`, `x` to `<cwd>/x`, a trailing `/**` and `/` removed), each
  `sandbox.filesystem.denyWrite` and `allowWrite` entry likewise (`~/x` to `$HOME/x`, absolute kept, relative under
  `<cwd>`); a pair fails when `w == d or w.startswith(d + "/")` for a deny path `d` and an allowWrite path `w`. A deny path
  below an allowWrite path (`.git/hooks` under the worktree) passes. FAIL names the rule and the path.
- `probe <role>` (SKIP for an `--unsandboxed` role or with `--no-sim`; FAIL `bwrap not on PATH` when `--sim` is not
  given and `shutil.which("bwrap")` is None): a mark `.preflight-<8 hex>` is touched in every existing allowWrite
  directory (an entry `~/x` is `$HOME/x`, by `os.path.expanduser` as `ancestor` resolves it, for its existence check,
  its mark and the detail; C502) and in `<run>/_control/`, then `cat <config>` prints `PREFLIGHT-READ-OK` or
  `PREFLIGHT-READ-REFUSED`; the probe is one bash string run as `[sys.executable, "-I", <sim>, <config>, <role>,
  <probe>]` (timeout 120 s). PASS when every allowWrite mark exists on disk, the `_control/` mark does not, and the
  output holds `PREFLIGHT-READ-REFUSED`. FAIL details: `write refused in <dirs>`, `write into <run>/_control/ allowed`,
  `read of <config> allowed`. Every mark is removed afterwards.
- `worktree <role>`: the agent's `cwd` is a directory, has `.git` (directory or file) and, when it has
  `pyproject.toml`, a `.venv/` directory (`uv sync` once per worktree). FAIL names what is missing.
- `waiters`: every token `[\w./<>~-]*wait_for_[a-z_]+\.py` in `<run>/_*.md` has no `<` or `>` and resolves (absolute, else
  `<run>/<basename>`) to a file directly in the run folder. FAIL names the brief and the token.
- `formats`: `[sys.executable, "-I", <formats>, <run>]` exits 0; the detail is `exit <n>: <line>`, where `<line>` is
  the last line of stdout, or of stderr when stdout is empty (Task 3's `status` exit 2 writes only to stderr; a line
  on stderr never replaces a stdout line).
- `monitor` (SKIP with `--no-monitor`): `[sys.executable, "-I", <monitor>, "status", <run>]` exits 0; FAIL when the file
  is missing or the exit is not 0; the detail is `exit <n>: <line>` as for `formats`.
- `disk`: `shutil.disk_usage(p).free // 2**20` is at least `--min-free-mb` for the run folder, `tempfile.gettempdir()`
  and each checked role's cwd.
- `usage`: `<run>/_control/usage.json` (Contracts). FAIL when it is missing or does not parse, when the newest reading is
  more than `--usage-age` minutes before now, when a limit of the newest reading has `used_pct >= --max-pct`, or when the
  rate from the latest earlier reading of the same `name` and the same `resets_at` (rising values only) times `--scale`
  reaches 100% before `min(resets_at, now + --hours)`: `100% at taken_at + (100 - used) / rate hours`.
- `launch`: the file exists; each key line of the Contracts is present and non-empty; `Size:` holds a digit;
  `Estimate:` matches `\b\d+ roles?\b`, `\b\d+(?:-\d+)? sessions?\b`, `\$\d` and `\bper unit\b`; the first table whose
  header cells (spaces and backticks stripped) include `role`, `lane` and `settings` (Task 2's K2) has the six cells; its rows (after the separator) name exactly the agents of every
  `<run>/_control/_agents*.json`; each row's `role` cell (backticks stripped) is an agent name and its `settings` cell, stripped of spaces and
  backticks, equals that agent's `settings`. With
  `--yes`: every checked role is named (`(?<![\w-])<role>(?![\w-])`) in a `Yes: <YYYY-MM-DDTHH:MMZ> — <text>` line
  stamped no later than now, and no `Yes:` line is stamped after now.

`timeout DIR... [--check MIN]`: a DIR holding `task.yaml` is one case, else each `DIR/*/task.yaml` (sorted). A case with
`session: false` is code-only and skipped; a session case needs `timeout_minutes:` (else `FAIL <suite>/<case>: a session
case without timeout_minutes`, exit 1); `trials:` and `sessions:` default to 1 (`evals.py:476`, `:251`). Prints
`<suite>/<case>: <trials> x <sessions> x <minutes> min = <product> min` per session case, then
`total: <sum> min over <n> session cases (<k> code-only skipped)`; with `--check M`: `FAIL timeout: …` and exit 1 when
`M < sum`, else `PASS timeout: …`. Parsed with `re` (the standard library has no YAML).

`polls TRANSCRIPT...`: every `tool_use` named `Bash` in an `assistant` line of the JSONL files; a command is a sleep loop
when `\bsleep\b` occurs between a `\bdo\b` and its matching `\bdone\b` (nesting counted; a `done` before any `do` is
ignored), or when it holds both `\bwhile\b` and `\btime\.sleep\(`. Prints `sleep loop: <file>:<line>: <first 80 chars>`
per hit and `polls: <n> Bash commands, <k> sleep loops`; exit 1 when `k > 0`.

`clock RECORD... [--transcript JSONL]... [--slack MIN]` (`--slack 10`): a stamp is `YYYY-MM-DDTHH:MM(:SS)?Z`,
`YYYY-MM-DD HH:MM(:SS)?( UTC)?` or `HH:MM(:SS)? UTC` (two-digit hours); after the stamps are cut out of a line, each
token `(?<![\w:.])\d{1,2}:[0-5x][0-9x](?::[0-5][0-9])?(?![\w:])` is a problem `not in date -u form: <token>`. A line with a stamp
is matched to the earliest transcript `tool_use` (by its line's `timestamp`) whose new text holds the stripped line:
`content` of a Write, `new_string` of an Edit, `command` of a Bash. A stamp without a date takes the writer's day, the
day before or the day after, whichever is nearest the writer's time. A gap of more than `--slack` whole minutes is a
problem `<stamp> was written at <time>, <gap> min apart` (`<time>` the writer's `timestamp` as `%Y-%m-%dT%H:%M:%SZ`); a line no tool wrote is counted, not failed. Prints
`<record>:<line>: <problem>` per problem and `clock: <n> stamped lines, <m> matched a writer, <k> problems`; exit 1
when `k > 0`.

## Steps
Every command runs from builder A's checkout root on Task 1's commit; `SK` is `.claude/skills/running-specagent-pipelines`.
Task 1's tree has the figures of Task 1's Step 8a Expected line: 202 skill tests, `SKILL.md` 11750 bytes.
This task's own figures were measured on a scratch copy of the skill at ff3354a with the two edits of
Task 1 that it builds on (5c's `--model opus` drop in `references/launch.md`, a stand-in `scripts/manager/README.md`).

- [ ] **Step 1 — the tests.** Write `<skill>/scripts/tests/test_preflight.py` (37 tests). The stubs `FAKE_SIM`,
  `FAKE_FORMATS` and `FAKE_MONITOR` stand in for `example/sim_bwrap.py`, Task 3's `check_formats.py` and Task 3's
  `monitor_records.py status` (its exact lines, Contracts), so no test starts bwrap, a session or another task's script:
````python
"""The manager's pre-flight (`scripts/manager/preflight.py`): the checks before a launch, the launch table and the yes,
capacity, timeouts from the eval cases, the polling check and the clock check. Every test runs the script as the manager
does, on a run folder built in tmp_path, with fake `sim_bwrap.py`, `check_formats.py` and `monitor_records.py` scripts;
no test starts a session or a sandbox."""

import json
import re
import shutil
import subprocess
import sys

import pytest
from transcript_home import SCRIPTS

PREFLIGHT = SCRIPTS / "manager" / "preflight.py"
SKILL = SCRIPTS.parent
NOW = "2026-10-29T20:00Z"
# Built from parts, so that no skill file spells a model name (Global Constraint 10).
OPUS, SONNET = "op" + "us", "son" + "net"

NINE = (
    "Read(~/.claude/projects/**)",
    "Read(/<run-dir>/_control/**)",
    "Read(/<checkout>/docs/handoff/**)",
    "Read(//proc/**)",
    "Bash(claude agents:*)",
    "Bash(claude logs:*)",
    "Bash(claude attach:*)",
    "Bash(ps:*)",
    "Bash(pgrep:*)",
)

FAKE_SIM = """
import os, subprocess, sys
config, agent, probe = sys.argv[1:4]
with open(os.environ["FAKE_SIM_LOG"], "a", encoding="utf-8") as log:
    log.write(agent + "\\n")
mode = os.environ.get("FAKE_SIM_MODE", "good")
if mode in ("good", "ro"):
    probe = probe.replace(os.environ["FAKE_SIM_CONTROL"], os.environ["FAKE_SIM_NOWHERE"])
if mode == "ro":
    probe = probe.replace("touch ", "true ")
out = subprocess.run(["/bin/bash", "-c", probe], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
print(out.stdout + out.stderr)
"""

FAKE_FORMATS = """
import os, sys
with open(os.environ["FAKE_FORMATS_LOG"], "a", encoding="utf-8") as log:
    log.write(" ".join(sys.argv[1:]) + "\\n")
code = int(os.environ.get("FAKE_FORMATS_EXIT", "0"))
print("checked 4 files")
if code:
    print("plan-log.md:1: line 1 is not a STATUS line")
sys.exit(code)
"""

FAKE_MONITOR = """
import os, sys
with open(os.environ["FAKE_MONITOR_LOG"], "a", encoding="utf-8") as log:
    log.write(" ".join(sys.argv[1:]) + "\\n")
mode = os.environ.get("FAKE_MONITOR_ARMED", "1")
if mode == "1":
    print("armed since 2026-10-29 19:50:00 UTC, last round 2026-10-29 19:59:30 UTC, interval 30 s")
    sys.exit(0)
if mode == "gone":
    print(f"{sys.argv[2]}: no such run folder", file=sys.stderr)
    sys.exit(2)
print("not armed: no watch recorded")
print("read 0 watch records", file=sys.stderr)
sys.exit(1)
"""

LAUNCH = """# Launch: demo run

Purpose: build the demo plan's two lanes
Size: one context cannot hold it: 11 tasks at 120k-180k tokens each, measured on the last run
Model rule: the model is the `model` key of each role's settings file under `_control/`
Estimate: 3 roles, one fresh session per unit, 12-16 sessions, $40-$60 by usage_report.py
Budget: 300 calls and 4000000 output tokens per session
Usage: five-hour 40% (resets 2026-10-29T21:30Z), weekly 30% (resets 2026-11-04T13:00Z), read at 2026-10-29T19:55Z

| role | lane | work | settings | skills | ECC texts | cost estimate |
|---|---|---|---|---|---|---|
| planner | a | writes the plan | `_control/planner-settings.json` | running-specagent-pipelines | planner | $10 |
| builder-a | a | builds lane A | `_control/builder-a-settings.json` | running-specagent-pipelines | tdd-guide | $25 |
| judge | - | reads the record once | `_control/judge-settings.json` | - | - | $5 |
"""


class Run:
    """A ready run folder: two roles (a planner in a plain checkout, a builder in a worktree with its own .venv), a judge
    config, settings under `_control/`, a brief naming a waiter, `_launch.md`, `usage.json` and the three fakes."""

    def __init__(self, tmp_path):
        self.root = tmp_path
        self.run, self.checkout = tmp_path / "run", tmp_path / "checkout"
        self.plan, self.wt, self.home = tmp_path / "plan", tmp_path / "wt-a", tmp_path / "home"
        self.control = self.run / "_control"
        for d in (
            self.control,
            self.checkout / ".git",
            self.checkout / "docs" / "handoff",
            self.plan / ".git",
            self.wt / ".venv",
            self.home / ".cache",
            tmp_path / "bin",
            tmp_path / "fakes",
        ):
            d.mkdir(parents=True)
        (self.wt / ".git").write_text("gitdir: ../checkout/.git/worktrees/wt-a\n", encoding="utf-8")
        (self.wt / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
        self.config = self.control / "_agents.json"
        self.planner_settings = self.control / "planner-settings.json"
        self.builder_settings = self.control / "builder-a-settings.json"
        self.write_json(
            self.config,
            {
                "common": [
                    "--strict-mcp-config",
                    "--effort",
                    "max",
                    "--permission-mode",
                    "auto",
                    "--setting-sources",
                    "local",
                ],
                "agents": {
                    "planner": {
                        "cwd": str(self.plan),
                        "add_dirs": [str(self.run)],
                        "settings": "_control/planner-settings.json",
                    },
                    "builder-a": {
                        "cwd": str(self.wt),
                        "add_dirs": [str(self.run)],
                        "settings": "_control/builder-a-settings.json",
                    },
                },
                "budget": {"calls": 300, "output_tokens": 4000000},
            },
        )
        self.write_json(
            self.control / "_agents-judge.json",
            {
                "agents": {"judge": {"cwd": str(self.run), "add_dirs": [], "settings": "_control/judge-settings.json"}},
            },
        )
        self.write_json(self.planner_settings, self.settings([self.plan, self.run]))
        self.write_json(self.builder_settings, self.settings([self.wt, self.run, self.checkout / ".git"]))
        self.write_json(self.control / "judge-settings.json", self.settings([self.run]))
        (self.run / "_wait_for_log.py").write_text("# waiter\n", encoding="utf-8")
        self.common = f"Wait with `python3 -I {self.run}/_wait_for_log.py {self.run}/plan-log.md 'Task 4: written'`.\n"
        (self.run / "_common.md").write_text(self.common, encoding="utf-8")
        (self.run / "_launch.md").write_text(LAUNCH, encoding="utf-8")
        self.usage(
            [
                ("2026-10-29T19:00Z", [("five-hour", 30, "2026-10-29T21:30Z"), ("weekly", 30, "2026-11-04T13:00Z")]),
                ("2026-10-29T19:55Z", [("five-hour", 40, "2026-10-29T21:30Z"), ("weekly", 30, "2026-11-04T13:00Z")]),
            ]
        )
        self.sim, self.formats, self.monitor = (tmp_path / "fakes" / n for n in ("sim.py", "formats.py", "monitor.py"))
        for path, text in ((self.sim, FAKE_SIM), (self.formats, FAKE_FORMATS), (self.monitor, FAKE_MONITOR)):
            path.write_text(text, encoding="utf-8")
        self.sim_log, self.formats_log, self.monitor_log = (
            tmp_path / n for n in ("sim.log", "formats.log", "monitor.log")
        )
        self.env = {
            "HOME": str(self.home),
            "PATH": f"{tmp_path / 'bin'}:/usr/bin:/bin",
            "FAKE_SIM_LOG": str(self.sim_log),
            "FAKE_SIM_CONTROL": str(self.control),
            "FAKE_SIM_NOWHERE": str(tmp_path / "nowhere"),
            "FAKE_FORMATS_LOG": str(self.formats_log),
            "FAKE_MONITOR_LOG": str(self.monitor_log),
        }

    def settings(self, allow_write):
        return {
            "permissions": {
                "allow": [],
                "deny": [r.replace("<run-dir>", str(self.run)).replace("<checkout>", str(self.checkout)) for r in NINE],
            },
            "sandbox": {
                "enabled": True,
                "autoAllowBashIfSandboxed": True,
                "allowUnsandboxedCommands": False,
                "failIfUnavailable": True,
                "filesystem": {
                    "allowWrite": [str(p) for p in allow_write],
                    "denyRead": ["~/.claude/projects", f"{self.control}", f"{self.checkout}/docs/handoff"],
                },
            },
            "env": {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": ""},
        }

    @staticmethod
    def write_json(path, data):
        path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")

    def edit(self, path, change):
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data)
        self.write_json(path, data)

    def usage(self, readings):
        self.write_json(
            self.control / "usage.json",
            {
                "readings": [
                    {
                        "taken_at": taken,
                        "source": "get_usage",
                        "extra_usage": False,
                        "limits": [{"name": n, "used_pct": p, "resets_at": r} for n, p, r in limits],
                    }
                    for taken, limits in readings
                ]
            },
        )

    def args(self, *extra):
        """`--sim` and `--monitor` are left out when `extra` names `--no-sim`, `--no-monitor` or another `--monitor`."""
        sim = [] if "--no-sim" in extra else ["--sim", self.sim]
        monitor = [] if {"--no-monitor", "--monitor"} & set(map(str, extra)) else ["--monitor", self.monitor]
        return [
            "check",
            self.run,
            "--checkout",
            self.checkout,
            *sim,
            "--formats",
            self.formats,
            *monitor,
            "--now",
            NOW,
            *extra,
        ]


def preflight(*args, env):
    return subprocess.run(
        [sys.executable, "-I", str(PREFLIGHT), *map(str, args)],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )


def results(proc):
    lines = [re.fullmatch(r"(PASS|FAIL|SKIP) ([a-z]+)(?: ([\w-]+))?: (.*)", line) for line in proc.stdout.splitlines()]
    return [m.groups() for m in lines if m]


def found(proc, check, agent=None):
    """The (status, detail) pairs of one check."""
    return [(s, d) for s, c, a, d in results(proc) if c == check and a == agent]


def test_a_ready_run_passes_sixteen_checks_writes_the_result_file_and_leaves_no_probe_mark(tmp_path):
    r = Run(tmp_path)
    proc = preflight(*r.args(), env=r.env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    per_role = [
        (s, c, a)
        for a in ("planner", "builder-a")
        for s, c in (("PASS", "blind"), ("PASS", "ancestor"), ("PASS", "probe"), ("PASS", "worktree"))
    ]
    run_wide = [("PASS", c, None) for c in ("waiters", "formats", "monitor", "disk", "usage", "launch")]
    assert [(s, c, a) for s, c, a, _ in results(proc)] == [
        ("PASS", "config", None),
        ("PASS", "model", None),
        *per_role,
        *run_wide,
    ]
    assert proc.stdout.splitlines()[-1] == f"preflight: 16 passed, 0 failed, 0 skipped — {r.control}/preflight.json"
    saved = json.loads((r.control / "preflight.json").read_text(encoding="utf-8"))
    assert saved["passed"] is True and saved["written_at"] == NOW and saved["roles"] == ["planner", "builder-a"]
    assert saved["run_dir"] == str(r.run) and len(saved["results"]) == 16
    assert {k: saved["results"][2][k] for k in ("check", "agent", "status")} == {
        "check": "blind",
        "agent": "planner",
        "status": "PASS",
    }
    assert sorted(str(p) for p in tmp_path.rglob(".preflight-*")) == []
    assert r.sim_log.read_text(encoding="utf-8").split() == ["planner", "builder-a"]
    assert r.formats_log.read_text(encoding="utf-8").split() == [str(r.run)]
    assert r.monitor_log.read_text(encoding="utf-8").split() == ["status", str(r.run)]


def test_a_model_in_the_config_a_brief_or_lessons_fails_and_a_model_key_in_a_settings_file_does_not(tmp_path):
    r = Run(tmp_path)
    r.edit(r.planner_settings, lambda s: s.update(model=OPUS))
    assert [s for s, _ in found(preflight(*r.args(), env=r.env), "model")] == ["PASS"]
    r.edit(r.config, lambda c: c["common"].extend(["--model", OPUS]))
    (r.run / "_common.md").write_text(r.common + f"Use {OPUS.capitalize()} for the plan.\n", encoding="utf-8")
    (r.run / "lessons.md").write_text(f"- the {SONNET.upper()} critic missed it\n", encoding="utf-8")
    proc = preflight(*r.args(), env=r.env)
    [(status, detail)] = found(proc, "model")
    assert proc.returncode == 1 and status == "FAIL"
    assert "_control/_agents.json:" in detail and "_common.md:2" in detail and "lessons.md:1" in detail
    assert "settings" not in detail


def test_a_config_or_a_settings_file_outside_control_fails_and_the_config_failure_stops_the_rest(tmp_path):
    r = Run(tmp_path)
    outside = r.run / "_agents.json"
    outside.write_text(r.config.read_text(encoding="utf-8"), encoding="utf-8")
    proc = preflight(*r.args("--config", outside), env=r.env)
    assert proc.returncode == 1 and [(s, c) for s, c, _, _ in results(proc)] == [("FAIL", "config")]
    assert proc.stdout.splitlines()[-1] == f"preflight: 0 passed, 1 failed, 0 skipped — {r.control}/preflight.json"
    assert json.loads((r.control / "preflight.json").read_text(encoding="utf-8"))["passed"] is False
    (r.run / "builder-a-settings.json").write_text(r.builder_settings.read_text(encoding="utf-8"), encoding="utf-8")
    r.edit(r.config, lambda c: c["agents"]["builder-a"].update(settings="builder-a-settings.json"))
    [(status, detail)] = found(preflight(*r.args(), env=r.env), "config")
    assert status == "FAIL" and "builder-a" in detail and "_control" in detail
    assert found(preflight(*r.args("--roles", "planner"), env=r.env), "config")[0][0] == "PASS"
    [(status, detail)] = found(preflight(*r.args("--roles", "planner,critic"), env=r.env), "config")
    assert status == "FAIL" and "critic" in detail


def test_blind_names_every_missing_deny_rule_flag_and_denyread_path(tmp_path):
    r = Run(tmp_path)

    def planner(s):
        deny = s["permissions"]["deny"]
        deny[deny.index(f"Read(/{r.control}/**)")] = f"Read({r.control}/**)"
        s["sandbox"]["allowUnsandboxedCommands"] = True

    def builder(s):
        deny = s["permissions"]["deny"]
        deny.remove("Bash(pgrep:*)")
        deny[deny.index("Read(//proc/**)")] = "Read(/proc/**)"
        s["sandbox"]["filesystem"]["denyRead"].remove(f"{r.checkout}/docs/handoff")

    r.edit(r.planner_settings, planner)
    r.edit(r.builder_settings, builder)
    proc = preflight(*r.args(), env=r.env)
    [(s1, d1)], [(s2, d2)] = found(proc, "blind", "planner"), found(proc, "blind", "builder-a")
    assert (s1, s2) == ("FAIL", "FAIL")
    assert f"Read(/{r.control}/**)" in d1 and "allowUnsandboxedCommands" in d1 and "pgrep" not in d1
    assert "Bash(pgrep:*)" in d2 and "Read(//proc/**)" in d2 and f"{r.checkout}/docs/handoff" in d2
    [(s3, d3)] = found(preflight(*r.args("--unsandboxed", "planner"), env=r.env), "blind", "planner")
    assert s3 == "FAIL" and f"Read(/{r.control}/**)" in d3 and "allowUnsandboxedCommands" not in d3


ANCESTOR = [
    # (allowWrite, deny rules, denyWrite, expected): {R} the tmp root, {wt} the builder's cwd, {home} $HOME
    (["{wt}/.git"], ["Edit(/{wt})"], [], "FAIL"),
    (["{wt}"], ["Write(/{wt}/**)"], [], "FAIL"),
    (["{R}/data-cache"], ["Edit(/{R}/data/**)"], [], "PASS"),
    (["{wt}"], ["Edit(/{wt}/.git/hooks/**)"], [], "PASS"),
    (["~/.cache"], ["Edit(~/.cache/**)"], [], "FAIL"),
    (["{wt}/data/out"], ["Edit(/data/**)"], [], "FAIL"),
    (["{wt}/sub"], [], ["{wt}"], "FAIL"),
]


@pytest.mark.parametrize(
    "allow, deny, deny_write, expected",
    ANCESTOR,
    ids=["parent", "equal", "sibling-prefix", "below", "home", "cwd-anchored", "denyWrite"],
)
def test_a_deny_rule_on_an_allowwrite_path_or_above_it_fails_and_one_below_it_passes(
    tmp_path, allow, deny, deny_write, expected
):
    r = Run(tmp_path)
    fill = {"R": tmp_path, "wt": r.wt, "home": r.home}

    def change(s):
        s["permissions"]["deny"] += [x.format(**fill) for x in deny]
        s["sandbox"]["filesystem"]["allowWrite"] = [x.format(**fill) for x in allow]
        s["sandbox"]["filesystem"]["denyWrite"] = [x.format(**fill) for x in deny_write]

    r.edit(r.builder_settings, change)
    [(status, detail)] = found(
        preflight(*r.args("--roles", "builder-a", "--no-sim"), env=r.env), "ancestor", "builder-a"
    )
    assert status == expected, detail


@pytest.mark.parametrize(
    "mode, expected, words",
    [
        ("good", "PASS", []),
        ("open", "FAIL", ["write into", "_control", "read of"]),
        ("ro", "FAIL", ["write refused in"]),
    ],
)
def test_the_probe_passes_only_when_worktree_writes_land_and_control_stays_shut(tmp_path, mode, expected, words):
    r = Run(tmp_path)
    proc = preflight(*r.args("--roles", "planner"), env={**r.env, "FAKE_SIM_MODE": mode})
    [(status, detail)] = found(proc, "probe", "planner")
    assert status == expected and all(w in detail for w in words), detail
    if mode == "ro":
        assert str(r.plan) in detail and "write into" not in detail
    assert sorted(str(p) for p in tmp_path.rglob(".preflight-*")) == []


def test_an_allowwrite_entry_under_home_is_probed_and_reported_at_its_expanded_path(tmp_path):
    r = Run(tmp_path)
    r.edit(r.builder_settings, lambda s: s["sandbox"]["filesystem"]["allowWrite"].append("~/.cache"))
    cache = str(r.home / ".cache")
    proc = preflight(*r.args("--roles", "builder-a"), env={**r.env, "FAKE_SIM_MODE": "ro"})
    [(status, detail)] = found(proc, "probe", "builder-a")
    assert status == "FAIL" and cache in detail and "~/.cache" not in detail, detail
    proc = preflight(*r.args("--roles", "builder-a"), env={**r.env, "FAKE_SIM_MODE": "good"})
    assert [s for s, _ in found(proc, "probe", "builder-a")] == ["PASS"], proc.stdout
    assert sorted(str(p) for p in tmp_path.rglob(".preflight-*")) == []


def test_without_bwrap_the_probe_fails_unless_it_is_skipped_on_purpose_and_unsandboxed_roles_skip_it(tmp_path):
    r = Run(tmp_path)
    env = {**r.env, "PATH": str(tmp_path / "bin")}
    args = [
        "check",
        r.run,
        "--checkout",
        r.checkout,
        "--formats",
        r.formats,
        "--monitor",
        r.monitor,
        "--now",
        NOW,
        "--roles",
        "planner",
    ]
    proc = preflight(*args, env=env)
    assert found(proc, "probe", "planner") == [("FAIL", "bwrap not on PATH")] and proc.returncode == 1
    proc = preflight(*args, "--no-sim", env=env)
    assert [s for s, _ in found(proc, "probe", "planner")] == ["SKIP"] and proc.returncode == 0
    assert proc.stdout.splitlines()[-1].startswith("preflight: 11 passed, 0 failed, 1 skipped — ")
    r.edit(r.planner_settings, lambda s: s["sandbox"].update(enabled=False))
    proc = preflight(*r.args("--roles", "planner", "--unsandboxed", "planner"), env=r.env)
    assert [s for s, _ in found(proc, "probe", "planner")] == ["SKIP"]
    assert [s for s, _ in found(proc, "ancestor", "planner")] == ["SKIP"]
    assert [s for s, _ in found(proc, "blind", "planner")] == ["PASS"] and not r.sim_log.exists()


def test_worktree_fails_without_the_cwd_its_git_or_the_venv_a_pyproject_needs(tmp_path):
    r = Run(tmp_path)
    shutil.rmtree(r.wt / ".venv")
    (r.plan / ".git").rmdir()
    proc = preflight(*r.args("--no-sim"), env=r.env)
    [(s1, d1)], [(s2, d2)] = found(proc, "worktree", "planner"), found(proc, "worktree", "builder-a")
    assert (s1, s2) == ("FAIL", "FAIL") and ".git" in d1 and ".venv" in d2
    (r.wt / "pyproject.toml").unlink()
    assert found(preflight(*r.args("--no-sim"), env=r.env), "worktree", "builder-a")[0][0] == "PASS"
    shutil.rmtree(r.plan)
    [(s3, d3)] = found(preflight(*r.args("--no-sim"), env=r.env), "worktree", "planner")
    assert s3 == "FAIL" and str(r.plan) in d3


def test_every_waiter_a_brief_names_is_a_file_in_the_run_folder_with_no_placeholder_left(tmp_path):
    r = Run(tmp_path)
    brief = r.run / "_planner-assignment.md"
    brief.write_text("Then `python3 -I _wait_for_ready.py plan-log.md`.\n", encoding="utf-8")
    [(status, detail)] = found(preflight(*r.args("--no-sim"), env=r.env), "waiters")
    assert status == "FAIL" and "_planner-assignment.md" in detail and "_wait_for_ready.py" in detail
    (r.run / "_wait_for_ready.py").write_text("# waiter\n", encoding="utf-8")
    assert found(preflight(*r.args("--no-sim"), env=r.env), "waiters")[0][0] == "PASS"
    (r.run / "_wait_for_task.py").write_text("# waiter\n", encoding="utf-8")
    brief.write_text("Then `python3 -I <run-dir>/_wait_for_task.py plan-log.md 4`.\n", encoding="utf-8")
    [(status, detail)] = found(preflight(*r.args("--no-sim"), env=r.env), "waiters")
    assert status == "FAIL" and "<run-dir>/_wait_for_task.py" in detail


def test_formats_and_monitor_report_the_exit_and_the_last_line_of_their_script(tmp_path):
    r = Run(tmp_path)
    env = {**r.env, "FAKE_FORMATS_EXIT": "1", "FAKE_MONITOR_ARMED": "0"}
    proc = preflight(*r.args("--no-sim"), env=env)
    assert found(proc, "formats") == [("FAIL", "exit 1: plan-log.md:1: line 1 is not a STATUS line")]
    assert found(proc, "monitor") == [("FAIL", "exit 1: not armed: no watch recorded")]
    assert r.formats_log.read_text(encoding="utf-8").split() == [str(r.run)]
    gone = preflight(*r.args("--no-sim"), env={**r.env, "FAKE_MONITOR_ARMED": "gone"})
    assert found(gone, "monitor") == [("FAIL", f"exit 2: {r.run}: no such run folder")]
    [(status, detail)] = found(
        preflight(*r.args("--no-sim", "--monitor", tmp_path / "absent.py"), env=r.env), "monitor"
    )
    assert status == "FAIL" and "absent.py" in detail
    assert [s for s, _ in found(preflight(*r.args("--no-sim", "--no-monitor"), env=env), "monitor")] == ["SKIP"]


def test_disk_fails_below_the_minimum_free_space(tmp_path):
    r = Run(tmp_path)
    assert found(preflight(*r.args("--no-sim", "--min-free-mb", "1"), env=r.env), "disk")[0][0] == "PASS"
    assert found(preflight(*r.args("--no-sim", "--min-free-mb", "1000000000"), env=r.env), "disk")[0][0] == "FAIL"


FIVE = "five-hour"
USAGE = [
    # (readings, extra args, expected, a word of the detail); now = 2026-10-29T20:00Z
    ([("2026-10-29T19:29Z", [(FIVE, 10, "2026-10-29T23:00Z")])], [], "FAIL", "31 min"),
    (
        [
            ("2026-10-29T19:00Z", [(FIVE, 40, "2026-10-29T21:30Z")]),
            ("2026-10-29T20:00Z", [(FIVE, 60, "2026-10-29T21:30Z")]),
        ],
        [],
        "PASS",
        "",
    ),
    (
        [
            ("2026-10-29T19:00Z", [(FIVE, 40, "2026-10-29T22:30Z")]),
            ("2026-10-29T20:00Z", [(FIVE, 60, "2026-10-29T22:30Z")]),
        ],
        [],
        "FAIL",
        "2026-10-29T22:00Z",
    ),
    (
        [
            ("2026-10-29T19:00Z", [(FIVE, 40, "2026-10-29T21:30Z")]),
            ("2026-10-29T20:00Z", [(FIVE, 60, "2026-10-29T21:30Z")]),
        ],
        ["--scale", "2"],
        "FAIL",
        "2026-10-29T21:00Z",
    ),
    ([("2026-10-29T20:00Z", [(FIVE, 80, "2026-10-29T23:00Z")])], [], "FAIL", "80"),
    ([("2026-10-29T20:00Z", [(FIVE, 79, "2026-10-29T23:00Z")])], [], "PASS", ""),
    (
        [
            ("2026-10-29T19:00Z", [("weekly", 40, "2026-11-04T13:00Z")]),
            ("2026-10-29T20:00Z", [("weekly", 41, "2026-11-04T13:00Z")]),
        ],
        [],
        "PASS",
        "",
    ),
    (
        [
            ("2026-10-29T19:00Z", [("weekly", 40, "2026-11-04T13:00Z")]),
            ("2026-10-29T20:00Z", [("weekly", 41, "2026-11-04T13:00Z")]),
        ],
        ["--hours", "72"],
        "FAIL",
        "2026-11-01T07:00Z",
    ),
    (
        [
            ("2026-10-29T19:00Z", [(FIVE, 10, "2026-10-29T19:30Z")]),
            ("2026-10-29T20:00Z", [(FIVE, 70, "2026-10-30T00:30Z")]),
        ],
        [],
        "PASS",
        "",
    ),
]


@pytest.mark.parametrize(
    "readings, extra, expected, word",
    USAGE,
    ids=[
        "stale",
        "rate-ends-after-reset",
        "rate-ends-before-reset",
        "scaled",
        "at-max",
        "below-max",
        "weekly-within-hours",
        "weekly-over-72h",
        "reset-between-readings",
    ],
)
def test_usage_fails_on_a_stale_reading_a_limit_at_the_maximum_or_a_rate_that_ends_before_the_reset(
    tmp_path, readings, extra, expected, word
):
    r = Run(tmp_path)
    r.usage(readings)
    [(status, detail)] = found(preflight(*r.args("--roles", "planner", "--no-sim", *extra), env=r.env), "usage")
    assert status == expected and word in detail, detail


def test_usage_fails_when_the_file_is_missing(tmp_path):
    r = Run(tmp_path)
    (r.control / "usage.json").unlink()
    [(status, detail)] = found(preflight(*r.args("--roles", "planner", "--no-sim"), env=r.env), "usage")
    assert status == "FAIL" and "usage.json" in detail


def launch_with(r, change):
    (r.run / "_launch.md").write_text(change(LAUNCH), encoding="utf-8")
    return found(preflight(*r.args("--roles", "planner", "--no-sim"), env=r.env), "launch")


def test_the_launch_table_needs_the_key_lines_the_six_cells_by_name_and_one_row_per_role_with_its_settings(tmp_path):
    r = Run(tmp_path)
    header = "| role | lane | work | settings | skills | ECC texts | cost estimate |"
    swapped = "| cost estimate | role | `settings` | lane | ECC texts | skills | work | notes |"  # cells by name, backticks stripped
    rows = LAUNCH.split(header + "\n|---|---|---|---|---|---|---|\n")[1]

    def reorder(text):
        cells = [[c.strip() for c in line.strip("|").split("|")] for line in rows.strip().splitlines()]
        moved = [f"| {c[6]} | {c[0]} | {c[3]} | {c[1]} | {c[5]} | {c[4]} | {c[2]} | - |" for c in cells]
        return text.split(header)[0] + swapped + "\n|---|---|---|---|---|---|---|---|\n" + "\n".join(moved) + "\n"

    assert [s for s, _ in launch_with(r, lambda t: t)] == ["PASS"]
    assert [s for s, _ in launch_with(r, reorder)] == ["PASS"]
    cases = [
        (lambda t: re.sub(r"(?m)^Size:.*\n", "", t), "Size:"),
        (
            lambda t: t.replace(
                "Size: one context cannot hold it: 11 tasks at 120k-180k tokens each, measured on the last run",
                "Size: one context cannot hold it",
            ),
            "Size:",
        ),
        (lambda t: t.replace("$40-$60", "forty to sixty dollars"), "Estimate:"),
        (lambda t: t.replace("one fresh session per unit, ", ""), "Estimate:"),
        (lambda t: t.replace(" cost estimate |", " cost |"), "cost estimate"),
        (lambda t: re.sub(r"(?m)^\| builder-a .*\n", "", t), "builder-a"),
        (lambda t: t + "| critic | - | reviews | `_control/critic-settings.json` | - | - | $5 |\n", "critic"),
        (lambda t: t.replace("`_control/planner-settings.json`", "`planner-settings.json`"), "planner"),
    ]
    for change, word in cases:
        [(status, detail)] = launch_with(r, change)
        assert status == "FAIL" and word in detail, (word, detail)
    (r.control / "_agents-judge.json").unlink()
    [(status, detail)] = launch_with(r, lambda t: t)
    assert status == "FAIL" and "judge" in detail


def test_with_yes_every_checked_role_is_named_in_a_yes_line_stamped_no_later_than_now(tmp_path):
    r = Run(tmp_path)
    launch = r.run / "_launch.md"
    judge = ["--config", r.control / "_agents-judge.json", "--roles", "judge", "--no-sim", "--yes"]

    def yes(*args):
        return found(preflight(*r.args(*args), env=r.env), "launch")

    [(status, detail)] = yes("--no-sim", "--yes")
    assert status == "FAIL" and "planner" in detail and "builder-a" in detail
    launch.write_text(LAUNCH + "\nYes: 2026-10-29T19:58Z — planner-b, builder-a — another run\n", encoding="utf-8")
    [(status, detail)] = yes("--no-sim", "--yes")
    assert status == "FAIL" and "planner" in detail and "builder-a" not in detail
    launch.write_text(
        LAUNCH + "\nYes: 2026-10-29T19:58Z — planner, builder-a — the demo run as in the table\n", encoding="utf-8"
    )
    assert [s for s, _ in yes("--no-sim", "--yes")] == ["PASS"]
    assert [s for s, _ in yes("--no-sim")] == ["PASS"]
    [(status, detail)] = yes(*judge)
    assert status == "FAIL" and "judge" in detail
    launch.write_text(
        launch.read_text(encoding="utf-8") + "Yes: 2026-10-29T20:30Z — judge — the final review\n", encoding="utf-8"
    )
    [(status, detail)] = yes(*judge)
    assert status == "FAIL" and "2026-10-29T20:30Z" in detail and "judge" in detail
    launch.write_text(launch.read_text(encoding="utf-8").replace("T20:30Z", "T19:59Z"), encoding="utf-8")
    assert [s for s, _ in yes(*judge)] == ["PASS"]


def case(root, suite, name, text):
    (root / suite / name).mkdir(parents=True)
    (root / suite / name / "task.yaml").write_text(f"name: {name}\n{text}", encoding="utf-8")


def test_timeout_sums_trials_times_sessions_times_minutes_over_every_session_case(tmp_path):
    case(tmp_path, "s1", "a", "trials: 3\ntimeout_minutes: 15\n")
    case(tmp_path, "s1", "b", "trials: 1\nsessions: 2            # two runs of one stage\ntimeout_minutes: 10\n")
    case(tmp_path, "s1", "c", "session: false   # graded by code\ntimeout_minutes: 99\n")
    case(tmp_path, "s2", "d", "timeout_minutes: 20\n")
    proc = preflight("timeout", tmp_path / "s1", tmp_path / "s2", env={})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines() == [
        "s1/a: 3 x 1 x 15 min = 45 min",
        "s1/b: 1 x 2 x 10 min = 20 min",
        "s2/d: 1 x 1 x 20 min = 20 min",
        "total: 85 min over 3 session cases (1 code-only skipped)",
    ]
    assert (
        preflight("timeout", tmp_path / "s2" / "d", env={}).stdout.splitlines()[-1]
        == "total: 20 min over 1 session cases (0 code-only skipped)"
    )
    low = preflight("timeout", tmp_path / "s1", tmp_path / "s2", "--check", "84", env={})
    assert low.returncode == 1 and low.stdout.splitlines()[-1].startswith("FAIL timeout:")
    enough = preflight("timeout", tmp_path / "s1", tmp_path / "s2", "--check", "85", env={})
    assert enough.returncode == 0 and enough.stdout.splitlines()[-1].startswith("PASS timeout:")
    case(tmp_path, "s3", "e", "trials: 2\n")
    proc = preflight("timeout", tmp_path / "s3", env={})
    assert proc.returncode == 1 and "FAIL s3/e: a session case without timeout_minutes" in proc.stdout


def tool(timestamp, name, **inputs):
    content = [{"type": "tool_use", "id": "t", "name": name, "input": inputs}]
    return json.dumps(
        {"type": "assistant", "timestamp": timestamp, "message": {"role": "assistant", "content": content}}
    )


def test_polls_finds_a_sleep_inside_a_loop_body_and_nothing_else(tmp_path):
    commands = [
        "while ! grep -q done plan-log.md; do sleep 30; done",  # a `done` before the `do` is no loop end
        "for f in a b; do echo $f; done; sleep 1",
        "until test -s out.txt; do sleep 5; done",
        'python3 -c "import time\nwhile True:\n    time.sleep(5)"',
        "sleep 0.1 && echo ok",
        "while true; do for f in a; do echo $f; done; sleep 5; done",
        "for f in a b; do echo $f; done; sleep 1; while true; do date; done",
    ]
    lines = [json.dumps({"type": "user", "timestamp": "2026-10-29T19:00:00.000Z", "message": {"content": "go"}})]
    lines += [tool(f"2026-10-29T19:0{i}:00.000Z", "Bash", command=c) for i, c in enumerate(commands)]
    lines.append(tool("2026-10-29T19:09:00.000Z", "Write", file_path="x.sh", content="while true; do sleep 1; done"))
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("\n".join(lines) + "\n", encoding="utf-8")
    proc = preflight("polls", transcript, env={})
    assert proc.returncode == 1
    hits = [
        int(m.group(1)) for m in re.finditer(rf"(?m)^sleep loop: {re.escape(str(transcript))}:(\d+): ", proc.stdout)
    ]
    assert hits == [2, 4, 5, 7]
    assert proc.stdout.splitlines()[-1] == "polls: 7 Bash commands, 4 sleep loops"
    clean = tmp_path / "clean.jsonl"
    clean.write_text(lines[2] + "\n" + lines[5] + "\n", encoding="utf-8")
    proc = preflight("polls", clean, env={})
    assert proc.returncode == 0 and proc.stdout.splitlines() == ["polls: 2 Bash commands, 0 sleep loops"]


def test_clock_fails_a_time_not_in_date_u_form_and_a_stamp_far_from_its_writer(tmp_path):
    record = tmp_path / "rec.md"
    lines = [
        "- 20:12 UTC (main session): merged main into the plan",
        "- 18:00 UTC (plan fixer): fixed C1",
        "HANDOFF planner after Task 0 — 2026-10-29 20:14",
        "- 23:58 UTC: the last line of the day",
        "- 20:1x UTC: an estimated time",
        "- 07:00 UTC: a line no tool wrote",
        "see lessons.md:147 and test_docs.py:156-160",
    ]
    record.write_text("\n".join(lines) + "\n", encoding="utf-8")
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(
        "\n".join(
            [
                tool(
                    "2026-10-29T20:13:05.000Z",
                    "Edit",
                    file_path=str(record),
                    old_string="x",
                    new_string=lines[0] + "\n",
                ),
                tool("2026-10-29T20:13:30.000Z", "Bash", command=f"printf '%s\\n' '{lines[1]}' >> rec.md"),
                tool("2026-10-29T20:14:40.000Z", "Write", file_path="handoff.md", content=lines[2] + "\nState: none\n"),
                tool("2026-10-29T21:00:00.000Z", "Bash", command=f"grep -nF -- '{lines[0]}' rec.md"),
                tool("2026-10-30T00:03:00.000Z", "Edit", file_path=str(record), old_string="y", new_string=lines[3]),
                tool("2026-10-30T00:04:00.000Z", "Edit", file_path=str(record), old_string="z", new_string=lines[4]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    proc = preflight("clock", record, "--transcript", transcript, env={})
    assert proc.returncode == 1
    assert proc.stdout.splitlines() == [
        f"{record}:2: 18:00 UTC was written at 2026-10-29T20:13:30Z, 133 min apart",
        f"{record}:5: not in date -u form: 20:1x",
        "clock: 5 stamped lines, 4 matched a writer, 2 problems",
    ]
    # line 2's gap is 133.5 min: 133 whole minutes, not more than --slack 133, more than --slack 132
    proc = preflight("clock", record, "--transcript", transcript, "--slack", "133", env={})
    assert proc.stdout.splitlines()[-1] == "clock: 5 stamped lines, 4 matched a writer, 1 problems"
    proc = preflight("clock", record, "--transcript", transcript, "--slack", "132", env={})
    assert proc.stdout.splitlines()[-1] == "clock: 5 stamped lines, 4 matched a writer, 2 problems"


def section(text, heading):
    return re.search(rf"(?ms)^{re.escape(heading)}$(.*?)(?=^#{{1,2}} |\Z)", text).group(1)


def test_the_manager_readme_documents_the_usage_line_and_every_option_of_every_subcommand():
    text = section((SCRIPTS / "manager" / "README.md").read_text(encoding="utf-8"), "## preflight.py")
    assert re.search(
        r"(?m)^Usage: python3 -I scripts/manager/preflight\.py check <run-dir> --checkout <checkout>", text
    )
    for sub in ("check", "timeout", "polls", "clock"):
        out = subprocess.run(
            [sys.executable, "-I", str(PREFLIGHT), sub, "--help"], capture_output=True, text=True, check=True
        ).stdout
        options = set(re.findall(r"--[a-z][a-z-]+", out)) - {"--help"}
        assert sorted(o for o in options if o not in text) == [], sub
    assert "--scale" in text and "--yes" in text


def test_the_docs_carry_the_launch_table_the_clock_rule_the_request_lines_and_the_reference_page():
    launch = (SKILL / "example" / "launch.md").read_text(encoding="utf-8")
    for key in ("Purpose:", "Size:", "Model rule:", "Estimate:", "Budget:", "Usage:", "Yes:"):
        assert re.search(rf"(?m)^{re.escape(key)} ", launch), key
    assert "Launched:" in launch and not re.search(r"(?m)^Launched:", launch)  # C17: the prose only
    header = next(line for line in launch.splitlines() if line.startswith("| role |"))
    assert {"role", "lane", "settings", "skills", "ECC texts", "cost estimate"} <= {
        c.strip() for c in header.strip("|").split("|")
    }
    common = (SKILL / "example" / "common.md").read_text(encoding="utf-8")
    assert re.search(r"(?m)^Request-line bound: (\d+) minutes?\b", common).group(1) == "15"
    for s in (
        "`SANDBOX: <what was refused> — <why the step needs it>`",
        "COPY-REQUEST: <stage> -> <worktree>",
        "`CHECKOUT-REQUEST: <sha>`",
        "`FF-REQUEST: <branch> <sha> -> <branch> <sha>`",
        "`SUPPLIED:`",
        "`COPIED:`",
        "`CHECKED-OUT:`",
        "`FF-DONE:`",
        "`REFUSED: <KIND> — <why>`",
        "Order <msg_id>",
        "`ACK <msg_id>`",
        "`date -u +%Y-%m-%dT%H:%MZ`",
        "timeout -k 10",
    ):
        assert s in common, s
    page = (SKILL / "references" / "preflight-and-capacity.md").read_text(encoding="utf-8")
    assert page.splitlines()[0] == "# Pre-flight and capacity"
    assert re.findall(r"(?m)^### (.*)$", page) == [
        "Pre-flight",
        "The launch table and the yes",
        "Capacity",
        "Timeouts",
        "The clock and polling",
        "Size",
    ]
    for s in (
        "scripts/manager/preflight.py check",
        "_control/usage.json",
        "--scale",
        "--hours",
        "--yes",
        "timeout -k 10",
        "one context cannot hold",
        "one session plus a verifier",
        "monitor_records.py status",
    ):
        assert s in page, s
    ref = (SKILL / "references" / "launch.md").read_text(encoding="utf-8")
    assert "--model" not in ref and "<run-dir>/_control/<role>-settings.json" in ref
    assert "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE" in ref and "design-plugins.json" in ref
````

- [ ] **Step 2 — red.** Run:
  ```bash
  SK=.claude/skills/running-specagent-pipelines
  uv run pytest -q -p no:cacheprovider "${SK:?}/scripts/tests/test_preflight.py" 2>&1 | tail -1
  uv run pytest -q -p no:cacheprovider "${SK:?}/scripts/tests" 2>&1 | tail -1
  ```
  Expected: `37 failed` (no `preflight.py`; the two documentation tests also want the files of Steps 4-7), then
  `37 failed, 202 passed`.

- [ ] **Step 3 — the script, green.** Write `<skill>/scripts/manager/preflight.py` against the Interfaces: standard
  library only, no shebang line (it runs as `python3 -I <path>`: `.claude/skills/` takes no `chmod`, and EXE001 fails a
  shebang in a file that is not executable; lessons.md, 22:23 UTC). Ruff 0.16.10 (`uv.lock:956-957`) enables 826 rules
  with this repo's settings (`pyproject.toml:17-22`; `ruff check --show-settings`), among them PLW1510 (`check=` on
  every `subprocess.run`), UP017 (`datetime.UTC`) and FURB167 (`re.MULTILINE`, not `re.M`). Every function stays under
  50 lines (`.claude/rules/python.md:9`): `check` runs two checks, four per role and six for the run, so each group gets
  a helper of its own (the planner's scratch version had a `check` of 64 lines). Run the two commands of Step 2 again.
  Expected: `2 failed, 35 passed`, the two being
  `test_the_manager_readme_documents_the_usage_line_and_every_option_of_every_subcommand` and
  `test_the_docs_carry_the_launch_table_the_clock_rule_the_request_lines_and_the_reference_page`, then `2 failed, 237
  passed`. The wrong versions the planner ran once against these tests (26, each failed at least one test): the timeout
  without its trials; without its sessions; a code-only case counted; only the first DIR read; the clock check without
  the wrap at midnight; the clock's writer taken as the latest transcript entry holding the line instead of the
  earliest; `>=` for `>` at `--slack`; a loop body ending at the first `done`; ending at the last `done`; the ancestor
  test by `startswith` without the `/`; the ancestor test reversed; the usage rate taken across a reset; no `--scale`;
  no `--hours` horizon; `>` for `>=` at `--max-pct`; the model matched case-sensitively; a `model` key in a settings
  file counted; the probe checking only the allowWrite marks; only the `_control/` mark; a waiter token with a
  placeholder accepted; a `Yes:` line stamped after now naming a role; a role matched without its lookarounds; the
  `settings` cell compared unstripped; the last line taken from stdout and stderr joined; from stdout only; from stderr
  first. Then `<skill>/example/sim_bwrap.py` expands a leading `~/` as Claude Code does (C502; it passed the settings'
  `~/` entries to bwrap as written). Apply exactly this diff, then `git diff --stat -- "${SK:?}/example/sim_bwrap.py" |
  tail -1`. Expected: ` 1 file changed, 8 insertions(+), 5 deletions(-)`.
  ```diff
  @@ -3 +3,2 @@
  -/tmp/claude-1000), tmpfs over denyRead, read-only binds over every Edit(...) deny and denyWrite path.
  +/tmp/claude-1000), tmpfs over denyRead, read-only binds over every Edit(...) deny and denyWrite path; a leading `~/` is the
  +home directory in each of them, as Claude Code expands it.
  @@ -23 +24,2 @@
  -norm = lambda r: "/" + re.sub(r"/\*\*$", "", r[5:-1]).lstrip("/")
  +home = os.path.expanduser
  +norm = lambda r: "/" + re.sub(r"/\*\*$", "", home(r[5:-1])).lstrip("/")
  @@ -25 +27 @@
  -for d in [a["cwd"], *a["add_dirs"], *fs.get("allowWrite", []), "/tmp/claude-1000"]:
  +for d in [a["cwd"], *a["add_dirs"], *map(home, fs.get("allowWrite", [])), "/tmp/claude-1000"]:
  @@ -27 +29 @@
  -for d in fs.get("denyRead", []):
  +for d in map(home, fs.get("denyRead", [])):
  @@ -30 +32,2 @@
  -for d in [norm(r) for r in s["permissions"]["deny"] if r.startswith("Edit(")] + fs.get("denyWrite", []):
  +edit_deny = [norm(r) for r in s["permissions"]["deny"] if r.startswith("Edit(")]
  +for d in edit_deny + [home(d) for d in fs.get("denyWrite", [])]:
  ```

- [ ] **Step 4 — the launch table.** Write `<skill>/example/launch.md`:
````markdown
# Launch: the <run-name> run

The manager fills this file before every launch and sends its table to the owner in one message; each yes of the owner
is appended as a `Yes:` line. When the pre-flight has passed and the first role starts, the manager appends `Launched: `
and the UTC time as `date -u +%Y-%m-%dT%H:%M:%SZ` prints it, once (no relaunch, resume or hand-over changes it); the
owner's surface takes the run's start from it. The pre-flight (`scripts/manager/preflight.py check --yes` of the skill)
holds the launch until every line below is filled and every role it starts is named in a `Yes:` line. No model is named
here: the roles read the run folder's `_*.md`, so the models go in the manager's chat message only.

Purpose: <what the run builds, in one sentence, and the spec or plan it builds from>
Size: <n> tasks; <why one context cannot hold the work> (otherwise one session plus a verifier, and no table)
Model rule: <the rule the manager applies per role, stated without naming a model>
Estimate: <n> roles, <n>-<m> sessions, $<low>-$<high> per unit, $<total> for the run
Budget: $<amount> for the run; at $<amount> the manager launches nothing new and asks the owner
Usage: <the newest reading of _control/usage.json: each limit, its percentage, its reset time>

| role | lane | settings | skills | ECC texts | cost estimate |
|---|---|---|---|---|---|
| planner | plan | `_control/planner-settings.json` | <the skills its brief loads> | <the ECC texts of its brief> | $<n> |
| plan-fixer | plan | `_control/plan-fixer-settings.json` | <skills> | <ECC texts> | $<n> |
| critic | review | `_control/critic-settings.json` | <skills> | <ECC texts> | $<n> |
| builder-a | a | `_control/builder-a-settings.json` | <skills> | <ECC texts> | $<n> |
| builder-b | b | `_control/builder-b-settings.json` | <skills> | <ECC texts> | $<n> |
| verifier | checks | `_control/verifier-settings.json` | <skills> | <ECC texts> | $<n> |
| judge | end | `_control/judge-settings.json` | <skills> | <ECC texts> | $<n> |

Yes: <YYYY-MM-DDTHH:MMZ> — <roles> — <what the owner approved>
````

  In `<skill>/example/README.md`, replace:
````text
1. Make the run folder outside the repository and copy each file into it with a leading `_` (`common.md` becomes
   `_common.md`, `agents.json` becomes `_agents.json`), except `lessons.md`, which keeps its name because the agents
   add to it. This README stays here.
````
  with:
````text
1. Make the run folder outside the repository and copy each file into it with a leading `_` (`common.md` becomes
   `_common.md`, `launch.md` becomes `_launch.md`), except `lessons.md`, which keeps its name because the agents
   add to it, and the configs and settings files, which go to `<run-dir>/_control/` (`agents.json` becomes
   `_control/_agents.json`, `agents-judge.json` becomes `_control/_agents-judge.json`, `planner-settings.json`
   becomes `_control/planner-settings.json`), each agent's `settings` naming its file as
   `_control/<role>-settings.json`: the roles' `Read(/<run-dir>/_control/**)` deny keeps them out of reach, and the
   pre-flight reads them there. This README stays here.
````
  In `<skill>/example/README.md`, replace:
````text
4. After one round of `--check`, start the watcher in the background from the main session:
   `python3 -I <skill-dir>/scripts/watch_agents.py <run-dir>/_agents.json`. The judge comes once, at the end, with
   the owner's approval: `bash <skill-dir>/scripts/judge_after_verify.sh <run-dir>/_agents-judge.json <checkout>
   <record-file>...`.
````
  with:
````text
4. Fill `_launch.md`: the key lines and one table row per role. Start the request-line monitor in the background
   (`python3 -I <skill-dir>/scripts/monitor_records.py watch <run-dir>`), append the usage reading to
   `_control/usage.json` and run the pre-flight:
   `python3 -I <skill-dir>/scripts/manager/preflight.py check <run-dir> --checkout <checkout>`. Send the owner the
   table in one message, with the models; append the answer as a `Yes:` line and run the pre-flight again with
   `--yes` (`references/preflight-and-capacity.md`).
5. After one round of `--check`, start the watcher in the background from the main session:
   `python3 -I <skill-dir>/scripts/watch_agents.py <run-dir>/_control/_agents.json`. The judge comes once, at the
   end, with the owner's approval: `bash <skill-dir>/scripts/judge_after_verify.sh
   <run-dir>/_control/_agents-judge.json <checkout> <record-file>...`.
````
  In `<skill>/example/README.md`, append as the last entry of the file list, after its last line and before the blank
  line above `## Placeholders` (Global Constraint 14, C19: never between other tasks' entries):
````text
- `launch.md`: the launch table the manager fills before every launch, with the owner's `Yes:` lines
  (`_launch.md` in the run folder; `references/preflight-and-capacity.md`).
````
  In `<skill>/scripts/tests/test_skill_example.py`, append as the last entry of `FILES`, after its last entry (at
  ff3354a `*(f"{r}-settings.json" for r in ROLES),`) and before the closing `}`:
````text
    "launch.md",
````

- [ ] **Step 5 — `example/common.md`: the ACK rule, the clock rule, the two requests, the answers and the bound.**
  In `<skill>/example/common.md`, replace:
````text
only wakes it sooner. Load the messaging tools with ToolSearch `select:SendMessage,ListAgents`.
````
  with:
````text
only wakes it sooner. Load the messaging tools with ToolSearch `select:SendMessage,ListAgents`.
An order from the main session ends with the line "Order <msg_id>: append the line `ACK <msg_id>` to <record>
before anything else." (`<msg_id>` is 8 lowercase hex). Append `ACK <msg_id>` at line start in your own record
file first, then act on the order; the watcher resends an order whose `ACK` line it does not find.
````
  In `<skill>/example/common.md`, replace:
````text
<command>)` and any `timeout` is `timeout -k 10 <s>`. Test files run 4 at a time when a step runs several; never one
long chain.
````
  with:
````text
<command>)` and any `timeout` is `timeout -k 10 <s>`. Test files run 4 at a time when a step runs several; never one
long chain. A time you write in a record file comes from `date -u +%Y-%m-%dT%H:%MZ` run in the same step, never
from memory or an estimate; you wait with a waiter, never with a `sleep` loop.
````
  In `<skill>/example/common.md`, replace:
````text
for with one line `COPY-REQUEST: <stage> -> <worktree>` in your record file, which the main session fulfils byte for byte.
````
  with:
````text
for with one line `COPY-REQUEST: <stage> -> <worktree>` in your record file, which the main session fulfils byte for byte.
Two more requests go the same way, one line each in your record file: `CHECKOUT-REQUEST: <sha>` when your worktree
must move to a commit you cannot check out yourself, and `FF-REQUEST: <branch> <sha> -> <branch> <sha>` when a
branch must be fast-forwarded. The main session answers below the request in your record file with `SUPPLIED:` (a
`SANDBOX:` line), `COPIED:` (`COPY-REQUEST:`), `CHECKED-OUT:` (`CHECKOUT-REQUEST:`), `FF-DONE:` (`FF-REQUEST:`) or
`REFUSED: <KIND> — <why>` (`<KIND>` is the request's prefix); each answer closes the oldest open request of its kind.
Request-line bound: 15 minutes. The main session answers a request line within that time; the monitor reports one
that waits longer, and you go on with what you can and never repeat the line.
````

- [ ] **Step 6 — the reference page, `MOVED`, `SKILL.md` and `references/launch.md`.** Write
  `<skill>/references/preflight-and-capacity.md`:
````markdown
# Pre-flight and capacity

What the manager checks and asks before a launch, and the rules that keep a run inside its time and its limits. The
script is `scripts/manager/preflight.py` (standard library only); its options are in `scripts/manager/README.md`.

### Pre-flight
Before every launch, the first one and each one after a settings change, run
`python3 -I scripts/manager/preflight.py check <run-dir> --checkout <checkout>`. It prints one `PASS`, `FAIL` or `SKIP`
line per check, writes `<run-dir>/_control/preflight.json` and exits 0 only when nothing failed; the launch waits for
that. The checks, in their order:
- `config`: the watcher config and every settings file lie inside `<run-dir>/_control/` and parse.
- `model`: no config, brief or `lessons.md` of the run names a model or `--model` (the model is the manager's setting).
- `blind`: each role's settings deny the nine rules that keep it blind to transcripts, the control files, the hand-overs
  and the processes; a sandboxed role also fails closed and hides the same three paths from reading.
- `ancestor`: no `Edit(...)`, `Write(...)` or `denyWrite` path is an allowWrite path or one above it (a deny on an
  ancestor refuses every write below it); a deny below an allowWrite path, such as `.git/hooks`, is fine.
- `probe`: `example/sim_bwrap.py` builds the role's sandbox from its settings and runs a probe in it: a write lands in
  every allowWrite directory, a write into `_control/` and a read of the config are refused. It needs `bwrap` on PATH;
  `--no-sim` skips it on purpose, `--unsandboxed <role>` skips it for a role that runs without the sandbox.
- `worktree`: each role's directory exists, is a git checkout and, with a `pyproject.toml`, has its `.venv` (`uv sync`
  once per worktree).
- `waiters`: every waiter a brief names is a file in the run folder, with no placeholder left.
- `formats`: `scripts/check_formats.py <run-dir>` exits 0.
- `monitor`: `monitor_records.py status <run-dir>` reports the request-line watch armed (its `watch` command starts it).
- `disk`: at least `--min-free-mb` (512) MiB free in the run folder, the temporary directory and each worktree.
- `usage` and `launch`: below.

### The launch table and the yes
The manager fills `<run-dir>/_launch.md` from `example/launch.md`: the lines `Purpose:`, `Size:`, `Model rule:`,
`Estimate:` (roles, sessions, dollars per unit), `Budget:` and `Usage:`, and one table row per agent of every
`_control/_agents*.json` with its lane, settings file, skills, ECC texts and cost estimate. The table counts every
session the run will start, fresh sessions per milestone and the final judge included. It goes to the owner in one
message, which alone names the models (they never go in a file the roles read). Each yes is appended as
`Yes: <YYYY-MM-DDTHH:MMZ> — <roles> — <what the owner approved>` and covers only the roles and the work it names; with
`--yes` the pre-flight requires a `Yes:` line for every role it checks, stamped no later than now. The manager asks the
owner only before a launch, a destructive action, a merge into `main` or spending; a routine question it decides itself
and states the assumption in its record. Every status it gives carries a number and the record path it comes from.

### Capacity
The roles cannot read the usage limits. Before each launch the manager reads them with the desktop app's `get_usage`
and appends one reading to `<run-dir>/_control/usage.json`: `taken_at`, `source`, `extra_usage` and, per limit, `name`,
`used_pct` and `resets_at`, the times as `date -u +%Y-%m-%dT%H:%MZ` prints them; an old reading is never edited. The
`usage` check fails when the newest reading is older than `--usage-age` (30) minutes, when a limit stands at
`--max-pct` (80) or above, or when the rate since the previous reading of the same window, times `--scale`, reaches
100% before the window resets or the run ends (`--hours`, 5), whichever comes first. `--scale` is the run's rate
against the measured one: 2 when the launch doubles the sessions. A launch that fails here waits for the reset or
starts fewer roles.

### Timeouts
A suite's timeout comes from its cases, never from a guess: `python3 -I scripts/manager/preflight.py timeout
evals/regression evals/capability --check <minutes>` sums trials x sessions x `timeout_minutes` over the session cases
and fails when the minutes set for the suite are fewer. Every long command in a brief runs under
`timeout -k 10 <seconds>`, its seconds taken from the same numbers.

### The clock and polling
A role never writes a time from memory: every stamp in a record file comes from `date -u +%Y-%m-%dT%H:%MZ` run in the
same step. `preflight.py clock <record>... --transcript <jsonl>` finds times not in that form and stamps more than
`--slack` (10) minutes from the moment a tool wrote them. Waiting is done by the waiters and the monitor, never by a
`sleep` loop; `preflight.py polls <jsonl>...` finds a `sleep` in a shell loop body or a Python `while` loop with
`time.sleep(`.

### Size
A pipeline only when one context cannot hold the work; otherwise one session plus a verifier. The `Size:` line of the
launch table says which, with the number of tasks and the reason.
````

  In `<skill>/scripts/tests/test_skill_md.py` (Task 1 moved `MOVED` there from `test_docs.py`), replace:
````text
    "sandbox-and-blindness.md": "Blind to models and authors, inside the sandbox",
````
  with:
````text
    "sandbox-and-blindness.md": "Blind to models and authors, inside the sandbox",
    "preflight-and-capacity.md": "Pre-flight and capacity",
````
  In `<skill>/SKILL.md`, replace:
````text
| Ask before launching any agent | One message before the run: how many sessions, for what, including fresh sessions per milestone and the final judge. Approval covers only that task. |
````
  with:
````text
| Ask before launching any agent | The `_launch.md` table, one yes per launch, the pre-flight first (see Pre-flight and capacity). |
````
  In `<skill>/SKILL.md`, replace:
````text
| No early compaction in SpecAgent sessions | `"env": {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": ""}` in `--settings` (clears the main session's 60%, which the daemon passes on). Never `--autocompact` with a small window. |
````
  with:
````text
| No early compaction in SpecAgent sessions | The empty compaction override in every `--settings` (see Launch). |
````
  In `<skill>/SKILL.md`, replace:
````text
| Only the plugins and MCP a role needs | `--strict-mcp-config`; design plugins only for design roles (`~/.claude/design-plugins.json` merged into `--settings`). |
````
  with:
````text
| Only the plugins and MCP a role needs | `--strict-mcp-config`; design plugins only for design roles (see Launch). |
````
  In `<skill>/SKILL.md`, replace:
````text
  worktrees of the roles that edit and verify.
````
  with:
````text
  worktrees of the roles that edit and verify.
- [Pre-flight and capacity](references/preflight-and-capacity.md): the checks before a launch, the launch table
  and the yes, capacity around the five-hour window, timeouts from the cases, the clock, the size rule.
````
  In `<skill>/references/launch.md`, replace:
````text
  `--settings`, 2026-10-09); add the env override above.
````
  with:
````text
  `--settings`, 2026-10-09); add the compaction override of the next item.
- No early compaction in SpecAgent sessions: `"env": {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": ""}` in `--settings` clears the
  main session's 60%, which the daemon passes on; never `--autocompact` with a small window.
- Only the plugins and MCP a role needs: `--strict-mcp-config` on every launch and resume; design plugins only for
  design roles (`~/.claude/design-plugins.json` merged into `--settings`).
````
  Then `wc -c < "${SK:?}/SKILL.md"`. Expected: `11764` (Task 1's 11750 and these four edits' 14 bytes; at most
  12000, `test_skill_md.py`).

- [ ] **Step 7 — the README section.** Append to `<skill>/scripts/manager/README.md`, after one blank line:
````markdown
## preflight.py
Usage: python3 -I scripts/manager/preflight.py check <run-dir> --checkout <checkout> [--config P] [--launch P] [--roles A,B] [--unsandboxed ROLE]... [--sim P | --no-sim] [--formats P] [--monitor P | --no-monitor] [--min-free-mb N] [--usage-age MIN] [--max-pct PCT] [--scale X] [--hours H] [--yes] [--now ISO]
Usage: python3 -I scripts/manager/preflight.py timeout <dir>... [--check MIN]
Usage: python3 -I scripts/manager/preflight.py polls <transcript>...
Usage: python3 -I scripts/manager/preflight.py clock <record>... [--transcript JSONL]... [--slack MIN]

The manager's checks before a launch and two audits of a run's practice (`references/preflight-and-capacity.md`).
- `check` prints `PASS|FAIL|SKIP <check>[ <role>]: <detail>` for `config` and `model`, then per role `blind`,
  `ancestor`, `probe` and `worktree`, then `waiters`, `formats`, `monitor`, `disk`, `usage` and `launch`; a `config`
  failure stops the rest. It writes `<run-dir>/_control/preflight.json`; exit 0 when nothing failed, 1 otherwise, 2 on
  a usage error. Options: `--config` (default `<run-dir>/_control/_agents.json`), `--launch` (default
  `<run-dir>/_launch.md`), `--roles` (default every agent of the config), `--unsandboxed ROLE` (repeatable: no
  `ancestor` or `probe` for that role), `--sim` (default the skill's `example/sim_bwrap.py`) or `--no-sim` (skip the
  probe), `--formats` (default the skill's `check_formats.py`), `--monitor` (default the skill's `monitor_records.py`)
  or `--no-monitor`, `--min-free-mb` (512), `--usage-age` (30 minutes), `--max-pct` (80), `--scale` (1: the run's
  rate against the measured one), `--hours` (5: the run's expected length), `--yes` (a `Yes:` line for every checked
  role), `--now` (default the current UTC time).
- `timeout` sums trials x sessions x `timeout_minutes` over the session cases of each suite directory (a directory with
  a `task.yaml` is one case); `--check MIN` fails (exit 1) when MIN is below the total.
- `polls` finds `sleep` loops in the Bash commands of the transcripts; exit 1 when it finds one.
- `clock` finds times not in `date -u` form and stamps more than `--slack` (10) minutes from the `--transcript` tool
  call that wrote them; exit 1 when it finds one.
````

- [ ] **Step 8 — the decision page, its summary, the index line and the log entry.** Write
  `wiki/decisions/the-launch-table-and-one-yes.md`:
````markdown
---
title: The launch table and one yes
type: decision
status: draft
updated: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: a launch spends the owner's money and limits, so the owner sees every role with its settings, skills, texts and cost in one table and answers once
would_change_if: a measured run in which launches approved without a table, or role by role, cost the owner less time and started no wrong role
decision_status: decided
scope: global
---
# The launch table and one yes

Before a launch the manager fills the run's `_launch.md` from the pipeline skill's `example/launch.md`: the purpose, the
size, the model rule, the estimate, the budget, the newest usage reading, and one row per role with its lane, settings
file, skills, ECC texts and cost estimate. The table goes to the owner in one message, which alone names the models; the
owner's answer is appended as a `Yes:` line, and `preflight.py check --yes` holds the launch until every role it starts
is named in one.

## Record and source
- [Pre-flight and capacity](../../.claude/skills/running-specagent-pipelines/references/preflight-and-capacity.md)
- [The launch table form](../../.claude/skills/running-specagent-pipelines/example/launch.md)
````
  Write `wiki/decisions/the-launch-table-and-one-yes.summary.md`:
````markdown
Decision (owner, 2026-10-29): the launch table and one yes.
Before a launch the manager fills _launch.md: purpose, size, model rule, estimate, budget, usage, one row per role.
The owner gets the table in one message, which alone names the models, and answers once; the answer is a Yes: line.
preflight.py check --yes holds the launch until every role it starts is named in a Yes: line.
````
  In `wiki/index.md`, add this line after the last line of `## Decisions` (after Task 1's two lines):
````markdown
- [The launch table and one yes](decisions/the-launch-table-and-one-yes.md): before a launch the owner gets one table of roles, settings, skills, ECC texts and costs and answers once; the answer is a Yes: line the pre-flight checks.
````
  Append to `wiki/log.md`, after one blank line:
````markdown
## 2026-10-29 pages written with Task 4 of the manager-build run
- commit: Task 4 of the manager-build run
- created: decisions/the-launch-table-and-one-yes.md
- updated: index.md
````
  Then run the first command of Step 2. Expected: `37 passed`.

- [ ] **Step 9 — the full checks.** Run, each from the checkout root (`command -v just` first if you run `just check`
  instead of the two ruff commands; `justfile:10` is the same pair):
  ```bash
  SK=.claude/skills/running-specagent-pipelines
  uv run pytest -q -p no:cacheprovider "${SK:?}/scripts/tests" 2>&1 | tail -1
  uv run ruff check . && uv run ruff format --check .
  python3 -I "${SK:?}/scripts/manager/catalogue.py" briefs "${SK:?}/example"; echo "exit $?"
  python3 -I "${SK:?}/scripts/manager/preflight.py" timeout evals/regression evals/capability; echo "exit $?"
  wc -c < "${SK:?}/SKILL.md"
  python3 -c 'import ast, sys; t = ast.parse(open(sys.argv[1]).read()); print(max(n.end_lineno - n.lineno + 1 for n in ast.walk(t) if isinstance(n, ast.FunctionDef)))' "${SK:?}/scripts/manager/preflight.py"
  ```
  The harness suite, `harness validate`, `docs-check` and `wiki-lint` are the verifier's (`_common.md:74-76`; C503).
  Expected: `239 passed`; `All checks passed!` then `... files already formatted`; `ok: 7 briefs checked` and `exit 0`
  (`check_briefs` reads only `*-assignment.md`, so `launch.md` is not a brief); then
````text
regression/access-probe-critic: 1 x 1 x 15 min = 15 min
regression/cache-share-reader: 1 x 2 x 15 min = 30 min
regression/pipeline-critic-unproven-finding: 1 x 1 x 15 min = 15 min
regression/pipeline-handoff-carries-facts: 1 x 1 x 10 min = 10 min
regression/pipeline-verifier-planted-defect: 1 x 1 x 15 min = 15 min
regression/reader-quotes-locations: 3 x 1 x 15 min = 45 min
capability/wiki-answer-grounded: 3 x 1 x 15 min = 45 min
total: 175 min over 7 session cases (10 code-only skipped)
exit 0
````
  `11764`; a number below 50. The 175 minutes are 5.9.1's timeout of these two suites at this commit, summed
  from their cases.

- [ ] **Step 10 — the commit.** Commit every file of the `files:` line with a pathspec:
  ```bash
  SK=.claude/skills/running-specagent-pipelines
  F=("${SK:?}/scripts/manager/preflight.py" "${SK:?}/scripts/tests/test_preflight.py"
     "${SK:?}/example/launch.md" "${SK:?}/scripts/tests/test_skill_example.py"
     "${SK:?}/example/README.md" "${SK:?}/example/common.md" "${SK:?}/example/sim_bwrap.py"
     "${SK:?}/references/preflight-and-capacity.md" "${SK:?}/scripts/tests/test_skill_md.py"
     "${SK:?}/SKILL.md" "${SK:?}/references/launch.md"
     "${SK:?}/scripts/manager/README.md" wiki/decisions/the-launch-table-and-one-yes.md
     wiki/decisions/the-launch-table-and-one-yes.summary.md wiki/index.md
     wiki/log.md)
  git add -- "${F[@]}" && git commit -F <file holding the message below> -- "${F[@]}"
  git show --stat --format=%h HEAD | tail -1
  ```
  Expected: a last line that begins ` 16 files changed`. Then append `Task 4: done — <sha>` to your build log.

## Wiki, index and llms lines
- `wiki/decisions/the-launch-table-and-one-yes.md` (answer 6a) with its `.summary.md` (Step 8); Task 11's section 9
  list links it.
- `wiki/index.md`: the line of Step 8, after Task 1's two decision lines; `wiki/log.md`: the entry of Step 8.
- `docs/llms.txt`: no line (it lists no skill file and no decision page: `grep -c 'wiki/decisions' docs/llms.txt` is 0
  at ff3354a). `references/preflight-and-capacity.md` and `example/launch.md` need no summary (`SUMMARY_FOLDERS` is
  `wiki/decisions` and `docs/runbooks`, `catalog.py:60`).

## Commit message
```text
feat(skill): the pre-flight, the launch table, the clock rule and the request lines

manager-build Task 4. scripts/manager/preflight.py checks a run before its launch: the config and every settings file
under _control/, no model outside the settings files, the blind deny rules, no deny on or above a write path, a sandbox
probe through sim_bwrap.py (which now expands ~/ in the sandbox paths), each worktree, the waiters, the formats, the
monitor's armed state, the disk, the usage reading against the five-hour and weekly limits and the _launch.md table with
one Yes: line per role (answer 6a); it sums a suite's timeout from its cases (5.9.1) and finds sleep loops and loose
times in a run's record (10.19, 10.20). example/launch.md is the table the owner answers once; example/common.md gains
the ACK rule, the clock rule, the CHECKOUT and FF requests, their answers and the request-line bound;
references/preflight-and-capacity.md holds the rules SKILL.md links.
```

## Deferred
- The pre-flight does not run Task 1's `catalogue.py briefs`: the manager runs it by hand at launch
  (`references/launch.md`, Task 1's 5c); a seventeenth check would tie the pre-flight's fixed result list (Step 1's
  first test) to another script's output. Sent to the plan fixer for the index's Deferred list.
- `sim_bwrap.py` gains only the `~/` expansion: no `Write(` rule (each has an `Edit(` twin), no last tmpfs of its own.
- The usage reading itself: the manager writes `_control/usage.json` from the desktop app's `get_usage` (D3); the
  pre-flight reads the file and never calls a usage service.
- A probe against a live run folder with the real bwrap: the main session's first launch of the next run; no test here
  starts bwrap or a session (the `probe` check takes `--sim`).

## Verified
- `example/sim_bwrap.py:13`: `agents_json, name, probe = sys.argv[1], sys.argv[2], sys.argv[3]`, the probe's argv.
- C502: `example/sim_bwrap.py:23` (`norm`: `Edit(~/.claude/**)` becomes `/~/.claude`), `:25-29` and `:33` (entries used
  as written, list argv); each `example/*settings*.json` (7) has 3 `~/` allowWrite and 6 `~/` denyRead entries,
  `Edit(~/.claude/**)` and an `Edit(` twin per `Write(` rule; Claude Code expands `~/` (vault
  `context/measurements/2026-10-29-sandbox-probes.md:6-7`, rows 1, 8, 13); a fake `bwrap`: 8 argv items hold `~`
  before, 0 after. Step 3's diff applies with `patch` and passes `ruff check` and `ruff format --check` at its path.
- `packages/harness/src/harness/evals.py:57-58` (`yaml.safe_load` of `evals/<suite>/*/task.yaml`), `:215`
  (`timeout=task["timeout_minutes"] * 60`), `:251` (`task.get("sessions", 1)`), `:476` (`task.get("trials", 1)`),
  `:488` (`task.get("session") is False`): the rules of `timeout`.
- `preflight.py timeout evals/regression evals/capability` (the scratch implementation, ff3354a's evals): the nine lines of
  Step 9, exit 0.
- Ruff 0.16.10 (`uv.lock:956-957`); `ruff check --show-settings` lists 826 rules, EXE001, EXE002, PLW1510, UP017 and
  FURB167 among them; the test file passes `ruff check` and `ruff format --check` with `pyproject.toml`.
  `ruff check --select EXE` on a file whose line 1 is `#!/usr/bin/env python3`: `Found 1 error.` (EXE001) at mode 644,
  `All checks passed!` at 755; the scratch implementation (no shebang, mode 664) passes it and all 37 tests.
- Step 2 and Step 3, measured on the scratch copy: `37 failed` (whole suite `37 failed, 146 passed`), then
  `2 failed, 35 passed` (`2 failed, 181 passed`), then `37 passed` (`183 passed`) after the doc texts; Task 1's tree has
  56 more tests (202 - 146; `202 passed` at task-01.md:1250 since 3cf4ec6), hence 239.
- The 26 wrong versions of Step 3, each run once against the tests: 26 red. A502's four of `probe` (no `~/` expansion;
  the raw entry in the detail; marks removed by the raw entries; home from the working directory): 1, 1, 1, 2 failed.
- `wc -c SKILL.md`: 11933 at ff3354a, 11947 with Step 6's four edits (+14), hence 11764 on Task 1's 11750.
- Task 3's `status` lines and exit codes: task-03.md:66-72, :185, :201-205 at 8d86fb3, carried into the Contracts by the
  plan fixer at 6d855b6.
- Task 1's `check_briefs` reads only `sorted(folder.glob("*-assignment.md"))` (task-01.md:184).
- `.claude/rules/python.md:9`: "Keep functions under 50 lines"; measured with `ast` (`end_lineno - lineno + 1`).
- `packages/harness/src/harness/plans.py:10-12`: a task file starts with `# Task N` and is checked against 1,500 lines.
- Python 3.12: `datetime.fromisoformat` reads a trailing `Z` (3.11 and later), `shutil.disk_usage`, `shutil.which`,
  `tempfile.gettempdir` (docs.python.org/3.12/library/datetime.html, shutil.html, tempfile.html).
- C17: task-05.md:62-66 at afc990c (`Launched:`, once); `date -u +%Y-%m-%dT%H:%M:%SZ` printed `2026-10-29T23:05:47Z`.
