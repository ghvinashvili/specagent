---
title: The template is every project's default structure; whatever the owner relies on is built into it
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [main, planner]
sources: []
decided: 2026-10-02
by: owner
review: 2027-10-31
why: a mechanism that lives only in one machine's user-level configuration silently disappears in a project elsewhere
decision_status: decided
would_change_if: never
---
# The template carries what the owner relies on

**Rule.** The template is the default structure every future project of any complexity starts from, possibly on other machines. A mechanism the owner relies on in their own environment (the first case: the context hand-off hook) is built into the template as a project-level version.

**Why.** A mechanism that lives only in one machine's user-level configuration silently disappears in a project elsewhere. The owner restated the template's goal on 2026-10-25: any complex project must be buildable on it at a high level, so it takes in whatever more turns up that it should carry.

**How to apply.**
- Build the project-level version with tests and docs; keep it silent where the user-level one already runs, so nothing fires twice.
- Keep the role sessions' need-to-know rules: the manager's hand-off stays closed to role types.
- The rule covers any such mechanism, not only the hand-off.
- Besides single mechanisms, the template carries the chat-agent pipeline strategy, the second brain with its learning layer, and its own organisation as a vault (the owner's order of 2026-10-25).
- What goes in: what a project already runs in order, and the practices the owner named; the rest of the backlog by need, not ahead of it (the owner's order of 2026-10-28).

Related: [[manager-owns-structure]], [[no-conversation-copies]].
