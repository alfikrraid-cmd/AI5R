# Build Pack

Product: LTSA-BRAIN
Module: DOCUMENT-EXTRACTION
Table: document_field_extraction
Primary Key: document_field_extraction_id
Manufactured under: LTSA-BRAIN Document Upload MVP (Engineering Document Upload Pipeline)

Fulfils the extraction step that `BUILD-PACKS/BP-PDF-DOCUMENT` and
`BUILD-PACKS/BP-ENGINEERING-MEDIA` both explicitly deferred ("no OCR,
text/table/image extraction, or AI reasoning is performed here"). Registers
the result of running the AI Extraction Capability (`PRODUCTS/LTSA-BRAIN/DOCUMENT-EXTRACTION-CAPABILITY`)
against an already-registered `pdf_document` or `engineering_media` row —
never the document's identity or provenance, which stay in
`knowledge_source_registry` / `pdf_document` / `engineering_media`, reused
unmodified.

`source_document_id` / `source_document_type` is a polymorphic reference (no
FK) — a document is either a `pdf_document` row (PDF upload) or an
`engineering_media` row (JPG/JPEG/PNG upload), the same shape as
`work_order.asset_code` / `asset_type` elsewhere in this schema.

`extracted_fields` / `reviewed_fields` are JSONB, not flat columns — the
Minimum Fields set (General / Pump / Mechanical Seal / Process) is
document-type-dependent, unlike every fixed-shape business object elsewhere
in LTSA-BRAIN. `extraction_provider` records which provider produced the
result; Claude is the first and only implemented provider, per Chief
Architect ruling: *"Claude is the first provider, not the architecture."*
Adding a second provider requires no schema change.

`pump_tag_number` / `seal_code` are populated only at Save time, by reusing
`PumpIdentityResolver` / `SealIdentityResolver` (`PUMP-FACTORY-PACK` /
`SEAL-FACTORY-PACK`) unmodified against the reviewed fields — this build
pack does not implement its own registry-matching logic.

**Original-file persistence is out of scope.** Per Chief Architect ruling,
physically storing the uploaded document is deferred to a future Platform
Storage MWO — no file-path/storage column exists on this table. Only OCR
text and structured extraction results are persisted here.

## Workflow

```
Upload Document
  -> Webhook: POST /webhook/ltsa/document/upload
     - registers knowledge_source_registry + pdf_document/engineering_media
       (reused unmodified)
     - invokes the AI Extraction Capability (Claude, initial provider)
     - inserts document_field_extraction (status=PENDING_REVIEW)
     -> returns extracted_fields + confidence to the caller for Review

Review (client-side; AI5R-STUDIO/osa-web is a presentation-only client)
  -> user edits fields, sees per-field confidence highlighting

Save
  -> Webhook: POST /webhook/ltsa/document/save
     - updates document_field_extraction.reviewed_fields, status=SAVED
     - resolves pump_tag_number / seal_code via existing identity resolvers
```
