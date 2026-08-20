-- MWO-LTSA-SEAL-INSPECTION-REPAIR-001 -- engineering INSPECTION and
-- REPAIR records for physical mechanical seals, layered on top of
-- migration 018 (seal_unit) and migration 019 (seal_lifecycle_event).
--
-- These are ENGINEERING records, not lifecycle-state truth: creating an
-- inspection or repair row here never writes a seal_lifecycle_event row
-- and never mutates seal_unit.status/current_pump_tag_number -- that
-- remains the exclusive job of seal_lifecycle_service.apply_lifecycle_event
-- (an explicit SEND_FOR_INSPECTION/INSPECTION_COMPLETED/SEND_FOR_REPAIR/
-- REPAIR_COMPLETED/SCRAP call), never inferred from an inspection/repair
-- outcome. Detailed findings/parts data intentionally never lives on
-- seal_lifecycle_event itself (this MWO's own architecture rule).
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.seal_inspection (
    inspection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seal_unit_id UUID NOT NULL REFERENCES public.seal_unit(seal_unit_id),
    inspection_date TIMESTAMPTZ NOT NULL,
    -- Pump-at-time-of-inspection, an honest historical reference (never
    -- seal_unit.current_pump_tag_number, which is a live snapshot that
    -- can already have moved on by the time this row is read).
    pump_tag_number VARCHAR(100) REFERENCES public.ltsa_pumps(tag_number),
    inspection_type TEXT NOT NULL,
    overall_condition TEXT,
    failure_mode TEXT,
    root_cause TEXT,
    recommendation TEXT,
    disposition TEXT,
    inspected_by TEXT,
    notes TEXT,
    source_reference TEXT,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_seal_inspection_type CHECK (
        inspection_type IN ('RECEIVING', 'POST_REMOVAL', 'PRE_REPAIR', 'POST_REPAIR', 'GENERAL')
    ),
    -- NULL allowed: assessment may be incomplete at the moment this row
    -- is written (this MWO's own explicit rule) -- never defaulted to a
    -- fabricated disposition.
    CONSTRAINT chk_seal_inspection_disposition CHECK (
        disposition IS NULL
        OR disposition IN ('RETURN_TO_STOCK', 'REPAIR_REQUIRED', 'SCRAP_RECOMMENDED', 'MONITOR')
    )
);

CREATE INDEX IF NOT EXISTS idx_seal_inspection_seal_unit
    ON public.seal_inspection(seal_unit_id, inspection_date, inspection_id);

CREATE INDEX IF NOT EXISTS idx_seal_inspection_pump
    ON public.seal_inspection(pump_tag_number, inspection_date, inspection_id);

-- Component-level findings as child rows rather than dozens of fixed
-- columns on seal_inspection (this MWO's own explicit instruction) --
-- the same "narrow header + child detail rows" shape seal_lifecycle_event
-- already avoids needing for a different reason (append-only history).
CREATE TABLE IF NOT EXISTS public.seal_inspection_finding (
    finding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id UUID NOT NULL REFERENCES public.seal_inspection(inspection_id),
    component TEXT NOT NULL,
    condition TEXT,
    measurement_name TEXT,
    -- NUMERIC (not FLOAT): NULL and 0 must stay distinct (this MWO's own
    -- explicit rule) -- NUMERIC's NULL-ability already gives this for
    -- free, called out here because a lossy type choice could quietly
    -- break it.
    measured_value NUMERIC,
    unit TEXT,
    acceptance_min NUMERIC,
    acceptance_max NUMERIC,
    finding TEXT,
    action_required TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_seal_inspection_finding_component CHECK (
        component IN (
            'SEAL_FACE', 'MATING_RING', 'O_RING', 'SLEEVE', 'SPRING',
            'DRIVE_PIN', 'SET_SCREW', 'GLAND', 'OTHER'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_seal_inspection_finding_inspection
    ON public.seal_inspection_finding(inspection_id);

CREATE TABLE IF NOT EXISTS public.seal_repair (
    repair_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seal_unit_id UUID NOT NULL REFERENCES public.seal_unit(seal_unit_id),
    inspection_id UUID REFERENCES public.seal_inspection(inspection_id),
    repair_date TIMESTAMPTZ NOT NULL,
    -- No controlled vocabulary given for repair_type in this MWO's own
    -- field list (unlike repair_result below) -- left as free TEXT
    -- rather than a fabricated CHECK list this MWO never specified.
    repair_type TEXT NOT NULL,
    repair_action TEXT NOT NULL,
    -- JSONB, not a normalized parts child table: audited first (this
    -- MWO's own instruction) -- internal_component_master/
    -- internal_component_stock exist in CANONICAL_SCHEMA.sql but have no
    -- repository/service/route anywhere in this codebase (confirmed by
    -- repo-wide search), so there is no reusable parts/action model to
    -- prefer over JSONB. Reused exactly as this MWO's own minimum field
    -- list already specifies.
    parts_replaced JSONB,
    repair_result TEXT,
    performed_by TEXT,
    notes TEXT,
    source_reference TEXT,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_seal_repair_result CHECK (
        repair_result IS NULL OR repair_result IN ('COMPLETED', 'PARTIAL', 'FAILED', 'SCRAPPED')
    )
);

CREATE INDEX IF NOT EXISTS idx_seal_repair_seal_unit
    ON public.seal_repair(seal_unit_id, repair_date, repair_id);

CREATE INDEX IF NOT EXISTS idx_seal_repair_inspection
    ON public.seal_repair(inspection_id);
