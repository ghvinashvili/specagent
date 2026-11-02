---
title: Every improvement is measured by its real effect, not assumed to work
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-11-02
review: 2027-11-02
audience: [all]
sources: []
decided: 2026-11-02
by: owner
why: lessons, vault pages and template rules were added run after run, but only the manager's own lessons had a recurrence count; no one knew whether an agent lesson or a vault page lowered the errors it was written for
decision_status: decided
would_change_if: the owner's word
---
# Measure the effect of every improvement

**Rule.** Every improvement to how the work is done (a lesson, a vault page, a template rule, a hook, a role or model
change, a cache or pipeline setting) is measured by its real effect, so the owner knows what it gave. Concretely:

- A lesson names the cause it targets. A finding names the lesson it breaks (a `Lesson:` field beside `Checklist:`),
  so recurrences are counted by a script, never by hand.
- Per lesson, a report shows when it was added, the findings of its cause per unit before and after, and its
  recurrences after; a lesson broken a second time is flagged to become a check in code
  ([[a-rule-broken-twice-becomes-code]]).
- The vault's effect is measured: which pages each session read (from its transcript), and whether findings of the
  causes those pages cover fall where they were read.
- A lesson counts from the moment a session actually holds it, not from the time it was written: the lane pack in the
  system prompt is frozen for a run, so a lesson added mid-run reaches a role when a new session of it starts and reads
  the dated lessons (or by an order it acknowledged), and enters the pack at the next run. The report splits findings
  by whether the session that made them held the lesson.
- The effect is followed across runs: a lesson carried into the template or the vault is checked in the next runs.
- Every number goes on the run's measurement page under `context/measurements/` with the command that produced it,
  and into the owner's summary; a claimed gain without a number is reported as unmeasured.

**How to apply.** The manager runs the template's measurement scripts at each run's end and before any claim that a
change helped; a gap in what can be measured goes to the template keeper as a fix, not as a note.
