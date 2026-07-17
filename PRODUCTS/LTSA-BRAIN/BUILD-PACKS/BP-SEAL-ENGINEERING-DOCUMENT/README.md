# Build Pack

Product: LTSA-BRAIN
Module: SEAL-ENGINEERING-DOCUMENT
Table: seal_engineering_document
Primary Key: document_code (immutable)
Manufactured under: MWO-LTSA-030 (Mechanical Seal Knowledge Manufacturing)
Extended under: MWO-LTSA-040B (Engineering Document Acquisition)

Drawing, Datasheet, Installation Guide, Inspection Sheet, Maintenance
Manual, Service Bulletin, and Engineering Specification are Engineering
Documents that must be linked to both a Mechanical Seal (`seal_code`, FK to
`BUILD-PACKS/BP-SEAL`'s `seal_registry`) and a Knowledge Source
(`knowledge_source_id`, FK to `BUILD-PACKS/BP-KNOWLEDGE-SOURCE`'s
`knowledge_source_registry`, MWO-LTSA-040A) — not an independent product and
not generic document management (Architecture Decision, MWO-LTSA-030 items
6-7). `document_type` is a closed set of seven named types, enforced both by
the Create workflow's input validation and by a database CHECK constraint.
`file_reference` is a pointer/path field, not a storage backend.

`knowledge_source_id` is required by every Create request (workflow-layer
validation) but stored as a nullable column with an FK, not a database-level
`NOT NULL`, so this table's schema can be safely altered without assuming
whether a live deployment already has pre-040B rows (MWO-LTSA-040B WP-000
design decision 3).

**Engineering Documents are immutable.** The Update workflow permits
changing only `status` — a lifecycle marker, not part of a document's
substantive identity. A new revision of a document must be registered as a
brand-new `document_code` row via Create, never as a mutation of an
existing one (MWO-LTSA-040B Business Rule). No other field, including
`title`, `revision`, `document_number`, or `description`, can be changed
after creation.
