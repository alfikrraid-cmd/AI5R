-- MWO-LTSA-040B (Engineering Document Acquisition) -- idempotent upgrade
-- path for a database that already applied 001_create_table.sql in its
-- pre-040B (MWO-030) shape. Safe to re-run; mirrors the ALTER block in
-- DATABASE/CANONICAL_SCHEMA.sql.
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS knowledge_source_id TEXT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS document_number TEXT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS issue_date DATE;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS manufacturer TEXT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS language TEXT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS file_name TEXT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS file_format TEXT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS page_count INTEGER;

ALTER TABLE public.seal_engineering_document DROP CONSTRAINT IF EXISTS seal_engineering_document_type_check;
ALTER TABLE public.seal_engineering_document ADD CONSTRAINT seal_engineering_document_type_check
    CHECK (document_type IN (
        'DRAWING', 'DATASHEET', 'INSTALLATION_GUIDE', 'INSPECTION_SHEET',
        'MAINTENANCE_MANUAL', 'SERVICE_BULLETIN', 'ENGINEERING_SPECIFICATION'
    ));

ALTER TABLE public.seal_engineering_document DROP CONSTRAINT IF EXISTS seal_engineering_document_page_count_check;
ALTER TABLE public.seal_engineering_document ADD CONSTRAINT seal_engineering_document_page_count_check
    CHECK (page_count IS NULL OR page_count >= 0);

ALTER TABLE public.seal_engineering_document DROP CONSTRAINT IF EXISTS seal_engineering_document_knowledge_source_fk;
ALTER TABLE public.seal_engineering_document
    ADD CONSTRAINT seal_engineering_document_knowledge_source_fk
    FOREIGN KEY (knowledge_source_id) REFERENCES public.knowledge_source_registry(knowledge_source_id);
