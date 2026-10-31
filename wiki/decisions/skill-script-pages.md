---
title: The skill's script docs are one page per script, the README an index
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: one README with a section per script grew past the 12 KB rule for a folder README, and a page per script is read alone when a step needs it
would_change_if: a script page that drifts from its script's --help, or the README over 12,000 bytes again
decision_status: decided
scope: global
tags:
  - decision
---
# The skill's script docs are one page per script, the README an index

Each script of the pipeline skill has its page, `scripts/docs/<stem>.md`, with its usage, options and files;
`scripts/README.md` holds the index line of each page, the config fields and the tests, at most 12,000 bytes, and a new
script adds its page and its line. `scripts/tests/test_docs.py` keeps both. The README held a section per script,
19,156 bytes, when the manager-build run began (tracker TD-008; manager spec 8.3.9).

## Record and source
- [The scripts' index](../../.claude/skills/running-specagent-pipelines/scripts/README.md)
- Task 10 of the manager-build run, commit 129a9d5
