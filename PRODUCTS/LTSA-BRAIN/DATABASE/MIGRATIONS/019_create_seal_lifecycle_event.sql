-- MWO-LTSA-SEAL-LIFECYCLE-EVENT-LEDGER-001 -- the canonical append-only
-- historical-truth ledger for physical mechanical seals, distinct from
-- both seal_unit (this table's own current-state snapshot: status /
-- current_pump_tag_number, deliberately never reconstructed from history)
-- and record_change_history (administrative/audit history of stored-
-- value corrections, never repurposed as a lifecycle model -- see
-- migration 018's own header). A physical seal's real timeline
-- (REGISTERED/INSTALL/REMOVE/inspection/repair/RETURN_TO_STOCK/SCRAP)
-- lives here, and only here.
--
-- No MOVE event: moving a seal between pumps is represented honestly as
-- REMOVE (old pump) followed by a separate INSTALL (new pump) row --
-- never a single event that would hide which pump it came from.
--
-- event_type is a controlled vocabulary via CHECK constraint (the same
-- convention CANONICAL_SCHEMA.sql already uses for status-shaped enum
-- columns elsewhere, e.g. trigger_type -- confirmed by grep, reused
-- rather than a second convention), never a free-text column.
--
-- Append-only by omission, not by trigger: no repository method for
-- UPDATE/DELETE on this table exists anywhere in application code (the
-- exact same discipline record_change_history's own migration 017
-- already established) -- this migration adds no trigger.
--
-- created_by is TEXT NOT NULL (server-derived authenticated actor id,
-- never request-supplied) and event_at/created_at are TIMESTAMPTZ (this
-- table's own historical-truth purpose makes timezone-aware timestamps
-- load-bearing, unlike the rest of this schema's existing TIMESTAMP
-- columns) -- event_at is the real-world moment the event occurred
-- (caller-supplied, e.g. backdating a legacy paper record), created_at
-- is when this ledger row was written (always NOW(), never backdated).
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.seal_lifecycle_event (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seal_unit_id UUID NOT NULL REFERENCES public.seal_unit(seal_unit_id),
    event_type TEXT NOT NULL,
    pump_tag_number VARCHAR(100) REFERENCES public.ltsa_pumps(tag_number),
    event_at TIMESTAMPTZ NOT NULL,
    reason TEXT,
    notes TEXT,
    source_reference TEXT,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_seal_lifecycle_event_type CHECK (
        event_type IN (
            'REGISTERED', 'INSTALL', 'REMOVE', 'SEND_FOR_INSPECTION', 'INSPECTION_COMPLETED',
            'SEND_FOR_REPAIR', 'REPAIR_COMPLETED', 'RETURN_TO_STOCK', 'SCRAP'
        )
    )
);

-- Chronological query readiness (#6.6's own future consumer, no schema
-- redesign needed): event_at ASC with a deterministic tie-break
-- (event_id) is the ORDER BY this migration's own indexes are shaped
-- for, by seal_unit and independently by pump.
CREATE INDEX IF NOT EXISTS idx_seal_lifecycle_event_seal_unit
    ON public.seal_lifecycle_event(seal_unit_id, event_at, event_id);

CREATE INDEX IF NOT EXISTS idx_seal_lifecycle_event_pump
    ON public.seal_lifecycle_event(pump_tag_number, event_at, event_id);
