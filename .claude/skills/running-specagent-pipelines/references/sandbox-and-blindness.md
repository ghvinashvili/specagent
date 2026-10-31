# Blind to models and authors, inside the sandbox

No role knows which model any other session runs on, and none tries to find out who wrote what: a reviewer that knows
the author's model judges the model, not the text, and a session that knows its reviewer's model spares itself. So:
- Briefs name no model or effort; the model is set in the settings file (`"model": …`), never on the command line,
  and the watcher passes `--settings <path>`, not the text. The control files (`agents.json`, `*-settings.json`) live
  in `<run-dir>/_control/`, which no role may read; briefs and record files stay in the run folder.
- Every role runs its shell commands inside Claude Code's sandbox (`example/*-settings.json`): writes only in its own
  worktree, the run folder, the package caches and the main repository's `.git` (worktree commits need it, and it is
  writable by default, `hooks/` and `config` excepted); `denyRead` hides `~/.config`, `~/.claude/projects`
  (transcripts), `~/.claude/.credentials.json`, `_control`, the hand-off notes and keys; network only to the package
  hosts; `failIfUnavailable` so a session never runs unsandboxed by accident. Permission rules alone are porous (a Bash
  `python3` can open a path the Read tool may not): the sandbox is the wall, the rules the second layer, the brief's
  rule the third.
- How the sandbox mounts the rules (measured 2026-10-29 on a live bwrap): `/` read-only; then writable binds for the cwd,
  every `--add-dir`, every `allowWrite` path and the temp dir; then a tmpfs over each `denyRead` folder and a read-only
  bind of `/dev/null` over each `denyRead` file (below, "A file in denyRead"); then read-only binds over every path an
  `Edit(...)`/`Write(...)` deny rule or `denyWrite` names. A later mount covers an earlier one,
  so a deny on `<checkout>/**` made the allowed `<checkout>/.git` read-only and no worktree could commit for 40 minutes.
  Rules: a deny never names an ancestor of a path the role must write (deny the checkout's top-level folders with `/**`
  and its top-level files with a bare rule: a `/**` rule never matches the file itself); the checkout is no `--add-dir`
  (add-dirs are mounted writable); the verifier may write its own worktree; the sandbox leaves empty read-only dotfiles
  in a working tree (`.bashrc`, `.gitconfig`, `.idea`, `.vscode`, `.claude/commands`, …), listed root-anchored in
  `.git/info/exclude`. Simulate a settings file before the rollout: `example/sim_bwrap.py <run>/_control/agents.json
  <agent> '<probe>'`.
- Protected paths inside a working directory (`.claude/settings.json`, `.claude/skills`, `.claude/agents`,
  `.claude/commands`, `.claude/hooks`, `.mcp.json`, `.git/{hooks,config}`) are closed to sandboxed commands whatever
  `allowWrite` says; the Write and Edit tools still write them. A task that writes such files: authored files with
  Write/Edit; bulk copies staged in the run folder and placed by the manager on a `COPY-REQUEST` line; the verifier
  verifies such commits from `git archive <sha> | tar -x -C <run-dir>/scratch/verifier/<sha>/` or asks
  `CHECKOUT-REQUEST: <sha>`.

### A file in denyRead

The read-deny loop of the installed binary (`~/.local/share/claude/versions/2.1.314`, `LC_ALL=C grep -a -o 'file mask
already covers: [ -~]\{0,110\}'`):
`` file mask already covers: ${Xe} -> ${xn}`);continue}xt.add(xn),w.push("--ro-bind","/dev/null",xn),Kn.push({source:"/dev/null",landing:xn ``.
Claude Code 2.1.314 masks a file in `denyRead` with a read-only bind of `/dev/null` and a folder with a tmpfs; an
update can change it, and the next pre-flight's `blind` check is the live proof.

### Rules with one slash

The pre-flight and the eval grader read `Edit(/x)` two ways (J8), so until the runtime's reading is pinned the
pre-flight refuses any single-slash `Edit` or `Write` rule: write `//<path>` for the root, `<path>` for the cwd.

### The commit trailer

A commit names no model either, but Claude Code's default commit text ends with `Co-Authored-By: <model name>
<noreply@anthropic.com>`. In 2.1.314 (`~/.local/share/claude/versions/2.1.314`, `LC_ALL=C grep -a -o
'.\{0,200\}includeCoAuthoredBy===!1.\{0,60\}'`) a valid `attribution` object wins; otherwise `"includeCoAuthoredBy":
false` makes the commit text and the PR text empty, and an absent key, `true` or any other value keeps the default. The
key is marked "Deprecated: Use attribution instead" and still works, so every role's settings carry it and no
`attribution` object (`example/*-settings.json`), and the pre-flight's `blind` check fails a file whose key is not the
boolean `false` and a file with an `attribution` key, whatever it holds. An object is valid when it has a `commit` or a
`pr` (`LC_ALL=C grep -a -o '.\{0,40\}\.commit!==void 0||.\{0,40\}'`), and `{"pr": ""}` leaves the commit text at the
default trailer. The check reads the file, not the runtime: after a Claude Code update, run the greps again.
