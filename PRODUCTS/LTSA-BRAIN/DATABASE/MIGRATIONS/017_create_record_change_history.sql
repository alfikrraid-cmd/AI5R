-- MWO-LTSA-AUDIT-CHANGE-HISTORY-001 -- canonical, append-only field-level
-- change history for the generic "Edit Value" correction mechanism.
--
-- Phase 0 confirmed: no audit_log/change_history/audit_trail table exists
-- anywhere in this repository (repo-wide grep, zero matches). This is the
-- ONE new ledger this MWO adds -- reused by every domain (CMON,
-- Installation, and any future PM/CM/master-data correction), never a
-- second table per domain, per this MWO's own "NO duplicate ledger" rule.
--
-- Immutability is enforced by omission, not by a DB trigger: no
-- repository method for UPDATE/DELETE on this table exists anywhere in
-- application code (RecordChangeHistoryRepository exposes only append()
-- and list_for_entity()) -- the same "no code path exists" discipline
-- document_field_extraction's own review history already relies on for
-- its own immutable fields.
--
-- old_value/new_value are nullable TEXT: a real SQL NULL in the column
-- means "the canonical value was/became NULL"; the literal text '0'
-- means the value was/became zero -- these are never conflated (Hard
-- Rule: "0 must remain distinct from NULL"). Every value is stored as
-- its plain string representation -- this table records WHAT changed
-- for human/audit review, not a typed replica of every domain's own
-- column types (which already live in the domain's own canonical table).
--
-- reason is NOT NULL -- every correction must be justified (Hard Rule:
-- "reason REQUIRED"). changed_by is NOT NULL and UUID -- always a real
-- authenticated actor, never NULL, never a spoofable string (server-
-- derived only, the same discipline created_by/updated_by already use
-- throughout this schema).
--
-- source_reference is nullable TEXT -- an optional pointer to original
-- source evidence/provenance (e.g. a pm_cm_evidence evidence_id, or a
-- document_field_extraction id) for a correction that has one; NEVER a
-- write path to the original evidence itself (Hard Rule: "NEVER
-- overwrite original uploaded/source evidence" -- this table only ever
-- references it, never mutates it).

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.record_change_history (
    change_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by UUID NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    reason TEXT NOT NULL,
    source_reference TEXT
);

CREATE INDEX IF NOT EXISTS idx_record_change_history_entity
    ON public.record_change_history(entity_type, entity_id, changed_at DESC);
