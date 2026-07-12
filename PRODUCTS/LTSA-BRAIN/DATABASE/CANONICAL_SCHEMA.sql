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
