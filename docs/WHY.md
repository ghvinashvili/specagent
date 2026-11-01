# Why it is built this way

Every rule below is one a reader may question. Each section gives the rule, the reason, and the file in this checkout
that holds the decision or the measurement; the README's table "What you get" gives the same facts by feature.

## Role sessions are full chats, not subagents

Every role is a background Claude Code session (`claude --agent <type> --bg`): it can be resumed by its id, is listed
by `claude agents`, and has its own tools and permissions, while `.claude/settings.json` denies the `Agent` tool
([ADR-0001](decisions/0001-role-chats-are-sessions.md)). On one task with the same model (2026-10-02) the sessions cost
a twelfth of the subagents and their product passed more hidden checks; their documents were shallower (a plan of 156
lines against 678), which the comparison traced to thin demands against full ones, so a session now gets the
assignment a subagent would get ([ADR-0006](decisions/0006-a-role-session-gets-what-a-subagent-would-get.md)).

## Every role runs in a sandbox, the manager does not

A role session runs its shell commands in Claude Code's sandbox: it writes only in its own worktree, the run folder,
the package caches and the repository's `.git`, cannot read the transcripts, the control files or the hand-over notes,
and does not start without the sandbox (`failIfUnavailable`). Permission rules alone are porous, since a Bash
`python3` can open a path the Read tool may not, so the sandbox is the wall and the rules the second layer
([sandbox and blindness](../.claude/skills/running-specagent-pipelines/references/sandbox-and-blindness.md)). The
manager stays outside to launch the sessions and supply what a sandboxed role asks for (`COPY-REQUEST` lines, met byte
for byte; [SKILL.md](../.claude/skills/running-specagent-pipelines/SKILL.md)), and code a role wrote never runs with
its access: after an audit (2026-10-04) caught a branch's conftest.py writing outside its checkout during the write
gate, the gate runs a branch's tests in a sandbox
([ADR-0017](decisions/0017-the-write-gate-runs-a-branch-s-tests-in-a-sandbox.md)).

## Roles are blind to models and authors

No role learns which model another session runs on or who wrote a file: a reviewer that knows the author's model
judges the model, not the text, and a session that knows its reviewer's model spares itself
([decision](../wiki/decisions/roles-are-blind-to-models-and-authors.md)). So briefs name no model, the model is set in
a settings file in the run's control folder, which no role may read, and the sandbox hides the transcripts
([sandbox and blindness](../.claude/skills/running-specagent-pipelines/references/sandbox-and-blindness.md)).

## Small contexts: a hand-over at 200k, since 2026-11-01 a compaction near 197k

Since 2026-11-01 a session compacts itself near 197k and keeps its lane's pack in the system prompt; the hand-over
below is the watcher's backstop (README "The cache and the context"). The history of the rule:


Every call re-reads the whole context from the cache, so a read costs its size times the calls that follow it.
Measured 2026-10-22: 27k tokens at a session's first call, 81k after ten calls, 180-200k at the hand-over after 30-70
calls, 84% of the growth tool results; in a replay of the same work a hand-over at 140-180k moved the cost by under
7%, 120k cost more, 100k a third more and no cap twice as much
([context and cost](../.claude/skills/running-specagent-pipelines/references/context-and-cost.md)). Without a cap
sessions grew to 500-740k tokens per call (2026-10-15), and a 300k cap cost 15-25% more per task than 200k over 269
sessions (2026-10-26) ([SKILL.md](../.claude/skills/running-specagent-pipelines/SKILL.md),
[hand-over rule](../.claude/skills/running-specagent-pipelines/example/handoff-rule.md)).

## Proof for every finding, and at most three rounds

A finding names its place, the command and its output (or the quoted source), the expected result and the fix;
without proof it goes to "To check", so an author answers evidence, not an opinion
([SKILL.md](../.claude/skills/running-specagent-pipelines/SKILL.md)). The eval case
`pipeline-critic-unproven-finding` checks that the critic reports the defect it can prove and refuses the claim it
cannot, and a finding line without `— proof:` fails it ([evals](../evals/README.md)). After three rounds on one
finding a rule decides (the spec and the owner's recorded decisions win, otherwise the safer option); a harness run is
bounded the same way, three rounds per counter and five starts of `write` per run, then it stops for the human
([ADR-0024](decisions/0024-a-run-loops-until-its-reviewers-pass.md)).

## Nothing waits for the owner

The owner says yes once, before the run, to how many sessions run and for what, the final judge included; after that
no session asks: `AskUserQuestion` is denied, a dispute after round three is decided by rule, and a doubtful item is
held and logged ([SKILL.md](../.claude/skills/running-specagent-pipelines/SKILL.md)). Files are the record and
messages only wake the other side, so each role starts as soon as its input is ready and a run goes on while the owner
is away.

## English only

`uv run harness validate` refuses a letter of a refused block: a script outside the Latin blocks costs about twice the tokens for every
agent that reads it, and the template copies its text into every project
([decision](../wiki/decisions/the-template-is-english-only.md),
[ADR-0030](decisions/0030-the-template-is-english-only.md)).

## No sample project and no development records

A new project gets the template and nothing of the projects before it (owner, 2026-10-29: a clean template for a new
project): the sample package, its material and the template's own plans and design records left the repository
([CHANGELOG](../CHANGELOG.md)), and `omit` in [docs/template/variables.yaml](template/variables.yaml) keeps their
names so that a project never receives them should they return. A role reads what the repository holds as the
project's own, and every page it reads is paid for again on each call that follows
([context and cost](../.claude/skills/running-specagent-pipelines/references/context-and-cost.md)).

## A private vault, a public commons, and private material refused in code

The rules and decisions that outlive one project belong to their user, so every user gets a vault of their own: a git
repository made by `python3 ops/new-vault.py <path>`, whose next step names a private remote. The global lessons of all
users are worth more in one public place than scattered, so the commons is a separate public repository fed by pull
request ([decision](../wiki/decisions/the-shared-knowledge-base.md)). Private material must never reach it, so the
refusal is code, not a judgment a chat can be talked out of: `ops/contribute.py` names the class it refuses (a private
path, a secret, a letter of a refused block, a name other than the vault's own origin id), its one option is `--dry-run`, and no
flag skips a check, even on the user's own order (`test_no_flag_skips_a_check` in
[ops/tests/test_contribute.py](../ops/tests/test_contribute.py)).

## A decision for one project is not a global rule

A project's decisions are pages in its own `wiki/decisions/`; a decision for every project is the owner's to record in
the vault, where `scope` says whether it holds for any project or for one domain ([CLAUDE.md](../CLAUDE.md), "The
owner's vault"; [vault rules](../templates/vault/rules.md)). In the commons a page enters as a candidate under one
origin id and becomes a rule only when a second origin confirms it, since what held in one project may hold there
only ([decision](../wiki/decisions/the-shared-knowledge-base.md); that review flow is not built yet).

## Contradictions are settled by evidence and scope, not by vote

A page that a new statement contradicts is not overwritten: the librarian marks it `disputed`, records both statements
with their sources and escalates ([librarian](../.claude/agents/librarian.md)). A decision that changed gets a new page
and the old one `status: revised`, and every decision names `would_change_if`, the evidence that would revise it
([vault rules](../templates/vault/rules.md)). Where a commons page and a vault page disagree, the vault page wins and
the disagreement goes back to the commons as a finding ([CLAUDE.md](../CLAUDE.md)): the number of pages that agree
says nothing about which evidence holds, or where.

## The garbage collector checks before it deletes

Background jobs leave a `tmp` folder each, and an earlier run's jobs filled about 90 GB with them. The pipeline skill's
[clean_jobs_tmp.py](../.claude/skills/running-specagent-pipelines/scripts/clean_jobs_tmp.py) only lists them unless
given `--apply`, and removes only those of finished jobs (no process, a state of done, failed or stopped, no resumed
session under a new id, untouched for `--hours`), never following a symlink. A finished run's worktrees and scratch
wait for the owner's rule, "check that nothing was missed, then delete" (TD-010 in the
[tech-debt tracker](exec-plans/tech-debt-tracker.md): the template-core run left five worktrees, 14 GB of job outputs
and 17.7 GB of scratch), and `uv run harness abort` saves a run's uncommitted work before it removes the checkouts.

## Files, not messages

Every answer is a line in a file: `STATUS:` on line 1, `Task N: done — <sha>`, findings with ids answered by id; a
message only wakes the other side ([SKILL.md](../.claude/skills/running-specagent-pipelines/SKILL.md)). A session can
stop at any point and a fresh one goes on from the files and a note of facts, which keeps a hand-over cheap when the
watcher orders one (a compaction near 197k is the rule since 2026-11-01);
the eval case `pipeline-handoff-carries-facts` checks that a note carries facts, not pointers to files
([evals](../evals/README.md)).

## Diagrams are Mermaid text

The stage maps and the README's diagrams are Mermaid flowcharts in Markdown, which GitHub and Obsidian draw with no
plugin, no Node.js and no render step; the owner did not want the vendored renderer in the template
([decision](../wiki/decisions/diagrams-are-mermaid-text.md)). `uv run harness docs-check` reports a map that no longer
matches its stage table.
