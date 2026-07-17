# Build Pack

Product: LTSA-BRAIN
Module: DOCUMENT-CLASSIFICATION
Table: document_classification
Primary Key: document_classification_id (immutable)
Manufactured under: MWO-LTSA-040D (Engineering PDF Acquisition)

Records one classification attempt against one PDF Document (FK to
`BUILD-PACKS/BP-PDF-DOCUMENT`'s `pdf_document`). `classification_type`
reuses the same 11-value closed set as `pdf_document.document_type` — no
separate classification taxonomy is named anywhere in the original work
order; its job is to assign a PDF to one of the Supported PDF Types.

**Repeatable by design** — "PDF Classification must be repeatable"
(Business Rule) is satisfied by allowing multiple classification rows
against the same `pdf_document_id`, not by mutating one row (same
reasoning as `acquisition_job`, 040C). Unlike `pdf_metadata`, no `UNIQUE`
constraint on `pdf_document_id`.

Create/List/Detail only, no Update or Delete — repeatability is achieved
via new rows, not by editing an existing classification's `status`/
`confidence` after the fact; no rule describes a confirm/reject lifecycle
for an existing row.

This build pack performs no OCR, AI reasoning, or content analysis —
`classification_type`/`confidence`/`status` are caller-supplied, the same
convention as every other acquisition workflow in this product.
