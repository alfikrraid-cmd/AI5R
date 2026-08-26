-- MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016A
-- Additive only. condition_monitoring_schedule previously had no status/
-- next_due columns at all (left as an Open Question when the table was
-- first created -- see CANONICAL_SCHEMA.sql's own header comment on that
-- table), so the owner-approved PLANNED/ACTIVE/OVERDUE/COMPLETED/
-- CANCELLED lifecycle already implemented for pm_schedule
-- (MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016) could not be mirrored onto
-- Condition Monitoring without this migration. Mirrors pm_schedule's own
-- existing status/next_due shape exactly -- same column names, same
-- types, same DEFAULT convention (pm_schedule.status defaults 'ACTIVE';
-- this defaults 'PLANNED' since a brand-new CMON schedule has never had
-- a stored status before and 'PLANNED' is the correct starting state
-- under the now-authoritative lifecycle, not a behavior change for any
-- existing row -- there are zero existing condition_monitoring_schedule
-- rows in production at the time of this migration).
--
-- No DROP, no RENAME, no rewrite of any existing column. No data
-- population, no historical backfill.

ALTER TABLE public.condition_monitoring_schedule
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'PLANNED',
    ADD COLUMN IF NOT EXISTS next_due TIMESTAMP;
