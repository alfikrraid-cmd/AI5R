-- Migration 054: LTSA HCC Master Reconciliation R2A (governed data migration)
-- Lineage: migration 053 (053_create_current_seal_installation.sql)
-- Phase: LTSA_HCC_MASTER_RECONCILIATION_R2A (Chief-authorized; R1 audit
-- LTSA_HCC_99_ASSET_CRITICALITY_CANONICAL_AUDIT_R1 = PASS).
--
-- Data only. No DDL, no DELETE, no rename, no history table touched.
--
-- 1. 211-P-25A / 211-P-25B: add to ltsa_pumps. Both already exist in
--    asset_registry (asset_type PUMP, area HCC) with CM/PM history, but
--    were absent from ltsa_pumps. They are distinct assets from
--    212-P-25A/B (Chief decision: HCC contract rows 31/32 source tag
--    212-P-25A/B corrected to 211-P-25A/B). Field provenance:
--      tag_number  ASSET_REGISTRY (+ CHIEF_DECISION tag correction)
--      area        ASSET_REGISTRY ('HCC')
--      status      ASSET_REGISTRY ('UNKNOWN')
--      name        CONTRACT_SOURCE (HCC contract rows 31/32 service)
--      pump_type   CONTRACT_SOURCE (HCC contract rows 31/32 'OH6')
--    api_plan, seal_type, drawing_ref, location, manufacturer, model stay
--    NULL: no non-inferred evidence; deliberately NOT copied from
--    212-P-25A/B. criticality stays NULL (deferred to R2B).
--
-- 2. 701-MM-51 / 702-MM-51: asset_registry.asset_type NULL -> 'AGITATOR'.
--    Source evidence: HCC contract rows 81/93 service "BENFIELD STORAGE
--    AGITATOR". Follows the existing production convention for non-pump
--    equipment (uppercase descriptive class, e.g. 'LIQUID RING
--    COMPRESSOR'); no CHECK constraint exists; application code only tests
--    asset_type = 'PUMP', so non-PUMP behaviour is unchanged. Neither asset
--    is added to ltsa_pumps.
--
-- 212-P-13A/B and 212-P-13AR/BR are intentionally untouched (identity
-- UNRESOLVED per R1).
--
-- Idempotent: INSERT ... ON CONFLICT DO NOTHING; UPDATE only where
-- asset_type IS NULL. Preconditions and postconditions RAISE on failure.
-- Run with: psql -v ON_ERROR_STOP=1 --single-transaction -f <this file>

DO $$
BEGIN
    IF (SELECT count(*) FROM public.asset_registry
         WHERE asset_code IN ('211-P-25A', '211-P-25B')
           AND asset_type = 'PUMP' AND area = 'HCC') <> 2 THEN
        RAISE EXCEPTION '054 precondition: 211-P-25A/B must exist in asset_registry as PUMP/HCC';
    END IF;
    IF (SELECT count(*) FROM public.ltsa_pumps
         WHERE tag_number IN ('212-P-25A', '212-P-25B')) <> 2 THEN
        RAISE EXCEPTION '054 precondition: 212-P-25A/B must exist in ltsa_pumps';
    END IF;
    IF (SELECT count(*) FROM public.asset_registry
         WHERE asset_code IN ('701-MM-51', '702-MM-51')
           AND (asset_type IS NULL OR asset_type = 'AGITATOR')) <> 2 THEN
        RAISE EXCEPTION '054 precondition: 701/702-MM-51 must exist in asset_registry with asset_type NULL or AGITATOR';
    END IF;
    IF EXISTS (SELECT 1 FROM public.ltsa_pumps
                WHERE tag_number IN ('701-MM-51', '702-MM-51')) THEN
        RAISE EXCEPTION '054 precondition: 701/702-MM-51 must not exist in ltsa_pumps';
    END IF;
END $$;

INSERT INTO public.ltsa_pumps (tag_number, area, status, name, pump_type, notes)
SELECT a.asset_code, a.area, 'UNKNOWN', 'LIGHT NAPTHA STRP OVHDPUMP', 'OH6',
       'R2A 054: added from asset_registry. name/pump_type from HCC contract row '
       || CASE a.asset_code WHEN '211-P-25A' THEN '31' ELSE '32' END
       || ' (source tag ' || replace(a.asset_code, '211-', '212-')
       || ' corrected to ' || a.asset_code
       || ' by Chief decision). Distinct asset from ' || replace(a.asset_code, '211-', '212-')
       || '; nothing copied from it.'
  FROM public.asset_registry a
 WHERE a.asset_code IN ('211-P-25A', '211-P-25B')
ON CONFLICT (tag_number) DO NOTHING;

UPDATE public.asset_registry
   SET asset_type = 'AGITATOR', updated_at = now()
 WHERE asset_code IN ('701-MM-51', '702-MM-51')
   AND asset_type IS NULL;

DO $$
BEGIN
    IF (SELECT count(*) FROM public.ltsa_pumps
         WHERE tag_number IN ('211-P-25A', '211-P-25B')
           AND area = 'HCC' AND criticality IS NULL) <> 2 THEN
        RAISE EXCEPTION '054 postcondition: 211-P-25A/B not present in ltsa_pumps as HCC with NULL criticality';
    END IF;
    IF (SELECT count(*) FROM public.asset_registry
         WHERE asset_code IN ('701-MM-51', '702-MM-51') AND asset_type = 'AGITATOR') <> 2 THEN
        RAISE EXCEPTION '054 postcondition: 701/702-MM-51 asset_type is not AGITATOR';
    END IF;
    IF EXISTS (SELECT 1 FROM public.ltsa_pumps
                WHERE tag_number IN ('701-MM-51', '702-MM-51')) THEN
        RAISE EXCEPTION '054 postcondition: MM-51 present in ltsa_pumps';
    END IF;
    IF EXISTS (SELECT 1 FROM public.ltsa_pumps WHERE criticality IS NOT NULL) THEN
        RAISE EXCEPTION '054 postcondition: ltsa_pumps.criticality must remain unpopulated';
    END IF;
END $$;

-- Rollback (manual, not executed by this file; forward-only convention,
-- see migration 040). Safe only while no child row references the two
-- new ltsa_pumps rows (installation_report, seal_unit, seal_lifecycle_event,
-- seal_inspection, historical_seal_service_activity,
-- current_seal_installation all FK ltsa_pumps.tag_number):
--
--   DELETE FROM public.ltsa_pumps
--    WHERE tag_number IN ('211-P-25A', '211-P-25B')
--      AND notes LIKE 'R2A 054:%';
--   UPDATE public.asset_registry SET asset_type = NULL, updated_at = now()
--    WHERE asset_code IN ('701-MM-51', '702-MM-51') AND asset_type = 'AGITATOR';
