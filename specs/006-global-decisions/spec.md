# Spec 006 — global decisions: born from a found mistake, proven, carried by the template

Owner's decisions, 2026-10-31 (vault `context/owner-statements/2026-10-31.md`; pages
`decisions/global/global-decisions-are-rules-not-quotes.md`, `a-rule-broken-twice-becomes-code.md`): the global
decisions are what every project must have from its first day, so that a fundamental mistake found once in any project
is not made again in another; they are rules, never the owner's words; a rule enters on proof and the owner's yes and
leaves by its `would_change_if`; the template carries them and keeps working this way, with no clean-up pass before a
publication.

## Intent
Today the vault's 61 global pages were written from the owner's statements: about 36 carry the owner's quoted words
(94 hits by a heuristic list), 23 hold Georgian letters, 2 name a proof page, none a `kind:` or `template:` field, and the template ships none of them (`templates/vault/decisions/global/` is empty),
so a project on another machine starts with no rule at all, and a publication needs a clean-up pass. This spec makes
the global decisions one body of proven, neutral rules that every project starts with, and makes the way a rule is
born, proven, kept, carried and retired the template's own: written once, checked in code.

## Requirements
1. **The form of a global page.** Rule, why, how to apply, in neutral English; no quote, name, language, machine,
   account, path or e-mail of the owner; `proof: [context/<page>]` names the measurement page or the record of the
   found mistake; `would_change_if` names the evidence that would revise it; a page personal by nature carries
   `template: no`; `kind:` names the page a lesson (proof mandatory) or an order (the owner's standing decision on how
   the work is done: no proof, never deleted for lack of one, `review:` one year on, changed only by the owner's word). (The vault's `rules.md` and `ops/check_pages.py` say so since 2026-10-31; the template says it in
   its own files: `templates/vault/rules.md`, the manager's documents.)
2. **Where a rule lives, by who must obey it.** One ladder, written in one place of the template, the other documents
   pointing to it: a finding is recorded in the run; a cause shared by two findings becomes a rule in the run's
   `lessons.md`; at the run's end the main session compares the run's causes with the vault's pages and the other
   runs' records; a cause found in two runs becomes a rule where its reader is: the main session's rules in the
   vault's global decisions and `manager-lessons`, a role session's rules in the skill's `example/lessons.md` "Read
   first" and `first-pass-rules.md` (a role session reads no vault); a rule broken a second time becomes a check in
   code (hook, validate rule, watcher or monitor script, test). Proof first: the measurement page or the record exists
   before a rule cites it.
3. **The way in and out.** The main session proposes a global rule with its proof page; the page enters on the owner's
   yes, never on the main session's judgment; when a run's verifier records the `would_change_if` case, the main
   session marks the page `withdrawn` with the record's path and tells the owner. The manager's documents carry these
   steps as the end-of-run routine, next to the measurement page.
4. **The existing pages.** Every global page of the owner's vault is brought to the form of R1: the owner's words moved
   to `context/owner-statements/<date>.md` and named in `sources:`; the proof found among the vault's measurements,
   memory and the runs' records; the writer sorts each page into lesson or order (an order keeps `kind: order` and a
   `review:` date one year on, and needs no proof); a lesson that none proves today leaves `decisions/global/` for `context/candidates/`
   with `review: <date>` (owner, 2026-10-31: it waits for its proof, and no useless record piles up): the main
   session proposes it again when a run's record or a measurement proves it, and past its review date with no proof
   it is deleted (git keeps the history); personal pages marked `template: no`. No page's meaning changes; a page that
   cannot be made neutral without changing its meaning, or that is one project's decision, is listed for the owner.
5. **The template carries them.** `templates/vault/decisions/global/` holds a copy of every global page that has a
   proof and is not `template: no`, made by one script that runs the same checks (`check_pages.py`, no Georgian
   letter, no model name, no owner marker) and refuses otherwise; `ops/new-vault.py` seeds a new vault with them and
   their INDEX lines; the template's tests cover the copy and the seed.
6. **Checks in code.** `check_pages.py` (the vault's and the template's copy) refuses a global page without an existing
   proof page, with a quoted text of the owner (a quote whose words are mostly not English, or hold a Georgian letter)
   or with a Georgian letter outside `context/`, and names a candidate past its review date (prove it or delete it); the
   template's tests cover each refusal.
7. **Every template change carries its migration line.** `docs/template/MIGRATIONS.md` keeps an `## Unreleased` entry
   above the versions: a commit on `main` that changes a template-owned path adds its line there in the same commit
   (date, the paths, the step a project takes), and the release moves the entry under its version number. A check in
   code refuses a commit that changes a template-owned path and not the entry (`harness version-check` or a test the
   gates run). Found 2026-10-31: eight commits after 1.7.0 changed template-owned paths with no entry.
8. **Taken by copying.** Every path this spec changes is template-owned and copied verbatim by the migration rules
   (`templates/vault/**`, `ops/**`, `docs/template/**`, the skill's files); none is on the hand-merge list (`CLAUDE.md`,
   `pyproject.toml`, `.claude/settings.json`, the wiki files). The 1.8.0 entry's Steps are the copy and the Checks, with
   no hand-merge and no role in the project; a project on this machine reads `~/vault` and takes nothing else.
9. **The version.** `docs/template/VERSION` 1.8.0; a `docs/template/MIGRATIONS.md` entry for 1.8.0 (the paths this run
   changes, "Breaks active runs"); `CHANGELOG.md`; `docs/llms.txt`.

## Limits
- The owner decides what is a decision; the sessions decide how it is written and checked. No page's meaning changes
  without the owner's yes; the writer lists, never decides, a page it cannot make neutral.
- Roles stay blind to models and authors: no model name in any page the template carries, none in the briefs.
- The owner's vault is a git repository: the writer works in a worktree of it, the main session merges and pushes.

Calls made by the spec's author, open to the owner: the quote check falls back to Georgian letters and a short list of
Latin-script Georgian words where no English word list is installed; the ladder's one place is the skill's `SKILL.md`
"Briefs" paragraph, the manager's documents point to it; the writer edits the vault in a worktree on a branch; a candidate's review date is 90 days from the day it moves.

## Done
`python3 ops/check_pages.py .` on the vault: 0 problems, every global page with `kind:` and, by its kind, `proof:` (a lesson)
or `review:` (an order); no page left in `decisions/global/` without one of them (a lesson that nothing proves is in `context/candidates/`);
`git grep` finds no quoted owner text and no Georgian letter under `decisions/global/`; `templates/vault/decisions/
global/` holds every proven, non-personal page and a fresh vault starts with them; `uv run pytest -q`, `harness
validate`, `docs-check`, the skill's `check_formats.py` pass; the ladder of R2 stands in `SKILL.md`,
`docs/roles/manager-chat.md` and `templates/vault/rules.md`, and no other document contradicts it.

## Out of scope
Project decisions in each project's wiki; the commons; the carry into grantsdaily (a copy, by R8); the lessons of runs still open;
the content of any rule (what a rule says is the owner's, this spec is about its form, proof and path).

## Run plan (proposed; the owner decides)
Three units in order, one verifier. Unit 1 = R2, R3, R6, R7: the documents and the checks (builder, template worktree).
Unit 2 = R4: the 61 pages, in a worktree of the vault (writer; it first copies the template's `templates/vault/ops/*.py` of
Unit 1 into the vault worktree, the vault's own copies being the template's). Unit 3 = R5, R8, R9: the copy script and the
seed, the 1.8.0 entry as a copy, the version (builder). The verifier checks each unit on its commit; the main session
merges the template branch and the vault branch and pushes both. The builder and the writer mechanical class (owner, 2026-10-31:
the work is mechanical; a doubtful page is listed, never decided), the verifier judgment class (owner, 2026-10-31).
Estimate ~$30-40, about 3 hours.
