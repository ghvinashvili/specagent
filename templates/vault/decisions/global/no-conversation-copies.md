---
title: No copies of conversations anywhere; a hand-off keeps the main points; hand-off files reach subagents
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [all]
sources: []
decided: 2026-10-02
by: owner
review: 2027-10-31
why: whatever is kept is read again later; a full copy fills the context with talk instead of material
decision_status: decided
would_change_if: never
---
# No conversation copies

**Rule.** No transcript copy is kept or cached. A hand-off keeps the main points so that work continues after compaction: what the owner wants and why, what was agreed, what is open, then the state of the work (done, in progress, problems, next steps, files). Caches hold documents, instructions, references and sources; memory holds rules, reasons in own words and references, never verbatim conversation.

**Why.** Whatever is kept is read again later, and a full copy fills the context with talk instead of material. The template's hand-off hook and the owner's user-level hook ask for the main points only. The owner's hook also fires inside subagents and sends them to the newest file in `docs/handoff/`, which spoils blind work.

**How to apply.**
- Write hand-offs as main points, never as a transcript.
- Before blind work (an audit, a comparison, a reviewer who must not know the author's conclusions), move the hand-off files to a sibling directory, leave a short neutral newest file, and say in the prompt that the directory belongs to another session.
- Subagents reuse the main session's scratchpad path: move everything except shared tools out of it to a directory no prompt names.
- Restore both afterwards.

Related: [[keep-context-small]].
