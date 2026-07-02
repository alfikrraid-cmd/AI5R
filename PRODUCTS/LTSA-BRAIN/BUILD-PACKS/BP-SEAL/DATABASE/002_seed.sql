INSERT INTO public.seal_registry (seal_code)
VALUES ('TEST-001')
ON CONFLICT (seal_code) DO NOTHING;
