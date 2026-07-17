# Build Pack

Product: LTSA-BRAIN
Module: WORKSHEET-TABLE
Table: worksheet_table
Primary Key: worksheet_table_id (immutable)
Manufactured under: MWO-LTSA-040C (Universal Tabular Data Acquisition)

Part of the Universal Acquisition Infrastructure. One Worksheet may
contain multiple Structured Tables (`worksheet_id`, FK to
`BUILD-PACKS/BP-WORKSHEET`'s `worksheet`); one Structured Table may
manufacture multiple Canonical Objects (a future capability — not built by
this MWO, see Architecture Decision items 1/5/6/10). Attributes were not
specified by the original work order; this table mirrors Worksheet's own
shape one level down (`table_name`/`row_count`/`column_count`). A
structural fact about the source file — no Update or Delete workflow
exists. Only Create, List, Detail.
