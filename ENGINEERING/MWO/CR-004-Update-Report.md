# CR-004 — Customer Update Implementation Report

Parent: MWO-P-003 — Customer Registry Functional Completion (WP-004)
Canonical file: `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-UPDATE-001.json`
Deprecated file: `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-UPDATE-001.json`

---

## Implementation

`PUT /ltsa/customer/update` → `Validate Update Input` (code: requires `id`; accepts any subset of the schema's 13 non-key, non-timestamp columns — `customer_code, customer_name, customer_type, industry, tax_id, billing_email, phone, address, city, province, country, status, notes` — throws if `id` is missing or if no updatable field is present) → `Build Update Statement` (code: constructs a parameterized `UPDATE ... SET col = $1, ... WHERE id = $N RETURNING *` statement and a matching ordered `params` array, from only the fields actually supplied — a partial update) → `Update Customer` (`executeQuery` with the built query/params passed through via expressions) → `Check Update Result` (code: `$input.first()`-safe, 404 if zero rows affected) → `Respond Update`.

**No precedent for "update" exists anywhere in the product** (no build pack has ever had a real update workflow) — this is genuinely new logic, not a reuse of an existing real pattern like Create/Detail were. It stays within the MWO's constraints by using only node types already present in this product (`code`, `postgres executeQuery`, `respondToWebhook`) and the same zero-row-safe response pattern established in WP-001/WP-002, rather than introducing a new node type, a new response envelope shape, or the n8n Postgres node's structured `update` operation mode (which has no precedent in this product and could not be verified against this n8n version's actual parameter schema without a live instance — using it would have been an unverifiable guess, not evidence-based reuse).

An unresolved edge case, noted rather than silently handled: if a request updates `customer_code` to a value that collides with another row, Postgres will raise a unique-constraint error that propagates unhandled (same as Create's original missing-field behavior before its conflict check was added). This is not required by WP-004's acceptance criteria (which only specify targeted-field-only updates and 404-on-unknown-id) and was not added, to avoid scope expansion beyond what was approved.

**Credential and parameterization:** `hzgFaX04t1nL01vF` / `"Postgres account"`; genuine `$1..$N` positional placeholders bound via `queryReplacement`, consistent with the WP-001/WP-002 correction (see `CR-001-Create-Report.md`).

## Validation Performed

- JSON validity: passed.
- Node graph: single linear chain (no branch — 404 is data-driven by `Check Update Result`, not a workflow branch, since `RETURNING *` on zero matched rows returns zero rows regardless).
- Field mapping: `updatable` list in `Validate Update Input` matches exactly the canonical schema's editable columns (excludes `id`, `created_at`; `updated_at` is set server-side by `Build Update Statement`, not client-supplied).
- Live n8n execution: not performed (same pre-existing environment condition as prior work packages).

## Required Tests

Delivered: `customer_update_test.sh` — creates two fixture rows (target + control), applies a single-field update to the target, and asserts: the targeted field changed, an untouched field on the same row did not change, the control row was not affected, and a nonexistent id affects zero rows.

**Execution status: WARNING — written, not executed** (same environment gap as prior work packages).

## Acceptance Criteria — Status

| Criterion | Status |
|---|---|
| Valid update modifies only targeted row's specified fields; other rows unaffected | Implemented; asserted by test §1 (not yet executed) |
| Unknown identifier returns defined 404; no row created as side effect | Implemented (`RETURNING *` naturally yields 0 rows; `UPDATE` never creates rows) — asserted by test §2 (not yet executed) |
| Only existing resolved credential referenced | **Met** |

## Summary

| Item | Result |
|---|---|
| Real logic implemented in canonical file | PASS |
| Deprecated file marked, not deleted | PASS |
| Canonical map (WP-000) respected | PASS |
| Functional test written | PASS |
| Functional test executed against live DB | WARNING — not executable in this environment |
| Scope limited to Customer Update only | PASS |
