-- AI5R — Power BI Machine Credentials & Audit Ledger
-- Phase: LTSA_POWER_BI_R1C_MACHINE_CREDENTIAL_IMPLEMENTATION_R1
-- Base Lineage: 0254379deeaa524f3d707d5e3df3c3c473da9e27
-- Contract: ltsa-bi/1.0.0
--
-- Provisions durable storage for unattended Power BI Service and Desktop
-- scheduled refresh machine credentials (Basic Auth over HTTPS).
--
-- Security & Governance Constraints:
-- 1. Structural role enforcement: CHECK (role = 'BI_READER') prevents privilege escalation.
-- 2. Scrypt canonical hash format: scrypt$16384$8$1$<salt_hex>$<hash_hex>
-- 3. Dual-hash zero-downtime rotation: primary_secret_hash + secondary_secret_hash with grace expiry.
-- 4. Organization tenant binding: references public.organizations(id).
-- 5. Independent of quarantined R4 migrations (040-048).
--
-- Forward-only migration convention.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.ltsa_bi_machine_credential (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL UNIQUE,
    description TEXT,
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE RESTRICT,
    role TEXT NOT NULL DEFAULT 'BI_READER' CHECK (role = 'BI_READER'),
    primary_secret_hash TEXT NOT NULL,
    primary_created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    secondary_secret_hash TEXT,
    secondary_created_at TIMESTAMPTZ,
    secondary_expires_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'REVOKED', 'EXPIRED')),
    revoked_at TIMESTAMPTZ,
    revoked_by TEXT,
    revocation_reason TEXT,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bi_machine_credential_client_id
    ON public.ltsa_bi_machine_credential (client_id);

CREATE INDEX IF NOT EXISTS idx_bi_machine_credential_org_id
    ON public.ltsa_bi_machine_credential (organization_id);

CREATE TABLE IF NOT EXISTS public.ltsa_bi_credential_audit_event (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES public.ltsa_bi_machine_credential(id) ON DELETE SET NULL,
    client_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('CREDENTIAL_CREATED', 'AUTH_SUCCESS', 'AUTH_FAILURE', 'CREDENTIAL_ROTATED', 'CREDENTIAL_REVOKED', 'CREDENTIAL_EXPIRED')),
    actor TEXT NOT NULL DEFAULT 'SYSTEM',
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_ip TEXT,
    user_agent TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_bi_audit_client_id
    ON public.ltsa_bi_credential_audit_event (client_id);

CREATE INDEX IF NOT EXISTS idx_bi_audit_occurred_at
    ON public.ltsa_bi_credential_audit_event (occurred_at);

-- Documented Rollback (forward-only repository convention):
-- DROP TABLE IF EXISTS public.ltsa_bi_credential_audit_event;
-- DROP TABLE IF EXISTS public.ltsa_bi_machine_credential;
