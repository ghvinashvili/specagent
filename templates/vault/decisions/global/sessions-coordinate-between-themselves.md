---
title: Sessions settle their contract between themselves; the owner gets finished results, never session names or a plan to re-approve
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [all]
sources: []
decided: 2026-09-24
by: owner
review: 2027-10-31
why: the owner decides goals, trade-offs and real product choices, not the wiring between sessions, and does not track session names
decision_status: decided
would_change_if: the owner asks to see a cross-session contract or stage list before it is built
---
# Sessions coordinate between themselves

**Rule.** When work is split across sessions, the technical contract between them (which fields, units, parameters, who computes what) and the order of work are settled by message between the sessions, not put to the owner. The owner owns the goals and the plan; the sessions own the wiring. Once a design is settled, the sessions build it to the end without bringing a plan or stage list back for another review.

**Why.** Work split into an engine session and an extension session drew objections from the owner: a design full of engine fields put to them, a wrong claim about where a value comes from that the other session could have answered, a session referred to by its number, and a combined stage list brought back for review (2026-09-24, 2026-09-25). The owner decides goals and product choices; the wiring is the sessions' work.

**How to apply.**
- Before telling the owner how a part on the other session's side works, or proposing a diagnosis that rests on it, ask that session: my side's code and the plan's text lag behind the other side.
- The producing session does not wait to be asked: every field or parameter it adds and every change of meaning (a field now sent, another default, a unit) goes to the consuming session the same hour, with exact spelling, range, default and expected use. Check mechanically: list every field emitted and parameter read, search the consumer's code for each; the consumer decides about what it never reads.
- The owner still gets what they can judge (before/after pictures, gate results, changes of look or behaviour) and what is genuinely theirs (a trade-off, a cost, a ship into their browser); a question reaches them only when it touches a standing rule or a real product choice. Standing rules still bind the sessions' agreement.
- In what the owner reads, never name a session by its number or slug; describe it by what it does, and never hand them a task split across sessions. Peer messages may use the names.
- A chat inside the template folder holds every peer message (the template's `crossSessionInbound: "hold"`, which local settings cannot open; editing the frozen settings stops active runs): open template chats from a folder outside the template, answer a chat inside the template through a file outside the repo and give the owner its path (2026-10-04).

Related: [[decisions-are-the-owners-technical-choices-are-mine]].
