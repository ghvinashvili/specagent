# The end of a run: the judge, the gate and the merge

The last steps of one run of the pipeline skill, once every task is verified: section 9 of
[how it works, step by step](how-it-works.md#9-the-judge-the-gate-and-the-merge) in full. `<run>` is the run folder,
outside the repository; every step is taken from the skill's
[SKILL.md](../.claude/skills/running-specagent-pipelines/SKILL.md) and its
[watcher, monitor and collector](../.claude/skills/running-specagent-pipelines/references/watching.md) page, unless a
link says otherwise.

## The judge

When every task is verified, `scripts/judge_after_verify.sh` waits for the STATUS lines and launches the judge once, in
a detached worktree; it reads the diff and the reports, blocks only with proof, and writes its verdict on line 2 of
`judge.md`: `VERDICT: release`, `release with conditions` (majors listed) or `blocked` (a blocker with proof; the
skill's `example/judge-assignment.md`). Each finding (`#### J<n>`) has a severity and a cause: a blocker goes back
to the builders if the cause is `(code)`, to the plan fixer if `(plan)` or `(spec)`; a major or a minor stays in
`judge.md` for the owner. The judge comes once and does not run again: a blocker's fix is one commit logged
`J<n>: fixed — <sha>`, the verifier re-checks it like a V fix, and the gate at the merge waits for that line.

## The gate, the merge and the push

After the verdict the main session merges at the gate (tests, lint, `just validate`, `uv run harness docs-check`; the
verifier has run the full suites at the milestones): a red gate goes back to the builder as a finding, a green one is
merged into `main` and pushed. The push is the main session's alone: a role never pushes, never starts an agent and
never creates a worktree (the skill's `example/common.md`, "Ending").

## The score and the measurement page

The main session measures the run and itself with the steps of
[measuring](../.claude/skills/running-specagent-pipelines/references/measuring.md), in their order:
`check_formats.py <run>` first (no number of the run is trusted while it lists an error), `findings_report.py` (the
findings per kind and the escape table), `usage_report.py` (calls and cost per role, the run's sessions picked by the
prefix of their names), `startup_report.py` (each session's context at its first write), `measure_manager.py` (the
manager's own calls, reads and lessons, and the findings per checklist item) and `scripts/manager/score_run.py` last,
which reads the records and `_watch.log` and writes one score for the run
([decision](../wiki/decisions/one-score-per-run-by-script.md)): the last row of its output is the economy row (units;
cost, sessions, copies and findings per unit; escaped). Every number, the score and the cost among them, with the
command that produced it, goes into your private vault's `context/measurements/<date>-<run>.md`, committed before
your summary or any page cites it; the README's two measured runs come from two such pages
([the measurements](economy.md#the-measurements)).

## The decisions and the vault

The run's decisions become pages in `wiki/decisions/`, written with the work
([decision](../wiki/decisions/decisions-are-written-with-the-work.md)), and `ops/obsidian-ingest.py` ingests each
through the claude-obsidian plugin (text into `.raw/captured/`, claims into `wiki/meta/ledgers/`); with
`CLAUDE_OBSIDIAN_SESSION_CONTEXT=1` in `.claude/settings.json` the plugin injects `wiki/hot.md` into every later session
([decision](../wiki/decisions/the-checkout-is-a-claude-obsidian-vault.md)).

A rule for every project joins your vault's `decisions/global/` as a lesson, only with its proof page and your yes,
or as an order (your standing decision on how the work is done), with your word and a `review:` date and no proof.
A page leaves it, marked `withdrawn`, when a run's verifier records the case its `would_change_if` names
([the routine](roles/manager-chat.md), "After a run").

## The collector

`scripts/collect_run.py` removes what the run leaves behind; the main session runs it, never a role ([its
page](../.claude/skills/running-specagent-pipelines/scripts/docs/collect_run.md)). A dry run lists, each with what its
deletion loses, the run's worktrees (each agent's `cwd`) and their branches, `<run>/scratch` and the job folders of the
finished sessions, and it keeps the record files and `lessons.md`. It refuses while the record is not saved: a record's
line 1 is not `STATUS: done`, `check_formats.py` fails, a lesson lacks its `(skill: <sha>)` or `(skill: none)` mark, a
done commit is not in `main`, a run branch has commits that are not, a deferred item of the plan is not in the tracker,
a run worktree has uncommitted paths, or a session of the run is still running. `--apply --yes <digest>` removes the
list you said yes to (a list that changed needs a new yes); once three runs were applied with a yes, `--apply` alone.
Each apply appends to `<run>/collected.md`.
