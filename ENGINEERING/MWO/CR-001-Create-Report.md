# CR-001 — Customer Create Implementation Report

Parent: MWO-P-003 — Customer Registry Functional Completion (WP-001)
Canonical file (per `CR-000-Canonicalization-Report.md`): `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-CREATE-001.json`
Deprecated file: `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-CREATE-001.json`

---

## Implementation

The canonical file's single `Webhook` trigger (unchanged path: `POST ltsa/customer/create`) is now followed by a real node chain, modeled on the product's one existing real create workflow (`MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-REGISTRY-001.json`):

`Webhook Create Customer` → `Validate Customer Input` (code: throws if `customer_code` or `customer_name` — the two fields `API_CONTRACT.md` lists as required — are missing; defaults the remaining fields to the canonical schema's own column defaults, e.g. `customer_type: 'company'`, `country: 'Indonesia'`, `status: 'active'`) → `Check Existing Customer` (parameterized `SELECT id FROM customer_registry WHERE customer_code = ...`) → `Check Customer Conflict` (code: safely reads `$input.first()`, following the same zero-row-safe pattern as the product's real `WF-LTSA-PUMP-DETAIL-001.json`) → `IF Customer Code Exists` → **true:** `Respond Conflict` (409) / **false:** `Insert Customer to PostgreSQL` (parameterized `INSERT ... RETURNING *`) → `Response Success`.

The pre-insert existence check exists because `customer_registry.customer_code` carries a `UNIQUE NOT NULL` constraint (`DATABASE/MIGRATIONS/005_create_customer_registry.sql` line 5) — confirmed by direct read of the canonical schema, not assumed. No precedent for this exact check existed elsewhere in the product; it reuses only node types and patterns already real and present (`code`, `postgres executeQuery`, `if`, `respondToWebhook`), no new architecture.

**Credential:** `id: hzgFaX04t1nL01vF`, `name: "Postgres account"` — the one existing resolved reference (IR-003). No new credential introduced.

**Query parameterization — corrected during implementation:** the first draft mirrored `WF-LTSA-PUMP-DETAIL-001.json`'s exact pattern of embedding a `{{ $json.field }}` expression directly in the query text *and* also setting `queryReplacement`. On review, that combination is self-defeating: n8n resolves the `{{ }}` expression client-side before the query ever reaches Postgres, so `queryReplacement` never actually binds anything — the existing product precedent is real but not actually parameterized. Both queries in this file were corrected to use genuine positional placeholders (`$1`, `$2`, ...) in the query text with the values supplied only via `queryReplacement`, which is the mechanism n8n's Postgres node actually uses for parameter binding. This is a correctness/security fix applied before finalizing WP-001, not a deviation reused elsewhere without justification — the same fix was also applied to WP-002 (see `CR-002-Detail-Report.md`) for consistency.

**Deprecation marking:** the BP-007 duplicate now carries `_deprecated: true`, `_deprecatedReason`, and `_canonicalReplacement` metadata fields (additive, ignored by n8n) — the JSON equivalent of IR-001's SQL comment-header convention. No node, file, or existing field was deleted.

---

## Validation Performed

- **JSON validity:** `python -c "import json; json.load(...)"` — passed for both the canonical and deprecated files.
- **Node graph:** every node referenced in `connections` exists; every non-terminal node has an outgoing connection; both `IF` branches terminate in a `respondToWebhook` node (no dead branch, no missing response path).
- **Field mapping:** every column the `INSERT` targets exists in `DATABASE/MIGRATIONS/005_create_customer_registry.sql`; every field `API_CONTRACT.md`'s documented Create Payload lists is read by `Validate Customer Input`.
- **Live n8n execution:** **not performed.** No n8n instance is reachable from this repository/environment (confirmed in `MWO-P-001` §5/§9 — n8n is an external, already-hosted service this repo does not provision). This is a pre-existing environment condition, not something WP-001 introduced or could resolve.

---

## Required Tests

Delivered: `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/TEST/customer_create_test.sh` — a functional test against a real, controllable PostgreSQL instance (via standard `libpq` environment variables or `LTSA_TEST_DSN`), asserting:
1. A valid insert produces exactly one row with the correct `customer_code`/`customer_name`.
2. A duplicate `customer_code` is rejected by the schema's unique constraint (the same constraint `Check Existing Customer`/`IF Customer Code Exists` test for at the workflow level, surfaced as HTTP 409 via `Respond Conflict`).
3. The missing-required-field path is documented as a specification-level check only — `Validate Customer Input`'s throw-on-missing-field logic is JS running inside an n8n Code node and cannot be exercised by `psql`; this step is not claimed as executed, only verified by direct reading of the node's source.

The prior `customer_registry_test.sh` (bare `curl` against `n8n.osa-system.com`, no assertions) is marked `DEPRECATED` in place with a comment header, per `MWO-P-001-LTSA-Product-Audit.md` backlog item 009. Not deleted.

**Execution status: WARNING — written, not executed.** A local PostgreSQL server was found listening on `localhost:5432` in this environment, but no usable credential/connection string is available to this session (an unauthenticated connection attempt was correctly rejected by the server: `fe_sendauth: no password supplied`). No credential was guessed or searched for. Per the MWO's own flagged **Testing capability prerequisite**, this test is ready to run once a connection string is supplied but has **not** been run, and its assertions above are not claimed as verified — only as logically sound against the schema and workflow source actually read.

---

## Acceptance Criteria — Status

| Criterion | Status |
|---|---|
| Valid payload creates one row with correctly mapped fields | Implemented; asserted by test §1 (not yet executed) |
| Missing required field rejected, no row created | Implemented (throw-on-missing in `Validate Customer Input`); not executable by this test harness — specification-level only |
| Duplicate `customer_code` returns a defined conflict, not silent success/crash | Implemented (`Check Existing Customer` → `IF` → `Respond Conflict` 409); asserted by test §2 (not yet executed) |
| Only the existing resolved credential is referenced | **Met** — `hzgFaX04t1nL01vF` only, no placeholder |
| Exactly one authoritative Create file; other marked `DEPRECATED` | **Met** |

## Summary

| Item | Result |
|---|---|
| Real logic implemented in canonical file | PASS |
| Deprecated file marked, not deleted | PASS |
| Canonical map (WP-000) respected, not altered | PASS |
| Functional test written | PASS |
| Functional test executed against live DB | **WARNING — not executable in this environment (no connection credentials available)** |
| Scope limited to Customer Create only | PASS |
