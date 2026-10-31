---
name: adr
description: Record a decision as a MADR file under docs/decisions and link it from the index. Use when the human says a decision is made.
disable-model-invocation: true
argument-hint: "[title-with-dashes]"
allowed-tools: Bash(ls docs/decisions *) Read Write Edit
---
# ADR

1. Next number: highest `NNNN` in `docs/decisions/` plus one.
2. Copy `docs/decisions/adr-template.md` to `docs/decisions/NNNN-$0.md`; fill front matter (`status: accepted`, `date`, `decision-makers`) and every section; leave no placeholder.
3. Add the line to `docs/decisions/README.md`, after the newest record (`- [ADR-NNNN Title](NNNN-$0.md): one sentence`).
4. A superseded decision gets `status: "superseded by ADR-NNNN"`; its text is never edited.
