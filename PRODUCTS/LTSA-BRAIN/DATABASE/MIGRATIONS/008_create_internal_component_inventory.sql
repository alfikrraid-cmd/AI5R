-- MWO-LTSA-INTERNAL-COMPONENT-SCHEMA-001 -- reconciles the canonical
-- ingestion/upsert contract (ltsa_internal_component_ingestion.py /
-- ltsa_internal_component_upsert.py / ltsa_pump_inventory_db_upsert.py's
-- load_state()) with the persisted schema. Those Python modules were
-- already committed and already unconditionally query/insert/update
-- internal_component_master, internal_component_stock, and
-- seal_internal_component_link -- this migration brings a database
-- created before that contract existed up to the shape those modules
-- already require, without dropping or altering any existing table.
--
-- Table shapes verbatim from DATABASE/CANONICAL_SCHEMA.sql's own
-- "INTERNAL COMPONENT INVENTORY" section (MWO-LTSA-057E, Internal
-- Component Inventory Canonical Model): strictly internal AI5R /
-- engineering inventory, separate from user-facing seal_stock. GPN may
-- be temporarily pending during workbook migration, but every internal
-- component is expected to eventually have exactly one real GPN.
--
-- internal_component_rejections / internal_component_summary are
-- intentionally NOT tables here -- both are diagnostic-only structures
-- produced by build_internal_component_projection() and never queried
-- against a persisted table anywhere in the upsert pipeline.
--
-- Idempotent: every statement is CREATE ... IF NOT EXISTS, safe to re-run.

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
