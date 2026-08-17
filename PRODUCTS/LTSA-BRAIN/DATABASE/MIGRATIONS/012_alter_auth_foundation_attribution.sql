-- MWO-LTSA-AUTH-003A-FINAL -- minimal Record Attribution foundation for
-- the auth/user-administration domain itself (Phase 11's own carve-out:
-- "If auth/user administration itself requires attribution changes,
-- implement them minimally" -- PM/CM/Inventory/Installation are
-- explicitly OUT of this MWO's scope; this migration touches only the
-- two tables migration 007 already created).
--
-- created_by/updated_by are both nullable, self-referencing UUID
-- pointers to users.id -- never a display name (Hard Rule 18: "Last
-- Updated By must identify an immutable user identity"). Nullable
-- because the very first bootstrap user(s) (ltsa_bootstrap_admin.py) are
-- created by an out-of-band operator action with no prior authenticated
-- actor to attribute to -- exactly the same "informal reference where a
-- real one cannot always exist" reasoning already used elsewhere in this
-- schema, except here a real DB-level FK is safe and correct: unlike
-- installation_report/document_field_extraction (which predate `users`
-- in CANONICAL_SCHEMA.sql's own bootstrap order), this migration always
-- runs strictly after migration 007 creates `users`, so the FK can never
-- fail to resolve.
--
-- updated_at already exists on both tables (migration 007) and is left
-- untouched; a creator must never be overwritten by a later editor (Hard
-- Rule 19), so created_by is set once, at INSERT time, by the caller.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS is a no-op on a table that already
-- has these columns, so re-running this file is always safe.

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES public.users(id);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES public.users(id);

ALTER TABLE public.organization_memberships ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES public.users(id);
ALTER TABLE public.organization_memberships ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES public.users(id);
