INSERT INTO public.engineering_media (engineering_media_id, knowledge_source_id, media_name, media_type)
VALUES ('TEST-001', 'TEST-001', 'Seed Test Engineering Media', 'PHOTO')
ON CONFLICT (engineering_media_id) DO NOTHING;
