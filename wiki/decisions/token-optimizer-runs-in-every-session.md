---
title: token-optimizer runs in every session
type: decision
status: draft
updated: 2026-11-01
created: 2026-11-01
tags:
  - decision
  - economy
audience: [all]
decided: 2026-11-01
by: owner
why: the owner wants the plugin's compression, checkpoints and measurement in every session, the roles included, with every feature on, and a downloaded template set up the same way without a manual step
would_change_if: a run whose verifier or builder was wrong because a compressed tool result hid the line it needed, measured against the same unit without the plugin; or a release of the plugin that `harness validate` refuses and nobody accepts
decision_status: decided
scope: global
---
# token-optimizer runs in every session

The owner (2026-11-01): the plugin works in full, in every session, nothing of it turned off. The main session had
turned the lossy parts off on its own reading of "maximum accuracy" and was corrected the same hour.

## The rule
- `token-optimizer` (github.com/alexgreensh/token-optimizer, PolyForm Noncommercial 1.0.0 with a small-business
  permission) is declared in `plugins/.claude-plugin/marketplace.json` with a github source and enabled in
  `.claude/settings.json`; `ops/bootstrap.py` installs it at project scope from the author's repository. Its code is
  never vendored: the licence forbids commercial use beyond the small-business permission, so a project that does not
  qualify removes the entry from the marketplace, the settings, `docs/roles/extensions.yaml` and
  `docs/roles/need-to-know.yaml`.
- Every feature stays on: Bash, search and MCP output compressed after the call, a repeated Read of an unchanged file
  served as a diff or a structure map, a checkpoint before compaction and a restore after it, the quality score, the
  savings ledger and the dashboard. A feature of it is switched off only on the owner's word.
- Role sessions: a role runs under `--setting-sources local` and loads no project plugin by itself, so bootstrap writes
  the plugin's installed directory into `plugin_dirs` of `specagent-launch.json` in Claude Code's config directory, and
  the pipeline skill's watcher adds `--plugin-dir` for it to every launch and resume. The harness's stage launcher gives
  it to every role type through `plugins` of `docs/roles/need-to-know.yaml`.
- `docs/roles/extensions.yaml` accepts version 5.13.61 and what it brings (11 hook events, 5 skills, 2 commands);
  `harness validate` fails on another version or a new component until a human accepts it again.
- Its state is per role session, never shared (the owner, 2026-11-01: usable, but one role cannot read another's):
  `agent_env_dirs` of `docs/roles/need-to-know.yaml` names `TOKEN_OPTIMIZER_PLUGIN_DATA`, the variable the plugin
  prefers over Claude Code's shared `CLAUDE_PLUGIN_DATA` for its archives, read cache, checkpoints and session
  database; the harness gives every stage `<stage dir>/plugin-data/<VAR>`, the pipeline skill's watcher gives every
  agent `<run dir>/_plugin-data/<agent>/<VAR>` and denies the other agents' directories (permissions and sandbox);
  the consent flags are seeded so the hooks work from the first call. The session's own chat loads the plugin
  with Claude Code's shared data directory, as before.
- The marketplace entry pins the git tag `v5.13.61`, the version `docs/roles/extensions.yaml` accepts; bootstrap
  installs that version's directory into the launch file. A newer release is taken by changing both and accepting
  what it brings.

## What was measured
Replayed on the spec 006 run's 55 sessions (the owner's vault, measurement 2026-11-01-token-optimizer-replay), the
compression would have saved about 0.1% net of the billed tokens, at most 1.7%: 96% of the billed tokens are context
re-reads, most Bash output is file text the plugin leaves alone, and the plugin adds about 500 tokens of its own to
every call. In a live test it cut a 60-commit `git log` to a header saying 42 commits, and the model answered 42. The
live runs with it on are the measurement that decides `would_change_if`.
