# Extensions

An extension is anything the flow uses that this repository did not write: a Claude Code plugin, a set of skills,
an MCP server, a command-line tool, another coding agent, a proxy in front of the API, a service. Any of them can
be brought in, and any part of the flow can be handed to one that does it better. This file says what stays fixed,
where each form enters, how an extension is compared with the repository's own part, and how it is admitted and
updated. The register is `docs/roles/extensions.yaml`; `harness extensions` checks it.

## 1. What stays fixed
These are the contract of the flow. An extension works inside them. Changing one of them is a decision about the
flow itself (an ADR and the human), never a side effect of installing something.
- Every role is a session started by `harness launch` from a stage table; one manager talks to the human.
- A stage has declared inputs, an output directory, a `result.json` by schema and a gate.
- What a role type may see is in `docs/roles/need-to-know.yaml`; reviewing types stay blind.
- A role session does not ask the human; a question is an escalation.
- The configuration is frozen while a run is active; the run directory is the only state.
- The tool set of a role type is fixed and the same in every session of the type (the prompt cache depends on it).

## 2. Forms and where each one enters

| Form | What it is | Where it enters | Switched on for |
| --- | --- | --- | --- |
| `plugin` | a Claude Code plugin: skills, hooks, agents, commands, MCP and LSP servers, monitors, executables | the internal marketplace `plugins/`, or a marketplace on the allowlist; `enabledPlugins` | the role types that name it in `plugins` (`need-to-know.yaml`); off for every other type |
| `skills` | skill directories or instruction files that are not packaged as a plugin | copied into an internal plugin under `plugins/`, with the origin and commit in its `plugin.json` | as a plugin |
| `mcp` | an MCP server: tools from an outside system | `.mcp.json` | the manager through `enabledMcpjsonServers`; a role type through `mcp_servers` in its row, passed by the launcher with `--mcp-config`; the server's tools are added to the `tools` list of the type's agent file |
| `cli` | a command-line tool the session runs through Bash | the dev container image and `permissions.allow`; the sandbox network list when it needs a host | every type that has Bash; the type's instruction or a skill says when to use it |
| `agent-cli` | another coding agent with a non-interactive mode | as `cli`; a role type whose instruction runs it and writes the stage's `result.json` from its output | one role type per use, added with the `new-role-type` skill |
| `proxy` | a gateway or router between Claude Code and the API | `env` in `.claude/settings.json` | every session; measure with `harness cache-report` before and after, because a proxy that rewrites requests or switches models changes what the prompt cache can reuse |
| `service` | a long-running server: a vector store, a workflow engine, a memory store | reached through an `mcp` or `cli` entry of its own | as that entry |

A library or framework the product itself is built with is a dependency of a package under `packages/` and is not
an extension of the flow; it is decided in the plan and recorded in an ADR like any other design choice.

## 3. What an extension may take over

| Part of the flow | The repository's own part | An extension replaces it by | Stays fixed around it |
| --- | --- | --- | --- |
| how a type does its work: planning, test-first, debugging, review method, writing style | Working method in `.claude/agents/<type>.md` | a skill, named in that section; the own text for that step is removed | the six sections, Returns, the gate |
| a whole role type | `.claude/agents/<type>.md` and its contract | an agent file of a plugin, copied into `.claude/agents/` with the `new-role-type` skill (a plugin's own agents ignore `hooks`, `mcpServers` and `permissionMode`) | the stage table row, the contract, the access row |
| the order of work for a class of projects | a pipeline in `docs/roles/pipelines/` | the extension's workflow written as a pipeline: its agents become role types, its steps become stages | sessions instead of subagents, a gate after every stage |
| conventions: commit style, documentation gardening | `.claude/skills/commit-style`, `.claude/skills/doc-gardening`, commitizen | another plugin's skill or hook | the checks in CI |
| deterministic checks on edit and on stop | `.claude/hooks/` | hooks of a plugin; they run beside the repository's hooks | the repository's hooks keep running |
| language intelligence | one LSP plugin per language | another LSP plugin | nothing |
| knowledge: retrieval, memory, code graph | `wiki/`, the knowledge pack, `graphify-out/` | a tool or server that builds or searches an index | a fact carries its source; the pack stays the delivery to a role session |
| a second opinion from another model | none | an `agent-cli` role type in a reviewing stage | blind access, the verdict schema |
| checks in CI: review of a pull request, security scan | `.github/workflows/` | the extension run in a workflow | CI is outside a run |

What is not handed over inside the flow: starting sessions and agents, the stage tables, the gates, the access
rules. An extension that brings its own orchestration is not switched on inside role sessions. It is either
written as a pipeline (row three), or the whole flow is compared with it on the same project (section 4).

## 4. Comparing an extension with the repository's own part
Reading two texts does not decide which is better. The comparison is a trial on the same cases.
1. Name the part and the candidate in an ADR draft in `docs/decisions/`.
2. `uv run harness extensions --inspect <directory>` lists what a plugin brings. Read its hooks, scripts and MCP
   servers. What touches section 1 is written into the ADR now.
3. On a branch: admit the extension (section 5) and switch the one part to it for the one role type concerned.
4. Run the same eval cases on the base and on the branch, with the same number of trials: `uv run harness eval`.
   If no case exercises the part, write the case first; a case both variants can fail.
5. Compare the pass rate per case, the transcripts of the failed trials, tokens and time
   (`uv run harness cache-report`), and what is loaded at session start (`uv run harness audit`).
6. Record one of three results in the ADR:
   - `adopt`: the part moves to the extension, and the repository's own text or code for it is deleted, so that one
     source remains;
   - `keep`: the own part stays; the ADR says what the trial showed;
   - `borrow`: the extension is not switched on; the ideas taken from it are written into the own part, with the
     extension and its version named beside them.
The human approves the pull request. The same trial is repeated when either side changes materially.

## 5. Admission
1. Source. A plugin comes from the internal marketplace or from a marketplace on the `strictKnownMarketplaces`
   list. A plugin from any other repository enters through the internal marketplace: an entry in
   `plugins/.claude-plugin/marketplace.json` with a git source pinned to a commit (`sha`).
2. Part of a plugin. A plugin's hooks cannot be switched off one by one. When only some of its skills are wanted,
   the plugin is not enabled; the wanted skill directories go into an internal plugin, with the licence file and
   the origin recorded, and are updated by a pull request that names the new commit.
3. `docs/roles/extensions.yaml`: form, source, pinned version, what it serves; for a plugin, what it brings.
4. `docs/roles/need-to-know.yaml`: `project_plugins` and the `plugins` or `mcp_servers` of the types that use it.
5. A role session loads project and local settings only (`--setting-sources project,local`), so a plugin a
   developer installed for themselves never reaches a role session. The manager is the human's own session and
   keeps the user's plugins; an extension that talks with the human (requirements, design review) belongs there.

## 6. Update
A new version is a pull request: the version in `extensions.yaml`, the output of `uv run harness extensions`
(what it brings now that nobody accepted), the regression evals. `harness validate` fails while the installed
version or components differ from the accepted ones, so an automatic update on one machine is seen at once. Runs
in flight keep the configuration they started with.

## 7. What `harness extensions` reports about a plugin in a role session
- agents: cannot be started (the `Agent` tool is denied); see row two of section 3;
- commands: are typed by a person; a role session has nobody to type them; skills are invoked by the model;
- MCP servers and channels: not loaded unless the type's row names the server;
- monitors: do not start in a print stage; in a background stage their output reaches the model for the whole session;
- a default main agent in the plugin's settings: the launcher's `--agent` overrides it;
- hooks: all of them run in every session of a type that keeps the plugin, from the first moment.
