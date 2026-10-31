---
title: Plan the whole thing first, from researched sources, in one plan document
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [all]
sources: []
decided: 2026-09-11
by: owner
review: 2027-10-31
why: rushing into edits produced garbage, answers from memory were poor, and a big build started before the deciding constraint was named
decision_status: decided
would_change_if: never
---
# Plan whole, research first, one document

**Rule.** Before code or a long build, work out the whole design and show it; keep one complete, current plan document and one dated document per research question; check current primary sources first; name the constraint that decides whether the task is possible before any big install.

**Why.** Rushing into edits produced garbage, answers from memory were poor, and a big build was started before its deciding constraint was named. A plan scattered over files beside a stale one brings the same problems again.

**How to apply.**
- *Design before code:* show the whole design first (what stays fixed, what moves, what each block holds and why, the container before the decoration); engine work gets its complete plan into the plan document first (what stays untouched, where each new piece sits in the existing seams, generic and dynamic, nothing wired in by hand), not options or permission at each step.
- *One plan, one file per analysis:* a superseded plan is trimmed or archived, and said so; each research question is its own date-prefixed document, never a section of another report.
- *Researched and complete:* *modern* or *this year's standard* means current primary sources, the owner's tooling and small files included (`.gitignore`, `settings.json`, `.mcp.json`, hooks, frontmatter); growing an answer after each complaint is the same failure as coding without a design. A named method is built only from a written list of its rules with a source per rule; where sources disagree or are silent, say so and show the options; memory is where the search starts, not a specification.
- *The blocker first:* state the deciding constraint in one or two sentences and let the owner decide; give what each route costs and gives, then wait.
- *One idea at a time:* judge it on its own terms; no comparing or combining unless asked; each keeps its own code, documents and frozen versions.
- *A running plan keeps its shape:* no renumbering, no new numbered tasks, each answer goes into its task. The plan of a new run is ordered part files with an index (`task-NN.md`), the task count fixed when the task order is written; a task's extra goes to its own part file or the Deferred list with the reason.

Related: [[decisions-are-the-owners-technical-choices-are-mine]], [[designs-come-from-the-code-read]],
[[do-what-was-asked-then-the-root-cause]].
