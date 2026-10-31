# Provenance of commits

## Trailers
Every commit a role session makes ends with:

    Harness-Run: <run-id>
    Harness-Stage: <stage>
    Claude-Session-Id: <session id>
    Co-Authored-By: Claude <noreply@anthropic.com>

The launcher sets them through the `attribution.commit` setting, passed with `--settings` on launch and on resume
(`launch.session_flags`); a resumed copy under a new id carries the new id. The manager's and a human's commits keep
Claude Code's default attribution.

## From a commit to the chat that wrote it
1. `git log -1 --format=%B <sha>`: the run, the stage and the session id.
2. `<runs root>/<run-id>/stages/<stage>/`: the prompt the session received, its `progress.md`, `result.json`, `gate.json`.
3. `stages/<stage>/logs/`: `session-end.jsonl` has the transcript path; `launch.txt` has the launch and resume output.
4. `claude --resume <session id>` opens that conversation.

## Pull requests
- `.github/PULL_REQUEST_TEMPLATE.md` has the line "Produced by run"; the run directory is the evidence behind the pull request.
- A link to the chat exists only for cloud and Remote Control sessions (`attribution.sessionUrl` adds a `Claude-Session`
  trailer there). Local role sessions have no URL: the session id is the reference.
- On Team and Enterprise plans with the GitHub integration, merged pull requests that contain Claude Code work get the
  label `claude-code-assisted` from analytics; the harness does not depend on it.

## Checks
- The trailers are text set by configuration, not a signature: they say where to look, they do not prove authorship.
- A commit on a worktree branch without `Harness-Run` was not made by a launched role session; treat it as a finding in review.
