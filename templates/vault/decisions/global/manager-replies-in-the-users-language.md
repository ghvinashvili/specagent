---
title: The manager chat replies in the language the user writes in
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-11-01
audience: [main]
sources: []
decided: 2026-11-01
by: owner
review: 2027-11-01
why: the user reads the language they write in; an answer in another language reads as ignoring them, and the slip comes after long work in another language (logs, code, agents' records)
decision_status: decided
would_change_if: the user names another language for the replies
---
# The manager chat replies in the language the user writes in

**Rule.** Every reply of the manager chat to the user is in the language of the user's own messages, whatever
language the tools, logs, code, records and agents use: answers, status lines, questions, tables and the tool-call
descriptions the user sees. Code, file and command names, identifiers and quotations keep their form. A user who
writes a language in another script (a transliteration) is answered in that language's own script.

**Why.** The user reads the language they write in; a reply in another one reads as ignoring them. The slip comes
right after long work in another language, so the rule is enforced by a check, not by memory.

**How to apply.**
- Before sending, look at the first sentence; if it is not in the user's language, rewrite the whole reply.
- A Stop hook (the language gate) compares the reply's letters, outside code and links, with the language of the
  user's last message and sends the turn back once when they differ; the template ships it registered.
- Messages to agents and other sessions follow [[agents-work-in-english]]; they never set the reply's language.
- A user's own page may add how to read their writing (their transliteration, their style).

Related: [[agents-work-in-english]].
