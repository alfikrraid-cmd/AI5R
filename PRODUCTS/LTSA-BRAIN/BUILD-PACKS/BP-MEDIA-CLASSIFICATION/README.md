# Build Pack

Product: LTSA-BRAIN
Module: MEDIA-CLASSIFICATION
Table: media_classification
Primary Key: media_classification_id (immutable)
Manufactured under: MWO-LTSA-040E (Engineering Media Acquisition)

Records one classification attempt against one Engineering Media asset
(FK to `BUILD-PACKS/BP-ENGINEERING-MEDIA`'s `engineering_media`).
`classification_type` reuses the same 9-value closed set as
`engineering_media.media_type` — no separate classification taxonomy is
named anywhere in the original work order; its job is to assign a media
asset to one of the Supported Media Types.

**Repeatable by design** — "Media classification must be repeatable"
(Business Rule) is satisfied by allowing multiple classification rows
against the same `engineering_media_id`, not by mutating one row (same
reasoning as `document_classification`, MWO-LTSA-040D, and
`acquisition_job`, MWO-LTSA-040C).

Create/List/Detail only, no Update or Delete — repeatability is achieved
via new rows, not by editing an existing classification's `status`/
`confidence` after the fact.

This build pack performs no image recognition, object detection, OCR,
speech recognition, video/audio analysis, or AI reasoning —
`classification_type`/`confidence`/`status` are caller-supplied, the same
convention as every other acquisition workflow in this product.
