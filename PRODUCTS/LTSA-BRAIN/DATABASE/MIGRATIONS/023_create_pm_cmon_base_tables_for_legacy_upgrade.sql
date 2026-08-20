-- MWO-LTSA-PM-CMON-SCHEMA-CLOSURE-001 -- legacy-safe base-table closure
-- for deployments that already have LTSA core/catalog tables but predate
-- WO-PMOCC-001 / WO-CMON-001. Migrations 014 and 015 are additive ALTERs
-- that expect pm_occurrence and condition_monitoring_reading to exist; this
-- migration supplies the missing base tables without dropping or rewriting
-- any existing table/data. It intentionally mirrors CANONICAL_SCHEMA.sql's
-- final PM/CMON table shapes so 014/015 become no-ops where their columns
-- are already present.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

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
    source_reference TEXT,
    source_workbook_name TEXT,
    source_sheet_name TEXT,
    source_row_number INTEGER
);

CREATE INDEX IF NOT EXISTS idx_pm_occurrence_asset
    ON public.pm_occurrence(asset_code, occurrence_date, pm_occurrence_code);

CREATE INDEX IF NOT EXISTS idx_pm_occurrence_source_reference
    ON public.pm_occurrence(source_reference);

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
    source_reference TEXT,
    source_workbook_name TEXT,
    source_sheet_name TEXT,
    source_row_number INTEGER
);

CREATE INDEX IF NOT EXISTS idx_condition_monitoring_reading_asset
    ON public.condition_monitoring_reading(asset_code, reading_date, condition_monitoring_reading_code);

CREATE INDEX IF NOT EXISTS idx_condition_monitoring_reading_source_reference
    ON public.condition_monitoring_reading(source_reference);
