# Build Pack

Product: LTSA-BRAIN
Module: ACQUISITION-JOB
Table: acquisition_job
Primary Key: acquisition_job_id
Manufactured under: MWO-LTSA-040C (Universal Tabular Data Acquisition)

Part of the Universal Acquisition Infrastructure — the job-log record of
one acquisition attempt against one Workbook (`workbook_id`, FK to
`BUILD-PACKS/BP-WORKBOOK`'s `workbook`) using one Mapping Profile
(`mapping_profile_id`, FK to `BUILD-PACKS/BP-MAPPING-PROFILE`'s
`mapping_profile`). Attributes were not specified by the original work
order — this is a minimal, generic job-log shape reflecting the pipeline's
stated stages (registration → mapping → normalization → validation)
without asserting manufacturing occurred: a `READY_FOR_MANUFACTURING` job
has not written any business object (Architecture Decision item 9).

`status` (`PENDING`/`IN_PROGRESS`/`READY_FOR_MANUFACTURING`/`FAILED`) is
the one part of this table's design most likely to need revision once a
future MWO builds a real acquisition workflow against it — flagged here,
not hidden.

Create/List/Detail/Update — no Delete. "Acquisition must be repeatable"
(Business Rule) is satisfied by allowing multiple job rows against the
same (workbook_id, mapping_profile_id) pair, not by deleting and retrying
one row.

This build pack does not parse Excel files or write to any canonical
business-object table — per Architecture Decision items 1/5/6/9/10, a
completed Acquisition Job records that a workbook is validated, mapped,
and ready for manufacturing; the manufacturing step itself is deferred to
future MWOs.
