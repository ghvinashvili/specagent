---
status: accepted
date: 2026-10-04
decision-makers: the human, who chose the split on 2026-10-03 and approved it with the opening for fix runs on 2026-10-04; drafted by server-e6, reviewed by server-19
consulted: harness maintainers
informed: all package owners
---

# A type that is not blind reads what a subagent reads, and a fix run may change the hook scripts

## Context and Problem Statement
`docs/roles/need-to-know.yaml` closed the agent files, the stage tables, the policy itself, the generated role-type
catalog and `design/` to every role type, because they name the model, effort and budget of every type. A subagent
sent into the repository reads all of them, and the human's rule is that no role type is weaker than a subagent
(ADR-0006). The audit of 2026-10-04 (run 20261004-011757-audit-max) then found defects in those files and under
`.claude/`, which the write gate's scope check closes to every role's branch: no run could have fixed them.

## Decision Drivers
* A producer type is refused nothing a subagent sent to do the same job could do (the human's rule; ADR-0006).
* A blind type still does not learn who made the work, what the others found or how the flow judges it.
* What closes a path for every session, secrets above all, stays in the project's settings, where a subagent meets it
  too.
* A role session never changes the rules that govern itself or another session.

## Considered Options
* Split `repo_deny` into a list closed to every role and `blind_deny` for the blind types; a fix run opens the hook
  scripts with one explicit line of its brief, and the rest of `.claude/` is changed by the manager
* Keep the lists, and let the manager change every closed file by hand
* Open everything to every type

## Decision Outcome
Chosen option: the first, because it alone meets every driver.
- `repo_deny` in the defaults holds what no role reads: `.claude/agent-memory/**` and `docs/handoff/**` (ADR-0007).
  Secrets are closed to every session, subagents included, by `permissions.deny` and `sandbox.filesystem.denyRead`
  in `.claude/settings.json`.
- `blind_deny` holds the agent files, the stage tables, the policy, `docs/generated/role-types.md` and `design/**`.
  `access.type_row` adds it to `repo_deny` for a type whose row says `blind: true`, so every reader of the list (the
  deny rules of a session, its material, the scope check) sees the same list.
- A type that is not blind is refused more only for a reason a subagent's job would respect as well: the writer does
  not read the hidden eval cases (`repo_deny_extra`), and the two types that read untrusted text read nothing of the
  repository. The test that holds this decision names each exception with its reason.
- A session that enters a checkout reads that checkout's project settings, skills, agents and commands (Claude Code's
  settings and worktree documents, checked by server-19). A change to them on a unit's branch would govern the
  reviewer that enters the branch, or the unit's next attempt, before any review. So the scope check keeps
  `.claude/**` closed to every branch, with one exception: when the run's brief has the line `- Hooks: open`, the hook
  scripts under `.claude/hooks/` may change. Every session runs the main checkout's hooks
  (`"$CLAUDE_PROJECT_DIR"/.claude/hooks/...`, and a role session starts at the root), so a changed script runs
  nowhere before the run is integrated, after the verifier, the critic, the judge and the human. The rest of
  `.claude/` is changed by the manager outside a run, reviewed and approved like this decision.
- Claude Code asks before every edit under `.claude/`, and in a role session nobody answers (measured for
  `.claude/hooks` by run 20261003-230523-sandbox-probe). `permission-request.py` answers yes to one request only: an
  Edit or a Write of a file under `.claude/hooks/` of the session's own checkout, in a run whose brief opens the
  hooks, by a type whose checkout is its own work (`HARNESS_OWN_CHECKOUT`, set for a type that changes the repository
  or builds a trial), in a session started in the main checkout, on a path with no `..`, no symbolic link from the
  checkout down and to a file with no second hard link. Every other prompt is denied as before, also when the hook
  cannot read the request. Every role session's settings say `"disableAllHooks": false`, so a checkout's own settings
  cannot switch the hooks off.
- The scope check sees both paths of a move (`git diff --no-renames`). Without it a file moved out of a closed path
  was named by its new path only, and the check never saw the closed one; found while this decision was written.

### Consequences
* Good, because the producers of a fix run read every file the audit found a defect in, and change the hook scripts
  under the whole review of a run.
* Good, because the blindness of the reviewing types is now a list of its own, with its reason.
* Bad, because a producer can read how the critic and the judge are instructed and could write to pass them. The
  critic and the judge reproduce what they judge (ADR-0006, ADR-0011), and the human approves the plan and the result.
* Bad, because the settings, agents, skills, commands and rules of the flow are still changed by hand, by the manager.
* Bad, because a file tool follows a link made between the answer and the write; that holds for every edit a role
  session makes, with a prompt or without, and the first fix wave takes it up.

### Confirmation
`packages/harness/tests/test_access.py`: `test_a_type_that_is_not_blind_reads_what_a_subagent_reads`,
`test_a_blind_type_does_not_read_the_texts_that_judge_the_work`,
`test_a_session_knows_whether_its_checkout_is_its_own_work` and
`test_stage_settings_carry_skills_cache_lifetime_and_no_auto_memory`. `packages/harness/tests/test_gates.py`:
`test_a_brief_that_opens_the_hooks_lets_a_branch_change_the_hook_scripts_only` and
`test_a_branch_that_moves_a_closed_file_out_is_refused`. `packages/harness/tests/test_hooks.py`:
`test_a_fix_run_that_opens_the_hooks_may_edit_the_hook_scripts_of_its_own_checkout`,
`test_every_other_permission_prompt_of_a_role_session_is_denied`, `test_a_hook_script_is_judged_without_links` and
`test_a_permission_prompt_the_hook_cannot_read_is_denied_in_a_role_session`.

## Pros and Cons of the Options

### Split, with the hook scripts opened by the brief
* Good, because it meets every driver, with one list per reason.
* Bad, because a producer can read the reviewers' instructions (above), and the rest of `.claude/` stays manual.

### Keep the lists; the manager edits every closed file
* Good, because nothing in the flow changes.
* Bad, because a third of the audit's fixes would skip the plan, the verifier, the critic and the judge, and the
  producers would stay weaker than a subagent.

### Open everything
* Good, because it is the simplest.
* Bad, because a blind type would learn who made the work and how it is judged, every role would read the handoffs,
  and a branch could rewrite the settings of the sessions that enter it.

## More Information
Amends [ADR-0006](0006-a-role-session-gets-what-a-subagent-would-get.md): the access a session adds is limited only
where blindness, untrusted text or the sessions that enter a checkout need it. The audit's findings and the probes
that show them are under `context/fix-20261004/`.
