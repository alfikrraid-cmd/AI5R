# MWO-P-004 — Pump Registry Functional Completion

Status: WP-000 COMPLETE — AWAITING CHIEF ARCHITECT APPROVAL TO PROCEED TO WP-001. See `PM-000-Canonicalization-Report.md`.
Type: Manufacturing Work Order (Feature Completion)
Role: Implementation Engineer
Architecture: FROZEN — no new architecture, service, table, or framework proposed
Phase: LTSA Production Sprint 01
Basis: `ENGINEERING/MWO/MWO-P-001-LTSA-Product-Audit.md`, `ENGINEERING/MWO/LTSA-Integrity-Recovery-Summary.md` (+ `IR-001`, `IR-002`, `IR-003`), `ENGINEERING/MWO/MWO-P-003-Customer-Registry-Functional-Completion.md`, `ENGINEERING/MWO/MWO-P-003-Implementation-Summary.md`, Sprint 01 Checkpoint Report — no new audit scope opened
Scope: `PRODUCTS/LTSA-BRAIN` Pump Registry artifacts only
Revision Note: Revised per Chief Architecture Review — OpenAPI work removed (deferred to a dedicated API Freeze MWO), validation split into Structural Validation (in scope) and Runtime Verification (out of scope), work package reports renamed `PM-000`–`PM-003`, a permanent Canonical Mapping Lock rule added, and a Definition of Done item added confirming the mapping stayed unchanged.

---

## # Executive Summary

Per the Sprint 01 Checkpoint Report (§3), Pump Registry is rated PARTIAL: 2 of 5 operations (Create, Detail) are real, credentialed, and schema-correct as of MWO-P-002. The remaining 3 (List, Update, Delete) exist only as static-response stubs in `BUILD-PACKS/BP-PUMP`. Evidence gathered while drafting this MWO (direct read of all 5 `BP-PUMP/WORKFLOWS/*.json` files and their embedded `settings.registry` metadata) confirms all five `BP-PUMP` stub workflows — including the two whose operations are already complete elsewhere — target the `pump_registry`/`pump_code` schema, which IR-001 already marked `DEPRECATED` at the database level. They are not just non-functional; they are non-functional against a table that no longer has canonical status. This MWO completes List, Update, and Delete against the canonical `ltsa_pumps` schema only, following the WP-000-first, one-canonical-implementation pattern MWO-P-003 established for Customer Registry. Create and Detail are excluded — they are already done. This MWO produces Structural Validation only; Runtime Verification (live n8n execution, database verification) is explicitly out of scope and deferred.

---

## # Objective

Replace the three remaining non-functional Pump Registry operations (List, Update, Delete) with real, canonical-schema-backed implementations, reusing the patterns already proven in `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-REGISTRY-001.json` (Create), `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-PUMP-DETAIL-001.json` (Detail), and the Customer Registry work packages completed under MWO-P-003.

---

## # Scope

- `MODULES/PUMP/WORKFLOWS/` — new canonical files for List, Update, Delete (this directory currently holds only Create; it is the product's only existing home for real, canonical-schema-aligned Pump logic, so it is where the new canonical files belong — not a new location, not a new pattern).
- `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-{LIST,UPDATE,DELETE}-001.json` — marked `DEPRECATED` in place (JSON metadata convention, as used in MWO-P-003), not deleted.
- `MODULES/PUMP/API/openapi.yaml` — **Deferred to API Freeze MWO.** Not modified by this MWO.
- Structural Validation only (see §2 revision) — no test scripts, no live database or n8n interaction of any kind.

## # Out of Scope

- **Create and Detail** — already complete (real, credentialed, schema-correct); no file for either operation may be touched by this MWO.
- **Consolidating `BUILD-PACKS/BP-PUMP` as a whole build pack** (its README, SCHEMAS, remaining non-workflow files) — only the three workflow files and the three already-deprecated database files it contains are referenced by this MWO; the build pack itself is not being retired or restructured.
- **All OpenAPI / API specification work.** `MODULES/PUMP/API/openapi.yaml` and every other API specification file are not modified. Deferred to a dedicated future API Freeze MWO.
- **Runtime Verification of any kind** — live n8n execution, PostgreSQL verification, response verification, integration verification. Out of scope for this MWO (see §2 revision). No test script authoring or execution occurs under this MWO.
- Customer Registry, Seal Registry, Asset, Inspection, Maintenance, Equipment — untouched.
- Authentication, Authorization — not introduced (n8n's existing credential-reference pattern only, same constraint as MWO-P-002/P-003).
- Packaging, Deployment, Release tagging — not addressed.
- UI — the two `PumpRegistryPage.tsx`/`PumpDetailPage.tsx` files remain untouched.
- Governance, Constitution, README — untouched, per standing instruction.

## # Dependencies

- **MWO-P-002 (commit `5e349cd`)** — this MWO depends entirely on IR-001's canonical designation of `ltsa_pumps` (`MODULES/PUMP/DATABASE/001_create_pumps.sql`) and IR-003's credential resolution (`hzgFaX04t1nL01vF` / `"Postgres account"`). Both are treated as settled, not re-litigated.
- **MWO-P-003 pattern precedent** — the validate → check → act → respond node chain and `$1`-positional-parameterized `executeQuery` pattern (corrected mid-MWO-P-003 from a vestigial `queryReplacement` usage) are reused as-is. No new node type or response envelope shape is introduced.
- **Runtime Verification, generally** — this MWO does not perform it and does not depend on it being available. A future MWO (candidate: Test Execution & Verification Infrastructure, per the Sprint 01 Checkpoint Report's §7 recommendation) will be required before any workflow produced here — or produced by MWO-P-003 — can be called verified rather than structurally sound.

## # Constraints

- Architecture is frozen — no new table, service, credential mechanism, or framework.
- No governance work. No modification to any Constitution document, README, or Engineering Governance material.
- No authentication. No authorization.
- No packaging. No deployment.
- **No OpenAPI or API specification work of any kind.** `MODULES/PUMP/API/openapi.yaml` is not modified. Every OpenAPI-shaped deliverable in this MWO reads: "Deferred to API Freeze MWO."
- No implementation outside Pump Registry.
- **Structural Validation only.** JSON validation, node graph validation, canonical validation, and static review are in scope. Live n8n execution, PostgreSQL verification, response verification, and integration verification (Runtime Verification) are out of scope for this MWO in their entirety.
- No new implementation pattern unless explicitly requested — reuse MWO-P-003's validate/check/act/respond and parameterized-query patterns exactly.

**Canonical Mapping Lock**

Once WP-000 formally confirms the canonical mapping, the mapping is frozen for the remainder of MWO-P-004.

No canonical decision may change during implementation.

If contradictory evidence appears during implementation:

STOP.

Document the evidence.

Recommend a new MWO.

Wait for approval.

Do not continue implementation.

---

## WP-000 — Pump Registry Canonicalization

**Responsibility:** identify duplicate implementations, identify canonical workflows, identify deprecated workflows, identify canonical API (identification/reporting only — no API specification file is modified by this or any other work package in this MWO), identify canonical database objects. No implementation of List/Update/Delete may begin before this work package is formally executed and its map confirmed.

**Preliminary findings (gathered during MWO drafting; WP-000 execution must formally confirm and lock these, not merely restate them):**

Three distinct locations hold Pump artifacts, not two as with Customer Registry:

| Location | Contains | Schema targeted |
|---|---|---|
| `MODULES/PUMP/WORKFLOWS/` | Create only (`WF-LTSA-PUMP-REGISTRY-001.json`) | `ltsa_pumps` (canonical) |
| `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/` | Detail only (`WF-LTSA-PUMP-DETAIL-001.json`) | `ltsa_pumps` (canonical) |
| `BUILD-PACKS/BP-PUMP/WORKFLOWS/` | All five ops (Create, Detail, List, Update, Delete) as static-response stubs | `pump_registry` (already `DEPRECATED` — IR-001) |

Direct read of all five `BP-PUMP/WORKFLOWS/*.json` files confirms each carries identical `settings.registry` metadata: `"table": "pump_registry"`, `"primary_key": "pump_code"`, fields `pump_code, pump_name, manufacturer, model, serial_number, location, status` — a different table, different primary key type, and a different field set than canonical `ltsa_pumps` (`tag_number, area, location, pump_type, api_plan, seal_type, status, manufacturer, model, drawing_ref, notes`). `BP-PUMP/README.md` independently confirms "Table: pump_registry, Primary Key: pump_code." `BP-PUMP/SCHEMAS/pump.openapi.json` is an empty generic stub (`"PUMP": {"type": "object"}`) with no real field information at all. All four `BP-PUMP/DATABASE/*.sql` files already carry `DEPRECATED (MWO-P-002 / IR-001)` headers, confirmed by direct read.

**Status: CONFIRMED AND LOCKED.** WP-000 has been formally executed. Full method, artifact inventory, and rationale recorded in `ENGINEERING/MWO/PM-000-Canonicalization-Report.md`.

**Pump Registry Canonical Map (locked):**

| Operation | Canonical | Deprecated | Status |
|---|---|---|---|
| Create | `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-REGISTRY-001.json` | `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-CREATE-001.json` | **Already complete — not touched by this MWO, including its deprecated counterpart** |
| Detail | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-PUMP-DETAIL-001.json` | `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-DETAIL-001.json` | **Already complete — not touched by this MWO, including its deprecated counterpart** |
| List | `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-LIST-001.json` *(new)* | `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-LIST-001.json` | Incomplete — WP-001 |
| Update | `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-UPDATE-001.json` *(new)* | `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-UPDATE-001.json` | Incomplete — WP-002 |
| Delete | `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-DELETE-001.json` *(new)* | `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-DELETE-001.json` | Incomplete — WP-003 |

**Canonical database object:** `ltsa_pumps` (`MODULES/PUMP/DATABASE/001_create_pumps.sql`, mirrored in `DATABASE/CANONICAL_SCHEMA.sql`) — already canonicalized by IR-001; confirmed and inherited, not re-derived. Deprecated: `RELEASE/database.sql`'s `ltsa_pumps` (SERIAL) block and all of `BUILD-PACKS/BP-PUMP/DATABASE/*.sql` (`pump_registry`) — both already marked, not deleted.

**Canonical API (identification only — no file modified):** `MODULES/PUMP/API/openapi.yaml` is the only Pump API spec with real, schema-correct field definitions; `BUILD-PACKS/BP-PUMP/SCHEMAS/pump.openapi.json` is deprecated-adjacent by the same reasoning as its workflows. Recorded for reference only — deferred to the API Freeze MWO, not actioned here.

**Deliverables:** Pump Registry Canonical Map — **confirmed** (see `PM-000-Canonicalization-Report.md`).

**Acceptance Criteria:**
- Exactly one canonical implementation exists for each of List, Update, Delete. — **Met.**
- Create and Detail are confirmed already-canonical and excluded from further action. — **Met.**
- No duplicate implementation remains active. — **Met** (none activated; List/Update/Delete's deprecated files to be marked in WP-001–WP-003).
- Deprecated artifacts are identified but not removed. — **Met.**

**Known gap outside this MWO's authority (documented, not actioned):** `BP-PUMP`'s Create and Detail stub workflows remain entirely unmarked (no `DEPRECATED` metadata), unlike their already-marked `DATABASE/*.sql` counterparts. Out of this MWO's approved scope; recommended for a future MWO. See `PM-000-Canonicalization-Report.md` for detail.

**Lock:** See Canonical Mapping Lock under Constraints. This map is now locked for the remainder of MWO-P-004.

---

## WP-001 — Pump List

**Objective:** Implement real list logic for Pump Registry, replacing the non-functional `BP-PUMP` stub.

**Scope:** New file `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-LIST-001.json`: webhook → `SELECT * FROM ltsa_pumps ORDER BY created_at DESC;` → response, reusing MWO-P-003 WP-003's List pattern exactly (no filter/parameter beyond what's already implied by the module — `MODULES/PUMP/DOCS/PUMP_REGISTRY_SPEC.md` documents no list parameters). `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-LIST-001.json` marked `DEPRECATED` in place.

**Deliverables:**
- New canonical List workflow.
- Deprecated BP-PUMP List file marked, not deleted.
- OpenAPI documentation: **Deferred to API Freeze MWO.**

**Acceptance Criteria:**
- Returns all `ltsa_pumps` rows in a response shape consistent with the Create/Detail workflows' existing envelope.
- Empty table returns an empty list, not an error, at the code level (verified by static review, not execution).
- Uses only the existing resolved credential (`hzgFaX04t1nL01vF`).
- Deprecated BP-PUMP List file marked, not deleted.

**Required Validation (Structural Validation only):**
- JSON validation — the new and marked-deprecated files parse as valid JSON.
- Node graph validation — every node reachable, every branch (if any) terminates in a response node.
- Canonical validation — implemented into the file WP-000's map designates canonical for List, and no other.
- Static review — the query text and field list are manually checked against `MODULES/PUMP/DATABASE/001_create_pumps.sql`'s actual columns.

**Runtime Verification:** Out of scope for this MWO. No live execution, no database connection, no test script authored or run.

**Known Risks:** Without Runtime Verification, this work package cannot claim the workflow actually functions against a live database — only that it is structurally sound and schema-consistent by static review. This is a deliberate, approved scope limitation, not an oversight. This is the simplest of the three remaining operations and has a direct, already-proven structural precedent (Customer Registry's List workflow, MWO-P-003 WP-003).

---

## WP-002 — Pump Update

**Objective:** Implement real update logic for Pump Registry, replacing the non-functional `BP-PUMP` stub.

**Scope:** New file `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-UPDATE-001.json`, reusing MWO-P-003 WP-004's Update pattern: webhook → validate (requires `tag_number` as the identifier — `tag_number` is `ltsa_pumps`'s `NOT NULL UNIQUE` business key, confirmed by direct read of `001_create_pumps.sql`; accepts any subset of the remaining editable columns: `area, location, pump_type, api_plan, seal_type, status, manufacturer, model, drawing_ref, notes`) → dynamically-built parameterized `UPDATE ... WHERE tag_number = $N RETURNING *` → 200/404 response. `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-UPDATE-001.json` marked `DEPRECATED` in place.

**Deliverables:**
- New canonical Update workflow.
- Deprecated BP-PUMP Update file marked, not deleted.
- OpenAPI documentation: **Deferred to API Freeze MWO.**

**Acceptance Criteria:**
- Valid update modifies only the targeted row's specified fields; other rows unaffected (verified by static review of the generated query, not execution).
- Unknown `tag_number` results in zero rows affected by construction (`WHERE tag_number = $N`, no fallback insert path) — verified by static review.
- Uses only the existing resolved credential.

**Required Validation (Structural Validation only):**
- JSON validation, node graph validation, canonical validation, static review — same four categories as WP-001, applied to the Update workflow's dynamic `SET`-clause construction and parameter ordering.

**Runtime Verification:** Out of scope for this MWO. No live execution, no database connection, no test script authored or run.

**Known Risks:** Identifying by `tag_number` (a business key) rather than a surrogate `id` is a deliberate deviation from Customer Registry's Update (which used `id`) — justified because `PUMP_REGISTRY_SPEC.md` and every real Pump workflow (Create's validation, Detail's lookup) already key on `tag_number`, not `id`; using `id` here would be inconsistent with the module's own established convention. This must be confirmed, not assumed, during WP-000 execution. Without Runtime Verification, the dynamic query-building logic's correctness rests on static review only — the same class of latent defect MWO-P-003 found (and fixed) in its own first draft was only caught by careful reading, not execution; static review here must be held to that same standard.

---

## WP-003 — Pump Delete

**Objective:** Implement real delete logic for Pump Registry, replacing the non-functional `BP-PUMP` stub.

**Scope:** New file `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-DELETE-001.json`, reusing MWO-P-003 WP-005's Delete pattern: webhook → validate `tag_number` → parameterized `DELETE FROM ltsa_pumps WHERE tag_number = $1 RETURNING *` → 200/404 response. `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-DELETE-001.json` marked `DEPRECATED` in place.

**Deliverables:**
- New canonical Delete workflow.
- Deprecated BP-PUMP Delete file marked, not deleted.
- OpenAPI documentation: **Deferred to API Freeze MWO.**

**Acceptance Criteria:**
- Delete targets exactly one row by `tag_number`, by construction (`WHERE tag_number = $1`) — verified by static review.
- Unknown `tag_number` results in zero rows affected, not an error, by construction — verified by static review.

**Required Validation (Structural Validation only):**
- JSON validation, node graph validation, canonical validation, static review — same four categories as WP-001/WP-002.

**Runtime Verification:** Out of scope for this MWO. No live execution, no database connection, no test script authored or run.

**Known Risks:** `PUMP_REGISTRY_SPEC.md` states the pump module is "Used By: Seal Registry, PM Planner, CM Work Order, Inspection History, Billing Report" — none of which currently exist as real consumers (confirmed: Seal has no real workflows, and PM Planner/CM Work Order/Billing Report have no artifacts anywhere in the product per MWO-P-001). Delete therefore has no real downstream referential-integrity concern *today*, but this should be re-checked if any of those modules are ever built — noted here so it is not silently forgotten. As with WP-001/WP-002, correctness rests entirely on static review in the absence of Runtime Verification.

---

## # Execution Order

WP-000 (Canonicalization, mandatory first) → WP-001 (List) → WP-002 (Update) → WP-003 (Delete).

Rationale: WP-000 must complete and lock the map before any file is touched. List, Update, and Delete have no interdependency on each other's new code (Create already exists and is real, so no fixture-seeding order is required as it was for Customer Registry). This order is a reasonable default, not a hard technical requirement.

## # Expected Deliverables

- 3 new canonical workflow files under `MODULES/PUMP/WORKFLOWS/` (List, Update, Delete)
- 3 deprecated `BP-PUMP` workflow files marked in place (not deleted)
- 1 Pump Registry Canonical Map (WP-000)
- OpenAPI documentation: **Deferred to API Freeze MWO** (no `MODULES/PUMP/API/openapi.yaml` change under this MWO)
- No test scripts, no Runtime Verification artifacts of any kind

## # Expected Reports

One report per work package: `PM-000` (Canonicalization), `PM-001` (List), `PM-002` (Update), `PM-003` (Delete) — "PM" for Pump Module, chosen specifically to avoid collision with Pull Request terminology. Plus one `MWO-P-004-Implementation-Summary.md` on completion, mirroring MWO-P-003's structure.

## # Definition of Done

- WP-000's Canonical Map formally confirmed and locked before any other WP begins.
- List, Update, Delete each have exactly one canonical implementation, structurally validated; their `BP-PUMP` counterparts marked `DEPRECATED`, not deleted.
- Create and Detail remain untouched.
- No OpenAPI or API specification file modified by this MWO.
- Structural Validation complete for all three new workflows; Runtime Verification explicitly not attempted and not claimed.
- No file outside Pump Registry scope touched.
- **The canonical mapping remained unchanged throughout implementation.**
- Nothing committed or pushed without explicit Chief Architect approval.

---

This document has been revised per Chief Architecture Review. Implementation has not started. No repository file other than this MWO document was modified in producing this revision. No commit, no push.
