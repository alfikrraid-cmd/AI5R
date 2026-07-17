# MWO-LTSA-040C — Universal Tabular Data Acquisition

Status: APPROVED — Architecture Decision locked, implementation authorized
Type: Manufacturing Work Order (Acquisition Infrastructure)
Epic: Engineering Knowledge Acquisition
Role: Implementation Engineer
Architecture: FROZEN — no new architecture, service, table pattern, or framework introduced
Foundation: v1.0 — LOCKED, unchanged by this MWO
Engineering Standard: v1.0 — LOCKED, unchanged by this MWO
Basis: `ENGINEERING/AI5R_ENGINEERING_STANDARD_v1.0.md`; `MWO-LTSA-040A` (`knowledge_source_registry`, the table every Workbook originates from); `BUILD-PACKS/BP-SEAL/*` (canonical CRUD shape)
Scope: `PRODUCTS/LTSA-BRAIN` only

---

## Executive Summary

This MWO manufactures the Universal Acquisition Infrastructure: six generic, workbook-type-agnostic tracking objects (Workbook, Worksheet, Worksheet Table, Column Mapping, Mapping Profile, Acquisition Job) that record how a tabular source (Excel today, CSV/ODS/ERP export later, without redesign) was registered, mapped, normalized, and validated. It does not write to any canonical business-object table (`ltsa_pumps`, `seal_registry`, `seal_stock`, etc.) — per the Architecture Decision, a successful Acquisition Job produces a validated, mapped workbook "ready for manufacturing," not manufactured business objects. That step is explicitly deferred to future MWOs that will consume Acquisition Jobs.

---

## WP-000 — Architecture Decision (approved, resolved) and Design Decisions for Under-Specified Attributes

**Architecture Decision, recorded verbatim:**

1. MWO-LTSA-040C manufactures only the Universal Acquisition Infrastructure — not Pump, Mechanical Seal, Stock, Compatibility, Installation History, or any other canonical business object.
2. Supported Workbook Types define supported targets, not implementation scope.
3. Deliverables are the canonical scope: Workbook, Worksheet, Worksheet Table, Column Mapping, Mapping Profile, Acquisition Job. Nothing else.
4. "Object Manufacturing" (in the original work order's Objective) means manufacturing Acquisition Objects, not business objects.
5. Workbook import ends after Validation, Normalization, Mapping, Registration. It does not write to the Pump/Mechanical Seal/Stock/Compatibility/Installation registries.
6. Canonical business objects remain unchanged. Future MWOs will consume Acquisition Jobs to manufacture business objects.
7. Implementation must remain generic — no workbook-specific parser, no customer-specific parser, no hardcoded Pump Master parser.
8. Mapping Profile is the extension point. Customer-specific column names are handled through Mapping Profiles, never code.
9. A successful acquisition produces a validated, normalized, mapped workbook, ready for manufacturing, but performs no manufacturing of engineering objects.
10. Future MWOs will implement Workbook → Canonical Object manufacturing using the Acquisition Layer built by this MWO.

**Design decisions for attributes the original work order did not specify (cited, per Evidence Standard):**

1. **`workbook_type` added to `Workbook`, constrained to the 11 named Supported Workbook Types.** The original work order names a whole "Supported Workbook Types" section (Pump Master, Mechanical Seal Master, Seal Stock, Seal Interchange, Pump Compatibility, Installation History, Maintenance History, Engineer Master, Customer Master, Vendor Master, Bill Of Material) but `Workbook`'s own attribute list omits it. Without storing this classification somewhere, "Supported Workbook Types" would be unreachable — no other object in the pipeline is positioned to carry it as cleanly, since a Worksheet/Table is a structural fact about *a* workbook, not a classification of *which kind*. Added as a `CHECK`-constrained column, validated the same generic way every other closed-set field in this product already is (Architecture Decision item 7: this is config, not a parser).
2. **`Worksheet Table` attributes (none given): `table_name`, `row_count`, `column_count`.** Mirrors `Worksheet`'s own given shape (`worksheet_name`/`row_count`/`column_count`) one level down, since a Structured Table is described only as "may manufacture multiple Canonical Objects" — a structural fact, not a business concept requiring richer metadata this MWO isn't scoped to define (Architecture Decision item 3).
3. **`Mapping Profile` attributes (none given): `profile_name`, `workbook_type`, `customer`, `description`, `status`.** `workbook_type` is required because a profile's Column Mappings only make sense against one workbook type's canonical attribute set (a Pump Master profile and a Seal Stock profile cannot share source-column vocabulary). `customer` is free text, matching the given examples ("Pertamina RU II," "Chevron," "Exxon," "Internal LTSA" — the last of which is not a `customer_registry` entry, so a foreign key would not fit all examples); this mirrors the same "leave ungoverned dimension as free text" choice made for `knowledge_source_registry.customer`/`site`/`unit` in MWO-040A.
4. **`Column Mapping` attributes beyond the given source-column/canonical-attribute pair: `mapping_profile_id` (parent FK), `is_mandatory`.** A mapping only has meaning within a profile (Business Purpose: "A Mapping Profile defines how customer-specific column names map to canonical LTSA attributes"). `is_mandatory` is added because the Validation section explicitly requires validating "Missing Mandatory Values" — this is the only place that concept can be recorded generically without a per-workbook-type parser.
5. **`Acquisition Job` attributes (none given): `workbook_id`, `mapping_profile_id`, `status`, `started_at`, `completed_at`, `rows_processed`, `rows_valid`, `rows_invalid`, `error_summary`.** A minimal, generic job-log shape reflecting the pipeline's own stated stages (registration → mapping → normalization → validation) without asserting manufacturing occurred, consistent with item 9 above. `status` uses a 4-value set (`PENDING`, `IN_PROGRESS`, `READY_FOR_MANUFACTURING`, `FAILED`) chosen for minimality, not because the original text specifies these exact labels — flagged here as the one part of this design most likely to need revision once a real acquisition workflow is built against it.
6. **CRUD policy per object:** `Workbook`, `Worksheet`, `Worksheet Table` get Create/List/Detail only — no Update, no Delete — mirroring "Original Workbook must never be modified" (Business Rule) and treating all three as immutable structural facts about the source file, the same immutability class as `knowledge_source_registry`. `Mapping Profile` and `Column Mapping` get full 5-operation CRUD, since "Mapping Profiles must be reusable" (Business Rule) implies they are a managed, editable resource, not a one-time record. `Acquisition Job` gets Create/List/Detail/Update (no Delete) — its `status`/count/`completed_at`/`error_summary` fields legitimately progress over a job's lifecycle, but no rule suggests a job record should ever be removed, and "Acquisition must be repeatable" (Business Rule) is satisfied by allowing multiple Job rows against the same Workbook + Mapping Profile pair, not by mutating one row repeatedly.

**Canonical Mapping Table (locked):**

| Business Object | Canonical Table | CRUD |
|---|---|---|
| Workbook | `public.workbook` (new) | Create/List/Detail |
| Worksheet | `public.worksheet` (new) | Create/List/Detail |
| Worksheet Table | `public.worksheet_table` (new) | Create/List/Detail |
| Mapping Profile | `public.mapping_profile` (new) | Full CRUD |
| Column Mapping | `public.column_mapping` (new) | Full CRUD |
| Acquisition Job | `public.acquisition_job` (new) | Create/List/Detail/Update |
| Knowledge Source (referenced) | `public.knowledge_source_registry` (MWO-040A) | Untouched |

**Rejected scope:** any table for Pump/Mechanical Seal/Stock/Compatibility/Installation History/Maintenance History/Engineer/Customer/Vendor/Bill of Material acquisition targets — explicitly deferred (Architecture Decision items 1, 6, 10).

---

## Objective

Manufacture the six Universal Acquisition Infrastructure objects as `BUILD-PACKS/BP-<NAME>` packs, additive to `DATABASE/CANONICAL_SCHEMA.sql`, cloning the exact pattern already proven by `BP-SEAL`/`BP-KNOWLEDGE-SOURCE`.

## Scope

- Six new tables: `workbook`, `worksheet`, `worksheet_table`, `mapping_profile`, `column_mapping`, `acquisition_job`.
- Six new build packs: `BP-WORKBOOK`, `BP-WORKSHEET`, `BP-WORKSHEET-TABLE`, `BP-MAPPING-PROFILE`, `BP-COLUMN-MAPPING`, `BP-ACQUISITION-JOB`.
- Documentation-only, additive update to `product.manifest.json`.
- Structural validation and a Completion Report.

## Out of Scope

- OCR, PDF, image analysis, AI, Recommendation, Runtime redesign (per the original work order's own Out of Scope).
- Any write path into a canonical business-object table (Architecture Decision items 1, 5, 6).
- Any workbook-type-specific or customer-specific code (Architecture Decision items 7-8) — every closed-set validation in this MWO is generic, parameterized by data (a `CHECK` constraint / an allow-list array), never a per-type branch.
- Actual Excel file parsing (no `.xlsx` reading library, no spreadsheet-file n8n node) — every workflow in this MWO accepts already-extracted metadata (names, counts, mappings) as JSON input, the same way every other n8n workflow in this product accepts a JSON body rather than a raw file. Real file parsing is Runtime-layer work, out of scope per "Do NOT redesign Runtime."
- n8n-level execution — structural validation only, same standing reason as every prior MWO.

## Dependencies

- **MWO-LTSA-040A** — `knowledge_source_registry`, the table `workbook.knowledge_source_id` references.
- **MWO-P-006 / RV-004** — `PRODUCTS/LTSA-BRAIN/VERIFICATION/` test infrastructure.

## Constraints

- Architecture frozen; Foundation v1.0 and Engineering Standard v1.0 locked and unmodified.
- No new table pattern — every table follows `seal_registry`'s shape (TEXT PK, `created_at`/`updated_at TIMESTAMP DEFAULT NOW()`), extended with `CHECK` constraints for closed-set fields, matching every prior MWO this sprint.
- Nothing generic-vs-specific is violated: every enum/allow-list is data (an array or `CHECK` list), not a code branch.

### Execution Rules

1. WP-000 is approved (Architecture Decision + attribute design decisions recorded above).
2. WP-001 through WP-008 (schema + 6 build packs + manifest) execute as a single batch.
3. Structural Validation (WP-009) covers the full batch.
4. One Completion Report after the batch.
5. Nothing committed or pushed without separate, explicit approval.

---

## WP-001 — Canonical Schema

Six new tables, additive to `CANONICAL_SCHEMA.sql`, per the Canonical Mapping Table above.

## WP-002 through WP-007 — Build Packs

One work package per build pack (`BP-WORKBOOK`, `BP-WORKSHEET`, `BP-WORKSHEET-TABLE`, `BP-MAPPING-PROFILE`, `BP-COLUMN-MAPPING`, `BP-ACQUISITION-JOB`), each DATABASE + SCHEMAS + WORKFLOWS (per its CRUD policy above) + TEST + README, cloning `BP-SEAL`'s pattern.

## WP-008 — Manifest Documentation

Additive `implementation_status` entries for all six new modules.

## WP-009 — Structural Validation & Completion Report

`bash -n` on every new `.sh` file; JSON-parse validation on every new `.json` file; `git status` scope confirmation; a real (bounded, no-guessed-credential) database connection attempt, reported honestly; `ENGINEERING/MWO/MWO-LTSA-040C-Completion-Report.md`.

---

## Deliverables

- `DATABASE/CANONICAL_SCHEMA.sql` — 6 new tables (WP-001)
- `BUILD-PACKS/BP-WORKBOOK`, `BP-WORKSHEET`, `BP-WORKSHEET-TABLE`, `BP-MAPPING-PROFILE`, `BP-COLUMN-MAPPING`, `BP-ACQUISITION-JOB` (WP-002–WP-007)
- `product.manifest.json` — additive entries (WP-008)
- `ENGINEERING/MWO/MWO-LTSA-040C-Completion-Report.md` (WP-009)
- No change to any canonical business-object table, `knowledge_source_registry`, or `ENGINEERING/RUNTIME/`.

## Acceptance Criteria

- No canonical business-object table (`ltsa_pumps`, `seal_registry`, `seal_stock`, `seal_pump_compatibility`, `seal_interchange_compatibility`, `seal_engineering_document`, `customer_registry`, `asset_registry`, `soot_blower_registry`, `work_order`, `maintenance_history`) is touched.
- Every closed-set validation (workbook_type, acquisition_job status) is a generic allow-list, never a per-type code branch.
- `Workbook`/`Worksheet`/`Worksheet Table` have no Update or Delete workflow.
- Structural Validation passes for every new file; Runtime Verification's standing blocker is stated, not hidden.

## Definition of Done

- WP-001–WP-008 complete, no out-of-scope file touched.
- WP-009's Structural Validation stated PASS/WARNING/BLOCKER; Completion Report exists.
- Nothing committed or pushed without separate, explicit approval.

---

This document, together with the schema addition and six new build packs, is being produced per the Chief Architect's "Implementation may proceed" instruction. Commit and push remain separate, later approvals.
