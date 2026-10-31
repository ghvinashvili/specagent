---
title: Manager lessons live in the vault, a section per project
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: the same management mistake never twice in any project; one page that every main session reads in its first calls
would_change_if: the page passes 8,000 bytes with live items, or three runs end with no item fired again and none added
decision_status: decided
scope: global
tags:
  - decision
---
# Manager lessons live in the vault, a section per project

The owner's rule is that the same management mistake never happens twice. On 2026-10-29 at 17:03 UTC the owner chose
answer (a) to question 3 of the manager spec, with a section per project: the manager-lessons page is the vault's
`decisions/global/manager-lessons.md`, pushed with the vault, so that the main session of every project reads the same
page in its first calls. Answer (b), a page in each project's `wiki/decisions/`, was not taken: the four mistakes that
started the page were management mistakes, not project ones, and a lesson kept in one project would not stop the same
mistake in the next.

The template ships the page's form and its check. `templates/vault/forms/manager-lessons.md` is copied once to the
vault's `decisions/global/` (`templates/vault/rules.md`, Forms): the global items under `## All projects`, one section
per project, and `## Below the fold`. An item is a line
`<n>. <trigger> -> <rule>; cost measured <cost>; <YYYY-MM-DD>, <record>`, appended the moment a mistake is found; the
same mistake again adds a date and a record to it, and an item that fired in no run for three runs moves below the
fold. `scripts/manager/measure_manager.py lessons` checks the items' form and numbers and the 8,000-byte limit, and
with `--since` lists the items added and fired again in a run.

## Record and source
- [The manager in chat](../../docs/roles/manager-chat.md)
- [The manager-lessons form](../../templates/vault/forms/manager-lessons.md)
- [The owner's vault is read on need](the-owners-vault-is-read-on-need.md)
