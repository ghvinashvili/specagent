---
title: Ingest samples
type: source
status: verified
updated: "2026-09-28"
source_kind: data
raw:
  - context/ingest-samples/README.md
---
# Ingest samples

`context/ingest-samples/` holds sample files for the dedupe rule. `README.md:2` names the package that reads them;
`README.md:4` states the rule: a file whose content hash is already stored is skipped.
