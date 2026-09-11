-- MWO-LTSA-069 -- smallest-safe migration-applied-state tracking.
--
-- Why this exists: a read-only production audit for MWO-LTSA-069 (see
-- ENGINEERING/MWO/MWO-LTSA-069-Group-Agent-Deployment-Stability-Closure.md)
-- found that migration 032's own header claim ("NOT applied to production
-- by this MWO") was false in production reality -- its tables already
-- existed live, with real data, applied out-of-band at an unknown time by
-- an unknown mechanism. There was, and still is, no way to answer "which
-- of migrations 005-033 are actually applied?" from the repository alone.
-- This migration does not retroactively answer that question (see
-- 034_KNOWN_MIGRATION_STATE.md in this same directory for what IS and
-- ISN'T known, honestly) -- it only creates the ledger table future
-- deployments should write to, so the question is answerable going
-- forward.
--
-- NOT applied to production by this MWO -- report/design only, per
-- MWO-LTSA-069's explicit "Do NOT modify production DB" instruction. An
-- operator applying this file must also perform the one-time backfill
-- described in 034_KNOWN_MIGRATION_STATE.md's "Operator Action" section --
-- this file alone does not populate historical rows, by design (this
-- migration cannot know what it doesn't know; fabricating applied_at
-- timestamps for 005-031 would be worse than leaving them unrecorded).

CREATE TABLE IF NOT EXISTS public.schema_migration_history (
    migration_file  TEXT PRIMARY KEY,
    -- 'CONFIRMED_APPLIED': verified against a real database by a named,
    --   dated, human-run check (see verification_note).
    -- 'ASSUMED_APPLIED_SEQUENTIAL': not independently verified, but the
    --   database's own migration-runner (if one exists) or an operator
    --   applied every prior-numbered file in order, so this one is
    --   presumed applied too. Weaker than CONFIRMED_APPLIED -- say so.
    -- 'UNKNOWN': no evidence either way. The honest default; never
    --   silently upgraded to one of the above without a real check.
    status              TEXT NOT NULL DEFAULT 'UNKNOWN'
                        CHECK (status IN ('CONFIRMED_APPLIED', 'ASSUMED_APPLIED_SEQUENTIAL', 'UNKNOWN')),
    -- Nullable on purpose: an UNKNOWN row legitimately has no applied_at.
    -- Never fabricate a value here to satisfy a NOT NULL constraint.
    applied_at          TIMESTAMPTZ,
    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    recorded_by         TEXT NOT NULL,
    verification_note   TEXT
);
