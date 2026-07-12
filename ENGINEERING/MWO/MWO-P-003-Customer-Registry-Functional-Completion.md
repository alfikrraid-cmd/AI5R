# MWO-P-003 — Customer Registry Functional Completion

Status: IMPLEMENTED — AWAITING REVIEW AND COMMIT DECISION. See `ENGINEERING/MWO/MWO-P-003-Implementation-Summary.md` and per-work-package reports `CR-000` through `CR-006`.
Type: Manufacturing Work Order (Feature Completion)
Role: Senior Software Engineer
Architecture: FROZEN — no new architecture, service, table, or framework proposed
Phase: LTSA Production Sprint 01
Parent / Basis: `ENGINEERING/MWO/MWO-P-001-LTSA-Product-Audit.md` (backlog items 006, 009) and `ENGINEERING/MWO/LTSA-Integrity-Recovery-Summary.md` (MWO-P-002) — no new audit scope opened
Scope: `PRODUCTS/LTSA-BRAIN` Customer Registry artifacts only

---

## Objective

Replace every Customer Registry workflow stub with fully functional implementations, reading and writing the canonical `customer_registry` schema established by MWO-P-002 (`DATABASE/MIGRATIONS/005_create_customer_registry.sql`, mirrored in `DATABASE/CANONICAL_SCHEMA.sql`).

This MWO is intentionally limited to Customer Registry only.

- Do not include Pump.
- Do not include Seal.
- Do not include Authentication.
- Do not include Packaging.
- Do not include API Freeze.

---

## Pre-Existing Condition (read before the work packages)

Per `MWO-P-001` §4/§5 and `LTSA-Integrity-Recovery-Summary.md` item 7/10, every Customer Registry operation currently exists as **two separate, non-functional artifacts** rather than one:

| Operation | Build-pack A (stub) | Build-pack B (empty shell) |
|---|---|---|
| Create | `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-CREATE-001.json` — webhook trigger only, no downstream node | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-CREATE-001.json` — `"nodes": []`, `"connections": {}` |
| Detail/Get | `.../BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-GET-001.json` — stub | `.../BP-007-.../OUTPUTS/WF-LTSA-CUSTOMER-DETAIL-001.json` — empty shell |
| List | `.../BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-LIST-001.json` — stub | `.../BP-007-.../OUTPUTS/WF-LTSA-CUSTOMER-LIST-001.json` — empty shell |
| Update | `.../BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-UPDATE-001.json` — stub | `.../BP-007-.../OUTPUTS/WF-LTSA-CUSTOMER-UPDATE-001.json` — empty shell |
| Delete | `.../BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-DELETE-001.json` — stub | `.../BP-007-.../OUTPUTS/WF-LTSA-CUSTOMER-DELETE-001.json` — empty shell |
| By Code | *(none)* | `.../BP-007-.../OUTPUTS/WF-LTSA-CUSTOMER-BY-CODE-001.json` — empty shell, **undocumented anywhere** (`IR-002-Workflow-Report.md`) |

Note the **Get/Detail naming divergence**: BP-005 calls this operation `GET`, BP-007 calls the same logical operation `DETAIL`. This was not previously flagged and must be resolved, not carried forward.

Each work package below (except WP-006) must therefore **consolidate its pair of pre-existing artifacts into one authoritative file**, marking the other `DEPRECATED` in place (not deleted) — the same pattern IR-001 already used for the `ltsa_pumps` / `pump_registry` duplication. This is reconciliation of existing artifacts, not new-feature design.

This table above is preliminary evidence only. **WP-000 below produces the authoritative Customer Registry Canonical Map.** WP-001–WP-006 must implement into the file WP-000 designates canonical for their operation and must not independently choose a canonical file outside that map.

**Canonical schema reference:** `customer_registry` (UUID PK, 14 columns, includes at minimum `customer_code`, `customer_name`, `customer_type`, `industry`, `billing_email`, `phone`, `city`, `province` per `MWO-P-001` §3 / `IR-001-Database-Report.md`). The full authoritative field list is `DATABASE/CANONICAL_SCHEMA.sql`; no work package below may query the deprecated `ltsa_customers` table (`RELEASE/database.sql`) — IR-001 explicitly flagged this as a forward-looking constraint for exactly this MWO.

**Credential reference:** the only real, resolved PostgreSQL credential in this product is `id: hzgFaX04t1nL01vF`, `name: "Postgres account"` (`IR-003-Credential-Report.md`). Every work package below must reuse this existing reference. No new credential ID, secret, or authentication mechanism may be introduced.

---

## Work Packages

### WP-000 — Customer Registry Canonicalization

**Objective:** Before implementing any Customer Registry workflow, identify the single canonical implementation location for each operation.

**Tasks:**
- Identify every Customer Registry workflow artifact (BP-005, BP-007, and any other location a Customer Registry workflow file exists).
- Compare the BP-005 and BP-007 implementations for each operation.
- Determine the canonical implementation target for each operation.
- Determine the deprecated implementation for each operation.
- Produce a canonical mapping table.

**Deliverables:** Customer Registry Canonical Map — one row per operation. Full method, artifact inventory, and rationale recorded in `ENGINEERING/MWO/CR-000-Canonicalization-Report.md`.

| Operation | Canonical | Deprecated |
|---|---|---|
| Create | `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-CREATE-001.json` | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-CREATE-001.json` |
| Detail (documented as `get`) | `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-GET-001.json` | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-DETAIL-001.json` |
| List | `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-LIST-001.json` | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-LIST-001.json` |
| Update | `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-UPDATE-001.json` | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-UPDATE-001.json` |
| Delete | `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-DELETE-001.json` | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-DELETE-001.json` |
| By Code | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-BY-CODE-001.json` | *(none — no BP-005 counterpart exists)* |

**Rationale (summary):** every BP-005 file already carries a live `Webhook` trigger node whose path matches `API_CONTRACT.md`/`README.md` exactly; every corresponding BP-007 file is `"nodes": []` — a generator-produced empty shell never wired to the documented contract. BP-005 is canonical for all five documented operations. The `GET`/`DETAIL` naming split is resolved in favor of `GET` (BP-005's name and path, already documented) — no rename performed. By Code has no BP-005 counterpart, so its sole BP-007 artifact is canonical by default. Full evidence in `CR-000-Canonicalization-Report.md`.

**Acceptance Criteria:**
- Exactly one canonical implementation exists for every operation. — **Met.**
- No duplicate implementation remains active. — **Met** (deprecated files marked as each canonical replacement is built in WP-001–WP-005; see their reports).
- Deprecated artifacts are identified but not removed. — **Met**, per the map above.

**Lock:** The Customer Registry Canonical Map above is locked for the remainder of this MWO. See Constraints — canonical decisions may not change during WP-001–WP-006.

---

### WP-001 — Customer Create

**Objective:** Implement real create logic, replacing the stub/empty-shell pair with one authoritative, database-backed workflow.

**Scope:** Implement into the file WP-000's Customer Registry Canonical Map designates canonical for Create: webhook trigger → input validation against the canonical schema's required fields → `INSERT INTO customer_registry (...) RETURNING *` → response, modeled on the existing real pattern in `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-REGISTRY-001.json`. Uses the existing resolved credential reference only.

**Deliverables:**
- The workflow file WP-000 designated canonical for Create, made functional.
- The workflow file WP-000 designated deprecated for Create, marked `DEPRECATED` in place, not deleted.
- A functional test (see Required Tests).

**Acceptance Criteria:**
- A valid payload creates one row in `customer_registry` with correctly mapped fields.
- A payload missing a required field is rejected with a defined validation error; no row is created.
- If the canonical schema enforces a uniqueness constraint on `customer_code`, a duplicate-code request returns a defined conflict response, not a silent success or an unhandled DB error.
- The committed workflow references only the existing resolved credential (`hzgFaX04t1nL01vF`); no placeholder or new credential ID appears anywhere in the file.
- Exactly one file is the authoritative Create implementation (per WP-000's map); the other is marked `DEPRECATED`, not deleted.

**Required Tests:** A functional test that exercises the workflow's actual logic against a real, controllable PostgreSQL instance (not the external `n8n.osa-system.com` host) and asserts resulting row state for: (a) valid create, (b) missing-required-field rejection, (c) duplicate-code conflict if applicable. This supersedes `BP-005-CUSTOMER-REGISTRY/TEST/customer_registry_test.sh`, which currently asserts nothing beyond a bare `set -e` against an unverifiable external URL (`MWO-P-001` §7).

---

### WP-002 — Customer Detail

**Objective:** Implement real single-record retrieval and resolve the `GET`/`DETAIL` naming divergence.

**Scope:** `BP-005 WF-LTSA-CUSTOMER-GET-001.json` (stub) and `BP-007 OUTPUTS/WF-LTSA-CUSTOMER-DETAIL-001.json` (empty shell) are the same logical operation under two names, neither currently functional; resolving that naming split is part of WP-000's canonicalization. Implement into the file WP-000 designates canonical for Detail. Confirm the identifier field (`id` vs `customer_code`) against `API_CONTRACT.md`'s documented `get` path rather than assuming; do not invent a new identifier convention. Real logic: webhook → validate identifier → `SELECT * FROM customer_registry WHERE <identifier> = ...` → 200/404 response, modeled on `WF-LTSA-PUMP-DETAIL-001.json`'s existing real pattern.

**Deliverables:**
- The workflow file WP-000 designated canonical for Detail, made functional, under one canonical name.
- The workflow file WP-000 designated deprecated for Detail, marked `DEPRECATED` in place, not deleted.
- A functional test.

**Acceptance Criteria:**
- A known identifier returns the full, correctly mapped record.
- An unknown identifier returns a defined 404, not a stub or hardcoded response.
- No ambiguity remains between `GET` and `DETAIL` naming — exactly one is authoritative (per WP-000's map), referenced consistently in any documentation touched by this MWO.

**Required Tests:** Functional test against a controllable PostgreSQL instance covering found and not-found cases, using a record created via WP-001's real create logic (test-fixture dependency on WP-001).

---

### WP-003 — Customer List

**Objective:** Implement real list/query logic.

**Scope:** Implement into the file WP-000's Customer Registry Canonical Map designates canonical for List: webhook → `SELECT * FROM customer_registry` → response. Only parameters/filters already documented in `API_CONTRACT.md` may be implemented — no new query capability may be introduced (no feature expansion).

**Deliverables:**
- The workflow file WP-000 designated canonical for List, made functional.
- The workflow file WP-000 designated deprecated for List, marked `DEPRECATED` in place, not deleted.
- A functional test.

**Acceptance Criteria:**
- Returns all existing `customer_registry` rows in the response shape already documented.
- An empty table returns an empty list, not an error.
- No parameter or filter beyond what is already documented is added.

**Required Tests:** Functional test against a controllable PostgreSQL instance verifying returned row count and field shape, using records created via WP-001.

---

### WP-004 — Customer Update

**Objective:** Implement real update logic.

**Scope:** Implement into the file WP-000's Customer Registry Canonical Map designates canonical for Update: webhook → validate identifier + payload → `UPDATE customer_registry SET ... WHERE ... RETURNING *` → 200/404 response.

**Deliverables:**
- The workflow file WP-000 designated canonical for Update, made functional.
- The workflow file WP-000 designated deprecated for Update, marked `DEPRECATED` in place, not deleted.
- A functional test.

**Acceptance Criteria:**
- A valid update modifies only the targeted row's specified fields; no other row is affected.
- An unknown identifier returns a defined 404; no row is created as a side effect.
- The committed workflow references only the existing resolved credential; no new credential introduced.

**Required Tests:** Functional test against a controllable PostgreSQL instance verifying before/after row state for a record created via WP-001, plus the not-found path.

---

### WP-005 — Customer Delete

**Objective:** Implement real delete logic.

**Scope:** Implement into the file WP-000's Customer Registry Canonical Map designates canonical for Delete: webhook → validate identifier → `DELETE FROM customer_registry WHERE ... RETURNING *` → 200/404 response.

**Deliverables:**
- The workflow file WP-000 designated canonical for Delete, made functional.
- The workflow file WP-000 designated deprecated for Delete, marked `DEPRECATED` in place, not deleted.
- A functional test.

**Acceptance Criteria:**
- An existing record is removed; a subsequent Detail lookup (WP-002) against the same identifier returns 404.
- An unknown identifier returns a defined 404, not an error or crash.

**Required Tests:** Functional test against a controllable PostgreSQL instance using a disposable record created solely for this test (not one shared with WP-002/003/004's fixtures), deleting it, and confirming removal. Run this work package's tests last, or against isolated fixtures, so it does not remove records other work packages' tests depend on.

---

### WP-006 — Customer By Code

**Objective:** Implement real lookup-by-`customer_code` logic for the one orphan artifact discovered during MWO-P-002.

**Scope:** WP-000's Customer Registry Canonical Map should record this operation with `BP-007 OUTPUTS/WF-LTSA-CUSTOMER-BY-CODE-001.json` as canonical and no deprecated counterpart, since no BP-005 equivalent exists. It currently exists as an empty shell and is documented nowhere — not in `API_CONTRACT.md`'s five operations, not in `CHANGELOG.md` (`IR-002-Workflow-Report.md`). This work package completes a file that already exists in the product tree; it is not a new endpoint invention. Real logic: webhook → validate `customer_code` parameter → `SELECT * FROM customer_registry WHERE customer_code = ...` → 200/404 response. Because this operation has no prior specification, this work package must also add the minimum documentation needed to retire its orphan status — one entry in `API/customer-registry/API_CONTRACT.md` (or equivalent) recording the route, request, and response shape for an artifact that already exists, not a new design.

**Deliverables:**
- Functional `WF-LTSA-CUSTOMER-BY-CODE-001.json`.
- One documentation entry recording its contract.
- A functional test.

**Acceptance Criteria:**
- A known `customer_code` returns the correct record.
- An unknown `customer_code` returns a defined 404.
- The operation is no longer undocumented — a contract entry exists mapping this file to a stated request/response shape.

**Required Tests:** Functional test against a controllable PostgreSQL instance, found and not-found cases, using a record created via WP-001.

---

## Recommended Execution Order

WP-000 (Canonicalization) → WP-001 (Create) → WP-002 (Detail) → WP-006 (By Code) → WP-003 (List) → WP-004 (Update) → WP-005 (Delete).

Rationale: WP-000 must complete first — it determines which file every subsequent work package implements into. WP-002, WP-003, WP-004, and WP-006 all require a real record to exist as a test fixture, which only WP-001 produces. WP-005 runs last because it is destructive and must not remove fixtures the other work packages' tests depend on.

---

## Constraints

- Architecture is frozen — no new table, service, framework, or architectural pattern.
- No governance work.
- No feature expansion — WP-006 documents an existing artifact; no work package may add a parameter, filter, or operation not already present in the tree or in `API_CONTRACT.md`.
- No API redesign — the webhook-path-vs-REST-path conflict recorded in `MWO-P-001` §4 (backlog item 008, "API Freeze") remains explicitly out of scope. All six work packages follow the existing n8n webhook-trigger pattern already present in every workflow file in this product.
- No UI work.
- No implementation outside Customer Registry — Pump, Seal, Asset, Inspection, Maintenance, and Equipment are untouched by this MWO.
- No new authentication mechanism or credential — every work package reuses the existing resolved reference (`hzgFaX04t1nL01vF` / `"Postgres account"`) established in IR-003.
- No work package may query the deprecated `ltsa_customers` table — only the canonical `customer_registry` schema, per IR-001's explicit forward-looking constraint.
- **Do not implement Customer logic in both BP-005 and BP-007.** Choose one canonical implementation per operation — the one designated by WP-000's Customer Registry Canonical Map — and mark the other `DEPRECATED` in place, never deleted. Never duplicate functionality.
- **Canonical implementations selected in WP-000 shall not change during this MWO.** WP-001–WP-006 implement into the file the Canonical Map already designates — they do not re-evaluate or re-select it. If, during implementation of any work package, evidence surfaces that a different file should have been canonical (e.g. a third undiscovered artifact, or a materially wrong WP-000 determination), **implementation must stop immediately** and a new MWO must be proposed to re-open canonicalization. Do not change a canonical decision mid-implementation and do not silently work around a WP-000 determination that turns out to be wrong.
- Tests must be functional, not existence/parse-only (the gap identified in `MWO-P-001` backlog item 009), and must not depend on the external, unverifiable `n8n.osa-system.com` host.
- **Testing capability prerequisite:** the current development environment's ability to execute functional tests was found unavailable during MWO-P-002's post-recovery verification attempt (`LTSA-Integrity-Recovery-Summary.md`, Post-Recovery Verification Attempt). This MWO does not resolve that gap and does not prescribe a specific testing tool. A working testing capability — whichever tool is chosen — must be confirmed available in the target environment before WP-001 implementation begins; this is a dependency to be resolved or explicitly accepted before work starts, not something to route around silently.
- One MWO. One product area. One commit. — all seven work packages (WP-000–WP-006) are implemented and reviewed together; no partial or interim commits.

---

## Out of Scope (explicit)

Pump, Seal, Authentication, Packaging, API Freeze, UI, governance, and any module or product area outside Customer Registry.

---

All seven work packages (WP-000–WP-006) have been implemented per this work order; see `MWO-P-003-Implementation-Summary.md` for the consolidated result. Nothing has been committed or pushed — all changes exist only in the local working tree on `feature/ltsa-brain`, awaiting review and a commit decision.
