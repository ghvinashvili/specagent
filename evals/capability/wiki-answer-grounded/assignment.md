# Assignment — research (researcher)

## Goal
The answer is read by somebody who will change how `ingest` skips files and who trusts a statement only as far as
its source goes. They will open the lines you cite, and nothing else.

## Material
none: the brief names the material of the question, and it is given with the brief.

## Deliver
- `output/findings.md`: the answer to the brief's question as a list, one statement per item. Every statement ends
  with the place in the raw material that says it, as `context/ingest-samples/<file>:<line>`, and names the wiki
  page it was found through (`wiki/concepts/...`, `wiki/entities/...` or `wiki/sources/...`).
- `output/questions.md`: what the question needs and neither the wiki nor the raw material answers.

## Prove
Start from `wiki/index.md`, follow the pages to the sources they cite, and open every cited line yourself: a
statement a page makes and its source does not support is reported as such, not repeated. Before you finish,
re-open every location you cite.

## Done when
Every condition under which a file is skipped has its statement with a source line, statements the sources do not
support are named, and `result.json` lists both files with status `complete`.
