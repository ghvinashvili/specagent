---
status: accepted
date: 2026-10-02
decision-makers: platform team
consulted: harness maintainers
informed: all package owners
---

# A role session works to a subagent's depth: its instruction with its task, its whole material, its own compaction point

## Context and Problem Statement
ADR-0006 gave a role session every demand a subagent would get. A measured stage showed that the same demands do not
yet give the same work. One reader stage ran twice from the same commit, on the same model (Sonnet 5.5) at the same
effort (`high`, recorded in both transcripts), with the same assignment and the same gate: once as a role session,
once as a subagent whose prompt was built from the role session's own files. Of 267 lines of instruction, 5 differed,
all about the prompt cache: the role session had its material in the cache, the subagent read it from the files.

| | role session | subagent |
| --- | --- | --- |
| time, price | 5.1 minutes, 1.35 $ | 12.2 minutes, 3.07 $ |
| quotes, all at their lines | 208 | 431 |
| probes | 2 | 8, among them the project's checks before a change |
| thinking | about 38,000 characters | about 173,000 characters |

The role session did what its assignment named and passed its gate. It skipped steps of its type's method that the
subagent took on its own: the checks before a change, the probes of edge cases. The difference that remained was where
the instruction stood: the role session had its type's instruction only in its system prompt, the subagent had it in
its task, under a system prompt of its own that asks it to complete the task fully and to be thorough. An earlier run
showed a second gap: the human's `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` of 60 reached role sessions through the environment
of the background service, and a role session was compacted three times where a subagent was compacted once.

The human's demand: a role session works to the detail a subagent works to, every source extracted in every direction
the plan names, and it neither searches for its material nor misses any of it.

## Decision Drivers
* Depth equal to a subagent's on the same job, kept by text and by gates, not left to chance.
* The whole material of a job in the prompt: nothing to search for, nothing missed, whatever its size.
* The prompt cache stays: sessions of one type share their system prompt.
* Nothing of the human's own settings reaches a role session.

## Considered Options
* Leave the instruction in the system prompt only.
* The type's instruction and the role rules also in the first message, with the task, as a subagent receives them.
* Move the instruction out of the agent file into the first message.
* A gate check for every step of every method.
* Compress the material further before it is cached.

## Decision Outcome
Chosen option: "The type's instruction and the role rules also in the first message", because it puts them where a
subagent has them and changes nothing a session of the type shares in the cache. With it:
* `prompt.md` begins with the type's instruction (the agent file without its frontmatter) and the role rules, then the
  brief, the assignment, the stage and the inputs. The system prompt is as before.
* The role rules carry what a subagent's own system prompt asks of it: complete the task fully, without gold-plating
  and without leaving it half-done; be thorough; every step of the type's method is part of the task.
* The material is given whole up to half the model's window: 2,000,000 characters, about 500,000 tokens, on a
  1,000,000-token window; 320,000 on haiku, whose window is 200,000 tokens (`pack.budget`). The budget is a ceiling,
  not a size: a stage gets what its brief and assignment name. What does not fit is named before the launch by
  `harness material`, and the manager splits the stage instead of letting it search.
* Every role session accounts for every file of its material, whatever its type: the file heads a section of its
  output, or it has its row in the output's Coverage (a section `Coverage` or `output/coverage.md`) saying what was
  taken from it and where it went, or why it holds nothing for the task. The checks every gate makes
  (`gates.common_checks`) fail a file that no output names. Having the material in the prompt is not using it; the
  gate checks the use.
* Whatever a stage's texts list is in its prompt: `harness launch` refuses a stage whose listed material does not
  fit (`material_does_not_fit`), and the manager splits it or narrows its assignment. A file that is not text (an
  image, a PDF) cannot be in the prompt; the material names it for the session to open with Read, and it is
  accounted for like any other file.
* The effort of a stage follows the work: the table's value is the default, and a hard run raises the stages whose
  output decides (`harness run --effort <stage>=max`). Measured on the reader stage above, `max` found every fact
  and five contradictions where `high` missed one fact and wrote half the quotes, at four times the price.
* A role session compacts where Claude Code compacts on its own: `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` is `100` in its
  settings (the window less Claude Code's reserve). The human's own sessions keep their setting.
* The material stays as `pack.material` frames it: every line after its number, an empty line left out with its
  number. Measured on the material of the stage above, this is 7 % longer than the files themselves; the numbers are
  what keeps every quote at its line. Shorter forms either lose text or make the session count lines, which moves
  quotes off their lines, so nothing is compressed further.

### Consequences
* Good, because the method of the type stands with the task, where a subagent's stands.
* Good, because no file of the material can be passed over in silence.
* Good, because a role session is compacted only where its window ends, and its material survives a compaction in
  the system prompt.
* Bad, because the first message is longer by the instruction and the rules (about 14,000 characters for a reader),
  read from the cache on every request.
* Bad, because every request reads the whole material and the whole conversation again: a large material and a long
  conversation make each request dearer. Quality comes first here; `harness cache-report` shows the price.
* Neutral: that the role session now reaches a subagent's depth is not yet measured. The next measurement repeats the
  stage above for the role session alone and compares it with the subagent's result.

### Confirmation
`packages/harness/tests/test_assign.py` checks that the first message begins with the instruction and the rules
before the brief; `test_access.py` the budget per model and the compaction setting of a role session;
`test_gates.py` that the gate of any stage fails a file of the material that no output heads or covers.

## More Information
[ADR-0003](0003-brief-as-first-message.md), [ADR-0004](0004-rules-and-pack-in-the-system-prompt.md),
[ADR-0006](0006-a-role-session-gets-what-a-subagent-would-get.md). A type that cannot write a file accounts for no
material: [ADR-0012](0012-a-type-that-cannot-write-accounts-for-no-material.md).
