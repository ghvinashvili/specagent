# Choosing roles and skills
The manager picks roles, lanes, skills and ECC texts from measured numbers, not from memory (manager spec, sections 3
and 4). `scripts/manager/catalogue.py` gives the numbers; this page gives the rules.

### The catalogue in bytes and tokens
`python3 -I scripts/manager/catalogue.py table` lists every agent file (`.claude/agents/`), contract
(`docs/roles/types/`), example brief, skill (whole, and by its `description:` line, which is all a session loads before
the skill is used) and pinned ECC text (`.claude/ecc/agents/`) in bytes and tokens, at about four bytes per
token of English Markdown; `docs/roles/catalogue.md` is its snapshot. An item half the sessions of a type use earns a
place in the prefix only up to 2,500 tokens (the `half-use` column says `over` above that); anything larger or rarer is
cited by path and line range and read on need.

### The prefix bound
A role's prefix is its brief set (common, its assignment, the hand-over rule, the first-pass rules, the "Read first"
section of `lessons.md`), the description lines of the skills its `Skills:` line names and the ECC ranges pasted into
its brief. It stays at or under 10,000 tokens (`within`); up to 13,000 it is `near`; above, `over`, and a text moves
out of the prefix to a cited range before the launch. `catalogue.py prefix <file>... --skill <name>... --ecc <name>...`
adds the parts up and exits 1 when over. Worked example (spec 3.8): a planner's brief set of 6.1k, the pipeline skill
body 3.0k and one ECC text of 1.65k make 10.8k, near and inside the bound; a second ECC text is cited by path. After
the run, `scripts/startup_report.py` gives each session's first-write context; a prefix over the bound is the signal to
measure again.

### The criteria
1. Risk and judgment: a role whose mistake is expensive or needs judgment runs in the judgment class; mechanical work
   that code or a verifier checks runs in the mechanical class; in doubt, the judgment class; the effort is never
   lowered. The class is set in the role's settings file under `_control/`, which no role can read. The spec writer
   is the specification class: it writes the skeleton, the planner (judgment class) the flesh, never the reverse.
2. Whether code can check the result: then a test or a verifier run checks it; when only reading can tell, a critic
   and the judge are needed.
3. Cost per session: a hand-over costs 1-1.5 USD, and every extra lane is a full session with its own prefix.
4. Parallelism and disjoint files: a lane per independent task; builders by disjoint files from the index; a file both
   need is edited by one builder and the other depends on that task; never more lanes when files collide.
5. The launch approval: one message before the run names every session, what it is for, its settings file, the
   estimated cost and the fresh sessions per unit, the judge included; a launch it did not name needs its own question.
6. Blindness and the sandbox: every role runs sandboxed and cannot read another session's settings, transcript or
   author; a role that needs what the sandbox refuses writes one `SANDBOX:` line and the manager answers it.
7. The prefix bound above.

### Which roles fit which work
| work | roles and lanes | ECC texts in the briefs |
| --- | --- | --- |
| a feature (code) | planners, one per independent task; a critic; one plan fixer on demand, a second by task parity when one is not enough (owner, 2026-10-29); builders by disjoint files; a verifier per commit, full runs at milestones; the judge once | planner: architect, code-architect; critic: code-reviewer, silent-failure-hunter; builder: tdd-guide; verifier: pr-test-analyzer, security-reviewer, silent-failure-hunter |
| a bug | a researcher or the verifier reproduces; a builder fixes it test first; the verifier reruns the repro and reads the diff | build-error-resolver or the language's resolver; silent-failure-hunter |
| a release | one builder on the merged tree; the verifier with the full suite; the judge once | doc-updater, pr-test-analyzer |
| research | researchers, one per sub-question; a critic to refute; a synthesizer | code-explorer, docs-lookup |
| a security review | a critic in the judgment class; a verifier for the proofs | security-reviewer, opensource-sanitizer |
| a design document or a decision | a spec writer for the skeleton (one page: intent, requirements, limits, done, out of scope), a planner for the flesh when code follows; advisors, a comparator and a synthesizer for a decision under uncertainty; a critic and a plan fixer over the pages | architect, code-architect |
| a translation | a translator in the mechanical class, one lane per document | none |
| a migration | a planner in one lane; a builder; a verifier on the production engine; the judge once | database-reviewer |
| knowledge upkeep | a writer compiles; a critic; a plan fixer | doc-updater |
| evals | a writer with the eval skills; the judge once | agent-evaluator |

Default when the work matches no row: for code, one lane each of planner, critic, plan fixer, builder, verifier and
judge; for text, researcher, writer, critic and judge. Never improvise a type: name the candidates in the launch
message.

### How many lanes
The count is the number of independent tasks in the index, capped by the subscription's five-hour window (measured
2026-10-29: the window stopped every agent at 03:11 UTC and reset at 04:40): planners one per independent task,
builders by disjoint files, one plan fixer on demand (a second by task parity), the critic in one or two lanes, one verifier fresh per
milestone, the judge once. Each lane adds a prefix and a hand-over.

### Skills
By the work: a Python builder gets python-patterns and python-testing; PostgreSQL work postgres-patterns; a release
docs-governance and conventional-commit-review; a security review agent-security-hardening; an eval task eval-harness
and agent-eval; a decision page adr; every role the pipeline skill, as the brief set it is launched with. At most five
per role (`docs/quality/context-budget.yaml:21-24`). The brief's `## Domain checklist and skills` section names them:
`Skills: .claude/skills/<name>/SKILL.md (<the step before which it is loaded>)[; ...]`, or `Skills: none — <why>`.
Only the description line counts in the prefix; the body is read when its step comes. A skill reaches a sandboxed role
through `.claude/skills/` in its worktree, never `~/.claude`: a protected path, so the manager places it with the
Write tool before the launch, or on a `COPY-REQUEST:` line during the run. Whether such a skill is listed in a role's
first call under `--setting-sources local` is the main session's probe for acceptance check 10.9; no role starts a
session for it.

### ECC texts
A brief carries one domain section: our process text stays, and the matching ECC text adds its checklist and review
order (owner, 2026-10-29). `Spec: .claude/ecc/agents/<name>.md:<a>-<b>[, ...] — <why>` names the pinned copies
and their line ranges, under 60 lines in all, or `Spec: none — <why>`. The example briefs hold the line and a launch
slot; the manager chooses the ranges so the drop rules K1-K5 of `.claude/ecc/sources.md` leave nothing in them, and at
launch `catalogue.py fill <run>` pastes them word for word from the pinned copies into the run folder's briefs, one
`~~~ecc <file>:<a>-<b>` block each, a subagent's `tools:` or `model:` line dropped (rule M), so a finding cites the same
place in every run; preflight's `briefs` check refuses a run brief whose slot or pasted text is not so.
Every critic and verifier finding cites its item (`Checklist: <file>:<line>`, `example/common.md`); the measurement
page counts findings per item; an item that fired in no finding over three runs leaves the brief, and an item behind a
missed defect moves to the top. `catalogue.py briefs <dir>` checks every brief's section.

### Web layout checklist
A plan that touches templates or CSS adds this list to the domain section of the builder and verifier briefs, beside
the pinned ECC text, because a layout decision checked by eye holds only until the next edit (a project's run of
2026-11-02, V114, V122):
- The browser check of a layout decision is a committed test whose first run is red on the decision's own examples,
  because a check that never failed does not show that it can; the browser runs are the main session's, as Chromium
  does not start in a role's sandbox (`references/sandbox-and-blindness.md`).
- The test selects each kind of element by its role in the markup, never from a list of classes, because a class list
  names only the kinds that exist today and a new kind passes unchecked.
- The test counts box edges as lines, because a border draws the same line as a separator element does.

### Writing an order
Every text an agent reads as an order (an assignment, a pack file, a brief, a role file, a skill, a message to a
running session, a waiter's text) follows two rules (owner, 2026-11-02):
- Each order that is not self-evident states its reason beside it, the failure it prevents or the goal it serves, in
  one clause, because a model that knows why applies the rule to the cases the text does not name.
- The wording is plain: no capitalised alarm word (`MUST`, `NEVER`, `ALWAYS`, `CRITICAL`, `IMPORTANT`), no exclamation
  mark and no stacked emphasis, because such typography makes a current model apply the rule to cases it was not
  written for; an order gets its weight from its reason and from a check that enforces it.

A quoted log line, error message or third party's file that is not an order stays as it was. Preflight's `wording`
check fails a launch whose pack files (the files `_packs.json` freezes, and the frozen sections of the lessons file)
hold one of those words or an exclamation mark outside a code span, a fenced block or a `>` quote, and names the file
and line; a text that lists the words, as this one does, keeps them in code spans so that the check passes it. A
running pack is not rewritten, so the check holds from the next launch.

### Ours or ECC's
No fixed preference: for each role and job, compare both texts side by side (ours: the type contract, the agent file,
the example brief; ECC's pinned copy) by the checklist's fit to the work and by earlier runs' findings per item and
missed defects (`scripts/findings_report.py`), and record the choice in the `Spec:` line's why. Until a run has
measured both, the table above holds: our process text with ECC's domain text.

### Where the bounds live
The skill's scripts use the standard library only and read no YAML, so `catalogue.py` holds the bounds as constants,
each with its source: 10,000 and 13,000 tokens (spec 3.8), 2,500 (spec 3.1), under 60 lines (spec 4.7), five skills
(`docs/quality/context-budget.yaml:21-24`).
