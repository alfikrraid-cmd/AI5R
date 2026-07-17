# MWO-LTSA-040C-R1 — Workbook Acquisition Pattern Alignment

Status: WP-000 DRAFTED — awaiting separate, explicit approval before implementation (per Chief Architect's explicit instruction: "Do not implement the retrofit now. Only produce the retrofit MWO specification.")
Type: Manufacturing Work Order (Retrofit — Acquisition Layer)
Epic: Engineering Knowledge Acquisition
Role: Implementation Engineer
Architecture: FROZEN — no new architecture, service, table pattern, or framework introduced
Foundation: v1.0 — LOCKED, unchanged by this MWO
Engineering Standard: v1.0 — LOCKED, unchanged by this MWO
Basis: `ADR-004` (Engineering Acquisition Pattern — the governing decision this retrofit exists to satisfy); `MWO-LTSA-040C` (`workbook`, `worksheet`, `worksheet_table`, `mapping_profile`, `column_mapping`, `acquisition_job` — the tables this MWO retrofits); `MWO-LTSA-040D` (`pdf_document`/`pdf_metadata`/`document_classification`/`pdf_acquisition_job` — the four-stage shape this MWO clones table-for-table); `BUILD-PACKS/BP-PDF-METADATA`, `BP-DOCUMENT-CLASSIFICATION`, `BP-PDF-ACQUISITION-JOB` (structural precedent for the new/renamed tables)
Scope: `PRODUCTS/LTSA-BRAIN` only

---

## Executive Summary

ADR-004 (Engineering Acquisition Pattern) declares that every Acquisition Object must follow the shape Acquisition Object → Metadata → Classification → Acquisition Job, and names Workbook's target shape explicitly: `workbook` → Workbook Metadata → Workbook Classification → Workbook Acquisition Job. MWO-LTSA-040C, drafted before ADR-004 existed, does not conform: it has no `workbook_metadata` or `workbook_classification` table, and its `acquisition_job` table is shared between `workbook_id` and `mapping_profile_id` rather than being a dedicated, Workbook-scoped Acquisition Job. This MWO produces the retrofit specification only — per explicit instruction, it does not touch `MWO-LTSA-040C`'s existing implementation. Implementation awaits a separate, later approval, exactly as MWO-LTSA-040D's own WP-000 was gated before its Implementation Approval was granted.

---

## WP-000 — Design Decisions for Under-Specified Attributes (cited, per Engineering Standard v1.0 §7 Evidence Standard)

**Architecture call: add two new tables (`workbook_metadata`, `workbook_classification`); rename `acquisition_job` to `workbook_acquisition_job`, unchanged in shape except the name.**
Basis: ADR-004 §2 names the target shape as "Workbook Acquisition Job," not "Acquisition Job" — the existing name predates ADR-004 and was never scoped by MWO-LTSA-040C to be shared across Acquisition Object types (only `workbook_id` and `mapping_profile_id` FKs exist on it today; no other Acquisition Object type references it). A rename, not a redesign: no column, constraint, or FK target changes. This mirrors MWO-LTSA-040D's own precedent of giving PDF its own dedicated `pdf_acquisition_job` rather than extending the generic-sounding table, except here the retrofit runs in the opposite direction (renaming the generic table to a dedicated one, since Workbook — not a hypothetical future shared consumer — is its only real caller today).

1. **`mapping_profile_id` remains on `workbook_acquisition_job` as a required FK, unchanged from today's `acquisition_job`.** Basis: ADR-004 §3 (Migration Strategy) explicitly declines to resolve this by inference and defers it to this retrofit MWO's own WP-000. Resolution: `mapping_profile` has no analogue in PDF or Engineering Media because those object types have no reusable, customer-specific column-mapping concept — Workbook's own Business Rule ("Mapping Profiles must be reusable") is unique to tabular acquisition. A Workbook Acquisition Job's job is specifically to record "workbook X was validated and mapped using profile Y" (MWO-LTSA-040C Business Purpose); removing the FK would delete information the original work order requires, not merely rename a table. `mapping_profile`/`column_mapping` remain untouched, standalone, full-CRUD reusable-configuration tables, outside the four-stage pattern (the pattern governs the Acquisition Object → Metadata → Classification → Job chain; it does not claim to enumerate every table an Acquisition Object type needs) — this is stated as an explicit scope boundary, not silently assumed.
2. **`workbook_metadata` attributes: `title`, `author`, `company`, `application`, `application_version`, `last_saved_by`.** Basis: mirrors `pdf_metadata`'s role (container-level file properties, not business content) adapted to what a spreadsheet file's own document properties actually are (Excel's standard "Document Properties": Title, Author, Company, Application Name, Application Version, Last Saved By — the direct Excel-file analogues of a PDF's Title/Author/Producer). `creation_date`/`modification_date` are deliberately **not** duplicated here — `workbook.created_date` and `workbook.imported_date` already exist on the Acquisition Object table itself (added under MWO-LTSA-040C, before this pattern existed), unlike `pdf_document`, which carries no date fields of its own. Duplicating them on `workbook_metadata` would create the same kind of redundancy MWO-LTSA-040D's WP-000 design decision 4 flagged and accepted for `file_hash`/`file_size` — but there, the original work order explicitly named both fields on both objects; here, nothing in MWO-LTSA-040C's original text names workbook-file-property dates at all, so inventing a second, redundant pair is not evidence-grounded. Flagged as the one attribute set in this retrofit with the least direct textual citation, since "Workbook Metadata" did not exist as a named concept before ADR-004.
3. **`workbook_metadata` is Create/List/Detail only, one row per `workbook` (`UNIQUE` on `workbook_id`), no Update/Delete.** Basis: direct structural precedent, `pdf_metadata` (MWO-LTSA-040D design decision 8) — a spreadsheet file has exactly one set of document properties at a time, the same reasoning applied there.
4. **`workbook_classification.classification_type` reuses the same 11-value `workbook_type` closed set already defined on `workbook`.** Basis: direct structural precedent, `document_classification.classification_type` (MWO-LTSA-040D design decision 6) — no separate classification taxonomy exists for Workbook any more than one existed for PDF; classification's job is to assign a Workbook to one of the 11 Supported Workbook Types.
5. **`workbook_classification` is Create/List/Detail only, repeatable (no uniqueness constraint), no Update/Delete.** Basis: direct structural precedent, `document_classification` (MWO-LTSA-040D design decision 5/9) — "repeatable" is satisfied by new rows, not by mutating an existing classification's `status`/`confidence`.
6. **`workbook_acquisition_job`'s column shape, status set (`PENDING`/`IN_PROGRESS`/`READY_FOR_MANUFACTURING`/`FAILED`), and CRUD policy (Create/List/Detail/Update, no Delete) are unchanged from today's `acquisition_job`.** Basis: this is a rename, not a redesign (Architecture call, above) — MWO-LTSA-040C's own WP-000 design decisions 5 and 6 (which chose this status set and CRUD policy) remain valid and are not re-litigated here. Unlike `pdf_acquisition_job`, `READY_FOR_MANUFACTURING` is retained rather than replaced with `COMPLETED`, because Workbook's own pipeline genuinely ends at "ready for manufacturing" (MWO-LTSA-040C Architecture Decision item 9: a successful acquisition is "ready for manufacturing," future MWOs manufacture business objects from it) — this differs from PDF, whose Out of Scope explicitly excludes any manufacturing step, per MWO-LTSA-040D WP-000 design decision 10. The two status sets diverging is intentional, not an inconsistency to fix.
7. **No change to `workbook`, `worksheet`, `worksheet_table`, `mapping_profile`, or `column_mapping`'s own columns.** Basis: ADR-004 does not require every table an Acquisition Object type owns to fit inside the four-stage pattern (see design decision 1) — only that the Acquisition Object, Metadata, Classification, and Acquisition Job stages exist and follow the shared shape. `worksheet`/`worksheet_table` remain structural children of `workbook` (a distinct, already-conforming concept: "one workbook may contain multiple worksheets," a fact about file structure, not file metadata or classification), untouched.

**Canonical Mapping Table (locked):**

| Business Object | Canonical Table | Change |
|---|---|---|
| Workbook (unchanged) | `public.workbook` | No change |
| Worksheet (unchanged) | `public.worksheet` | No change |
| Worksheet Table (unchanged) | `public.worksheet_table` | No change |
| Mapping Profile (unchanged) | `public.mapping_profile` | No change |
| Column Mapping (unchanged) | `public.column_mapping` | No change |
| **Workbook Metadata (new)** | `public.workbook_metadata` (new) | New table |
| **Workbook Classification (new)** | `public.workbook_classification` (new) | New table |
| **Workbook Acquisition Job (renamed)** | `public.workbook_acquisition_job` (renamed from `public.acquisition_job`) | Rename only — no column/constraint/FK change |

**Rejected scope:** removing `mapping_profile_id` from the Acquisition Job table to make the pattern "purer" (would delete real, cited information — design decision 1); duplicating `created_date`/`modification_date` on `workbook_metadata` without textual basis (design decision 2); altering `workbook_acquisition_job`'s status set to match `pdf_acquisition_job`'s (would erase a real, cited business distinction — design decision 6); any change to `worksheet`/`worksheet_table`/`mapping_profile`/`column_mapping` themselves.

---

## Objective

Bring Workbook Acquisition into structural conformance with ADR-004 (Engineering Acquisition Pattern): add `workbook_metadata` and `workbook_classification`, and rename `acquisition_job` to `workbook_acquisition_job`, without altering any existing column, constraint, FK, or CRUD behavior beyond the rename itself.

## Scope

- Two new tables: `workbook_metadata`, `workbook_classification`, additive to `CANONICAL_SCHEMA.sql`.
- One rename: `acquisition_job` → `workbook_acquisition_job` (table name, primary key column name `acquisition_job_id` → `workbook_acquisition_job_id`, all FK references, indexes, and constraint names updated to match; no change to column types, nullability, or the status `CHECK` set).
- Two new build packs: `BP-WORKBOOK-METADATA`, `BP-WORKBOOK-CLASSIFICATION` (Create/List/Detail only, cloning `BP-PDF-METADATA`/`BP-DOCUMENT-CLASSIFICATION`).
- One renamed build pack: `BUILD-PACKS/BP-ACQUISITION-JOB` → `BUILD-PACKS/BP-WORKBOOK-ACQUISITION-JOB` (all internal file/table/column references renamed to match; CRUD behavior, validation logic, and status set unchanged).
- Documentation-only, additive/corrective update to `product.manifest.json` (new entries for the two new modules; the existing `acquisition_job` entry updated to reflect the rename, not a fresh module).
- Structural validation and a Completion Report.

## Out of Scope

- Any change to `workbook`, `worksheet`, `worksheet_table`, `mapping_profile`, or `column_mapping`'s own schema (design decision 7).
- Any change to `mapping_profile_id`'s presence or meaning on the (renamed) Acquisition Job table (design decision 1).
- Any change to the Acquisition Job status set or CRUD policy beyond the rename (design decision 6).
- OCR, AI reasoning, Recommendation, Engineering Analysis, Knowledge Extraction — unchanged from MWO-LTSA-040C's own Out of Scope.
- Any write path into a canonical business-object table.
- n8n-level execution — structural validation only, same standing reason as every prior MWO.
- **Implementation of any kind.** Per explicit instruction, this document is the retrofit specification only.

## Dependencies

- **ADR-004** — the governing pattern this retrofit exists to satisfy.
- **MWO-LTSA-040C** — the tables and build packs this MWO retrofits.
- **MWO-LTSA-040D** — `pdf_metadata`, `document_classification`, `pdf_acquisition_job` as the direct structural template.
- **MWO-P-006 / RV-004** — `PRODUCTS/LTSA-BRAIN/VERIFICATION/` test infrastructure, reused by every new/renamed `TEST/*.sh` script.

## Constraints

- Architecture frozen; Foundation v1.0 and Engineering Standard v1.0 locked and unmodified.
- The rename must be written idempotently and safely: `ALTER TABLE ... RENAME TO`, `ALTER TABLE ... RENAME COLUMN ...`, `ALTER INDEX ... RENAME TO ...`, guarded the same defensive way MWO-LTSA-040B's `ALTER TABLE ADD COLUMN IF NOT EXISTS` pattern was — since no live database has ever been bootstrapped in this repository (every Completion Report's standing Runtime Verification blocker), this remains a theoretical migration-safety question, not an observed one, but must still be written defensively, per that same precedent.
- No new architecture, service, credential mechanism, or table pattern is introduced.

### Execution Rules

1. **This document (WP-000) is submitted for approval. It does not itself authorize implementation.** Per explicit instruction ("Do not implement the retrofit now"), WP-001 onward (schema rename + 2 new tables + 2 new/renamed build packs + manifest) do not execute until separate, explicit Implementation Approval is given.
2. Once approved, WP-001 through WP-006 execute as a single batch.
3. Structural Validation (WP-007) covers the full batch, including a scope check confirming `workbook`, `worksheet`, `worksheet_table`, `mapping_profile`, and `column_mapping`'s own files show zero diff.
4. One Completion Report after the batch.
5. Nothing committed or pushed without separate, explicit approval (in addition to, and after, the implementation approval in Rule 1).

---

## WP-001 — Canonical Schema

`workbook_metadata` and `workbook_classification` added, additive, to `CANONICAL_SCHEMA.sql`. `acquisition_job` renamed to `workbook_acquisition_job` in place (rename statements, not a drop/recreate, to describe intent honestly even though no live data exists yet).

## WP-002 — BUILD-PACKS/BP-WORKBOOK-METADATA

Create/List/Detail only, cloning `BP-PDF-METADATA`'s file shape exactly, field names adapted per design decision 2.

## WP-003 — BUILD-PACKS/BP-WORKBOOK-CLASSIFICATION

Create/List/Detail only, cloning `BP-DOCUMENT-CLASSIFICATION`'s file shape exactly, `classification_type` reusing `workbook_type`'s closed set.

## WP-004 — BUILD-PACKS/BP-WORKBOOK-ACQUISITION-JOB (renamed from BP-ACQUISITION-JOB)

All files renamed and internally updated (table name, PK column name, workflow node names/paths, test script names) — no change to validation logic, status set, or CRUD policy.

## WP-005 — Manifest Documentation

Additive entries for `workbook_metadata`/`workbook_classification`; the existing `acquisition_job` entry updated in place to describe the rename (not deleted and re-added as if new), citing this retrofit MWO.

## WP-006 — Cross-References

Any other file that names `acquisition_job`/`BP-ACQUISITION-JOB`/`acquisition_job_id` (e.g. `mapping_profile`/`column_mapping` READMEs, if any reference it) updated to the new name, confirmed by a repository-wide search before the batch is considered complete.

## WP-007 — Structural Validation & Completion Report

`bash -n` on every new/renamed `.sh` file; JSON-parse validation on every new/renamed `.json` file; `git status`/`git diff` confirming `workbook`, `worksheet`, `worksheet_table`, `mapping_profile`, `column_mapping` show zero diff and that the `acquisition_job` → `workbook_acquisition_job` change is a pure rename (no column/constraint/FK content change beyond the name); a real (bounded, no-guessed-credential) database connection attempt, reported honestly; `ENGINEERING/MWO/MWO-LTSA-040C-R1-Completion-Report.md`.

---

## Deliverables

- `DATABASE/CANONICAL_SCHEMA.sql` — 2 new tables + 1 rename (WP-001)
- `BUILD-PACKS/BP-WORKBOOK-METADATA`, `BP-WORKBOOK-CLASSIFICATION` (WP-002–WP-003)
- `BUILD-PACKS/BP-WORKBOOK-ACQUISITION-JOB` (renamed from `BP-ACQUISITION-JOB`) (WP-004)
- `product.manifest.json` — additive + corrective entries (WP-005)
- `ENGINEERING/MWO/MWO-LTSA-040C-R1-Completion-Report.md` (WP-007)
- No change to `workbook`, `worksheet`, `worksheet_table`, `mapping_profile`, `column_mapping`'s own columns, `knowledge_source_registry`, `pdf_document`/`pdf_metadata`/`document_classification`/`pdf_acquisition_job`, or `ENGINEERING/RUNTIME/`.

## Acceptance Criteria

- `workbook`, `worksheet`, `worksheet_table`, `mapping_profile`, `column_mapping` show zero diff in `git status`/`git diff` beyond any necessary reference-name updates identified in WP-006.
- `acquisition_job` → `workbook_acquisition_job` is verifiably a pure rename: same columns, same constraints (renamed, not redefined), same FKs, same status `CHECK` values.
- `workbook_metadata`, `workbook_classification` have no Update or Delete workflow, matching `pdf_metadata`/`document_classification`.
- Structural Validation passes for every new/renamed file; Runtime Verification's standing blocker is stated, not hidden.

## Definition of Done

- WP-001–WP-006 complete, no out-of-scope file touched.
- WP-007's Structural Validation stated PASS/WARNING/BLOCKER; Completion Report exists.
- Nothing committed or pushed without separate, explicit approval.

---

This document is WP-000 only — the retrofit specification for MWO-LTSA-040C-R1. Per explicit instruction, no implementation has occurred: `MWO-LTSA-040C`'s existing schema and build packs are untouched. Implementation awaits a separate, later Implementation Approval.
