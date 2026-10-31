---
title: A request is answered below it, in the requester's file
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: a role waits on its own file, so the answer lands there in one form a script can find, with its time at a fixed place
would_change_if: a run in which a role missed an answer written in this form, or two open requests of one kind were closed in the wrong order
decision_status: decided
scope: global
tags:
  - decision
---
# A request is answered below it, in the requester's file

A request line is answered in the requester's own file, below it, by one line: `SUPPLIED:` for a `SANDBOX:` request,
`COPIED:` for `COPY-REQUEST:`, `CHECKED-OUT:` for `CHECKOUT-REQUEST:`, `FF-DONE:` for `FF-REQUEST:`, or
`REFUSED: <KIND> — <why>`, each ending with its `date -u` time; an answer closes the oldest open request of its kind
(`check_formats.py`'s `REQUEST_KINDS`; manager spec 5.4 and 8.3.3, acceptance check 10.7). The template-core run
answered a `COPY-REQUEST:` with `COPIED:` in the requester's file (its `build-log-b.md:22` and `:24`), with the time
inside the text rather than at a fixed place, so no script could read it; `monitor_records.py answer` now writes the
line.

## Record and source
- [The record monitor](../../.claude/skills/running-specagent-pipelines/scripts/docs/monitor_records.md)
- [The format checks](../../.claude/skills/running-specagent-pipelines/scripts/docs/check_formats.md)
- [The record monitor answers no request](monitor-answers-no-request.md)
