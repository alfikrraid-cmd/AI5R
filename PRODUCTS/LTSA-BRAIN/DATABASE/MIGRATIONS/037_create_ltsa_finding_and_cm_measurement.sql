-- MWO-LTSA-REPORTING-R3 -- additive schema-only foundation approved in
-- LTSA_REPORTING_R2_DATA_FOUNDATION. Two new tables. No existing table
-- altered, no data migrated, no historical backfill, no rows inserted
-- by this migration (both tables start empty everywhere, including
-- production).
--
-- ltsa_finding: normalized cross-domain finding entity. Reuses the exact
-- informal polymorphic reference convention already proven by
-- pm_cm_evidence.record_type/record_code (migration 014) -- source_domain
-- CHECK vocabulary extended with 'INSTALLATION_REPORT' as a third domain
-- alongside the two pm_cm_evidence already supports. source_record_code
-- is deliberately NOT a real FK (no single target table exists across
-- three domains without a supertype -- same reasoning already recorded
-- in migration 014's own header for record_code). status/severity are
-- both nullable TEXT with a CHECK vocabulary; NULL is the literal
-- representation of "N/A / unknown" (Chief's own R2 decision) -- never a
-- 4th enum value. Severity is never derived from asset criticality
-- (asset_registry/ltsa_pumps C/SC is a wholly separate fact) -- this
-- migration enforces nothing that could conflate the two; that
-- discipline belongs to the future R4 API layer, not to a DB constraint.
-- No uniqueness constraint on (source_domain, source_record_code):
-- multiple legitimate findings may belong to one CM/PM/Installation
-- transaction (Chief's own explicit R3 instruction) -- a plain index
-- only.
--
-- asset_code FKs to asset_registry (the proven canonical asset identity
-- authority, R1/R2) following the same convention migration 036 already
-- established for new tables (unlike the older, pre-asset_registry-era
-- transaction tables' own plain-TEXT asset_code columns) -- nullable,
-- since an Installation Report finding does not always resolve to one
-- canonical asset the same way a CM reading always does. ON DELETE
-- RESTRICT matches migration 036's own asset_code FK exactly: a
-- referenced asset must not be deletable while findings still point to
-- it. No MA/area/equipment metadata is duplicated here -- always
-- resolved from asset_registry / resolve_area_ma() at query time.
--
-- created_by/updated_by/owner_pic are plain UUID with no FK to `users` --
-- this matches the established, still-current PM/Condition-Monitoring
-- domain convention (migrations 014/027/028: pm_occurrence.created_by,
-- condition_monitoring_reading.created_by, pm_schedule.created_by/
-- updated_by are all plain UUID, never FK'd to users), not the
-- auth-domain-only FK pattern from migration 012 (which applies solely
-- to users/organization_memberships). owner_pic is the PIC/owner
-- *reference* Chief's R3 instruction asks for ("owner/pic reference
-- where architecture supports it") -- a raw actor UUID, consistent with
-- this domain's own disclosed "no display-name resolution" limitation,
-- not a new free-text name field.
--
-- condition_monitoring_reading_measurement: the HYBRID (Option C)
-- generic child table approved in R2 -- holds the 12 currently-MISSING
-- CM concepts (separator x3, cooler-surface/product x4, buffer x2,
-- reservoir x3, temperature gauge x1) and the 3 AMBIGUOUS fields
-- (stored under their literal source_label, never a guessed canonical
-- measurement_code -- this migration inserts zero rows for any of them,
-- pending field-engineering resolution) plus any future measurement
-- type, without ever touching the 44 existing named columns on
-- condition_monitoring_reading. reading_id is a REAL FK this time
-- (unlike pm_cm_evidence's informal record_code) because a measurement
-- row is genuinely meaningless without its parent reading -- ON DELETE
-- CASCADE matches the one directly analogous precedent in this schema
-- (migration 036's ltsa_contract_asset_scope.contract_code -> a child
-- row that only exists because of its parent), not RESTRICT (which
-- migration 036 reserves for references to a shared master/reference
-- table like asset_registry/customer_registry, the opposite case here).
-- measurement_code is nullable TEXT with NO enum/CHECK constraint --
-- deliberately open-ended so a newly-observed measurement type can be
-- inserted under a new code with zero future migration, matching
-- Chief's own "supports future measurement types without repeated
-- schema migrations" requirement exactly. measurement_label is the
-- always-required human-readable label; source_label is a separate,
-- nullable field reserved for preserving a literal, as-found source
-- wording verbatim when it differs from (or is not yet resolved to) a
-- canonical measurement_label -- exactly the mechanism the 3 AMBIGUOUS
-- CM fields need. verification_status reuses the EXACT existing
-- repo-standard vocabulary already defined on
-- knowledge_source_registry.verification_status (DRAFT/UNDER_REVIEW/
-- VERIFIED/CANONICAL) rather than inventing a new one -- appropriate
-- here since it maps directly onto the same underlying concept (has
-- this stored fact been engineering-confirmed yet).
--
-- Value storage: value_numeric and value_text are both nullable columns
-- on the same row (never a variant/tagged-union type this schema has no
-- precedent for) with a CHECK requiring at least one to be populated --
-- a numeric gauge reading uses value_numeric, a checklist/text
-- observation uses value_text, and this migration performs no
-- conversion between the two in either direction.

CREATE TABLE IF NOT EXISTS public.ltsa_finding (
    finding_code        TEXT PRIMARY KEY NOT NULL,
    source_domain        TEXT NOT NULL
        CHECK (source_domain IN ('CONDITION_MONITORING_READING', 'PM_OCCURRENCE', 'INSTALLATION_REPORT')),
    source_record_code   TEXT NOT NULL,
    asset_code           TEXT REFERENCES public.asset_registry(asset_code) ON DELETE RESTRICT,
    finding_text         TEXT NOT NULL,
    status               TEXT CHECK (status IS NULL OR status IN ('OPEN', 'IN_PROGRESS', 'CLOSED')),
    severity             TEXT CHECK (severity IS NULL OR severity IN ('NORMAL', 'ATTENTION', 'CRITICAL')),
    recommendation       TEXT,
    action               TEXT,
    owner_pic            UUID,
    opened_date          DATE,
    closed_date          DATE,
    source_reference     TEXT,
    created_at           TIMESTAMP DEFAULT NOW(),
    created_by           UUID,
    updated_at           TIMESTAMP DEFAULT NOW(),
    updated_by           UUID,
    CONSTRAINT ltsa_finding_closed_date_check CHECK (closed_date IS NULL OR opened_date IS NULL OR closed_date >= opened_date)
);

CREATE INDEX IF NOT EXISTS idx_ltsa_finding_source ON public.ltsa_finding(source_domain, source_record_code);
CREATE INDEX IF NOT EXISTS idx_ltsa_finding_asset_code ON public.ltsa_finding(asset_code);
CREATE INDEX IF NOT EXISTS idx_ltsa_finding_status ON public.ltsa_finding(status) WHERE status IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ltsa_finding_severity ON public.ltsa_finding(severity) WHERE severity IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.condition_monitoring_reading_measurement (
    measurement_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reading_id           TEXT NOT NULL REFERENCES public.condition_monitoring_reading(condition_monitoring_reading_code) ON DELETE CASCADE,
    measurement_code     TEXT,
    measurement_label    TEXT NOT NULL,
    value_numeric        NUMERIC,
    value_text           TEXT,
    unit                 TEXT,
    measurement_side     TEXT CHECK (measurement_side IS NULL OR measurement_side IN ('DE', 'NDE')),
    source_label         TEXT,
    source_reference     TEXT,
    verification_status  TEXT NOT NULL DEFAULT 'DRAFT'
        CHECK (verification_status IN ('DRAFT', 'UNDER_REVIEW', 'VERIFIED', 'CANONICAL')),
    created_at           TIMESTAMP DEFAULT NOW(),
    created_by           UUID,
    updated_at           TIMESTAMP DEFAULT NOW(),
    updated_by           UUID,
    CONSTRAINT condition_monitoring_reading_measurement_value_check
        CHECK (value_numeric IS NOT NULL OR value_text IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_condition_monitoring_reading_measurement_reading_id
    ON public.condition_monitoring_reading_measurement(reading_id);

-- Rollback (manual, not executed by this file -- forward-only migration
-- convention already established in this directory, see migrations 035/036):
--
--   DROP TABLE IF EXISTS public.condition_monitoring_reading_measurement;
--   DROP TABLE IF EXISTS public.ltsa_finding;
--
-- Safe unconditionally: both tables are new, nothing else references
-- them yet, and this migration performs no data changes to roll back.
