-- MWO-LTSA-SEAL-UNIT-IDENTITY-FOUNDATION-001 -- the minimum canonical
-- primitive for PHYSICAL mechanical-seal identity, distinct from
-- seal_registry (SEAL TYPE / catalog identity). Phase 0 confirmed: no
-- serial-number or physical-unit column exists anywhere in this schema
-- today -- seal_code identifies a type, never a physical unit
-- (seal_pump_compatibility/seal_stock/installation_report.seal_code all
-- reference the type). This migration adds the missing primitive only;
-- no repair/warranty/lifecycle-event workflow, no stock auto-adjustment.
--
-- Identity hierarchy (audited, not invented): no real manufacturer serial
-- number is available anywhere in existing repository/domain evidence
-- (installation_report's own seal_* column cluster --
-- seal_manufacture/seal_type/seal_arrangement/seal_size/material_code/
-- drawing_no/seal_location/seal_code -- has no serial-number field), so
-- serial_number is nullable here by design (Hard Rule: "MUST be nullable
-- because historical/old seals may not have one... Never fabricate").
-- seal_unit_id (system-generated UUID) is therefore the one identity
-- every physical unit always has, matching this MWO's own preferred
-- hierarchy's tier-3 fallback.
--
-- Known-serial uniqueness policy (explicit, not left implicit): when a
-- real serial number IS recorded, it must be globally unique -- two
-- physical units can never legitimately claim the same manufacturer
-- serial. A plain UNIQUE column constraint would be wrong here (it would
-- also forbid more than one NULL/unknown-serial unit, which is the
-- common case for historical seals); a partial unique index -- unique
-- only among non-NULL values -- expresses "unique when known, unlimited
-- when unknown" exactly, the same distinction this schema already
-- applies elsewhere (Hard Rule "0 must remain distinct from NULL",
-- reused in kind here for "known must be distinct from unknown").
--
-- status vocabulary: no existing IN_STOCK/INSTALLED/REMOVED/SCRAPPED-
-- shaped vocabulary exists anywhere in this schema (repo-wide grep,
-- zero matches) -- these 7 states are new, not a rename of anything
-- pre-existing. Transitions between them are explicitly OUT of this
-- MWO's scope (identity foundation only).
--
-- current_pump_tag_number is CURRENT STATE ONLY (a convenience pointer,
-- "which pump is this unit on right now, if any"), never historical
-- truth -- a physical seal unit moving between pumps over its life is
-- the entire reason seal_unit exists as separate from seal_code; the
-- lifecycle EVENT stream (INSTALL/REMOVE/INSPECT/REPAIR/RETURN/SCRAP)
-- is explicitly deferred to a future dedicated MWO, and is NOT
-- record_change_history (which stays administrative/audit history:
-- who changed which stored value and why -- never repurposed here as
-- the lifecycle model).
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.seal_unit (
    seal_unit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seal_code TEXT NOT NULL REFERENCES public.seal_registry(seal_code),
    serial_number TEXT,
    status TEXT NOT NULL DEFAULT 'IN_STOCK',
    current_pump_tag_number VARCHAR(100) REFERENCES public.ltsa_pumps(tag_number),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_seal_unit_serial_number_unique
    ON public.seal_unit(serial_number) WHERE serial_number IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_seal_unit_seal_code
    ON public.seal_unit(seal_code);

CREATE INDEX IF NOT EXISTS idx_seal_unit_current_pump_tag_number
    ON public.seal_unit(current_pump_tag_number);

-- Closes the already-proven structured pump-link gap (MWO-LTSA-SEAL-
-- LIFECYCLE-REPAIR-AUDIT-001 finding #7: installation_report had no
-- structured pump_tag_number FK, only free-text plant_equip_no) and adds
-- the optional physical-unit link -- both additive/nullable, preserving
-- every existing raw/source column (plant_equip_no, seal_code, and all
-- report fields) unchanged. A legacy installation_report row with both
-- columns NULL remains fully valid (Hard Rule: "legacy report may remain
-- NULL... existing data must remain valid").
ALTER TABLE public.installation_report
    ADD COLUMN IF NOT EXISTS seal_unit_id UUID REFERENCES public.seal_unit(seal_unit_id),
    ADD COLUMN IF NOT EXISTS pump_tag_number VARCHAR(100) REFERENCES public.ltsa_pumps(tag_number);

CREATE INDEX IF NOT EXISTS idx_installation_report_seal_unit_id
    ON public.installation_report(seal_unit_id);

CREATE INDEX IF NOT EXISTS idx_installation_report_pump_tag_number
    ON public.installation_report(pump_tag_number);
