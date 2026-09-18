-- MECHANICAL-SEAL-DOMAIN-CONSOLIDATION-R1 -- deterministic Seal ID
-- backfill + safe Seal Type backfill, for the columns added in
-- 043_add_seal_registry_identity_and_type.sql.
--
-- ORDERING (Chief Architect decision): created_at ASC, tiebreak
-- seal_code ASC. NULLS LAST on created_at so any legacy row missing it
-- still sorts deterministically (after every row that has a real
-- created_at), never silently first.
--
-- OEM PREFIX MAPPING: only 'John Crane' -> 'JC' is defined, because
-- Phase 1 audit confirmed (read-only, dev DB) manufacturer is uniformly
-- 'John Crane' for all existing seal_registry rows today -- the same
-- population migration 013 itself audited (61 rows). A seal_id must
-- never assert an OEM the data does not actually evidence (the exact
-- discipline migration 013 already applies to gpn_john_crane), so this
-- migration REFUSES to run (preflight RAISE EXCEPTION, not a silent
-- skip) if it ever finds an unmapped manufacturer -- that is a real
-- signal a second OEM has entered the catalog and this migration's
-- mapping needs a conscious extension, not an auto-generated guess.
--
-- IDEMPOTENT / re-runnable: only touches rows where seal_id/seal_type is
-- still NULL. Re-running this file after it already succeeded is a
-- no-op (matches "Do NOT regenerate/renumber them during application
-- startup"). If it is ever re-run after a genuinely new John Crane seal
-- was added, numbering continues from the current MAX(...) suffix
-- rather than restarting at 1, so previously assigned IDs never change.
--
-- seal_type backfill is intentionally conservative: only set where
-- exactly one distinct seal_type exists across a seal_code's linked
-- mechanical_seal_stock_pool rows (self-computed HAVING COUNT(DISTINCT
-- seal_type) = 1) -- Phase 1 audit found 0 seal_code-linked pool rows in
-- the local dev snapshot, so this cannot be validated against real data
-- here; the query is written to be safe under real production data
-- regardless (any seal_code with genuinely conflicting seal_type values
-- across pools is left NULL, never guessed).

DO $$
DECLARE
    v_unmapped_count INT;
BEGIN
    SELECT COUNT(*) INTO v_unmapped_count
    FROM public.seal_registry
    WHERE seal_id IS NULL
      AND NOT (manufacturer ILIKE 'John Crane');

    IF v_unmapped_count > 0 THEN
        RAISE EXCEPTION
            'Preflight failed: % seal_registry row(s) have a manufacturer with no known Seal ID OEM prefix mapping (only ''John Crane'' -> MS-JC- is defined today). Extend the OEM prefix mapping in this migration before applying -- do not guess a prefix.',
            v_unmapped_count;
    END IF;
END $$;

-- Seal Type backfill (safe subset only; everything else stays NULL / N/A).
UPDATE public.seal_registry sr
SET seal_type = safe.only_type
FROM (
    SELECT seal_code, MIN(seal_type) AS only_type
    FROM public.mechanical_seal_stock_pool
    WHERE seal_code IS NOT NULL
    GROUP BY seal_code
    HAVING COUNT(DISTINCT seal_type) = 1
) safe
WHERE sr.seal_code = safe.seal_code
  AND sr.seal_type IS NULL;

-- Seal ID backfill, John Crane only, deterministic order, resumable.
WITH offset_calc AS (
    SELECT COALESCE(MAX(CAST(SUBSTRING(seal_id FROM 'MS-JC-(\d+)$') AS INT)), 0) AS max_existing
    FROM public.seal_registry
    WHERE seal_id LIKE 'MS-JC-%'
),
ordered AS (
    SELECT
        seal_code,
        ROW_NUMBER() OVER (ORDER BY created_at ASC NULLS LAST, seal_code ASC) AS rn
    FROM public.seal_registry
    WHERE seal_id IS NULL
      AND manufacturer ILIKE 'John Crane'
)
UPDATE public.seal_registry sr
SET seal_id = 'MS-JC-' || LPAD((ordered.rn + offset_calc.max_existing)::text, 4, '0')
FROM ordered, offset_calc
WHERE sr.seal_code = ordered.seal_code;

-- Postflight: refuse to leave duplicate seal_id values behind.
DO $$
DECLARE
    v_duplicate_count INT;
BEGIN
    SELECT COUNT(*) INTO v_duplicate_count
    FROM (
        SELECT seal_id
        FROM public.seal_registry
        WHERE seal_id IS NOT NULL
        GROUP BY seal_id
        HAVING COUNT(*) > 1
    ) d;

    IF v_duplicate_count > 0 THEN
        RAISE EXCEPTION 'Postflight failed: % duplicate seal_id value(s) found after backfill.', v_duplicate_count;
    END IF;
END $$;

-- Uniqueness enforced only now that backfill has proven itself
-- duplicate-free -- partial index (WHERE seal_id IS NOT NULL) so any
-- future unmapped-OEM row stays legally NULL, same pattern as seal_unit.
-- serial_number's own partial unique index (migration 018).
CREATE UNIQUE INDEX IF NOT EXISTS idx_seal_registry_seal_id_unique
    ON public.seal_registry (seal_id)
    WHERE seal_id IS NOT NULL;

-- Documented Rollback (forward-only repository convention):
--
-- DROP INDEX IF EXISTS public.idx_seal_registry_seal_id_unique;
-- UPDATE public.seal_registry SET seal_id = NULL, seal_type = NULL;
-- (Rollback of a backfill is destructive by nature -- confirm no
-- consumer has taken a dependency on seal_id before running this.)
