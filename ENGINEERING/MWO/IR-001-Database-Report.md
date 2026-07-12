# IR-001 — Database Canonicalization Report

Parent: MWO-P-002 — LTSA Integrity Recovery
Scope: `ltsa_pumps`, `customer`, `pump` (as listed in MWO-P-002, Work Package 1)
Branch: `feature/ltsa-brain` (local, tracking `origin/feature/ltsa-brain`)

---

## Method

Every `.sql` and schema-declaring file under `PRODUCTS/LTSA-BRAIN` was enumerated and read in full. For each duplicated entity, the definition actually queried by real (non-stub) runtime workflow logic was preferred; where no runtime evidence existed, the more complete definition matching its module's documented API contract was preferred. No table was deleted. Obsolete definitions were marked with a `DEPRECATED (MWO-P-002 / IR-001)` header comment pointing to the canonical file, per the work order's "remove or archive only if safe" instruction — marking in place was judged the safe action for tracked files.

---

## Findings and Actions

### Entity: `customer`

| Definition | Path | Status |
|---|---|---|
| **Canonical** | `PRODUCTS/LTSA-BRAIN/DATABASE/MIGRATIONS/005_create_customer_registry.sql` (`customer_registry`, UUID PK, 14 columns) | Selected: unchanged, now also mirrored in `DATABASE/CANONICAL_SCHEMA.sql` |
| Duplicate | `PRODUCTS/LTSA-BRAIN/RELEASE/database.sql` (`ltsa_customers`, SERIAL PK, 6 generic columns) | Marked `DEPRECATED`, not deleted |

Rationale: `customer_registry`'s column names (`customer_code`, `customer_name`, `customer_type`, `industry`, `billing_email`, `phone`, `city`, `province`) match `API/customer-registry/API_CONTRACT.md`'s documented create payload field-for-field. `ltsa_customers`'s generic `code`/`name` columns do not.

**Result: PASS** — one canonical definition now designated; duplicate marked, not removed (no runtime currently queries either, so no runtime pointer to update).

---

### Entity: `pump` / table `ltsa_pumps`

| Definition | Path | Status |
|---|---|---|
| **Canonical** | `PRODUCTS/LTSA-BRAIN/MODULES/PUMP/DATABASE/001_create_pumps.sql` (`ltsa_pumps`, UUID PK, `tag_number`/`area`/... 13 columns) | Selected: unchanged, now also mirrored in `DATABASE/CANONICAL_SCHEMA.sql` |
| Duplicate (name collision) | `PRODUCTS/LTSA-BRAIN/RELEASE/database.sql` (`ltsa_pumps`, SERIAL PK, 6 generic columns) | Marked `DEPRECATED`, not deleted |
| Duplicate (different name, same entity) | `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-PUMP/DATABASE/{001_create_table,002_seed,003_indexes,999_rollback}.sql` (`public.pump_registry`, TEXT PK `pump_code`, 9 columns) | Marked `DEPRECATED` on all 4 files, not deleted |

Rationale: `ltsa_pumps` (MODULES/PUMP version) is the exact table queried by the product's only two real, non-stub workflows:
- `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-REGISTRY-001.json` — `INSERT INTO ltsa_pumps (...)`.
- `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-PUMP-DETAIL-001.json` — `SELECT * FROM public.ltsa_pumps WHERE tag_number = ...` (this workflow's existence and content is a correction to MWO-P-001, see `IR-002-Workflow-Report.md`).

This is the strongest possible evidence class (working queries), so it outranks the other two candidates, neither of which is queried anywhere.

**Result: PASS** — one canonical definition confirmed already correct; both duplicates marked, not removed. **The `RELEASE/database.sql` `ltsa_pumps` block was a direct name collision with the canonical table** — had both been applied to the same database, the second `CREATE TABLE IF NOT EXISTS` would have silently no-op'd against whichever schema was applied first, masking the conflict rather than failing loudly. This is now flagged in-file.

---

## Runtime Reference Check

**Result: PASS, no change required.** Both real workflows already reference the canonical `ltsa_pumps` definition (`public.ltsa_pumps`, `tag_number`-keyed). No workflow currently queries `customer_registry`, `ltsa_customers`, or `pump_registry`, so there was no incorrect runtime pointer to redirect.

**WARNING:** If/when the stub Customer Registry or `BP-PUMP` workflows (see `IR-002-Workflow-Report.md`) are later given real query logic, they must be pointed at the canonical tables designated here (`customer_registry`, `ltsa_pumps`) and not at the deprecated `ltsa_customers` or `pump_registry` tables. This is a forward-looking note, not a defect present today (those workflows currently issue no queries at all).

---

## Deliverable

`PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql` — new file, consolidating the canonical DDL for `customer_registry`, `ltsa_pumps`, and (for completeness, no conflict existed) `seal_registry`, each annotated with its source path and selection rationale.

---

## Out of Scope (not touched)

`ltsa_assets`, `ltsa_inspections`, `ltsa_maintenances` in `RELEASE/database.sql` were left untouched — they are not among the three entities MWO-P-002 IR-001 lists (`ltsa_pumps`, `customer`, `pump`), and per MWO-P-001's audit they are the *only* database artifact that exists for those three modules; deprecating them would remove the sole record of a manifest-declared module with no replacement, which is manifest/feature-scope work reserved for `IR-004-Manifest-Report.md`, not database canonicalization.

---

## Summary

| Item | Result |
|---|---|
| Canonical `customer` schema designated | PASS |
| Canonical `pump` (`ltsa_pumps`) schema designated | PASS |
| Duplicate definitions marked (not deleted) | PASS |
| Runtime already references canonical schema | PASS |
| Future stub-workflow implementations must target canonical tables | WARNING (forward-looking, no current defect) |
| Conflicting schema definitions remain | **No** — acceptance criterion met |
