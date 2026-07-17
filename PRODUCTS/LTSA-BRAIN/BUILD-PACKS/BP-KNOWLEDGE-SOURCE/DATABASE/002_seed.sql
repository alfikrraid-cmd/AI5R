INSERT INTO public.knowledge_source_registry (knowledge_source_id, source_type, source_name)
VALUES ('TEST-001', 'ENGINEER_NOTE', 'Seed Test Source')
ON CONFLICT (knowledge_source_id) DO NOTHING;
