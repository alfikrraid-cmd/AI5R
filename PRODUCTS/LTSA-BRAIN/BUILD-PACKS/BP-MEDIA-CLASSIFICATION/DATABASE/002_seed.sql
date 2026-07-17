INSERT INTO public.media_classification (media_classification_id, engineering_media_id, classification_type)
VALUES ('TEST-001', 'TEST-001', 'PHOTO')
ON CONFLICT (media_classification_id) DO NOTHING;
