-- MWO-LTSA-SEAL-WARRANTY-ASSESSMENT-001 -- canonical mechanical-seal
-- warranty window + technical warranty assessment, layered on #6.1
-- seal_unit, #6.2 seal_lifecycle_event, and #6.3 seal_inspection.
--
-- installation_event_id anchors this row to ONE specific INSTALL
-- lifecycle event (never seal_unit.current_pump_tag_number, never
-- "the latest INSTALL" guessed implicitly) -- a seal reinstalled after
-- REMOVE/repair/RETURN_TO_STOCK gets a SECOND, fully independent
-- installation cycle and warranty row here, never overwriting the first
-- (this MWO's own REINSTALLATION TEST). No pump_tag_number column here
-- by design: the authoritative pump-at-installation is always resolvable
-- via installation_event_id -> seal_lifecycle_event.pump_tag_number
-- (INSTALL always carries a pump per #6.2's own pump_required rule),
-- never duplicated/denormalized onto this table.
--
-- window_status (installation_date/warranty_end/WITHIN|OUT|INSUFFICIENT)
-- is a system-computed TIME calculation. decision_status (PENDING_
-- EXAMINATION/ACCEPTED/REJECTED/NOT_APPLICABLE) is a separate, explicit,
-- human technical/business decision -- this MWO's own CRITICAL
-- DISTINCTION. The application layer (seal_warranty_service.py) is the
-- only writer, and never sets ACCEPTED/REJECTED automatically.
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.seal_warranty_assessment (
    assessment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seal_unit_id UUID NOT NULL REFERENCES public.seal_unit(seal_unit_id),
    installation_event_id UUID NOT NULL REFERENCES public.seal_lifecycle_event(event_id),
    inspection_id UUID REFERENCES public.seal_inspection(inspection_id),
    claim_date TIMESTAMPTZ,
    failure_date TIMESTAMPTZ,
    -- Copied from installation_event.event_at at creation time (never
    -- re-derived later): seal_lifecycle_event is itself append-only/
    -- immutable (#6.2), so this is a stable denormalization of an
    -- already-immutable fact, not a second source of truth.
    installation_date TIMESTAMPTZ NOT NULL,
    warranty_end TIMESTAMPTZ NOT NULL,
    window_status TEXT NOT NULL,
    decision_status TEXT NOT NULL DEFAULT 'PENDING_EXAMINATION',
    technical_reason TEXT,
    decision_reason TEXT,
    source_reference TEXT,
    assessed_by TEXT,
    decided_by TEXT,
    created_by TEXT NOT NULL,
    assessed_at TIMESTAMPTZ,
    decided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_seal_warranty_window_status CHECK (
        window_status IN ('WITHIN_WARRANTY_WINDOW', 'OUT_OF_WARRANTY', 'INSUFFICIENT_DATA')
    ),
    CONSTRAINT chk_seal_warranty_decision_status CHECK (
        decision_status IN ('PENDING_EXAMINATION', 'ACCEPTED', 'REJECTED', 'NOT_APPLICABLE')
    )
);

CREATE INDEX IF NOT EXISTS idx_seal_warranty_assessment_seal_unit
    ON public.seal_warranty_assessment(seal_unit_id, installation_date, assessment_id);

CREATE INDEX IF NOT EXISTS idx_seal_warranty_assessment_installation_event
    ON public.seal_warranty_assessment(installation_event_id);

CREATE INDEX IF NOT EXISTS idx_seal_warranty_assessment_inspection
    ON public.seal_warranty_assessment(inspection_id);
