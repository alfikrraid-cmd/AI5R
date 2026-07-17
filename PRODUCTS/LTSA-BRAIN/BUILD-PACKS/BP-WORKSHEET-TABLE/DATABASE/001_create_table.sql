CREATE TABLE IF NOT EXISTS public.worksheet_table (
    worksheet_table_id TEXT PRIMARY KEY NOT NULL,
    worksheet_id TEXT NOT NULL REFERENCES public.worksheet(worksheet_id),
    table_name TEXT,
    row_count INTEGER,
    column_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT worksheet_table_row_count_check CHECK (row_count IS NULL OR row_count >= 0),
    CONSTRAINT worksheet_table_column_count_check CHECK (column_count IS NULL OR column_count >= 0)
);
