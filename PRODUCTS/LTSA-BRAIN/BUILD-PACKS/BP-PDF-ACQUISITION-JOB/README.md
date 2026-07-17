# Build Pack

Product: LTSA-BRAIN
Module: PDF-ACQUISITION-JOB
Table: pdf_acquisition_job
Primary Key: pdf_acquisition_job_id
Manufactured under: MWO-LTSA-040D (Engineering PDF Acquisition)

The job-log record of one acquisition attempt against one PDF Document
(`pdf_document_id`, FK to `BUILD-PACKS/BP-PDF-DOCUMENT`'s `pdf_document`)
originating from one Knowledge Source (`knowledge_source_id`, FK to
`BUILD-PACKS/BP-KNOWLEDGE-SOURCE`'s `knowledge_source_registry`) — both
FKs are named attributes of "PDF Acquisition Job" in the original work
order's own Business Objects section, not inferred.

`status` (`PENDING`/`IN_PROGRESS`/`COMPLETED`/`FAILED`) is adapted from
`acquisition_job.status` (040C: `PENDING`/`IN_PROGRESS`/`READY_FOR_
MANUFACTURING`/`FAILED`), with `READY_FOR_MANUFACTURING` replaced by
`COMPLETED` because this MWO's own Out of Scope excludes "Engineering
Object Manufacturing" — this is the one part of this table's design most
likely to need revision once a real acquisition workflow runs against it,
flagged here, not hidden.

Create/List/Detail/Update — no Delete. "PDF Acquisition must be
repeatable" (Business Rule) is satisfied by allowing multiple job rows
against the same (knowledge_source_id, pdf_document_id) pair, not by
deleting and retrying one row. Update permits only `status`,
`finished_at`, `validation_errors` — `knowledge_source_id`,
`pdf_document_id`, and `started_at` are fixed at Create time.

This build pack does not parse PDF files, perform OCR, or write to any
canonical business-object table — a `COMPLETED` job records that a PDF is
registered, classified, and validated; extraction of any kind is deferred
to future MWOs (MWO-LTSA-046 through 049).
