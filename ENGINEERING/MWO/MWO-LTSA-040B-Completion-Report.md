# MWO-LTSA-040B Completion Report

Parent: MWO-LTSA-040B — Engineering Document Acquisition
Branch: `feature/ltsa-brain` (local; not committed)
Foundation v1.0 / Engineering Standard v1.0: both locked, unmodified by this MWO

Per the Execution Rules, WP-001–WP-003 executed as one continuous batch; WP-000's design decisions (cited to the MWO's own text rather than a separate Chief Architect message) stood in for the architecture-approval gate. No BLOCKER occurred, so no individual per-WP report was produced; this report aggregates all of them plus WP-004's validation.

---

## WP-000 Recap

Seven design decisions recorded and cited in full in `MWO-LTSA-040B-Engineering-Document-Acquisition.md`. Summary: extend `seal_engineering_document` in place rather than build a parallel table; keep `seal_code` required (both Knowledge Source and Mechanical Seal links are mandatory per Business Purpose); `knowledge_source_id` required at the workflow layer but nullable at the DB layer for migration safety; no rename of the existing table/build pack; Update narrowed to `status` only per the immutability Business Rule; no explicit existence-check node beyond the FK itself, matching MWO-030 precedent; "Engineering Document Relationship" realized as two simple FKs, not a junction table.

---

## Work Packages Completed

### WP-001 — Schema Alteration
`DATABASE/CANONICAL_SCHEMA.sql`'s `seal_engineering_document` block updated to its final shape (9 new columns: `knowledge_source_id`, `document_number`, `issue_date`, `manufacturer`, `language`, `description`, `file_name`, `file_format`, `page_count`; `document_type` widened from 4 to 7 values; new `page_count` non-negative CHECK; new FK to `knowledge_source_registry`), immediately followed by idempotent `ALTER TABLE ADD COLUMN IF NOT EXISTS` / `DROP CONSTRAINT IF EXISTS ... ADD CONSTRAINT` statements so a database already carrying the MWO-030 shape converges to the same end state on re-apply. Mirrored exactly in `BUILD-PACKS/BP-SEAL-ENGINEERING-DOCUMENT/DATABASE/001_create_table.sql` (updated) and a new, standalone `004_alter_add_acquisition_fields.sql`. `document_code`, `seal_code` (`NOT NULL`), `title` (`NOT NULL`), and the `seal_registry` FK are unchanged.

### WP-002 — Build Pack Update
- **Create workflow**: now requires `knowledge_source_id` (throws if absent, matching every other required-field check in this product); validates `document_type` against the widened 7-value set; validates `page_count` is a non-negative number if supplied; inserts all 16 columns.
- **Update workflow**: `updatable` array narrowed from 5 fields to exactly `['status']`; the error message for an empty update now states plainly that `status` is the only updatable field, rather than the generic "at least one updatable field is required."
- **Detail/List workflows**: unchanged — both already `SELECT *`/return the full row, so new columns surface automatically.
- **Delete workflow**: unchanged and retained — MWO-040B's Business Rule addresses mutation-in-place ("new revisions must create new document records"), not removal; unlike MWO-040A's Knowledge Source, no MWO-040B rule states documents must never be deleted, so Delete was not removed (WP-000 does not list this as a decision because it required no change).
- **Schemas**: `seal_engineering_document.schema.json` gained the 9 new properties and widened `document_type` enum; `required` now includes `knowledge_source_id`.
- **Tests**: `create_test.sh` gained a `knowledge_source_registry` fixture, an acquisition-field insert/assert, and a new check that `MAINTENANCE_MANUAL` (a 040B-added type) is accepted. `update_test.sh` was rewritten to assert status-only mutability (title/revision unchanged after a status update) and to document, via source-review note, that the workflow's own code has no path to mutate other fields. `detail_test.sh` and `list_test.sh` gained the same `knowledge_source_registry` fixture for consistency with the new FK. `delete_test.sh` was not touched — no field it exercises changed.
- **README**: rewritten to describe the dual FK requirement and the immutability policy.

### WP-003 — Manifest Documentation
`product.manifest.json`'s `seal_engineering_document` entry rewritten to describe the 040B extension (widened type set, immutability, nullable-but-required `knowledge_source_id`); `knowledge_source_registry` entry gained a closing clause noting the now-physical linkage. `_meta` extended to reference this MWO. No module enablement or artifact flag changed.

**No file under `BUILD-PACKS/BP-KNOWLEDGE-SOURCE/` or `BUILD-PACKS/BP-SEAL/` was touched** — both referenced only by FK, confirmed by `git diff --stat` scope (only `CANONICAL_SCHEMA.sql`, `product.manifest.json`, and `BUILD-PACKS/BP-SEAL-ENGINEERING-DOCUMENT/*` show as changed).

---

## Structural Validation Summary

| Check | Result |
|---|---|
| Shell syntax validation, all 5 `TEST/*.sh` scripts in the changed build pack | PASS — verified individually via `bash -n`, zero failures |
| JSON validation, all 5 `WORKFLOWS/*.json` + 2 `SCHEMAS/*.json` files (7 total) | PASS — verified individually via parse, zero failures |
| `product.manifest.json` | PASS — valid JSON after edit |
| Idempotency of new SQL | PASS — every new statement uses `ADD COLUMN IF NOT EXISTS` / `DROP CONSTRAINT IF EXISTS` before `ADD CONSTRAINT`, confirmed by direct read |
| Update workflow updatable-field list | PASS — confirmed by direct read of `WF-LTSA-BRAIN-SEAL-ENGINEERING-DOCUMENT-UPDATE-001.json`: `const updatable = ['status'];`, no other field reachable |
| Scope validation | PASS — `git diff --stat` confirms only `CANONICAL_SCHEMA.sql` (260 insertions), `product.manifest.json` (36 insertions/3 deletions), and files under `BUILD-PACKS/BP-SEAL-ENGINEERING-DOCUMENT/` changed; `BP-KNOWLEDGE-SOURCE` and `BP-SEAL` (the two referenced-only build packs) show zero diff |

**Runtime Verification, attempted for real:** `psql -h localhost -U postgres -w -v ON_ERROR_STOP=1 -c "SELECT 1;"` was run directly. Result: `psql: error: connection to server at "localhost" (::1), port 5432 failed: fe_sendauth: no password supplied` — the same standing condition as MWO-LTSA-030, MWO-LTSA-040A, and every prior MWO this sprint. Because no live connection is available, the `ALTER TABLE ADD COLUMN` idempotency claim above is verified by static review of the SQL's own syntax (`IF NOT EXISTS` on every statement), not by actually re-running it against a pre-040B-shaped table — stated explicitly rather than implied.

---

## PASS / WARNING / BLOCKER

- **WP-001 (Schema Alteration): PASS.**
- **WP-002 (Build Pack Update): PASS.**
- **WP-003 (Manifest Documentation): PASS.**
- **WP-004 (Structural Validation): PASS as structural validation; BLOCKER as a runtime-verification outcome** — stated separately, not conflated. Exactly one named cause: no credentialed PostgreSQL connection in this session.

## Known Limitations

- The idempotent `ALTER TABLE` upgrade path has not been exercised against an actual pre-040B-shaped table — it is syntactically reviewed, not executed.
- `knowledge_source_id`'s database-level nullability (vs. its workflow-level requiredness) means a row could theoretically be inserted with a `NULL` knowledge_source_id if a caller bypassed the Create workflow's validation and wrote directly to the table — a known, documented trade-off (WP-000 decision 3), not an oversight.
- No backfill mechanism exists for any engineering document that might already exist in a live deployment predating this MWO (again, currently theoretical — no live deployment has ever executed against this product).
- Whether `description` should have remained mutable (a defensible, less-strict reading of "immutable") was resolved conservatively toward the stricter reading; this is stated in WP-000 decision 5 as a judgment call, reversible via a future MWO if the stricter reading proves impractical.

---

## Production Impact

No existing registry's classification changes as a direct result beyond `seal_engineering_document` itself, which moves from a standalone 4-type registry to a 7-type registry with real provenance linkage — the same "partial" posture (structurally validated, execution blocked on the standing credential gap) as every other module.

---

## Definition of Done — Status

- WP-001–WP-003 complete, no out-of-scope file touched (verified via `git status`/`git diff --stat`). **Met.**
- WP-004's Structural Validation stated PASS/WARNING/BLOCKER; Completion Report exists. **Met.**
- Nothing committed or pushed without separate, explicit approval. **Met — awaiting instruction.**

---

Stopping here as instructed. Nothing was committed or pushed.
