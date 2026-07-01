INSERT INTO public.pump_registry (pump_code)
VALUES ('TEST-001')
ON CONFLICT (pump_code) DO NOTHING;
