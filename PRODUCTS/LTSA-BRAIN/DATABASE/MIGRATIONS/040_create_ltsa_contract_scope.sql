-- MWO-LTSA-CONTRACT-SCOPE-R3 -- minimum production-safe LTSA Contract
-- Scope foundation (Chief Architect approved design, R2).
--
-- Two additive tables. No existing table is altered, renamed, or
-- rewritten. No INSERT/backfill of any kind -- both tables start empty,
-- including in production, until an authorized operator explicitly
-- scopes a contract (a separate, later, human-reviewed action -- see
-- R2's own "EXISTING 257 ASSETS MUST NOT be automatically scoped").
--
-- ltsa_contract: the commercial agreement. No stored active/status
-- column by design (R2 decision 2) -- active/current state is always
-- derived at query time from start_date/end_date vs. the caller's
-- requested reporting period, the same "computed, never stored"
-- convention already established for pm_schedule/condition_monitoring_
-- schedule's own PLANNED/ACTIVE/OVERDUE lifecycle (see migration 029's
-- own header). customer_code is nullable: customer_registry has zero
-- rows in this environment today, so a hard NOT NULL FK would make this
-- table unusable until that table is separately populated -- the FK
-- itself is still wired now so referential integrity is enforced the
-- moment a customer row does exist.
--
-- ltsa_contract_asset_scope: the explicit join that makes contract
-- membership provable (R2 decision 4) -- never inferred from
-- asset_registry.status, ltsa_pumps membership, area, MA, or PM/CM
-- history. asset_code FK's straight to asset_registry (the proven
-- canonical asset identity authority, R1/R2) -- never ltsa_pumps,
-- never a duplicate tag/area/asset_type column (those stay
-- asset_registry's own authority, per R2's explicit "avoid duplicating
-- asset tag/area/asset type" instruction). scope_start_date/
-- scope_end_date are optional per-asset overrides; when null they
-- inherit the parent contract's own start_date/end_date (R2's
-- "inherited dates" rule) -- resolved by callers, not by a trigger or
-- generated column, keeping this migration a pure additive DDL change.
-- PRIMARY KEY (contract_code, asset_code) prevents the same asset being
-- double-scoped within one contract; the same asset MAY legitimately
-- appear under more than one contract_code (different rows) -- a real
-- business case (e.g. contract renewal/succession), not a bug.
--
-- No mechanical seal / seal_registry / seal_unit reference anywhere in
-- this migration (R2 decision 6 -- seals stay out of contract asset
-- scope this phase).

CREATE TABLE IF NOT EXISTS public.ltsa_contract (
    contract_code   TEXT PRIMARY KEY,
    contract_name   TEXT NOT NULL,
    customer_code   TEXT REFERENCES public.customer_registry(customer_code) ON DELETE RESTRICT,
    start_date      DATE NOT NULL,
    end_date        DATE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    CONSTRAINT ltsa_contract_dates_check CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_ltsa_contract_customer_code ON public.ltsa_contract(customer_code);

CREATE TABLE IF NOT EXISTS public.ltsa_contract_asset_scope (
    contract_code     TEXT NOT NULL REFERENCES public.ltsa_contract(contract_code) ON DELETE CASCADE,
    asset_code        TEXT NOT NULL REFERENCES public.asset_registry(asset_code) ON DELETE RESTRICT,
    scope_start_date  DATE,
    scope_end_date    DATE,
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (contract_code, asset_code),
    CONSTRAINT ltsa_contract_asset_scope_dates_check
        CHECK (scope_start_date IS NULL OR scope_end_date IS NULL OR scope_end_date >= scope_start_date)
);

-- Coverage/asset-listing queries always filter by contract_code first
-- (every planned endpoint is scoped to one contract) and frequently
-- need "which contracts scope this asset" (e.g. future write-path
-- validation) -- the PK already covers the first access path
-- (contract_code, asset_code); this covers the reverse.
CREATE INDEX IF NOT EXISTS idx_ltsa_contract_asset_scope_asset_code ON public.ltsa_contract_asset_scope(asset_code);

-- Rollback (manual, not executed by this file -- forward-only migration
-- convention already established in this directory, see migration 035):
--
--   DROP TABLE IF EXISTS public.ltsa_contract_asset_scope;
--   DROP TABLE IF EXISTS public.ltsa_contract;
--
-- Safe unconditionally: both tables are new, nothing else references
-- them yet, and this migration performs no data changes to roll back.
