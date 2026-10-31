# The manager in chat: the pipeline skill's main session

The owner's manager is the main session that runs the pipeline skill (`.claude/skills/running-specagent-pipelines/`,
`<skill>` below). It is the one chat the owner talks to: it plans a run with the owner, launches the roles as
background sessions with the owner's yes, keeps them moving, measures them and itself, and writes down what was
learned. `docs/roles/MANAGER.md` is the harness's manager (`claude --agent manager`), a separate design for harness
runs; this page is about the chat.

## No sandbox, four guards

Every role runs sandboxed and blind: it sees its brief, its worktree and the run folder. The manager runs without the
sandbox, because it does what the sandbox refuses the roles: merges in any worktree, `.claude/` and `.git`
administration, data moved between disks, sessions launched and stopped, transcripts read for measurements, and the
vault pushed. Four guards take the sandbox's place:

1. The permission rules: never read the credentials under `~/.config`, never push the template.
2. The auto-mode classifier: an irreversible deletion is refused and left to the owner.
3. The owner's launch rule: agents and the judge start only with the owner's yes, asked in one message with their
   count, purpose, settings files and estimated cost.
4. It never runs project code or tests itself; the roles do, in their sandboxes.

The template's project session keeps the sandbox on: the `sandbox` block of `.claude/settings.json` sets `enabled`
true and `allowUnsandboxedCommands` false, and its `excludedCommands` are `claude *`, the `uv run harness` commands
`launch`, `resume`, `poll`, `eval`, `watch`, `doctor*`, `abort` and `integrate`, and `python3 ops/machine-setup.py`
with no option, `--user` or `--undo`. The manager's chat is another session. A role's refusal (`SANDBOX:`, "Read-only
file system", "sandbox violation") is answered by supplying the path, host or material into the run folder, never by
weakening a sandbox; a step that cannot wait is held, not faked.

## Duties by phase

Each script runs as `python3 -I <skill>/scripts/...`; every time the manager writes comes from `date -u`.

Before a run:
- The size rule: a pipeline only when one context cannot hold the work; otherwise one session and a verifier.
- The duty list, after the index and before the launch:
  `scripts/duty_list.py extract <plan-dir> --out <run-dir>/_control/duties.md`.
- The pre-flight: `scripts/manager/preflight.py`; the usage reading of the desktop app's `get_usage` is written to
  `_control/usage.json` before each launch.
- The `_launch.md` table, each of its times from `date -u`.

During a run:
- The monitor: `scripts/monitor_records.py watch <run-dir>`, a background command, re-armed with the same command
  after every exit.
- The surface, started after the launch as a background command and re-armed after every exit, as the monitor is:
  `scripts/manager/surface.py <run> --phrases <file> --out <run>/_control/surface.txt --every 120`.
- Orders: `scripts/watch_agents.py --order <agent> <text> <config>` prints `order <msg_id> <agent>` and the prompt
  the manager sends; the role answers `ACK <msg_id>` at a line start, and a missing ACK is resent by stop and resume.
- The `Merged:` duties, each `Merged:` line with the merge's hex sha.

The owner's questions:
- A routine question is decided by the manager, with the assumption stated.
- Only four kinds are asked, once, in one message with the sizes and the options: agent launches, destructive or
  irreversible actions, merges into `main`, and spending.
- Every status line carries a digit and a record path.
- The status answer is two or three short lines, "now: …, next: …". Their figures (a role's unit, context and cost,
  the run's cost) are copied as printed from the stdout of
  `python3 -I <skill>/scripts/manager/surface.py <run> --phrases <owner phrase file>`, never computed, and each line
  carries the record path `<run>/_control/surface.txt`. The whole stdout goes to the owner only when the owner asks
  for the costs or the full state.

After a run: the measurements, in the order of `references/measuring.md`, `### After every run, in this order`, then
the steps of `## After a run` below.

## Measuring itself

The manager starts under 30,000 tokens. Both profiles, the terminal `claude` profile and `just manager` (`justfile`),
are measured once at their first call with `measure_manager.py first-call <one transcript of each>`, and the one
under 30,000 is kept; then `first-call` runs on three starts in a row. At the run's end:
- `measure_manager.py calls <transcript> --handoff-dir <container>/docs/handoff`: no call over 200,000 tokens, and a
  hand-off written before each compaction;
- `measure_manager.py reads <transcript> decisions/global/manager-lessons.md`: the lessons page read in one of the
  first five calls.

The transcript is `~/.claude/projects/<project>/<session id>.jsonl`; the tool is
`python3 -I <skill>/scripts/manager/measure_manager.py` (`scripts/manager/README.md`). The numbers go on the run's
measurement page, `<vault>/context/measurements/<date>-<run>.md`.

It hands over at 200k like every role: a hand-off under `docs/handoff/`, written before the compaction at the hook's
first notice (`.claude/hooks/handoff.py`), then a fresh session; never an endless chat.

## Recovery

After a reboot: `claude respawn --all`. After a compaction or a fresh start, the manager reads, in this order:
1. the newest hand-off note under `docs/handoff/`;
2. the lessons page, `<vault>/decisions/global/manager-lessons.md`;
3. `_control/registry.json`, before any record (each role's unit, state and orders, as the watcher keeps them);
4. `head -1` of every record file;
5. the tail of `_watch.log`;
6. `claude agents --json --all`.

Then it restarts the watcher on `_agents.json`. No transcript is read back.

## The lessons page

`<vault>/decisions/global/manager-lessons.md`, pushed with the vault, holds the main session's own mistakes: the
global items under `## All projects` and one section per project under it, copied once from
`templates/vault/forms/manager-lessons.md`. Every main session reads it in its first calls. An item is appended the
moment a mistake is found, with its measured cost and its record:
`<n>. <trigger> -> <rule>; cost measured <cost>; <YYYY-MM-DD>, <record>`. The same mistake again appends a date and a
record to its item; an item that fired in no run for three runs moves below the fold with its number. The page stays
under 8,000 bytes, checked with `measure_manager.py lessons <page> --since <the run's first day>`. The first four items
of spec 7.7 (a duty read late, a rollout not simulated, an estimated time, a guessed timeout) are written by the main
session with their records.

## After a run

1. An owner decision goes as one line into `<vault>/context/owner-statements/<date>.md` in the same turn (the owner's
   words, the `date -u` time, the meaning in one sentence), committed before any page cites it.
2. Then the page: global in `decisions/global/`, project in `wiki/decisions/`, with `decided`, `by`, `why` and
   `would_change_if`, and one `INDEX.md` line.
3. The measurement page before any summary cites a number; `ops/check_pages.py` after every vault write, with 0
   problems.
4. One `log.md` line per unit of work.
5. The learning loop: a lesson becomes a record in the form of `forms/learning-record.md`; a trigger that recurs in
   two runs or two projects, or a cause two findings share
   (`measure_manager.py checklist <run>/critique.md <run>/verify.md`), becomes a decision page and one line in the
   skill or the brief template, by hand. `audit_read_first.py` runs before a "Read first" section is compacted, and
   `replay_cases.py` turns a finding with a read-only command into an eval case. Roles write only `lessons.md` and
   their record; the manager writes the pages.
6. Then the collector: each item of `## Lessons from this run` is marked `(skill: <sha>)` or `(skill: none)`, and the
   `Merged:` records stay unmarked. Then
   `python3 -I <skill>/scripts/collect_run.py <run> --repo <checkout> --plan <plan folder> --kept <page> ...` runs as
   a dry run and its list goes to the owner; on the owner's yes the same command runs with `--apply --yes <digest>`;
   after three such runs, `--apply` alone. The owner reads `<run>/collected.md`.

The graph over the vault: no graph rule exists before a measurement page of the export's size and of a query's
tokens; that measurement is the main session's.
