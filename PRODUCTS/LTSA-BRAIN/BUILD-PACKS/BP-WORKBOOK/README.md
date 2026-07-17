# Build Pack

Product: LTSA-BRAIN
Module: WORKBOOK
Table: workbook
Primary Key: workbook_id (immutable)
Manufactured under: MWO-LTSA-040C (Universal Tabular Data Acquisition)

Part of the Universal Acquisition Infrastructure — registers a tabular
source file's identity, never its content. Every Workbook must originate
from exactly one Knowledge Source (`knowledge_source_id`, FK to
`BUILD-PACKS/BP-KNOWLEDGE-SOURCE`'s `knowledge_source_registry`), the
canonical owner of file provenance. `workbook_type` is a closed set of the
11 Supported Workbook Types, validated generically (an allow-list, never a
per-type parser — Architecture Decision item 7).

**Original Workbook must never be modified** — no Update or Delete
workflow exists for this table. Only Create, List, Detail.

This build pack does not parse Excel files or write to any canonical
business-object table (`ltsa_pumps`, `seal_registry`, etc.) — per
Architecture Decision items 1/5/6, a Workbook registration is metadata
only. Object manufacturing from an acquired workbook is deferred to future
MWOs consuming `acquisition_job`.
