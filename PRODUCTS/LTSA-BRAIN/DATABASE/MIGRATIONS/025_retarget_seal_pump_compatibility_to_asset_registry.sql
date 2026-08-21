-- MWO-LTSA-ASSET-SEAL-COMPATIBILITY-001
-- Active seal compatibility is compatibility to a canonical LTSA asset.
--
-- Backward compatibility: keep the existing table and `pump_tag_number`
-- column name for current workflows/API consumers. Semantic debt: the
-- column now stores the compatible LTSA asset identity; pump-specific
-- consumers should filter to asset_registry.asset_type = 'PUMP'.

DO $$
BEGIN
    IF to_regclass('public.asset_registry') IS NULL THEN
        RAISE EXCEPTION 'asset_registry is required before retargeting seal_pump_compatibility';
    END IF;
END $$;

ALTER TABLE public.seal_pump_compatibility
    DROP CONSTRAINT IF EXISTS seal_pump_compatibility_pump_tag_number_fkey;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.seal_pump_compatibility'::regclass
          AND conname = 'seal_pump_compatibility_asset_code_fkey'
    ) THEN
        ALTER TABLE public.seal_pump_compatibility
            ADD CONSTRAINT seal_pump_compatibility_asset_code_fkey
            FOREIGN KEY (pump_tag_number)
            REFERENCES public.asset_registry(asset_code)
            ON DELETE NO ACTION;
    END IF;
END $$;
