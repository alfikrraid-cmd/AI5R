-- document_field_extraction
--
-- Manufactured under MWO-LTSA-Document-Upload-MVP (Engineering Document
-- Upload Pipeline: Upload -> OCR -> AI Field Extraction -> Review -> Save).
--
-- Fulfils the extraction step explicitly deferred by
-- BUILD-PACKS/BP-PDF-DOCUMENT and BUILD-PACKS/BP-ENGINEERING-MEDIA ("no OCR,
-- text/table/image extraction, or AI reasoning is performed here... deferred
-- to future MWOs"). Does NOT re-register document identity or provenance --
-- those remain BP-KNOWLEDGE-SOURCE (knowledge_source_registry),
-- BP-PDF-DOCUMENT (pdf_document), and BP-ENGINEERING-MEDIA
-- (engineering_media), reused unmodified. This table adds exactly one new
-- capability output: the AI Extraction Capability's result against an
-- already-registered document.
--
-- source_document_id / source_document_type is a polymorphic reference
-- (no FK), the same pattern already used by work_order.asset_code /
-- asset_type in this schema -- a document may be a pdf_document (PDF
-- upload) or an engineering_media asset (JPG/JPEG/PNG upload), two separate
-- tables with no common supertype.
--
-- extracted_fields is the AI Extraction Capability's normalized output
-- (per-field {value, confidence} pairs for the MVP's Minimum Fields set:
-- General/Pump/Mechanical Seal/Process). reviewed_fields is the same shape
-- after a human reviews and edits it in the Review screen; NULL until
-- status advances past PENDING_REVIEW. JSONB (not flat columns) is used
-- deliberately here -- unlike every other table in this schema, the field
-- set is genuinely provider- and document-type-dependent, not a fixed
-- business-object shape.
--
-- extraction_provider records which AI Extraction Capability provider
-- produced the result (Claude is the first and only provider implemented;
-- the column exists so a future provider requires no schema change).
--
-- pump_tag_number / seal_code are nullable and are populated only at Save
-- time, by reusing PumpIdentityResolver / SealIdentityResolver
-- (SEAL-FACTORY-PACK, PUMP-FACTORY-PACK) unmodified against the reviewed
-- fields -- this table does not implement its own matching logic.
--
-- Per Chief Architect ruling: original file persistence (the physical
-- uploaded document) is explicitly OUT OF SCOPE for this MWO and deferred to
-- a future Platform Storage MWO. This table stores only OCR text and
-- structured extraction results -- no file-path/storage column is added
-- here. knowledge_source_registry.file_hash/file_size already capture
-- upload-time file identity metadata without a physical storage location.

CREATE TABLE IF NOT EXISTS public.document_field_extraction (
    document_field_extraction_id TEXT PRIMARY KEY NOT NULL,
    source_document_id TEXT NOT NULL,
    source_document_type TEXT NOT NULL,
    detected_document_type TEXT NOT NULL,
    detected_document_type_confidence NUMERIC,
    extraction_provider TEXT NOT NULL DEFAULT 'claude',
    ocr_text TEXT,
    extracted_fields JSONB NOT NULL DEFAULT '{}'::jsonb,
    reviewed_fields JSONB,
    status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
    pump_tag_number VARCHAR(100) REFERENCES public.ltsa_pumps(tag_number),
    seal_code TEXT REFERENCES public.seal_registry(seal_code),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT document_field_extraction_source_type_check
        CHECK (source_document_type IN ('PDF', 'MEDIA')),
    CONSTRAINT document_field_extraction_detected_type_check
        CHECK (detected_document_type IN (
            'MECHANICAL_SEAL_INSTALLATION_REPORT', 'PUMP_DATASHEET',
            'MECHANICAL_SEAL_DRAWING', 'PUMP_DRAWING', 'NAMEPLATE', 'UNKNOWN'
        )),
    CONSTRAINT document_field_extraction_status_check
        CHECK (status IN ('PENDING_REVIEW', 'REVIEWED', 'SAVED')),
    CONSTRAINT document_field_extraction_confidence_check
        CHECK (detected_document_type_confidence IS NULL
            OR (detected_document_type_confidence >= 0 AND detected_document_type_confidence <= 1))
);
