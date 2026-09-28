-- AI5R — Condition Monitoring Field Form Idempotency Constraint
-- Phase: CM_R5E_3_FIELD_FORM_IDEMPOTENCY_SCHEMA_GATE
--
-- Enforces physical database-level uniqueness for field-form condition
-- monitoring readings while leaving all legacy, historical, WhatsApp, and
-- ad-hoc CMON writers completely unaffected.
--
-- A partial UNIQUE index ensures:
-- 1. Uniqueness is enforced ONLY on rows where source_reference LIKE 'field_form:%'
-- 2. Uniqueness applies ONLY to active rows (WHERE deleted_at IS NULL),
--    preserving standard LTSA soft-delete semantics (re-apply permitted after soft-delete)
-- 3. Non-field-form source_reference values (e.g. document_field_extraction:*,
--    WHATSAPP::*, manual refs, NULLs) are completely unconstrained by this index.
--
-- Preflight: fails immediately if any duplicate active field_form keys exist.

DO $$
DECLARE
    v_duplicate_count INT;
BEGIN
    SELECT COUNT(*) INTO v_duplicate_count
    FROM (
        SELECT source_reference
        FROM public.condition_monitoring_reading
        WHERE source_reference LIKE 'field_form:%'
          AND deleted_at IS NULL
        GROUP BY source_reference
        HAVING COUNT(*) > 1
    ) d;

    IF v_duplicate_count > 0 THEN
        RAISE EXCEPTION 'Preflight check failed: % duplicate active field_form source_reference keys found.', v_duplicate_count;
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS idx_condition_monitoring_reading_field_form_unique
    ON public.condition_monitoring_reading (source_reference)
    WHERE source_reference LIKE 'field_form:%'
      AND deleted_at IS NULL;

-- Documented Rollback (forward-only repository convention):
--
-- DROP INDEX IF EXISTS public.idx_condition_monitoring_reading_field_form_unique;
