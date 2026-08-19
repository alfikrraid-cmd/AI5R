-- LTSA-BRAIN Canonical Database Schema
-- Produced by: MWO-P-002 / IR-001 (Database Canonicalization)
-- Scope: ltsa_pumps, customer, pump (per MWO-P-002 IR-001 task list)
--
-- This file is the single canonical source for the three entities MWO-P-001
-- (LTSA Product Audit) found with conflicting definitions. It does not
-- introduce new tables or fields; each block below is a verbatim copy of the
-- definition selected as canonical, with its original source path noted.
--
-- Selection rule applied: prefer the definition that (a) is already queried
-- by real, non-stub runtime workflow logic, and failing that, (b) is the
-- most complete definition and matches its module's documented API contract.
--
-- Duplicate/obsolete definitions were left in place at their original paths
-- but marked with a DEPRECATED header comment pointing back here; none were
-- deleted (MWO-P-002 constraint: "Remove or archive obsolete definitions
-- only if safe" — marking, not deleting, is the safe action for tracked
-- files with git history).

-- ============================================================
-- CUSTOMER — canonical: customer_registry
-- Source: ../DATABASE/MIGRATIONS/005_create_customer_registry.sql
-- Rationale: most complete definition (14 columns); field names match
-- ../API/customer-registry/API_CONTRACT.md's documented payload
-- (customer_code, customer_name, customer_type, industry, billing_email,
-- phone, city, province). Not yet queried by any workflow (see IR-002) —
-- selected on completeness/contract-match, not runtime evidence.
-- Deprecated duplicate: ../RELEASE/database.sql `ltsa_customers` (generic,
-- 6 columns, field names do not match the API contract).
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS customer_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_code VARCHAR(50) UNIQUE NOT NULL,
    customer_name VARCHAR(255) NOT NULL,
    customer_type VARCHAR(50) DEFAULT 'company',
    industry VARCHAR(100),
    tax_id VARCHAR(100),
    billing_email VARCHAR(255),
    phone VARCHAR(100),
    address TEXT,
    city VARCHAR(100),
    province VARCHAR(100),
    country VARCHAR(100) DEFAULT 'Indonesia',
    status VARCHAR(50) DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customer_registry_code
ON customer_registry(customer_code);

CREATE INDEX IF NOT EXISTS idx_customer_registry_status
ON customer_registry(status);

-- ============================================================
-- PUMP — canonical: ltsa_pumps
-- Source: ../MODULES/PUMP/DATABASE/001_create_pumps.sql
-- Rationale: this is the exact table queried by the product's only two
-- real (non-stub) workflows — WF-LTSA-PUMP-REGISTRY-001.json (INSERT) and
-- BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-PUMP-DETAIL-001.json
-- (SELECT ... FROM public.ltsa_pumps WHERE tag_number = ...). Runtime
-- evidence takes priority over the other two candidate definitions.
-- Deprecated duplicates:
--   - ../RELEASE/database.sql `ltsa_pumps` (SERIAL PK, generic 6-column
--     shape) — same table NAME, incompatible DDL; a direct collision risk.
--   - ../BUILD-PACKS/BP-PUMP/DATABASE/001_create_table.sql `pump_registry`
--     (different table name, TEXT PK `pump_code`) — not queried by any
--     workflow.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS ltsa_pumps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tag_number VARCHAR(100) NOT NULL UNIQUE,
    area VARCHAR(100) NOT NULL,
    location VARCHAR(150),
    pump_type VARCHAR(100),
    api_plan VARCHAR(50),
    seal_type VARCHAR(150),
    status VARCHAR(50) DEFAULT 'UNKNOWN',
    manufacturer VARCHAR(150),
    model VARCHAR(150),
    drawing_ref TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ltsa_pumps_tag_number ON ltsa_pumps(tag_number);
CREATE INDEX IF NOT EXISTS idx_ltsa_pumps_area ON ltsa_pumps(area);
CREATE INDEX IF NOT EXISTS idx_ltsa_pumps_status ON ltsa_pumps(status);

-- ============================================================
-- SEAL — canonical: seal_registry (no conflict found; included for completeness)
-- Source: ../BUILD-PACKS/BP-SEAL/DATABASE/001_create_table.sql
-- Rationale: the only definition found for this entity; already consistent
-- with ../REGISTRIES/SEAL.json. No duplicate exists, so no deprecation
-- needed. Not in MWO-P-002's explicit IR-001 scope list (ltsa_pumps,
-- customer, pump) but included here so this file is a complete canonical
-- reference for every entity with more than a stub definition.
-- ============================================================

CREATE TABLE IF NOT EXISTS public.seal_registry (
    seal_code TEXT PRIMARY KEY NOT NULL,
    seal_name TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    shaft_size NUMERIC,
    material TEXT,
    temperature_limit NUMERIC,
    pressure_limit NUMERIC,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    -- MWO-LTSA-SEAL-INVENTORY-IDENTIFIERS-001 -- business identifiers
    -- hanging off canonical seal identity, not part of that identity;
    -- nullable, manually completable, never fabricated. No DB-level FK
    -- to users on created_by/updated_by: `users` does not exist in this
    -- bootstrap file at all (only migration 007 creates it) -- see
    -- migration 013's header for the full reasoning (same pattern
    -- already used by document_field_extraction.reviewed_by).
    kimap_pertamina TEXT,
    gpn_john_crane TEXT,
    created_by UUID,
    updated_by UUID
);

-- ============================================================
-- ASSET, SOOT BLOWER, WORK ORDER, MAINTENANCE HISTORY
-- Manufactured under MO-001 (OSA Maintenance v0.1), no prior conflicting
-- definitions existed for any of these four -- new tables, additive to this
-- canonical file, not a reconciliation. Sources:
--   ../BUILD-PACKS/BP-ASSET/DATABASE/001_create_table.sql
--   ../BUILD-PACKS/BP-SOOT-BLOWER/DATABASE/001_create_table.sql
--   ../BUILD-PACKS/BP-WORK-ORDER/DATABASE/001_create_table.sql
--   ../BUILD-PACKS/BP-MAINTENANCE-HISTORY/DATABASE/001_create_table.sql
-- See MANUFACTURING/MO-001/MO-001-SPECIFICATION.md for the reuse rationale.
-- ============================================================

CREATE TABLE IF NOT EXISTS public.asset_registry (
    asset_code TEXT PRIMARY KEY NOT NULL,
    asset_name TEXT NOT NULL,
    asset_type TEXT,
    area TEXT,
    manufacturer TEXT,
    model TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.soot_blower_registry (
    soot_blower_code TEXT PRIMARY KEY NOT NULL,
    soot_blower_name TEXT NOT NULL,
    boiler_area TEXT,
    blower_type TEXT,
    manufacturer TEXT,
    model TEXT,
    steam_pressure NUMERIC,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- work_order.asset_code / asset_type is an intentional polymorphic reference
-- (not a foreign key): an asset may live in pump_registry (ltsa_pumps),
-- seal_registry, asset_registry, or soot_blower_registry -- four separate
-- tables with no common supertype in this schema.
CREATE TABLE IF NOT EXISTS public.work_order (
    work_order_code TEXT PRIMARY KEY NOT NULL,
    customer_code TEXT,
    asset_code TEXT,
    asset_type TEXT,
    description TEXT NOT NULL,
    priority TEXT DEFAULT 'NORMAL',
    status TEXT DEFAULT 'OPEN',
    assigned_to TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.maintenance_history (
    maintenance_record_code TEXT PRIMARY KEY NOT NULL,
    work_order_code TEXT,
    asset_code TEXT,
    asset_type TEXT,
    action_taken TEXT NOT NULL,
    performed_by TEXT,
    performed_at TIMESTAMP DEFAULT NOW(),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- PM SCHEDULE
-- Manufactured under WO-PM-001 (implements ADR-PM-001).
--
-- Models only the recurring PLAN. Each occurrence of the plan being
-- performed is already fully canonical via work_order (work_type = 'PM')
-- and maintenance_history above -- no columns for that half exist here,
-- by design (see ADR-PM-001's Canonical Model). asset_code/asset_type is
-- the same polymorphic reference used by work_order/maintenance_history.
-- checklist is JSONB: an owned, bounded, ordered list with no independent
-- identity outside its schedule, the same convention already used by
-- document_field_extraction.extracted_fields. last_performed/next_due/
-- status are stored, not derived -- see ADR-PM-001's Open Question for why.
-- Source: ../BUILD-PACKS/BP-PM-SCHEDULE/DATABASE/001_create_table.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS public.pm_schedule (
    pm_schedule_code TEXT PRIMARY KEY NOT NULL,
    asset_code TEXT,
    asset_type TEXT,
    procedure TEXT NOT NULL,
    frequency TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    checklist JSONB,
    assigned_to TEXT,
    estimated_duration_hours NUMERIC,
    next_due TIMESTAMP,
    last_performed TIMESTAMP,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- PM OCCURRENCE
-- Manufactured under WO-PMOCC-001 (implements ADR-PM-OCCURRENCE-001).
--
-- The Occurrence half of pm_schedule's Plan/Occurrence split, superseding
-- ADR-PM-001's original "PM Occurrence = a maintenance_history record,
-- optionally linked to a Work Order with work_type = 'PM'" ruling once
-- real evidence (DISCOVERY-LTSA-REPORT-001's report section 5, "PM Mech
-- Seal") showed routine PM visits are not Work-Order-dispatched and carry
-- a per-accessory checklist-completion matrix neither work_order nor
-- maintenance_history can hold. Structurally the direct counterpart to
-- condition_monitoring_reading below: asset_code/asset_type denormalized
-- for query convenience; api_plan/area are Derived from ltsa_pumps/the
-- Asset registry, never duplicated here. pm_schedule_code is a required,
-- informal reference (no FK) to the owning Schedule. work_order_code is
-- optional and informal (no FK) -- not evidenced as typical, included
-- only for consistency with maintenance_history.work_order_code /
-- cm_report.work_order_code's established convention. status defaults to
-- 'DONE' -- the only value evidenced in the source report's sampled rows.
-- Source: ../BUILD-PACKS/BP-PM-OCCURRENCE/DATABASE/001_create_table.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS public.pm_occurrence (
    pm_occurrence_code TEXT PRIMARY KEY NOT NULL,
    pm_schedule_code TEXT NOT NULL,
    asset_code TEXT,
    asset_type TEXT,
    occurrence_date TIMESTAMP,
    status TEXT DEFAULT 'DONE',
    checklist_completion JSONB,
    work_order_code TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    -- MWO-LTSA-PM-CM-INTAKE-001 -- real draft/submit/review workflow;
    -- see migration 014's own header for the full column-by-column
    -- reasoning (activities is additive alongside checklist_completion,
    -- workflow_status is a new column deliberately distinct from the
    -- pre-existing status column above).
    activities JSONB,
    finding TEXT,
    preliminary_recommendation TEXT,
    remarks TEXT,
    provenance TEXT DEFAULT 'MANUAL',
    workflow_status TEXT DEFAULT 'DRAFT',
    submitted_by UUID,
    submitted_at TIMESTAMP,
    reviewed_by UUID,
    reviewed_at TIMESTAMP,
    return_reason TEXT,
    technical_reviewed_by UUID,
    technical_reviewed_at TIMESTAMP,
    technical_outcome TEXT,
    technical_comment TEXT,
    technical_recommendation TEXT,
    created_by UUID,
    updated_by UUID,
    -- MWO-LTSA-HISTORICAL-JULY-INGESTION-001 -- informal pointer back to
    -- the document_field_extraction staging row a historically-imported
    -- record was promoted from (e.g. "document_field_extraction:<id>"),
    -- the smallest canonical extension needed to answer "which historical
    -- report produced this record" (Phase 16). Same non-FK, application-
    -- resolved convention as every other cross-entity reference in this
    -- schema. NULL for every record created through the real digital
    -- workflow (this MWO's own new capability, not a change to existing
    -- behavior).
    source_reference TEXT
);

-- ============================================================
-- CM REPORT
-- Manufactured under WO-CM-001 (implements ADR-CM-001).
--
-- A standalone Corrective Maintenance failure record. asset_code/
-- asset_type is the same polymorphic reference used by work_order/
-- maintenance_history/pm_schedule. work_order_code is an optional,
-- informal reference -- a CM Report may exist without ever having a
-- Work Order (ADR-CM-001's Canonical Model), so no FK is declared.
-- priority/assigned_to/failure_description intentionally overlap in
-- shape with work_order's own priority/assigned_to/description --
-- a disclosed, non-duplicative overlap per ADR-CM-001 (the two
-- objects have independent existence and may legitimately diverge
-- once both exist). status uses its own OPEN/IN_PROGRESS/RESOLVED/
-- CLOSED vocabulary, distinct from work_order.status.
-- Source: ../BUILD-PACKS/BP-CM-REPORT/DATABASE/001_create_table.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS public.cm_report (
    cm_report_code TEXT PRIMARY KEY NOT NULL,
    asset_code TEXT,
    asset_type TEXT,
    work_order_code TEXT,
    failure_category TEXT NOT NULL,
    severity TEXT NOT NULL,
    priority TEXT,
    failure_description TEXT NOT NULL,
    root_cause TEXT,
    immediate_action TEXT,
    corrective_action TEXT,
    downtime_hours NUMERIC,
    assigned_to TEXT,
    status TEXT DEFAULT 'OPEN',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- CONDITION MONITORING SCHEDULE / READING
-- Manufactured under WO-CMON-001 (implements ADR-CONDITION-MONITORING-001).
--
-- A recurring, scheduled mechanical-seal inspection domain -- deliberately
-- NOT the same domain as cm_report (Corrective Maintenance) above. Real-
-- world "Condition Monitoring" (a scheduled, weekly-per-pump inspection)
-- and cm_report's "CM Report" (Corrective Maintenance, a reactive
-- failure record) share an acronym only, per DISCOVERY-LTSA-REPORT-001 /
-- DISCOVERY-CONDITION-MONITORING-001 -- hence this domain's short code is
-- CMON, never a bare CM, and neither table references cm_report.
--
-- Two entities, a Plan and its Occurrence:
--   condition_monitoring_schedule owns frequency and applicable_parameters
--   (JSONB) only -- api_plan and area are Derived from ltsa_pumps, never
--   duplicated here. No status column: no vocabulary is evidenced in the
--   source document, left as an Open Question rather than fabricated.
--
--   condition_monitoring_reading is a dense, append-only measurement log:
--   DE/NDE-split temperatures, a leak Y/N flag per side, single-point
--   suction/discharge, and a nullable pump_operating_state (present in the
--   source report's own format definition; population in the sampled data
--   was unconfirmed, so it is stored honestly nullable).
--   condition_monitoring_schedule_code is a required, informal reference
--   back to the owning Schedule (no DB-level FK, same non-FK convention as
--   every cross-entity reference in this product).
-- Source: ../BUILD-PACKS/BP-CONDITION-MONITORING/DATABASE/001_create_table.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS public.condition_monitoring_schedule (
    condition_monitoring_schedule_code TEXT PRIMARY KEY NOT NULL,
    asset_code TEXT,
    asset_type TEXT,
    frequency TEXT,
    applicable_parameters JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.condition_monitoring_reading (
    condition_monitoring_reading_code TEXT PRIMARY KEY NOT NULL,
    condition_monitoring_schedule_code TEXT NOT NULL,
    asset_code TEXT,
    asset_type TEXT,
    reading_date TIMESTAMP,
    flushing_temp_de NUMERIC,
    flushing_temp_nde NUMERIC,
    quench_temp_de NUMERIC,
    quench_temp_nde NUMERIC,
    flushing_in_temp_de NUMERIC,
    flushing_in_temp_nde NUMERIC,
    flushing_out_temp_de NUMERIC,
    flushing_out_temp_nde NUMERIC,
    cooling_water_in_temp_de NUMERIC,
    cooling_water_in_temp_nde NUMERIC,
    cooling_water_out_temp_de NUMERIC,
    cooling_water_out_temp_nde NUMERIC,
    mechseal_temp_de NUMERIC,
    mechseal_temp_nde NUMERIC,
    mechanical_seal_leak_de BOOLEAN,
    mechanical_seal_leak_nde BOOLEAN,
    water_jacket_temp_de NUMERIC,
    water_jacket_temp_nde NUMERIC,
    suction_temp NUMERIC,
    discharge_temp NUMERIC,
    pump_operating_state TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    -- MWO-LTSA-PM-CM-INTAKE-001 -- measurement fields confirmed present
    -- in the golden "Mechanical Seal Condition Monitoring" reports but
    -- missing from the columns above, plus the same workflow/attribution
    -- shape pm_occurrence gains above; see migration 014's header for the
    -- full reasoning (mechseal_temp_de/nde above is left untouched and
    -- ambiguous relative to the golden report's separate "Stuffing box
    -- temp"/"Seal gland temp" rows -- both are added here as their own
    -- named columns rather than guessing which one mechseal_temp meant).
    suction_pressure NUMERIC,
    discharge_pressure NUMERIC,
    quench_pressure_de NUMERIC,
    quench_pressure_nde NUMERIC,
    stuffing_box_temp_de NUMERIC,
    stuffing_box_temp_nde NUMERIC,
    seal_gland_temp_de NUMERIC,
    seal_gland_temp_nde NUMERIC,
    vertical_vibration_de NUMERIC,
    vertical_vibration_nde NUMERIC,
    horizontal_vibration_de NUMERIC,
    horizontal_vibration_nde NUMERIC,
    axial_vibration_de NUMERIC,
    axial_vibration_nde NUMERIC,
    bearing_temp_de NUMERIC,
    bearing_temp_nde NUMERIC,
    motor_current NUMERIC,
    finding TEXT,
    provenance TEXT DEFAULT 'MANUAL',
    workflow_status TEXT DEFAULT 'DRAFT',
    submitted_by UUID,
    submitted_at TIMESTAMP,
    reviewed_by UUID,
    reviewed_at TIMESTAMP,
    return_reason TEXT,
    technical_reviewed_by UUID,
    technical_reviewed_at TIMESTAMP,
    technical_outcome TEXT,
    technical_comment TEXT,
    technical_recommendation TEXT,
    created_by UUID,
    updated_by UUID,
    -- MWO-LTSA-HISTORICAL-JULY-INGESTION-001 -- see pm_occurrence.
    -- source_reference's own comment; identical purpose/convention here.
    source_reference TEXT
);

-- ============================================================
-- PM / CONDITION MONITORING EVIDENCE
-- Manufactured under MWO-LTSA-PM-CM-INTAKE-001.
--
-- No object-storage/S3/filesystem mechanism exists anywhere in this
-- repository (confirmed by architecture audit before writing this table);
-- file bytes are stored in the same canonical Postgres database every
-- other durable LTSA table already uses, a disclosed minimal choice, not
-- a mock. record_type/record_code is an informal polymorphic reference
-- (the same non-FK convention already used throughout this schema),
-- shared by both PM Occurrence and Condition Monitoring Reading rather
-- than duplicated per domain.
-- ============================================================

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

-- ============================================================
-- MWO-LTSA-HOC-PM-CM (HOC PM/CM Historical Data Ingestion) -- idempotent
-- upgrade path, applied against a database that already has pm_occurrence/
-- cm_report/condition_monitoring_reading in their pre-HOC shape.
--
-- Provenance: pm_occurrence, cm_report, and condition_monitoring_reading
-- previously had no way to trace an imported row back to its source cell,
-- unlike internal_component_master/internal_component_stock above (which
-- already established source_workbook_name/source_sheet_name/
-- source_row_number). Extended with the exact same 3-column convention so
-- a bulk-imported historical workbook (e.g. "CM & PM Summary HOC
-- JUNI.xlsx") is auditable the same way.
--
-- failure_date (cm_report only): every other occurrence-shaped table here
-- already has a real "when did this happen" column distinct from
-- created_at/updated_at (pm_occurrence.occurrence_date,
-- condition_monitoring_reading.reading_date) -- cm_report did not. Without
-- it, a historical finding's real date is unrecoverable from import time.
-- Nullable: a live-entered CM Report with no explicit failure date is
-- unaffected.
--
-- Sources:
--   ../BUILD-PACKS/BP-PM-OCCURRENCE/DATABASE/004_alter_add_hoc_provenance_fields.sql
--   ../BUILD-PACKS/BP-CM-REPORT/DATABASE/004_alter_add_hoc_provenance_fields.sql
--   ../BUILD-PACKS/BP-CONDITION-MONITORING/DATABASE/004_alter_add_hoc_provenance_fields.sql
-- ============================================================

ALTER TABLE public.pm_occurrence ADD COLUMN IF NOT EXISTS source_workbook_name TEXT;
ALTER TABLE public.pm_occurrence ADD COLUMN IF NOT EXISTS source_sheet_name TEXT;
ALTER TABLE public.pm_occurrence ADD COLUMN IF NOT EXISTS source_row_number INTEGER;

ALTER TABLE public.cm_report ADD COLUMN IF NOT EXISTS source_workbook_name TEXT;
ALTER TABLE public.cm_report ADD COLUMN IF NOT EXISTS source_sheet_name TEXT;
ALTER TABLE public.cm_report ADD COLUMN IF NOT EXISTS source_row_number INTEGER;
ALTER TABLE public.cm_report ADD COLUMN IF NOT EXISTS failure_date TIMESTAMP;

ALTER TABLE public.condition_monitoring_reading ADD COLUMN IF NOT EXISTS source_workbook_name TEXT;
ALTER TABLE public.condition_monitoring_reading ADD COLUMN IF NOT EXISTS source_sheet_name TEXT;
ALTER TABLE public.condition_monitoring_reading ADD COLUMN IF NOT EXISTS source_row_number INTEGER;

-- ============================================================
-- KNOWLEDGE SOURCE REGISTRY
-- Manufactured under MWO-LTSA-040A (Knowledge Source Registry).
--
-- Canonical registry for engineering source provenance inside LTSA
-- (Architecture Decision item 4). Deliberately NOT AI5R-SDK/KNOWLEDGE's
-- KnowledgeSource/KnowledgeSourceRegistry -- that package is frozen,
-- AI5R-platform-level, and explicitly not reused, modified, or integrated
-- with by this MWO (Architecture Decision items 1-2). The identical name is
-- a known, deliberate collision between two unrelated artifacts, not an
-- oversight.
--
-- The relationship "Knowledge Source -> Engineering Document" named in
-- MWO-LTSA-040A is logical only here -- no FK is added in this block.
-- Physical linkage is deferred to MWO-LTSA-040B (Architecture Decision
-- item 6). Installation Event, Inspection Event, Failure Event, and
-- Engineering Media do not exist yet and are not created here (item 7) --
-- reserved for future MWOs (item 10).
--
-- No DELETE workflow exists for this table, by design: the original
-- engineering source must never be removed by Engineering Knowledge
-- Acquisition (Business Rule; Architecture Decision item 9).
--
-- Source: ../BUILD-PACKS/BP-KNOWLEDGE-SOURCE/DATABASE/001_create_table.sql
-- See ENGINEERING/MWO/MWO-LTSA-040A-Knowledge-Source-Registry.md
-- ============================================================

CREATE TABLE IF NOT EXISTS public.knowledge_source_registry (
    knowledge_source_id TEXT PRIMARY KEY NOT NULL,
    source_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    original_file_name TEXT,
    source_date DATE,
    customer TEXT,
    site TEXT,
    unit TEXT,
    uploaded_by TEXT,
    upload_timestamp TIMESTAMP DEFAULT NOW(),
    source_url TEXT,
    verification_status TEXT NOT NULL DEFAULT 'DRAFT',
    confidence_level NUMERIC,
    file_hash TEXT,
    file_size BIGINT,
    media_type TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT knowledge_source_registry_source_type_check
        CHECK (source_type IN (
            'INSTALLATION_REPORT', 'SERVICE_REPORT', 'INSPECTION_REPORT', 'FAILURE_REPORT',
            'DRAWING', 'DATASHEET', 'BILL_OF_MATERIAL', 'MAINTENANCE_HISTORY',
            'PUMP_MASTER_EXCEL', 'STOCK_EXCEL', 'INSTALLATION_HISTORY_EXCEL',
            'PHOTO', 'VIDEO', 'ENGINEER_NOTE', 'CUSTOMER_NOTE'
        )),
    CONSTRAINT knowledge_source_registry_verification_status_check
        CHECK (verification_status IN ('DRAFT', 'UNDER_REVIEW', 'VERIFIED', 'CANONICAL')),
    CONSTRAINT knowledge_source_registry_file_size_check
        CHECK (file_size IS NULL OR file_size >= 0)
);

-- ============================================================
-- SEAL STOCK, PUMP COMPATIBILITY, INTERCHANGE COMPATIBILITY,
-- ENGINEERING DOCUMENT
-- Manufactured under MWO-LTSA-030 (Mechanical Seal Knowledge Manufacturing).
--
-- Mechanical Seal itself is NOT re-manufactured here. Per the Architecture
-- Decision recorded in MWO-LTSA-030, `seal_registry` (above) already IS the
-- canonical Mechanical Seal registry -- these four tables are new,
-- additive, and each carries a real foreign key back to it (and, for Pump
-- Compatibility, to `ltsa_pumps`). Unlike work_order/maintenance_history's
-- polymorphic (asset_code, asset_type) pair above, none of these
-- relationships is polymorphic -- each side always points at exactly one
-- concrete table, so a real FK is possible and used.
--
-- Sources:
--   ../BUILD-PACKS/BP-SEAL-STOCK/DATABASE/001_create_table.sql
--   ../BUILD-PACKS/BP-SEAL-PUMP-COMPATIBILITY/DATABASE/001_create_table.sql
--   ../BUILD-PACKS/BP-SEAL-INTERCHANGE-COMPATIBILITY/DATABASE/001_create_table.sql
--   ../BUILD-PACKS/BP-SEAL-ENGINEERING-DOCUMENT/DATABASE/001_create_table.sql
-- See ENGINEERING/MWO/MWO-LTSA-030-Mechanical-Seal-Knowledge-Manufacturing.md
-- ============================================================

-- Seal Stock belongs to Mechanical Seal, NOT Pump (MWO-LTSA-030 Business
-- Rule) -- one stock record per seal_code, never per pump.
CREATE TABLE IF NOT EXISTS public.seal_stock (
    seal_code TEXT PRIMARY KEY NOT NULL REFERENCES public.seal_registry(seal_code),
    quantity_on_hand NUMERIC NOT NULL DEFAULT 0,
    reorder_point NUMERIC,
    location TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- One Mechanical Seal may fit multiple Pumps; one Pump may accept multiple
-- compatible seals (MWO-LTSA-030 Business Rules) -- many-to-many, so a
-- composite primary key rather than a surrogate one.
-- pump_tag_number references ltsa_pumps.tag_number (MODULES/PUMP), the
-- canonical Pump Registry -- never BUILD-PACKS/BP-PUMP's deprecated
-- pump_registry.pump_code (Architecture Decision, MWO-LTSA-030 item 3).
CREATE TABLE IF NOT EXISTS public.seal_pump_compatibility (
    seal_code TEXT NOT NULL REFERENCES public.seal_registry(seal_code),
    pump_tag_number VARCHAR(100) NOT NULL REFERENCES public.ltsa_pumps(tag_number),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (seal_code, pump_tag_number)
);

-- Interchange Compatibility: a Mechanical Seal may be substituted by another
-- manufacturer's seal (e.g. JC-100, JC-102, Flowserve-210 in MWO-LTSA-030's
-- worked example) -- self-referential many-to-many against seal_registry.
CREATE TABLE IF NOT EXISTS public.seal_interchange_compatibility (
    seal_code TEXT NOT NULL REFERENCES public.seal_registry(seal_code),
    compatible_seal_code TEXT NOT NULL REFERENCES public.seal_registry(seal_code),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (seal_code, compatible_seal_code),
    CONSTRAINT seal_interchange_not_self CHECK (seal_code <> compatible_seal_code)
);

-- Engineering Documents (Drawing, Datasheet, Installation Guide, Inspection
-- Sheet) are documents owned by a Mechanical Seal, not an independent
-- product and not generic document management (Architecture Decision,
-- MWO-LTSA-030 items 6-7) -- document_type is a closed set, always FK'd to
-- exactly one seal_code.
-- Extended under MWO-LTSA-040B (Engineering Document Acquisition): added
-- knowledge_source_id (FK to knowledge_source_registry, MWO-040A) plus
-- acquisition-layer metadata columns, and widened document_type from 4 to
-- 7 values. seal_code stays NOT NULL and document_code stays the immutable
-- PK -- unchanged from MWO-030 (Business Purpose: "Documents must be
-- linked to Knowledge Source and Mechanical Seal", both required).
-- knowledge_source_id is nullable at the DB layer (required at the
-- workflow layer instead) so this ALTER is safe to apply against a
-- database that may already have MWO-030-shaped rows -- see WP-000 design
-- decision 3 in MWO-LTSA-040B-Engineering-Document-Acquisition.md.
CREATE TABLE IF NOT EXISTS public.seal_engineering_document (
    document_code TEXT PRIMARY KEY NOT NULL,
    seal_code TEXT NOT NULL REFERENCES public.seal_registry(seal_code),
    knowledge_source_id TEXT REFERENCES public.knowledge_source_registry(knowledge_source_id),
    document_type TEXT NOT NULL,
    document_number TEXT,
    title TEXT NOT NULL,
    revision TEXT,
    issue_date DATE,
    manufacturer TEXT,
    language TEXT,
    description TEXT,
    file_reference TEXT,
    file_name TEXT,
    file_format TEXT,
    page_count INTEGER,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT seal_engineering_document_type_check
        CHECK (document_type IN (
            'DRAWING', 'DATASHEET', 'INSTALLATION_GUIDE', 'INSPECTION_SHEET',
            'MAINTENANCE_MANUAL', 'SERVICE_BULLETIN', 'ENGINEERING_SPECIFICATION'
        )),
    CONSTRAINT seal_engineering_document_page_count_check
        CHECK (page_count IS NULL OR page_count >= 0)
);

-- Idempotent upgrade path for a database that already has the MWO-030
-- (pre-040B) shape of this table -- CREATE TABLE IF NOT EXISTS above is a
-- no-op once the table exists, so these statements are what actually bring
-- an existing deployment to the current shape. Safe to re-run.
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS knowledge_source_id TEXT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS document_number TEXT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS issue_date DATE;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS manufacturer TEXT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS language TEXT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS file_name TEXT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS file_format TEXT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS page_count INTEGER;

ALTER TABLE public.seal_engineering_document DROP CONSTRAINT IF EXISTS seal_engineering_document_type_check;
ALTER TABLE public.seal_engineering_document ADD CONSTRAINT seal_engineering_document_type_check
    CHECK (document_type IN (
        'DRAWING', 'DATASHEET', 'INSTALLATION_GUIDE', 'INSPECTION_SHEET',
        'MAINTENANCE_MANUAL', 'SERVICE_BULLETIN', 'ENGINEERING_SPECIFICATION'
    ));

ALTER TABLE public.seal_engineering_document DROP CONSTRAINT IF EXISTS seal_engineering_document_page_count_check;
ALTER TABLE public.seal_engineering_document ADD CONSTRAINT seal_engineering_document_page_count_check
    CHECK (page_count IS NULL OR page_count >= 0);

ALTER TABLE public.seal_engineering_document DROP CONSTRAINT IF EXISTS seal_engineering_document_knowledge_source_fk;
ALTER TABLE public.seal_engineering_document
    ADD CONSTRAINT seal_engineering_document_knowledge_source_fk
    FOREIGN KEY (knowledge_source_id) REFERENCES public.knowledge_source_registry(knowledge_source_id);

-- ============================================================
-- INSTALLATION REPORT
-- Manufactured under MWO-LTSA-060 (production persistence path for the
-- Installation Workspace created by MWO-LTSA-056).
--
-- One row per real, signed mechanical-seal installation report -- a
-- historical engineering record, not a live registry item. Every column
-- traces 1:1 to a field already represented in
-- AI5R-STUDIO/dashboard/src/modules/ltsa/data/sampleInstallations.js
-- (MWO-LTSA-056's literal transcription of the one real source document).
--
-- installation_code is a deterministic code derived from the report's own
-- printed sequence number and year (matches sampleInstallations.js's
-- pre-existing "INSTL-001-2026" id convention), never a random UUID, so
-- re-seeding the same source report always resolves to the same row.
-- report_no is the report's own printed number, its own UNIQUE column,
-- separate from installation_code -- the same PK/business-key split
-- seal_engineering_document draws between document_code/document_number.
--
-- plant_equip_no is an informal reference with NO foreign key -- the same
-- "asset_code TEXT, resolved at the application layer" convention
-- pm_schedule/cm_report/work_order/maintenance_history already use (see
-- PM SCHEDULE section above); multiple Installation Reports for the same
-- pump must be possible, so there is deliberately no UNIQUE constraint on
-- it either. seal_code is a real, nullable FK to seal_registry ("Seal
-- relationship where supported" -- NULL on the one real seed row, since
-- the source report carries no seal_registry identifier, only descriptive
-- text). drawing_no is a plain column, not a FK -- Drawing Workspace has
-- no document_number-keyed lookup path today, so drawing_no is reused as
-- an identity string for navigation only.
--
-- seal_chamber_shaft_inspection, site_activities, bill_of_material, the
-- four observation checklists, and signatures are all JSONB -- each is an
-- owned, bounded, ordered list with no independent identity outside its
-- report, the same convention pm_schedule.checklist already establishes.
-- Source: ../BUILD-PACKS/BP-INSTALLATION/DATABASE/001_create_table.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS public.installation_report (
    installation_code TEXT PRIMARY KEY NOT NULL,
    report_no TEXT NOT NULL UNIQUE,
    tso_no TEXT,
    report_date TEXT,
    customer TEXT,
    address TEXT,
    plant TEXT,
    unit TEXT,
    po_no TEXT,
    packing_list_no TEXT,
    location TEXT,

    equipment_mfr TEXT,
    model_type TEXT,
    size TEXT,
    configuration TEXT,
    serial_no TEXT,
    plant_equip_no TEXT,
    pump_type TEXT,
    shaft_speed TEXT,
    rotation TEXT,
    seal_manufacture TEXT,
    seal_type TEXT,
    seal_arrangement TEXT,
    seal_size TEXT,
    material_code TEXT,
    drawing_no TEXT,
    seal_location TEXT,
    seal_code TEXT REFERENCES public.seal_registry(seal_code),

    liquid TEXT,
    temperature_range TEXT,
    specific_gravity TEXT,
    viscosity TEXT,
    flash_point TEXT,
    boiling_point TEXT,
    freeze_point TEXT,
    vapor_press TEXT,
    discharge_press TEXT,
    suction_press TEXT,
    differential_press TEXT,
    stuffing_box_press TEXT,
    seal_press TEXT,
    corrosion_erosion_by TEXT,
    api_plan TEXT,
    flush_liquid TEXT,
    flush_pressure TEXT,
    flush_temp TEXT,
    flush_flowrate TEXT,
    buffer_barrier_press TEXT,
    buffer_barrier_fluid TEXT,
    quench_fluid TEXT,

    seal_chamber_shaft_inspection JSONB,

    basic_seal_condition TEXT,
    gland_condition TEXT,
    sleeve_condition TEXT,
    shaft_condition TEXT,
    bearing_condition TEXT,
    gasket_condition TEXT,
    radial_bearing_no TEXT,
    thrust_bearing_no TEXT,

    summary_intro TEXT,
    site_activity_intro TEXT,
    site_activities JSONB,

    bom_caption TEXT,
    bill_of_material JSONB,

    gland_observation_note TEXT,
    gland_observation JSONB,
    sleeve_observation_note TEXT,
    sleeve_observation JSONB,
    retainer_disc_observation_note TEXT,
    retainer_disc_observation JSONB,
    cartridge_drive_collar_observation_note TEXT,
    cartridge_drive_collar_observation JSONB,

    signatures JSONB,

    source_document_name TEXT NOT NULL,

    -- MWO-LTSA-INSTALLATION-REPORT-STRUCTURAL-CORRECTION-001 -- 2 of 5
    -- golden-sample reports (211-P-2A DE, 212-P-13AR) carry a
    -- post-installation Condition-Monitoring-shaped measurement table
    -- directly on the same signed document (dated/timestamped, DE/NDE
    -- split point measurements). This is historical evidence belonging to
    -- THIS report, not a live Condition Monitoring reading -- it has no
    -- other canonical home today (condition_monitoring_reading itself is
    -- still uncommitted, gated behind a PROPOSED, not ACCEPTED, ADR). NULL
    -- for the 3 of 5 reports that carry no such table (not every report
    -- has one) -- an empty array would falsely assert "zero readings were
    -- taken" rather than "this report has no such section". Array shape
    -- (one element per point measurement row): { measurement, value, unit,
    -- location, de, nde, dateTime, condition } -- variable/optional keys
    -- per entry, matching the report's own variable row-set (10-16 rows
    -- observed, no two reports identical). No thresholds, no alarm
    -- states, no CMON linkage: this column preserves only what the report
    -- itself prints.
    post_installation_readings JSONB,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Idempotent upgrade path for a database that already has the pre-
-- MWO-LTSA-INSTALLATION-REPORT-STRUCTURAL-CORRECTION-001 shape of this
-- table -- CREATE TABLE IF NOT EXISTS above is a no-op once the table
-- exists, so this statement is what actually brings an existing
-- deployment (including a89369e's own installation_report, migration 009)
-- to the current shape. Safe to re-run.
ALTER TABLE public.installation_report ADD COLUMN IF NOT EXISTS post_installation_readings JSONB;

CREATE INDEX IF NOT EXISTS idx_installation_report_installation_code
ON public.installation_report (installation_code);

CREATE INDEX IF NOT EXISTS idx_installation_report_report_no
ON public.installation_report (report_no);

CREATE INDEX IF NOT EXISTS idx_installation_report_plant_equip_no
ON public.installation_report (plant_equip_no);

CREATE INDEX IF NOT EXISTS idx_installation_report_seal_code
ON public.installation_report (seal_code);

-- ============================================================
-- INTERNAL COMPONENT INVENTORY
-- Manufactured under MWO-LTSA-057E (Internal Component Inventory Canonical Model).
--
-- Strictly internal AI5R / engineering inventory, separate from user-facing
-- seal_stock. GPN may be temporarily pending during workbook migration, but
-- every internal component is expected to eventually have exactly one real GPN.
-- ============================================================

CREATE TABLE IF NOT EXISTS public.internal_component_master (
    component_id TEXT PRIMARY KEY NOT NULL,
    component_class TEXT NOT NULL,
    gpn_number TEXT,
    gpn_status TEXT NOT NULL,
    identity_fingerprint TEXT NOT NULL,
    description TEXT NOT NULL,
    size_text TEXT,
    specification TEXT,
    source_workbook_name TEXT,
    source_sheet_name TEXT,
    source_row_number INTEGER,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT internal_component_class_check CHECK (component_class IN (
        'O_RING', 'MATING_RING', 'SEAL_PART', 'MECHANICAL_SEAL',
        'MECHANICAL_SEAL_ASSY', 'SHAFT_SLEEVE', 'SET_SCREW',
        'RETAINER', 'SPARE_PART'
    )),
    CONSTRAINT internal_component_gpn_status_check CHECK (gpn_status IN ('GPN_PENDING', 'GPN_ASSIGNED')),
    CONSTRAINT internal_component_gpn_consistency_check CHECK (
        (gpn_status = 'GPN_PENDING' AND gpn_number IS NULL)
        OR (gpn_status = 'GPN_ASSIGNED' AND gpn_number IS NOT NULL)
    ),
    CONSTRAINT internal_component_identity_fingerprint_unique UNIQUE (identity_fingerprint)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_internal_component_master_gpn_unique
    ON public.internal_component_master (gpn_number)
    WHERE gpn_number IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.internal_component_stock (
    component_stock_id TEXT PRIMARY KEY NOT NULL,
    component_id TEXT NOT NULL REFERENCES public.internal_component_master(component_id),
    quantity_on_hand NUMERIC,
    warehouse_name TEXT,
    rack_name TEXT,
    location_tag TEXT,
    source_workbook_name TEXT NOT NULL,
    source_sheet_name TEXT NOT NULL,
    source_row_number INTEGER NOT NULL,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT internal_component_stock_source_unique UNIQUE (source_workbook_name, source_sheet_name, source_row_number)
);

CREATE TABLE IF NOT EXISTS public.seal_internal_component_link (
    seal_code TEXT NOT NULL REFERENCES public.seal_registry(seal_code),
    component_id TEXT NOT NULL REFERENCES public.internal_component_master(component_id),
    relationship_basis TEXT NOT NULL,
    source_workbook_name TEXT NOT NULL,
    source_sheet_name TEXT NOT NULL,
    source_row_number INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (seal_code, component_id, source_sheet_name, source_row_number),
    CONSTRAINT seal_internal_component_relationship_basis_check CHECK (relationship_basis IN ('WORKBOOK_ROW'))
);

-- ============================================================
-- WORKBOOK, WORKSHEET, WORKSHEET TABLE, MAPPING PROFILE,
-- COLUMN MAPPING, ACQUISITION JOB
-- Manufactured under MWO-LTSA-040C (Universal Tabular Data Acquisition).
--
-- The Universal Acquisition Infrastructure only -- per Architecture
-- Decision items 1/5/6, this MWO does NOT write to any canonical
-- business-object table (ltsa_pumps, seal_registry, seal_stock, etc.).
-- A successful acquisition_job produces a validated, normalized, mapped
-- workbook "ready for manufacturing" (item 9); future MWOs consume
-- acquisition_job to actually manufacture business objects (item 10).
--
-- workbook_type is a closed, 11-value set (the "Supported Workbook Types"
-- from the original work order) shared by workbook and mapping_profile;
-- every validation of it is a generic allow-list, never a per-type parser
-- (Architecture Decision item 7).
--
-- Sources:
--   ../BUILD-PACKS/BP-WORKBOOK/DATABASE/001_create_table.sql
--   ../BUILD-PACKS/BP-WORKSHEET/DATABASE/001_create_table.sql
--   ../BUILD-PACKS/BP-WORKSHEET-TABLE/DATABASE/001_create_table.sql
--   ../BUILD-PACKS/BP-MAPPING-PROFILE/DATABASE/001_create_table.sql
--   ../BUILD-PACKS/BP-COLUMN-MAPPING/DATABASE/001_create_table.sql
--   ../BUILD-PACKS/BP-ACQUISITION-JOB/DATABASE/001_create_table.sql
-- See ENGINEERING/MWO/MWO-LTSA-040C-Universal-Tabular-Data-Acquisition.md
-- ============================================================

-- Every Workbook must originate from exactly one Knowledge Source
-- (Business Rule). Immutable once registered -- "Original Workbook must
-- never be modified" -- no Update or Delete workflow exists for this
-- table (WP-000 design decision 6).
CREATE TABLE IF NOT EXISTS public.workbook (
    workbook_id TEXT PRIMARY KEY NOT NULL,
    knowledge_source_id TEXT NOT NULL REFERENCES public.knowledge_source_registry(knowledge_source_id),
    workbook_type TEXT NOT NULL,
    workbook_name TEXT NOT NULL,
    workbook_version TEXT,
    sheet_count INTEGER,
    created_date DATE,
    imported_date DATE,
    uploaded_by TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT workbook_type_check
        CHECK (workbook_type IN (
            'PUMP_MASTER', 'MECHANICAL_SEAL_MASTER', 'SEAL_STOCK', 'SEAL_INTERCHANGE',
            'PUMP_COMPATIBILITY', 'INSTALLATION_HISTORY', 'MAINTENANCE_HISTORY',
            'ENGINEER_MASTER', 'CUSTOMER_MASTER', 'VENDOR_MASTER', 'BILL_OF_MATERIAL'
        )),
    CONSTRAINT workbook_sheet_count_check CHECK (sheet_count IS NULL OR sheet_count >= 0)
);

-- One Workbook may contain multiple Worksheets (Business Rule). Immutable,
-- same class as workbook (WP-000 design decision 6).
CREATE TABLE IF NOT EXISTS public.worksheet (
    worksheet_id TEXT PRIMARY KEY NOT NULL,
    workbook_id TEXT NOT NULL REFERENCES public.workbook(workbook_id),
    worksheet_name TEXT NOT NULL,
    row_count INTEGER,
    column_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT worksheet_row_count_check CHECK (row_count IS NULL OR row_count >= 0),
    CONSTRAINT worksheet_column_count_check CHECK (column_count IS NULL OR column_count >= 0)
);

-- One Worksheet may contain multiple Structured Tables; one Structured
-- Table may manufacture multiple Canonical Objects (Business Rules, the
-- latter describing a future capability, not built here). Attributes not
-- specified by the original work order -- mirrors worksheet's own shape
-- one level down (WP-000 design decision 2). Immutable, same class as
-- workbook/worksheet.
CREATE TABLE IF NOT EXISTS public.worksheet_table (
    worksheet_table_id TEXT PRIMARY KEY NOT NULL,
    worksheet_id TEXT NOT NULL REFERENCES public.worksheet(worksheet_id),
    table_name TEXT,
    row_count INTEGER,
    column_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT worksheet_table_row_count_check CHECK (row_count IS NULL OR row_count >= 0),
    CONSTRAINT worksheet_table_column_count_check CHECK (column_count IS NULL OR column_count >= 0)
);

-- A Mapping Profile defines how customer-specific column names map to
-- canonical LTSA attributes, and must be reusable (Business Purpose /
-- Business Rule) -- full CRUD, not immutable. workbook_type scopes which
-- canonical attribute set a profile's column_mapping rows target (WP-000
-- design decision 3). customer is free text, matching the given examples
-- ("Internal LTSA" is not a customer_registry entry), the same choice
-- already made for knowledge_source_registry.customer (MWO-040A).
CREATE TABLE IF NOT EXISTS public.mapping_profile (
    mapping_profile_id TEXT PRIMARY KEY NOT NULL,
    profile_name TEXT NOT NULL,
    workbook_type TEXT NOT NULL,
    customer TEXT,
    description TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT mapping_profile_workbook_type_check
        CHECK (workbook_type IN (
            'PUMP_MASTER', 'MECHANICAL_SEAL_MASTER', 'SEAL_STOCK', 'SEAL_INTERCHANGE',
            'PUMP_COMPATIBILITY', 'INSTALLATION_HISTORY', 'MAINTENANCE_HISTORY',
            'ENGINEER_MASTER', 'CUSTOMER_MASTER', 'VENDOR_MASTER', 'BILL_OF_MATERIAL'
        ))
);

-- A Column Mapping (Source Column -> Canonical Attribute) only has
-- meaning within a Mapping Profile. is_mandatory records whether the
-- target canonical_attribute is required, serving the original work
-- order's "Validate ... Missing Mandatory Values" requirement generically
-- (WP-000 design decision 4). Full CRUD, same reusability rationale as
-- mapping_profile.
CREATE TABLE IF NOT EXISTS public.column_mapping (
    column_mapping_id TEXT PRIMARY KEY NOT NULL,
    mapping_profile_id TEXT NOT NULL REFERENCES public.mapping_profile(mapping_profile_id),
    source_column TEXT NOT NULL,
    canonical_attribute TEXT NOT NULL,
    is_mandatory BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- A minimal, generic job-log shape reflecting the pipeline's stated stages
-- (registration -> mapping -> normalization -> validation) without
-- asserting manufacturing occurred -- a READY_FOR_MANUFACTURING job has
-- not written any business object (Architecture Decision item 9). Create/
-- List/Detail/Update (status and result fields progress over a job's
-- lifecycle) but no Delete -- "Acquisition must be repeatable" (Business
-- Rule) is satisfied by allowing multiple job rows per (workbook_id,
-- mapping_profile_id) pair, not by deleting and retrying one row (WP-000
-- design decision 6). The status set itself (WP-000 design decision 5) is
-- the one part of this table most likely to need revision once a future
-- MWO builds a real acquisition workflow against it.
CREATE TABLE IF NOT EXISTS public.acquisition_job (
    acquisition_job_id TEXT PRIMARY KEY NOT NULL,
    workbook_id TEXT NOT NULL REFERENCES public.workbook(workbook_id),
    mapping_profile_id TEXT NOT NULL REFERENCES public.mapping_profile(mapping_profile_id),
    status TEXT NOT NULL DEFAULT 'PENDING',
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    rows_processed INTEGER,
    rows_valid INTEGER,
    rows_invalid INTEGER,
    error_summary TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT acquisition_job_status_check
        CHECK (status IN ('PENDING', 'IN_PROGRESS', 'READY_FOR_MANUFACTURING', 'FAILED')),
    CONSTRAINT acquisition_job_rows_processed_check CHECK (rows_processed IS NULL OR rows_processed >= 0),
    CONSTRAINT acquisition_job_rows_valid_check CHECK (rows_valid IS NULL OR rows_valid >= 0),
    CONSTRAINT acquisition_job_rows_invalid_check CHECK (rows_invalid IS NULL OR rows_invalid >= 0)
);


-- ============================================================
-- PDF DOCUMENT, PDF METADATA, DOCUMENT CLASSIFICATION,
-- PDF ACQUISITION JOB
-- Manufactured under MWO-LTSA-040D (Engineering PDF Acquisition).
--
-- Four new tables, parallel to (not an extension of) seal_engineering_
-- document (MWO-040B) -- this MWO's own Business Rule requires only a
-- Knowledge Source link, not a Mechanical Seal link, and MWO-040A's own
-- roadmap (WP-000 item 10) already treats "040D connects PDF Acquisition"
-- as its own distinct connection, the same way 040C ("Excel Acquisition")
-- built its own workbook/worksheet family instead of retrofitting
-- seal_engineering_document.
--
-- No OCR, text/table/image extraction, AI, or knowledge extraction is
-- performed here -- every field is caller-supplied metadata, the same
-- convention as every other acquisition workflow in this product.
--
-- Sources:
--   ../BUILD-PACKS/BP-PDF-DOCUMENT/DATABASE/001_create_table.sql
--   ../BUILD-PACKS/BP-PDF-METADATA/DATABASE/001_create_table.sql
--   ../BUILD-PACKS/BP-DOCUMENT-CLASSIFICATION/DATABASE/001_create_table.sql
--   ../BUILD-PACKS/BP-PDF-ACQUISITION-JOB/DATABASE/001_create_table.sql
-- See ENGINEERING/MWO/MWO-LTSA-040D-Engineering-PDF-Acquisition.md
-- ============================================================

-- Every PDF Document must originate from exactly one Knowledge Source
-- (Business Rule). Immutable once registered -- "Original PDF must never
-- be modified" -- no Update or Delete workflow exists for this table,
-- same immutability class as workbook (040C).
CREATE TABLE IF NOT EXISTS public.pdf_document (
    pdf_document_id TEXT PRIMARY KEY NOT NULL,
    knowledge_source_id TEXT NOT NULL REFERENCES public.knowledge_source_registry(knowledge_source_id),
    document_name TEXT NOT NULL,
    document_type TEXT NOT NULL,
    file_name TEXT,
    page_count INTEGER,
    file_size BIGINT,
    file_hash TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT pdf_document_type_check
        CHECK (document_type IN (
            'INSTALLATION_REPORT', 'SERVICE_REPORT', 'INSPECTION_REPORT', 'FAILURE_REPORT',
            'JOHN_CRANE_DRAWING', 'DATASHEET', 'MAINTENANCE_MANUAL', 'SERVICE_BULLETIN',
            'ENGINEERING_SPECIFICATION', 'CALIBRATION_REPORT', 'HYDROTEST_REPORT',
            'PM_CMON_MONTHLY_REPORT'
        )),
    CONSTRAINT pdf_document_page_count_check CHECK (page_count IS NULL OR page_count >= 0),
    CONSTRAINT pdf_document_file_size_check CHECK (file_size IS NULL OR file_size >= 0)
);

-- One PDF Document's own container-level properties (title/author/
-- producer/version), recorded once at acquisition time -- a structural
-- fact about the source file, the same immutability class as worksheet
-- (040C). UNIQUE on pdf_document_id: a single PDF file has exactly one
-- set of document properties at a time (WP-000 design decision 8) --
-- unlike Worksheet, no business rule in this MWO describes multiple
-- PDF Metadata rows per PDF Document.
CREATE TABLE IF NOT EXISTS public.pdf_metadata (
    pdf_metadata_id TEXT PRIMARY KEY NOT NULL,
    pdf_document_id TEXT NOT NULL REFERENCES public.pdf_document(pdf_document_id),
    title TEXT,
    author TEXT,
    producer TEXT,
    creation_date TIMESTAMP,
    modification_date TIMESTAMP,
    pdf_version TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT pdf_metadata_pdf_document_id_unique UNIQUE (pdf_document_id)
);

-- A single classification attempt against one PDF Document. Repeatable
-- by design -- "PDF Classification must be repeatable" (Business Rule)
-- is satisfied by allowing multiple classification rows per PDF
-- Document, not by mutating one row (same reasoning as acquisition_job,
-- 040C) -- so, unlike pdf_metadata, no UNIQUE constraint on
-- pdf_document_id. classification_type reuses the same 11-value closed
-- set as pdf_document.document_type (WP-000 design decision 6) -- no
-- separate classification taxonomy is named anywhere in the work order.
CREATE TABLE IF NOT EXISTS public.document_classification (
    document_classification_id TEXT PRIMARY KEY NOT NULL,
    pdf_document_id TEXT NOT NULL REFERENCES public.pdf_document(pdf_document_id),
    classification_type TEXT NOT NULL,
    classification_version TEXT,
    confidence NUMERIC,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT document_classification_type_check
        CHECK (classification_type IN (
            'INSTALLATION_REPORT', 'SERVICE_REPORT', 'INSPECTION_REPORT', 'FAILURE_REPORT',
            'JOHN_CRANE_DRAWING', 'DATASHEET', 'MAINTENANCE_MANUAL', 'SERVICE_BULLETIN',
            'ENGINEERING_SPECIFICATION', 'CALIBRATION_REPORT', 'HYDROTEST_REPORT'
        ))
);

-- The job-log record of one acquisition attempt against one PDF Document
-- originating from one Knowledge Source -- both FKs are named attributes
-- of "PDF Acquisition Job" in the original work order's own Business
-- Objects section, not inferred. status set (PENDING/IN_PROGRESS/
-- COMPLETED/FAILED) adapted from acquisition_job (040C), with
-- READY_FOR_MANUFACTURING replaced by COMPLETED because this MWO's own
-- Out of Scope excludes "Engineering Object Manufacturing" (WP-000
-- design decision 10) -- flagged as the label most likely to need
-- revision once a real acquisition workflow runs against it.
-- Create/List/Detail/Update, no Delete -- "must be repeatable" is
-- satisfied by multiple job rows, not by mutating or deleting one.
CREATE TABLE IF NOT EXISTS public.pdf_acquisition_job (
    pdf_acquisition_job_id TEXT PRIMARY KEY NOT NULL,
    knowledge_source_id TEXT NOT NULL REFERENCES public.knowledge_source_registry(knowledge_source_id),
    pdf_document_id TEXT NOT NULL REFERENCES public.pdf_document(pdf_document_id),
    status TEXT NOT NULL DEFAULT 'PENDING',
    started_at TIMESTAMP DEFAULT NOW(),
    finished_at TIMESTAMP,
    validation_errors TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT pdf_acquisition_job_status_check
        CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED'))
);

-- ============================================================
-- ENGINEERING MEDIA, MEDIA METADATA, MEDIA CLASSIFICATION,
-- MEDIA ACQUISITION JOB
-- Manufactured under MWO-LTSA-040E (Engineering Media Acquisition).
--
-- The third canonical Acquisition Object, alongside Workbook (040C) and
-- PDF (040D), conforming to ADR-004 (Engineering Acquisition Pattern):
-- Acquisition Object -> Metadata -> Classification -> Acquisition Job.
-- Clones MWO-LTSA-040D's four-table shape table-for-table (MWO-LTSA-040E
-- Dependencies section). engineering_media's own media_name/file_name/
-- file_size/file_hash/status columns complete that table-for-table clone
-- of pdf_document -- not separately itemized in MWO-LTSA-040E's WP-000
-- (which resolved knowledge_source_id/media_type/status explicitly), so
-- flagged here, not silently assumed, per Evidence Standard practice.
--
-- No image recognition, object detection, OCR, speech recognition, video/
-- audio analysis, or AI reasoning is performed here -- every field is
-- caller-supplied metadata, the same convention as every other
-- acquisition workflow in this product.
--
-- Sources:
--   ../BUILD-PACKS/BP-ENGINEERING-MEDIA/DATABASE/001_create_table.sql
--   ../BUILD-PACKS/BP-MEDIA-METADATA/DATABASE/001_create_table.sql
--   ../BUILD-PACKS/BP-MEDIA-CLASSIFICATION/DATABASE/001_create_table.sql
--   ../BUILD-PACKS/BP-MEDIA-ACQUISITION-JOB/DATABASE/001_create_table.sql
-- See ENGINEERING/MWO/MWO-LTSA-040E-Engineering-Media-Acquisition.md
-- ============================================================

-- Every Engineering Media must originate from exactly one Knowledge
-- Source (Business Rule; WP-000 design decision 1). Immutable once
-- registered -- "Original media must never be modified" -- no Update or
-- Delete workflow exists for this table, same immutability class as
-- pdf_document (040D) and workbook (040C).
CREATE TABLE IF NOT EXISTS public.engineering_media (
    engineering_media_id TEXT PRIMARY KEY NOT NULL,
    knowledge_source_id TEXT NOT NULL REFERENCES public.knowledge_source_registry(knowledge_source_id),
    media_name TEXT NOT NULL,
    media_type TEXT NOT NULL,
    file_name TEXT,
    file_size BIGINT,
    file_hash TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT engineering_media_type_check
        CHECK (media_type IN (
            'PHOTO', 'VIDEO', 'AUDIO', 'THERMAL_IMAGE', 'INFRARED_IMAGE',
            'INSPECTION_IMAGE', 'CCTV_RECORDING', 'DRONE_RECORDING', 'OTHER'
        )),
    CONSTRAINT engineering_media_file_size_check CHECK (file_size IS NULL OR file_size >= 0)
);

-- One Engineering Media asset's own container-level technical properties,
-- recorded once at acquisition time -- a structural fact about the source
-- file, the same immutability class and one-to-one shape as pdf_metadata
-- (040D, WP-000 design decision 4). resolution is free text (distinct
-- from structured width/height); gps_location/camera_device are the only
-- two attributes the work order marks optional, kept as free text (WP-000
-- design decisions 9/10).
CREATE TABLE IF NOT EXISTS public.media_metadata (
    media_metadata_id TEXT PRIMARY KEY NOT NULL,
    engineering_media_id TEXT NOT NULL REFERENCES public.engineering_media(engineering_media_id),
    resolution TEXT,
    duration NUMERIC,
    width INTEGER,
    height INTEGER,
    frame_rate NUMERIC,
    audio_channels INTEGER,
    gps_location TEXT,
    camera_device TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT media_metadata_engineering_media_id_unique UNIQUE (engineering_media_id),
    CONSTRAINT media_metadata_width_check CHECK (width IS NULL OR width >= 0),
    CONSTRAINT media_metadata_height_check CHECK (height IS NULL OR height >= 0),
    CONSTRAINT media_metadata_audio_channels_check CHECK (audio_channels IS NULL OR audio_channels >= 0)
);

-- A single classification attempt against one Engineering Media asset.
-- Repeatable by design -- "Media classification must be repeatable"
-- (Business Rule) is satisfied by allowing multiple classification rows,
-- not by mutating one row (WP-000 design decision 5). classification_type
-- reuses the same 9-value closed set as engineering_media.media_type --
-- no separate classification taxonomy is named anywhere in the work
-- order.
CREATE TABLE IF NOT EXISTS public.media_classification (
    media_classification_id TEXT PRIMARY KEY NOT NULL,
    engineering_media_id TEXT NOT NULL REFERENCES public.engineering_media(engineering_media_id),
    classification_type TEXT NOT NULL,
    classification_version TEXT,
    confidence NUMERIC,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT media_classification_type_check
        CHECK (classification_type IN (
            'PHOTO', 'VIDEO', 'AUDIO', 'THERMAL_IMAGE', 'INFRARED_IMAGE',
            'INSPECTION_IMAGE', 'CCTV_RECORDING', 'DRONE_RECORDING', 'OTHER'
        ))
);

-- The job-log record of one acquisition attempt against one Engineering
-- Media asset originating from one Knowledge Source (WP-000 design
-- decision 7) -- status set (PENDING/IN_PROGRESS/COMPLETED/FAILED)
-- adapted from pdf_acquisition_job (040D), itself adapted from
-- acquisition_job (040C), with COMPLETED used (not READY_FOR_
-- MANUFACTURING) because this MWO's Out of Scope excludes "Engineering
-- Object Manufacturing." Create/List/Detail/Update, no Delete --
-- "acquisition must be repeatable" is satisfied by multiple job rows, not
-- by mutating or deleting one.
CREATE TABLE IF NOT EXISTS public.media_acquisition_job (
    media_acquisition_job_id TEXT PRIMARY KEY NOT NULL,
    knowledge_source_id TEXT NOT NULL REFERENCES public.knowledge_source_registry(knowledge_source_id),
    engineering_media_id TEXT NOT NULL REFERENCES public.engineering_media(engineering_media_id),
    status TEXT NOT NULL DEFAULT 'PENDING',
    started_at TIMESTAMP DEFAULT NOW(),
    finished_at TIMESTAMP,
    validation_errors TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT media_acquisition_job_status_check
        CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED'))
);

-- ============================================================
-- DOCUMENT FIELD EXTRACTION
-- Manufactured under the LTSA-BRAIN Document Upload MVP (Engineering
-- Document Upload Pipeline: Upload -> OCR -> AI Field Extraction -> Review
-- -> Save).
--
-- Fulfils the extraction step BP-PDF-DOCUMENT (040D) and BP-ENGINEERING-
-- MEDIA (040E) both explicitly deferred ("no OCR, text/table/image
-- extraction, or AI reasoning is performed here... deferred to future
-- MWOs"). Additive only -- knowledge_source_registry, pdf_document, and
-- engineering_media are reused unmodified as the upload/provenance and
-- acquisition-object records; this table adds the AI Extraction
-- Capability's result against an already-registered document.
--
-- source_document_id / source_document_type is a polymorphic reference (no
-- FK), the same pattern already used by work_order.asset_code / asset_type
-- above -- a document may be a pdf_document (PDF upload) or an
-- engineering_media asset (JPG/JPEG/PNG upload), two tables with no common
-- supertype in this schema.
--
-- extracted_fields / reviewed_fields use JSONB (unlike every other table in
-- this file) because the field set is genuinely provider- and document-
-- type-dependent (the MVP's Minimum Fields: General/Pump/Mechanical
-- Seal/Process), not a fixed business-object shape. extraction_provider
-- records which AI Extraction Capability provider produced the result
-- (Claude is the first and only provider implemented; the column exists so
-- adding a future provider requires no schema change, per Chief Architect
-- ruling: "Claude is the first provider, not the architecture").
--
-- pump_tag_number / seal_code are nullable, populated only at Save time by
-- reusing PumpIdentityResolver / SealIdentityResolver (PUMP-FACTORY-PACK /
-- SEAL-FACTORY-PACK) unmodified against the reviewed fields -- this table
-- does not implement its own matching logic.
--
-- Per Chief Architect ruling, original-file persistence (the physical
-- uploaded document) is explicitly OUT OF SCOPE for this MWO and deferred
-- to a future Platform Storage MWO -- no file-path/storage column is added
-- here.
--
-- Source: ../BUILD-PACKS/BP-DOCUMENT-EXTRACTION/DATABASE/001_create_table.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS public.document_field_extraction (
    document_field_extraction_id TEXT PRIMARY KEY NOT NULL,
    source_document_id TEXT NOT NULL,
    source_document_type TEXT NOT NULL,
    detected_document_type TEXT NOT NULL,
    detected_document_type_confidence NUMERIC,
    extraction_provider TEXT NOT NULL DEFAULT 'claude',
    ocr_text TEXT,
    extracted_fields JSONB NOT NULL DEFAULT '{}'::jsonb,
    reviewed_fields JSONB,
    status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
    pump_tag_number VARCHAR(100) REFERENCES public.ltsa_pumps(tag_number),
    seal_code TEXT REFERENCES public.seal_registry(seal_code),
    -- MWO-LTSA-INSTALLATION-REPORT-INGESTION-001 -- source_page/reviewed_by/
    -- reviewed_at close the provenance gap for a human-reviewed extraction
    -- (Phase 5's required source_page/reviewed_by/reviewed_at fields; every
    -- other required field -- source_document_id, extracted_value,
    -- confidence, review_status -- already existed). reviewed_by holds the
    -- reviewing user's id (auth foundation, migration 007) but carries NO
    -- database-level FK -- CANONICAL_SCHEMA.sql's own engineering-domain
    -- bootstrap never creates public.users (only migration 007 does, as a
    -- separate step; no table in this file references it), so a hard FK
    -- here would break `--bootstrap-schema` on a fresh database. This is
    -- the same "informal reference, resolved at the application layer"
    -- convention pm_schedule.asset_code/installation_report.plant_equip_no
    -- already establish. REJECTED is a genuinely new terminal status: a
    -- human reviewer determining a draft is unusable (duplicate, illegible,
    -- wrong document) previously had no terminal state distinct from
    -- PENDING_REVIEW/REVIEWED; a REJECTED row is never promoted to any
    -- canonical table (installation_report or otherwise) by any code path.
    source_page INTEGER,
    reviewed_by UUID,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT document_field_extraction_source_type_check
        CHECK (source_document_type IN ('PDF', 'MEDIA')),
    CONSTRAINT document_field_extraction_detected_type_check
        CHECK (detected_document_type IN (
            'MECHANICAL_SEAL_INSTALLATION_REPORT', 'PUMP_DATASHEET',
            'MECHANICAL_SEAL_DRAWING', 'PUMP_DRAWING', 'NAMEPLATE', 'UNKNOWN',
            'HISTORICAL_PM_OCCURRENCE_CANDIDATE', 'HISTORICAL_CMON_READING_CANDIDATE',
            'HISTORICAL_FINDING_CANDIDATE'
        )),
    CONSTRAINT document_field_extraction_status_check
        CHECK (status IN ('PENDING_REVIEW', 'REVIEWED', 'SAVED', 'REJECTED')),
    CONSTRAINT document_field_extraction_confidence_check
        CHECK (detected_document_type_confidence IS NULL
            OR (detected_document_type_confidence >= 0 AND detected_document_type_confidence <= 1))
);

-- Idempotent upgrade path for a database that already has the pre-
-- MWO-LTSA-INSTALLATION-REPORT-INGESTION-001 shape of this table --
-- CREATE TABLE IF NOT EXISTS above is a no-op once the table exists, so
-- these statements are what actually bring an existing deployment to the
-- current shape. Safe to re-run (DROP CONSTRAINT IF EXISTS then re-ADD).
ALTER TABLE public.document_field_extraction ADD COLUMN IF NOT EXISTS source_page INTEGER;
ALTER TABLE public.document_field_extraction ADD COLUMN IF NOT EXISTS reviewed_by UUID;
ALTER TABLE public.document_field_extraction ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP;

ALTER TABLE public.document_field_extraction DROP CONSTRAINT IF EXISTS document_field_extraction_status_check;
ALTER TABLE public.document_field_extraction ADD CONSTRAINT document_field_extraction_status_check
    CHECK (status IN ('PENDING_REVIEW', 'REVIEWED', 'SAVED', 'REJECTED'));

CREATE INDEX IF NOT EXISTS idx_document_field_extraction_source
    ON public.document_field_extraction(source_document_id, source_document_type);
CREATE INDEX IF NOT EXISTS idx_document_field_extraction_status
    ON public.document_field_extraction(status);
CREATE INDEX IF NOT EXISTS idx_document_field_extraction_pump_tag_number
    ON public.document_field_extraction(pump_tag_number);
CREATE INDEX IF NOT EXISTS idx_document_field_extraction_seal_code
    ON public.document_field_extraction(seal_code);
