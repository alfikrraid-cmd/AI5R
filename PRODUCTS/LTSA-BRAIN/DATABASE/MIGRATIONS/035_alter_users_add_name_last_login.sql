-- MWO-LTSA-SUPERUSER-USER-MANAGEMENT-001
-- Add human user display name and last_login timestamp tracking to users table.
-- Idempotent: ADD COLUMN IF NOT EXISTS is safe to execute repeatedly.

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS name VARCHAR(255);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;

