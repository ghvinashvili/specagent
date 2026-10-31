---
title: A design for a system comes from reading its code; without that, bring measured facts and leave the design to its owning session
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [all]
sources: []
decided: 2026-09-24
by: owner
review: 2027-10-31
why: design advice for an engine I had not read was advice in the air (2026-09-24); checked against the code, the proposed mirror did not fit
decision_status: decided
would_change_if: never
---
# Designs come from the code read

**Rule.** A design for a system is derived from that system's code: it names the code path it changes and what it
costs there, not an abstract mechanism. A system with its own owning session is designed by that session, with the
code in front of it; from another session I bring measured facts, limits and sources.

**Why.** A session that had measured a vendor's API proposed engine designs without having read the engine, and the
engine session took them in as they came; the owner called this advice in the air. Checked against the code, the
proposed mirror did not fit (every event would arrive twice under a single quote lock, and each record is journaled
before it is applied, so the journal would double), and the design was rewritten around what the engine already does.

**How to apply.**
- Before suggesting how a system should work, read the relevant code or plan section and say what I read. A
  proposal built only on the owner's last sentence is advice in the air.
- When the owner raises a concern about a system I do not own (whether data will be late, say), answer with what I
  know for certain (measured numbers) and hand the design question to the owning session.
- A suggestion from another session is input, not a decision: check it against how the system actually caches,
  journals, locks and spends per second, and say in the design why it was kept or changed.
- Only the owner's own words bind. When a session relays them, keep them apart from that session's own proposals.

Related: [[sessions-coordinate-between-themselves]], [[decisions-are-the-owners-technical-choices-are-mine]],
[[agents-are-blind]].
