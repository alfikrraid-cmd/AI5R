# Build Pack

Product: LTSA-BRAIN
Module: ENGINEERING-MEDIA
Table: engineering_media
Primary Key: engineering_media_id (immutable)
Manufactured under: MWO-LTSA-040E (Engineering Media Acquisition)

The third canonical Acquisition Object, alongside Workbook (MWO-LTSA-040C)
and PDF (MWO-LTSA-040D), conforming to ADR-004 (Engineering Acquisition
Pattern). Registers an engineering media asset's identity, never its
content — no image recognition, object detection, OCR, speech
recognition, video/audio analysis, or AI reasoning. Every Engineering
Media must originate from exactly one Knowledge Source
(`knowledge_source_id`, FK to `BUILD-PACKS/BP-KNOWLEDGE-SOURCE`'s
`knowledge_source_registry`). `media_type` is a closed set of the 9
Supported Media Types, validated generically (an allow-list, never a
per-type parser).

`media_name`/`file_name`/`file_size`/`file_hash`/`status` complete this
table's shape as a table-for-table clone of `pdf_document` (MWO-LTSA-040D)
— these were not separately itemized in MWO-LTSA-040E's own WP-000 (which
resolved `knowledge_source_id`/`media_type`/`status` explicitly), so this
is flagged here, not silently assumed, per Evidence Standard practice.
Unlike `pdf_document`, no `page_count` analogue exists — Engineering
Media's technical dimensions (width/height/duration/frame_rate) belong on
`media_metadata` instead (WP-000 design decision 4), not on this table.

**Original media must never be modified** — no Update or Delete workflow
exists for this table. Only Create, List, Detail.

This build pack does not parse media files, extract content, or write to
any canonical business-object table — an Engineering Media registration
is metadata only. Classification is a separate, repeatable child object
(`BUILD-PACKS/BP-MEDIA-CLASSIFICATION`); analysis of any kind is deferred
to future MWOs (MWO-LTSA-050 through 053).
