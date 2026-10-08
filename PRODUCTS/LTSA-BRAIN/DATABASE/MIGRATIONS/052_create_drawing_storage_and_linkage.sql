-- Migration 052: LTSA Mechanical Seal Drawing Storage and Linkage Foundation (R9C)
-- Base lineage: d36a4bb9531d776b58d31034ded6b7cd98f3e171 (migration 051)
-- Additive only; safe to run against an existing database.

-- 1. Make seal_code nullable on seal_engineering_document so drawings can exist
-- independently of a pre-existing seal_registry record (e.g., pump General Arrangement drawings,
-- unlinked engineering files, or drawings prior to seal identification).
ALTER TABLE public.seal_engineering_document ALTER COLUMN seal_code DROP NOT NULL;

-- 2. Additive metadata columns to public.seal_engineering_document
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS object_key TEXT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS sha256_checksum TEXT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS content_type TEXT;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS uploaded_by UUID REFERENCES public.users(id) ON DELETE SET NULL;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS provenance TEXT DEFAULT 'MANUAL';
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS revision_status TEXT DEFAULT 'PENDING_REVIEW';
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS is_current_revision BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS superseded_at TIMESTAMPTZ;
-- R9D-BR03: Lineage tracking between legacy (E-series) and newer (GA-series) drawings
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS superseded_by_document_code TEXT REFERENCES public.seal_engineering_document(document_code) ON DELETE SET NULL;
ALTER TABLE public.seal_engineering_document ADD COLUMN IF NOT EXISTS drawing_generation TEXT CHECK (drawing_generation IS NULL OR drawing_generation IN ('LEGACY', 'NEWER', 'STANDARD'));

-- 3. Invariant: At most one CURRENT revision per drawing number for document_type = 'DRAWING'
CREATE UNIQUE INDEX IF NOT EXISTS idx_drawing_current_revision
    ON public.seal_engineering_document(document_number)
    WHERE (is_current_revision = TRUE AND document_type = 'DRAWING');

-- 4. Checksum index for instant deduplication lookup
CREATE INDEX IF NOT EXISTS idx_seal_eng_doc_checksum
    ON public.seal_engineering_document(sha256_checksum);

CREATE INDEX IF NOT EXISTS idx_seal_eng_doc_superseded_by
    ON public.seal_engineering_document(superseded_by_document_code);

CREATE INDEX IF NOT EXISTS idx_seal_eng_doc_generation
    ON public.seal_engineering_document(drawing_generation);

-- 5. Additive association table for many-to-many drawing linkages and REFERENCE_ONLY support.
-- Supports document_code = NULL for pure reference-only evidence (e.g. pump/service/installation drawing refs).
-- R9C2: includes equipment_side (DE, NDE, SINGLE, NA, or NULL for unclassified) to support distinct pump sides.
-- Target types include DRAWING for validated legacy->newer drawing lineage traceability.
CREATE TABLE IF NOT EXISTS public.drawing_engineering_link (
    link_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_code TEXT REFERENCES public.seal_engineering_document(document_code) ON DELETE CASCADE,
    drawing_number TEXT NOT NULL,
    raw_reference TEXT,
    normalized_reference TEXT,
    target_type TEXT NOT NULL CHECK (target_type IN ('SEAL', 'PUMP', 'INSTALLATION', 'HISTORICAL_SERVICE', 'DRAWING')),
    target_code TEXT NOT NULL,
    equipment_side TEXT CHECK (equipment_side IS NULL OR equipment_side IN ('DE', 'NDE', 'SINGLE', 'NA')),
    source_type TEXT NOT NULL,
    source_record_id TEXT,
    evidence_method TEXT NOT NULL,
    confidence_status TEXT NOT NULL CHECK (confidence_status IN ('CONFIRMED', 'REFERENCE_ONLY', 'CONFLICT', 'UNLINKED')),
    notes TEXT,
    created_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_drawing_link_doc_code
    ON public.drawing_engineering_link(document_code);
CREATE INDEX IF NOT EXISTS idx_drawing_link_drawing_no
    ON public.drawing_engineering_link(drawing_number);
CREATE INDEX IF NOT EXISTS idx_drawing_link_normalized_ref
    ON public.drawing_engineering_link(normalized_reference);
CREATE INDEX IF NOT EXISTS idx_drawing_link_target
    ON public.drawing_engineering_link(target_type, target_code);
CREATE INDEX IF NOT EXISTS idx_drawing_link_equipment_side
    ON public.drawing_engineering_link(equipment_side);
CREATE INDEX IF NOT EXISTS idx_drawing_link_confidence
    ON public.drawing_engineering_link(confidence_status);

