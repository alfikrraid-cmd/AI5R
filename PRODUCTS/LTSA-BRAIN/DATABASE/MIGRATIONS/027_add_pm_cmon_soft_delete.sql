-- MWO-LTSA-PM-CONDITION-MONITORING-FOUNDATION-012
-- Additive soft-delete markers preserve operational records and auditability.
-- No historical import, rewrite, DROP, TRUNCATE, or legacy-table mutation.

ALTER TABLE public.pm_occurrence
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS deleted_by UUID;

ALTER TABLE public.condition_monitoring_reading
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS deleted_by UUID;

CREATE INDEX IF NOT EXISTS idx_pm_occurrence_active_asset
    ON public.pm_occurrence(asset_code, occurrence_date)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_condition_monitoring_reading_active_asset
    ON public.condition_monitoring_reading(asset_code, reading_date)
    WHERE deleted_at IS NULL;
