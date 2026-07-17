INSERT INTO public.soot_blower_registry (soot_blower_code, soot_blower_name)
VALUES ('TEST-001', 'Seed Test Soot Blower')
ON CONFLICT (soot_blower_code) DO NOTHING;
