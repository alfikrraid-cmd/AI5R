# Build Pack

Product: LTSA-BRAIN
Module: WORKSHEET
Table: worksheet
Primary Key: worksheet_id (immutable)
Manufactured under: MWO-LTSA-040C (Universal Tabular Data Acquisition)

Part of the Universal Acquisition Infrastructure. One Workbook may contain
multiple Worksheets (`workbook_id`, FK to `BUILD-PACKS/BP-WORKBOOK`'s
`workbook`). A structural fact about the source file, not business data —
no Update or Delete workflow exists for this table, matching Workbook's
own immutability. Only Create, List, Detail.
