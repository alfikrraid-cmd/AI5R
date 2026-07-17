# MWO-LTSA-040D — Engineering PDF Acquisition

Status: WP-000 DRAFTED — awaiting separate, explicit approval before implementation (per the original work order's own closing instruction: "Wait for approval before implementation")
Type: Manufacturing Work Order (Acquisition Layer)
Epic: Engineering Knowledge Acquisition
Role: Implementation Engineer
Architecture: FROZEN — no new architecture, service, table pattern, or framework introduced
Foundation: v1.0 — LOCKED, unchanged by this MWO
Engineering Standard: v1.0 — LOCKED, unchanged by this MWO
Basis: `ENGINEERING/AI5R_ENGINEERING_STANDARD_v1.0.md`; `MWO-LTSA-040A` (`knowledge_source_registry`, the table every PDF Document originates from); `MWO-LTSA-040B` (`seal_engineering_document`, the Engineering Document Registry pattern this MWO reuses the shape of); `BUILD-PACKS/BP-SEAL`, `BP-ACQUISITION-JOB` (canonical CRUD and job-log shapes)
Scope: `PRODUCTS/LTSA-BRAIN` only

---

## Executive Summary

This MWO manufactures the Engineering PDF Acquisition layer: four generic, PDF-type-agnostic tracking objects (PDF Document, PDF Metadata, Document Classification, PDF Acquisition Job) that record how an engineering PDF was registered, described, classified, and validated against a Knowledge Source — without performing OCR, text/table/image extraction, or AI reasoning. It does not alter `seal_engineering_document` and does not require a Mechanical Seal link, distinguishing it from MWO-LTSA-040B. The original PDF file is never modified; a successful acquisition produces a registered, classified PDF Document "ready for future extraction" (Future Dependencies: MWO-LTSA-046 through 049), not extracted knowledge.

---

## WP-000 — Design Decisions for Under-Specified Attributes (cited, per Engineering Standard v1.0 §7 Evidence Standard)

**Architecture call: manufacture four new tables; do not extend `seal_engineering_document`.**
Basis: the original work order's Architecture section says "Reuse ... Engineering Document Registry (MWO-LTSA-040B)," but its own Business Purpose states only "must become registered engineering assets ... linked to Knowledge Source" — no Mechanical Seal linkage requirement, unlike MWO-040B's Business Purpose ("linked to Knowledge Source **and** Mechanical Seal"). `seal_engineering_document.seal_code` is `NOT NULL`; forcing every PDF through that table would require inventing a seal linkage this work order never asks for. Its own Deliverables also name new registries ("PDF Registry," "PDF Metadata Registry," "Document Classification Registry," "PDF Acquisition Job Registry"), not an "Engineering Document Registry Update" the way MWO-040B explicitly did. Read together, "Reuse Engineering Document Registry" means reuse the *pattern* it established (document-type `CHECK` set, file/page metadata shape, immutability), the same way MWO-040C read "Reuse existing LTSA modules" as pattern-reuse, not literal table reuse.
Direct corroborating evidence: MWO-LTSA-040A's own WP-000 (item 10, its approved Architecture Decision) already lays out the roadmap this MWO belongs to — "040B connects Engineering Documents, 040C connects Excel Acquisition, 040D connects PDF Acquisition, 040E connects Engineering Media, 040F connects Video Acquisition." Each entry names a distinct connection, not a shared table; 040C ("Excel Acquisition") built its own `workbook`/`worksheet` family rather than extending `seal_engineering_document`, and this MWO ("PDF Acquisition") is the same kind of entry in the same list — a new, parallel connection point off `knowledge_source_registry`, not a retrofit of 040B's table.

1. **`pdf_document.knowledge_source_id` is `NOT NULL` (unlike `seal_engineering_document`'s nullable FK of the same name).** Basis: Business Rule "Every PDF must originate from exactly one Knowledge Source" is unconditional, and — unlike MWO-040B, which added the FK to an already-existing, possibly-populated table — `pdf_document` is a brand-new table with no pre-existing rows, so a `NOT NULL` FK from creation carries none of the migration risk MWO-040B's WP-000 flagged. Matches the precedent set by `workbook.knowledge_source_id` (MWO-040C), the other brand-new table with the identical business-rule wording.
2. **`document_type` is a `CHECK`-constrained 11-value closed set** (`INSTALLATION_REPORT`, `SERVICE_REPORT`, `INSPECTION_REPORT`, `FAILURE_REPORT`, `JOHN_CRANE_DRAWING`, `DATASHEET`, `MAINTENANCE_MANUAL`, `SERVICE_BULLETIN`, `ENGINEERING_SPECIFICATION`, `CALIBRATION_REPORT`, `HYDROTEST_REPORT`), taken verbatim from the "Supported PDF Types" section. Generic allow-list, never a per-type parser — same treatment as `workbook_type` (040C) and `knowledge_source_registry.source_type` (040A).
3. **`pdf_document.status` is unconstrained `TEXT`, no `CHECK`.** Basis: no status values are enumerated anywhere in the work order (unlike `verification_status` in 040A, which names its 4 values explicitly). The nearest sibling object, `seal_engineering_document.status`, was left as unconstrained `TEXT` for the same reason in MWO-040B. Inventing an enum with no textual basis would be the kind of undocumented design choice the Evidence Standard exists to prevent.
4. **`file_hash`/`file_size` are kept on `pdf_document` despite already existing on `knowledge_source_registry`.** Basis: both fields are explicitly named as `PDF Document` attributes in the work order's own Business Objects section, not left to inference. Flagged as a known, accepted redundancy (the PDF's own file identity vs. the Knowledge Source's) rather than silently deduplicated against a table this MWO does not own.
5. **`document_classification` is a separate table (not a mutable field on `pdf_document`), keyed by its own `classification_id` and FK'd to `pdf_document_id`.** Basis: Business Rule "PDF Classification must be repeatable." A single `document_type`-like field on `pdf_document` cannot represent multiple repeatable classification attempts with independent `confidence`/`status` per attempt; a child table can, one row per classification run — the same reasoning MWO-040C used for `acquisition_job` ("repeatable... by allowing multiple Job rows, not by mutating one row").
6. **`document_classification.classification_type` reuses the same 11-value `document_type` closed set**, not a separate vocabulary. Basis: no distinct classification taxonomy is named anywhere in the work order; the only closed set given is "Supported PDF Types," and classification's job is to assign a PDF to one of those types.
7. **`document_classification.confidence` is `NUMERIC`, `classification_version` is `TEXT`, `status` is unconstrained `TEXT`.** Basis: `confidence` mirrors `knowledge_source_registry.confidence_level NUMERIC` (040A), the only prior precedent for a confidence-shaped field in this product. `classification_version` follows the loose-typing precedent of `workbook_version TEXT` (040C) since no version scheme is specified. `status` follows the same no-enumerated-values reasoning as design decision 3.
8. **`pdf_metadata` attributes (Title, Author, Producer, Creation Date, Modification Date, PDF Version) are Create/List/Detail only, one row per `pdf_document`, no Update/Delete.** Basis: these are standard PDF document-properties (analogous to file metadata, not body content) recorded once at acquisition time — distinct from the "No text extraction" rule, which concerns document *content*, not container-level properties. Treated as immutable, the same class as `worksheet` (040C): a structural fact about the source file, recorded once.
9. **CRUD policy per object:**
   - `pdf_document`: Create/List/Detail only. Basis: Business Rule "Original PDF must never be modified" — identical wording and identical immutability class to `workbook` (040C, design decision 6).
   - `pdf_metadata`: Create/List/Detail only (design decision 8).
   - `document_classification`: Create/List/Detail only, no Update. Basis: "repeatable" is satisfied by new rows (design decision 5), not by mutating a classification's `status`/`confidence` after the fact — no rule in the work order describes a confirm/reject lifecycle for an existing classification row.
   - `pdf_acquisition_job`: Create/List/Detail/Update, no Delete. Basis: identical shape and reasoning to `acquisition_job` (040C) — `started_at`/`finished_at`/`status`/`validation_errors` legitimately progress over a job's lifecycle; "must be repeatable" is satisfied by multiple job rows against the same PDF Document, not by mutating one row.
10. **`pdf_acquisition_job.status` is a 4-value `CHECK` set: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`.** Basis: adapted from `acquisition_job.status` (040C: `PENDING`, `IN_PROGRESS`, `READY_FOR_MANUFACTURING`, `FAILED`) — same job-log shape, but the terminal success label is changed from `READY_FOR_MANUFACTURING` to `COMPLETED` because this work order's own Out of Scope explicitly excludes "Engineering Object Manufacturing"; its Success Criteria instead says a PDF can be "registered, classified, validated, tracked, and linked," which `COMPLETED` describes without implying a manufacturing step this MWO does not perform. Flagged as the one label most likely to need revision once a real acquisition workflow runs against it, same caveat 040C raised for its own job-status set.
11. **`validation_errors` is unconstrained `TEXT`.** Basis: direct precedent, `acquisition_job.error_summary TEXT` (040C).

**Canonical Mapping Table (locked):**

| Business Object | Canonical Table | CRUD |
|---|---|---|
| PDF Document | `public.pdf_document` (new) | Create/List/Detail |
| PDF Metadata | `public.pdf_metadata` (new) | Create/List/Detail |
| Document Classification | `public.document_classification` (new) | Create/List/Detail |
| PDF Acquisition Job | `public.pdf_acquisition_job` (new) | Create/List/Detail/Update |
| Knowledge Source (referenced) | `public.knowledge_source_registry` (MWO-040A) | Untouched |
| Engineering Document (pattern reused, not altered) | `public.seal_engineering_document` (MWO-040B) | Untouched |

**Rejected scope:** extending `seal_engineering_document` with PDF-specific columns; any OCR, text/table/image extraction, AI reasoning, or engineering-object manufacturing (explicitly Out of Scope in the original work order).

---

## Objective

Manufacture the Engineering PDF Acquisition layer as `BUILD-PACKS/BP-<NAME>` packs, additive to `DATABASE/CANONICAL_SCHEMA.sql`, cloning the proven pattern of `BP-SEAL-ENGINEERING-DOCUMENT` (040B) and `BP-ACQUISITION-JOB` (040C).

## Scope

- Four new tables: `pdf_document`, `pdf_metadata`, `document_classification`, `pdf_acquisition_job`.
- Four new build packs: `BP-PDF-DOCUMENT`, `BP-PDF-METADATA`, `BP-DOCUMENT-CLASSIFICATION`, `BP-PDF-ACQUISITION-JOB`.
- Documentation-only, additive update to `product.manifest.json`.
- Structural validation and a Completion Report.

## Out of Scope

- OCR, AI reasoning, recommendation, engineering analysis, knowledge extraction (per the original work order's own Out of Scope).
- Text extraction, table extraction, image extraction.
- Any write path into a canonical business-object table (`ltsa_pumps`, `seal_registry`, `seal_stock`, `seal_engineering_document`, etc.) or Runtime redesign.
- Any PDF-type-specific or customer-specific code — every closed-set validation is a generic allow-list (`CHECK` constraint), never a per-type branch.
- Actual PDF file parsing/byte handling — every workflow accepts already-extracted metadata (names, counts, hashes) as JSON input, the same convention as every other acquisition workflow in this product (040C precedent).
- n8n-level execution — structural validation only, same standing reason as every prior MWO.

## Dependencies

- **MWO-LTSA-040A** — `knowledge_source_registry`, the table `pdf_document.knowledge_source_id` and `pdf_acquisition_job.knowledge_source_id` reference.
- **MWO-LTSA-040B** — `seal_engineering_document`, source of the reused pattern (document-type `CHECK`, file/page metadata shape).
- **MWO-P-006 / RV-004** — `PRODUCTS/LTSA-BRAIN/VERIFICATION/` test infrastructure.

## Constraints

- Architecture frozen; Foundation v1.0 and Engineering Standard v1.0 locked and unmodified.
- No new table pattern — every table follows `seal_registry`'s shape (TEXT PK, `created_at`/`updated_at TIMESTAMP DEFAULT NOW()`), extended with `CHECK` constraints for closed-set fields.
- Nothing generic-vs-specific is violated: every enum/allow-list is data, not a code branch.

### Execution Rules

1. **This document (WP-000) is submitted for approval. It does not itself authorize implementation.** Per the original work order's explicit closing instruction ("Wait for approval before implementation"), WP-001 onward (schema + 4 build packs + manifest) do not execute until separate, explicit approval is given — unlike MWO-040C, where WP-000 approval auto-authorized the full implementation batch.
2. Once approved, WP-001 through WP-006 (schema + 4 build packs + manifest) execute as a single batch.
3. Structural Validation (WP-007) covers the full batch.
4. One Completion Report after the batch.
5. Nothing committed or pushed without separate, explicit approval (in addition to, and after, the implementation approval in Rule 1).

---

## WP-001 — Canonical Schema

Four new tables, additive to `CANONICAL_SCHEMA.sql`, per the Canonical Mapping Table above.

## WP-002 through WP-005 — Build Packs

One work package per build pack (`BP-PDF-DOCUMENT`, `BP-PDF-METADATA`, `BP-DOCUMENT-CLASSIFICATION`, `BP-PDF-ACQUISITION-JOB`), each DATABASE + SCHEMAS + WORKFLOWS (per its CRUD policy above) + TEST + README, cloning `BP-SEAL-ENGINEERING-DOCUMENT`'s and `BP-ACQUISITION-JOB`'s pattern.

## WP-006 — Manifest Documentation

Additive `implementation_status` entries for all four new modules.

## WP-007 — Structural Validation & Completion Report

`bash -n` on every new `.sh` file; JSON-parse validation on every new `.json` file; `git status` scope confirmation; a real (bounded, no-guessed-credential) database connection attempt, reported honestly; `ENGINEERING/MWO/MWO-LTSA-040D-Completion-Report.md`.

---

## Deliverables

- `DATABASE/CANONICAL_SCHEMA.sql` — 4 new tables (WP-001)
- `BUILD-PACKS/BP-PDF-DOCUMENT`, `BP-PDF-METADATA`, `BP-DOCUMENT-CLASSIFICATION`, `BP-PDF-ACQUISITION-JOB` (WP-002–WP-005)
- `product.manifest.json` — additive entries (WP-006)
- `ENGINEERING/MWO/MWO-LTSA-040D-Completion-Report.md` (WP-007)
- No change to any canonical business-object table, `seal_engineering_document`, `knowledge_source_registry`, or `ENGINEERING/RUNTIME/`.

## Acceptance Criteria

- No canonical business-object table (`ltsa_pumps`, `seal_registry`, `seal_stock`, `seal_pump_compatibility`, `seal_interchange_compatibility`, `seal_engineering_document`, `customer_registry`, `asset_registry`, `soot_blower_registry`, `work_order`, `maintenance_history`, `workbook`, `worksheet`, `worksheet_table`, `mapping_profile`, `column_mapping`, `acquisition_job`) is touched.
- Every closed-set validation (`document_type`, `classification_type`, `pdf_acquisition_job.status`) is a generic allow-list, never a per-type code branch.
- `pdf_document`, `pdf_metadata`, `document_classification` have no Update or Delete workflow.
- Structural Validation passes for every new file; Runtime Verification's standing blocker is stated, not hidden.

## Definition of Done

- WP-001–WP-006 complete, no out-of-scope file touched.
- WP-007's Structural Validation stated PASS/WARNING/BLOCKER; Completion Report exists.
- Nothing committed or pushed without separate, explicit approval.

---

This document is WP-000 only — the architecture and design-decision record for MWO-LTSA-040D. Per the original work order's own instruction, implementation (WP-001 onward: schema + build packs) awaits separate, explicit approval.
