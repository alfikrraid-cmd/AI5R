-- MWO-LTSA-INSTALLATION-REPORT-INGESTION-001 -- closes the provenance gap
-- on the existing, already-committed document_field_extraction table (the
-- canonical AI-extraction/human-review staging table this MWO's
-- Installation Report ingestion contract reuses instead of inventing a
-- parallel review table). Every other required provenance field --
-- source_document_id, extracted_value (extracted_fields), confidence
-- (detected_document_type_confidence / per-field confidence inside
-- extracted_fields, matching AI-EXTRACTION/models.py's own FieldValue(
-- value, confidence) shape), review_status (status) -- already existed.
--
-- source_page: which page of a multi-page scan a field was read from.
-- reviewed_by: the reviewing user's id (auth foundation, migration 007),
-- but carries NO database-level FK -- no table in CANONICAL_SCHEMA.sql's
-- own engineering-domain bootstrap references public.users (only
-- migration 007 creates it, as a separate step; a hard FK here would
-- break --bootstrap-schema on a fresh database). Same "informal
-- reference, resolved at the application layer" convention
-- pm_schedule.asset_code/installation_report.plant_equip_no already
-- establish -- never a free-text name, just no DB-level FK.
-- reviewed_at: when the human review decision was made.
-- REJECTED: a genuinely new terminal status. A human reviewer determining
-- a draft is unusable (duplicate, illegible, wrong document) previously
-- had no terminal state distinct from PENDING_REVIEW/REVIEWED. No code
-- path promotes a REJECTED row to any canonical table.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS is a no-op on a table that already
-- has these columns; the CHECK constraint is dropped and re-added with
-- its final definition every run, which is itself idempotent (DDL, not
-- data), so re-running this file is always safe.

ALTER TABLE public.document_field_extraction ADD COLUMN IF NOT EXISTS source_page INTEGER;
ALTER TABLE public.document_field_extraction ADD COLUMN IF NOT EXISTS reviewed_by UUID;
ALTER TABLE public.document_field_extraction ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP;

ALTER TABLE public.document_field_extraction DROP CONSTRAINT IF EXISTS document_field_extraction_status_check;
ALTER TABLE public.document_field_extraction ADD CONSTRAINT document_field_extraction_status_check
    CHECK (status IN ('PENDING_REVIEW', 'REVIEWED', 'SAVED', 'REJECTED'));
