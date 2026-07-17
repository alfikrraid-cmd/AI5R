# MWO-LTSA-040B — Engineering Document Acquisition

Status: APPROVED — implementation authorized
Type: Manufacturing Work Order (Acquisition Layer)
Epic: Engineering Knowledge Acquisition
Role: Implementation Engineer
Architecture: FROZEN — no new architecture, service, table pattern, or framework introduced
Foundation: v1.0 — LOCKED, unchanged by this MWO
Engineering Standard: v1.0 — LOCKED, unchanged by this MWO
Basis: `ENGINEERING/AI5R_ENGINEERING_STANDARD_v1.0.md`; `MWO-LTSA-030` (owner of `seal_engineering_document`, the table this MWO extends); `MWO-LTSA-040A` (owner of `knowledge_source_registry`, the table this MWO links to; its own Architecture Decision item 6 explicitly deferred physical linkage to this MWO)
Scope: `PRODUCTS/LTSA-BRAIN` only

---

## Executive Summary

This MWO physically connects the two objects MWO-LTSA-040A left logically related: `knowledge_source_registry` and `seal_engineering_document`. It also broadens the Engineering Document object with acquisition-layer metadata (document number, issue date, manufacturer, language, description, file name/format, page count) and extends its supported type set from 4 to 7 values. It performs no OCR, parsing, extraction, or AI reasoning — its responsibility ends at registration, normalization, and relationship creation, per its own Objective section.

---

## WP-000 — Design Decisions (derived directly from MWO-LTSA-040B's text; no separate Architecture Decision message was required, but every call below is cited to the specific line it comes from, per Engineering Standard v1.0 §7 Evidence Standard)

1. **Extend `seal_engineering_document` in place; do not create a parallel table.** Basis: the MWO's own Architecture section says "Reuse Mechanical Seal Registry" and "Reuse BUILD-PACK"; its Deliverables list "Engineering Document Registry **Update**" (not "Manufacture") as a named item; and MWO-LTSA-040A's own Architecture Decision item 6 states physical linkage "will be introduced when Engineering Document Acquisition is implemented (MWO-LTSA-040B)" — i.e., this MWO was always intended to alter the table MWO-030 built, not duplicate it. Creating a second, parallel "Engineering Document" table would itself be the kind of duplication the Engineering Standard's Canonicalization Standard (§6) exists to prevent.
2. **`seal_code` (Mechanical Seal Code) stays required.** Basis: Business Purpose states plainly "Documents must be linked to Knowledge Source **and** Mechanical Seal" — both links, not one optional. No business rule loosens this for the 3 newly-added document types.
3. **`knowledge_source_id` is required at the workflow/validation layer, but added as a nullable column with an FK (not `NOT NULL`) at the database layer.** Basis: Business Rule "Every Engineering Document must originate from exactly one Knowledge Source" mandates it as a business requirement, enforced by Create's input validation (throws if absent) — matching how every other Create workflow in this product enforces required fields. Adding a `NOT NULL` *database* constraint via `ALTER TABLE ADD COLUMN` on a table that already exists is unsafe unless the table is provably empty or a default is supplied; since no live database has ever been bootstrapped in this repository (confirmed by every prior Completion Report's Runtime Verification section), this is currently a theoretical risk, not an observed one — but the migration is written defensively regardless, as standard practice for an `ALTER` against a canonical table, and is documented here rather than silently assumed safe.
4. **The table and build pack keep their existing names (`seal_engineering_document`, `BUILD-PACKS/BP-SEAL-ENGINEERING-DOCUMENT`).** Basis: the MWO's own Business Object is named "Engineering Document," matching the object MWO-030 already built; renaming it was not requested, and doing so unprompted would itself be a redesign, contradicted by "No redesign" (Constraints).
5. **The Update workflow is narrowed to permit only the `status` field.** Basis: Business Rule "Engineering Documents are immutable. New revisions must create new document records." `status` is a lifecycle marker (e.g. a superseded document being marked as such once a newer revision is registered), not part of a document's substantive identity (title, revision, file, document number) — the same category of field every other registry in this product treats as legitimately mutable independent of the record's core content. All other fields, including `description`, are treated as immutable post-creation under this reading, since the rule states immutability without carving out an exception for descriptive metadata.
6. **No existence-check node beyond the database's own foreign key is added for `knowledge_source_id` or `seal_code`.** Basis: this matches the precedent depth already established in MWO-LTSA-030's Pump Compatibility and Interchange Compatibility workflows, neither of which added an explicit "does the referenced row exist" lookup beyond the FK constraint itself — a real FK violation is allowed to surface as the error, consistent across this product.
7. **"Engineering Document Relationship" (Deliverables) is the `knowledge_source_id` FK plus the pre-existing `seal_code` FK — not a separate join table.** Both relationships are simple many-to-one references from a single row, not many-to-many; no junction table is needed or requested.

**Canonical Mapping Table (locked):**

| Business Object (MWO term) | Canonical Table | Status |
|---|---|---|
| Engineering Document | `public.seal_engineering_document` (`BUILD-PACKS/BP-SEAL-ENGINEERING-DOCUMENT`, MWO-030, extended by this MWO) | Altered — 9 new columns, extended `document_type` set, new FK |
| Knowledge Source (referenced) | `public.knowledge_source_registry` (MWO-040A) | Untouched — read-only reference by new FK |
| Mechanical Seal (referenced) | `public.seal_registry` (MWO-P-005) | Untouched — read-only reference by pre-existing FK |

---

## Objective

Manufacture the Engineering Document Acquisition layer: extend `seal_engineering_document` so every Engineering Document is linked to exactly one Knowledge Source and exactly one Mechanical Seal, supports 7 document types, carries acquisition-layer metadata, and is immutable except for its lifecycle `status`.

## Scope

- Alter `public.seal_engineering_document` in `PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql`: add `knowledge_source_id` (FK to `knowledge_source_registry`), `document_number`, `issue_date`, `manufacturer`, `language`, `description`, `file_name`, `file_format`, `page_count`; extend `document_type`'s `CHECK` to 7 values; add a `page_count` non-negative `CHECK`.
- Update `BUILD-PACKS/BP-SEAL-ENGINEERING-DOCUMENT`: DATABASE (updated `001_create_table.sql` reflecting final shape, new idempotent `004_alter_add_acquisition_fields.sql`, updated seed/indexes), SCHEMAS, the Create and Update workflows, TEST scripts, README.
- Documentation-only, additive update to `product.manifest.json`.
- Structural validation and a Completion Report.

## Out of Scope

- **OCR, PDF parsing, image analysis, AI, Recommendation.** Every new field is caller-supplied metadata.
- **`ENGINEERING/RUNTIME/`.** No Runtime change.
- **`knowledge_source_registry`.** Read-only reference; no file in `BUILD-PACKS/BP-KNOWLEDGE-SOURCE` is modified.
- **Detail/List workflows.** Both already `SELECT *`/return the full row; no code change is needed for them to surface the new columns.
- **A Delete workflow.** None existed before this MWO and none is added — consistent with immutability.
- **n8n-level execution.** Structural validation only, same standing reason as every prior MWO.

## Dependencies

- **MWO-LTSA-030** — `seal_engineering_document`, the table this MWO alters.
- **MWO-LTSA-040A** — `knowledge_source_registry`, the table this MWO's new FK references.
- **MWO-P-006 / RV-004** — `PRODUCTS/LTSA-BRAIN/VERIFICATION/` test infrastructure, reused by every updated `TEST/*.sh` script.

## Constraints

- Architecture frozen; Foundation v1.0 and Engineering Standard v1.0 locked and unmodified.
- No new table, service, or credential mechanism.
- `document_code` remains the immutable primary key (unchanged from MWO-030).
- Every schema change is written idempotently (`ADD COLUMN IF NOT EXISTS`, `DROP CONSTRAINT IF EXISTS` before re-adding).

### Execution Rules

1. WP-001 through WP-003 execute as a single batch (design decisions in WP-000 stood in for a separate architecture-approval gate, per Evidence Standard citation above).
2. Structural Validation (WP-004) covers the full batch.
3. One Completion Report after the batch.
4. Nothing committed or pushed without separate, explicit approval.

---

## WP-001 — Schema Alteration

**Scope:** `CANONICAL_SCHEMA.sql`'s `seal_engineering_document` block updated to its final shape (for fresh bootstraps) plus explicit idempotent `ALTER TABLE` statements immediately after (for databases that already have the MWO-030 shape) — both converge to the same end state. Mirrored in `BUILD-PACKS/BP-SEAL-ENGINEERING-DOCUMENT/DATABASE/001_create_table.sql` (updated) and a new `004_alter_add_acquisition_fields.sql` (the standalone, idempotent upgrade path).

**Acceptance Criteria:** Every new column nullable except where the business object requires it structurally (none besides the pre-existing `seal_code`/`document_type`/`title`); `document_type` CHECK covers all 7 values; `page_count` CHECK rejects negative values; new FK references `knowledge_source_registry(knowledge_source_id)`; nothing about `document_code`, `seal_code`, `title`, or the `seal_registry` FK is altered.

## WP-002 — Build Pack Update

**Scope:** `BUILD-PACKS/BP-SEAL-ENGINEERING-DOCUMENT` updated: Create workflow accepts and validates the new fields (extended `document_type` enum, non-negative `page_count`, required `knowledge_source_id`); Update workflow's updatable-field list narrowed to `status` only; both schema files gain the new properties; `TEST/` scripts updated to fixture a `knowledge_source_registry` row, exercise the extended type set, and verify Update's narrowed scope; README updated.

## WP-003 — Manifest Documentation

**Scope:** `product.manifest.json`'s `seal_engineering_document` and `knowledge_source_registry` `implementation_status` entries updated additively to record this MWO's linkage.

## WP-004 — Structural Validation & Completion Report

**Scope:** `bash -n` on every changed `.sh` file; JSON-parse validation on every changed `.json` file; `git status`/`git diff` confirmation of exact scope; a real (bounded, no-guessed-credential) database connection attempt, reported honestly; `ENGINEERING/MWO/MWO-LTSA-040B-Completion-Report.md`.

---

## Deliverables

- `DATABASE/CANONICAL_SCHEMA.sql` — `seal_engineering_document` altered (WP-001)
- `BUILD-PACKS/BP-SEAL-ENGINEERING-DOCUMENT/*` — updated DATABASE/SCHEMAS/WORKFLOWS/TEST/README (WP-002)
- `product.manifest.json` — updated `implementation_status` entries (WP-003)
- `ENGINEERING/MWO/MWO-LTSA-040B-Completion-Report.md` (WP-004)
- No change to `knowledge_source_registry`, `seal_registry`, or `ENGINEERING/RUNTIME/`.

## Acceptance Criteria

- Every Engineering Document created after this MWO carries a `knowledge_source_id` (enforced at the workflow layer) and a `seal_code` (enforced at both layers, unchanged from MWO-030).
- 7 document types accepted; the 3 new ones (`MAINTENANCE_MANUAL`, `SERVICE_BULLETIN`, `ENGINEERING_SPECIFICATION`) are rejected before this MWO and accepted after, verified by test.
- Update can change `status` and nothing else — verified by test.
- Structural Validation passes for every changed file; Runtime Verification's standing blocker is stated, not hidden.

## Definition of Done

- WP-001–WP-003 complete, no out-of-scope file touched.
- WP-004's Structural Validation stated PASS/WARNING/BLOCKER; Completion Report exists.
- Nothing committed or pushed without separate, explicit approval.

---

This document, together with the schema alteration and updated build pack, is being produced per the Chief Architect's "Wait for approval before implementation" instruction having been satisfied by the MWO's own APPROVED status and unambiguous text (WP-000 above cites the specific resolving language for each design call). Commit and push remain separate, later approvals.
