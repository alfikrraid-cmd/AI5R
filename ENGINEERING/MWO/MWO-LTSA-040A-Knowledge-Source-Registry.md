# MWO-LTSA-040A — Knowledge Source Registry

Status: APPROVED — Architecture Decision locked, implementation authorized
Type: Manufacturing Work Order (Provenance Registry)
Epic: Engineering Knowledge Acquisition
Role: Implementation Engineer
Architecture: FROZEN — no new architecture, service, table pattern, or framework introduced
Foundation: v1.0 — LOCKED, unchanged by this MWO
Engineering Standard: v1.0 — LOCKED, unchanged by this MWO
Basis: `ENGINEERING/AI5R_ENGINEERING_STANDARD_v1.0.md`; `BUILD-PACKS/BP-SEAL/*` (canonical CRUD shape, cloned pattern); `MWO-LTSA-030` (direct structural precedent for a new, additive, LTSA-BRAIN-scoped table)
Scope: `PRODUCTS/LTSA-BRAIN` only

---

## Executive Summary

This MWO manages knowledge provenance only: a registry recording that an engineering knowledge source (a report, drawing, Excel file, photo, note, etc.) exists, who uploaded it, when, and its verification state — so that every future extracted knowledge object can trace back to exactly one source. It performs no extraction, no OCR, no parsing, no AI reasoning.

Before implementation, two things needed resolving. First, an identically-named artifact already exists — `AI5R-SDK/KNOWLEDGE/knowledge_source.py` / `knowledge_source_registry.py`, part of a frozen ("no redesign without Architecture Review"), AI5R-platform-level, product-agnostic Knowledge Foundation (KF-005), currently disconnected from every product. Second, the MWO's own "Produced Relationships" section names `Engineering Document`, which already exists as `seal_engineering_document` (MWO-LTSA-030) but scoped narrowly to Mechanical Seal ownership, raising the question of whether this MWO should retrofit it. Both were resolved by an explicit Architecture Decision before any implementation began (WP-000, below).

---

## WP-000 — Architecture Decision (approved, resolved)

Recorded verbatim from the Chief Architect's approved decision:

1. Knowledge Source Registry, as defined by MWO-LTSA-040A, is LTSA-scoped. It is not `AI5R-SDK/KNOWLEDGE`.
2. `AI5R-SDK/KNOWLEDGE` remains an AI5R platform module. It is not reused by LTSA — no modification, no integration, no redesign.
3. Knowledge Source Registry belongs to `PRODUCTS/LTSA-BRAIN`, following the canonical BUILD-PACK architecture.
4. Knowledge Source Registry is the canonical registry for engineering source provenance inside LTSA.
5. `seal_engineering_document` remains unchanged — no schema modification, no foreign key addition, no redesign.
6. The relationship Knowledge Source → Engineering Document is logical, not physical, in MWO-040A. Physical linkage is introduced when Engineering Document Acquisition is implemented (MWO-LTSA-040B).
7. Installation Event, Inspection Event, Failure Event, and Engineering Media do not exist yet. They are not manufactured inside MWO-040A — they belong to future MWOs.
8. MWO-040A manufactures Knowledge Source only. Nothing else.
9. CRUD policy: Knowledge Source supports Create, List, Detail, Update. Delete is intentionally omitted — original engineering sources must never be removed by Engineering Knowledge Acquisition.
10. Future MWOs: 040B connects Engineering Documents, 040C connects Excel Acquisition, 040D connects PDF Acquisition, 040E connects Engineering Media, 040F connects Video Acquisition.
11. No further clarification required. Implementation may proceed.

**Canonical Mapping Table (locked):**

| Business Object (MWO term) | Canonical Table | Status |
|---|---|---|
| Knowledge Source | `public.knowledge_source_registry` (new) | New, additive — the sole deliverable of this MWO |
| Engineering Document (referenced, logical only) | `public.seal_engineering_document` (`BUILD-PACKS/BP-SEAL-ENGINEERING-DOCUMENT`, MWO-030) | Untouched — no FK added; physical link deferred to MWO-040B |
| Installation Event, Inspection Event, Failure Event, Engineering Media | none yet | Not manufactured by this MWO — future MWOs |

**Rejected candidates, not used:** `AI5R-SDK/KNOWLEDGE` (frozen, AI5R-platform-level, per Architecture Decision items 1-2 — not modified, not integrated, not redesigned).

---

## Objective

Manufacture the Knowledge Source Registry: a single canonical table recording every engineering knowledge source's provenance metadata, delivered as `BUILD-PACKS/BP-KNOWLEDGE-SOURCE` (DATABASE + SCHEMAS + WORKFLOWS + TEST + README), cloning the exact pattern `BP-SEAL` and MWO-LTSA-030's build packs already prove — additive to `DATABASE/CANONICAL_SCHEMA.sql`.

## Scope

- One new table in `PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql`: `knowledge_source_registry`. Additive only.
- One new build pack: `BUILD-PACKS/BP-KNOWLEDGE-SOURCE`, with DATABASE/SCHEMAS/WORKFLOWS/TEST/README, following `BP-SEAL`'s shape — Create, List, Detail, Update only (no Delete, per Business Rule and Architecture Decision item 9).
- Documentation-only, additive update to `product.manifest.json`'s `implementation_status` section.
- Structural validation of every new file and a Completion Report.

## Out of Scope

- **OCR, PDF extraction, Excel parsing, video analysis, AI reasoning, AI diagnosis, Recommendation Engine.** Every attribute stored is caller-supplied metadata; nothing in this MWO reads or interprets file contents.
- **`AI5R-SDK/KNOWLEDGE`.** No file in that package is read, modified, or integrated with (Architecture Decision items 1-2).
- **`seal_engineering_document`.** No schema modification, no FK addition (Architecture Decision item 5). The Knowledge Source → Engineering Document relationship is documented as logical only in this MWO.
- **Installation Event, Inspection Event, Failure Event, Engineering Media.** None of these tables exist and none is created here (Architecture Decision item 7) — reserved for future MWOs (040B–040F, per item 10).
- **Delete operation.** Not built for Knowledge Source, by design (Architecture Decision item 9) — the original source must never be removable via this registry's own workflows.
- **`ENGINEERING/RUNTIME/`, `PRODUCTS/LTSA-BRAIN/REGISTRIES/*.json`.** Neither touched — no Runtime change, no Registry-folder change (distinct from the `_registry`-suffixed table naming convention, which this MWO does use).
- **n8n-level execution.** Same standing reason as every prior MWO this sprint — structural validation only.

## Dependencies

- **MWO-P-002 / IR-001** — `DATABASE/CANONICAL_SCHEMA.sql` as the single canonical schema file this MWO extends additively.
- **MWO-P-005 / MWO-LTSA-030** — `BP-SEAL`'s CRUD shape (conflict-check Create, unfiltered List, key-lookup Detail, dynamic-SET-clause Update) as the exact pattern this MWO's four workflows clone.
- **MWO-P-006 / RV-004** — `PRODUCTS/LTSA-BRAIN/VERIFICATION/` (shared test runner, `psql_common.sh`) reused by every new `TEST/*.sh` script, not re-derived.

## Constraints

- Architecture is frozen. Foundation v1.0 and Engineering Standard v1.0 are locked and unmodified.
- No new architecture, service, credential mechanism, or table pattern is introduced — `knowledge_source_registry` follows `seal_registry`'s exact shape (TEXT PK, `created_at`/`updated_at TIMESTAMP DEFAULT NOW()`), extended only with `CHECK` constraints for its two closed-set fields (`source_type`, `verification_status`), the same convention MWO-030's `seal_engineering_document` already established for `document_type`.
- `knowledge_source_id` is immutable — never included in the Update workflow's updatable-field list (Business Rule, Architecture Decision).
- No Delete workflow is built (Business Rule, Architecture Decision item 9).
- Every Create workflow uses the graceful pre-insert conflict-check pattern (`Check Existing → IF Exists → 409`) established by Seal Create under MWO-P-005.

### Execution Rules (approval granularity, stated explicitly per Engineering Standard v1.0 §5)

1. WP-000 (Architecture Decision) is approved — recorded above, not re-derived.
2. WP-001 through WP-004 execute as a single batch, without stopping, once WP-000 is approved ("Implementation may proceed," item 11).
3. Structural Validation (WP-005) is performed against the full batch, not per-WP.
4. One Completion Report is produced after the full batch. No individual report is produced per WP unless a BLOCKER occurs.
5. Nothing is committed or pushed without separate, explicit approval.

---

## WP-001 — Canonical Schema

**Scope:** One new table, additive to `DATABASE/CANONICAL_SCHEMA.sql`: `knowledge_source_registry` (PK `knowledge_source_id`, `source_type` and `verification_status` each constrained to their closed sets via `CHECK`).

**Acceptance Criteria:** `CREATE TABLE IF NOT EXISTS` (idempotent); nothing existing in the file is altered; no FK added to or from `seal_engineering_document` (Architecture Decision item 5).

## WP-002 — BUILD-PACKS/BP-KNOWLEDGE-SOURCE

**Scope:** Full build pack for Knowledge Source (`knowledge_source_registry`, PK `knowledge_source_id`, single-key CRUD — Create/List/Detail/Update only, no Delete). Create validates `source_type` against its 15-value closed set and rejects a non-numeric or negative `file_size`; Update permits changing any field except `knowledge_source_id`, validating `source_type`/`verification_status` against their closed sets whenever supplied.

## WP-003 — Manifest Documentation

**Scope:** Additive-only update to `product.manifest.json`'s `implementation_status` section, recording the new `knowledge_source_registry` module at `"partial"` status, matching MWO-030's own precedent entries in structure and honesty about validation state.

## WP-004 — Structural Validation & Completion Report

**Scope:** `bash -n` on every new `.sh` file; JSON-parse validation on every new `.json` file; `git status` confirmation that no out-of-scope file was touched (in particular, `seal_engineering_document`'s files and `AI5R-SDK/KNOWLEDGE/*` must show zero diff); `ENGINEERING/MWO/MWO-LTSA-040A-Completion-Report.md` produced, stating PASS/WARNING/BLOCKER per work package and naming Runtime Verification's standing blocker explicitly, not implied as passed.

---

## Deliverables

- `DATABASE/CANONICAL_SCHEMA.sql` — 1 new table (WP-001)
- `BUILD-PACKS/BP-KNOWLEDGE-SOURCE/{DATABASE,SCHEMAS,WORKFLOWS,TEST}/*`, `README.md` (WP-002)
- `product.manifest.json` — additive `implementation_status` entry (WP-003)
- `ENGINEERING/MWO/MWO-LTSA-040A-Completion-Report.md` (WP-004)
- No change to `seal_engineering_document`, `AI5R-SDK/KNOWLEDGE/*`, `REGISTRIES/*.json`, or `ENGINEERING/RUNTIME/`.

## Acceptance Criteria

- `knowledge_source_registry` is additive; nothing existing in `CANONICAL_SCHEMA.sql` is altered.
- The build pack matches `BP-SEAL`'s file shape (DATABASE/README/SCHEMAS/WORKFLOWS/TEST), minus a Delete workflow/test, by design.
- `knowledge_source_id` is never updatable; no Delete operation exists anywhere in the build pack.
- `seal_engineering_document` and `AI5R-SDK/KNOWLEDGE/*` show zero diff in `git status`.
- Structural Validation passes for every new file; Runtime Verification's standing blocker is stated, not hidden.

## Definition of Done

- WP-000's Architecture Decision recorded and treated as approved (met by this document).
- WP-001–WP-003 complete, each additive only, no out-of-scope file touched (verified via `git status`, not assumed).
- WP-004's Structural Validation stated PASS/WARNING/BLOCKER per work package; Completion Report exists.
- Nothing committed or pushed without separate, explicit approval.

---

This document, together with the new build pack and schema addition, is being produced per the Chief Architect's explicit "Implementation may proceed" instruction. Commit and push remain separate, later approvals, per Engineering Standard v1.0 §10/§11.
