---
title: A global decision is stored as a rule, never as the owner's quote, so it ships with the template as written
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [all]
sources: [context/measurements/2026-10-31-spec005.md]
decided: 2026-10-31
by: owner
review: 2027-10-31
why: a decision that holds for every project is part of the template, and the template is public; a page that needs editing before each upload is a second pass that gets skipped
decision_status: decided
would_change_if: the template stops being published
---
# A global decision is a rule, not a quote

**Rule.** A page under `decisions/global/` states the decision as a rule in neutral English: what holds, why, how to apply it. It carries no quote of the owner, no name, no language or circumstance of the owner, no machine, account, path or e-mail. What the owner said, with the date and the original words, is kept in `context/owner-statements/` and named in the page's `sources:`; `by:` and `decided:` still record who decided and when.

**Why.** `decisions/global/` holds what must be in every project: the lessons learned from mistakes that were found, so no project makes them again, and the rules that let the system improve itself; the owner's words are not that. The template carries these pages and the template is published, so a page written this way is ready to ship the moment it is decided; nothing is cleaned before an upload.

**How to apply.**
- Two kinds, named in `kind:`. A lesson is a rule learned from a mistake that was found or from a measurement: its `proof:` is mandatory, it enters on the owner's yes, it leaves by its `would_change_if`, and one that nothing proves waits in `context/candidates/` with a `review:` date and is deleted past it.
- An order is a standing decision of the owner on how the work is done (the language of the work, what a session may do on its own, the quality bar): it needs no proof, is never deleted for lack of one, carries a `review:` date one year on, and changes only by the owner's word; its `why:` names the purpose, not a case.
- A lesson comes from evidence, not from anyone's say-so, the owner's included: a mistake that was found (the case, with its record) or a measurement, named in its `why:`; a statement with no case behind it stays in `context/owner-statements/` until one shows it right.
- Only a decision held to be right enters (`decision_status: decided`, `status: verified`): the main session proposes it with its proof page and it enters on the owner's yes, never on the main session's own judgment; a doubtful one waits in `context/`, a wrong one never enters.
- A page found wrong later is marked `withdrawn` with the record's path, when a run's verifier records the case that `would_change_if` names; the main session tells the owner, and the page leaves the template at the next copy.
- A general order and a proven lesson are `template: yes`; a page personal by nature (the owner's own language, accounts, machines, services) is `template: no` and stays in the vault. `ops/check_pages.py` refuses a lesson without an existing proof page under `context/`, an order without `review:`, and a global page with a quote, a non-English letter or a personal marker; the template takes only `template: yes` pages, in template-owned paths that a project takes by copying, so a change needs no hand-merge.

Related: [[a-rule-broken-twice-becomes-code]], [[template-carries-what-user-relies-on]].
