CREATE TABLE IF NOT EXISTS public.worksheet (
    worksheet_id TEXT PRIMARY KEY NOT NULL,
    workbook_id TEXT NOT NULL REFERENCES public.workbook(workbook_id),
    worksheet_name TEXT NOT NULL,
    row_count INTEGER,
    column_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT worksheet_row_count_check CHECK (row_count IS NULL OR row_count >= 0),
    CONSTRAINT worksheet_column_count_check CHECK (column_count IS NULL OR column_count >= 0)
);
