-- MWO-LTSA-SEAL-INSTALLATION-FITMENT-001 -- the smallest linkage needed
-- between installation_report (engineering installation EVIDENCE) and
-- the exact seal_lifecycle_event row that is the authoritative physical
-- installation EVENT (event_type = 'INSTALL'). No new table: this
-- migration only adds the one missing FK column to the existing
-- installation_report table (migration 018 already added seal_unit_id/
-- pump_tag_number there for the same reason -- extended here, not
-- duplicated).
--
-- Nullable by design: a legacy or not-yet-linked installation_report
-- remains fully valid with installation_event_id = NULL (this MWO's own
-- explicit LEGACY REPORTS rule) -- never fabricated or guessed.
--
-- Immutability is enforced in application code (installation_fitment_
-- service.py's own guarded link_installation()), not by a DB trigger --
-- the same "append-only/immutable by omission, not by trigger"
-- discipline migrations 019-021 already established for this schema.
-- linked_by/link_reason: the server-derived actor and the required
-- reason for the link action itself (this MWO's own ACTOR/LEGACY
-- REPORTS rules -- "reason required for linking an existing legacy
-- report"). installation_report has no created_by/updated_by column at
-- all (unlike every other seal-domain table); rather than invent a
-- second audit mechanism (record_change_history stays administrative-
-- correction-only, never repurposed), these two columns record the one
-- fact this MWO's own linkage action needs, on the same row, written in
-- the same atomic guarded UPDATE that performs the link.
ALTER TABLE public.installation_report
    ADD COLUMN IF NOT EXISTS installation_event_id UUID REFERENCES public.seal_lifecycle_event(event_id),
    ADD COLUMN IF NOT EXISTS linked_by TEXT,
    ADD COLUMN IF NOT EXISTS link_reason TEXT;

CREATE INDEX IF NOT EXISTS idx_installation_report_installation_event_id
    ON public.installation_report(installation_event_id);
