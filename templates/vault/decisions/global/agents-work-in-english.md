---
title: Pipeline agents work in English from the first word
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [all]
sources: []
decided: 2026-10-10
by: owner
review: 2027-10-31
why: text outside the Latin script costs about twice the tokens and eats the usage limit; only the main session talks to the owner
decision_status: decided
would_change_if: a measurement shows output outside the Latin script no dearer, or the owner wants to read agent files without translation
---
# Pipeline agents work in English from the first word

**Rule.** Every launched agent (planner, critic, builder, verifier, judge, writers, any future role) thinks, replies, names its tool calls and writes files and summaries in English. No summary files in the owner's language are asked of agents (files named for that language keep their name, the content is English). The main session translates for the owner.

**Why.** Text outside the Latin script costs about twice the tokens and eats the usage limit, and only the main session talks to the owner, so nothing an agent writes needs to be in the owner's language. The rule once failed for a hidden reason: for a checkout under the user's home directory, the agent runtime also loads the user-level instructions file, whose rule to answer in the owner's language then reached the agents. Setting the sources to local stops that file from loading while the settings' denies still apply.

**How to apply.**
- State the rule in the launch prompt itself and in the shared brief (`_common.md`, "Language"), not only in a role's assignment; also in the watcher's FRESH and NUDGE prompts.
- Every launch and every resume carries the `--setting-sources local` flag (recorded in the skill and in `_agents.json`, `common`).
