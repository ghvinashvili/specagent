# scripts/manager

The manager's own scripts: standard library only, each run as `python3 -I <script>` and each read by the manager or by
the pre-flight before a launch, never by a role (no brief names them).

## catalogue.py
Measures what a role session loads (manager spec, section 3): every agent file (`.claude/agents/`), contract
(`docs/roles/types/`), example brief, skill (whole, and by its `description:` line, which is all a session loads before
the skill is used) and pinned ECC text (`.claude/ecc/agents/`), in bytes and in tokens at four bytes per token.
`table` prints the catalogue: a block per kind, a total per block, and a `half-use` column that says `over` for an item
above 2,500 tokens. `prefix` adds up one role's start-up prefix (each FILE whole, each `--skill` by its description
line, each `--ecc` text whole) and gives the verdict of spec 3.8: within 10,000 tokens, near up to 13,000, over above.
`briefs` checks the `## Domain checklist and skills` section of every `*-assignment.md` in a folder: one `Spec:` line
(pinned ranges under 60 lines in all, or `none — <why>`), one `Skills:` line (at most five skills under
`.claude/skills/`, each with its step, or `none — <why>`), the launch slot or the pasted text, under 60 lines. How the
numbers are used: `references/choosing-roles-and-skills.md`.

```text
Usage: python3 -I scripts/manager/catalogue.py table [--checkout DIR]
Usage: python3 -I scripts/manager/catalogue.py prefix FILE... [--skill NAME]... [--ecc NAME]... [--checkout DIR]
Usage: python3 -I scripts/manager/catalogue.py briefs DIR [--checkout DIR]
```

`--checkout` defaults to the checkout the skill sits in. Exit codes: 0 done (`prefix` within or near; `briefs` finds no
problem and prints `ok: <n> briefs checked`); 1 `prefix` over 13,000 tokens, or `briefs` finds a problem (one line each,
`<file>: <problem>`); 2 a folder or a file that cannot be read.

Example (a planner's brief files, one skill, two ECC texts):

```text
$ python3 -I scripts/manager/catalogue.py prefix example/common.md example/planner-assignment.md \
    example/handoff-rule.md example/first-pass-rules.md --skill python-testing --ecc architect --ecc code-architect
9080	example/common.md
6612	example/planner-assignment.md
3288	example/handoff-rule.md
2148	example/first-pass-rules.md
214	python-testing (description)
7240	.claude/ecc/agents/architect.md
2481	.claude/ecc/agents/code-architect.md
total: 31063 bytes, 7766 tokens, within
```

## preflight.py
Usage: python3 -I scripts/manager/preflight.py check <run-dir> --checkout <checkout> [--config P] [--launch P] [--roles A,B] [--unsandboxed ROLE]... [--sim P | --no-sim] [--formats P] [--monitor P | --no-monitor] [--min-free-mb N] [--usage-age MIN] [--max-pct PCT] [--scale X] [--hours H] [--yes] [--now ISO]
Usage: python3 -I scripts/manager/preflight.py timeout <dir>... [--check MIN]
Usage: python3 -I scripts/manager/preflight.py polls <transcript>...
Usage: python3 -I scripts/manager/preflight.py clock <record>... [--transcript JSONL]... [--slack MIN]

The manager's checks before a launch and two audits of a run's practice (`references/preflight-and-capacity.md`).
- `check` prints `PASS|FAIL|SKIP <check>[ <role>]: <detail>` for `config` and `model`, then per role `blind`,
  `ancestor`, `probe` and `worktree`, then `waiters`, `formats`, `monitor`, `disk`, `usage`, `live` and `launch`; a
  `config` failure stops the rest. `live` fails on a busy outside session in the checkout or its worktrees that no
  `Live:` line names. It writes `<run-dir>/_control/preflight.json`; exit 0 when nothing failed, 1 otherwise, 2 on a
  usage error. Options: `--config` (default `<run-dir>/_control/_agents.json`), `--launch` (default
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

## surface.py
The owner's surface: one line for the run (its cost from `usage_report.py` against the
`$` amount of the `Budget:` line of `_launch.md`), one per role of the registry its config names (state, unit and how
long on it, context, cost, what it waits for, the record path), the newest reading of `_control/usage.json` with the
next reset, the hand-over orders past the cap, the free disk and the open alarms of `_control/monitor.json`. The
registry is the `registry` field of `--config` (default `_control/_agents.json`), else `_control/registry.json`, as the
watcher reads it. Each line is a phrase of the phrase file (default `example/surface-phrases.en.json`) with the numbers
inserted. The manager answers status questions from it and keeps `_control/surface.txt` fresh with `--out` and
`--every 120` in the background.
Exit 0; 2 with one `surface: <reason>` line on stderr (argparse's own 2 for a bad option).

Usage: python3 -I scripts/manager/surface.py RUN_DIR [--config FILE] [--phrases FILE] [--prefix P] [--since YYYY-MM-DD] [--now YYYY-MM-DDTHH:MM:SSZ] [--out FILE] [--every SECONDS] [--rounds N]

Usage: python3 -I scripts/manager/surface.py --check-phrases FILE

## measure_manager.py

The manager's own measures, from the transcript path the manager gives
(`~/.claude/projects/<project>/<session id>.jsonl`; a call and its context as `usage_report.py` counts them):
its first call against 30,000 tokens (three starts in a row; the first transcripts of both profiles, the one under
30,000 is kept), every call against the 200,000 cap and a `*-handoff.md` file written before each
compaction, since the compaction before or the session's start, the manager-lessons page read in a tool call of
the first five calls, the page's form, size and recurrences, and the findings per `Checklist:` item, the
count that promotes a shared cause to a rule. Read-only, no model, standard library only.

```text
Usage: python3 -I scripts/manager/measure_manager.py first-call TRANSCRIPT... [--limit 30000]
Usage: python3 -I scripts/manager/measure_manager.py calls TRANSCRIPT [--cap 200000] [--handoff-dir DIR]
Usage: python3 -I scripts/manager/measure_manager.py reads TRANSCRIPT TEXT [--calls 5]
Usage: python3 -I scripts/manager/measure_manager.py lessons PAGE [--max-bytes 8000] [--since YYYY-MM-DD]
Usage: python3 -I scripts/manager/measure_manager.py checklist RECORD...
```

Exit 0 when every check passes, 1 when one fails, 2 on a usage error or a missing file. `lessons` with `--since <the
run's first day>` prints the items added, the items fired again with their counts and the recurrences for the run's
measurement page;
`checklist <run>/critique.md <run>/verify.md` prints `<count> <file>:<line>` per cited item, highest first.

## score_run.py

One score per run folder: the findings per task by kind (C, A, R, V; the V ids
with a `(plan)` cause and the ones the critic missed: a `(plan)` V on a task with a `## Task N` section in
`critique.md`; the builders' B ids), the sessions, hand-overs (`fresh` lines of `_watch.log`), cap orders (`cap`
lines) and idle restarts per role, the first-call context (median), the cache-read share, the cost per
task and per role at `usage_report.py`'s prices (a role's cost split into the dollars of its cache reads, writes and
output), the request lines with the minutes to their answer, and the lesson classes repeated. Read-only.

```text
Usage: python3 -I scripts/manager/score_run.py RUN_DIR [--prefix NAME/] [--since YYYY-MM-DD] [--json]
```

Rules, applied alike to every run:
1. A call writes a record file when it is an Edit or Write whose path names one, or a Bash command whose stdout
   redirection (`>`, `>>`), `tee` or `sed -i` names it outside quotes; a Read, `2>/dev/null`, `2>&1` and `>&2`
   write nothing. Its text is the command (Bash), the lines `new_string` adds (Edit) or the content (Write).
2. That text names a task by `Task N:` or `## Task N` at a line start (or after a quote), or by an id there
   (`#### C2`, `V1: applied — …`): the task the id is filed under, C, A and R by `critique.md`'s sections, V by
   `verify.md`'s, a B by the build-log rule below in the log it is written to; a B answered in
   `critique-response.md` names the task of the B whose first line in its log says `sent to`. An id filed under no
   task names none.
3. A session that names no task takes the tasks of its role's next session (by start time) that names one: a
   hand-over continues its unit, an idle restart is that unit's cost; a role's sessions after its last naming
   session keep `none`.
4. `attribution[<session id>]["by"]` says how: `lines`, `next` or `none`; two or more tasks split the cost equally.
5. `rejected`, per task: the ids filed under it with an answer line `<id>: rejected` in `critique-response.md` or a
   build log, each id once (a B by a line in its own log, or in `critique-response.md` when its log says `sent to`);
   an id filed under no task counts in `none`.
6. A session is idle when none of its record writes holds a unit line (a `Task N` or id line as rule 2 finds them,
   or a request line: `SANDBOX:`, `COPY-REQUEST:`, `CHECKOUT-REQUEST:`, `FF-REQUEST:`), it ran no `git commit`
   and reached no call over 200,000 tokens.

A B id counts once per build log (an `answered` line repeats the id), for the task its text names first after its
first ` — `, else for the task of the next `Task N: done` line below it, else for `none`. A finding counts in
`repeated` from one up, keyed by its `Checklist:` item when that item is a line of `lessons.md` (any path ending in
it): a line of the section that starts `Checklist:` and holds one `<file>:<line>` token, the rule of
`measure_manager.py checklist`; prose or a `Checklist:` in backticks is none. The minutes of
a request need a `YYYY-MM-DD HH:MM UTC` time on the request line and its answer, else `n/a`. A missing source leaves
its cells `n/a` and notes it at the end of the first line: `_watch.log` the fresh and cap cells, the `claude`
command the sessions, a role's transcripts its idle, first call, cache read, cost and dollars (and the task costs, with no
transcript on the machine). Exit 0; the first line is the score, then the tables; `--json` prints the whole
result, with `attribution` per session id.

An economy row ends the output (`--json`: `economy`), per numbered task:
`| units | cost per unit | cache write $ per unit | sessions per unit | copies per unit | findings per unit | escaped |`,
copies being the `cap` and `unit end` lines of `_watch.log` (else `_control/watch.out`), `escaped` the M, J and O ids.

The first line for the manager-build run of 2026-10-29:

```text
score manager-build-2026-10-29: tasks 11, findings C 32 A 13 R 8 V 9 (plan 5, missed 3), rejected 0, sessions 210 (cap 56, idle 3), cost $674.50, cache-read 98%
```

The three tables' header rows, then the last line (`none` when no finding cites `lessons.md`):

```text
| task | C | A | R | V | V plan | missed | B | rejected | cost |
| role | sessions | fresh | cap | idle | first call | cache read | cost | read $ | write $ | output $ |
| request | file:line | minutes |
repeated lesson classes: lessons.md:12 (C1, V1)
```
