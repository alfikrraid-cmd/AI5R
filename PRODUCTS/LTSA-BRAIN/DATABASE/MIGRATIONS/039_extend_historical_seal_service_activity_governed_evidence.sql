-- LTSA_HISTORICAL_INSTALLATION_2024_2025_IMPORT_IMPLEMENTATION_R1
-- Additive extension of public.historical_seal_service_activity (migration 036)
-- so it can hold GOVERNED historical mechanical-seal installation evidence
-- imported from an approved, hash-frozen manifest.
--
-- ADDITIVE ONLY: no column is dropped, renamed or retyped; migration 036's
-- columns and principles (history only, never Current Installation; finish
-- date as the event date; conservative asset matching; idempotent source
-- keys) are preserved.
--
-- New semantics:
--   * provenance: source_hash, source_fingerprint (sha256 of source file hash,
--     sheet, row), historical_event_id, event_fingerprint, import_manifest_sha256,
--     imported_at
--   * position (DE / NDE / PUMP_LEVEL) with the same-row evidence text
--   * dates: source_date_raw (cell as found), parsed_source_date, and an
--     approved corrected_event_date (DAY_MONTH_SWAP) - event_date must equal
--     the corrected date when a correction is approved
--   * evidence_grade (DIRECT_EVIDENCE / CORROBORATED), deduplication_status
--   * event_type restricted to INSTALLATION / REINSTALLATION_REFURBISHED_SEAL
--   * APPEND-ONLY: UPDATE, DELETE and TRUNCATE are rejected by triggers. The
--     only way to remove the protection is the documented rollback below.

BEGIN;

ALTER TABLE public.historical_seal_service_activity
    ADD COLUMN IF NOT EXISTS historical_event_id TEXT,
    ADD COLUMN IF NOT EXISTS source_hash TEXT,
    ADD COLUMN IF NOT EXISTS source_fingerprint TEXT,
    ADD COLUMN IF NOT EXISTS event_fingerprint TEXT,
    ADD COLUMN IF NOT EXISTS position TEXT NOT NULL DEFAULT 'PUMP_LEVEL',
    ADD COLUMN IF NOT EXISTS position_source_raw TEXT,
    ADD COLUMN IF NOT EXISTS position_extraction_reason TEXT,
    ADD COLUMN IF NOT EXISTS source_date_raw TEXT,
    ADD COLUMN IF NOT EXISTS parsed_source_date DATE,
    ADD COLUMN IF NOT EXISTS corrected_event_date DATE,
    ADD COLUMN IF NOT EXISTS date_correction_status TEXT,
    ADD COLUMN IF NOT EXISTS date_correction_reason TEXT,
    ADD COLUMN IF NOT EXISTS evidence_grade TEXT,
    ADD COLUMN IF NOT EXISTS deduplication_status TEXT,
    ADD COLUMN IF NOT EXISTS import_manifest_sha256 TEXT,
    ADD COLUMN IF NOT EXISTS imported_at TIMESTAMPTZ;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'hssa_historical_event_id_key') THEN
        ALTER TABLE public.historical_seal_service_activity
            ADD CONSTRAINT hssa_historical_event_id_key UNIQUE (historical_event_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'hssa_source_fingerprint_key') THEN
        ALTER TABLE public.historical_seal_service_activity
            ADD CONSTRAINT hssa_source_fingerprint_key UNIQUE (source_fingerprint);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'hssa_position_check') THEN
        ALTER TABLE public.historical_seal_service_activity
            ADD CONSTRAINT hssa_position_check CHECK (position IN ('DE', 'NDE', 'PUMP_LEVEL'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'hssa_evidence_grade_check') THEN
        ALTER TABLE public.historical_seal_service_activity
            ADD CONSTRAINT hssa_evidence_grade_check
            CHECK (evidence_grade IS NULL OR evidence_grade IN ('DIRECT_EVIDENCE', 'CORROBORATED'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'hssa_date_correction_status_check') THEN
        ALTER TABLE public.historical_seal_service_activity
            ADD CONSTRAINT hssa_date_correction_status_check
            CHECK (date_correction_status IS NULL OR date_correction_status IN ('NOT_REQUIRED', 'APPROVED'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'hssa_approved_correction_check') THEN
        ALTER TABLE public.historical_seal_service_activity
            ADD CONSTRAINT hssa_approved_correction_check
            CHECK (date_correction_status IS DISTINCT FROM 'APPROVED'
                   OR (corrected_event_date IS NOT NULL AND date_correction_reason IS NOT NULL
                       AND event_date = corrected_event_date));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'hssa_event_type_check') THEN
        ALTER TABLE public.historical_seal_service_activity
            ADD CONSTRAINT hssa_event_type_check
            CHECK (event_type IN ('INSTALLATION', 'REINSTALLATION_REFURBISHED_SEAL'));
    END IF;
    -- A governed (manifest-imported) row must carry its full provenance.
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'hssa_governed_provenance_check') THEN
        ALTER TABLE public.historical_seal_service_activity
            ADD CONSTRAINT hssa_governed_provenance_check
            CHECK (historical_event_id IS NULL
                   OR (source_hash IS NOT NULL AND source_fingerprint IS NOT NULL AND event_fingerprint IS NOT NULL
                       AND evidence_grade IS NOT NULL AND date_correction_status IS NOT NULL
                       AND pump_tag_number IS NOT NULL AND event_date IS NOT NULL
                       AND import_manifest_sha256 IS NOT NULL AND imported_at IS NOT NULL));
    END IF;
END $$;

CREATE OR REPLACE FUNCTION public.hssa_reject_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'historical_seal_service_activity is append-only: % is not allowed', TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$;

DROP TRIGGER IF EXISTS hssa_append_only_row ON public.historical_seal_service_activity;
CREATE TRIGGER hssa_append_only_row
    BEFORE UPDATE OR DELETE ON public.historical_seal_service_activity
    FOR EACH ROW EXECUTE FUNCTION public.hssa_reject_mutation();

DROP TRIGGER IF EXISTS hssa_append_only_truncate ON public.historical_seal_service_activity;
CREATE TRIGGER hssa_append_only_truncate
    BEFORE TRUNCATE ON public.historical_seal_service_activity
    FOR EACH STATEMENT EXECUTE FUNCTION public.hssa_reject_mutation();

CREATE INDEX IF NOT EXISTS idx_hssa_governed_pump_event
    ON public.historical_seal_service_activity (pump_tag_number, event_date)
    WHERE historical_event_id IS NOT NULL;

COMMIT;

-- ROLLBACK (documented, NOT executed by this file; run only under an approved
-- change, and only after confirming no governed rows must be kept). The
-- append-only protection is removed first, then the additive schema:
--
-- BEGIN;
-- DROP TRIGGER IF EXISTS hssa_append_only_truncate ON public.historical_seal_service_activity;
-- DROP TRIGGER IF EXISTS hssa_append_only_row ON public.historical_seal_service_activity;
-- DROP FUNCTION IF EXISTS public.hssa_reject_mutation();
-- DROP INDEX IF EXISTS public.idx_hssa_governed_pump_event;
-- ALTER TABLE public.historical_seal_service_activity
--     DROP CONSTRAINT IF EXISTS hssa_governed_provenance_check,
--     DROP CONSTRAINT IF EXISTS hssa_event_type_check,
--     DROP CONSTRAINT IF EXISTS hssa_approved_correction_check,
--     DROP CONSTRAINT IF EXISTS hssa_date_correction_status_check,
--     DROP CONSTRAINT IF EXISTS hssa_evidence_grade_check,
--     DROP CONSTRAINT IF EXISTS hssa_position_check,
--     DROP CONSTRAINT IF EXISTS hssa_source_fingerprint_key,
--     DROP CONSTRAINT IF EXISTS hssa_historical_event_id_key,
--     DROP COLUMN IF EXISTS imported_at, DROP COLUMN IF EXISTS import_manifest_sha256,
--     DROP COLUMN IF EXISTS deduplication_status, DROP COLUMN IF EXISTS evidence_grade,
--     DROP COLUMN IF EXISTS date_correction_reason, DROP COLUMN IF EXISTS date_correction_status,
--     DROP COLUMN IF EXISTS corrected_event_date, DROP COLUMN IF EXISTS parsed_source_date,
--     DROP COLUMN IF EXISTS source_date_raw, DROP COLUMN IF EXISTS position_extraction_reason,
--     DROP COLUMN IF EXISTS position_source_raw, DROP COLUMN IF EXISTS position,
--     DROP COLUMN IF EXISTS event_fingerprint, DROP COLUMN IF EXISTS source_fingerprint,
--     DROP COLUMN IF EXISTS source_hash, DROP COLUMN IF EXISTS historical_event_id;
-- COMMIT;
