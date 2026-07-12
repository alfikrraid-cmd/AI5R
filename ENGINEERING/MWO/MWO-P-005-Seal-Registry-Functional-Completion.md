# MWO-P-005 — Seal Registry Functional Completion

Status: DRAFT — WORK ORDER ONLY, NO IMPLEMENTATION PERFORMED
Type: Manufacturing Work Order (Feature Completion)
Role: Implementation Engineer
Architecture: FROZEN — no new architecture, service, table, or framework proposed
Foundation: v1.0 — LOCKED, unchanged by this MWO
Engineering Standard: v1.0 — LOCKED, unchanged by this MWO; this MWO is drafted in direct compliance with it (see §5, §6, §8, §12 citations throughout)
Phase: LTSA Production Sprint 02
Basis: `ENGINEERING/MWO/MWO-P-001-LTSA-Product-Audit.md`, `ENGINEERING/MWO/MWO-P-003-Customer-Registry-Functional-Completion.md` + reports, `ENGINEERING/MWO/MWO-P-004-Pump-Registry-Functional-Completion.md` + reports, `ENGINEERING/AI5R_ENGINEERING_STANDARD_v1.0.md` — no new audit scope opened
Scope: `PRODUCTS/LTSA-BRAIN` Seal Registry artifacts only

---

## Executive Summary

Per `MWO-P-001-LTSA-Product-Audit.md` §2–3 and the Sprint 01 Checkpoint Report, Seal Registry's database schema (`seal_registry`) is internally consistent and already mirrored in `DATABASE/CANONICAL_SCHEMA.sql`, but all 5 of its workflows (`BUILD-PACKS/BP-SEAL/WORKFLOWS/*.json`) remain non-functional static-response stubs — 0 of 5 operations have real logic. This MWO completes all 5 using the validated pattern proven in MWO-P-003 (Customer Registry) and MWO-P-004 (Pump Registry).

**Evidence gathered while drafting this MWO surfaces a structural difference from both prior feature-completion MWOs, worth stating up front:** Seal Registry has **no duplicate implementation location.** A repository-wide search found Seal artifacts in exactly one place (`BUILD-PACKS/BP-SEAL/`); no second build pack, no `MODULES/SEAL/` directory, and no `BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/` entry exists for Seal. Direct read of all 5 `BP-SEAL/WORKFLOWS/*.json` files' embedded `settings.registry` metadata confirms each already targets the correct table (`seal_registry`) and the correct field set, exactly matching `BP-SEAL/DATABASE/001_create_table.sql` and `REGISTRIES/SEAL.json` — unlike Pump, where the equivalent metadata revealed a schema mismatch. **Seal Registry's problem is purely that its logic is missing, not that its target is wrong or duplicated.** WP-000 must formally confirm this, but if confirmed, the canonicalization outcome is: one canonical location per operation, the existing `BP-SEAL` file, completed **in place** — not superseded by a new file with the old one marked deprecated, since there is nothing duplicate to deprecate.

---

## Objective

Complete Seal Registry using the validated engineering process from MWO-P-003 and MWO-P-004: a mandatory WP-000 canonicalization gate, followed by real, schema-correct, credentialed implementation of all 5 operations, using only patterns already proven in this product.

---

## Scope

- `BUILD-PACKS/BP-SEAL/WORKFLOWS/WF-LTSA-BRAIN-SEAL-{CREATE,DETAIL,LIST,UPDATE,DELETE}-001.json` — completed in place, pending WP-000 confirmation that no duplicate location exists (see Executive Summary).
- Structural Validation only, per Engineering Standard v1.0 §8 — no test scripts, no live n8n or database interaction of any kind.

## Out of Scope

- Customer Registry, Pump Registry, Asset, Inspection, Maintenance, Equipment — untouched.
- Authentication, Authorization — not introduced (existing credential-reference pattern only).
- Packaging, Deployment, Release tagging — not addressed.
- **All OpenAPI / API specification work.** `BUILD-PACKS/BP-SEAL/SCHEMAS/seal.openapi.json` (confirmed by direct read to be an empty generic stub, `{"SEAL": {"type": "object"}}`, carrying no real field information) is not modified. Per Engineering Standard v1.0 and the precedent set in MWO-P-004, API specification work is deferred to a dedicated future API Freeze MWO.
- Runtime Verification of any kind — live n8n execution, database verification, response verification, integration verification. Structural Validation only, per Engineering Standard v1.0 §8.
- UI — no Seal UI exists anywhere in the product; none is created.
- Governance, Constitution, README, Foundation, Engineering Standard — untouched. Both are locked per Chief Architect instruction; this MWO introduces no new engineering concept.

## Dependencies

- **MWO-P-002 (commit `5e349cd`)** — this MWO depends on IR-001's mirroring of `seal_registry` into `DATABASE/CANONICAL_SCHEMA.sql` and IR-003's credential resolution (`hzgFaX04t1nL01vF` / `"Postgres account"`). Both are treated as settled, not re-litigated.
- **MWO-P-003 and MWO-P-004 pattern precedent** — the validate → check/act → respond node chain, genuine `$1..$N` positional query parameterization (per Engineering Standard v1.0 §6, the corrected pattern, not the vestigial `queryReplacement`-plus-interpolation combination still latent in the product's oldest real Pump workflows), and the `{success, message, data}` / `{success, message, count, data}` response envelope are reused as-is. No new node type, pattern, or envelope shape is introduced, per Engineering Standard v1.0 §2.
- **Runtime Verification, generally** — not performed here, same as MWO-P-004. Per Engineering Standard v1.0 §17, establishing a working Runtime Verification capability remains the sprint's standing top recommendation; this MWO does not resolve it and does not depend on it being available for its own (Structural-Validation-only) scope.

## Constraints

- Architecture is frozen — no new table, service, credential mechanism, or framework. Foundation v1.0 and Engineering Standard v1.0 are locked and unmodified by this MWO.
- No new engineering concept, pattern, or convention is introduced — every implementation decision below cites the specific MWO-P-003 or MWO-P-004 precedent it reuses.
- No governance work.
- No OpenAPI or API specification work of any kind.
- No implementation outside Seal Registry.
- **Structural Validation only** (Engineering Standard v1.0 §8) — JSON validation, node graph validation, canonical validation, and static review are in scope; live n8n execution, database verification, response verification, and integration verification are out of scope in their entirety.
- **Canonical Mapping Lock** (Engineering Standard v1.0 §6): once WP-000 formally confirms the canonical mapping, it is frozen for the remainder of this MWO. No canonical decision may change during implementation. If contradictory evidence appears during implementation: STOP. Document the evidence. Recommend a new MWO. Wait for approval. Do not continue implementation.
- **Out-of-scope findings are documented, not fixed** (Engineering Standard v1.0 §2) — any unrelated problem discovered during this MWO is recorded in the relevant report and left untouched.

### Execution Rules (approval granularity, stated explicitly per Engineering Standard v1.0 §5 / §17)

This MWO uses **two different approval granularities for its two phases**, declared here up front rather than left implicit:

1. **WP-000 requires its own individual approval.** Implementation of WP-001–WP-005 may not begin until WP-000's Canonical Mapping is confirmed and separately approved.
2. **WP-001 through WP-005 execute as a single batch, without stopping between them, once WP-000 is approved.** No individual work-package report is produced for WP-001–WP-005 unless a BLOCKER occurs in one of them — in which case that specific work package's report is produced and implementation of the remaining batch stops pending review, per Engineering Standard v1.0 §5's implement→validate→report→stop→wait sequence.
3. **One Completion Report is produced after the full batch (WP-001–WP-005) completes**, covering all five operations together.
4. Nothing is committed or pushed without separate, explicit approval for each, per Engineering Standard v1.0 §10–§11.

---

## WP-000 — Seal Registry Canonicalization

**Responsibility:** Determine the canonical implementation for every Seal operation, lock the canonical mapping, and produce a Canonicalization Report — per Engineering Standard v1.0 §6, in full, before any implementation work package may begin.

**Preliminary findings (gathered during MWO drafting; WP-000 execution must formally confirm and lock these, not merely restate them):**

| Location | Contains | Schema targeted |
|---|---|---|
| `BUILD-PACKS/BP-SEAL/WORKFLOWS/` | All five ops (Create, Detail, List, Update, Delete) as static-response stubs | `seal_registry` (canonical — matches `DATABASE/CANONICAL_SCHEMA.sql` exactly) |

No second location exists. Direct read of all five `BP-SEAL/WORKFLOWS/*.json` files confirms each carries identical `settings.registry` metadata (`"table": "seal_registry"`, `"primary_key": "seal_code"`, fields `seal_code, seal_name, manufacturer, model, shaft_size, material, temperature_limit, pressure_limit, status`) that matches `BP-SEAL/DATABASE/001_create_table.sql` and `REGISTRIES/SEAL.json` field-for-field. `seal_code` is the schema's actual `PRIMARY KEY` column (a `TEXT` key, not a separate UUID surrogate `id` with a distinct business key, unlike `customer_registry`/`ltsa_pumps`) — so no identifier-convention ambiguity exists for Detail/Update/Delete: `seal_code` is the only candidate and the correct one.

**Proposed Canonical Mapping Table:**

| Operation | Canonical | Deprecated | Status |
|---|---|---|---|
| Create | `BUILD-PACKS/BP-SEAL/WORKFLOWS/WF-LTSA-BRAIN-SEAL-CREATE-001.json` | *(none — no duplicate exists)* | Incomplete — WP-001, completed in place |
| Detail | `BUILD-PACKS/BP-SEAL/WORKFLOWS/WF-LTSA-BRAIN-SEAL-DETAIL-001.json` | *(none — no duplicate exists)* | Incomplete — WP-002, completed in place |
| List | `BUILD-PACKS/BP-SEAL/WORKFLOWS/WF-LTSA-BRAIN-SEAL-LIST-001.json` | *(none — no duplicate exists)* | Incomplete — WP-003, completed in place |
| Update | `BUILD-PACKS/BP-SEAL/WORKFLOWS/WF-LTSA-BRAIN-SEAL-UPDATE-001.json` | *(none — no duplicate exists)* | Incomplete — WP-004, completed in place |
| Delete | `BUILD-PACKS/BP-SEAL/WORKFLOWS/WF-LTSA-BRAIN-SEAL-DELETE-001.json` | *(none — no duplicate exists)* | Incomplete — WP-005, completed in place |

**Canonical database object:** `seal_registry` (`BUILD-PACKS/BP-SEAL/DATABASE/001_create_table.sql`, mirrored in `DATABASE/CANONICAL_SCHEMA.sql`) — already canonical per IR-001 ("for completeness, no conflict existed"); WP-000 confirms and inherits this, does not re-derive it.

**Canonical API (identification only — no file modified):** No real API specification exists for Seal — `BP-SEAL/SCHEMAS/seal.openapi.json` is an empty generic stub. This identification is recorded for reference only; per Out of Scope, no API specification file is modified by this MWO.

**Deliverables:** Seal Registry Canonical Map (table above, to be formally confirmed by WP-000 execution — not implementation), recorded in a Canonicalization Report.

**Acceptance Criteria:**
- Every Seal Registry workflow artifact is identified (confirmed: exactly 5, one location).
- Confirmation of whether a duplicate implementation exists (preliminary finding: none does — WP-000 must verify this negative finding with the same rigor as a positive one).
- Exactly one canonical implementation path exists for each operation.
- Canonical database object and canonical API confirmed and inherited, not re-derived.

**Lock:** Once confirmed, this map is locked for the remainder of MWO-P-005, per the Canonical Mapping Lock under Constraints.

---

## WP-001 — Seal Create

**Objective:** Implement real create logic, replacing the static-response stub in place.

**Scope:** `BUILD-PACKS/BP-SEAL/WORKFLOWS/WF-LTSA-BRAIN-SEAL-CREATE-001.json`, edited in place (no new file, no deprecation marking — WP-000 found nothing to supersede): webhook (path unchanged, `ltsa/seal/create`) → validate input (`seal_code`, `seal_name` required, matching the schema's `NOT NULL` columns; remaining fields — `manufacturer, model, shaft_size, material, temperature_limit, pressure_limit, status` — optional) → conflict check on `seal_code` (reusing MWO-P-003 WP-001's pre-insert-existence-check pattern, since `seal_code` is `PRIMARY KEY`, the same uniqueness-conflict class Customer Registry's `customer_code` required) → parameterized `INSERT ... RETURNING *` → 201/409 response.

**Deliverables:** Functional `WF-LTSA-BRAIN-SEAL-CREATE-001.json`.

**Acceptance Criteria:**
- Valid payload creates one row with correctly mapped fields.
- Missing `seal_code` or `seal_name` is rejected; no row created.
- Duplicate `seal_code` returns a defined conflict response, not a silent failure or unhandled DB error.
- Uses only the existing resolved credential.

**Required Validation (Structural Validation only):** JSON validation, node graph validation, canonical validation, static review of the query and field list against `001_create_table.sql`.

**Known Risks:** None beyond the standing, sprint-wide absence of Runtime Verification (Engineering Standard v1.0 §8, §17).

---

## WP-002 — Seal Detail

**Objective:** Implement real single-record retrieval, replacing the static-response stub in place.

**Scope:** `BUILD-PACKS/BP-SEAL/WORKFLOWS/WF-LTSA-BRAIN-SEAL-DETAIL-001.json`, edited in place: webhook (path unchanged, `ltsa/seal/detail`) → parse `seal_code` from query parameter (reusing the query-parameter-parsing pattern established for Pump Detail/Delete, adapted to the field name this schema actually uses) → validate presence → parameterized `SELECT * FROM seal_registry WHERE seal_code = $1` → 200/404 response.

**Deliverables:** Functional `WF-LTSA-BRAIN-SEAL-DETAIL-001.json`.

**Acceptance Criteria:**
- Known `seal_code` returns the correct, full record.
- Unknown `seal_code` returns a defined 404.
- Missing query parameter returns a defined 400.

**Required Validation (Structural Validation only):** Same four categories as WP-001.

**Known Risks:** None beyond the standing absence of Runtime Verification.

---

## WP-003 — Seal List

**Objective:** Implement real list logic, replacing the static-response stub in place.

**Scope:** `BUILD-PACKS/BP-SEAL/WORKFLOWS/WF-LTSA-BRAIN-SEAL-LIST-001.json`, edited in place: webhook (path unchanged, `ltsa/seal/list`) → `SELECT * FROM seal_registry ORDER BY created_at DESC;` → response. No filter/parameter added — no documentation specifies one, and Engineering Standard v1.0 §2 forbids inventing capability beyond approved scope.

**Deliverables:** Functional `WF-LTSA-BRAIN-SEAL-LIST-001.json`.

**Acceptance Criteria:**
- Returns all `seal_registry` rows in the established response envelope.
- Empty table returns an empty list, not an error.

**Required Validation (Structural Validation only):** Same four categories as WP-001.

**Known Risks:** None beyond the standing absence of Runtime Verification.

---

## WP-004 — Seal Update

**Objective:** Implement real update logic, replacing the static-response stub in place.

**Scope:** `BUILD-PACKS/BP-SEAL/WORKFLOWS/WF-LTSA-BRAIN-SEAL-UPDATE-001.json`, edited in place: webhook (path unchanged, `ltsa/seal/update`) → validate (`seal_code` required as identifier; accepts any subset of the remaining editable columns: `seal_name, manufacturer, model, shaft_size, material, temperature_limit, pressure_limit, status`) → dynamically-built parameterized `UPDATE ... WHERE seal_code = $N RETURNING *` (reusing MWO-P-003 WP-004 / MWO-P-004 WP-002's dynamic partial-update pattern exactly) → 200/404 response.

**Deliverables:** Functional `WF-LTSA-BRAIN-SEAL-UPDATE-001.json`.

**Acceptance Criteria:**
- Valid update modifies only the targeted row's specified fields; other rows unaffected.
- Unknown `seal_code` returns a defined 404; no row created as a side effect.

**Required Validation (Structural Validation only):** Same four categories as WP-001, plus static review of the dynamic parameter-ordering logic (the same class of review MWO-P-004 WP-002 applied).

**Known Risks:** Dynamic query construction is the same code class where MWO-P-003 previously found a real, self-corrected defect through static reading alone (Engineering Standard v1.0 §7, §16) — that standard of review applies here. No other risk beyond the standing absence of Runtime Verification.

---

## WP-005 — Seal Delete

**Objective:** Implement real delete logic, replacing the static-response stub in place.

**Scope:** `BUILD-PACKS/BP-SEAL/WORKFLOWS/WF-LTSA-BRAIN-SEAL-DELETE-001.json`, edited in place: webhook (path unchanged, `ltsa/seal/delete`) → parse and validate `seal_code` from query parameter → parameterized `DELETE FROM seal_registry WHERE seal_code = $1 RETURNING *` → 200/404 response.

**Deliverables:** Functional `WF-LTSA-BRAIN-SEAL-DELETE-001.json`.

**Acceptance Criteria:**
- Existing record is removed; a subsequent Detail lookup against the same `seal_code` returns 404.
- Unknown `seal_code` returns a defined 404, not an error or crash.

**Required Validation (Structural Validation only):** Same four categories as WP-001.

**Known Risks:** No downstream consumer of Seal data currently exists as a real artifact anywhere in the product (confirmed in `MWO-P-001`), so no referential-integrity concern is active today — noted for completeness, consistent with the equivalent note in MWO-P-004 WP-003, not re-derived as a new finding.

---

## Execution Order

WP-000 (Canonicalization, individually approved) → **[approval]** → WP-001 (Create) → WP-002 (Detail) → WP-003 (List) → WP-004 (Update) → WP-005 (Delete), executed as one continuous batch per the Execution Rules above → **[Completion Report, then stop]**.

Rationale: WP-000 must complete and lock the map before any file is touched, per Engineering Standard v1.0 §6. Because every operation is completed in place (no new file to seed as a test fixture, and no cross-operation dependency exists among Create/Detail/List/Update/Delete beyond what static review can confirm), there is no technical requirement for individual gates between WP-001–WP-005, consistent with the batching precedent already proven in MWO-P-003.

## Expected Deliverables

- 1 Seal Registry Canonical Map (WP-000), confirming no duplicate implementation exists.
- 5 `BP-SEAL/WORKFLOWS/*.json` files completed in place with real logic (no new files, no deprecation markings — nothing superseded).
- No OpenAPI or API specification change.
- No test scripts, no Runtime Verification artifacts of any kind.

## Expected Reports

- `SM-000-Canonicalization-Report.md` ("SM" for Seal Module, consistent with the `PM`/Pump Module convention established in MWO-P-004 and the Engineering Standard v1.0 §12 rule that the prefix `PR` must never be used).
- One `MWO-P-005-Completion-Report.md`, covering WP-001–WP-005 together, produced after the full batch completes.
- Individual work-package reports for WP-001–WP-005 are produced **only if a BLOCKER occurs** in one of them, per the Execution Rules above.

## Definition of Done

- WP-000's Canonical Map formally confirmed, locked, and individually approved before WP-001 begins.
- All five Seal operations have real, structurally-validated logic, completed in the single existing file per operation — no duplicate created, none needed.
- No OpenAPI or API specification file modified by this MWO.
- Structural Validation complete for all five workflows; Runtime Verification explicitly not attempted and not claimed.
- No file outside Seal Registry scope touched.
- **The canonical mapping remained unchanged throughout implementation.**
- No per-work-package report produced for WP-001–WP-005 unless a BLOCKER occurred.
- Nothing committed or pushed without explicit Chief Architect approval.

---

This document has been created per Chief Architect instruction, in Document Drafting Mode (Engineering Standard v1.0 §13). Implementation has not started. No repository file other than this MWO document was modified in producing it. No commit, no push.
