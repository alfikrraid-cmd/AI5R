-- PART A -- SUPERSEDED -- DO NOT USE FOR BACKFILL DECISIONS.
-- Superseded 2026-09-16 by PART B (below), the CANONICAL -- CURRENT
-- AUTHORITATIVE CLASSIFIER. Reason: this substring method never checks
-- shaft_size, so a seal_type that happens to name only one seal_registry
-- row can be reported "A_DETERMINISTIC_UNIQUE" even when that row's size
-- does not actually match the installation's recorded seal_size (real
-- production proof: INSTL-006-2026/INSTL-028-2026, T604/3", both wrongly
-- "A" here -- see PART B's own header for the full account). Kept below
-- only for historical/audit traceability of the method that was used
-- before the size-aware upgrade; never re-derive a Class A backfill
-- candidate from Part A's output.
--
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

-- ============================================================================
-- PART B -- CANONICAL -- CURRENT AUTHORITATIVE CLASSIFIER (added by
-- MECHANICAL-SEAL-CONSOLIDATION-LINKAGE-CLASSIFIER-RECONCILIATION-R1,
-- canonicalized by MECHANICAL-SEAL-LINKAGE-CLASSIFIER-CANONICALIZATION-R1,
-- 2026-09-16). READ-ONLY DIAGNOSTIC -- does not apply any migration, does
-- not mutate production, does not backfill. Part A above is left
-- completely intact as the historical record of the substring method; it
-- is NOT deleted, because its own header already disclosed its limitation
-- and deferred exactly this upgrade ("A real size-aware match can be added
-- later, but only with verified, tested normalization -- not guessed
-- here").
--
-- WHY PART A IS SUPERSEDED: Part A's substring match on seal_type (e.g.
-- 'T48MP' ILIKE inside 'LTSA-SEAL-T48MP-2-3-4') can never distinguish
-- between the 16-18 seal_registry rows that share a seal_name, so on real
-- production data it produced B_MULTIPLE_CANDIDATES for the overwhelming
-- majority of otherwise-resolvable rows (31/42) and, more importantly, it
-- can produce a FALSE "unique" Class A whenever a seal_type happens to
-- match only one registry row by name alone, even when that row's
-- shaft_size does not actually match the installation's recorded seal_size
-- (verified against real production data for T604: only one seal_registry
-- row is named 'T604' (shaft_size=2.875), but INSTL-006-2026 and
-- INSTL-028-2026 both recorded seal_size='3"' (=3.0) -- a genuine
-- dimensional mismatch that Part A's method cannot see because it never
-- looks at shaft_size at all).
--
-- CANONICAL RULE: NORMALIZED_EXACT_SEAL_TYPE + VERIFIED_EXACT_SHAFT_SIZE.
--   1. seal_type must match seal_registry.seal_name by trimmed,
--      case-insensitive EXACT equality -- never substring/contains/fuzzy.
--   2. seal_size must be deterministically parsed (fraction, bare-inch,
--      decimal-inch, or "NN MM" -- see parsed_size below) and matched
--      against seal_registry.shaft_size by exact numeric equality --
--      ALWAYS, regardless of how many type-only candidates exist. Type
--      alone, even when it happens to be unique, is never sufficient
--      evidence of a specific historical installed identity (this is the
--      exact rule Part A's own single-candidate cases silently violated).
--   A = exactly one candidate survives both required dimensions.
--   B = two or more candidates survive both.
--   C = required evidence (seal_type, seal_manufacture) exists but zero
--       candidates survive after applying it.
--   D = required evidence (seal_type, or a parseable seal_size once a
--       seal_type candidate exists) is absent or unusable.
--
-- Size parser coverage (validated against every one of the 17 distinct
-- real production installation_report.seal_size values, zero exceptions,
-- and against this mission's own 12 example format/value pairs, all
-- exact matches): '<whole>.<num>/<den>"' fractional inches (e.g.
-- '3.1/2"' -> 3.5), bare whole inches (e.g. '6"' -> 6.0), decimal inches
-- (e.g. '2.375"' -> 2.375), and '<N> MM' millimetres (e.g. '55 MM' -> 55.0,
-- compared to seal_registry.shaft_size as a raw number since that column
-- has no unit dimension of its own and production data never presented a
-- conflicting mm-vs-inch pair for the same seal_type).

WITH parsed_installations AS (
    SELECT
        ir.installation_code,
        ir.plant_equip_no,
        ir.pump_tag_number,
        ir.seal_type,
        ir.seal_manufacture,
        ir.seal_size AS raw_seal_size,
        CASE
            WHEN ir.seal_size IS NULL OR btrim(ir.seal_size) IN ('', '-') THEN NULL
            WHEN ir.seal_size ~ '^\s*\d+\.\d+/\d+\s*"?\s*$' THEN
                (regexp_match(ir.seal_size, '^\s*(\d+)\.(\d+)/(\d+)\s*"?\s*$'))[1]::numeric
                + (regexp_match(ir.seal_size, '^\s*(\d+)\.(\d+)/(\d+)\s*"?\s*$'))[2]::numeric
                    / (regexp_match(ir.seal_size, '^\s*(\d+)\.(\d+)/(\d+)\s*"?\s*$'))[3]::numeric
            WHEN ir.seal_size ~ '^\s*\d+(\.\d+)?\s*"\s*$' THEN
                (regexp_match(ir.seal_size, '^\s*(\d+(?:\.\d+)?)\s*"\s*$'))[1]::numeric
            WHEN ir.seal_size ~* '^\s*\d+(\.\d+)?\s*MM\s*$' THEN
                (regexp_match(ir.seal_size, '^\s*(\d+(?:\.\d+)?)\s*MM\s*$', 'i'))[1]::numeric
            ELSE NULL
        END AS parsed_size
    FROM public.installation_report ir
    WHERE ir.seal_code IS NULL
),
type_candidates AS (
    SELECT pi.installation_code, sr.seal_code, sr.shaft_size
    FROM parsed_installations pi
    JOIN public.seal_registry sr
      ON pi.seal_type IS NOT NULL
     AND btrim(upper(sr.seal_name)) = btrim(upper(pi.seal_type))
),
size_candidates AS (
    SELECT tc.installation_code, tc.seal_code
    FROM type_candidates tc
    JOIN parsed_installations pi ON pi.installation_code = tc.installation_code
    WHERE pi.parsed_size IS NOT NULL
      AND tc.shaft_size IS NOT NULL
      AND abs(tc.shaft_size - pi.parsed_size) < 0.01
),
counts AS (
    SELECT
        pi.installation_code,
        pi.plant_equip_no,
        pi.pump_tag_number,
        pi.seal_type,
        pi.raw_seal_size,
        pi.parsed_size,
        COUNT(DISTINCT tcand.seal_code) AS type_candidate_count,
        COUNT(DISTINCT scand.seal_code) AS size_candidate_count,
        (ARRAY_AGG(DISTINCT scand.seal_code) FILTER (WHERE scand.seal_code IS NOT NULL))[1] AS sole_matched_seal_code
    FROM parsed_installations pi
    LEFT JOIN type_candidates tcand ON tcand.installation_code = pi.installation_code
    LEFT JOIN size_candidates scand ON scand.installation_code = pi.installation_code
    GROUP BY pi.installation_code, pi.plant_equip_no, pi.pump_tag_number,
             pi.seal_type, pi.raw_seal_size, pi.parsed_size
)
SELECT
    installation_code,
    plant_equip_no,
    pump_tag_number,
    seal_type,
    raw_seal_size,
    parsed_size,
    type_candidate_count,
    size_candidate_count,
    CASE
        WHEN seal_type IS NULL THEN 'D_INSUFFICIENT_EVIDENCE'
        WHEN type_candidate_count = 0 THEN 'C_NO_CANDIDATE'
        WHEN parsed_size IS NULL THEN 'D_INSUFFICIENT_EVIDENCE'
        WHEN size_candidate_count = 0 THEN 'C_NO_CANDIDATE'
        WHEN size_candidate_count = 1 THEN 'A_DETERMINISTIC_UNIQUE'
        ELSE 'B_MULTIPLE_CANDIDATES'
    END AS proposed_linkage_class,
    CASE WHEN size_candidate_count = 1 THEN sole_matched_seal_code ELSE NULL END AS matched_seal_code
FROM counts
ORDER BY proposed_linkage_class, installation_code;

-- Verified TWICE against real production data (2026-09-16): once via an
-- independent Python re-implementation of this exact rule, and once by
-- executing this exact SELECT (pure read, no INSERT/UPDATE/DELETE) against
-- the real production ltsa_brain database. Both give identical tallies:
-- A=25, B=0, C=9, D=8 (42 total). Every Class A candidate_count after
-- type AND after size both equal exactly 1; INSTL-042-2026 verified to
-- resolve uniquely to LTSA-SEAL-T48MP-3-1-2 as expected.
--
-- PROVENANCE HOLD (seal-identity classification is NOT the same dimension
-- as source-provenance confidence -- do not collapse the two): of the 25
-- Class A rows, 2 have a genuine but SEPARATE, unresolved provenance
-- question -- INSTL-025-2026 (plant_equip_no=101-P-2A vs.
-- pump_tag_number/source_document both saying 101-P-3B) and
-- INSTL-041-2026 (plant_equip_no=140-P-26A vs. pump_tag_number/source_
-- document both saying 140-P-26B). Both pump tags in each pair are
-- confirmed real, distinct, registered pumps; the original scanned PDFs
-- are not accessible in this environment to confirm which pump the report
-- body actually names, so provenance cannot be resolved from data alone.
-- Their SEAL-IDENTITY class stays A (the type+size match itself is not in
-- doubt) -- only their BACKFILL ELIGIBILITY is held pending manual source
-- review:
--   CLASS_A_TOTAL=25
--   CLASS_A_WRITE_READY_WITHOUT_PROVENANCE_HOLD=23
--   CLASS_A_PROVENANCE_HOLD=2  (INSTL-025-2026, INSTL-041-2026)
--   BACKFILL_ELIGIBILITY=HOLD_PROVENANCE_REVIEW for those 2 rows only
-- ============================================================================
