CREATE INDEX IF NOT EXISTS idx_work_order_work_order_code
ON public.work_order (work_order_code);

CREATE INDEX IF NOT EXISTS idx_work_order_customer_code
ON public.work_order (customer_code);

CREATE INDEX IF NOT EXISTS idx_work_order_asset_code
ON public.work_order (asset_code);

CREATE INDEX IF NOT EXISTS idx_work_order_status
ON public.work_order (status);
