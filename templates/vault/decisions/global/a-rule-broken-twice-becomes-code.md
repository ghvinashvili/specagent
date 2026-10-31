---
title: A rule broken a second time becomes a check in code
type: decision
scope: global
kind: lesson
template: yes
status: verified
updated: 2026-10-31
audience: [all]
sources: [context/measurements/2026-10-31-consolidation.md]
decided: 2026-10-31
by: owner
proof: [context/measurements/2026-10-31-consolidation.md]
why: the consolidation run's verifier wrote a final line the watcher did not read and was relaunched three times, and a question to the main session waited three hours; both rules were written and read, and held only when a check held them
decision_status: decided
would_change_if: a run where a check in code costs more than the rule it holds
---
# A rule broken twice becomes a check in code

**Rule.** The lessons loop has three steps. A finding is recorded where it was made. A cause shared by two or more
findings becomes a rule (`lessons.md` in the run; `example/lessons.md`, `first-pass-rules.md` and
`references/common-mistakes.md` in the template). A rule broken a second time becomes a check in code: a hook, a script
run by the watcher or the records monitor, a `check_formats.py` or `harness validate` rule, a test, so that holding it
no longer depends on a session reading it.

**Why.** A text rule works only when the session reads it; a check holds every time. The template's own checks came
this way (the record guards, `check_blind`, the watcher's copies and revive, the request-line pairing) without the step
being written down.

**How to apply.**
- The main session records the third step in the template's lessons loop (SKILL.md "Briefs", the `example/lessons.md`
  head) in the run after consolidation that also writes the spec-writer rule (spec 005).
- Until then the manager applies it by hand and logs it in the run's `lessons.md`.
