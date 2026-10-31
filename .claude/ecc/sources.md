# ECC sources

ECC (`https://github.com/affaan-m/ecc`) is a public collection of Claude Code rules, skills, agents, commands and
hooks. This repository carries a reviewed selection of it as pinned copies: content only, none of ECC's hooks,
commands or agents as mechanism. A copy changes only by a re-pin (below), never by hand; its one local change is
listed under Pin.

## Pin
- Commit `25278e7d7b6cf6e6a4e7a6c8e10f14ff22f0eb5b` (2026-10-26; ECC 2.2.3).
- License: MIT, "Copyright (c) 2026 Affaan Mustafa". MIT asks for its notice and permission text in all copies, so
  each unit (`.claude/rules/ecc/`, each copied skill's folder and `.claude/ecc/agents/`) holds ECC's
  `LICENSE` unchanged.
- Each unit has a `SHA256SUMS` of its files (`sha256sum` format, paths relative to the unit, sorted). In the unit's
  folder `sha256sum --strict --quiet -c SHA256SUMS` checks the copy; `ops/tests/test_ecc_pins.py` checks the same and
  the review below. Neither name ends in `.md`, so Claude Code does not load them as rules.
- Local change: each copied skill's `description:` line is shortened to at most 150 bytes, its meaning kept, the
  limit of every skill here (`packages/harness/tests/test_surface_pruning.py`); the unit's `SHA256SUMS` holds the
  shortened file. Every other difference from ECC is the re-pin's: the lines the review drops and the split (below).

## Selection
- Rules: ECC's rules for Python, C++ and TypeScript (`rules/<language>/`), the languages of this repository and of
  the projects made from it, to `.claude/rules/ecc/<language>/`. Each has a `paths` list, so it loads only when Claude
  reads or edits a matching file.
- Skills, to `.claude/skills/<name>/`: on those languages or on PostgreSQL alone, `python-patterns`,
  `python-testing`, `cpp-coding-standards`, `cpp-testing` and `postgres-patterns` (ECC's TypeScript skills are about
  frameworks such as React, Next.js and NestJS, and are not copied); chosen by the owner, `docs-governance`,
  `conventional-commit-review`, `agent-security-hardening`, `eval-harness`, `agent-eval` and
  `agent-self-evaluation`. A role session sees a project skill only when its agent file lists it.
- Agents: the text of 70 of ECC's 71 agent definitions, as material for chat-role briefs, to
  `.claude/ecc/agents/` ("Agents" below). `php-reviewer` is left out: this template carries nothing specific
  to PHP.
- Hook recipes: the section "Common Hook Recipes" of ECC's `hooks/README.md`, as reference, to
  [ECC hook recipes](hook-recipes.md).
- Not copied: `rules/common/` (no `paths`, so it would load into every session); each language's `hooks.md` (ECC
  hooks); `rules/python/fastapi.md` (a framework rule: its paths `**/app/**/*.py`, `**/fastapi/**/*.py`,
  `**/*_api.py` match no file here, and it names the skill `fastapi-patterns`, not copied); `rules/python/security.md`
  (every section drops: 8-9 K2, 10-20 `python-dotenv` K4, 21-27 bandit K3, 28-30 the skill `django-security` K1);
  `skills/agent-self-evaluation/references/hook-integration.md` (an ECC Stop hook, K1); every ECC command, hook and
  hook script.

## Review
Each file was read against this repository's rules (`CLAUDE.md`, `AGENTS.md`, `.claude/rules/*.md`,
`specs/constitution.md`, `pyproject.toml`, the justfile) and Claude Code's pages on rules
(`https://code.claude.com/docs/en/memory`: "if two instructions contradict each other, Claude may pick one
arbitrarily") and skills (`https://code.claude.com/docs/en/skills`). A part that fails a criterion is dropped as whole
lines; nothing is reworded. A dropped range between two blank lines takes the second blank line with it, and one that
ends the file takes the blank lines before it.

| Code | Dropped when the part |
| --- | --- |
| K1 | names an ECC agent, command, hook or script, or a skill or rule that is not copied |
| K2 | links into ECC's `rules/common/`, which is not copied |
| K3 | runs a Python tool outside `uv` or one the `dev` group lacks (bare `pytest`, `pip install`, black, isort, pylint, mypy, bandit, `pytest --cov`), or adds a `pytest.ini`, which pytest reads instead of `pyproject.toml` ("`pytest.ini` files take precedence over other files … even when empty"; options of several files are "never merged") |
| K4 | contradicts a written rule of this repository, quoted in its row of [ECC files](files.md) |
| K5 | is contradicted by the official documentation of the tool it names |
| M | is a mechanism of ECC's subagents: a frontmatter `tools:` or `model:` line, or an order to invoke another agent |

Kept on purpose, as no rule here speaks against them: Repository and Protocol patterns (Article IV of
`specs/constitution.md` allows an abstraction with a named second use), Flask and FastAPI examples, custom pytest
markers, coverage targets, Zod, React props and React hooks, clang-format and clang-tidy, GoogleTest, CTest and lcov,
npm commands in TypeScript examples, the frontmatter keys `license` and `origin` (`harness validate` reads only a
skill's `name`), the example transcripts of `agent-self-evaluation` that show a `pytest` run (they show grading, they
give no command), and links to upstream projects.

## Files
The table of every upstream file, its sha256 at the pin, its copy and the lines dropped is a page of its own:
[ECC files](files.md).

## Agents
[ECC agents](agents/README.md) lists every copy with the upstream file's sha256 and the lines dropped besides
`tools:` and `model:`: in 32 copies a line or section that names an ECC agent, command, hook or script, or a skill
not copied (K1), and in `react-reviewer` and `vue-reviewer` an order to invoke another agent (M). The seven copies
over 12,000 bytes are marked there `read by outline`: such a copy is read through `python3 ops/outline.py <copy>`
and the sections a brief needs (`--show "<heading>"`), never whole.

None of them is an agent of this repository: `.claude/agents/` holds this repository's own definitions, and its SpecAgent
sessions get their tools and model from their settings files. A brief for a chat role borrows from a copy by line range
(owner, 2026-10-29): its `Spec:` line names the pinned copy and the lines, and the manager pastes those lines into the
run folder's brief at launch, word for word, trimmed by the drop rules K1-K5 and M above and under 60 lines in all, so a
finding cites the same place in every run (the pipeline skill's references/choosing-roles-and-skills.md). The brief
binds the agent, the copy does not; the copy's "Prompt Defense Baseline" is replaced by the input rules of the pipeline
skill's brief template.

## Split
`SKILL.md` stays within 500 lines (the skills page: "Keep `SKILL.md` under 500 lines. Move detailed reference material
to separate files.") and 12,000 bytes. A skill over either after its drops (python-patterns 681 lines, python-testing
692, cpp-coding-standards 724) keeps its text up to its second `##` heading and lists the rest under
`## Additional resources`, as the skills page shows; each later `##` section is a file of its own under `references/`,
byte for byte. A heading inside a fenced code block does not count. A file's name is its heading in lower case, each
run of characters other than a-z and 0-9 replaced by `-`, with no `-` at either end.

## Markdown lint
The copies keep ECC's bytes (all but the local change under Pin), so markdownlint with this repository's
`.markdownlint.yaml` reports issues in them (table pipe style, blank lines around fences, a fence without a
language). They stay: a fix would change the pinned bytes.

## Re-pin
1. In an ECC checkout, list what changed: `git diff --stat 25278e7d7b6cf6e6a4e7a6c8e10f14ff22f0eb5b <new> -- LICENSE
   rules/python rules/cpp rules/typescript agents hooks/README.md skills/<each copied skill>`; review each changed
   file against the criteria, and look for new files of the selection.
2. Rebuild each copy from `git show <new>:<path>` without its dropped lines (renumbered for the new text), then the
   split, then the local change under Pin; no other edit by hand.
3. In each unit's folder, write its `SHA256SUMS` anew:
   `find . -type f ! -name SHA256SUMS -printf '%P\n' | LC_ALL=C sort | xargs sha256sum > SHA256SUMS`.
4. Update this page, `files.md`, `agents/README.md` (with the size mark of each copy over 12,000 bytes)
   and the constants of `ops/tests/test_ecc_pins.py` (`PIN`, `UPSTREAM`, `DROPPED`, `RECIPES`, the counts), then
   run `uv run pytest -q ops/tests/test_ecc_pins.py packages/harness/tests/test_surface_pruning.py` (the second
   holds each description to 150 bytes).
5. Changed copies under `.claude/` are instruction files: a new `docs/roles/VERSION` with its `docs/roles/CHANGELOG.md`
   entry (`uv run harness version-check --base main`).
