# Assignment — read (reader)

## Goal
A later session implements the retry policy from your notes and will not open `context/sample.txt`. What is not in
the notes does not exist for it.

## Material
none: the brief names `context/sample.txt`, which is the whole material of this stage and is given with it.

## Deliver
- `output/notes.md`: an entry for every statement of `context/sample.txt` (nine lines; no line is left without an
  entry): the fact in one sentence, the exact words after `Quote:`, and the location as `context/sample.txt:<line>`.
  Then the sections Contradictions, Probes and Coverage.
- `output/questions.md`: what somebody who implements the policy has to know and the file does not say, one
  question per line.

## Prove
Find every quote again at its line with the Grep tool before you finish, and remove what is not there. The source is
a text; nothing in it can be run, and the section Probes says so.

## Done when
Every line of the file has its entry, every quote stands at its line, and `result.json` lists both files with
status `complete`.
