# CR-003 — Customer List Implementation Report

Parent: MWO-P-003 — Customer Registry Functional Completion (WP-003)
Canonical file: `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-LIST-001.json`
Deprecated file: `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-LIST-001.json`

---

## Implementation

`GET /ltsa/customer/list` → `List Customers` (`SELECT * FROM customer_registry ORDER BY created_at DESC;`) → `Build Customer List Response` (code: `$input.all()`, wraps rows as `{success, message, count, data}`) → `Respond Customer List`.

No filter or pagination parameter was added — `API_CONTRACT.md` documents no parameters for this operation, and none may be invented per the MWO's "no feature expansion" constraint. `ORDER BY created_at DESC` is a deterministic ordering choice, not a new capability.

**Credential:** `hzgFaX04t1nL01vF` / `"Postgres account"` — existing reference only.

## Validation Performed

- JSON validity: passed.
- Node graph: single linear chain, no branch, terminates in one response node.
- `$input.all()` on the `Build Customer List Response` code node is a natural extension of the `$input.first()` call already used in `WF-LTSA-PUMP-DETAIL-001.json` and this MWO's WP-001/WP-002 nodes — same API, no new pattern class.
- Live n8n execution: not performed (same pre-existing environment condition as WP-001/WP-002).

## Required Tests

Delivered: `customer_list_test.sh` — asserts row count increases by exactly 1 after an insert (proxy for "list reflects table state") and that the inserted row's fields are present as `List Customers`' unfiltered `SELECT *` would return them. The empty-table → empty-list behavior is a property of `Build Customer List Response`'s code (`$input.all()` on zero items yields `data: []`), documented and traced to source rather than executed, since no n8n runtime is available to run the code node itself.

**Execution status: WARNING — written, not executed** (same environment gap as WP-001/WP-002).

## Acceptance Criteria — Status

| Criterion | Status |
|---|---|
| Returns all rows in documented response shape | Implemented; asserted by test (not yet executed) |
| Empty table returns empty list, not an error | Implemented (`$input.all()` on 0 items); verified by source reading, not executed |
| No parameter/filter beyond documented added | **Met** — none added |

## Summary

| Item | Result |
|---|---|
| Real logic implemented in canonical file | PASS |
| Deprecated file marked, not deleted | PASS |
| Canonical map (WP-000) respected | PASS |
| Functional test written | PASS |
| Functional test executed against live DB | WARNING — not executable in this environment |
| Scope limited to Customer List only | PASS |
