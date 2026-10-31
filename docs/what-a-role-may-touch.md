# What each role session may touch

The sandbox, the guards and the request lines of one role session of the pipeline skill
(`.claude/skills/running-specagent-pipelines/`); [how it works, step by step](how-it-works.md) says where they come
in a run, and [ARCHITECTURE.md](../ARCHITECTURE.md#a-role-sessions-sandbox) draws them.

Every role but one that edits a checkout served by a local dev server or containers runs in the sandbox, with no
unsandboxed retry. Its Bash writes only in its own worktree, the run folder, the temp dir, the package caches and the
main repository's `.git` (its commits need it), and reaches only the package hosts; the eight protected paths of its
worktree (`.claude/settings.json`, `.claude/skills`, `.claude/hooks`, `.claude/agents`, `.claude/commands`, `.mcp.json`,
`.git/hooks`, `.git/config`) are closed to its shell and open to Write and Edit. Its settings and the sandbox deny the
transcripts, `<run>/_control/`, the checkout's `docs/handoff/`, the credentials file, `/proc`, `ps`, `pgrep` and
`claude agents|logs|attach`, so no role learns which model another runs on, who wrote a file or the owner's login
([decision](../wiki/decisions/roles-are-blind-to-models-and-authors.md)). Each role's settings (the skill's
`example/*-settings.json`) wire two guards before a tool call, on Read, Write and Edit only (a Bash call runs neither):
on Read, `guard-read.py` refuses a whole read of a file over 20,000 bytes; on Write and Edit, `guard-records.py` refuses
an edit that removes or rewrites a line of a record (line 1, the STATUS line, and line 2 where a brief keeps a field,
judge.md's `VERDICT:` or critique.md's `Reviewed:`, may change). A refused step is one `SANDBOX:` line in its record,
never a workaround ([decision](../wiki/decisions/the-sandbox-sets-itself-up-and-a-refusal-is-reported.md)); a bulk copy
into the protected paths is staged in `scratch/<role>/` and asked for with a `COPY-REQUEST:` line, a checkout it cannot
make with `CHECKOUT-REQUEST:`, a fast-forward with `FF-REQUEST:`. The records monitor (`monitor_records.py watch`) wakes
the manager, which supplies the path, host or material, or makes the copy byte for byte, the checkout or the
fast-forward, and answers below the request in the requester's file (`monitor_records.py answer`,
[decision](../wiki/decisions/request-answer-lines.md)): `SUPPLIED:`, `COPIED:`, `CHECKED-OUT:` or `FF-DONE:`, or
`REFUSED:` with the reason, within 15 minutes; the sandbox is never
weakened.
