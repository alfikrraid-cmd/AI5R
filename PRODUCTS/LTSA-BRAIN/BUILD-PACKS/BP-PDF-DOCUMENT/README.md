# Build Pack

Product: LTSA-BRAIN
Module: PDF-DOCUMENT
Table: pdf_document
Primary Key: pdf_document_id (immutable)
Manufactured under: MWO-LTSA-040D (Engineering PDF Acquisition)

Registers an engineering PDF's identity, never its content — no OCR, no
text/table/image extraction, no AI reasoning. Every PDF Document must
originate from exactly one Knowledge Source (`knowledge_source_id`, FK to
`BUILD-PACKS/BP-KNOWLEDGE-SOURCE`'s `knowledge_source_registry`), the
canonical owner of file provenance. `document_type` is a closed set of the
11 Supported PDF Types, validated generically (an allow-list, never a
per-type parser).

This table is parallel to, not an extension of, `seal_engineering_document`
(MWO-LTSA-040B) — this MWO's own Business Rule requires only a Knowledge
Source link, not a Mechanical Seal link, and MWO-LTSA-040A's own roadmap
already treats "040D connects PDF Acquisition" as its own distinct
connection point, the same way MWO-LTSA-040C ("Excel Acquisition") built
its own `workbook` family rather than retrofitting `seal_engineering_document`.

**Original PDF must never be modified** — no Update or Delete workflow
exists for this table. Only Create, List, Detail.

This build pack does not parse PDF files, extract content, or write to any
canonical business-object table — a PDF Document registration is metadata
only. Classification is a separate, repeatable child object
(`BUILD-PACKS/BP-DOCUMENT-CLASSIFICATION`); extraction of any kind is
deferred to future MWOs (MWO-LTSA-046 through 049).
