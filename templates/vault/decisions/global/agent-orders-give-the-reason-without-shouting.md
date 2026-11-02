---
title: Every agent order says why, in calm wording without capitalised alarm words
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
why: Anthropic's prompting guidance for the Claude 5 models says a model told why a request matters generalises from the reason, and that capitalised alarm words written for older models make current models over-apply the rule; the owner adopted both for every agent text
decision_status: decided
would_change_if: the owner's word
---
# Agent orders give the reason, without shouting

**Rule.** Every text an agent reads as an order (an assignment, a pack, a brief, a role file, a skill, a message to a
running session, a waiter's text) states, beside each order that is not self-evident, why it exists: the failure it
prevents or the goal it serves, in one clause. Orders are written in plain, calm wording: no capitalised alarm words
(MUST, NEVER, ALWAYS, CRITICAL, IMPORTANT), no exclamation, no stacked emphasis. Weight comes from the reason and from
a check that enforces the order, not from typography.

**How to apply.** The template's guidance on writing assignments carries both rules and its example files follow them;
a check in the template flags capitalised alarm words in the files a launch freezes into a pack. A running pack is not
rewritten mid-run (one frozen pack per lane, [[cache-and-compaction]]); the rule applies from the next pack. Quoted
text that is not an order (a log line, an error, a third party's file) is left as it is.

Related: [[verify-every-template-change]].
