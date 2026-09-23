-- LTSA CM R2: preserve the API Plan applicable to each CM occurrence.
-- Nullable by design: old rows and rows without source/master API Plan
-- evidence remain explicitly unknown. No backfill is performed here.
ALTER TABLE public.condition_monitoring_reading
    ADD COLUMN IF NOT EXISTS api_plan_snapshot TEXT;
