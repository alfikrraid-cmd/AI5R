# Build Pack

Product: LTSA-BRAIN
Module: MEDIA-ACQUISITION-JOB
Table: media_acquisition_job
Primary Key: media_acquisition_job_id
Manufactured under: MWO-LTSA-040E (Engineering Media Acquisition)

The job-log record of one acquisition attempt against one Engineering
Media asset (`engineering_media_id`, FK to
`BUILD-PACKS/BP-ENGINEERING-MEDIA`'s `engineering_media`) originating from
one Knowledge Source (`knowledge_source_id`, FK to
`BUILD-PACKS/BP-KNOWLEDGE-SOURCE`'s `knowledge_source_registry`) — both
FKs named attributes of "Media Acquisition Job" in the original work
order's own Business Objects section.

`status` (`PENDING`/`IN_PROGRESS`/`COMPLETED`/`FAILED`) is adapted from
`pdf_acquisition_job.status` (MWO-LTSA-040D), itself adapted from
`acquisition_job.status` (MWO-LTSA-040C). `COMPLETED` (not
`READY_FOR_MANUFACTURING`) is used because this MWO's own Out of Scope
excludes "Engineering Object Manufacturing."

Create/List/Detail/Update — no Delete. "Acquisition must be repeatable"
(Business Rule) is satisfied by allowing multiple job rows against the
same (`knowledge_source_id`, `engineering_media_id`) pair, not by deleting
and retrying one row. Update permits only `status`, `finished_at`,
`validation_errors` — `knowledge_source_id`, `engineering_media_id`, and
`started_at` are fixed at Create time.

This build pack does not parse media files, perform image/video/audio
analysis, or write to any canonical business-object table — a `COMPLETED`
job records that a media asset is registered, classified, and validated;
analysis of any kind is deferred to future MWOs (MWO-LTSA-050 through
053).
