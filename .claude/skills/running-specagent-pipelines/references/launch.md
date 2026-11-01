# Launch
```bash
cd <repo> && claude --name <role> --add-dir <run-dir> <more dirs> --strict-mcp-config --effort max \
  --permission-mode auto --setting-sources local --autocompact 235000 --exclude-dynamic-system-prompt-sections \
  --system-prompt-snapshot on --settings "$(cat <run-dir>/_control/<role>-settings.json)" \
  --append-system-prompt-file <run-dir>/_pack-<role>.md \
  --bg "Your system prompt holds this lane's pack, your assignment included: follow it. Start now."
```
- The first launch carries the same flags as the watcher's `common` and the lane's pack (`_pack-<role>.md`, built
  before the pre-flight), so the first session of a lane starts from the same bytes as every later one.
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
- Compaction instead of a hand-over, by default (owner, 2026-11-01): `common` carries `--autocompact 235000` (the session
  compacts near 197k), `cap` is 260000 and `handoff_at` 250000, so the watcher's hand-over is a backstop only; and
  `"env": {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": ""}` in `--settings` clears the main session's 60%, which the daemon passes
  on. A compaction costs about $0.45 against $0.70-1.00 for a hand-over and the session keeps its memory (a project's run of
  2026-11-01). A hand-over stays for a model change (a
  resume keeps the old model) and for a stuck session. A role writes the facts its next step needs into its record file
  as it works, since a compaction keeps only the main points; it writes a HANDOFF note only on the watcher's order.
- A long wait: a waiter returns within 3.5 minutes and the role runs it again (about 17 calls an hour, $0.040 each
  at 150k). A role whose input may be more than about an hour away gets a `work_check` in its agent entry; it then
  writes a hand-over note for the wait and the watcher relaunches it when the check finds work (`watch_agents.py`,
  hand-over and idle). A role without one keeps waiting in its session.
- A builder's lane after its `STATUS: done`: its agent entry carries a `final_check` (`open_ids.py <run> --kind V,R
  --cause code --tasks <the lane's tasks>`), so the verifier's later (code) findings revive it instead of waiting for
  the manager (a project's run of 2026-11-01: ten hours twice).
- One frozen pack per lane in the system prompt: `_pack-<role>.md` holds `_common.md`, the role's assignment,
  `_first-pass-rules.md`, `_handoff-rule.md` and the "Read first" section of lessons.md, is built by
  `scripts/make_pack.py --no-note` before the lane's first launch, and the agent's own `extra_prompt` passes it with
  `--append-system-prompt-file`. The system prompt is rebuilt the same on every call, so the pack survives a compaction
  and every session of the lane reads it from the cache. `common` also carries
  `--exclude-dynamic-system-prompt-sections` (git status, cwd, date and memory paths go into the first message, so a
  commit or a new day does not change the prefix before the pack) and `--system-prompt-snapshot on` (the prompt is
  recorded once and sent as-is until a compaction); both are in Claude Code 2.1.316 (probe: `claude --help | grep -c
  -- '--exclude-dynamic-system-prompt-sections\|--system-prompt-snapshot'` prints 2). The critic, verifier and judge
  packs leave `_first-pass-rules.md` out, as their briefs never read it. The scope is the pipeline skill's roles;
  the harness's stage types keep their own TTL (`docs/roles/need-to-know.yaml`) until the owner says otherwise.
  The sandbox is untouched: the CLI reads the pack at the start,
  outside any tool, and the pack lies outside `_control/`, closed to every role's Edit and Write. The pack is never rebuilt during the run (a changed pack exits
  the watcher 4); a lesson added later goes into lessons.md with its date. One model per lane for the whole run.
- The cache TTL per role: `"CLAUDE_CODE_PROMPT_CACHE_TTL": "<ttl>"` in the role's settings `env` next to that override
  (Claude Code 2.1.316 reads `5m` or `1h`, and the variable wins over the `promptCacheTtl` setting; unset, a subscription
  within its limits gets 1 hour and an API key 5 minutes). A cache write at 1 hour costs more than one at 5 minutes, and
  a gap over 5 minutes makes the next call write the prefix again (`docs/economy.md`, measured 2026-10-31). Every role
  runs at 5 minutes and keeps its cache warm by calls: a waiter returns within 3.5 minutes and the role runs it again;
  a wait known to be longer than about an hour ends the session, and the watcher relaunches it on work. The 1-hour TTL
  is rejected (a project's run of 2026-11-01: $59.51 more in writes against $26.91 saved, a net $32.60 more); `example/*-settings.json` carry it:

| TTL | Roles | Why |
|---|---|---|
| `5m` | planner, builder-a, builder-b, any writer, verifier, critic, plan-fixer, judge | every role: the waiters return within 3.5 minutes, so the next call comes inside the TTL |
| `1h` | none | rejected 2026-11-01: its writes cost more than the gaps it saves |

- Only the plugins and MCP a role needs: `--strict-mcp-config` on every launch and resume; design plugins only for
  design roles (`~/.claude/design-plugins.json` merged into `--settings`).
- A role that reads or writes the wiki loads the claude-obsidian plugin: `--plugin-dir "$(python3 ops/adopt-obsidian.py cli --dir)"`
  (a worktree is not the checkout the plugin was installed for) and `"CLAUDE_OBSIDIAN_SESSION_CONTEXT": "1"` in its
  settings `env`, so it starts with `wiki/hot.md`.
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
