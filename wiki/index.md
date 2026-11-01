---
type: meta
title: Wiki index
status: evergreen
created: 2026-10-30
updated: 2026-10-30
tags:
  - meta
  - index
---

# Wiki index

Kept by the librarian and by every builder that writes pages with its work (`.claude/rules/wiki.md`). One line per
page. Read this file first; never scan the directory.
The numbered ADRs, cited as ADR-00nn, are in [docs/decisions/](../docs/decisions/README.md), not here.

## Decisions
- [The checkout is a claude-obsidian vault](decisions/the-checkout-is-a-claude-obsidian-vault.md): the root is the plugin's vault, wiki/ its pages, adopted with the plugin's own commands; the plugin comes from git at project scope
- [token-optimizer runs in every session](decisions/token-optimizer-runs-in-every-session.md): every feature on, the roles too
- [Decisions and pages are written with the work](decisions/decisions-are-written-with-the-work.md): a code task's commit carries its pages, or its task says docs: none with a reason
- [The code graph is generated, layered and refreshed by git hooks](decisions/the-code-graph-is-generated-layered-and-refreshed-by-hooks.md): bash ops/graph.sh builds it and exports one index line per top folder and package under wiki/graph/
- [Pipelines run as SpecAgent sessions from a template skill](decisions/pipelines-run-as-specagent-sessions-from-a-template-skill.md): its example briefs and settings are copied into a run folder; its waiters and watcher keep each session to one unit of work
- [What an agent reads is small and layered](decisions/what-an-agent-reads-is-small-and-layered.md): plans are folders of task files of at most 1,500 lines; an index has one line per page; a page stays under 12 KB
- [The owner's vault is read on need](decisions/the-owners-vault-is-read-on-need.md): CLAUDE.md names the vault; a session opens its INDEX.md only when a step needs an owner rule and reads by ranges
- [ECC content is pinned, never its mechanism](decisions/ecc-content-is-pinned-never-its-mechanism.md): chosen ECC rules, skills and agent texts are copied at one pinned commit with their licence and checksums
- [The template is English only](decisions/the-template-is-english-only.md): harness validate fails on a letter of a refused block in a listed file; english_only: narrows it for a project's own text
- [Roles are blind to models and authors](decisions/roles-are-blind-to-models-and-authors.md): no role learns which model another runs on: its settings and its sandbox deny transcripts, control files, hand-over notes, /proc, ps, pgrep and claude agents, logs and attach
- [The sandbox sets itself up, and a refusal is reported](decisions/the-sandbox-sets-itself-up-and-a-refusal-is-reported.md): bootstrap sets the sandbox up on Linux, WSL2 and macOS and starts no role session on native Windows; harness doctor reports it
- [The learning layer is a later run](decisions/the-learning-layer-is-a-later-run.md): ECC's learning layer is not part of release 1.4.0
- [The control plane is a later run](decisions/the-control-plane-is-a-later-run.md): ECC's control plane is not part of release 1.4.0
- [Diagrams are Mermaid text](decisions/diagrams-are-mermaid-text.md): harness map writes one Mermaid flowchart per stage table, which GitHub and Obsidian draw; the template carries no diagram renderer
- [The shared knowledge base](decisions/the-shared-knowledge-base.md): every user gets a private vault (ops/new-vault.py); a global page goes to one public commons by pull request (ops/contribute.py), private material refused in code
- [ECC text reaches a brief by line range](decisions/ecc-text-reaches-a-brief-by-line-range.md): a brief's `Spec:` line names the pinned copies and lines; the manager pastes them word for word at launch, under 60 lines
- [The plan fixer and the translator are role types](decisions/plan-fixer-and-translator-are-role-types.md): agent files, contracts and need-to-know rows, so the catalogue counts them
- [The launch table and one yes](decisions/the-launch-table-and-one-yes.md): before a launch the owner gets one table of roles, settings, skills, ECC texts and costs and answers once; the answer is a Yes: line the pre-flight checks.
- [The owner's surface is rendered by a script](decisions/owner-surface-by-script.md): `surface.py` renders one line per role and the run's risks from the registry in fixed phrases; the manager copies its status figures from it
- [The manager is the pipeline skill's main session](decisions/the-manager-is-the-pipeline-skill-main-session.md): the owner's manager is the chat that runs the pipeline skill; docs/roles/manager-chat.md describes it, MANAGER.md stays the harness's
- [The manager runs without the sandbox, with four guards](decisions/the-manager-runs-without-the-sandbox.md): permission rules, the auto-mode classifier, the owner's launch rule, never project code; every role stays sandboxed
- [Manager lessons live in the vault](decisions/manager-lessons-live-in-the-vault.md): the vault's decisions/global/manager-lessons.md with a section per project; the template ships the form and the check
- [The manager's profile is measured at its first call](decisions/the-manager-profile-is-measured-at-its-first-call.md): the terminal claude profile and just manager measured once; the one under 30,000 tokens kept
- [The control plane lives in the skill](decisions/control-plane-in-the-skill.md): the registry, the orders and the record monitor are files under the run folder's `_control/`, written by the skill's standard-library scripts
- [The record monitor answers no request](decisions/monitor-answers-no-request.md): `monitor_records.py` finds the request lines and wakes the manager; the manager answers with `monitor_records.py answer`, since every answer changes a worktree or the sandbox
- [A request is answered below it, in the requester's file](decisions/request-answer-lines.md): `SUPPLIED:`, `COPIED:`, `CHECKED-OUT:`, `FF-DONE:` or `REFUSED: <KIND> — <why>` below the request, ending with its `date -u` time; it closes the oldest open request of its kind
- [The manager's duties come from the plan](decisions/duty-list-from-the-plan.md): `duty_list.py extract` writes `_control/duties.md` from the plan before the launch; the manager reads it at every wake-up and the monitor ticks a merge on a verified `Merged:` line
- [The collector deletes on the owner's yes for three runs, then by a standing rule](decisions/collector-yes-then-standing-rule.md): the owner's yes for the exact list (`--apply --yes <digest>`) for three runs, then `--apply` alone, the owner reading `collected.md` afterwards
- [A run is collected only after its record is checked as saved](decisions/collector-save-check.md): the collector deletes nothing until the final record lines, each lesson's skill mark, the done commits and every Deferred item's tracker row are checked
- [Code cases gate every push, session cases run nightly](decisions/code-cases-gate-every-push-sessions-run-nightly.md): `ci.yml` grades the code cases and the session cases' baselines at 1.0 on every push; the session cases run nightly by `evals/nightly.sh`; supersedes eight lines of ADR-0028
- [The skill's script docs are one page per script, the README an index](decisions/skill-script-pages.md): each script's usage, options and files on its page under `scripts/docs/`; `scripts/README.md` is the index, at most 12,000 bytes
- [usage_report.py's prices carry their date and source](decisions/dated-api-prices.md): `usage_report.py`'s list prices carry their date and page (`PRICES_AS_OF`, `PRICES_URL`), printed on the report's first line
- [Roles and sessions keep their names until the owner names them](decisions/roles-and-sessions-keep-their-names.md): a pipeline's agents are roles and one run of a role a session; nothing is renamed until the owner names them
- [The spec writer's model is a dated exception](decisions/the-spec-writers-model-is-a-dated-exception.md): the model the owner ordered for spec writing is recorded in the vault as a dated exception with its `would_change_if`, not as a new rule
- [A graph over the vault is measured before it is built](decisions/a-vault-graph-is-measured-before-it-is-built.md): no vault graph in this run; the main session measures `INDEX.md` and `outline.py` first, then decides
- [Bootstrap runs eleven steps in order](decisions/bootstrap-runs-eleven-steps-in-order.md): `ops/bootstrap.py`'s eleven steps in order, named in full by the template README and `ops/new-project.py`; supersedes ADR-0029 :38-40
- [One score per run, by script](decisions/one-score-per-run-by-script.md): `scripts/manager/score_run.py <run-dir>` scores every run by the same rules from its records; the manager-build run of 2026-10-29 is the baseline of each fold
- [No fresh session after a finished role's hand-off](decisions/no-fresh-session-after-a-finished-hand-off.md): a hand-off note launches a fresh session only when the role's `work_check` passes; else the watcher logs `idle` and re-checks every round
- [The plan file is split: steps in one file, blocks in another](decisions/plan-steps-and-blocks-in-two-files.md): every fenced block over 10 lines moves to `task-NN.code.md` under `## Block <id>` and its step names it; `harness plan-lint` checks the pair
- [The planner answers its own findings; the fixer is launched on demand](decisions/planner-answers-its-findings-fixer-on-demand.md): the watcher launches the plan fixer only when open ids reach `demand.queue` or `demand.wait_minutes`
- [The critic reviews the plan only; the verifier reads the code](decisions/critic-on-the-plan-verifier-on-the-code.md): the critic keeps one coverage round per task and opens no code; the verifier reads each built commit's diff and files V ids with a `(code)`, `(plan)` or `(spec)` cause
- [Pipeline economy: hand over by itself, size the units, check in pairs, write a facts pack](decisions/pipeline-economy-hand-over-units-checks-facts-pack.md): hand-over at a unit's end; units sized and checked in pairs; the manager's facts pack `_inputs/<topic>.md`; an economy row in `score_run.py`
- [Pipeline economy: a measured estimate, three model classes, and the open items closed](decisions/pipeline-economy-estimate-model-classes-open-items.md): a launch's `Estimate:` names the last measurement
- [The template is named SpecAgent](decisions/the-template-is-named-specagent.md): one word, read as "special agent"; its text, repository and own names use it
- [ECC texts live under .claude/ecc](decisions/ecc-texts-live-under-claude-ecc.md): the agent texts and the pages about the pin sit with a catalogue the manager reads before a brief for a role with a domain
- [Finished plans live in docs/exec-plans/done](decisions/finished-plans-live-in-exec-plans-done.md): merged runs' plans move out of active/ into done/, with their own README
- [The ADRs and the decision pages stay two stores](decisions/adrs-and-decision-pages-stay-two-stores.md): the ADRs stay in docs/decisions/, the decision pages here
- [The spec writer writes the skeleton, the planner the flesh](decisions/spec-writer-writes-the-skeleton.md): a one-page spec; the model map; a rule broken twice becomes code
- [The cache is measured in dollars and set per role](decisions/the-cache-is-measured-in-dollars-and-set-per-role.md): reads, writes and output in dollars; the TTL is 5m or 1h by role

## Concepts
- none yet

## Entities
- none yet

## Sources
- none yet

## Plans and the code graph
- [Active plans](plans/README.md): the plans in progress, a folder each with its `00-index.md` (`wiki/plans` links `docs/exec-plans/active/`)
- [Code graph](graph/index.md): one line per top folder and package; generated by `just graph`, not committed

## Vault (claude-obsidian)
- [Hot cache](hot.md): the last operations and facts, at most 500 words, injected into every session at its start
- [Vault overview](overview.md): what the vault is and how its pages, sources and ledgers relate
- [Operation log](log.md): one entry per ingest and per task that wrote pages
