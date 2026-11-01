# Launch
```bash
cd <repo> && claude --name <role> --add-dir <run-dir> <more dirs> --strict-mcp-config --effort max \
  --permission-mode auto --setting-sources local --settings "$(cat <run-dir>/_control/<role>-settings.json)" \
  --bg "Read and follow the assignment in <run-dir>/<role>-assignment.md. Start now."
```
- Add `--setting-sources local` to every launch and resume (also in `agents.json` `common`): for a checkout under the owner's home directory, Claude Code loads `~/.claude/CLAUDE.md` through the project source as well, and its language rule made about half of the planner's sessions think and narrate in that language (measured 2026-10-22: critic 0 of 9 sessions, planner 7 of 15). Settings passed with `--settings` still apply (tested: a deny holds); the project's `.claude/settings.json`, hooks and CLAUDE.md are not loaded, which the briefs replace.
- Put `--bg` last, right before the prompt; a variadic flag such as `--add-dir` swallows a prompt that follows it.
- Settings per role (see `example/*-settings.json`): allow `SendMessage`, `ListAgents`, `ToolSearch` and what the role
  uses; deny `Agent`, `EnterWorktree`, `AskUserQuestion` and git commands that rewrite or move branches; add
  `"crossSessionInbound": "accept"` (it did not stop holds of the main session's messages when passed through
  `--settings`, 2026-10-09); add the compaction override of the next item; set `"model"` by the role's class
  (specification, judgment or mechanical: the rule row "Models are set per role" of `SKILL.md`; the launch table's
  message names the models, no file a role reads does) and keep the effort max; add `"includeCoAuthoredBy": false`
  (the default `Co-Authored-By` trailer of a commit names the model, which no role may know; the pre-flight's `blind`
  check fails a file without it).
- No early compaction in SpecAgent sessions: `"env": {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": ""}` in `--settings` clears the
  main session's 60%, which the daemon passes on; never `--autocompact` with a small window.
- The cache TTL per role: `"CLAUDE_CODE_PROMPT_CACHE_TTL": "<ttl>"` in the role's settings `env` next to that override
  (Claude Code 2.1.316 reads `5m` or `1h`, and the variable wins over the `promptCacheTtl` setting; unset, a subscription
  within its limits gets 1 hour and an API key 5 minutes). A cache write at 1 hour costs more than one at 5 minutes, and
  a gap over 5 minutes makes the next call write the prefix again (`docs/economy.md`, measured 2026-10-31), so the TTL
  follows whether the role waits on another role; `example/*-settings.json` carry it:

| TTL | Roles | Why |
|---|---|---|
| `5m` | planner, builder-a, builder-b, any writer | they wait on no other role: the next call comes within minutes |
| `1h` | verifier, critic, plan-fixer, judge | they wait for a log line or a task: gaps over 5 minutes are the rule |

- Only the plugins and MCP a role needs: `--strict-mcp-config` on every launch and resume; design plugins only for
  design roles (`~/.claude/design-plugins.json` merged into `--settings`).
- A role that reads or writes the wiki loads the claude-obsidian plugin: `--plugin-dir "$(python3 ops/adopt-obsidian.py cli --dir)"`
  (a worktree is not the checkout the plugin was installed for) and `"CLAUDE_OBSIDIAN_SESSION_CONTEXT": "1"` in its
  settings `env`, so it starts with `wiki/hot.md`.
- A plugin every role loads on this machine: a role under `--setting-sources local` loads no plugin the user settings
  enable, so the plugin's directory goes into `plugin_dirs` of `~/.claude/specagent-launch.json` (the machine's file,
  outside every run); the watcher adds `--plugin-dir <dir>` to every launch and resume, and a path that holds no
  `.claude-plugin/plugin.json` is a config error at its start.
- The same file's `env` (variable names to strings) is what every role's process needs from this machine (a role gets
  no variable of the user settings): the watcher adds each name to every agent's settings file `env` at its start,
  before it hashes the control files, and keeps a name the file sets itself.
- Plugin state one role must not read from another (a blind type, the quarantine reader): the same file's `agent_dirs`
  (`ops/bootstrap.py` copies it from `agent_env_dirs` of `docs/roles/need-to-know.yaml`) gives every agent a directory of
  its own per variable, `<run-dir>/_plugin-data/<agent>/<VAR>`, seeded with the files it names, sets the variable in the
  agent's settings `env`, and closes every other agent's `_plugin-data` directory to it (Read, Edit and Write rules;
  the sandbox's denyRead and denyWrite when the file has a sandbox block);
  so every agent has a settings file of its own.
- Messages are best-effort: a session in another permission mode holds them, and they can expire. Every hand-off must
  also be in a file the recipient reads before each task; a message only wakes it sooner.
- A role that edits a checkout served by a local dev server or containers needs `"worktree": {"bgIsolation": "none"}` and
  `"sandbox": {"enabled": false}` (the one exception to the sandbox of every role, `example/README.md`), works on the
  current branch and may not switch branches.
- The verifier gets its own detached worktree (`git -c core.hooksPath=/dev/null worktree add --detach <dir> <sha>`, launched from there) and its
  own local dev server or containers, under another project name. It rebuilds from scratch only at milestones
  and applies other commits the way a deploy would.
- Every git command the main session runs on a role's commit before that commit is merged into the trunk, or inside
  a role's worktree, starts `git -c core.hooksPath=/dev/null`: the verifier's tree above, a merge of one builder's
  branch into the other's (a into b, b into a), a checkout of a role's sha. A hook in `.githooks/` runs scripts of
  the tree it checks out, so without the flag a role's unmerged code runs outside every role's sandbox. The trunk's
  own commits keep their hooks (`scripts/judge_after_verify.sh` makes the judge's tree from the trunk's HEAD): the
  merge into the trunk is where a role's code becomes the project's.
