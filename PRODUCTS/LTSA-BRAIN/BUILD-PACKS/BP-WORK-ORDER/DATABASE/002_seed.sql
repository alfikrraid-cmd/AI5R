INSERT INTO public.work_order (work_order_code, description)
VALUES ('TEST-001', 'Seed Test Work Order')
ON CONFLICT (work_order_code) DO NOTHING;
