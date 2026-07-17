# MWO-LTSA-040E — Engineering Media Acquisition

Status: WP-000 DRAFTED — awaiting separate, explicit approval before implementation (per the original work order's own closing instruction: "Wait for approval before implementation")
Type: Manufacturing Work Order (Acquisition Layer)
Epic: Engineering Knowledge Acquisition
Role: Implementation Engineer
Architecture: FROZEN — no new architecture, service, table pattern, or framework introduced
Foundation: v1.0 — LOCKED, unchanged by this MWO
Engineering Standard: v1.0 — LOCKED, unchanged by this MWO
Basis: `ENGINEERING/AI5R_ENGINEERING_STANDARD_v1.0.md`; `MWO-LTSA-040A` (`knowledge_source_registry`, the table every Engineering Media originates from); `MWO-LTSA-040D` (the four-object acquisition-layer shape — Document/Metadata/Classification/Acquisition Job — this MWO clones directly, table-for-table); `MWO-LTSA-040B` (`seal_engineering_document`, source of the reused *pattern*, not a physical link); `BUILD-PACKS/BP-SEAL`, `BP-PDF-ACQUISITION-JOB` (canonical CRUD and job-log shapes)
Scope: `PRODUCTS/LTSA-BRAIN` only

---

## Executive Summary

This MWO manufactures the Engineering Media Acquisition layer: four generic, media-type-agnostic tracking objects (Engineering Media, Media Metadata, Media Classification, Media Acquisition Job) that record how an engineering media asset (photo, video, audio, thermal/infrared image, inspection image, CCTV or drone recording, or other engineering media) was registered, described, classified, and validated against a Knowledge Source — without performing image recognition, object detection, OCR, speech recognition, video analysis, or any other AI reasoning. It does not alter `seal_engineering_document` or `pdf_document`, and requires no Mechanical Seal or Engineering Document link. The original media file is never modified; a successful acquisition produces a registered, classified Engineering Media asset "ready for future analysis" (Future Dependencies: MWO-LTSA-050 through 053), not analyzed knowledge.

---

## WP-000 — Design Decisions for Under-Specified Attributes (cited, per Engineering Standard v1.0 §7 Evidence Standard)

**Architecture call: manufacture four new tables, paralleling MWO-LTSA-040D's shape; do not extend `seal_engineering_document` or `pdf_document`.**
Basis: the original work order's Architecture section says "Reuse ... Engineering Document Registry (MWO-LTSA-040B)," but its own Business Purpose states only "Engineering media must become registered engineering assets ... ready for future analysis" — no Mechanical Seal or Engineering Document linkage requirement. Its own Deliverables name four new registries explicitly ("Engineering Media Registry," "Media Metadata Registry," "Media Classification Registry," "Media Acquisition Job Registry"), not an "Engineering Document Registry Update" the way MWO-040B's own work order did. Read together, "Reuse Engineering Document Registry" means reuse the *pattern* it (and MWO-040D, which reused it the same way) established — not literal table reuse. This is the identical reading MWO-LTSA-040D's own WP-000 applied to the same phrase, one MWO earlier in this same roadmap.
Direct corroborating evidence: MWO-LTSA-040A's own approved Architecture Decision (WP-000, item 10) lays out the roadmap this MWO belongs to — "040B connects Engineering Documents, 040C connects Excel Acquisition, 040D connects PDF Acquisition, 040E connects Engineering Media, 040F connects Video Acquisition." Each entry is its own distinct connection off `knowledge_source_registry`, not a shared table — 040C built `workbook`/`worksheet`, 040D built `pdf_document`, and this MWO ("Engineering Media") is the same kind of entry, not a retrofit of 040B or 040D.

1. **`engineering_media.knowledge_source_id` is `NOT NULL`.** Basis: Business Rule "Every Engineering Media must originate from exactly one Knowledge Source" is unconditional, and `engineering_media` is a brand-new table with no pre-existing rows — the same reasoning MWO-040D's design decision 1 applied to `pdf_document.knowledge_source_id`, and MWO-040C applied to `workbook.knowledge_source_id`.
2. **`media_type` is a `CHECK`-constrained 9-value closed set** (`PHOTO`, `VIDEO`, `AUDIO`, `THERMAL_IMAGE`, `INFRARED_IMAGE`, `INSPECTION_IMAGE`, `CCTV_RECORDING`, `DRONE_RECORDING`, `OTHER`). Basis: the work order's Objective names nine media kinds including "Other engineering media," while its separate "Supported Media Types" section lists only the first eight without repeating "Other." Unlike MWO-040C's "Supported Workbook Types" (treated as an exhaustive closed set because no items were named outside it elsewhere in that work order), this work order names "Other engineering media" explicitly, twice, in both its Objective and its Supported Media Types intro paragraph — so `OTHER` is included as a ninth allow-list value rather than silently dropped. Flagged here as the one place this MWO's closed set is not a literal transcription of a single section, per Evidence Standard practice.
3. **No conflict with `knowledge_source_registry.media_type`.** Basis: that pre-existing column (MWO-040A, `public.knowledge_source_registry`) is an unconstrained `TEXT` field on the Knowledge Source table itself, describing the source record generically. `engineering_media.media_type` (this MWO) is a new, `CHECK`-constrained column on a new, separate table describing the Engineering Media asset specifically. The two are unrelated columns on unrelated tables; neither is altered or referenced by the other, the same way MWO-040A's WP-000 explicitly resolved its own naming-collision question with `AI5R-SDK/KNOWLEDGE`.
4. **`media_metadata` is Create/List/Detail only, one row per `engineering_media` (`UNIQUE` on `engineering_media_id`), no Update/Delete.** Basis: Resolution/Duration/Width/Height/Frame Rate/Audio Channels/GPS Location/Camera Device are container-level technical properties of one media file, recorded once at acquisition time — the same immutability class and one-to-one shape as `pdf_metadata` (MWO-040D, design decision 8), not a repeatable, many-rows-per-parent object like `media_classification`.
5. **`media_classification` reuses the same 9-value `media_type` closed set for `classification_type`, is Create/List/Detail only, no Update, and allows multiple rows per `engineering_media`.** Basis: no separate classification taxonomy is named anywhere in the work order — the only closed set given is "Supported Media Types" — matching MWO-040D's identical treatment of `document_classification.classification_type` reusing `pdf_document.document_type`. "Media classification must be repeatable" (Business Rule) is satisfied by multiple classification rows, not by mutating one row's `status`/`confidence` — the same reasoning applied to `document_classification` (040D) and `acquisition_job` (040C).
6. **`engineering_media.status` and `media_classification.status` are unconstrained `TEXT`, no `CHECK`.** Basis: no status values are enumerated anywhere in the work order (unlike `media_acquisition_job.status`, addressed below). Same precedent as `pdf_document.status` and `document_classification.status` (040D), both left unconstrained for the identical reason.
7. **`media_acquisition_job.status` is a 4-value `CHECK` set: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`.** Basis: adapted from `pdf_acquisition_job.status` (040D), itself adapted from `acquisition_job.status` (040C). `COMPLETED` (not `READY_FOR_MANUFACTURING`) is used because this work order's own Out of Scope explicitly excludes "Engineering Object Manufacturing"; its Success Criteria instead says media can be "registered, classified, validated, tracked, and linked," which `COMPLETED` describes without implying a manufacturing step this MWO does not perform — identical reasoning to MWO-040D's design decision 10.
8. **`media_acquisition_job.validation_errors` is unconstrained `TEXT`.** Basis: named verbatim as a `Media Acquisition Job` attribute in the work order's own Business Objects section; direct precedent, `pdf_acquisition_job.validation_errors` (040D) / `acquisition_job.error_summary` (040C).
9. **`gps_location` and `camera_device` (on `media_metadata`) are nullable `TEXT`.** Basis: these are the only two Media Metadata attributes the work order itself marks "(optional)" — no structured lat/long or device-registry schema is given, so both are kept as free-form text, the same "leave ungoverned dimension as free text" choice MWO-040C made for `mapping_profile.customer`.
10. **`resolution` is `TEXT`; `width`/`height`/`audio_channels` are `INTEGER`; `duration` and `frame_rate` are `NUMERIC`.** Basis: Resolution is named as its own attribute distinct from Width/Height (e.g., a descriptive label like "4K" alongside structured pixel dimensions), so it is kept as free text rather than collapsed into Width/Height. Width/Height/Audio Channels are discrete counts, matching the `INTEGER` precedent of `worksheet.row_count`/`column_count` (040C). Duration and Frame Rate are fractional measurements with no fixed unit stated, matching the `NUMERIC` precedent of `knowledge_source_registry.confidence_level` and `document_classification.confidence`.
11. **Column ID naming (`media_metadata_id`, `media_classification_id`, `media_acquisition_job_id`) follows the `pdf_metadata_id`/`document_classification_id`/`pdf_acquisition_job_id` prefix convention (040D)**, itself following `knowledge_source_id`/`workbook_id` (040A/040C) — a table-name-prefixed primary key, not the work order's own shorter literal labels ("Metadata ID," "Classification ID," "Acquisition Job ID").
12. **CRUD policy per object:**
    - `engineering_media`: Create/List/Detail only. Basis: Business Rule "Original media must never be modified" — identical wording and immutability class to `pdf_document` (040D) and `workbook` (040C).
    - `media_metadata`: Create/List/Detail only (design decision 4).
    - `media_classification`: Create/List/Detail only, no Update (design decision 5).
    - `media_acquisition_job`: Create/List/Detail/Update, no Delete. Basis: identical shape and reasoning to `pdf_acquisition_job` (040D) / `acquisition_job` (040C) — `started_at`/`finished_at`/`status`/`validation_errors` legitimately progress over a job's lifecycle; "acquisition must be repeatable" is satisfied by multiple job rows against the same Engineering Media, not by mutating one row.

**Canonical Mapping Table (locked):**

| Business Object | Canonical Table | CRUD |
|---|---|---|
| Engineering Media | `public.engineering_media` (new) | Create/List/Detail |
| Media Metadata | `public.media_metadata` (new) | Create/List/Detail |
| Media Classification | `public.media_classification` (new) | Create/List/Detail |
| Media Acquisition Job | `public.media_acquisition_job` (new) | Create/List/Detail/Update |
| Knowledge Source (referenced) | `public.knowledge_source_registry` (MWO-040A) | Untouched |
| Engineering Document (pattern reused, not altered) | `public.seal_engineering_document` (MWO-040B) | Untouched |
| PDF Document family (structural precedent, not altered) | `public.pdf_document`, `pdf_metadata`, `document_classification`, `pdf_acquisition_job` (MWO-040D) | Untouched |

**Rejected scope:** extending `seal_engineering_document` or `pdf_document` with media-specific columns; any image recognition, object detection, OCR, speech recognition, video analysis, AI reasoning, recommendation, or engineering-object manufacturing (explicitly Out of Scope in the original work order).

---

## Objective

Manufacture the Engineering Media Acquisition layer as `BUILD-PACKS/BP-<NAME>` packs, additive to `DATABASE/CANONICAL_SCHEMA.sql`, cloning the proven four-object pattern of `BP-PDF-DOCUMENT`/`BP-PDF-METADATA`/`BP-DOCUMENT-CLASSIFICATION`/`BP-PDF-ACQUISITION-JOB` (040D).

## Scope

- Four new tables: `engineering_media`, `media_metadata`, `media_classification`, `media_acquisition_job`.
- Four new build packs: `BP-ENGINEERING-MEDIA`, `BP-MEDIA-METADATA`, `BP-MEDIA-CLASSIFICATION`, `BP-MEDIA-ACQUISITION-JOB`.
- Documentation-only, additive update to `product.manifest.json`.
- Structural validation and a Completion Report.

## Out of Scope

- AI reasoning, image recognition, object detection, OCR, speech recognition, recommendation, engineering analysis (per the original work order's own Out of Scope).
- Video analysis, audio analysis.
- Any write path into a canonical business-object table (`ltsa_pumps`, `seal_registry`, `seal_stock`, `seal_engineering_document`, `pdf_document`, etc.) or Runtime redesign.
- Any media-type-specific or customer-specific code — every closed-set validation is a generic allow-list (`CHECK` constraint), never a per-type branch.
- Actual media file parsing/byte handling — every workflow accepts already-extracted metadata (names, counts, hashes) as JSON input, the same convention as every other acquisition workflow in this product (040C/040D precedent).
- n8n-level execution — structural validation only, same standing reason as every prior MWO.

## Dependencies

- **MWO-LTSA-040A** — `knowledge_source_registry`, the table `engineering_media.knowledge_source_id` and `media_acquisition_job.knowledge_source_id` reference.
- **MWO-LTSA-040D** — direct structural precedent for the four-object acquisition-layer shape (Document/Metadata/Classification/Acquisition Job) this MWO clones table-for-table as Media/Metadata/Classification/Acquisition Job.
- **MWO-LTSA-040B** — `seal_engineering_document`, source of the reused pattern only (not a physical link).
- **MWO-P-006 / RV-004** — `PRODUCTS/LTSA-BRAIN/VERIFICATION/` test infrastructure.

## Constraints

- Architecture frozen; Foundation v1.0 and Engineering Standard v1.0 locked and unmodified.
- No new table pattern — every table follows `seal_registry`'s shape (TEXT PK, `created_at`/`updated_at TIMESTAMP DEFAULT NOW()`), extended with `CHECK` constraints for closed-set fields.
- Nothing generic-vs-specific is violated: every enum/allow-list is data, not a code branch.

### Execution Rules

1. **This document (WP-000) is submitted for approval. It does not itself authorize implementation.** Per the original work order's explicit closing instruction ("Wait for approval before implementation") and per explicit direction accompanying this MWO, WP-001 onward (schema + 4 build packs + manifest) do not execute until separate, explicit approval is given. No schema is written and no `BUILD-PACKS/` directory is created as part of producing this document.
2. Once approved, WP-001 through WP-006 (schema + 4 build packs + manifest) execute as a single batch.
3. Structural Validation (WP-007) covers the full batch.
4. One Completion Report after the batch.
5. Nothing committed or pushed without separate, explicit approval (in addition to, and after, the implementation approval in Rule 1).

---

## WP-001 — Canonical Schema

Four new tables, additive to `CANONICAL_SCHEMA.sql`, per the Canonical Mapping Table above. **Not executed by this document.**

## WP-002 through WP-005 — Build Packs

One work package per build pack (`BP-ENGINEERING-MEDIA`, `BP-MEDIA-METADATA`, `BP-MEDIA-CLASSIFICATION`, `BP-MEDIA-ACQUISITION-JOB`), each DATABASE + SCHEMAS + WORKFLOWS (per its CRUD policy above) + TEST + README, cloning `BP-PDF-DOCUMENT`'s and `BP-PDF-ACQUISITION-JOB`'s pattern. **Not executed by this document.**

## WP-006 — Manifest Documentation

Additive `implementation_status` entries for all four new modules. **Not executed by this document.**

## WP-007 — Structural Validation & Completion Report

`bash -n` on every new `.sh` file; JSON-parse validation on every new `.json` file; `git status` scope confirmation; a real (bounded, no-guessed-credential) database connection attempt, reported honestly; `ENGINEERING/MWO/MWO-LTSA-040E-Completion-Report.md`. **Not executed by this document.**

---

## Deliverables

- `DATABASE/CANONICAL_SCHEMA.sql` — 4 new tables (WP-001, pending approval)
- `BUILD-PACKS/BP-ENGINEERING-MEDIA`, `BP-MEDIA-METADATA`, `BP-MEDIA-CLASSIFICATION`, `BP-MEDIA-ACQUISITION-JOB` (WP-002–WP-005, pending approval)
- `product.manifest.json` — additive entries (WP-006, pending approval)
- `ENGINEERING/MWO/MWO-LTSA-040E-Completion-Report.md` (WP-007, pending approval)
- No change to any canonical business-object table, `seal_engineering_document`, `pdf_document`, `knowledge_source_registry`, or `ENGINEERING/RUNTIME/`.

## Acceptance Criteria

- No canonical business-object table (`ltsa_pumps`, `seal_registry`, `seal_stock`, `seal_pump_compatibility`, `seal_interchange_compatibility`, `seal_engineering_document`, `customer_registry`, `asset_registry`, `soot_blower_registry`, `work_order`, `maintenance_history`, `workbook`, `worksheet`, `worksheet_table`, `mapping_profile`, `column_mapping`, `acquisition_job`, `pdf_document`, `pdf_metadata`, `document_classification`, `pdf_acquisition_job`) is touched, once implemented.
- Every closed-set validation (`media_type`, `classification_type`, `media_acquisition_job.status`) is a generic allow-list, never a per-type code branch.
- `engineering_media`, `media_metadata`, `media_classification` have no Update or Delete workflow.
- Structural Validation passes for every new file; Runtime Verification's standing blocker is stated, not hidden.

## Definition of Done

- WP-000 (this document) complete and submitted for approval.
- WP-001–WP-006 remain unexecuted until separate, explicit approval is given.
- WP-007's Structural Validation, once run, stated PASS/WARNING/BLOCKER; Completion Report produced at that time.
- Nothing committed or pushed without separate, explicit approval.

---

This document is WP-000 only — the architecture and design-decision record for MWO-LTSA-040E. Per the original work order's own instruction and explicit accompanying direction, implementation (WP-001 onward: schema + build packs) awaits separate, explicit approval. MWO-LTSA-049 (Universal Engineering Manufacturing Engine) is a distinct, independent future work order and is neither merged with nor referenced as implementation basis for this MWO.
