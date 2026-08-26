-- MWO-LTSA-PM-CONDITION-MONITORING-SCHEDULE-FOUNDATION-013
-- Additive schedule attribution and soft-delete metadata only.
-- No schedule data population, historical rewrite, DROP, TRUNCATE, or DELETE.

ALTER TABLE public.pm_schedule
    ADD COLUMN IF NOT EXISTS maintenance_type TEXT DEFAULT 'PREVENTIVE_MAINTENANCE',
    ADD COLUMN IF NOT EXISTS interval_unit TEXT,
    ADD COLUMN IF NOT EXISTS effective_date DATE,
    ADD COLUMN IF NOT EXISTS source_reference TEXT,
    ADD COLUMN IF NOT EXISTS provenance TEXT DEFAULT 'MANUAL',
    ADD COLUMN IF NOT EXISTS created_by UUID,
    ADD COLUMN IF NOT EXISTS updated_by UUID,
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS deleted_by UUID;

ALTER TABLE public.condition_monitoring_schedule
    ADD COLUMN IF NOT EXISTS monitoring_type TEXT,
    ADD COLUMN IF NOT EXISTS measurement_point TEXT,
    ADD COLUMN IF NOT EXISTS interval_unit TEXT,
    ADD COLUMN IF NOT EXISTS effective_date DATE,
    ADD COLUMN IF NOT EXISTS source_reference TEXT,
    ADD COLUMN IF NOT EXISTS provenance TEXT DEFAULT 'MANUAL',
    ADD COLUMN IF NOT EXISTS created_by UUID,
    ADD COLUMN IF NOT EXISTS updated_by UUID,
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS deleted_by UUID;

CREATE INDEX IF NOT EXISTS idx_pm_schedule_active_asset
    ON public.pm_schedule(asset_code) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_condition_monitoring_schedule_active_asset
    ON public.condition_monitoring_schedule(asset_code) WHERE deleted_at IS NULL;
