-- AI5R Generated SQL
-- Product: LTSA-BRAIN

-- DEPRECATED (MWO-P-002 / IR-001): superseded by the canonical `customer_registry`
-- definition in ../DATABASE/MIGRATIONS/005_create_customer_registry.sql and
-- ../DATABASE/CANONICAL_SCHEMA.sql. This generic table is not referenced by any
-- workflow and must not be applied to a database that also runs the canonical
-- migration. Kept only for historical reference; do not deploy.
CREATE TABLE IF NOT EXISTS ltsa_customers (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- DEPRECATED (MWO-P-002 / IR-001): name collides with the canonical `ltsa_pumps`
-- table defined in ../MODULES/PUMP/DATABASE/001_create_pumps.sql (UUID PK,
-- tag_number/area schema), which is the definition actually queried by the
-- product's real workflows (WF-LTSA-PUMP-REGISTRY-001, WF-LTSA-PUMP-DETAIL-001).
-- This SERIAL/generic version must never be applied to the same database.
-- See ../DATABASE/CANONICAL_SCHEMA.sql. Kept only for historical reference.
CREATE TABLE IF NOT EXISTS ltsa_pumps (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ltsa_assets (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ltsa_inspections (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ltsa_maintenances (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
