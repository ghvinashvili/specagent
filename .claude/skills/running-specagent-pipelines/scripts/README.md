# Scripts

What each script does, how to run it, and the watcher's config (version 2). They need Python 3.12 and its standard
library only (`judge_after_verify.sh` also bash and git); none runs a model or uses the network. Run them with `python3 -I`, from the skill folder or by full
path. The waiters and the watcher run in the background (Bash `run_in_background`); every other script reads and
prints, and writes nothing unless its page says so. Each script's docstring has the details; its tests are in
`tests/` (see Tests). Each script's usage, options and files are on its page under `docs/`; this file
indexes them and keeps the config fields and the tests. The manager's own scripts are in `manager/`, with a
README of their own.

## Watching

- [`watch_agents.py`](docs/watch_agents.md): the watcher, version 3
- [`monitor_records.py`](docs/monitor_records.md): the record monitor: request lines, claims, duties, verdicts
- [`duty_list.py`](docs/duty_list.md): the manager's duty list from the plan
- [`migrate_agents_json.py`](docs/migrate_agents_json.md): a live run folder to config v2
- [`judge_after_verify.sh`](docs/judge_after_verify.md): the judge, once, after every task is verified

## Waiting
Zero-token waiters: each polls every 30 s, exits 0 when there is work, and returns within 3.5 minutes with exit 3 and
the line "Run the same command again now", so a waiting role's next call comes inside the 5-minute prompt cache
(owner, 2026-11-01); a wait known to be longer than about an hour ends the session instead. Copy them into
the run folder (`_wait_for_*.py`) and write the full command with its path arguments into each brief. With `--once`
each checks once and exits 0 (work) or 3 (none): the form an agent's `work_check` takes, as `open_ids.py` does.

- [`wait_for_task.py`](docs/wait_for_task.md): the critic's waiter
- [`wait_for_ready.py`](docs/wait_for_ready.md): the builder's waiter
- [`wait_for_log.py`](docs/wait_for_log.md): the verifier's waiter
- [`open_ids.py`](docs/open_ids.md): the open finding ids of a run folder; the plan fixer's `work_check`

## Measuring
Read-only reports for the main session (see `references/measuring.md`, "Measuring the pipeline", for when to run
which).

- [`usage_report.py`](docs/usage_report.md): tokens and cost per agent
- [`startup_report.py`](docs/startup_report.md): the start-up cost per session
- [`check_formats.py`](docs/check_formats.md): the format check of a run folder
- [`findings_report.py`](docs/findings_report.md): findings per kind and the escape table
- [`audit_read_first.py`](docs/audit_read_first.md): the "Read first" audit
- [`replay_cases.py`](docs/replay_cases.md): replay cases from findings
- [`make_pack.py`](docs/make_pack.md): a role's startup pack

## Cleaning up

- [`clean_jobs_tmp.py`](docs/clean_jobs_tmp.md): the tmp folders of finished background jobs
- [`collect_run.py`](docs/collect_run.md): a finished run's leftovers, removed only after its record is checked as saved

## Config v2
The config of `watch_agents.py` (`agents.json`; `example/agents.json` is one). Only `run_dir` and `agents` are
required; every other field takes its default. Keys that begin with `_` are ignored (comments). An unknown field,
`pack: true`, an agent without one of its fields, a role without a fresh text, a `handoff_at` not below `cap` or a `registry` that leaves `run_dir` is a config error (exit 2 at start; a reload keeps such a config out).

| field | default | meaning |
|---|---|---|
| `run_dir` | required | the run folder: record files, hand-over notes, briefs, settings files |
| `agents` | required | name → the agent's fields (below); the role is the part of the name after the slash |
| `common` | `[]` | flags for every launch and resume (`--effort max --setting-sources local …`; the model is set in the settings file) |
| `blocked_files` | `[]` | files of the run folder whose line 1 holding `blocked` (any case) is an exit event |
| `cap` | `260000` | the context of a session's last call, in tokens, past which it is ordered to hand over (a backstop: `--autocompact 235000` compacts near 197k first) |
| `handoff_wait` | `1200` | seconds after the order before a fresh session starts without a note |
| `nudges` | `6` | revivals per agent |
| `permission_wait` | `600` | seconds a block may last before it is cancelled or exits; `null`: every block exits at once |
| `final_stop_minutes` | `10` | a final agent's live session is stopped by the watcher: at its prompt at once, busy once its record is this many minutes old; the end exit waits for it; `null`: left live (owner, 2026-10-30: sessions close without the owner) |
| `interval` | `120` | seconds between rounds |
| `budget` | `{"calls": 3000, "output_tokens": 40000000}` | per session, counted over its whole transcript (compactions and waiter calls included); past either: the `budget …` line and exit 3 |
| `fresh` | the code's texts | role → the fresh session's prompt, `{run}` filled in; merged over the defaults |
| `lang` | the English-only sentence | appended to every fresh text, the nudge, the hand-over, unit-end and reload orders; `""`: nothing |
| `nudge` | the code's text | the prompt that resumes a revived session |
| `handoff_order` | the code's text | the prompt that resumes a session at the cap; `{run}` filled in |
| `unblock` | the code's text | the prompt that resumes a session after a cancelled permission prompt |
| `milestones` | `[]` | task numbers at which the builder and the verifier get fresh sessions (see [the watcher's page](docs/watch_agents.md)) |
| `extra_prompt` | none | `{"file": "<file in run_dir>", "mark": "<its first line>"}`, given below |
| `pack` | none | startup packs (`scripts/make_pack.py`), which this watcher does not pass: `true` is a config error |
| `handoff_at` | `250000` | context tokens of the last call past which the end of a unit orders a hand-over; below `cap` (absent with an own `cap` below 250000: three quarters of it) |
| `unit_end_grace` | `600` | seconds a unit end waits, from when its new line 1 was written, for the session's own note before the order; `0`: at once |
| `ack_wait` | `900` | seconds an order waits for its `ACK <msg_id>` line before it is resent |
| `ack_resends` | `2` | resends of an order without its `ACK` line; then `no ack …` and exit code 0 |
| `registry` | `"_control/registry.json"` | the registry file in `run_dir`; `orders.jsonl`, the inbox of `--order`, lies beside it; `manager/surface.py` reads the registry there too; a path that leaves `run_dir` is a config error |
| `unit_end_order` | the code's text | the prompt that resumes a session at a unit's end past `handoff_at`; `{run}` and `{at}` filled in |
| `reload_order` | the code's text | the prompt that resumes a session after a brief its texts name changed; `{file}` and `{time}` (UTC) filled in |

`fresh` holds an earlier run's texts for `planner`, `critic`, `builder`, `verifier` and `judge`, another's for
`plan-fixer`, and the milestone texts `milestone-builder` (`{n}`, `{next}`) and `milestone-verifier` (`{n}`); a config
gives only the roles it changes or adds (an earlier run's `builder-kb`, `verifier-kb`). `extra_prompt`'s file is passed with
`--append-system-prompt-file` to every new session and to the resume of a session whose transcript carries the mark
(an earlier run's `_caveman.md`). `migrate_agents_json.py` writes these fields from a live copy.

The fields of an agent (`agents.<name>`):

| field | meaning |
|---|---|
| `cwd` | the directory the session runs in (its checkout) |
| `add_dirs` | the `--add-dir` directories |
| `settings` | its settings file in `run_dir` (`_control/<role>-settings.json` in the examples, behind every role's `_control/**` deny), passed as text with `--settings` |
| `status` | its record file in `run_dir`; line 1 is its STATUS |
| `final` | the STATUS prefix that ends its work (`STATUS: done`) |
| `budget` | optional: overrides the common `budget` for this agent's sessions |
| `extra_prompt` | optional: `{"file", "mark"}`, this lane's own frozen pack in the system prompt (`--append-system-prompt-file`), replacing the run's `extra_prompt` for this agent; a new session gets it, a resume only when its transcript holds the mark; a changed file exits 4 |
| `work_check` | optional: a command (a list of strings, `{run}` and `{skill}` filled in) run on a hand-over note; exit 0 launches the fresh session, 3 leaves the role idle and re-checks it every round, any other launches (see [the watcher's page](docs/watch_agents.md)) |
| `on_demand` | optional, default `false`: the watcher alone launches the agent, when its `demand` passes, and stops it when none of its ids is open; the manager never launches it at the start, and it is never revived (see [the watcher's page](docs/watch_agents.md)) |
| `demand` | optional, needs `on_demand`: `kinds` (default `["C", "A", "B", "V", "R"]`), `cause` (`"plan"` or `"any"`, default `"plan"`), `parity` (`"odd"`, `"even"` or `"all"`, default `"all"`), `shared` (default `true`; `false` drops the shared ids, the index's, a non-task section's and the build logs' B lines: the second fixer's, judge J3), `queue` (a positive integer, default 6), `wait_minutes` (a non-negative number, default 45); the agent is launched when its open ids reach `queue` or the oldest has waited `wait_minutes`, and a key left out takes its default |

## Tests
```
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests
uv run pytest -q -p no:cacheprovider .claude/skills/running-specagent-pipelines/scripts/tests
```
The first from the skill folder, the second from the repository root (its `pyproject.toml` collects them with the
packages' tests), in under twenty seconds: synthetic run folders and transcripts under pytest's tmp_path, a stub
`claude` on PATH that answers `agents --json --all` and logs every other call; no model, no network. `test_docs.py`
checks this file, the pages under `docs/` and `example/agents.json` against the scripts; `test_skill_md.py`
checks `SKILL.md` and `references/`.
