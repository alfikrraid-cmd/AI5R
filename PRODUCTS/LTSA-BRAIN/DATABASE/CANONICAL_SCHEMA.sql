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
    updated_at TIMESTAMP DEFAULT NOW()
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
-- MWO-LTSA-040A is logical only here -- seal_engineering_document (above)
-- is intentionally left unmodified; no FK is added in either direction.
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
            'ENGINEERING_SPECIFICATION', 'CALIBRATION_REPORT', 'HYDROTEST_REPORT'
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
