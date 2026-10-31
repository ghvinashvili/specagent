# vault

Your second brain: the rules, decisions and process knowledge that outlive any one project, read by every project's
Claude sessions before they start. Private: one copy, kept in git and pushed only to a private repository of your own.
Made by `ops/new-vault.py` of the template, which drew the `origin` id in this file's frontmatter: the commons knows
your pages by that id, never by a name.

```text
INDEX.md                 start here: one line per page, grouped; never scan the directory
rules.md                 how pages are written (one page per decision, sources named, nothing silently rewritten)
log.md                   one line per change of the compiled pages
decisions/global/        your rules and decisions that apply to every project, one per page
decisions/<domain>/      rules for every project of one domain (`scope: <domain>`), one per page
concepts/                process knowledge: how pipelines run, what was measured, what failed and why
entities/                one page per project (with the path of its own wiki)
sources/                 one page per raw source, saying what it is and which pages it fed
context/                 raw material, copied verbatim and not edited (context/README.md, built by ops/build_indexes.py)
  owner-statements/      what you said and decided, one file per day or per decision
  measurements/          what was measured, how, and the numbers: the evidence a decision cites
  memory/<dir>/          Claude Code memory files (ops/collect_memory.py, secret filter); <dir> = where sessions ran
ops/                     outline.py, check_pages.py, split_large.py, build_indexes.py, collect_memory.py
forms/manager-lessons.md the main session's lessons page; copied once to decisions/global/ (rules.md)
forms/learning-record.md the shape of one learning record and the rule that promotes it (rules.md)
```

Pages are written in English, the language the agents read. Project decisions do not live here: they live in the
project's `wiki/decisions/`; a decision that holds for every project comes here.

## The commons

`INDEX.md` names `commons_path`: a clone of the public commons, where the global decisions and lessons of the
template's users meet by pull request. It is a source, not an authority: when a commons page and a page here disagree,
the page here wins and the disagreement goes back to the commons as a finding. A page of `decisions/global/` or
`concepts/` goes there only with your yes, by `python3 ops/contribute.py <page> [<evidence> ...]` in a project made
from the template; the script refuses private material in code (`rules.md`, "Sharing with the commons").
