-- MWO-LTSA-CM-R2 -- historical extraction asset reference is a reference
-- to a canonical LTSA asset, not a pump specifically (Chief Architect
-- domain correction, CM-R1C/CM-R2). Mirrors migration 025's own
-- established pattern for seal_pump_compatibility verbatim (same
-- rationale, same idempotent shape) -- this is the second, not the
-- first, application of this exact principle in this schema.
--
-- Backward compatibility: keep document_field_extraction and its
-- `pump_tag_number` column name for current workflows/API consumers
-- (historical_pm_cmon_cli.py, HistoricalPMCMONStagingRepository,
-- routers/historical_review.py). Semantic debt, disclosed: the column
-- now stores the compatible LTSA asset identity; pump-specific
-- consumers should filter to asset_registry.asset_type = 'PUMP'.
--
-- Pre-migration verification performed against the local sanitized
-- restore before writing this file (see MWO-LTSA-CM-R2 report):
-- CURRENT_ROWS=1240, CURRENT_DISTINCT_TAGS=229,
-- ROWS_VALID_IN_ASSET_REGISTRY=1228, ROWS_NOT_VALID_IN_ASSET_REGISTRY=0.
-- Zero orphan risk confirmed before this file was written, not assumed.

DO $$
BEGIN
    IF to_regclass('public.asset_registry') IS NULL THEN
        RAISE EXCEPTION 'asset_registry is required before retargeting document_field_extraction';
    END IF;
END $$;

ALTER TABLE public.document_field_extraction
    DROP CONSTRAINT IF EXISTS document_field_extraction_pump_tag_number_fkey;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.document_field_extraction'::regclass
          AND conname = 'document_field_extraction_asset_code_fkey'
    ) THEN
        ALTER TABLE public.document_field_extraction
            ADD CONSTRAINT document_field_extraction_asset_code_fkey
            FOREIGN KEY (pump_tag_number)
            REFERENCES public.asset_registry(asset_code)
            ON DELETE NO ACTION;
    END IF;
END $$;

-- Rollback (manual, not executed by this file -- forward-only
-- migration convention already established in this directory):
--
--   ALTER TABLE public.document_field_extraction
--       DROP CONSTRAINT IF EXISTS document_field_extraction_asset_code_fkey;
--   ALTER TABLE public.document_field_extraction
--       ADD CONSTRAINT document_field_extraction_pump_tag_number_fkey
--       FOREIGN KEY (pump_tag_number) REFERENCES public.ltsa_pumps(tag_number);
--
-- Safe only as long as no row's pump_tag_number was set to a
-- non-pump asset since this migration ran -- check before rolling back.
