# MWO-LTSA-TAP-GROUP-AGENT-001 — Proposed Migration (NOT APPLIED)

This document is a **design proposal only**. No schema in this document
has been created, and no production database has been touched. Phase 1
of the TAP LTSA WhatsApp Group Agent uses `InMemoryGroupAuthorizationRepository`
(`CORE-SERVICES/API/whatsapp_group_repository_inmemory.py`) exclusively —
state lives in process memory and is lost on restart, by design, per the
Phase 1 mission ("design it and test using disposable/local infrastructure
only... report proposed migration separately").

## Why a new table, not an extension of an existing one

`whatsapp_intake` (the existing personal-chat pending/confirmation table)
is shaped for a write-confirmation workflow (`create_pending`,
`find_pending_by_delivery_key`, `transition_pending`, ...) that does not
apply to group read-only Q&A. Reusing it would force an unrelated shape
onto a different concern. Group authorization and message dedup are new,
narrow, purely operational concerns — a new, small table pair is the
minimal-footprint choice, not a second user database (no user identity,
role, or credential is ever stored here).

## Proposed schema

```sql
-- Group authorization: mirrors whatsapp_registration_service.py's own
-- established PENDING -> ACTIVE (-> DISABLED) admin-gated lifecycle.
-- No plaintext WhatsApp group id is ever stored -- only its SHA256 hash,
-- matching hash_sender_identifier's own convention.
CREATE TABLE ltsa_whatsapp_group_authorization (
    group_hash          TEXT PRIMARY KEY,        -- sha256(raw transport group id)
    display_label       TEXT NOT NULL,           -- admin-supplied, never derived from untrusted transport metadata
    status               TEXT NOT NULL DEFAULT 'PENDING'
                         CHECK (status IN ('PENDING', 'ACTIVE', 'DISABLED')),
    allowed_scope_areas TEXT[],                  -- NULL = unrestricted; else intersected with sender's own scope, never unioned
    registered_by        TEXT NOT NULL,           -- admin user_id
    registered_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    activated_by         TEXT,
    activated_at         TIMESTAMPTZ,
    disabled_at          TIMESTAMPTZ
);

-- Dedup/replay ledger. provider_message_id is WhatsApp-transport-scoped
-- (Baileys message key id), globally unique per the transport's own
-- contract -- no separate "provider" column needed unless a second group
-- transport is added later, unlike whatsapp_intake's own provider column
-- (whose personal-chat providers already needed disambiguation).
CREATE TABLE ltsa_whatsapp_group_message_seen (
    provider_message_id TEXT PRIMARY KEY,
    seen_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Retention: rows older than e.g. 30 days can be safely pruned by a
-- scheduled job -- dedup only needs to cover the real-world window in
-- which WhatsApp/Baileys could plausibly redeliver the same event.
```

## Repository swap point

`CORE-SERVICES/BACKEND-API/dependencies.py`'s `get_group_authorization_repository()`
and the pipeline's `record_seen_message` call are the *only* things a
Postgres-backed implementation needs to replace — `whatsapp_group_agent_service.py`
and `routers/whatsapp_group_agent.py` depend only on
`GroupAuthorizationRepositoryProtocol`, never on the in-memory class
directly, so this is a single-file swap when the migration is approved
and applied.

## What this migration deliberately does NOT do

- Does not touch `organization_memberships`, `users`, or any existing
  auth table — sender authorization stays fully owned by the existing
  `find_identity_by_sender_hash` mechanism.
- Does not store a plaintext phone number or group id anywhere.
- Does not introduce a second WhatsApp provider/session-credential table
  — Baileys session material is filesystem-based local state (see
  `CORE-SERVICES/TAP-LTSA-GROUP-AGENT/README.md`), never persisted to
  Postgres.

## Status

**PROPOSED, NOT APPLIED.** Requires an explicit follow-up MWO/migration
review before any `CREATE TABLE` runs against a real database, dev or
production.
