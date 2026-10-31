# Context budget

What enters a session's context, what it costs and what checks it. Numbers live in `docs/quality/context-budget.yaml`;
`uv run harness audit` reports them and `harness audit --ci` fails on the limits marked `error`.

## What is loaded, and when

| Content | Loaded | Session |
| --- | --- | --- |
| `CLAUDE.md` with `@AGENTS.md`, `.claude/rules/harness.md` (no `paths`) | at start, and again from disk after a compaction | the manager, a human's session |
| role rules, then the knowledge pack: `CLAUDE.md`, `AGENTS.md`, the type's other `pack_files`, the wiki pages for its audience | at start, appended to the system prompt (`pack.md`, written once at launch) | role sessions |
| the material of the stage, after the pack, chosen by script (`harness/pieces.py`): its inputs, the pieces the brief names (for a stage that receives `context`), the pieces its assignment lists, every place its texts cite as `path:line` with its piece, the short files they name, the pieces that match the brief; every line exactly after its number, empty lines left out | at start, in the same appended text; given whole up to 2,000,000 characters (about 500,000 tokens, half of a 1,000,000-token window; 320,000 on haiku), of which the script's own choice at most 200,000 (100,000 on haiku) and the word match at most 40,000; what does not fit is named before the launch and the stage is split | every role session; a type whose agent file lists tools, none of them Write or Bash, gets its inputs, the brief's pieces when its stage receives `context`, and the pieces its assignment lists, and nothing chosen by script (ADR-0012) |
| agent file body, preloaded skills (`skills` field) | at start, as the system prompt | role sessions, manager |
| `MEMORY.md` of the agent's memory directory (`memory` field; the manager's is `.claude/agent-memory/manager/`), its first 200 lines or 25KB | at start, in the system prompt | the manager |
| rules with `paths`, package `CLAUDE.md` | when a matching file is read; not restored by a compaction until then | every session |
| skill names and descriptions | at start; the body only when the skill is used | every session |
| MCP tool names | at start; definitions are deferred until a tool is needed | manager only (roles run with `--strict-mcp-config`) |
| SessionStart hook output (`additionalContext`) | at start, on resume and after a compaction | role sessions |
| the type's instruction and the role rules again, then the brief, the stage's assignment and input paths (`prompt.md`) | first user message | role sessions |

## Rules
1. Instruction files: at most 200 lines per file (official). The word count is reported and compared with a third-party
   target; exceeding it is a warning, never a failed build.
2. Hooks guard, they do not inject: only `session-start.py` adds context, and its output stays under the 10,000-character cap
   of hook output. A `UserPromptSubmit` hook would add text to every turn; the audit reports any.
3. MCP: one always-on project server (`harness-state`), for the manager only. A new server goes into `.mcp.json` only with a
   reason in the pull request; a command-line tool is preferred where one exists.
4. Skills: a procedure lives in a skill, not in `CLAUDE.md`. Preloaded skills are counted per role type; skills nobody uses are
   found by `harness skill-usage` (`docs/quality/LEARNING.md`).
5. Cache: a resume re-sends the conversation and reads from the cache only what is unchanged and still within the cache
   lifetime (one hour on a subscription within plan usage, five minutes on usage credits or an API key). The launcher never
   changes model, effort, tools or MCP servers of a unit between launch and resume, and the Claude Code version is pinned,
   because each of those invalidates the prefix. A resume after a limit wait is a cold start by design.
6. Tool output: test output is filtered before it reaches the context (`.claude/hooks/compact-output.py`); the full output
   stays in a file whose path the session sees. Role sessions write long results to files and return paths.
7. Compaction: `progress.md` is the checkpoint that survives it; the SessionStart hook points back to it. Hook-injected
   context is lost in the summary, files are not.
8. Memory indexes: a `MEMORY.md` that agent memory loads (`.claude/agent-memory/<agent>/`,
   `.claude/agent-memory-local/<agent>/`) stays at most 5,000 bytes, one line per entry, with the detail in topic files
   read on need. Officially its first 200 lines or 25KB enter the system prompt at every start; the owner keeps memory
   indexes under 5 KB (vault `load-on-need`). `harness audit` warns above it. The manager's auto memory lives outside
   the repository; the human checks it with `/memory`.

## How to measure
- `uv run harness audit`: lines and words per instruction file, the size of every agent-memory `MEMORY.md`,
  always-loaded total, hooks that inject context, always-on MCP servers, preloaded skills per role type, description
  length per skill.
- Print stages: `usage.cache_creation` and `cache_read_input_tokens` in `stages/<stage>/logs/print.json`.
- Background stages: OpenTelemetry `claude_code.token.usage` by `type` (`input`, `output`, `cacheRead`, `cacheCreation`).
- In an interactive session: `/context`, `/usage`, `/doctor prompt-audit`, `claude plugin details <name>`.

## Schedule
- On every pull request: `harness audit --ci` (`.github/workflows/ci.yml`).
- Weekly: loop `context-audit` (`docs/loops/context-audit.yaml`); a finding becomes an issue or a change proposal.
