-- MWO-AUTH-USERNAME-001 -- backward-compatible username login support.
-- Legacy rows are not assigned fabricated usernames; username remains NULL
-- for existing users until an administrator sets a real human login name.
-- PostgreSQL UNIQUE permits multiple NULL emails, so existing email login
-- remains unique when present while email becomes optional for new users.

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS username VARCHAR(50);
ALTER TABLE public.users ALTER COLUMN email DROP NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_users_username_lower_present
ON public.users (lower(username))
WHERE username IS NOT NULL;