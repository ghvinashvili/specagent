---
title: Content-hash deduplication
type: concept
status: verified
updated: "2026-09-28"
expires: "2027-03-28"
sources:
  - sources/ingest-samples.md
related:
  - entities/ingest-package.md
---
# Content-hash deduplication

A file whose content hash already exists in the store is skipped at ingest
([Ingest samples](../sources/ingest-samples.md), `context/ingest-samples/README.md:4`).
The package that applies the rule is the [ingest package](../entities/ingest-package.md).

## Open points
- The samples do not say what happens when the hash matches and the file name differs (uncertain).
