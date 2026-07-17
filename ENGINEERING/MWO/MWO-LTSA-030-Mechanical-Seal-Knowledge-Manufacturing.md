# MWO-LTSA-030 — Mechanical Seal Knowledge Manufacturing

Status: APPROVED — Architecture Decision locked, implementation authorized
Type: Manufacturing Work Order (Knowledge Model)
Epic: LTSA Knowledge
Role: Implementation Engineer
Architecture: FROZEN — no new architecture, service, table pattern, or framework introduced
Foundation: v1.0 — LOCKED, unchanged by this MWO
Engineering Standard: v1.0 — LOCKED, unchanged by this MWO
Basis: `ENGINEERING/AI5R_ENGINEERING_STANDARD_v1.0.md`; `MANUFACTURING/MO-001/MO-001-SPECIFICATION.md` (direct structural precedent); `BUILD-PACKS/BP-SEAL/*` (canonical Mechanical Seal registry, cloned pattern for every new table); `DATABASE/CANONICAL_SCHEMA.sql` (target of this MWO's additive changes)
Scope: `PRODUCTS/LTSA-BRAIN` only

---

## Executive Summary

This is not an inventory module and not a stock module — it is a knowledge model describing how Mechanical Seals, their stock, their pump fitments, their manufacturer-interchange substitutes, and their engineering documents relate to one another, so that a query like "do we have a seal for Pump 211-P-1?" can be answered from stored relationships rather than tribal knowledge.

Before implementation, two terms in the original work order were ambiguous enough that two candidate, non-interoperating repository patterns could each plausibly satisfy them: "Manufacturing Framework" (the generic `AI5R-SDK/MANUFACTURING` recipe/capability pattern vs. the `BUILD-PACKS/BP-<NAME>` convention actually used for every real LTSA-BRAIN object) and "Knowledge Framework" (no framework by that name exists anywhere under `ENGINEERING/`; the only candidate, `AI5R-SDK/INTELLIGENCE/KNOWLEDGE`, was found disconnected from LTSA-BRAIN by a prior audit, MWO-P-001). Both were surfaced and resolved by an explicit Architecture Decision before any implementation began (WP-000, below).

---

## WP-000 — Architecture Decision (approved, resolved)

Recorded verbatim from the Chief Architect's approved decision:

1. Mechanical Seal Knowledge belongs to `PRODUCTS/LTSA-BRAIN`, not `AI5R-SDK/MANUFACTURING`.
2. Reuse `BUILD-PACKS/BP-<NAME>` architecture — the same canonical implementation style already used for Pump, Seal, Asset, Work Order, and Maintenance (the pattern `MANUFACTURING/MO-001` used, not the generic recipe/capability framework in `AI5R-SDK/MANUFACTURING`).
3. Pump references must use `MODULES/PUMP` (`ltsa_pumps.tag_number`), never the deprecated `BUILD-PACKS/BP-PUMP` (`pump_registry`).
4. Seal references must use `BUILD-PACKS/BP-SEAL` (`seal_registry`) as the canonical Mechanical Seal registry. Mechanical Seal is therefore **not** re-manufactured as a new table under this MWO — it already exists.
5. "Knowledge Framework" is removed from the specification's vocabulary; replaced throughout with "LTSA Engineering Knowledge Model" — a relational model queryable by the existing LTSA Copilot/AI-ASSISTANT layer, not a separate codebase to build or reuse.
6. Drawing, Datasheet, Installation Guide, and Inspection Sheet are Engineering Documents linked to Mechanical Seal. They are not independent products.
7. Do not implement generic document management. Documents exist only as Engineering Documents owned by a Mechanical Seal (always FK'd to exactly one `seal_code`, `document_type` a closed set of the four named types).
8. Continue implementation using the existing LTSA BUILD-PACK pattern. No further architecture clarification required.

**Canonical Mapping Table (locked):**

| Business Object (MWO term) | Canonical Table | Status |
|---|---|---|
| Mechanical Seal | `public.seal_registry` (`BUILD-PACKS/BP-SEAL`) | Already manufactured (MWO-P-005) — reused as-is, not touched |
| Seal Stock | `public.seal_stock` (new) | New, additive |
| Pump Compatibility | `public.seal_pump_compatibility` (new) | New, additive |
| Interchange Compatibility | `public.seal_interchange_compatibility` (new) | New, additive |
| Engineering Document | `public.seal_engineering_document` (new) | New, additive — added by Architecture Decision item 6, not in the original object list, but required by it |
| Pump (referenced, not owned) | `public.ltsa_pumps` (`MODULES/PUMP`) | Already manufactured (MWO-P-004) — read-only reference by FK, not touched |

**Deprecated / rejected candidates, not used:** `BUILD-PACKS/BP-PUMP.pump_registry` (deprecated stub, per Architecture Decision item 3); `AI5R-SDK/MANUFACTURING` recipe/capability framework (per item 1); `AI5R-SDK/INTELLIGENCE/KNOWLEDGE` (per item 5 — not referenced by this MWO).

---

## Objective

Manufacture the LTSA Engineering Knowledge Model for Mechanical Seals: Seal Stock, Pump Compatibility, Interchange Compatibility, and Engineering Documents — each additive to `DATABASE/CANONICAL_SCHEMA.sql`, each delivered as its own `BUILD-PACKS/BP-<NAME>` (DATABASE + SCHEMAS + WORKFLOWS + TEST + README), cloning the exact pattern `BP-SEAL` and `MANUFACTURING/MO-001`'s four packs already prove.

## Scope

- New tables in `PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql`: `seal_stock`, `seal_pump_compatibility`, `seal_interchange_compatibility`, `seal_engineering_document`. Additive only — nothing existing altered.
- Four new build packs: `BUILD-PACKS/BP-SEAL-STOCK`, `BUILD-PACKS/BP-SEAL-PUMP-COMPATIBILITY`, `BUILD-PACKS/BP-SEAL-INTERCHANGE-COMPATIBILITY`, `BUILD-PACKS/BP-SEAL-ENGINEERING-DOCUMENT`, each with DATABASE/SCHEMAS/WORKFLOWS/TEST/README, following BP-SEAL's shape exactly.
- Documentation-only, additive update to `PRODUCTS/LTSA-BRAIN/product.manifest.json`'s `implementation_status` section (matching the precedent set by MO-001's own manifest update) — not a Registry change; `REGISTRIES/*.json` is untouched (see Out of Scope).
- Structural validation of every new file (JSON parse, `bash -n`) and a Completion Report.

## Out of Scope

- **Re-manufacturing Mechanical Seal.** `seal_registry` and its five existing workflows (`BUILD-PACKS/BP-SEAL/WORKFLOWS/*.json`) are read-only for this MWO.
- **Touching `BUILD-PACKS/BP-PUMP` or `MODULES/PUMP`.** Pump is referenced by FK only (`ltsa_pumps.tag_number`); no pump file is modified.
- **`PRODUCTS/LTSA-BRAIN/REGISTRIES/*.json`.** Per the original work order's "No Registry changes" constraint. No `SEAL_STOCK.json`, `PUMP_COMPATIBILITY.json`, etc. is created.
- **`ENGINEERING/RUNTIME/`.** Per the original work order's "No Runtime changes" constraint. Nothing in this MWO touches the execution core.
- **Generic document management** of any kind (upload UI, storage backend, versioning engine). Engineering Documents are metadata rows (`file_reference` as a pointer/path field) owned by a seal, per Architecture Decision item 7.
- **Risk Intelligence / Copilot computation.** The worked example's risk logic (`Stock × Compatible Pumps × Open Work Orders → HIGH/MED/LOW`) is a query composed from this MWO's tables (a join across `seal_stock`, `seal_pump_compatibility`, and `work_order`), not a stored table or a new service — building the Copilot/Intelligence Layer that runs that query is explicitly out of scope (no Runtime/AI-ASSISTANT change is proposed here). The schema is shaped so that query is possible without further schema change.
- **n8n-level execution of any kind**, for the same standing reason as every prior MWO this sprint (`RV-004-Verification-Report.md`): no n8n instance is reachable from this environment. Structural validation only.
- Authentication, authorization, CI/CD — untouched, consistent with every prior MWO.

## Dependencies

- **MWO-P-002 / IR-001** — `DATABASE/CANONICAL_SCHEMA.sql` as the single canonical schema file this MWO extends additively.
- **MWO-P-004** — `ltsa_pumps` (`MODULES/PUMP`) as the canonical Pump Registry this MWO's Pump Compatibility table references by FK.
- **MWO-P-005** — `seal_registry` (`BUILD-PACKS/BP-SEAL`) as the canonical Mechanical Seal registry every new table in this MWO references by FK.
- **MWO-P-006 / RV-004** — `PRODUCTS/LTSA-BRAIN/VERIFICATION/` (shared test runner, `psql_common.sh`) reused by every new `TEST/*.sh` script in this MWO, not re-derived.
- **MANUFACTURING/MO-001** — the direct structural precedent for adding new, non-conflicting business-object tables additively via the BUILD-PACK pattern.

## Constraints

- Architecture is frozen. Foundation v1.0 and Engineering Standard v1.0 are locked and unmodified.
- No new architecture, service, credential mechanism, or table *pattern* is introduced — every new table is a plain Postgres table following `seal_registry`'s exact shape (TEXT/VARCHAR natural keys, `created_at`/`updated_at TIMESTAMP DEFAULT NOW()`), extended only with real FKs where the relationship is non-polymorphic (a deliberate, evidenced choice — see Canonical Mapping Table — not a new pattern).
- Every Create workflow uses the graceful pre-insert conflict-check pattern (`Check Existing → IF Exists → 409`) established by Seal Create under MWO-P-005, per `MO-001-SPECIFICATION.md` §4's consistency rule.
- Do not modify `seal_registry`, `ltsa_pumps`, or any of their existing workflow files.

### Execution Rules (approval granularity, stated explicitly per Engineering Standard v1.0 §5)

1. WP-000 (Architecture Decision) is approved — recorded above, not re-derived.
2. WP-001 through WP-006 execute as a single batch, without stopping, once WP-000 is approved (matching this MWO's own approval: "Continue implementation... No further architecture clarification required").
3. Structural Validation (WP-007) is performed against the full batch, not per-WP.
4. One Completion Report is produced after the full batch. No individual report is produced per WP unless a BLOCKER occurs.
5. Nothing is committed or pushed without separate, explicit approval.

---

## WP-001 — Canonical Schema

**Scope:** Four new tables, additive to `DATABASE/CANONICAL_SCHEMA.sql`: `seal_stock`, `seal_pump_compatibility`, `seal_interchange_compatibility`, `seal_engineering_document`. Full DDL and rationale recorded in the schema file's own header comment for this block.

**Acceptance Criteria:** Every new table uses `CREATE TABLE IF NOT EXISTS` (idempotent, matching every existing table in the file); every FK targets an existing canonical table/column; nothing existing in the file is altered.

## WP-002 — BUILD-PACKS/BP-SEAL-STOCK

**Scope:** Full build pack for Seal Stock (`seal_stock`, PK `seal_code`, single-key CRUD identical in shape to `BP-SEAL`'s own five operations, fields `quantity_on_hand`/`reorder_point`/`location` in place of Seal's spec fields).

## WP-003 — BUILD-PACKS/BP-SEAL-PUMP-COMPATIBILITY

**Scope:** Full build pack for Pump Compatibility (`seal_pump_compatibility`, composite PK `(seal_code, pump_tag_number)` — many-to-many per Business Rules, so Detail/Update/Delete address both key fields, not one).

## WP-004 — BUILD-PACKS/BP-SEAL-INTERCHANGE-COMPATIBILITY

**Scope:** Full build pack for Interchange Compatibility (`seal_interchange_compatibility`, composite PK `(seal_code, compatible_seal_code)`, self-referential against `seal_registry`, `CHECK (seal_code <> compatible_seal_code)`).

## WP-005 — BUILD-PACKS/BP-SEAL-ENGINEERING-DOCUMENT

**Scope:** Full build pack for Engineering Document (`seal_engineering_document`, PK `document_code`, single-key CRUD, `document_type` validated both at the workflow layer — `Validate ... Input` rejects any value outside the four named types — and at the schema layer, `CHECK (document_type IN (...))`).

## WP-006 — Manifest Documentation

**Scope:** Additive-only update to `product.manifest.json`'s `implementation_status` section, recording the four new modules (`seal_stock`, `seal_pump_compatibility`, `seal_interchange_compatibility`, `seal_engineering_document`) at `"partial"` status, matching MO-001's own precedent entries in structure and honesty about validation state (structurally validated, Runtime Verification blocked on the same standing no-credentialed-database condition as every other module). Does not change module enablement or artifact flags, per the section's own stated convention.

## WP-007 — Structural Validation & Completion Report

**Scope:** `bash -n` on every new `.sh` file; JSON-parse validation on every new `.json` file; `git status` confirmation that no out-of-scope file was touched; `ENGINEERING/MWO/MWO-LTSA-030-Completion-Report.md` produced, stating PASS/WARNING/BLOCKER per work package and naming Runtime Verification's standing blocker explicitly (no n8n instance, no credentialed database in this session — same condition as every prior MWO this sprint), not implied as passed.

---

## Deliverables

- `DATABASE/CANONICAL_SCHEMA.sql` — 4 new tables (WP-001)
- `BUILD-PACKS/BP-SEAL-STOCK/{DATABASE,SCHEMAS,WORKFLOWS,TEST}/*`, `README.md` (WP-002)
- `BUILD-PACKS/BP-SEAL-PUMP-COMPATIBILITY/{DATABASE,SCHEMAS,WORKFLOWS,TEST}/*`, `README.md` (WP-003)
- `BUILD-PACKS/BP-SEAL-INTERCHANGE-COMPATIBILITY/{DATABASE,SCHEMAS,WORKFLOWS,TEST}/*`, `README.md` (WP-004)
- `BUILD-PACKS/BP-SEAL-ENGINEERING-DOCUMENT/{DATABASE,SCHEMAS,WORKFLOWS,TEST}/*`, `README.md` (WP-005)
- `product.manifest.json` — additive `implementation_status` entries (WP-006)
- `ENGINEERING/MWO/MWO-LTSA-030-Completion-Report.md` (WP-007)
- No change to `seal_registry`, `ltsa_pumps`, `REGISTRIES/*.json`, or `ENGINEERING/RUNTIME/`.

## Acceptance Criteria

- Every new table is additive; nothing existing in `CANONICAL_SCHEMA.sql` is altered.
- Every new build pack matches `BP-SEAL`'s file shape exactly (DATABASE/README/SCHEMAS/WORKFLOWS/TEST), adapted for composite keys where the business object is a many-to-many relationship.
- Every FK in the Canonical Mapping Table points at the correct canonical table (never `BP-PUMP`'s deprecated stub).
- No generic document management is built; Engineering Documents remain scoped to seal ownership.
- Structural Validation passes for every new file; Runtime Verification's standing blocker is stated, not hidden.

## Definition of Done

- WP-000's Architecture Decision recorded and treated as approved (met by this document).
- WP-001–WP-006 complete, each additive only, no out-of-scope file touched (verified via `git status`, not assumed).
- WP-007's Structural Validation stated PASS/WARNING/BLOCKER per work package; Completion Report exists.
- Nothing committed or pushed without separate, explicit approval.

---

This document, together with the four new build packs and the schema addition, is being produced per the Chief Architect's explicit "Continue implementation" instruction. Commit and push remain separate, later approvals, per Engineering Standard v1.0 §10/§11.
