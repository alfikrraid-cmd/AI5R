-- MWO-LTSA-DRAWING-INPUT-R5A -- additive ingestion-foundation schema
-- approved in DRAWING_R5_INGESTION_DESIGN / DRAWING_R5A0_STORAGE_AUTHORITY.
-- Three additive changes only. Migration 038 is NOT modified.
--
-- 1) knowledge_source_registry gains one nullable object_storage_key
--    column -- the MinIO content-addressed key (<sha256>/<extension>,
--    computed and generated entirely at the application layer; this
--    migration never generates, infers, or backfills a key for any
--    existing row). No bucket column is added: R5A0's own MinIO
--    configuration audit found no existing bucket-name convention
--    anywhere in this stack, so a single canonical application-
--    configured bucket (an environment-level fact, decided in a later
--    application-code phase, R5B) is the correct authority -- not a
--    per-row DB fact. No presigned URL, raw filesystem path, or MinIO
--    credential is ever stored here (R5A0's own explicit prohibition).
--    NOT globally UNIQUE: R5A0 explicitly established that the same
--    binary object may legitimately have multiple provenance rows (two
--    different people/moments supplying byte-identical files) -- a
--    unique constraint here would wrongly forbid that.
--
-- 2) document_field_extraction.detected_document_type gains one new
--    value, 'ENGINEERING_DRAWING_CANDIDATE', alongside its 8 existing
--    values (PUMP_DRAWING/MECHANICAL_SEAL_DRAWING included, both left
--    completely untouched -- narrower, pump/seal-specific values from an
--    earlier MWO; Drawing-R5 ingestion is intentionally broader, per
--    Drawing-R1's own 'not pump-only' rule). CHECK constraint DROP/ADD
--    (not a DO-block) -- the same idempotent-upgrade-path convention
--    CANONICAL_SCHEMA.sql's own seal_engineering_document_type_check
--    already uses for exactly this kind of enum-widening. No row is
--    updated by this migration.
--
-- 3) engineering_drawing_attribute -- REVIEWED engineering facts with
--    field-level provenance (attribute_concept/value/unit/source_label/
--    source_location/source_artifact_code), reusing the exact
--    knowledge_source_registry verification_status vocabulary. This is
--    explicitly NOT raw AI extraction (document_field_extraction.
--    extracted_fields remains that, untouched, forever immutable
--    evidence) -- only a human-reviewed correction/confirmation is ever
--    written here.
--
-- attribute_concept is deliberately open TEXT with NO CHECK vocabulary
-- (R5A Section 11's own explicit instruction) -- future drawings will
-- introduce engineering facts beyond the 18 concepts already identified
-- in R5's own design; a closed enum would force a migration every time,
-- defeating the point.
--
-- source_artifact_code integrity mirrors migration 038's own
-- current_revision_code technique exactly: a plain single-column FK to
-- engineering_drawing_revision_artifact.artifact_code cannot prove the
-- artifact belongs to the SAME revision_code as the attribute -- a
-- composite FK against a new UNIQUE(revision_code, artifact_code) on
-- that table does. NULL source_artifact_code always trivially satisfies
-- the composite FK (Postgres MATCH SIMPLE, the default) -- a manually
-- entered verified fact with no traceable single source artifact
-- remains valid (R5A's own explicit allowance).
--
-- reviewed_by/reviewed_at are DB-enforced to be present whenever
-- verification_status is VERIFIED/CANONICAL -- safe to add here (unlike
-- retrofitting document_field_extraction's own already-populated
-- historical rows, which this migration never touches) because this is
-- a brand-new, currently-empty table with no legacy data or existing
-- code path to conflict with.
--
-- No UNIQUE(revision_code, attribute_concept): a drawing can legitimately
-- carry multiple facts under the same concept (multiple ports, DE/NDE
-- measurement pairs, multiple dimensions of the same family) -- R5A's
-- own explicit instruction. A future service/catalog layer may add
-- semantic keys (side/position) if ever needed; not this migration.
--
-- Delete policy: revision -> attribute = RESTRICT, artifact -> attribute
-- = RESTRICT (via the composite FK) -- reviewed engineering facts are
-- never CASCADE-deleted away, matching migration 038's own "never lose
-- history" discipline exactly.

ALTER TABLE public.knowledge_source_registry
    ADD COLUMN IF NOT EXISTS object_storage_key TEXT;

CREATE INDEX IF NOT EXISTS idx_knowledge_source_registry_object_storage_key
    ON public.knowledge_source_registry(object_storage_key) WHERE object_storage_key IS NOT NULL;

ALTER TABLE public.document_field_extraction
    DROP CONSTRAINT IF EXISTS document_field_extraction_detected_type_check;
ALTER TABLE public.document_field_extraction
    ADD CONSTRAINT document_field_extraction_detected_type_check
    CHECK (detected_document_type IN (
        'MECHANICAL_SEAL_INSTALLATION_REPORT', 'PUMP_DATASHEET',
        'MECHANICAL_SEAL_DRAWING', 'PUMP_DRAWING', 'NAMEPLATE', 'UNKNOWN',
        'HISTORICAL_PM_OCCURRENCE_CANDIDATE', 'HISTORICAL_CMON_READING_CANDIDATE',
        'HISTORICAL_FINDING_CANDIDATE', 'ENGINEERING_DRAWING_CANDIDATE'
    ));

-- Idempotent guard (mirrors migration 038's own current_revision_fkey
-- convention) -- Postgres has no ADD CONSTRAINT IF NOT EXISTS.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.engineering_drawing_revision_artifact'::regclass
          AND conname = 'engineering_drawing_revision_artifact_revision_unique'
    ) THEN
        ALTER TABLE public.engineering_drawing_revision_artifact
            ADD CONSTRAINT engineering_drawing_revision_artifact_revision_unique
            UNIQUE (revision_code, artifact_code);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.engineering_drawing_attribute (
    attribute_code       TEXT PRIMARY KEY NOT NULL,
    revision_code        TEXT NOT NULL REFERENCES public.engineering_drawing_revision(revision_code) ON DELETE RESTRICT,
    source_artifact_code TEXT,
    attribute_concept    TEXT NOT NULL,
    source_label         TEXT,
    value_numeric        NUMERIC,
    value_text           TEXT,
    unit                 TEXT,
    source_location      TEXT,
    verification_status  TEXT NOT NULL DEFAULT 'DRAFT'
        CHECK (verification_status IN ('DRAFT', 'UNDER_REVIEW', 'VERIFIED', 'CANONICAL')),
    reviewed_by          UUID,
    reviewed_at          TIMESTAMP,
    notes                TEXT,
    created_at           TIMESTAMP DEFAULT NOW(),
    created_by           UUID,
    updated_at           TIMESTAMP DEFAULT NOW(),
    updated_by           UUID,
    CONSTRAINT engineering_drawing_attribute_value_check
        CHECK (value_numeric IS NOT NULL OR value_text IS NOT NULL),
    CONSTRAINT engineering_drawing_attribute_reviewed_metadata_check
        CHECK (verification_status NOT IN ('VERIFIED', 'CANONICAL')
            OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)),
    CONSTRAINT engineering_drawing_attribute_source_artifact_same_revision
        FOREIGN KEY (revision_code, source_artifact_code)
        REFERENCES public.engineering_drawing_revision_artifact(revision_code, artifact_code)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_engineering_drawing_attribute_revision_code
    ON public.engineering_drawing_attribute(revision_code);
CREATE INDEX IF NOT EXISTS idx_engineering_drawing_attribute_source_artifact_code
    ON public.engineering_drawing_attribute(source_artifact_code) WHERE source_artifact_code IS NOT NULL;

-- Rollback (manual, not executed by this file -- forward-only migration
-- convention already established in this directory):
--
--   DROP TABLE IF EXISTS public.engineering_drawing_attribute;
--   ALTER TABLE public.engineering_drawing_revision_artifact
--       DROP CONSTRAINT IF EXISTS engineering_drawing_revision_artifact_revision_unique;
--   ALTER TABLE public.document_field_extraction
--       DROP CONSTRAINT IF EXISTS document_field_extraction_detected_type_check;
--   ALTER TABLE public.document_field_extraction
--       ADD CONSTRAINT document_field_extraction_detected_type_check
--       CHECK (detected_document_type IN (
--           'MECHANICAL_SEAL_INSTALLATION_REPORT', 'PUMP_DATASHEET',
--           'MECHANICAL_SEAL_DRAWING', 'PUMP_DRAWING', 'NAMEPLATE', 'UNKNOWN',
--           'HISTORICAL_PM_OCCURRENCE_CANDIDATE', 'HISTORICAL_CMON_READING_CANDIDATE',
--           'HISTORICAL_FINDING_CANDIDATE'
--       ));
--   ALTER TABLE public.knowledge_source_registry DROP COLUMN IF EXISTS object_storage_key;
--
-- Safe only if no row has been given detected_document_type =
-- 'ENGINEERING_DRAWING_CANDIDATE' or a populated object_storage_key
-- since this migration ran -- check before rolling back.
