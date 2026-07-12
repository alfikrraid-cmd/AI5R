# CR-002 — Customer Detail Implementation Report

Parent: MWO-P-003 — Customer Registry Functional Completion (WP-002)
Canonical file (per `CR-000-Canonicalization-Report.md`): `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-GET-001.json`
Deprecated file: `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-DETAIL-001.json`

---

## Naming Resolution

The `GET`/`DETAIL` naming divergence flagged in WP-000 is resolved in favor of `GET` — the name and path (`GET ltsa/customer/get`) already documented in `API_CONTRACT.md` and `README.md`. The canonical file keeps its existing name; no rename was performed. The `DETAIL` name is retired with the deprecated BP-007 file.

## Implementation

`GET /ltsa/customer/get` → `Parse Customer ID` (code: reads `$json.query?.id`) → `IF Valid ID` → **false:** `Respond 400` / **true:** `Get Customer Detail` (parameterized `SELECT * FROM customer_registry WHERE id = ...`) → `Build Customer Detail Response` (code: reads `$input.first()`, safe against zero rows) → `Respond Customer Detail` (200/404 driven by `statusCode`).

Directly modeled on the product's one existing real detail workflow, `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-PUMP-DETAIL-001.json` — same node sequence, same zero-row-safe pattern, same credential. The identifier field is confirmed as `id` (not `customer_code`) directly from `API_CONTRACT.md` (`GET /webhook/ltsa/customer/get?id={id}`), not assumed.

**Credential:** `hzgFaX04t1nL01vF` / `"Postgres account"` — existing reference only.

**Query parameterization — corrected during implementation:** same fix as WP-001 (see `CR-001-Create-Report.md`): the query text now uses a `$1` positional placeholder instead of an embedded `{{ $json.id }}` expression, so `queryReplacement` performs actual parameter binding instead of being vestigial.

---

## Validation Performed

- JSON validity: passed for both canonical and deprecated files.
- Node graph: `IF Valid ID` has both branches terminating in a response node (`Respond 400` / `Respond Customer Detail` via the success chain) — no dead branch.
- Field mapping: `SELECT *` returns all `customer_registry` columns; response shape matches the pump-detail precedent's `{success, message, data}` envelope, consistent with the rest of the product.
- Live n8n execution: not performed — no n8n instance reachable from this repository (same pre-existing condition as WP-001).

## Required Tests

Delivered: `customer_detail_test.sh` — creates a fixture record, asserts a known `id` resolves to the correct record, and asserts an unknown `id` resolves to zero rows at the DB level (the condition `Build Customer Detail Response` maps to HTTP 404).

**Execution status: WARNING — written, not executed** (same environment gap as WP-001: local PostgreSQL reachable, no usable credential available to this session).

## Acceptance Criteria — Status

| Criterion | Status |
|---|---|
| Known identifier returns full, correctly mapped record | Implemented; asserted by test §1 (not yet executed) |
| Unknown identifier returns defined 404, not stub/hardcoded response | Implemented; asserted by test §2 at the DB level (not yet executed) |
| No ambiguity between `GET`/`DETAIL` naming | **Met** — `GET` is canonical, documented, unchanged |

## Summary

| Item | Result |
|---|---|
| Real logic implemented in canonical file | PASS |
| Deprecated file marked, not deleted | PASS |
| Naming divergence resolved | PASS |
| Canonical map (WP-000) respected | PASS |
| Functional test written | PASS |
| Functional test executed against live DB | WARNING — not executable in this environment |
| Scope limited to Customer Detail only | PASS |
