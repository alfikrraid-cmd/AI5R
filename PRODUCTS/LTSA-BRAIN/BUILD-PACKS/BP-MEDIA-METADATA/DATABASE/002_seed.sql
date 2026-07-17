INSERT INTO public.media_metadata (media_metadata_id, engineering_media_id)
VALUES ('TEST-001', 'TEST-001')
ON CONFLICT (media_metadata_id) DO NOTHING;
