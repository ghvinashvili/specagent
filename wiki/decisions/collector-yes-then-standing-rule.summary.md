Decision (owner, 2026-10-29): the collector deletes on the owner's yes for three runs, then by a standing rule.
collect_run.py's dry run lists a finished run's leftovers with the list's digest.
For three runs it deletes only with --apply --yes <digest>, the owner's yes for that exact list.
Then --apply alone deletes, and the owner reads collected.md in the run folder afterwards.
