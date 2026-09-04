-- MWO-LTSA-TAP-GROUP-AGENT-001 Phase 2A -- persistent group authorization
-- + message dedupe ledger for the TAP LTSA WhatsApp Group Agent. Additive
-- only: two new tables, nothing existing altered. Mirrors
-- whatsapp_intake_pending's own established PENDING-lifecycle/attribution
-- shape (registered_by/activated_by as free-text actor references, same
-- as confirmed_by there -- no new FK to organizations/users introduced,
-- since group authorization is intentionally NOT the user database).
--
-- No plaintext WhatsApp group id or phone number is ever stored -- only
-- SHA256 hashes, matching hash_sender_identifier's own convention
-- (whatsapp_intake_service.py) and this migration's own group_hash.
--
-- NOT applied to production by this MWO -- report only, per instruction
-- (Phase 2A: build + test only, no real number paired, no deploy).

CREATE TABLE IF NOT EXISTS public.whatsapp_group_authorization (
    group_hash      TEXT PRIMARY KEY,
    display_label   TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'ACTIVE', 'DISABLED')),
    allowed_scope   TEXT[],
    registered_by   TEXT NOT NULL,
    registered_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    activated_by    TEXT,
    activated_at    TIMESTAMPTZ,
    disabled_by     TEXT,
    disabled_at     TIMESTAMPTZ
);

-- provider_message_id is WhatsApp/Baileys-transport-scoped, globally
-- unique per that transport's own contract -- stored as-is (not hashed),
-- matching whatsapp_intake_pending.last_outbound_provider_message_id's
-- own existing precedent of storing this exact id in plaintext (it is an
-- opaque message identifier, never a phone number or message body).
-- seen_at drives bounded retention: a scheduled job (not part of this
-- migration) prunes rows older than the real-world redelivery window
-- WhatsApp/Baileys could plausibly replay within (e.g. 30 days) -- this
-- table is a dedupe ledger, never a conversation log, and never grows
-- unbounded by design.
CREATE TABLE IF NOT EXISTS public.whatsapp_group_message_seen (
    provider_message_id TEXT PRIMARY KEY,
    seen_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_whatsapp_group_message_seen_seen_at
    ON public.whatsapp_group_message_seen(seen_at);
