CREATE TABLE IF NOT EXISTS public.pdf_metadata (
    pdf_metadata_id TEXT PRIMARY KEY NOT NULL,
    pdf_document_id TEXT NOT NULL REFERENCES public.pdf_document(pdf_document_id),
    title TEXT,
    author TEXT,
    producer TEXT,
    creation_date TIMESTAMP,
    modification_date TIMESTAMP,
    pdf_version TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT pdf_metadata_pdf_document_id_unique UNIQUE (pdf_document_id)
);
