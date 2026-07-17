CREATE INDEX IF NOT EXISTS idx_maintenance_history_record_code
ON public.maintenance_history (maintenance_record_code);

CREATE INDEX IF NOT EXISTS idx_maintenance_history_work_order_code
ON public.maintenance_history (work_order_code);

CREATE INDEX IF NOT EXISTS idx_maintenance_history_asset_code
ON public.maintenance_history (asset_code);
