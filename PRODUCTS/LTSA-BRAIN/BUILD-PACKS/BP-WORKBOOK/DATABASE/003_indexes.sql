CREATE INDEX IF NOT EXISTS idx_workbook_workbook_id
ON public.workbook (workbook_id);

CREATE INDEX IF NOT EXISTS idx_workbook_knowledge_source_id
ON public.workbook (knowledge_source_id);

CREATE INDEX IF NOT EXISTS idx_workbook_workbook_type
ON public.workbook (workbook_type);
