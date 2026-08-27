-- MWO-LTSA-WHATSAPP-INTAKE-FOUNDATION-024A -- WhatsApp intake foundation.
-- This migration creates sender mapping and pending-confirmation storage only.
-- It does not create PM/CMON records and does not alter operational tables.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.whatsapp_sender_identity (
    sender_e164_sha256 TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.users(id),
    provider TEXT NOT NULL DEFAULT 'whatsapp_cloud',
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    verified_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_sender_identity_user ON public.whatsapp_sender_identity(user_id);

CREATE TABLE IF NOT EXISTS public.whatsapp_intake_pending (
    intake_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    provider_message_id TEXT NOT NULL,
    sender_user_id UUID NOT NULL REFERENCES public.users(id),
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    original_message TEXT,
    detected_domain TEXT,
    structured_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    validation_result JSONB NOT NULL DEFAULT '{}'::jsonb,
    state TEXT NOT NULL DEFAULT 'RECEIVED',
    normalized_payload_hash TEXT NOT NULL,
    confirmation_id TEXT NOT NULL DEFAULT ('WA-CONF-' || replace(gen_random_uuid()::text, '-', '')),
    confirmed_by UUID REFERENCES public.users(id),
    confirmed_at TIMESTAMPTZ,
    provider_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    reply_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_whatsapp_intake_state CHECK (
        state IN ('RECEIVED', 'NEEDS_INFORMATION', 'READY_FOR_CONFIRMATION', 'CONFIRMED', 'CANCELLED', 'REJECTED', 'EXPIRED')
    ),
    CONSTRAINT chk_whatsapp_intake_domain CHECK (
        detected_domain IS NULL OR detected_domain IN ('PM', 'CONDITION_MONITORING', 'UNSUPPORTED_INTENT')
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_whatsapp_intake_delivery
    ON public.whatsapp_intake_pending(provider, provider_message_id, sender_user_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_whatsapp_intake_confirmation
    ON public.whatsapp_intake_pending(confirmation_id);

CREATE INDEX IF NOT EXISTS idx_whatsapp_intake_sender_state
    ON public.whatsapp_intake_pending(sender_user_id, state, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_whatsapp_intake_payload_hash
    ON public.whatsapp_intake_pending(sender_user_id, normalized_payload_hash);
