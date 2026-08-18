-- MWO-LTSA-PM-CM-INTAKE-001
--
-- Additive only. Two domains gain real workflow/attribution columns, plus
-- one new shared evidence table.
--
-- Domain correction (Chief Architect directive, this MWO): the business
-- "CM" in the historical John Crane / Pertamina daily reports (titled
-- "MECHANICAL SEAL CONDITION MONITORING") means Condition Monitoring, not
-- Corrective Maintenance. cm_report (failure_category/severity/
-- root_cause/corrective_action) is a DIFFERENT, pre-existing domain
-- (ADR-CM-001) and is untouched by this migration -- every column below
-- targets pm_occurrence and condition_monitoring_reading only.
--
-- Golden evidence (read directly this session): two full "Mechanical
-- Seal Condition Monitoring" John Crane/Pertamina reports (2026-07-13,
-- 2026-07-28, 25 equipment sheets total) plus a December 2022 combined
-- "Laporan PM, CM & Pemasangan Seal" monthly report (John Crane/PT Tommy
-- Adji Prasetyo/Pertamina RU II Dumai) -- the latter's page 34/35 is the
-- source for the PM cleaning-activities checklist (33 named items:
-- Flushing Line/DE/NDE, Quench Line, Strainer/DE/NDE, Check Valve DE/
-- NDE, Reservoir, Cooler/DE/NDE, Cooling Water Cooler Line/DE/NDE).
--
-- condition_monitoring_reading measurement gap: the existing (uncommitted
-- working-tree) table already has flushing/quench/cooling-water/mechseal
-- temps split DE/NDE, mechanical_seal_leak_de/nde (boolean), suction_temp,
-- discharge_temp, pump_operating_state -- a near-exact match to the
-- golden reports' "Check Points" tables. Confirmed MISSING against the
-- golden evidence: suction/discharge PRESSURE (only temp existed),
-- quench pressure (DE/NDE), stuffing box temp (DE/NDE) and seal gland
-- temp (DE/NDE) as their own named fields (the existing mechseal_temp_de/
-- nde column is ambiguous relative to the golden report's two distinct
-- rows "Stuffing box temp" and "Seal gland temp" -- left untouched,
-- disclosed as an open naming question, not silently reinterpreted),
-- vertical/horizontal/axial vibration (DE/NDE), bearing temp (DE/NDE),
-- motor current, and any free-text finding. Per this MWO's own Phase 1
-- instruction ("extend CMON canonically rather than creating a parallel
-- CM table"), these are added here in the same flat, explicitly-named,
-- DE/NDE-suffixed NUMERIC style the table already uses -- not a JSONB
-- bag, since that would introduce a second convention into one table
-- (Golden Rule: architecture is frozen unless explicitly requested).
--
-- pm_occurrence gains an `activities JSONB` checklist (the 33-item golden
-- structure: [{code, description, side, done}]) -- JSONB here matches
-- this table's OWN pre-existing `checklist_completion JSONB` column and
-- the exact reasoning already recorded in this file's own header comment
-- for why PM occurrence was split from maintenance_history in the first
-- place ("needs a checklist-completion matrix maintenance_history can't
-- hold"). `activities` is additive alongside (not a replacement for)
-- checklist_completion, since HOC-imported historical rows already
-- populate that column with unknown internal shape and must not be
-- silently reinterpreted.
--
-- Workflow/attribution columns are IDENTICAL and additive on both tables
-- (Phase 9/10): workflow_status (DRAFT default, matching this MWO's
-- draft-first mandate -- NOT the pre-existing `status` column on either
-- table, which already carries different, HOC-import-populated meaning
-- ('DONE'/'ACTIVE'/'OPEN' family) that this migration must not collide
-- with or reinterpret), submitted_by/submitted_at, reviewed_by/
-- reviewed_at/return_reason (TAP administrative review -- Phase 12),
-- technical_reviewed_by/technical_reviewed_at/technical_outcome/
-- technical_comment (John Crane technical review -- Phase 13),
-- preliminary_recommendation vs technical_recommendation (Phase 14: two
-- distinct, never-overwritten-into-each-other columns), created_by/
-- updated_by (Phase 9, the migration-012 attribution pattern -- plain
-- UUID, no DB FK, since `users` does not exist in this bootstrap file at
-- all), provenance (Phase 8, the smallest form of the requested MANUAL/
-- IMPORTED/AI_EXTRACTED/VERIFIED/SYSTEM vocabulary -- applied at record
-- level, not a second per-field provenance engine, defaulting MANUAL so
-- the zero-AI manual workflow is always the default truth per Hard Rule
-- 3/4).
--
-- workflow_status vocabulary: DRAFT / SUBMITTED / RETURNED_FOR_CORRECTION
-- / FINALIZED. FINALIZED is set exactly when John Crane's technical
-- review concludes with ACKNOWLEDGED or TECHNICALLY_APPROVED (Phase 15:
-- a finalized record must not be silently rewritten). A John Crane
-- "return for technical correction" (Phase 13) reuses the SAME
-- RETURNED_FOR_CORRECTION workflow_status TAP administrative review
-- already uses, distinguished only by which actor/timestamp/comment
-- columns are populated (technical_reviewed_by vs reviewed_by) -- no
-- second return vocabulary invented.
ALTER TABLE public.pm_occurrence
    ADD COLUMN IF NOT EXISTS activities JSONB,
    ADD COLUMN IF NOT EXISTS finding TEXT,
    ADD COLUMN IF NOT EXISTS preliminary_recommendation TEXT,
    ADD COLUMN IF NOT EXISTS remarks TEXT,
    ADD COLUMN IF NOT EXISTS provenance TEXT DEFAULT 'MANUAL',
    ADD COLUMN IF NOT EXISTS workflow_status TEXT DEFAULT 'DRAFT',
    ADD COLUMN IF NOT EXISTS submitted_by UUID,
    ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS reviewed_by UUID,
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS return_reason TEXT,
    ADD COLUMN IF NOT EXISTS technical_reviewed_by UUID,
    ADD COLUMN IF NOT EXISTS technical_reviewed_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS technical_outcome TEXT,
    ADD COLUMN IF NOT EXISTS technical_comment TEXT,
    ADD COLUMN IF NOT EXISTS technical_recommendation TEXT,
    ADD COLUMN IF NOT EXISTS created_by UUID,
    ADD COLUMN IF NOT EXISTS updated_by UUID;

ALTER TABLE public.condition_monitoring_reading
    ADD COLUMN IF NOT EXISTS suction_pressure NUMERIC,
    ADD COLUMN IF NOT EXISTS discharge_pressure NUMERIC,
    ADD COLUMN IF NOT EXISTS quench_pressure_de NUMERIC,
    ADD COLUMN IF NOT EXISTS quench_pressure_nde NUMERIC,
    ADD COLUMN IF NOT EXISTS stuffing_box_temp_de NUMERIC,
    ADD COLUMN IF NOT EXISTS stuffing_box_temp_nde NUMERIC,
    ADD COLUMN IF NOT EXISTS seal_gland_temp_de NUMERIC,
    ADD COLUMN IF NOT EXISTS seal_gland_temp_nde NUMERIC,
    ADD COLUMN IF NOT EXISTS vertical_vibration_de NUMERIC,
    ADD COLUMN IF NOT EXISTS vertical_vibration_nde NUMERIC,
    ADD COLUMN IF NOT EXISTS horizontal_vibration_de NUMERIC,
    ADD COLUMN IF NOT EXISTS horizontal_vibration_nde NUMERIC,
    ADD COLUMN IF NOT EXISTS axial_vibration_de NUMERIC,
    ADD COLUMN IF NOT EXISTS axial_vibration_nde NUMERIC,
    ADD COLUMN IF NOT EXISTS bearing_temp_de NUMERIC,
    ADD COLUMN IF NOT EXISTS bearing_temp_nde NUMERIC,
    ADD COLUMN IF NOT EXISTS motor_current NUMERIC,
    ADD COLUMN IF NOT EXISTS finding TEXT,
    ADD COLUMN IF NOT EXISTS provenance TEXT DEFAULT 'MANUAL',
    ADD COLUMN IF NOT EXISTS workflow_status TEXT DEFAULT 'DRAFT',
    ADD COLUMN IF NOT EXISTS submitted_by UUID,
    ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS reviewed_by UUID,
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS return_reason TEXT,
    ADD COLUMN IF NOT EXISTS technical_reviewed_by UUID,
    ADD COLUMN IF NOT EXISTS technical_reviewed_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS technical_outcome TEXT,
    ADD COLUMN IF NOT EXISTS technical_comment TEXT,
    ADD COLUMN IF NOT EXISTS technical_recommendation TEXT,
    ADD COLUMN IF NOT EXISTS created_by UUID,
    ADD COLUMN IF NOT EXISTS updated_by UUID;

-- Evidence attachments (Phase 6/22). No object-storage/S3/filesystem
-- mechanism exists anywhere in this repository today (confirmed by
-- architecture audit: seal_engineering_document/document_field_extraction
-- store only metadata/text; the one existing file-upload route,
-- POST /api/ltsa/import/pump-xlsx/dry-run, explicitly deletes the temp
-- file after parsing and leaves nothing behind). Rather than fabricate a
-- new filesystem/S3 dependency this MWO has no evidence is safe to add,
-- file bytes are stored in the same canonical Postgres database every
-- other durable LTSA table already uses (BYTEA) -- a real, disclosed,
-- minimal choice, not a mock. A dedicated object-storage MWO is the
-- correct place to migrate this later if evidence volume outgrows it.
-- record_type/record_code is an informal polymorphic reference (the same
-- non-FK convention already used throughout this schema for asset_code/
-- work_order_code) -- one evidence table serves both PM and Condition
-- Monitoring rather than duplicating it per domain.
CREATE TABLE IF NOT EXISTS public.pm_cm_evidence (
    evidence_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    record_type TEXT NOT NULL CHECK (record_type IN ('PM_OCCURRENCE', 'CONDITION_MONITORING_READING')),
    record_code TEXT NOT NULL,
    file_name TEXT NOT NULL,
    content_type TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    file_data BYTEA NOT NULL,
    category TEXT CHECK (category IS NULL OR category IN ('PHOTO', 'REPORT', 'MEASUREMENT', 'OTHER')),
    source TEXT DEFAULT 'MANUAL',
    uploaded_by UUID,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pm_cm_evidence_record ON public.pm_cm_evidence(record_type, record_code);
