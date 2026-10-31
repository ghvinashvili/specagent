# harness

The command line the manager session uses to run role sessions stage by stage. It builds Claude Code commands,
keeps the run's state on disk and checks every stage with a deterministic gate. Run it from the repository root:
`uv run harness <command>`. Every command prints JSON.

| Command | What it does |
| --- | --- |
| `run --slug <s> --brief <file> [--pipeline <name>]` | create a run directory beside the repository from a confirmed brief |
| `assign --run <id> --stage <stage> [--file <path>]` | store the stage's assignment: what the manager would write into the prompt of a subagent for the job (`templates/stage-assignment.md`; default source `<run>/assignments/drafts/<stage>.md`); a text without `Deliver`, `Prove` and `Done when` is refused, and so is a listed piece that does not exist or that the type may not read |
| `launch --run <id> --stage <stage>` | start the stage's session (or one per shard) with the type's access rules; `no_assignment` when the stage has none |
| `poll --run <id>` / `poll --all-active` | read `claude agents --json`, update state, run gates, print the next actions |
| `watch --run <id>` | poll until an action needs the manager |
| `resume --run <id> --stage <stage> [--shard N] --message <text>` | continue a unit: the same session, or a copy of it, with the stage's model and flags |
| `gate --run <id> --stage <stage> [--preview]` | run the stage's gate, write `gate.json`, record the verdict for a unit that is not running; `--preview` prints the checks that would fail now and records nothing (the stop hook of a role session asks it) |
| `approve --run <id> --stage <stage> --decision approved` | record the human's approval of a stage |
| `integrate --run <id> [--clean]` | after the last approval: the branch `run/<run-id>` with everything the run committed; `--clean` removes the run's checkouts and its sessions from the session list |
| `doctor` | what this machine needs before a role session can run |
| `validate` | check the repository's configuration: schemas, stage tables, access table, extensions |
| `plan-lint` | every plan folder under `docs/exec-plans/active/`: each task its `00-index.md` names exists, starts with `# Task N` and has at most 1,500 lines; no task file outside the order; each `task-NN.code.md` has its task file and defines once every `Block <id>` its steps name, and no other (also inside `docs-check`) |
| `catalog` | regenerate `docs/generated/role-types.md` from `.claude/agents/` |
| `map [--check]` | write `docs/generated/maps/<name>.md`, one Mermaid flowchart per stage table; `--check` lists stale or missing maps and writes nothing |
| `pack --type <type>` / `pack --check` | print a role type's knowledge pack, or every pack against the budget |
| `extensions [--inspect <dir>]` | compare plugins and MCP servers with `docs/roles/extensions.yaml`; list what a plugin brings |
| `material --run <id> --stage <stage>` | the pieces a stage's session gets in its cached system prompt, each with why (input, brief, assignment, cited, named, related), what did not fit, and the size; no model |
| `cache-report --run <id>` or `<transcript.jsonl>...` | prompt cache hit ratio, misses and their likely cause; sessions that ran on a model outside the policy |
| `steps --run <id>` / `steps --run-dir <path> [--repo <path>]` | the checks of `specs/001-chat-depth` on a finished run, unit by unit: the rule of every step of the unit's type against its last session's transcript, every `path:line`, every evidence command, the content checks of judge, researcher and synthesizer; one row per check; writes nothing, asks no model |
| `eval --suite regression [--case <name>] [--baseline] [--no-sessions]` | run eval cases in clean copies and grade them; `--no-sessions`: only the cases with `session: false`, graded by code without a model |
| `pipeline-report RUN_DIR [--baseline FILE] [--as-baseline FILE --label TEXT] [--prefix NAME]` | a pipeline run's findings per task by role and severity and their rounds, from its record files, against `evals/baseline/pipeline/earlier-run.json` or `--baseline`, written under `evals/results/<stamp>/`; `--as-baseline` writes the run's summary as a baseline instead; `--prefix` adds each role's usage from the transcripts (it runs `claude agents`: the main session's, never a role's) |
| `audit`, `skill-usage`, `version-check`, `wiki-lint`, `docs-check`, `limits`, `loop ...`, `inbox`, `route` | see `--help` |

Layout: `src/harness/` (one module per command group, `gates/` one module per stage), `tests/` (no Claude needed).
Tests: `uv run pytest -q packages/harness`.
