CREATE INDEX IF NOT EXISTS idx_worksheet_table_worksheet_table_id
ON public.worksheet_table (worksheet_table_id);

CREATE INDEX IF NOT EXISTS idx_worksheet_table_worksheet_id
ON public.worksheet_table (worksheet_id);
