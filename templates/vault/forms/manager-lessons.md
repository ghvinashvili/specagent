---
title: Manager lessons
type: decision
scope: global
status: verified
updated: YYYY-MM-DD
audience: [main]
sources: [context/owner-statements/YYYY-MM-DD.md]
decided: YYYY-MM-DD
by: owner
why: the same management mistake never twice; every main session reads this page in its first calls
decision_status: decided
would_change_if: three runs in a row end with no item fired again and no item added
---
# Manager lessons

The main session's own mistakes, each turned into a rule, read by every main session in its first calls. Copy this
form once to `decisions/global/manager-lessons.md`, list it in `INDEX.md`, set the dates and `sources`, and keep one
section per project under the global one. One item per mistake, appended the moment the mistake is found:

`<n>. <trigger> -> <rule>; cost measured <cost>; <YYYY-MM-DD>, <record>`

- `<n>` is the item's number, never reused; `<trigger>` is what happened; `<rule>` is what the manager does instead.
- `<cost>` is the measured cost with its number and unit: minutes waited, sessions without a commit, tokens, dollars.
- `<record>` is the file and line that show the mistake, such as `<run>/lessons.md:147`.
- The same mistake again: append `; <YYYY-MM-DD>, <record>` to its item; it keeps its number.
- An item that fired in no run for three runs moves under `## Below the fold` with its number.
- The page stays under 8,000 bytes, about 2,000 tokens. After each edit, and for the run's measurement page (the items
  added, the items fired again with their counts, the recurrences):
  `python3 -I <skill>/scripts/manager/measure_manager.py lessons <this page> --since <the run's first day>`.
- Classes of mistakes to name in a trigger: a duty read late, a rollout not simulated, an estimated time, a guessed
  timeout, polling by hand, an order lost on a watcher exit, the owner asked what a rule answers, a leftover not
  collected.

## All projects

## <project>

## Below the fold
