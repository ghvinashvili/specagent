# Worktree branches that conflict: summary for the owner

- Every background session works in its own worktree on its own branch, so a conflict shows only at the merge.
- Before: two tasks that touch one file share a `depends_on` edge, so one shard does both.
- When: merge in task order into `integrate/<run-id>`, never into `main`; on a conflict abort the merge and resume the
  shard of the later task with a message that names the files.
- Two shards that changed the same lines on purpose mean the plan is wrong: reject it and plan again. `/rewind` does
  not help; git on the worktree branch does.
