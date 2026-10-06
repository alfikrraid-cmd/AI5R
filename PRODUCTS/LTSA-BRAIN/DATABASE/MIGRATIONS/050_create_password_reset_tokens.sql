-- MWO-LTSA-AUTH-FORGOT-PASSWORD-001 -- Durable reset token persistence for self-service password reset.
-- Base lineage: 4011a7ba31ff946f838dfcf21cecae4c1a53b2a2
-- Migration slot 050: globally collision-free (049 reserved by Power BI machine credentials R1C).
--
-- Security rules:
-- 1. Raw tokens MUST NEVER be stored. Only the SHA-256 hash (64 hex characters) is persisted.
-- 2. Token single-use: used_at is set atomically upon password reset; tokens with used_at IS NOT NULL cannot be reused.
-- 3. Expiry: 15 minutes from issuance (expires_at). Checked via expires_at > now().
-- 4. Foreign key to public.users(id) with ON DELETE CASCADE.
-- 5. Timestamps use TIMESTAMPTZ.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_password_reset_tokens_hash
    ON public.password_reset_tokens (token_hash);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id
    ON public.password_reset_tokens (user_id);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at
    ON public.password_reset_tokens (expires_at);
