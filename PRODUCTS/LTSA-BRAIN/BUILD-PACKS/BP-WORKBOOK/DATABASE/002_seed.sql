INSERT INTO public.workbook (workbook_id, knowledge_source_id, workbook_type, workbook_name)
VALUES ('TEST-001', 'TEST-001', 'PUMP_MASTER', 'Seed Test Workbook')
ON CONFLICT (workbook_id) DO NOTHING;
