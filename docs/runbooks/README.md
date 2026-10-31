# Runbooks

| Situation | File |
| --- | --- |
| a run does not move, a session is blocked or timed out | `stuck-run.md` |
| worktree branches of shards conflict at merge | `worktree-conflict.md` |
| a usage limit or an API error stopped sessions | `usage-limit.md` |
| run a pipeline of background SpecAgent sessions (planner, plan fixer, critic, builders, verifier, judge) | [the pipeline skill](../../.claude/skills/running-specagent-pipelines/SKILL.md) |
| the disk fills with finished background jobs' `tmp` folders | `python3 -I .claude/skills/running-specagent-pipelines/scripts/clean_jobs_tmp.py` (a dry run; `--apply` removes) |
| a file too large to read whole: its outline with line ranges, or titled parts behind an index, each file at most 12,000 bytes | `python3 ops/outline.py <file>`; `python3 ops/split_large.py <file or folder>` |
| the source material in `context/` needs its layered indexes (categories in `ops/indexes.json`) | `python3 ops/build_indexes.py` |
| several slow test files: run them 4 at a time | `bash ops/par-tests.sh <out prefix> "<test command>" <path> ...` |
| the code graph is missing or out of date (no `wiki/graph/index.md`, or a commit, merge or checkout left it behind) | `bash ops/graph.sh` (the body of `just graph`; the `.githooks/` hooks run it with `--quick` after each commit, merge and checkout, about 5 s); hooks off, when `git config --get core.hooksPath` prints nothing: `python3 ops/bootstrap.py --wait`; graphify itself: `uv tool install graphifyy==0.9.64` |
| a measurement must run for hours on a server with nobody logged in | [server-windows.md](server-windows.md) |
| a site refuses the project's bot on a page robots.txt allows | [browser-fallback.md](browser-fallback.md) |
| an ECC rule, skill or agent text is out of date, or a pinned copy must change | [ECC sources](../../.claude/ecc/sources.md), "Re-pin" |
| a chat-role brief needs a domain's checks (a reviewer, a build-error resolver, a security or database role) | [ECC agents](../../.claude/ecc/agents/README.md): the copy nearest to the role, borrowed as [ECC sources](../../.claude/ecc/sources.md), "Agents", says |
| after an edit Claude reads "could not format", or that no test names a new source file | [ECC hook recipes](../../.claude/ecc/hook-recipes.md), "This repository's hooks" |

## How you are told
- `harness poll` sends one line for every new action that needs you (`escalation`, `approval`, `attention`, `max_attempts`,
  `timeout`, `limit_human`) and one when a run is done. The line goes to the standard input of the command in
  `HARNESS_NOTIFY_CMD` (export it in the shell that starts the manager and in the operator's crontab; see `.env.example`).
  Every line is also appended to `<runs root>/_audit/notify.jsonl`, whether or not a command is set.
- The `Notification` hook (`.claude/hooks/notify.py`) forwards what Claude Code itself announces in the manager's session:
  a permission prompt, an idle prompt, a usage-limit continuation that did not happen. Its types for background sessions
  (`agent_needs_input`, `agent_completed`) fire only while agent view is open in a terminal, so the poll is the reliable path.
- A poll happens only while something polls: the manager's `/loop`, or the night tick (`ops/night-tick.sh poll`).

## First look, always
1. `<runs root>/<run-id>/HANDOFF.md` (`uv run harness handoff --run <run-id>` rewrites it).
2. `uv run harness poll --run <run-id>`: the actions.
3. `claude agents --json --all --cwd .` and `claude logs <job-id>` for a session; never transcripts.
