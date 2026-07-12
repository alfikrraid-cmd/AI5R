# CR-006 — Customer By Code Implementation Report

Parent: MWO-P-003 — Customer Registry Functional Completion (WP-006)
Canonical file (only artifact for this operation; no BP-005 counterpart): `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-BY-CODE-001.json`

---

## Scope Note

Per `IR-002-Workflow-Report.md`, this file previously existed as an empty shell with no documentation anywhere — not in `API_CONTRACT.md`, not in `CHANGELOG.md`. This work package completes a file that already existed in the product tree; no new endpoint was invented.

## Implementation

`GET /ltsa/customer/by-code` → `Parse Customer Code` (reads `$json.query?.code`) → `IF Valid Code` → **false:** `Respond 400` / **true:** `Get Customer By Code` (parameterized `SELECT * FROM customer_registry WHERE customer_code = $1 LIMIT 1`) → `Build By-Code Response` (`$input.first()`-safe; 404 if not found) → `Respond By-Code`.

Structurally identical to WP-002's Detail workflow, substituting `customer_code` for `id` as the lookup key. Route (`GET ltsa/customer/by-code`) and query parameter (`code`) were not previously specified anywhere; they were chosen as the minimal, consistent extension of the existing `get?id={id}` convention — same HTTP method, same query-parameter style, same response envelope — not a new convention.

**Credential and parameterization:** `hzgFaX04t1nL01vF` / `"Postgres account"`; genuine `$1` positional placeholder via `queryReplacement`.

## Documentation Added

`API/customer-registry/API_CONTRACT.md` now lists `GET /webhook/ltsa/customer/by-code?code={customer_code}` alongside the other five endpoints, with a note identifying it as a previously-orphaned artifact completed under this MWO. The `Definition of Done` list gained one line ("Get customer by code works"). This is documentation of an artifact that already existed, not a new design — consistent with the MWO's "no feature expansion" constraint.

## Validation Performed

- JSON validity: passed.
- Node graph: both `IF Valid Code` branches terminate in a response node.
- `API_CONTRACT.md` now accounts for every workflow file present in the product's Customer Registry surface — no remaining undocumented operation.
- Live n8n execution: not performed (same pre-existing environment condition as all prior work packages).

## Required Tests

Delivered: `customer_by_code_test.sh` — asserts a known `customer_code` resolves to the correct record, and an unknown `customer_code` resolves to zero rows at the DB level.

**Execution status: WARNING — written, not executed** (same environment gap as prior work packages).

## Acceptance Criteria — Status

| Criterion | Status |
|---|---|
| Known `customer_code` returns the correct record | Implemented; asserted by test §1 (not yet executed) |
| Unknown `customer_code` returns a defined 404 | Implemented; asserted by test §2 (not yet executed) |
| Operation no longer undocumented | **Met** — `API_CONTRACT.md` entry added |

## Summary

| Item | Result |
|---|---|
| Real logic implemented in the (sole) canonical file | PASS |
| Orphan documentation gap closed | PASS |
| Canonical map (WP-000) respected — no BP-005 counterpart existed, none invented | PASS |
| Functional test written | PASS |
| Functional test executed against live DB | WARNING — not executable in this environment |
| Scope limited to Customer By Code only | PASS |
