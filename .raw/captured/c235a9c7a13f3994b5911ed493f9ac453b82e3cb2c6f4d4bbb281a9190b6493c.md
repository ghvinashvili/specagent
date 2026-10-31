---
title: The shared knowledge base
type: decision
status: draft
updated: 2026-10-29
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: every user of the template needs a private vault for the rules and decisions that outlive one project, and the global lessons of all users are worth more in one public place than scattered; private material must never reach that place, so the refusal is code, not a judgment a chat can be talked out of
would_change_if: the commons (not built yet) shows that its candidates go unreviewed, or that a refusal class blocks pages that hold nothing private; or private material passes the checks
decision_status: decided
scope: global
tags:
  - decision
---
# The shared knowledge base

Every user of the template gets a private vault of their own, and may offer a global decision or concept from it to
one public commons by pull request. The vault is the authority for its owner; the commons is a source, not an
authority.

## The vault

`python3 ops/new-vault.py <vault_path> [commons_path=<path>]` copies the vault form `templates/vault/`: `README.md`,
`rules.md` (how pages are written), `INDEX.md` (the empty index with its sections), `log.md`, the folders
`decisions/global/`, `concepts/`, `context/owner-statements/` and `context/measurements/`, and `ops/` with the vault's
own scripts (`outline.py`, `check_pages.py`, `split_large.py`, `build_indexes.py`, `collect_memory.py`). It draws an
opaque origin id (`secrets.token_hex(6)`, the `origin:` line of the README's frontmatter), writes `commons_path` into
`INDEX.md`, makes one commit and prints the user's own step: a private remote. It refuses a folder that is not empty,
and a machine where git has no identity, before it writes anything. `ops/new-project.py ... vault_path=<path>` runs it
when `<path>/INDEX.md` is missing. A page's `scope` is `global` or the name of one domain, whose decisions live in
`decisions/<domain>/`; the vault's `check_pages.py` accepts a public URL as a source.

## The commons

`commons_path` (default `~/aftpro-commons`, `docs/template/variables.yaml`) is a clone of the public commons, which
holds `pages/` and `evidence/<origin>/`. `CLAUDE.md` ("The owner's vault") tells every session that it is a source, not
an authority: where a commons page and a vault page disagree, the vault page wins and the disagreement goes back as a
finding. `harness doctor` checks that the vault holds `INDEX.md`, `rules.md` and an `ops/check_pages.py` that passes,
and that the clone was fetched within seven days; each gap names the command that closes it.

## Offering a page

After the owner's yes for a page, `python3 ops/contribute.py <vault-page> [<evidence-file> ...]` derives the commons
page: `title`, `summary`, `type`, `scope`, `status`, `projects`, `sources`, `would_change_if`, `licence`, `updated`, with
`status: candidate`, the vault's own origin id (and no other) in `projects`, each evidence file as
`evidence/<origin>/<file>.md` and `licence: CC-BY-4.0`; a concept becomes a `lesson`. It refuses, naming the class
and writing nothing:

- `path` (only `decisions/global/*.md` and `concepts/*.md`, the name in lowercase letters, digits and hyphens: it
  names the branch and the commons page), `type`, `missing-field`, `size` (12 KB);
- `private-path`: `context/`, `~/`, `/home/`, `/Users/`, `docs/handoff/` or a memory file in a source or the page, or
  evidence kept under `context/` or `.claude/`; `source`: neither a public URL nor submitted evidence;
- `origin`: a project named other than by the vault's own origin id; `rule-under-two-ids`: `status: rule`, since a
  page enters with one id and a second origin confirms it only by its own pull request;
- `secret`: the vault's own patterns (`collect_memory.py`) in the page, its file name and its evidence, reported by
  label only (a refusal line shows a hit as its label); `georgian`: in the same three, the block that
  `harness validate` checks and the two it misses;
- `evidence` (missing, not Markdown, or not UTF-8 text: the bytes scanned are the bytes committed), `exists` (the
  commons has the page, or the branch is there), `no-clone`.

No flag skips a check: an unknown option exits 2. The commit is built in an index of its own on top of the clone's
`HEAD`, so the clone's checkout stays as it was; the branch `contribute/<origin>/<name>` is pushed and `gh pr create`
opens the pull request, or, without `gh`, the two commands are printed. `--dry-run` prints the page (never one that
holds a secret) and the refusals. Tests: `ops/tests/test_new_vault.py`, `ops/tests/test_contribute.py`,
`packages/harness/tests/test_doctor_vault.py`.

## Not built yet

The commons repository itself, its checks and its review flow (a critic session per page; a candidate becomes a rule
when a second origin confirms it), and the measure of what the commons is used for. Until the review flow exists, a
page the commons already has is refused as `exists`.
