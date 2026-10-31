---
title: Diagrams are Mermaid text
type: decision
status: draft
updated: 2026-10-29
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: the owner does not want the vendored diagram renderer in the template; a Mermaid flowchart is text in a Markdown page that GitHub and Obsidian draw, so a map needs no plugin, no Node.js and no render step
would_change_if: a map needs a layout or an interaction that Mermaid text cannot give, and the owner accepts a renderer for it
decision_status: decided
scope: global
tags:
  - decision
---
# Diagrams are Mermaid text

The template carries no diagram renderer. On 2026-10-29 (17:3x UTC) the owner asked for the vendored one to leave the
template; its plugin, its reference material under `context/`, `harness map --render` and the doctor's Node.js item
went with it (`CHANGELOG.md`, [Unreleased], where "Removed" quotes the owner).

`harness map` writes one Mermaid `flowchart` per stage table to `docs/generated/maps/<name>.md`
(`packages/harness/src/harness/stagemap.py`, `flowchart` and `render_map`):

- a box per stage, in the order of the table: its id, its role type and its tags (per task, one call, blind reviewer);
- a diamond after each stage a human approves; the stages that wait for that stage start from the diamond;
- a dashed arrow labelled `revise` from a reviewer to the stage its verdict returns the work to;
- a double box per place a route label leads to: a pipeline, or `escalate`, which asks the human.

Node ids are positional (`s1`, `h3`, `r2`), so a stage id that is a Mermaid word such as `end`, or one that holds
`--`, cannot break a chart; a quote or a bar in a label becomes an entity code. `harness map --check` and
`harness docs-check` report a map that no longer matches its table, and `harness map` removes the files of the earlier
form (`packages/harness/tests/test_map.py`). With no renderer in the template, a diagram written by hand is a
`mermaid` block in the Markdown page it explains.
