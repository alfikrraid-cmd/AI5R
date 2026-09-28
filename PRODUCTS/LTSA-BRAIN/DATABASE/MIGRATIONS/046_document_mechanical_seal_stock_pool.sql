-- MECHANICAL-SEAL-DOMAIN-CONSOLIDATION-R1 -- schema-governance catch-up.
--
-- Same situation MWO-LTSA-069 already documented once for
-- whatsapp_group_authorization (see 034_KNOWN_MIGRATION_STATE.md): a
-- read-only Phase 1 audit for this mission found public.
-- mechanical_seal_stock_pool and public.mechanical_seal_stock_application
-- are real tables, actively queried by CORE-SERVICES/API/
-- mechanical_seal_stock_repository.py (backing GET /api/ltsa/mechanical-
-- seal-stock and the Mechanical Seal Stock UI page), with NO migration
-- file anywhere in this repository and NO reference in any .md doc --
-- confirmed by grepping the full repo (source, migrations, docs) for
-- both table names before writing this file. Applied out-of-band, by
-- whom/when is UNKNOWN, same as 032 was.
--
-- Verification performed: read-only `\d public.mechanical_seal_stock_pool`
-- / `\d public.mechanical_seal_stock_application` against the LOCAL
-- DEVELOPMENT container `ai5r-runtime-postgres-1` (AI5R_ENV=development,
-- CORE-SERVICES/RUNTIME/.env), 2026-09-16. That container was also found
-- to predate migration 013 (seal_registry has no kimap_pertamina/
-- gpn_john_crane/created_by/updated_by columns there), so it is not a
-- reliable stand-in for "current production schema" in general -- but
-- for these two specific tables, which no migration governs either way,
-- its live DDL is the best available evidence and is reproduced exactly
-- below. NOT verified against the production database (034's own
-- ai5ros-prod-postgres-1 container was not running in this environment).
--
-- CREATE TABLE IF NOT EXISTS: a pure no-op wherever these tables already
-- exist correctly (production included) -- this migration documents
-- reality, it does not assert or force it. It does not attempt to ALTER
-- an existing table into matching this shape, since any drift between
-- this captured DDL and a real environment's actual table is itself
-- exactly the kind of fact this migration must not silently paper over.
--
-- NOT applied to production by this action -- per this mission's
-- explicit "DO NOT modify production DB" instruction. An operator
-- applying this file to any environment should first run the same `\d`
-- checks against that target and confirm no drift before relying on it.

CREATE TABLE IF NOT EXISTS public.mechanical_seal_stock_pool (
    stock_pool_id         TEXT PRIMARY KEY,
    seal_code             TEXT REFERENCES public.seal_registry(seal_code),
    seal_type             TEXT NOT NULL,
    nominal_size          TEXT NOT NULL,
    size_unit             TEXT NOT NULL DEFAULT 'INCH',
    normalized_size       TEXT,
    application_size      TEXT,
    physical_stock_size   TEXT,
    drawing_reference     TEXT,
    complete_seal_gpn     TEXT,
    quantity_on_hand      NUMERIC,
    quantity_reserved     NUMERIC NOT NULL DEFAULT 0,
    quantity_available    NUMERIC GENERATED ALWAYS AS (
                              CASE
                                  WHEN quantity_on_hand IS NULL THEN NULL::numeric
                                  ELSE quantity_on_hand - quantity_reserved
                              END
                          ) STORED,
    stock_location        TEXT,
    verification_status   TEXT NOT NULL DEFAULT 'UNKNOWN'
                          CHECK (verification_status IN (
                              'CONFIRMED', 'VERIFY', 'VERIFY_CONFIGURATION',
                              'VERIFY_SIZE_COMPATIBILITY', 'MASTER_LINK_VERIFY', 'UNKNOWN'
                          )),
    compatibility_status  TEXT NOT NULL DEFAULT 'UNKNOWN'
                          CHECK (compatibility_status IN ('CONFIRMED', 'VERIFY', 'UNKNOWN')),
    source_reference      TEXT,
    notes                 TEXT,
    created_at            TIMESTAMP DEFAULT now(),
    updated_at            TIMESTAMP DEFAULT now(),
    CONSTRAINT mechanical_seal_stock_pool_qty_check
        CHECK (quantity_on_hand IS NULL OR quantity_on_hand >= 0),
    CONSTRAINT mechanical_seal_stock_pool_reserved_check
        CHECK (quantity_reserved >= 0),
    CONSTRAINT mechanical_seal_stock_pool_available_check
        CHECK (quantity_on_hand IS NULL OR quantity_reserved <= quantity_on_hand)
);

CREATE INDEX IF NOT EXISTS idx_mechanical_seal_stock_pool_seal_code
    ON public.mechanical_seal_stock_pool (seal_code);
CREATE INDEX IF NOT EXISTS idx_mechanical_seal_stock_pool_verification
    ON public.mechanical_seal_stock_pool (verification_status);

CREATE TABLE IF NOT EXISTS public.mechanical_seal_stock_application (
    stock_application_id           TEXT PRIMARY KEY,
    stock_pool_id                  TEXT NOT NULL
                                    REFERENCES public.mechanical_seal_stock_pool(stock_pool_id),
    equipment_tag                  TEXT NOT NULL,
    complete_seal_gpn              TEXT,
    seal_type_as_recorded          TEXT,
    size_as_recorded               TEXT,
    drawing_reference_as_recorded  TEXT,
    configuration_marker           TEXT,
    lifecycle_marker               TEXT,
    area                           TEXT,
    equipment_type                 TEXT,
    contract_group                 TEXT,
    verification_status            TEXT NOT NULL DEFAULT 'UNKNOWN'
                                    CHECK (verification_status IN (
                                        'CONFIRMED', 'VERIFY', 'VERIFY_CONFIGURATION',
                                        'VERIFY_SIZE_COMPATIBILITY', 'MASTER_LINK_VERIFY', 'UNKNOWN'
                                    )),
    compatibility_status           TEXT NOT NULL DEFAULT 'UNKNOWN'
                                    CHECK (compatibility_status IN ('CONFIRMED', 'VERIFY', 'UNKNOWN')),
    notes                           TEXT,
    created_at                     TIMESTAMP DEFAULT now(),
    updated_at                     TIMESTAMP DEFAULT now(),
    CONSTRAINT mechanical_seal_stock_application_unique UNIQUE (stock_pool_id, equipment_tag)
);

CREATE INDEX IF NOT EXISTS idx_mechanical_seal_stock_application_pool
    ON public.mechanical_seal_stock_application (stock_pool_id);
CREATE INDEX IF NOT EXISTS idx_mechanical_seal_stock_application_equipment
    ON public.mechanical_seal_stock_application (equipment_tag);

-- Documented Rollback (forward-only repository convention):
--
-- DROP TABLE IF EXISTS public.mechanical_seal_stock_application;
-- DROP TABLE IF EXISTS public.mechanical_seal_stock_pool;
-- (Only safe if this migration is what created them -- never run this
-- against an environment where these tables predate this file.)
