-- MECHANICAL-SEAL-DOMAIN-CONSOLIDATION-R1 -- read-only linkage
-- classification for historical installation_report rows against
-- seal_registry, per the mission's explicit new-evidence constraint:
--
--   "Do NOT populate historical installation_report.seal_code unless
--    deterministic authoritative evidence proves the link... Before any
--    historical seal linkage/backfill: classify installation records as
--    A = deterministic unique identity, B = multiple candidates,
--    C = no candidate, D = insufficient evidence. Only Class A may ever
--    be proposed for automatic linkage."
--
-- THIS SCRIPT IS PURE SELECT -- it contains no INSERT/UPDATE/DELETE and
-- must never be extended to include one. It classifies, it does not
-- link. Applying a Class A proposal (i.e. actually writing to
-- installation_report.seal_code) is a separate, explicit, Chief-
-- Architect-approved action, not performed by this script or by this
-- mission.
--
-- MATCHING METHOD (disclosed, not hidden): a candidate seal_registry row
-- is one whose seal_name contains the installation_report's free-text
-- seal_type (case-insensitive substring, not exact -- seal_name embeds
-- the type designation, e.g. 'LTSA-SEAL-T48MP-2-3-4' contains 'T48MP')
-- AND whose manufacturer matches exactly (case-insensitive). Seal
-- SIZE/material are deliberately NOT used to narrow candidates further:
-- installation_report.seal_size is free text in inconsistent formats
-- (e.g. '3.1/2"') that would require lossy normalization against
-- seal_registry.shaft_size (NUMERIC) to compare -- using it to silently
-- collapse a multi-candidate case down to a false "unique" match would
-- be exactly the fabricated precision this mission's evidence explicitly
-- forbids. A real size-aware match can be added later, but only with
-- verified, tested normalization -- not guessed here.
--
-- Run against a database that mirrors production's installation_report
-- content to get real Class A/B/C/D counts (verified 2026-09-16 against
-- the local ai5r-runtime-postgres-1 dev container: its 42 installation_
-- report rows exactly match the production audit's own worked example,
-- INSTL-042-2026/211-P-8A/T48MP -- but this should still be independently
-- re-run against the real production database before being treated as
-- final, since this session has no direct production access).

WITH candidates AS (
    SELECT
        ir.installation_code,
        ir.plant_equip_no,
        ir.seal_type      AS ir_seal_type,
        ir.seal_manufacture AS ir_manufacturer,
        (
            SELECT array_agg(sr.seal_code ORDER BY sr.seal_code)
            FROM public.seal_registry sr
            WHERE ir.seal_type IS NOT NULL
              AND ir.seal_manufacture IS NOT NULL
              AND sr.seal_name ILIKE '%' || ir.seal_type || '%'
              AND sr.manufacturer ILIKE ir.seal_manufacture
        ) AS candidate_seal_codes
    FROM public.installation_report ir
    WHERE ir.seal_code IS NULL
)
SELECT
    installation_code,
    plant_equip_no,
    ir_seal_type,
    ir_manufacturer,
    candidate_seal_codes,
    CASE
        WHEN ir_seal_type IS NULL OR ir_manufacturer IS NULL THEN 'D_INSUFFICIENT_EVIDENCE'
        WHEN candidate_seal_codes IS NULL OR array_length(candidate_seal_codes, 1) = 0 THEN 'C_NO_CANDIDATE'
        WHEN array_length(candidate_seal_codes, 1) = 1 THEN 'A_DETERMINISTIC_UNIQUE'
        ELSE 'B_MULTIPLE_CANDIDATES'
    END AS linkage_class
FROM candidates
ORDER BY linkage_class, installation_code;

-- Summary counts only (what the mission's Final Report asks for):
--
-- WITH candidates AS ( ... same as above ... )
-- SELECT
--     CASE
--         WHEN ir_seal_type IS NULL OR ir_manufacturer IS NULL THEN 'D_INSUFFICIENT_EVIDENCE'
--         WHEN candidate_seal_codes IS NULL OR array_length(candidate_seal_codes, 1) = 0 THEN 'C_NO_CANDIDATE'
--         WHEN array_length(candidate_seal_codes, 1) = 1 THEN 'A_DETERMINISTIC_UNIQUE'
--         ELSE 'B_MULTIPLE_CANDIDATES'
--     END AS linkage_class,
--     COUNT(*) AS row_count
-- FROM candidates
-- GROUP BY 1
-- ORDER BY 1;
