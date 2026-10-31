---
status: accepted
date: 2026-10-02
decision-makers: platform team
consulted: harness maintainers
informed: all package owners
---

# A checkout sets itself up: no manual installation after a clone or a new project

## Context and Problem Statement
The repository enabled `pyright-lsp@claude-plugins-official` for every type that reads or writes code. The plugin only
names a server; the server, `pyright-langserver`, has to be installed by hand. On the machine the template was built on
it never was: two writer sessions changed Python files 25 times and received no diagnostics, and nothing said so. Claude
Code reports a missing server only in the Errors tab of `/plugin`, and `harness doctor` did not look. The same machine
also lacked `uv`, which every command of the repository uses. The human's requirement: a checkout from GitHub, or a new
project from the template, works without installing anything by hand, for programming in general and for the web, on
Linux, macOS and Windows through WSL2, whether or not CLion or VS Code is there.

## Decision
- An internal plugin, `plugins/code-intel`, replaces `pyright-lsp`. Its `.lsp.json` names six servers: pyright (Python),
  typescript-language-server (JavaScript and TypeScript), intelephense (PHP), clangd (C and C++), and the HTML and CSS
  servers of vscode-langservers-extracted. Each starts through `scripts/lsp`, which looks in the plugin's data
  directory first, so the machine's PATH does not decide whether a server runs.
- The plugin's SessionStart hook (`scripts/ensure.py`) checks a stamp of the pinned versions (`toolchain/`) and, when it
  differs, installs in the background: uv from PyPI checked against its published hash when the machine has none,
  node and clangd as Python wheels, the servers with `npm ci` from the plugin's lock file. Nothing is installed
  system-wide; the toolchain is shared by every project on the machine. A server starts only when a file of its
  language is edited, so a language a project does not use costs nothing. `--probe` starts every server and asks it
  to initialize.
- `ops/bootstrap.py` sets up a checkout: uv into `~/.local/bin` when missing, `uv sync` on the machine's python3 when it
  is 3.12 or newer (the hooks then find the workspace's jsonschema), the project plugins of `.claude/settings.json`,
  the code-intel toolchain, and a closing `harness doctor`. The SessionStart hook of a session that is not a role
  session starts it in the background when uv or the workspace is missing; `ops/new-project.py` runs it at once.
- `harness doctor` reports the toolchain (installed, and every server answers), sends native Windows to WSL2, and
  accepts the workspace's jsonschema for the hooks.

## Consequences
- Good: a fresh checkout reaches a working state on its own; a missing server is reported instead of silently absent.
- Good: the versions are pinned and checked; the same servers run on every machine.
- Bad: the first session on a machine downloads a few hundred megabytes; it runs in the background and later sessions
  only compare a stamp.
- Bad: what needs the administrator stays with the human, once per machine: on Linux, `socat` and the AppArmor rule
  for bubblewrap that the sandbox needs. `doctor` and the setup's summary name the command; nothing asks for a
  password.
- Bad: the internal marketplace is known to Claude Code by one name for the whole machine, so the setup points it at
  the checkout it runs in. Several projects of this template on one machine take turns; a name per project belongs to
  the parts design (the design record in the owner's vault, `context/design-record/specs/2026-10-01-parts-and-project-brain-design/`; was `design/specs/2026-10-01-parts-and-project-brain-design.md`).
- Open: whether the servers' diagnostics reach a session was checked with the servers themselves (`--probe`, and a file
  with errors per language); a live session is the next check. Browser tests (Playwright) for the web are a later step.
- Amended on 2026-10-03 by `docs/decisions/0013-no-command-to-type-and-at-most-one-password.md`: the launcher
  records the trust, a role session needs the sandbox, and the sandbox is set up without a typed command.

## More Information

* Amended on 2026-10-29 by [ADR-0029](0029-a-checkout-sets-up-its-hooks-sandbox-and-graph.md): a checkout also sets up just, its git hooks, the sandbox on each OS and its first code graph.
