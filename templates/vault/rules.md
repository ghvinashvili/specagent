# Writing rules

1. One lesson, decision or entity per page, with a one-line summary at the top (the line `INDEX.md` shows).
2. Update the existing page instead of creating a second one. A decision that changed gets a new page with
   `status: revised` on the old one and a link to the new; nothing is silently rewritten.
3. Delete what turned out wrong (or mark it `withdrawn` with the reason); keep `context/` untouched.
4. Raw sources (`context/`) and compiled pages are always separate. After adding raw material run
   `python3 ops/split_large.py` (files over 24 KB become titled parts of at most 12 KB) and `python3 ops/build_indexes.py`
   (the layered indexes; a memory folder of more than 40 files gets its topics in `ops/memory-topics.json`). Every
   statement names its source (`context/<path>` and, where it helps, the line). `python3 ops/check_pages.py` checks
   the pages before each commit.

Frontmatter of every page

```text
---
title: <short>
type: decision | concept | entity | source
scope: global | <domain>  # global = any project; <domain> = any project of one domain (decisions/<domain>/)
status: verified | draft | disputed | stale
updated: YYYY-MM-DD
expires: YYYY-MM-DD      # optional; a page past it is stale until renewed
audience: [all]          # or role names: planner, builder, critic, verifier, main, <system-step>
sources: [context/...]   # or public URLs
---
```

A decision page also carries `decided` (date), `by` (owner | main-session | <role>), `why`, `decision_status`
(decided | revised | withdrawn), `would_change_if` (the evidence that would revise it), and `review` (a date) when
it is doubtful. A global lesson also carries `proof: [context/<page>]`: the measurement page or the record of the found
mistake that shows the rule right; `ops/check_pages.py` refuses a lesson without an existing one, whatever its date.

Sharing with the commons: a page of `decisions/global/` or `concepts/` may go to the public commons as a candidate,
only with your yes, by `ops/contribute.py` of a project made from the template. It refuses, naming the class: a
missing field (the public page also needs a `summary`, or the page's line in `INDEX.md`, and `would_change_if`); a
source under `context/` without a public copy submitted as evidence; a path into `context/`, `~/`, `/home/`, a
hand-over note or a memory file; a project named other than by your vault's own origin id; `status: rule` (a page
enters as a candidate; another origin confirms it by its own pull request); a file name other than lowercase letters,
digits and hyphens; a secret or a letter of a refused block in the page, its file name or its evidence; evidence that is not
UTF-8 text. No flag skips a check.

Forms: `forms/manager-lessons.md` is the main session's lessons page, copied once to
`decisions/global/manager-lessons.md` and read by every main session in its first calls: one item per management
mistake with its measured cost and its record, the page under 8,000 bytes (the template's pipeline skill checks it
with `scripts/manager/measure_manager.py lessons`). `forms/learning-record.md` is the shape of one learning record
(trigger, action, evidence, confidence, scope) and the rule that promotes a record to a decision page.

Never here: credentials, keys, tokens, account e-mails, server access details, personal data of anyone.

A page under `decisions/global/` states its rule in neutral English: what holds, why, how to apply it. It carries no
quote of the owner and nothing personal (no name, language, machine, account, path or e-mail); what the owner said, with
its date and original words, stays in `context/owner-statements/` and is named in `sources:`. So a global page is ready to
ship with the template the moment it is decided. A page personal by nature carries `template: no`.
Only a decision held to be right enters `decisions/global/` (`decision_status: decided`, `status: verified`), and right
means proven: a mistake that was found or a measurement, named in `why:`, never a statement alone, the owner's included.
A doubtful one waits in `context/` until it is settled, a wrong one never enters, and a page found wrong later is marked `withdrawn`.
A global page is one of two kinds, named in `kind:`: a lesson (from a found mistake or a measurement; `proof:` mandatory;
without it the page waits in `context/candidates/` with a `review:` date and is deleted past it) or an order (the owner's
standing decision on how the work is done; no proof; never deleted for lack of one; `review:` one year on; changed only by
the owner's word). A general order and a proven lesson carry `template: yes`, a personal order `template: no`; the template
holds them in paths a project takes by copying, never by a hand-merge or a run.
A global page and a candidate are each at most 4,000 bytes (a lesson or an order alike): one rule a page, short enough
to be read whole; a longer text is shortened, or split into pages that each hold one rule. The one exception is the main
session's lessons page, `decisions/global/manager-lessons.md`: it keeps the limit of its form, under 8,000 bytes.

`python3 ops/check_pages.py` refuses, in a page of `decisions/global/`: no `kind:`, or one that is neither `lesson` nor
`order`; a lesson whose `proof:` is missing or not an existing page under `context/`; an order without
`review: YYYY-MM-DD`; a quoted text of the owner (a quote with a letter of a refused block, or whose words are mostly
not English); a letter of a refused block anywhere in the page; a page over 4,000 bytes (the lessons page: 8,000 bytes
or more). In `context/candidates/` it refuses a candidate without `review:`, past it, or over 4,000 bytes.

The way in: the main session proposes the rule with its proof page (`proof:`), and the page enters `decisions/global/` on the
owner's yes, never on the main session's own judgment. The way out: every page names in `would_change_if` the evidence that
would revise it; when a run's verifier records such a case, the main session marks the page `withdrawn` with the
record's path and tells the owner. So a wrong rule leaves by the same proof that lets a right one in. Where a rule lives,
by who must obey it, is the ladder written once in the pipeline skill's `SKILL.md` ("Briefs"); the manager's end-of-run
routine (`docs/roles/manager-chat.md`, "After a run") carries these steps.