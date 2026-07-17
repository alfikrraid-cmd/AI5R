INSERT INTO public.worksheet_table (worksheet_table_id, worksheet_id, table_name)
VALUES ('TEST-001', 'TEST-001', 'Seed Test Table')
ON CONFLICT (worksheet_table_id) DO NOTHING;
