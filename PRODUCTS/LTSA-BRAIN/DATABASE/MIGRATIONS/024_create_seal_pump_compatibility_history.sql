-- MWO-LTSA-LEGACY-SEAL-COMPATIBILITY-EVIDENCE-001
-- Preserve valid compatibility evidence for retired/noncanonical pump tags
-- without weakening the active seal_pump_compatibility -> ltsa_pumps FK.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.seal_pump_compatibility_history (
    compatibility_history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seal_code TEXT NOT NULL REFERENCES public.seal_registry(seal_code),
    original_pump_tag_number VARCHAR(100) NOT NULL,
    original_compatibility_key TEXT NOT NULL,
    original_notes TEXT,
    original_created_at TIMESTAMP,
    source_reference TEXT,
    retirement_reason TEXT NOT NULL,
    retired_by TEXT,
    retired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT seal_pump_compatibility_history_unique_original
        UNIQUE (seal_code, original_pump_tag_number)
);

CREATE INDEX IF NOT EXISTS idx_seal_pump_compatibility_history_seal_code
    ON public.seal_pump_compatibility_history(seal_code);

CREATE INDEX IF NOT EXISTS idx_seal_pump_compatibility_history_original_pump
    ON public.seal_pump_compatibility_history(original_pump_tag_number);
