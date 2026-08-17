-- MWO-LTSA-INSTALLATION-REPORT-INGESTION-001 -- reconciles the canonical
-- Installation Report persistence contract. installation_gateway.py /
-- routers/installation.py (both already committed) and
-- equipment_timeline_service.py's build_lifecycle() (already committed,
-- already calls InstallationGateway.list_installations() to build
-- current_installation/installation_events/replacement_events) all already
-- assume this table exists; this migration brings a database created
-- before that contract existed up to the shape those modules already
-- require, without dropping or altering any existing table.
--
-- Table shape verbatim from DATABASE/CANONICAL_SCHEMA.sql's own
-- "INSTALLATION REPORT" section (MWO-LTSA-060, production persistence path
-- for the Installation Workspace created by MWO-LTSA-056): one row per
-- real, signed mechanical-seal installation report -- a historical
-- engineering record, not a live registry item. Every column traces 1:1
-- to a field already represented in
-- AI5R-STUDIO/dashboard/src/modules/ltsa/data/sampleInstallations.js
-- (MWO-LTSA-056's literal transcription of the one real source document).
--
-- Idempotent: every statement is CREATE ... IF NOT EXISTS, safe to re-run.

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

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_installation_report_installation_code
ON public.installation_report (installation_code);

CREATE INDEX IF NOT EXISTS idx_installation_report_report_no
ON public.installation_report (report_no);

CREATE INDEX IF NOT EXISTS idx_installation_report_plant_equip_no
ON public.installation_report (plant_equip_no);

CREATE INDEX IF NOT EXISTS idx_installation_report_seal_code
ON public.installation_report (seal_code);
