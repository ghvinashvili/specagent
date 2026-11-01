# Pre-flight and capacity

What the manager checks and asks before a launch, and the rules that keep a run inside its time and its limits. The
script is `scripts/manager/preflight.py` (standard library only); its options are in `scripts/manager/README.md`.

### Pre-flight
Before every launch, the first one and each one after a settings change, run
`python3 -I scripts/manager/preflight.py check <run-dir> --checkout <checkout>`. It prints one `PASS`, `FAIL` or `SKIP`
line per check, writes `<run-dir>/_control/preflight.json` and exits 0 only when nothing failed; the launch waits for
that. The checks, in their order:
- `config`: the watcher config and every settings file lie inside `<run-dir>/_control/` and parse.
- `model`: no config, brief or `lessons.md` of the run names a model or passes the model flag (the model is the
  manager's setting).
- `cache`: the config's `common` carries `--autocompact 235000`, `--exclude-dynamic-system-prompt-sections` and
  `--system-prompt-snapshot on`, and its `handoff_at` and `cap` lie above the compaction point (about 197k); the role
  has its own `extra_prompt` whose pack is a file of the run folder holding its mark; its settings keep
  `CLAUDE_CODE_PROMPT_CACHE_TTL` at `5m`, the empty compaction override and a `model` (one model per lane; owner,
  2026-11-01, `launch.md`).
- `blind`: each role's settings deny the ten rules that keep it blind to transcripts, the control files, the hand-overs
  and the processes and away from the credentials file `~/.claude/.credentials.json`; a sandboxed role also fails closed
  and hides the same four paths from reading. An `Edit` or `Write` deny rule with one leading slash (`Edit(/x)`) fails
  it for every role (`sandbox-and-blindness.md`, "Rules with one slash"). Every role's settings also carry
  `"includeCoAuthoredBy": false`; a file where the key is absent, `true` or no boolean fails it, because the commit
  would end with a `Co-Authored-By` trailer that names the model. A file with an `attribution` key fails it too,
  whatever the key holds: a valid object wins over `includeCoAuthoredBy` and can bring the trailer back
  (`sandbox-and-blindness.md`, "The commit trailer").
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
- `live`: `claude agents --json --all` lists every live session, busy or idle; one outside the run (not an agent of its
  configs, not under their `<project>/` prefix) that is busy in the checkout or one of its worktrees fails it, unless a
  `Live:` line of the launch file names it. The manager reads the list, then writes
  `Live: <name>, <name> — <what each is>` (the duplicate manager chat of 2026-10-30 launched a second run unseen).
- `usage` and `launch`: below.

### The launch table and the yes
The manager fills `<run-dir>/_launch.md` from `example/launch.md`: the lines `Purpose:`, `Size:`, `Model rule:`,
`Estimate:` (roles, fresh sessions per unit, sessions; the measurement page of the last run of the same shape it comes
from, its cost per session and its start-up read in tokens from `startup_report.py`; dollars per unit), `Budget:` and
`Usage:`, and one table row per agent of every `_control/_agents*.json`,
named in its `role` cell as the config names it (`<project>/planner`), with its lane, settings file, skills, ECC texts
and cost estimate. The table holds every role of the run from the start: a critic needs a planner to answer its
findings, and the `launch` check refuses a critic with no planner (`PAIRS` in `preflight.py`; 2026-10-31, a run launched
without one left the manager answering the critic). The owner's yes rests on a measured price, not a guess (the ingest
run cost $43.01 against $15-25).
The table counts every session the run will start, fresh sessions per milestone and the final judge included. It goes
to the owner in one message, which alone names the models (they never go in a file the roles read). Each yes is
appended as
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
