# Decisions

Architecture decision records (MADR 4.0), one line each; `docs/llms.txt` links this index (ADR-0026). A new record
starts from `adr-template.md` and gets its line here, after the newest one (`.claude/skills/adr/SKILL.md`).
These records are one of two decision stores, and they stay two. They are numbered and cited as ADR-00nn in code,
tests and documents, so moving them into the vault would mean one ingest a page and a new citation in every file that
names one, for nothing a reader gains. The other store is `wiki/decisions/` (listed in
[the wiki index](../../wiki/index.md)): a page each, with its reason and what would revise it, some naming an ADR as
their record.

- [ADR-0001 Role chats are sessions](0001-role-chats-are-sessions.md): why roles are full sessions and subagents are denied
- [ADR-0002 State on disk](0002-state-on-disk.md): why run state is JSON on disk and transcripts are not state
- [ADR-0003 Brief as first message](0003-brief-as-first-message.md): how the two instruction layers protect the prompt cache
- [ADR-0004 Rules and pack in the system prompt](0004-rules-and-pack-in-the-system-prompt.md): what sessions of one type share in the cache, measured
- [ADR-0005 What a live run needs](0005-what-a-live-run-needs.md): thirteen things the first complete run changed, each with its decision
- [ADR-0006 A role session gets what a subagent would get](0006-a-role-session-gets-what-a-subagent-would-get.md): the assignment per stage, depth in the types, gates that hold it, measured
- [ADR-0007 A conversation hands itself off before compaction](0007-a-conversation-hands-itself-off-before-compaction.md): the handoff hook of the manager's and a human's sessions, closed to role sessions
- [ADR-0008 A role session works to a subagent's depth](0008-a-role-session-works-to-a-subagents-depth.md): its instruction with its task, its whole material, its own compaction point, measured
- [ADR-0009 A checkout sets itself up](0009-a-checkout-sets-itself-up.md): uv, the workspace, the plugins and the language servers install on their own; what needs the administrator is named
- [ADR-0013 No command to type, at most one password per machine](0013-no-command-to-type-and-at-most-one-password.md): the launcher records the trust, a role session needs the sandbox, and the sandbox is set up as the user or with one password
- [ADR-0010 A run ends with integrate or abort](0010-a-run-ends-with-integrate-or-abort.md): abort ends a run nobody will integrate, uncommitted work is saved before a checkout goes, and doctor names what runs left behind
- [ADR-0011 Every step of a method is checked](0011-every-step-of-a-method-is-checked.md): a rule per step of every type's method, checked against the session's transcript in warn mode first, with the model and effort of the run's session as floors and the content checks of four gates
- [ADR-0012 A type that cannot write accounts for no material](0012-a-type-that-cannot-write-accounts-for-no-material.md): a type whose agent file lists tools, none of them Write or Bash, is not asked to account for its material and gets no pieces chosen by script
- [ADR-0015 A type that is not blind reads what a subagent reads](0015-a-type-that-is-not-blind-reads-what-a-subagent-reads.md): what no role reads, what only a blind type is refused, and the brief line that lets a fix run change the flow under .claude/
- [ADR-0016 A stage at max effort keeps its cache for an hour](0016-a-stage-at-max-effort-keeps-its-cache-for-an-hour.md): one-hour prompt cache for every type but the two that keep a low effort, measured on two max sessions
- [ADR-0017 The write gate runs a branch's tests in a sandbox](0017-the-write-gate-runs-a-branch-s-tests-in-a-sandbox.md): bubblewrap or Seatbelt, no network, no home directory, a fixed environment; no sandbox, no suite
- [ADR-0018 A role session writes its stage and its own checkout only](0018-a-role-session-writes-its-stage-and-its-own-checkout-only.md): Edit deny rules and sandbox denyWrite per type, read-only inputs, no messaging token, no instruction from reviewed work
- [ADR-0019 A role session runs only the harness commands listed for it](0019-a-role-session-runs-only-the-harness-commands-listed-for-it.md): the role rule of the CLI becomes a list; poll, watch and every later command refuse
- [ADR-0020 Hooks and gates fail closed and open nothing outside a stage](0020-hooks-and-gates-fail-closed-and-open-nothing-outside-a-stage.md): exit codes per event, rules from the main checkout, the plain spellings of a command read by the guards, no link followed out of a stage
- [ADR-0021 One writer at a time for run and loop state](0021-one-writer-at-a-time-for-run-and-loop-state.md): one lock per state file around read, change and write, never held while a session or a gate runs; a temporary file of its own for every write
- [ADR-0022 A prompt loop is judged by code](0022-a-prompt-loop-is-judged-by-code.md): `exit.check`, progress and spend of a prompt loop; `harness loop due` before every night session; one tick per fire
- [ADR-0023 One pause switch](0023-one-pause-switch.md): one flag the human sets and lifts; launch, resume, loop tick, poll and the night path start and change nothing while it is set
- [ADR-0024 A run loops until its reviewers pass](0024-a-run-loops-until-its-reviewers-pass.md): the critic attacks the plan before the work, proven findings go back to the plan or the writer within bounds, protected tests, exact model and effort
- [ADR-0025 A guard refuses the plain spellings; the sandbox and the write gate hold the rest](0025-a-guard-refuses-the-plain-spellings-and-the-boundary-holds-the-rest.md): the boundary of a role session by construction, a commit judged on its effect, gates that open no closed path, two limits the human accepted
- [ADR-0026 Plans in parts and layered document indexes](0026-plans-in-parts-and-layered-document-indexes.md): a plan is a folder of task files checked by plan-lint; docs/llms.txt lists a document or the folder README that lists it; a `.<language>.md` summary needs no line
- [ADR-0027 Pages are written with the work](0027-pages-are-written-with-the-work.md): a code task's commit carries its pages under wiki/, docs/runbooks/ or docs/decisions/, or its task says docs: none with a reason; integrate marks them verified
- [ADR-0028 Pipeline evals](0028-pipeline-evals.md): the error classes as eval cases graded by code without a session, three model runs, a report that compares runs
- [ADR-0029 A checkout sets up its hooks, sandbox and graph](0029-a-checkout-sets-up-its-hooks-sandbox-and-graph.md): bootstrap sets up just, the git hooks, the sandbox on each OS and the first code graph; the harness's own git runs no hook
- [ADR-0030 The template is English only](0030-the-template-is-english-only.md): harness validate fails on a letter of a refused block in a listed file; summaries are `<name>.summary.md`, in English
- [ADR template](adr-template.md): MADR 4.0
