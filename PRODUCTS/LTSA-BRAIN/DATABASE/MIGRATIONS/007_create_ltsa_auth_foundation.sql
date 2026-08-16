-- MWO-LTSA-AUTH-001 -- Human Identity + Server Authorization Foundation.
-- Canonical User/Organization/OrganizationMembership only. No role/
-- permission tables -- the fixed V1 role set and its permission mapping
-- live in code (API.auth_service.ROLE_PERMISSIONS), per this MWO's own
-- "Do not create DB role/permission tables unless repository precedent
-- or implementation evidence genuinely requires them" instruction.
--
-- Deliberately NOT added to any existing engineering table
-- (ltsa_pumps/seal_registry/etc.): those remain canonical, organization-
-- agnostic objects per this MWO's explicit "Data Model Correction" --
-- visibility is a relationship/scope concern, layered separately
-- (future MWO-LTSA-AUTH-003 for pump/inventory visibility scope,
-- MWO-LTSA-BOQ-001 for contract/BOQ scope), never a duplicated
-- organization_id column on the canonical object itself.
--
-- Reuses the same gen_random_uuid()/pgcrypto convention
-- 005_create_customer_registry.sql already established (the most recent
-- prior migration), not uuid-ossp's uuid_generate_v4() (the older
-- convention on ltsa_pumps).

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_organizations_code ON public.organizations(code);

-- V1 canonical organizations (frozen list, per this MWO's Decision 3 --
-- "Organization must be canonical persisted data," never a hardcoded
-- string comparison in application code). Idempotent: safe to re-run.
INSERT INTO public.organizations (code, name)
VALUES ('TAP', 'TAP'), ('PERTAMINA_RU_II', 'Pertamina RU II')
ON CONFLICT (code) DO NOTHING;

-- email is the only login identifier -- no unnecessary profile fields,
-- per this MWO's own "Do not add unnecessary profile fields" instruction.
-- password_hash stores the full encoded scrypt record (algorithm/cost
-- params/salt/hash, see API.auth_password.hash_password) -- never a raw
-- password, never returned by any API response (proven by
-- test_auth_router.py::test_me_response_never_contains_password_hash).
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);

-- Composite PK, not a surrogate id: the real business key IS
-- (user_id, organization_id), the same "no independent identity beyond
-- the pair" discipline seal_pump_compatibility already established for
-- its own many-to-many junction. role is a free-text V1 fixed-role
-- name (TAP_ADMIN/TAP_ENGINEER/PERTAMINA_ENGINEER/PERTAMINA_VIEWER),
-- validated at the application layer (API.auth_service.ROLE_PERMISSIONS
-- is the single source of truth for which role names are valid) -- no
-- DB CHECK constraint duplicating that list, so adding a role in code
-- never requires a migration.
CREATE TABLE IF NOT EXISTS public.organization_memberships (
    user_id UUID NOT NULL REFERENCES public.users(id),
    organization_id UUID NOT NULL REFERENCES public.organizations(id),
    role VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, organization_id)
);

CREATE INDEX IF NOT EXISTS idx_organization_memberships_user ON public.organization_memberships(user_id);
