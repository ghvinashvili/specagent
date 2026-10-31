---
title: Any plugin, skill, MCP server or tool must fit the agentic flow; a better one may replace a part, unchanged and pinned first
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [main, planner]
sources: []
decided: 2026-10-03
by: owner
review: 2027-10-31
why: the owner keeps a long list of candidate repositories and may need any of them; no road is closed now
decision_status: decided
would_change_if: never
---
# Extensions: no path closed

**Rule.** The flow stays compatible with every kind of extension (plugins, skills, MCP servers, tools, other agents)
without them breaking the structure: keep the fixed contract small and explicit; never design a part so that an
extension form has no entry. A replacement is decided by comparison on the same cases, not by reading. Rules in the
template's `docs/roles/EXTENSIONS.md`.

**Why.** The owner keeps a long list of candidate repositories and may need any of them, so no road is closed now.

**How to apply.**
- *Own form first.* An extension's own form, used unchanged and pinned, is the first candidate; a rewrite ("borrow")
  needs a written reason or a trial result.
- *One chosen tool per job.* Asked for the best of something, give and install exactly one, chosen and justified in a
  sentence, and remove an earlier attempt that does not fit.
- Tell tools apart by when they act (guard rails while code is written against a scanner that reports afterwards), not
  by name. A tool added as a complement reads as clutter; a second tool, if ever needed, is a separate decision raised
  then.

Related: [[template-standing-requirements]].
