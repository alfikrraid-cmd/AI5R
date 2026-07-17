# MWO-P-006 — Runtime Verification Infrastructure

Status: DRAFT — WORK ORDER ONLY, NO IMPLEMENTATION PERFORMED
Type: Manufacturing Work Order (Infrastructure)
Role: Implementation Engineer
Architecture: FROZEN — no new architecture, service, table, or framework proposed
Foundation: v1.0 — LOCKED, unchanged by this MWO
Engineering Standard: v1.0 — LOCKED, unchanged by this MWO
Phase: LTSA Production Sprint 03
Basis: `ENGINEERING/AI5R_ENGINEERING_STANDARD_v1.0.md`, Sprint 01 Checkpoint Report, Sprint 01 Engineering Review, Sprint 01 Retrospective, `ENGINEERING/MWO/MWO-P-003-Customer-Registry-Functional-Completion.md` + `CR-00X` reports, `ENGINEERING/MWO/MWO-P-004-Pump-Registry-Functional-Completion.md` + `PM-00X` reports, `ENGINEERING/MWO/MWO-P-005-Seal-Registry-Functional-Completion.md` + `SM-000`/Completion Report — no new audit scope opened
Scope: `PRODUCTS/LTSA-BRAIN` verification/test infrastructure only

---

## Executive Summary

Every synthesis report produced in Sprint 01 (Checkpoint Report, Engineering Review, Retrospective) independently identified the same top finding: no workflow in this product — old or new, across Customer Registry, Pump Registry, or Seal Registry — has ever been executed against a live system. This MWO builds the infrastructure to close that gap.

**A scope clarification, surfaced by evidence and stated here before any further planning, per Engineering Standard v1.0 §7 (Evidence Standard):** this repository provisions no n8n instance and none is reachable from this environment (confirmed originally in `MWO-P-001` §5/§9, unchanged in every MWO since). **Full end-to-end Runtime Verification through n8n itself is not achievable from repository evidence and is not what this MWO builds.** What is achievable, and what this MWO scopes itself to, is **database-level verification of the SQL logic embedded in each workflow** — executing the actual `INSERT`/`SELECT`/`UPDATE`/`DELETE` statements each workflow's Postgres node runs, against a real, controllable PostgreSQL instance, using the exact pattern MWO-P-003 already proved for Customer Registry (`customer_*_test.sh`, `LTSA_TEST_DSN`/standard `libpq` environment variables). This MWO extends that one proven pattern into reusable infrastructure and closes the resulting test-coverage gap for Pump and Seal (currently zero written tests for either, per `PM-003` and the MWO-P-005 Completion Report). Whether these tests can actually be *executed* in this MWO depends entirely on whether a usable database connection is available at implementation time — the same standing condition every prior MWO encountered and reported honestly rather than worked around.

---

## Objective

Build the Runtime Verification Infrastructure for LTSA-BRAIN: a shared verification framework, a test runner, and a complete database-level verification suite covering all three completed registries (Customer, Pump, Seal) — closing the Pump/Seal test-coverage gap and consolidating Customer's existing tests under the same runner.

---

## Scope

- New shared infrastructure under `PRODUCTS/LTSA-BRAIN/VERIFICATION/` (does not exist yet, confirmed by direct search).
- New per-registry test scripts under `BUILD-PACKS/BP-PUMP/TEST/` and `BUILD-PACKS/BP-SEAL/TEST/` (neither directory currently exists, confirmed by direct search — Pump and Seal have zero test coverage today).
- Registration of Customer Registry's 6 existing test scripts (`BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/TEST/customer_{create,detail,list,update,delete,by_code}_test.sh`) with the new runner. These files are read, not modified.
- One attempt at actual execution (WP-004), honestly reported regardless of outcome.

## Out of Scope

- **Modifying Customer Registry, Pump Registry, or Seal Registry workflow implementations.** Every `.json` workflow file in `MODULES/PUMP/WORKFLOWS/`, `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/`, `BUILD-PACKS/BP-SEAL/WORKFLOWS/`, and `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/` is read-only for this MWO.
- **Modifying Customer Registry's existing 6 test scripts.** They are consumed by the new runner as-is; if any prove structurally incompatible with the runner's discovery convention, that is a documented finding, not a fix performed under this MWO.
- **n8n-level execution of any kind.** No n8n instance is provisioned, reached, or simulated. This MWO's "Runtime Verification" is scoped to database-level SQL execution only, per the Executive Summary above.
- **CI/CD wiring.** The runner is built to be CI-compatible (non-zero exit on failure) but no pipeline, Dockerfile, or scheduled job is created — Packaging and Deployment remain out of scope, per Engineering Standard v1.0 and every prior MWO's constraint.
- Asset, Inspection, Maintenance, Equipment, UI, Authentication, Authorization — untouched; no artifact exists for most of these to verify.
- Any API specification file.
- Governance, Constitution, README, Foundation, Engineering Standard — untouched; both are locked.

## Dependencies

- **MWO-P-002 (`5e349cd`)** — canonical schema (`DATABASE/CANONICAL_SCHEMA.sql`) and resolved credential reference (`hzgFaX04t1nL01vF`), both read by the bootstrap script and reused by reference in test scripts, not re-derived.
- **MWO-P-003 (`f125dfc`)** — the `psql`-based, `LTSA_TEST_DSN`-parameterized test pattern this entire MWO generalizes. `customer_create_test.sh` is the direct structural template for every new Pump/Seal test script.
- **MWO-P-004 (`eb9330e`) / MWO-P-005 (`2d5a789`)** — the specific workflows this MWO's new tests verify: Pump's `MODULES/PUMP/WORKFLOWS/*.json` (List/Update/Delete new, Create/Detail pre-existing) and Seal's `BUILD-PACKS/BP-SEAL/WORKFLOWS/*.json` (all five, completed in place).
- **A usable PostgreSQL connection at implementation time.** Not guaranteed. Every prior attempt this sprint (MWO-P-003, MWO-P-004) found a local PostgreSQL server reachable on `localhost:5432` but no usable credential in-session; no credential was ever guessed or searched for, per standing instruction, and none will be for this MWO either. If unavailable again, WP-004 reports that plainly rather than fabricating a result.

## Constraints

- Architecture is frozen. Foundation v1.0 and Engineering Standard v1.0 are locked and unmodified.
- Do not modify Customer Registry, Pump Registry, or Seal Registry (their workflow implementation files).
- Do not redesign architecture — this MWO adds tooling and test scripts only; no new table, service, or credential mechanism is introduced anywhere in it.
- Document out-of-scope findings; do not fix them.
- No new engineering concept beyond what Engineering Standard v1.0 already codifies — every pattern this MWO uses (`psql`/`LTSA_TEST_DSN` test scripts, structural-vs-runtime validation separation, `_deprecated`-style non-invasive additive conventions) is a direct reuse, cited to its origin, not an invention.

### Execution Rules (approval granularity, stated explicitly per Engineering Standard v1.0 §5)

1. **WP-000 requires its own individual approval.** Implementation of WP-001–WP-004 may not begin until the Runtime Verification Planning section is confirmed and separately approved.
2. **WP-001 through WP-004 execute as a single batch, without stopping, once WP-000 is approved.**
3. **WP-004 produces its own named deliverable, the Verification Report (`RV-004-Verification-Report.md`)** — this is WP-004's actual purpose, not an incidental per-WP status report, and is produced regardless of whether live execution succeeds, fails, or cannot be attempted. It is distinct from the single overall Completion Report.
4. **One Completion Report is produced after the full batch completes**, aggregating WP-001–WP-004. No individual report is produced for WP-001–WP-003 unless a BLOCKER occurs in one of them.
5. Nothing is committed or pushed without separate, explicit approval.

---

## WP-000 — Runtime Verification Planning

**Responsibility:** Identify the canonical runtime verification approach, confirm no architectural changes are required, and produce the Runtime Verification Planning section (this section, to be formally confirmed rather than re-derived once approved).

**Canonical runtime verification approach (proposed):**

Database-level execution of each workflow's embedded SQL, via `psql`, against a target resolved through `LTSA_TEST_DSN` or standard `libpq` environment variables (`PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`) — the exact mechanism `customer_create_test.sh` through `customer_by_code_test.sh` already use. This is proposed as canonical because it is the only verification approach this product has ever actually proven to work structurally (six scripts, syntax-checked via `bash -n`, written against real schema evidence) and because `psql` is confirmed present in this environment while no Python PostgreSQL driver (`psycopg2`) is. No new tool, language, or dependency is introduced.

**Confirmation that no architectural changes are required:**

- The verification framework and runner read the already-canonical schema (`DATABASE/CANONICAL_SCHEMA.sql`) and already-resolved credential reference; they introduce neither.
- A new `PRODUCTS/LTSA-BRAIN/VERIFICATION/` directory and two new `TEST/` directories (`BP-PUMP/TEST/`, `BP-SEAL/TEST/`) are organizational, not architectural — they mirror the existing `BP-005-CUSTOMER-REGISTRY/TEST/` precedent and introduce no new table, service, or credential mechanism.
- No product workflow file is modified by this MWO (see Out of Scope) — verification infrastructure observes the product; it does not change it.

**Deliverables:** This Runtime Verification Planning section, confirmed.

**Acceptance Criteria:**
- The verification approach is identified and evidenced (not invented) — traced to `customer_create_test.sh` through `customer_by_code_test.sh`.
- No architectural change is proposed anywhere in this MWO.
- The n8n-level-execution scope limitation is explicitly acknowledged, not silently narrowed without comment.

---

## WP-001 — Verification Framework

**Objective:** Build the shared tooling every registry's test suite depends on, extracted from the pattern already proven six times in Customer Registry's tests, not invented fresh.

**Scope:** New files under `PRODUCTS/LTSA-BRAIN/VERIFICATION/`:
- `lib/psql_common.sh` — the `psql_run()` connection-resolution function and `LTSA_TEST_DSN`-or-libpq-env-var fallback logic, extracted verbatim from its six duplicated occurrences across the existing Customer test scripts into one sourced file.
- `bootstrap_schema.sh` — applies `DATABASE/CANONICAL_SCHEMA.sql` to the target database idempotently (`psql -f`), so a fresh, empty database can be brought to a verifiable state in one step.

**Deliverables:** `VERIFICATION/lib/psql_common.sh`, `VERIFICATION/bootstrap_schema.sh`.

**Acceptance Criteria:**
- `psql_common.sh`'s connection logic is behaviorally identical to what every existing Customer test script already does inline — extraction, not redesign.
- `bootstrap_schema.sh` applies successfully against a schema-less database (structurally reviewed against `CANONICAL_SCHEMA.sql`'s own `CREATE TABLE IF NOT EXISTS` idempotency, not assumed).
- Customer Registry's existing 6 test scripts are not modified to consume the new shared library in this work package — that would touch Customer Registry test files, and is deferred to a decision point in WP-002 (see Known Risks there), not assumed here.

**Required Validation:** Shell syntax validation (`bash -n`) for both new scripts; static review confirming the extracted connection logic matches the original inline pattern exactly, field for field.

**Known Risks:** None beyond the standing absence of a usable database connection in this environment.

---

## WP-002 — Verification Runner

**Objective:** Build a single script that discovers and executes every registry's test suite, reporting a consolidated result.

**Scope:** New file `PRODUCTS/LTSA-BRAIN/VERIFICATION/run_verification.sh`: discovers every `*_test.sh` file under `BUILD-PACKS/*/TEST/`, runs each in turn (sourcing `lib/psql_common.sh`'s connection resolution so a single `LTSA_TEST_DSN` setting governs the whole run), captures pass/fail per script by exit code, and prints a summary (scripts run, passed, failed) with a non-zero overall exit code if any script failed — CI-compatible in shape, though no CI is wired up under this MWO.

**Deliverables:** `VERIFICATION/run_verification.sh`.

**Acceptance Criteria:**
- Discovers all test scripts across all three registries' `TEST/` directories without hardcoding a fixed list (so a future fourth registry's tests are picked up automatically).
- Produces a clear, unambiguous pass/fail summary — never an implied result.
- Does not modify any discovered test script.

**Required Validation:** Shell syntax validation; a structural dry-run against the discovery logic only (listing which files would be executed, without requiring a live database) to confirm Customer Registry's 6 existing scripts and the new Pump/Seal scripts (WP-003) are all correctly discovered.

**Known Risks:** Customer Registry's existing test scripts each inline their own connection logic rather than sourcing a shared library (per WP-001's decision not to modify them). The runner must therefore invoke each script as an independent process respecting its own `LTSA_TEST_DSN`/env-var resolution, not assume every script sources `psql_common.sh` — a compatibility constraint the runner's design must account for, not paper over.

---

## WP-003 — Registry Verification Suite

**Objective:** Close the test-coverage gap for Pump Registry and Seal Registry — both currently at zero written tests (`PM-003`, MWO-P-005 Completion Report) — bringing all three registries to equivalent test coverage.

**Scope:** New files, one per operation, structurally identical to `customer_create_test.sh` through `customer_by_code_test.sh` (fixture setup, assertion, `trap`-based cleanup, honest labeling of any check that cannot be executed by `psql` alone):
- `BUILD-PACKS/BP-PUMP/TEST/pump_create_test.sh`, `pump_detail_test.sh`, `pump_list_test.sh`, `pump_update_test.sh`, `pump_delete_test.sh` — verifying the SQL logic in `MODULES/PUMP/WORKFLOWS/*.json` (identifier: `tag_number`, per `PM-000`/`PM-002`'s established convention).
- `BUILD-PACKS/BP-SEAL/TEST/seal_create_test.sh`, `seal_detail_test.sh`, `seal_list_test.sh`, `seal_update_test.sh`, `seal_delete_test.sh` — verifying the SQL logic in `BUILD-PACKS/BP-SEAL/WORKFLOWS/*.json` (identifier: `seal_code`, per `SM-000`'s established convention).

**Deliverables:** 10 new test scripts (5 Pump, 5 Seal).

**Acceptance Criteria:**
- Each script asserts the same class of behavior its Customer Registry equivalent does: valid-operation success, not-found handling, and — for Create — conflict handling, matching each workflow's actual implemented logic (read from the workflow file, not assumed from the Customer pattern).
- Each script cleans up its own fixture data via `trap`, matching the isolation discipline `customer_delete_test.sh` established.
- No script modifies any workflow file.

**Required Validation:** Shell syntax validation (`bash -n`) for all 10 scripts; static review of each script's query/assertions against the actual corresponding workflow file's SQL and the canonical schema.

**Known Risks:** None beyond the standing absence of a usable database connection. Pump's Create workflow's conflict-check pattern (`PM-001`... — actually Customer's `CR-001`, reused by Pump's own Create/Update logic per `PM-002`) and Seal's Create conflict-check (this MWO's own Seal Completion Report) must each be verified against their *own* actual implementation, not assumed identical to Customer's, since minor differences (e.g., Seal's lack of a surrogate `id` column) affect what a correct assertion checks for.

---

## WP-004 — Verification Report

**Objective:** Attempt actual execution of the full verification suite via the runner (WP-002), against whatever database connection is available at implementation time, and report the outcome honestly regardless of result.

**Scope:** Run `VERIFICATION/run_verification.sh`. If a usable `LTSA_TEST_DSN` (or equivalent `libpq` environment configuration) is available, execute for real and record actual PASS/FAIL results per script. If not — consistent with every prior attempt this sprint — state that plainly, name the specific blocking condition, and report the infrastructure's readiness state instead (built, structurally validated, discovery-confirmed, execution-blocked by one missing input).

**Deliverables:** `ENGINEERING/MWO/RV-004-Verification-Report.md` — this work package's actual output, distinct from the MWO's overall Completion Report (see Execution Rules).

**Acceptance Criteria:**
- The report states, per script, one of: executed-and-passed, executed-and-failed (with the specific failure), or not-executed (with the specific reason).
- No result is implied, assumed, or extrapolated from a partial run.
- If execution is blocked, the report states exactly what input would unblock it (e.g., "set `LTSA_TEST_DSN` to a reachable PostgreSQL connection string with `DATABASE/CANONICAL_SCHEMA.sql` applied") — the infrastructure this MWO builds should make that the *only* remaining gap, not one gap among several.

**Required Validation:** N/A — this work package's entire content is the validation attempt and its outcome.

**Known Risks:** This is the one work package in this MWO whose outcome cannot be predicted at drafting time. It may fully succeed (if a connection becomes available), partially succeed, or be entirely blocked again. All three outcomes are acceptable and must be reported as what actually happened — an MWO that builds real infrastructure but still cannot execute it is a genuine, honestly-reported improvement over an MWO with no infrastructure at all, not a failure of this MWO.

---

## Execution Order

WP-000 (Planning, individually approved) → **[approval]** → WP-001 (Framework) → WP-002 (Runner) → WP-003 (Suite) → WP-004 (Verification Report), executed as one continuous batch → **[Completion Report, then stop]**.

Rationale: WP-001 must exist before WP-002 can source it; WP-002 must exist before WP-003's scripts can be run by it; WP-004 requires all three. The sequence is a technical dependency chain, not merely a stylistic choice, unlike the largely-independent work packages in MWO-P-003/004/005.

## Expected Deliverables

- `VERIFICATION/lib/psql_common.sh`, `VERIFICATION/bootstrap_schema.sh` (WP-001)
- `VERIFICATION/run_verification.sh` (WP-002)
- 10 new test scripts across `BP-PUMP/TEST/` and `BP-SEAL/TEST/` (WP-003)
- `RV-004-Verification-Report.md` (WP-004)
- No product workflow file touched; no API specification touched; no CI/CD artifact created.

## Expected Reports

- `RV-000` is not a separate file — the Runtime Verification Planning section above, once approved, stands as WP-000's record within this MWO document itself.
- `RV-004-Verification-Report.md` — WP-004's named deliverable (see Execution Rules item 3).
- One `MWO-P-006-Completion-Report.md`, produced after the full batch, aggregating WP-001–WP-004.
- No individual report for WP-001–WP-003 unless a BLOCKER occurs in one of them.

## Definition of Done

- WP-000's Runtime Verification Planning confirmed and individually approved before WP-001 begins.
- Verification Framework and Runner built and structurally validated.
- Pump and Seal test coverage reaches parity with Customer Registry's existing 6 scripts (10 new scripts, 16 total across the product).
- WP-004's execution attempt occurred and is reported honestly, whatever its outcome.
- No product workflow, schema, or API specification file was modified.
- No architectural change was introduced anywhere in this MWO.
- Nothing committed or pushed without explicit Chief Architect approval.

---

This document has been created per Chief Architect instruction, in Document Drafting Mode (Engineering Standard v1.0 §13). Implementation has not started. No repository file other than this MWO document was modified in producing it. No commit, no push.
