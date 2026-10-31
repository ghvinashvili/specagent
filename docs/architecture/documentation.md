# Documentation layers

The documentation is laid out so that an agent reads only what it needs: an index of one line per item, then the one
document behind the line. Each layer has its place, its writer and its readers; indexes are layered and small; a plan
is a folder of task files; a page the owner reads has a short summary beside it. `harness docs-check` and
`harness plan-lint` hold this shape by code, and a project made from the template keeps it (ADR-0026,
`docs/decisions/0026-plans-in-parts-and-layered-document-indexes.md`).

## The four layers

| Layer | Where | Written by | Read by |
| --- | --- | --- | --- |
| User guide | `docs/user-guide/`, which a project adds once it has users; its `README.md` lists the pages | the builder of a user-facing change, with the change | the project's users and the human |
| Design wiki | `wiki/`, the Obsidian vault: concepts, entities, sources, the project's decisions in `wiki/decisions/`, formulas and balance tables in concept pages | the librarian, and builders with their work | role sessions (the pages for their audience come in the knowledge pack), the owner in Obsidian |
| Technical docs and runbooks | `docs/architecture/`, `docs/quality/`, `docs/references/`, and `docs/runbooks/` on how to operate what was built | the builder who changes the code or the operation, in the same commit | agents through `docs/llms.txt`, the human who operates the system |
| Decisions | `docs/decisions/`, the ADRs written with `.claude/skills/adr`; the project's decisions as pages in `wiki/decisions/` | whoever makes the decision, with the work it decides | anyone about to change what a decision covers |

## Indexes
`docs/llms.txt` is the entry point. A document under `docs/` is listed in one of three ways:
1. `docs/llms.txt` links it.
2. `docs/llms.txt` links its folder's `README.md`, and that README links it. One level only: a README that only another
   README links lists nothing.
3. A file inside a plan folder `docs/exec-plans/active/<plan>/` or `docs/exec-plans/done/<plan>/` is listed when
   `README.md` of that state's folder, linked from `docs/llms.txt`, links `<plan>/00-index.md`.

A line lists a document only by a Markdown link, `- [Title](path): one sentence`; a path in backticks lists nothing.
Every index (`docs/llms.txt`, a folder `README.md`, an `index.md`) holds one line per item and stays at most 12,000
bytes (12 KB counted in decimal, as the owner's vault counts it); an index that grows past it is split by folder, each
folder's lines moving to its own `README.md`. The decision records are listed in `docs/decisions/README.md`.

`uv run harness docs-check` checks:
- the listing: every document under `docs/` is listed by one of the three ways (`adr-template.md` and summaries need
  no line);
- the links: every relative link outside code resolves; links inside fenced code blocks and inline code are text, as
  lychee in CI reads them;
- the sizes: `docs/llms.txt` and each `README.md` or `index.md` under `docs/` at most 12,000 bytes;
- the plan folders: plan-lint's problems are docs-check's problems;
- the summaries: a page under `wiki/decisions/` or `docs/runbooks/` without its summary is a warning, never a failure;
- the spec sizes: a `specs/*/spec.md` that is not under 8,000 bytes is a warning, never a failure (a spec is about one
  page; a longer one is a sign the brief asked for the plan);
- the generated files: `docs/generated/` matches what its sources produce now.

## Plans in parts
A plan in progress is a folder `docs/exec-plans/active/<plan>/`:
- `00-index.md`: the goal, the global constraints, the decisions, and the task order, a table under `## Task order`
  with one row `| N | … |` per task;
- `task-NN.md`, one per task, at most 1,500 lines counted at newlines, its first line `# Task N — <title>`;
- `task-NN.code.md`, optional, beside its task file: every fenced block longer than 10 lines, under a heading
  `## Block <id>` (`3b`) that its step names as `Block 3b`; no line limit.

The task count is fixed when the task order is written: a task that grows does not become new numbered tasks; its extra
goes to that task's Deferred list with the reason. `uv run harness plan-lint` checks that every task the order names
exists, starts with its own heading and is not longer, that no task file is outside the order, that no number
appears twice, and that each code file and its steps name the same blocks (the rules in
`docs/exec-plans/active/README.md`); `harness docs-check` runs it too. Each plan folder gets one line in `docs/exec-plans/active/README.md`,
linking its `00-index.md`; its task files and its summary need no line of their own. Plan-mode drafts land in
`docs/exec-plans/active/` as single files (`plansDirectory` in `.claude/settings.json`) and are not linted. A finished plan moves to `docs/exec-plans/done/<plan>/` with its line in `docs/exec-plans/done/README.md`;
plan-lint reads `active/` only.

## Summaries for the owner
A page the owner reads gets a summary `<name>.summary.md` beside it: each decision page, each runbook, and the architecture
pages written for the owner, this one included (`docs/architecture/documentation.summary.md`). A summary is a few lines,
written in English in this template (owner, 2026-10-15; named `<name>.summary.md` since 1.4.0, ADR-0030). It is
listed in no index. `harness docs-check` warns for a page under `wiki/decisions/` or `docs/runbooks/` without one.
