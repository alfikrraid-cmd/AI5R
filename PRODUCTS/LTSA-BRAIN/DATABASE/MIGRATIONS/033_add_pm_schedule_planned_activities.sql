-- AI5R-PHASE4E1-PM-SCHEDULE-FOUNDATION
-- Additive only: one nullable JSONB column for PLANNED (not performed)
-- activities, plus relaxing `procedure` to nullable so the new optional
-- "Notes" UI field can persist through the same existing column without
-- requiring every caller to supply a value. No DROP, no RENAME, no
-- backfill, no data rewrite -- every existing pm_schedule row and every
-- existing procedure value is left byte-for-byte unchanged.

ALTER TABLE public.pm_schedule
    ADD COLUMN IF NOT EXISTS planned_activities JSONB;

ALTER TABLE public.pm_schedule
    ALTER COLUMN procedure DROP NOT NULL;
