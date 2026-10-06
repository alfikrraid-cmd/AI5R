-- LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -- password-change state on users.
-- Base lineage: b99c25119812abca54813a40e0ab4b465e72e6dc
-- Migration slot 051: unused on every branch at time of writing (050 = password reset tokens).
--
-- must_change_password: TRUE forces the user through POST /api/auth/change-password
--   before any other authenticated API is reachable (set by admin create with a
--   temporary password, and by admin password reset). Existing users get FALSE.
-- password_changed_at: when the password was last changed (change, reset, admin reset).
--   Access tokens issued before this instant are rejected, so a password change ends
--   other sessions. Existing users stay NULL = no token invalidation; do NOT backfill,
--   a non-NULL value would sign out every session issued before it.
--
-- Additive only; ADD COLUMN IF NOT EXISTS is safe to execute repeatedly. A constant
-- DEFAULT on PostgreSQL 11+ does not rewrite the table.
-- Rollback: roll the application back first (it selects explicit columns, so the extra
-- columns are harmless to it), then ALTER TABLE public.users DROP COLUMN IF EXISTS for both.

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ NULL;
