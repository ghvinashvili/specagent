# Memory map of the harness

Four memory types, after CoALA (working memory for the current decision cycle; long-term memory split into procedural, semantic and episodic), and where each one lives here. Every store is listed once and is an existing file or directory of this repository or of the runs root; there is no second "memory" location for the same thing.

| Type | What it holds here | Store | Who writes | When it is read | Never written there |
| --- | --- | --- | --- | --- | --- |
| Working | the current run: `state.json`; per unit `prompt.md`, `progress.md`, `tasks.json`, `result.json`, `output/` | `<runs root>/<run-id>/` (layout: `docs/roles/RUNS.md`) | `harness` (manifest, state, prompts, locks); the role session (progress, result, output); never a hand edit | at session start and after compaction (the SessionStart hook injects the pointers), at every checkpoint and resume; `harness poll` reads the state | instructions, credentials, another unit's files, notes meant for a later run |
| Episodic | what happened: every past run (results, gate verdicts, escalations with their answers, `HANDOFF.md`, `logs/`), eval results, completed plans | `<runs root>/<run-id>/` (kept; the harness prunes nothing), `evals/results/<timestamp>/`, `docs/exec-plans/done/` | `harness` and the sessions of that run; the eval runner; humans (plans) | by humans and the manager (`HANDOFF.md`, `harness escalations`); by graders; never by a role session of another run (`CLAUDE.md`: never read other runs) | conclusions rewritten from memory (the manager points at files); edits after the run |
| Semantic | facts about the code and the domain: architecture, design and quality docs, references, specs, decisions, the knowledge graph, source material | `docs/` (index `docs/llms.txt`), `specs/`, `docs/decisions/`, `graphify-out/`, `context/`, `wiki/` (compiled from `context/`; `knowledge.md`) | humans through pull requests; the doc-gardening workflow (fix-up pull requests); graphify (generated); the librarian (wiki pages, through pull requests) | on demand: `docs/llms.txt`, `graphify query`, `.claude/rules/*.md` with `paths`; the reader stage reads `context/` in full | run state; anything a session learned that no pull request verified; secrets |
| Procedural | how to act: default instructions, contracts, the stage table, skills, rules, hooks and settings, plugins, the managed policy file | `.claude/agents/<type>.md`, `docs/roles/types/<type>.md`, `docs/roles/stages.yaml`, `.claude/skills/`, `.claude/rules/`, `.claude/hooks/` with `.claude/settings.json`, `plugins/`, `/etc/claude-code/CLAUDE.md` | humans through pull requests, checked by `evals/regression`; never a session during a run (frozen fingerprint, ConfigChange hook) | at session start (`--agent` system prompt, CLAUDE.md, rules) and on demand (skills) | facts about a run; learnings written by a session: writing to procedural memory "can easily introduce bugs or allow an agent to subvert its designers' intentions" (CoALA, section 4.2) |

## Two stores Claude writes itself
- Manager auto memory: `<CLAUDE_CONFIG_DIR>/projects/<project>/memory/` (`MEMORY.md` index plus topic files with `type` `user`, `feedback`, `project` or `reference`; machine-local; one directory for every worktree of the repository; not removed by `cleanupPeriodDays`). Semantic and episodic notes about the human and this project. Only the manager keeps it: the launcher sets `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` for every role session and every eval trial. The human audits it with `/memory`.
- Manager agent memory: `.claude/agent-memory/manager/MEMORY.md` plus topic files (`memory: project`; committed and reviewed in pull requests). Semantic notes about running this harness: patterns of runs, recurring escalations. Its first 200 lines or 25 KB enter the manager's system prompt at session start.

## What a role session remembers across runs
Nothing by itself. A role type has no `memory` field and runs without auto memory (`docs/roles/MANAGER.md`, section 11, gives the four reasons). What a role learns goes into its `result.json` (`summary`, `open_questions`) and its report; a human turns a recurring finding into a rule, a skill, a contract line or an eval case in a pull request. That is the learning loop of this repository: episodic to procedural, through review, never through a session's own writes.

## Working memory across interruptions
The memory tool's multisession pattern (an initializer session writes a progress log, a feature checklist and an init script; later sessions read them first and update them at the end; a feature counts as complete only after end-to-end verification) is what `harness run` (initializer), `progress.md` (progress log, rewritten at every checkpoint), `tasks.json` with `passes` (feature checklist; a task passes only after its steps and tests) and the SessionStart hook (reads them first, also after compaction) implement. "Assume interruption" is the rule of the checkpoint skill.

A compaction is the other interruption, and it cuts the manager's or a human's conversation without ending it. Before
Claude Code compacts such a conversation, `.claude/hooks/handoff.py` asks the session to write a handoff into
`docs/handoff/` and once more to bring it up to date, and after the compaction asks the session to read the newest
handoff (`docs/decisions/0007-a-conversation-hands-itself-off-before-compaction.md`). The folder is not committed and
is closed to role sessions; a role session's handoff is its `progress.md`.

No store keeps a copy of the conversation. A handoff keeps its main points (what the person wants, what was agreed,
what is still open) beside the state of the work, so that the conversation goes on after a compaction; a checkpoint
and a memory entry hold the state of the work, the rules and the references the next session uses. Whatever is kept
is read again, and a transcript in a context crowds out the documents, instructions and sources the work needs.

## The instruction cache and memory
A file loaded into the system prompt is part of the cached prefix, and every change to it changes the prefix. Three rules follow: no role session loads a memory file into its prompt, so the role prefix is byte-identical across runs and projects; the files that do form the role prefix (agent file, rules, skills, hooks, settings, plugins) are frozen for the run by `state.config_fingerprint`; the manager's `MEMORY.md` changes the manager's own prefix at its next session start only, the cost of an interactive session, and touches no role session.
