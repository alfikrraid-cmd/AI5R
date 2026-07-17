# Build Pack

Product: LTSA-BRAIN
Module: MEDIA-METADATA
Table: media_metadata
Primary Key: media_metadata_id (immutable)
Manufactured under: MWO-LTSA-040E (Engineering Media Acquisition)

Records one Engineering Media asset's own container-level technical
properties (`resolution`, `duration`, `width`, `height`, `frame_rate`,
`audio_channels`, `gps_location`, `camera_device`) — not analyzed content.
A single media file has exactly one set of these properties at a time, so
`engineering_media_id` carries a `UNIQUE` constraint
(`media_metadata_engineering_media_id_unique`) — one row per
`engineering_media` (FK to `BUILD-PACKS/BP-ENGINEERING-MEDIA`'s
`engineering_media`), the same one-to-one shape as `pdf_metadata`
(MWO-LTSA-040D). `resolution` is free text (e.g. "4K"), distinct from the
structured `width`/`height` pixel dimensions; `gps_location`/
`camera_device` are the only two attributes the original work order marks
optional, kept as free text.

Create/List/Detail only, no Update or Delete — recorded once at
acquisition time as a structural fact about the source file, the same
immutability class as `pdf_metadata` (MWO-LTSA-040D) and `worksheet`
(MWO-LTSA-040C).

This build pack does not parse media files or perform any technical
analysis — every field is caller-supplied metadata, the same convention as
every other acquisition workflow in this product.
