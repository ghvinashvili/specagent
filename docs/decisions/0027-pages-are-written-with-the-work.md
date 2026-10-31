---
status: accepted
date: 2026-10-28
decision-makers: the owner, in the spec of the template-core run (items A1 and A2)
consulted: the template-core run's planner, critic and plan fixer
informed: every project created from this template
---

# Pages are written with the work

## Context and Problem Statement

The wiki had one writer: the librarian, compiling `context/` at night. What a builder learns while it changes code
(why the code is so, how to run it, what was decided) reached the wiki late or never. `mark_verified` accepted only a
wiki run's check stage, so a page written with code never became `verified` and never reached a knowledge pack, and
the page schema had no type for a decision. How does knowledge reach the wiki when it is known, held by code rather
than by a reviewer's memory?

## Decision Drivers

* Knowledge is written when it is known: in the commit that changes the code.
* A check by code, not by review: the gate that holds a writer to its tests holds it to its pages.
* One decision per page, and a changed decision is a new page (the owner's rules for the vault).
* An honest task without pages is not blocked: a stated reason is enough.

## Considered Options

* The librarian alone, nightly, from `context/`, as before
* Pages with the work, held by the write gate, with `docs: none — <reason>` as the stated exception
* The rule in `.claude/rules/wiki.md` without a gate

## Decision Outcome

Chosen option: "Pages with the work, held by the write gate, with `docs: none — <reason>` as the stated exception",
because it is the only option that writes knowledge when it is known and checks it without a model.

* A page is a `.md` file under `wiki/`, `docs/runbooks/` or `docs/decisions/` that is no `index.md`, `log.md`,
  `README.md` or `.<language>.md` summary. Code is a path outside `docs/`, `wiki/` and `context/` that is no `.md` file, so
  tests, configuration, schemas, scripts and CI files are code; an instruction file or a plan task file is neither.
* The write gate's check "the code comes with its pages, or every task says docs: none with a reason" fails a branch
  that changes code and touches no page, unless the planner gave every task of the shard `"docs": "none — <reason>"`
  in its `tasks.json` (`schemas/tasks.schema.json`). The gate reads the planner's list, which no writer writes; a
  `docs` in the writer's copy counts for nothing.
* A builder writes its pages as `draft`. `harness integrate` marks them `verified` when every verdict of the run is
  `accept`, and only a `verified` page reaches a knowledge pack.
* A decision page lives in `wiki/decisions/` with `type: decision` and the fields `decided`, `by`, `why`,
  `would_change_if`, `decision_status` and `scope` (`review` when it is doubtful); a revised page names the page that
  revises it in `revised_by`, which `harness wiki-lint` resolves.

### Consequences

* Good, because the commit carries its reasons, and decisions are found in the vault and, once verified, in knowledge
  packs.
* Good, because a task without pages says why in its plan, where the critic reads it.
* Bad, because a code task needs a page or a reason, the write gate has one more check, and every page needs a line in
  its index.

### Confirmation

`packages/harness/tests/test_write_docs_gate.py`, `packages/harness/tests/test_wiki_decisions.py` and
`packages/harness/tests/test_mark_verified_pages.py`; `uv run harness wiki-lint` on the repository.

## Pros and Cons of the Options

### The librarian alone, nightly, from `context/`, as before

* Good, because nothing changes for a builder.
* Bad, because what a builder knows reaches the wiki late or never, and a page written with code never becomes
  `verified`.

### Pages with the work, held by the write gate, with `docs: none — <reason>` as the stated exception

* Good, because the knowledge is written when it is known, and the gate checks it without a model.
* Bad, because the gate judges paths only: it sees that a page changed, not that the page is right; the verifier and
  the critic judge that.

### The rule in `.claude/rules/wiki.md` without a gate

* Good, because it costs no code.
* Bad, because a rule that no check holds is skipped when a task runs late.

## More Information

* The documentation layers: [documentation](../architecture/documentation.md).
* The first decision page: `wiki/decisions/decisions-are-written-with-the-work.md`.
* Source: the owner's spec of the template-core run, in the template's development records (outside the repository since 2026-10-29), which projects do
  not receive (items A1 and A2).
* Revisit when a measured run shows that pages written with the work are wrong more often than pages the librarian
  compiles later.
* Amended on 2026-10-29 by [ADR-0030](0030-the-template-is-english-only.md): a summary is `<name>.summary.md`, in English.
