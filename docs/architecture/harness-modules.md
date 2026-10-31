# Harness module map

One row per module of `packages/harness/src/harness/`; how the modules work together: [Harness architecture](harness.md).

| Module | Owns |
| --- | --- |
| `cli.py` | the argument parser; one branch per command, each prints the dict its function returns as JSON |
| `state.py` | every read and write of the run directory, schema validation, run creation, the config fingerprint, the session environment |
| `access.py` | the access table: inputs a stage may receive, the `input/` copies, deny rules, sandbox block, skills and plugins of a type |
| `pack.py` | role rules, the knowledge pack of a type, and the material section of a stage: the order of claim, the budgets, every line after its number |
| `pieces.py` | the material chosen by script: files cut at their seams, the places a stage's texts cite, the files they name, the pieces that match its brief (`harness material`) |
| `launch.py` | the assignment of a stage (`assign`, what makes a text one), prompt, flags, the first start of a unit, shards, print runs |
| `resume.py` | every later attempt of a unit |
| `poll.py` | reconciling `claude agents --json` with state.json; the next actions |
| `rounds.py` | the loops inside a run: a reviewer's `revise` taken once as a round, the findings sent back, the stages after it checked again, the bounds and the stops |
| `work.py` | the work commit, checkouts for stages that receive committed work, `integrate`, cleaning checkouts |
| `gates/` | one module per stage; `_common.py` holds the shared checks; a gate reads files and runs fixed commands; `preview` is the same checks for the stop hook, without recording; the checks of part 3 of `specs/001-chat-depth` (`path:line`, evidence, a module's `content_checks`) and the step rules, advisory in `warn`, deciding in `enforce` |
| `gates/steps.py` | the rule of every step, `<!-- check: ... -->`, checked against the transcript and the stage's files; `harness validate`'s rule check |
| `transcript.py` | the one reader of a session's transcript: its Read, Bash, Edit and Write calls, its model and effort |
| `catalog.py` | role-type catalog, `validate` (which refuses a spec-writer type that returns a data model, interfaces or tests), `docs-check` (the layered index, links outside code, index sizes, summary and spec-size warnings; a generated file is compared with what its source produces now) |
| `plans.py` | `plan-lint`: a plan folder's task files against the task order of its `00-index.md`, and each task's `task-NN.code.md` against the blocks its steps name (also run by `docs-check`) |
| `stagemap.py` | `harness map`: the Mermaid flowchart of every stage table (the stages in order, their role types, the human approvals, the returns and the routes) and its comparison with the committed page for `docs-check` |
| `extensions.py` | plugins and MCP servers against `docs/roles/extensions.yaml` |
| `doctor.py` | what the machine needs before a session can run |
| `trust.py` | the trust record `claude --bg` needs, written by launch and resume before a role session starts |
| `cache_report.py` | prompt-cache numbers per session; sessions outside the model policy |
| `limits.py`, `notify.py`, `loops.py`, `intake.py`, `select.py`, `wiki.py`, `audit.py`, `evals.py`, `otel.py`, `mcp_state.py` | usage limits, notifications, loops, untrusted input, type selection, wiki lint, audits, evals, traces, the read-only state server |
| `pipeline_report.py` | a run's findings by role and severity and their rounds, from the record files, against a baseline; with `--prefix`, each role's usage |
