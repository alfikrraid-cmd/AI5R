-- Migration 055: LTSA work request (PM / CM / Installation request)
-- Lineage: migration 054 (054_hcc_master_reconciliation_r2a.sql)
-- Phase: LTSA_PERTAMINA_RBAC_SCOPE_AND_REQUEST_R2
--
-- A Pertamina Engineer is VIEW + REQUEST only. A request is its own record:
-- it is never a work_order, pm_occurrence, cm_report, condition-monitoring
-- reading or installation record, so submitting one creates no authoritative
-- maintenance or installation data and needs no maintenance.write /
-- installation.write. Execution and result entry stay with the existing
-- TAP-side workflows. Production work_order has no type column (TD-020), so
-- the request type could not be stored there either.
--
-- Additive only: one new table, no existing table altered, no data written.

CREATE TABLE IF NOT EXISTS public.ltsa_work_request (
    request_code   TEXT PRIMARY KEY,
    request_type   TEXT NOT NULL CHECK (request_type IN ('PM', 'CM', 'INSTALLATION')),
    asset_code     TEXT NOT NULL REFERENCES public.asset_registry(asset_code) ON DELETE RESTRICT,
    description    TEXT NOT NULL CHECK (btrim(description) <> ''),
    status         TEXT NOT NULL DEFAULT 'SUBMITTED' CHECK (status IN ('SUBMITTED')),
    requested_by   UUID NOT NULL REFERENCES public.users(id),
    requested_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ltsa_work_request_asset_code ON public.ltsa_work_request (asset_code);
CREATE INDEX IF NOT EXISTS idx_ltsa_work_request_requested_by ON public.ltsa_work_request (requested_by);

-- Rollback (manual, not executed by this file; forward-only convention,
-- see migration 040). Safe while nothing else references the table:
--
--   DROP TABLE IF EXISTS public.ltsa_work_request;
