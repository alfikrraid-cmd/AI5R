-- MWO-LTSA-HISTORICAL-SEAL-SERVICE-ACTIVITY-001
-- Append-only historical service activity ledger for mechanical seals (2024-2025).
--
-- MANDATORY ARCHITECTURAL PRINCIPLES:
-- 1. HISTORY ONLY: Historical service activities are chronological lifecycle evidence;
--    they MUST NOT establish or overwrite Current Installation snapshots.
-- 2. CANONICAL DATE: Finish Date is the authoritative event_date. Start Date or
--    Failure Date may remain as raw metadata but never replace missing Finish Date.
-- 3. CONSERVATIVE ASSET MATCHING: Only EXACT and NORMALIZED_EXACT tags are linked
--    to pump_tag_number (FK to public.ltsa_pumps). AMBIGUOUS (missing suffix)
--    and NO_MATCH tags remain unlinked (pump_tag_number IS NULL) for human review.
-- 4. IDEMPOTENT: Enforced by UNIQUE (source_reference). Re-running import causes
--    zero duplicate entries.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.historical_seal_service_activity (
    activity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_reference TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL DEFAULT 'SERVICE_ACTIVITY',
    source_year INTEGER NOT NULL,
    source_filename TEXT NOT NULL,
    source_worksheet TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    source_job_document_number TEXT,
    sp_no TEXT,
    raw_tag TEXT NOT NULL,
    pump_tag_number VARCHAR(100) REFERENCES public.ltsa_pumps(tag_number),
    tag_match_outcome TEXT NOT NULL,
    raw_job_description TEXT,
    event_type TEXT NOT NULL DEFAULT 'INSTALLATION',
    failure_attribution TEXT NOT NULL DEFAULT 'UNKNOWN',
    seal_type TEXT,
    seal_size TEXT,
    drawing_number TEXT,
    quantity INTEGER DEFAULT 1,
    shaft_sleeve_condition TEXT,
    gland_plate_condition TEXT,
    team_service TEXT,
    end_user TEXT,
    location TEXT,
    ltsa_area TEXT,
    unit_area TEXT,
    api_plan TEXT,
    pump_type TEXT,
    process_fluid TEXT,
    source_start_date DATE,
    source_failure_date DATE,
    finish_date DATE,
    event_date DATE,
    date_status TEXT NOT NULL,
    status TEXT,
    remarks TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hssa_pump_tag
    ON public.historical_seal_service_activity(pump_tag_number, event_date);

CREATE INDEX IF NOT EXISTS idx_hssa_raw_tag
    ON public.historical_seal_service_activity(raw_tag);

CREATE INDEX IF NOT EXISTS idx_hssa_match_outcome
    ON public.historical_seal_service_activity(tag_match_outcome);

CREATE INDEX IF NOT EXISTS idx_hssa_source_ref
    ON public.historical_seal_service_activity(source_reference);
