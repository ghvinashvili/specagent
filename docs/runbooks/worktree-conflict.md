# Runbook: worktree branches that conflict

Every background session edits in its own worktree under `.claude/worktrees/` on its own branch; shards of one stage never
see each other's commits. A conflict therefore appears only when the branches are merged.

## Before it happens
- `harness launch` keeps a task and everything it depends on in one shard. Two tasks that touch the same file must share a
  `depends_on` edge in the planner's `tasks.json`; the plan gate cannot see file overlap, the planner's contract asks for it.
- The brief's "Out of scope" and the task's `category` say which directories a shard owns.

## When it happens
1. List the branches: `git worktree list` shows every worktree under `.claude/worktrees/` with its branch; the session id in a commit's trailers identifies the shard through `manifest.json` (`docs/quality/PROVENANCE.md`).
2. Merge in task order into an integration branch, never into `main`: `git switch -c integrate/<run-id>` then `git merge --no-ff <branch>`.
3. On a conflict, do not resolve it by hand without a record. `git merge --abort`, then resume the shard that owns the later
   task: `uv run harness resume --run <run-id> --stage write --shard <N> --message "Rebase onto <branch>; conflicts in <files>."`
   The gate of that shard and the `verify` stage run again on the result.
4. If both shards changed the same lines on purpose, the plan is wrong: reject at the approval point and plan again.

## What does not help
- `/rewind` and file checkpoints: they cover edits made with Claude's file tools in one session, not commands and not another
  session's changes. Going back is done with git on the worktree branch.
- Editing the main checkout from a role session: worktree isolation blocks it.
