---
status: accepted
date: 2026-10-03
decision-makers: the human, who asked for specs/001-chat-depth and approved its plan
consulted: harness maintainers
informed: all package owners
---

# Every step of a method is checked: a rule per step against the transcript, warn first, then enforce

## Context and Problem Statement
[ADR-0008](0008-a-role-session-works-to-a-subagents-depth.md) measured one reader stage run twice, as a role session
and as a subagent, from the same commit, on the same model and at the same effort: the role session wrote 208 quotes
and ran 2 probes, the subagent 431 quotes and 8 probes. The role session did what its assignment named and passed its
gate; it skipped the steps of its type's method that neither the assignment named nor a gate checked. ADR-0008 put
the type's instruction into the first message as well; whether that closes the gap is not measured. It listed "a
gate check for every step of every method" among its options and did not choose it, without writing down why.

Two more things stand between a role session and a subagent's depth
([spec](../../specs/001-chat-depth/spec.md), section 3). The effort: in the stage-map comparison of 2026-10-02 the
five subagents ran on `max`, the role sessions on `high`, the reader on `medium`, so the difference in depth cannot be
separated from the difference in effort. And the gates: three of them check content, four check it in part, and the
other eleven mostly check form.

## Decision Drivers
* A role session does every step of its type's method, not only the ones its assignment names.
* Depth, time and tokens are measured together; none is bought blind.
* Every new check is Python and asks no model; the chat writes as little as possible in addition.
* A wrong rule must not fail a stage without cause: a new stage spends a whole stage's tokens again.

## Considered Options
* Instruction only: the type's instruction in the first message, as ADR-0008 decided, and nothing more
* A rule per step, checked against the session's transcript and the stage's files, in warn mode first, then enforce
* A hidden rule: the same checks, kept out of the text the chat sees

## Decision Outcome
Chosen option: "A rule per step, checked against the session's transcript and the stage's files, in warn mode first,
then enforce", because it holds every step to a trace a script can read, asks no model, and lets a wrong rule be
found on finished runs before it can fail a stage. With it come part 1 and part 3 of the spec:

* The rule of a step: every numbered step of the Working method in `.claude/agents/<type>.md` ends with one comment
  `<!-- check: ... -->` in a small closed language (`read:`, `ran:`, `wrote:`, `output:`, `when:`, `trust:`),
  `packages/harness/src/harness/gates/steps.py`. A step that leaves no trace a script can check carries `trust:` and
  its reason. `harness validate` names a step without a rule, a rule outside the language and an `output:` that names
  a check no gate of the type has.
* The transcript: `packages/harness/src/harness/transcript.py` is the one module that reads a session's transcript.
  The gate reads the last session of a unit; a role session may not read the transcripts.
* Part 1, model and effort: the model and effort of a stage table are floors for sixteen types; `harness run` reads
  the model and effort of the session that runs it (`state.resolve_model_effort`) and raises the floors to them;
  `classifier` and `quarantine-reader` keep the table's; `harness run --effort` stands above everything. A raised
  effort multiplies `max_minutes` by 2 on `xhigh` and by 3 on `max`. The reason is fewer false `timeout` notices:
  `poll` does not stop a stage past its limit, it reports a `timeout` action. The choice, its source and the floor
  are recorded in `manifest.json` and do not change during the run.
* Part 3, content: in every type, every `path:line` names a file and a line that exist, and every evidence command
  was run as its entry says (in the session, or by the harness outside it, as a `checks.json` the stage received
  records); the judge names its sources as `<stage>#<n>` and accepts only when every blocking finding is answered;
  the researcher cites only lines it read or was given; the synthesizer names every input and both sides of a clash;
  the spec-writer's technical brief has a Constitution row per article and names only existing or `(new)` files.
* Warn, then enforce: `docs/roles/need-to-know.yaml` gives every type `steps: warn`, and the mode is fixed in the
  manifest when a run is created. In `warn` the new checks are recorded beside the verdict (`advisory` in `gate.json`,
  `## Gate warnings` in `HANDOFF.md`) and fail nothing; in `enforce` they decide as the stage's own checks do. A type
  moves to `enforce` with a one-line change and its commit.

### Consequences
* Good, because a skipped step is named, with its number and its rule, instead of passing unseen.
* Good, because `harness steps` runs the new checks on a finished run, writes nothing and asks no model, so a rule is
  tried on real sessions before it can fail one.
* Bad, because the cost rises: sixteen types run on the session's model and effort. A cache read costs 0.20 $ per
  million tokens on Opus 5.5 as on Sonnet 5.5, but output and cache writes cost twice as much, and on the reader
  `max` cost four times `high`. The exact price is not measured; `harness cache-report` shows it on the first run.
* Bad, because the time limits of a raised effort (×2, ×3) are not measured; the first real run corrects them.
* Bad, because the rule is visible to the chat, which may attend to what is checked only (spec risk 5). The rule
  names the step's own action, and the content checks of part 3 and the blind reviewers catch what goes beyond it.

### Confirmation
`harness steps` on the two runs of 2026-10-02 (`20261002-030221-e2e-count`, `20261002-044458-stage-map`) and on the
first real run of this change, each failing rule reviewed with the human, before any type moves to `enforce`.
The tests of the change: `packages/harness/tests/test_transcript.py`, `test_steps.py`, `test_depth.py`,
`test_model_effort.py` and the transcript test of `test_access.py`.

## Pros and Cons of the Options

### Instruction only
* Good, because nothing is built and nothing is checked that could be wrong.
* Bad, because the measured gap of ADR-0008 came from steps nobody checked, and nothing would name a skipped step.

### A rule per step, checked against the session's transcript and the stage's files, in warn mode first, then enforce
* Good, because every step is held to its trace by a script, and the human sees every failing rule before it decides.
* Bad, because a rule may be wrong until finished runs have tried it, and the transcript format can change with Claude
  Code (only `transcript.py` reads it, and its tests on recorded lines fail when it does).

### A hidden rule
* Good, because the chat cannot attend to the checked action alone.
* Bad, because it multiplies the failures a chat could have avoided, each of which costs a stage's tokens again.

## More Information
Amended by [ADR-0024](0024-a-run-loops-until-its-reviewers-pass.md): the table's model and effort are exact; the session that creates a run changes nothing.
[ADR-0008](0008-a-role-session-works-to-a-subagents-depth.md),
[specs/001-chat-depth/spec.md](../../specs/001-chat-depth/spec.md).
