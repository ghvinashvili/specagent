---
title: The ADRs and the decision pages stay two stores
type: decision
status: draft
updated: 2026-10-31
created: 2026-10-31
audience: [all]
decided: 2026-10-30
by: owner
why: moving the numbered ADRs into the vault would cost an ingest a page (about $1 by the owner's estimate) and a new citation in every file that names one, for nothing a reader gains
would_change_if: an ingest costs next to nothing, or the template stops citing its records by number
decision_status: decided
scope: project
tags:
  - decision
---
# The ADRs and the decision pages stay two stores

The template keeps its decisions in two places and they stay two. `docs/decisions/` holds the numbered ADRs (29 on 2026-10-31,
besides `adr-template.md` and the index `README.md`), cited as ADR-00nn in about 120 tracked files (code, tests, documents, plans);
each has one line in `docs/decisions/README.md`, which `docs/llms.txt` links. `wiki/decisions/` holds the decision pages of the
project, each with a `.summary.md` beside it and, once `ops/obsidian-ingest.py` has recorded it, a source under `.raw/` and entries
in the vault's ledgers. Moving the ADRs into the vault would mean an ingest a page (the owner's estimate: about $1) and a new
citation in every file that names one, for nothing a reader gains. One paragraph in `docs/decisions/README.md` and one sentence in
`wiki/index.md` say which store holds what and link each other's index; no ADR file, number or text changes.

## Record and source
- [Spec 004 consolidation, item S5](../../specs/004-consolidation/spec.md)
- [Decision records](../../docs/decisions/README.md): the index, with the paragraph that explains the split
- [Decisions are written with the work](decisions-are-written-with-the-work.md): a code task's commit carries its page under `wiki/` or `docs/decisions/` (ADR-0027)
- [The checkout is a claude-obsidian vault](the-checkout-is-a-claude-obsidian-vault.md): a wiki page is a source of the vault, recorded by an ingest
