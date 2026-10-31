---
title: Verify it yourself before saying it works - reproduce, operate every control, look at it, prove it fires on real data
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [all]
sources: []
decided: 2026-09-12
by: owner
review: 2027-10-31
why: the owner kept finding what the session's checks missed - dead mechanisms behind passing tests (2026-09-12), controls broken next to a fix and an animation shipped on numbers (2026-09-21)
decision_status: decided
would_change_if: never
---
# Verify it yourself before saying it is done

**Rule.** Say `done` or `it works` only after using the result the way the owner will.

**Why.** The owner kept finding what the session's own checks missed: engine mechanisms that never fired behind passing tests (2026-09-12), controls broken next to a fix and an animation reported done on measurements alone (2026-09-21), and, in knowledge work, vault pages and run briefs used unchecked, one with a false fact found within minutes of launch (2026-10-28). A diagnosis that rests on the owner repeating the failing action wastes their time the same way; they said they could not keep doing it (2026-09-22).

**How to apply.**
- Reproduce a failure yourself by driving the real path; one request to the owner may be reasonable, a second is too many. Asked whether it is fixed, answer that in the first sentence.
- Operate every control of a changed surface in a real browser before the next change and before reporting: click or drag each one, neighbours included, and check that the setting changed, that the control's own look followed and that nothing threw. Passing unit tests and a clean console are not evidence that a surface works.
- Judge visual and motion work by how it looks: study the rendered result (frame by frame for motion, the whole block for layout) before publishing; a screenshot not studied is worthless. Controls of one action sit together.
- A unit is tested only when something fails if its mechanism never fires on a real sample, since a test that builds its own input proves only that a path can run. Beside `all tests pass`, report how often each named branch fired on real data, and report a zero as a defect before the owner asks.
- Knowledge work is verified like code: a vault page, a design document, a run brief or a lesson is checked against its sources by a session other than its writer. The main session's practice since 2026-10-29: a vault compile ends with a critic session over the new pages, and a run's briefs are read by the critic in its first unit.

Related: [[checks-once-each]].
