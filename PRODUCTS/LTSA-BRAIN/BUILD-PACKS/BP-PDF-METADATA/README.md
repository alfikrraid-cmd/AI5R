# Build Pack

Product: LTSA-BRAIN
Module: PDF-METADATA
Table: pdf_metadata
Primary Key: pdf_metadata_id (immutable)
Manufactured under: MWO-LTSA-040D (Engineering PDF Acquisition)

Records one PDF Document's own container-level properties (`title`,
`author`, `producer`, `creation_date`, `modification_date`, `pdf_version`)
— standard PDF document properties, not extracted body content. A single
PDF file has exactly one set of these properties at a time, so
`pdf_document_id` carries a `UNIQUE` constraint (`pdf_metadata_pdf_
document_id_unique`) — one row per `pdf_document` (FK to
`BUILD-PACKS/BP-PDF-DOCUMENT`'s `pdf_document`), unlike Worksheet (040C),
which has no such cardinality limit.

Create/List/Detail only, no Update or Delete — recorded once at
acquisition time as a structural fact about the source file, the same
immutability class as `worksheet` (040C).

This build pack does not parse PDF files or extract text/table/image
content — every field is caller-supplied metadata, the same convention as
every other acquisition workflow in this product.
