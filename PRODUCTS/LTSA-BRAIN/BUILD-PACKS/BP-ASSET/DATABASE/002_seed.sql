INSERT INTO public.asset_registry (asset_code, asset_name)
VALUES ('TEST-001', 'Seed Test Asset')
ON CONFLICT (asset_code) DO NOTHING;
