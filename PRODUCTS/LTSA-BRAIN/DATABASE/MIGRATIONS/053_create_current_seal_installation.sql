-- Migration 053: LTSA Current Mechanical Seal Installation Foundation (R3A.5 / R3B)
-- Lineage: migration 052 (052_create_drawing_storage_and_linkage.sql)
-- Additive only; safe to run against an existing database.
-- NOTE: In preflight mode (R3A_5), this migration is authored and validated
-- locally but NOT applied to production.

CREATE TABLE IF NOT EXISTS public.current_seal_installation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pump_tag_number VARCHAR(100) NOT NULL REFERENCES public.ltsa_pumps(tag_number),
    equipment_side TEXT NOT NULL CHECK (equipment_side IN ('DE', 'NDE', 'SINGLE', 'NA')),
    seal_type TEXT,
    seal_size TEXT,
    drawing_no TEXT,
    assembly_gpn TEXT,
    material_code TEXT,
    source_type TEXT NOT NULL,
    source_reference TEXT,
    source_date DATE,
    resolution_status TEXT NOT NULL CHECK (resolution_status IN ('CONFIRMED', 'TYPE_ONLY', 'REVIEW_REQUIRED')),
    confidence_status TEXT NOT NULL,
    installed_at TIMESTAMPTZ,
    removed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Invariant: At most ONE active record per physical position (pump_tag_number, equipment_side)
-- regardless of resolution_status (CONFIRMED, TYPE_ONLY, REVIEW_REQUIRED).
-- Historical/superseded records have removed_at IS NOT NULL.
CREATE UNIQUE INDEX IF NOT EXISTS idx_current_seal_installation_active
    ON public.current_seal_installation (pump_tag_number, equipment_side)
    WHERE removed_at IS NULL;

-- Fast lookup by pump_tag_number
CREATE INDEX IF NOT EXISTS idx_current_seal_installation_pump_tag
    ON public.current_seal_installation (pump_tag_number);

-- Audit / lineage lookup by source reference
CREATE INDEX IF NOT EXISTS idx_current_seal_installation_source_ref
    ON public.current_seal_installation (source_reference);

-- Rollback instructions (DOWN migration):
-- DROP INDEX IF EXISTS public.idx_current_seal_installation_source_ref;
-- DROP INDEX IF EXISTS public.idx_current_seal_installation_pump_tag;
-- DROP INDEX IF EXISTS public.idx_current_seal_installation_active;
-- DROP TABLE IF EXISTS public.current_seal_installation;
