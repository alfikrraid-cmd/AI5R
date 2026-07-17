# MWO-P-001 — LTSA Product Audit

Status: EVIDENCE ONLY — READ-ONLY, NO IMPLEMENTATION PERFORMED
Type: Mission Work Order (Product Audit)
Role: Senior Software Engineer
Architecture: FROZEN — no architectural change proposed
Scope: `PRODUCTS/LTSA-BRAIN` and only the code/runtime/API/database/workflow/test/release assets it actually uses. Repository governance, ADRs, RC records, Constitution, and RepositoryPack are explicitly out of scope and not referenced below.

---

## Location Note (read this before the rest of the document)

`PRODUCTS/LTSA-BRAIN` does not exist on `main` and was not present in the working tree used for prior engineering-governance work in this repository. It exists only on the remote branch `origin/feature/ltsa-brain` (799 commits total; diverges from `main` at `92fa68f`, 749 commits of its own beyond that point; branch tip `c0841279`, dated 2026-07-11). This audit was performed entirely read-only against that branch tip via `git ls-tree` / `git show <ref>:<path>`, without checking the branch out — the local working tree (`main`) was not touched.

Three release tags exist on this branch (`v0.1.0-rc1`, `beta-v1.0`, `gamma-v1.0`); none is specific to LTSA-BRAIN — their commit messages concern unrelated platform/architecture milestones (see §8).

Two other LTSA-adjacent directories exist on the same branch — `AI5R-SDK/PRODUCTS/LTSA_BRAIN/` (an older, differently-named cognitive-engine Python package) and `AI5R-SDK/BRAIN/` / `AI5R-SDK/LTSA/`. A repository-wide search found no import or reference from `PRODUCTS/LTSA-BRAIN` into any of these, and no reference the other way; they are excluded from this audit as unrelated per the work order's scope rule. One unrelated file, `AI5R-SDK/FACTORY/TESTS/test_sql_generator.py`, contains one of the audited table names as a generic test fixture and is noted here for completeness but not analyzed further.

---

## 1. Product Overview

Source: `PRODUCTS/LTSA-BRAIN/product.manifest.json`

| Field | Value |
|---|---|
| Name | LTSA-BRAIN ("LTSA Brain") |
| Description | "Industrial Asset Reliability Platform" |
| Company | AI5R |
| Type | SaaS |
| Manifest version | 1.0.0 |
| Root `VERSION` file (branch tip) | `0.1.0-dev` — **contradicts** the manifest's declared version (see §8) |
| Declared modules (`enabled: true`) | customer, pump, asset, inspection, maintenance |

`PRODUCTS/LTSA-BRAIN/CORE/README.md` describes a "Core SDK" intended as the shared foundation ("standard response, validation, audit log, database helper, workflow templates, module generator foundation") for Pump, Seal, Asset, PM Planner, CM Work Order, and Billing — none of which exist as actual code; `CORE/` contains only this README.

Total tracked files under `PRODUCTS/LTSA-BRAIN` at branch tip: 67.

---

## 2. Current Features

| Module | Declared in manifest? | Artifacts found |
|---|:---:|---|
| Customer | Yes | `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/` (stub workflows), `API/customer-registry/API_CONTRACT.md`, `DATABASE/MIGRATIONS/005_create_customer_registry.sql` |
| Pump | Yes | **Two parallel, non-reconciled implementations**: `BUILD-PACKS/BP-PUMP/` (factory-generated stubs) and `MODULES/PUMP/` (real DB schema, one real workflow, partial API, two empty UI files, spec doc) |
| Asset | Yes | None found anywhere in the tree |
| Inspection | Yes | None found anywhere in the tree |
| Maintenance | Yes | None found anywhere in the tree |
| Seal | **No** (absent from manifest's module list) | `BUILD-PACKS/BP-SEAL/` (stub workflows) + `REGISTRIES/SEAL.json` (internally consistent with its own DB schema) |
| Equipment | No | `BUILD-PACKS/BP-EQUIPMENT/README.md` — 3 lines, no DB/API/workflow |

Three of five manifest-declared modules (asset, inspection, maintenance) have zero implementation of any kind. One module with real implementation depth (seal) isn't declared in the manifest at all.

---

## 3. Database

No single canonical schema exists. At least four independent, non-reconciled schema definitions were found:

1. **`PRODUCTS/LTSA-BRAIN/RELEASE/database.sql` + `RELEASE/schema.json`** — generic, identically-shaped 6-field boilerplate (`id SERIAL`, `code`, `name`, `status`, `created_at`, `updated_at`) for tables `ltsa_customers`, `ltsa_pumps`, `ltsa_assets`, `ltsa_inspections`, `ltsa_maintenances`. This is the only DB artifact that exists for asset/inspection/maintenance, and it is pure generated scaffolding with no domain fields.
2. **`PRODUCTS/LTSA-BRAIN/DATABASE/MIGRATIONS/005_create_customer_registry.sql`** — a real, detailed `customer_registry` table (UUID PK, 14 columns incl. `customer_code`, `industry`, `billing_email`, 2 indexes). Different table name and shape than (1)'s `ltsa_customers`.
3. **`PRODUCTS/LTSA-BRAIN/MODULES/PUMP/DATABASE/001_create_pumps.sql`** — a real `ltsa_pumps` table (UUID PK, `tag_number`, `area`, `pump_type`, `api_plan`, `seal_type`, etc., 13 columns + 3 indexes). **Same table name as (1)'s `ltsa_pumps` but an incompatible column set and a different primary-key type (UUID vs. SERIAL)** — a direct naming collision between two DDL scripts.
4. **`PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-PUMP/DATABASE/{001_create_table,002_seed,003_indexes,999_rollback}.sql`** — a third pump table, `public.pump_registry` (TEXT PK `pump_code`, 9 columns). Matches `BP-PUMP/README.md`'s stated table name, but not (1) or (3).
5. **`PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-SEAL/DATABASE/*.sql` + `REGISTRIES/SEAL.json`** — `public.seal_registry` (TEXT PK `seal_code`, 9 columns, incl. `shaft_size`, `material`, `temperature_limit`, `pressure_limit`). This is the one case where the registry document and DDL agree with each other.

No migration-runner script, no `schema_migrations`-style tracking table, and no CI job applying any of these `.sql` files was found anywhere in the tree. `DATABASE/MIGRATIONS/` (top-level, product-wide) contains a single file numbered `005`, with nothing for 001–004.

---

## 4. APIs

**Implemented (contract + working logic behind it):** none confirmed.

**Partial:**
- `MODULES/PUMP/API/openapi.yaml` — a real `Pump` schema with the domain fields matching (Database, item 3), but only `GET /pumps` (list) and `POST /pumps` (create) are defined. No get-by-id, update, or delete operation exists, despite the pump spec doc (`MODULES/PUMP/DOCS/PUMP_REGISTRY_SPEC.md`) listing five downstream consumers ("Used By: Seal Registry, PM Planner, CM Work Order, Inspection History, Billing Report") that would need more than list/create.
- `API/customer-registry/API_CONTRACT.md` — documents a full 5-operation contract (create/list/get/update/delete) as **n8n webhook paths** (`/webhook/ltsa/customer/create`, etc.).
- `RELEASE/openapi.json` — a full generic REST CRUD surface (`/customers`, `/customers/{id}`, `/pumps`, `/pumps/{id}`, `/assets`, `/assets/{id}`, `/inspections`, `/inspections/{id}`, `/maintenances`, `/maintenances/{id}`) but every response is an empty stub ("Successful response", no request/response body schema anywhere) — generated boilerplate, not a working contract.

**Missing:** no API surface of any kind for asset, inspection, or maintenance (consistent with §3).

**Conflicting convention:** the customer API is specified two incompatible ways in the same product — n8n webhook paths in `API_CONTRACT.md` vs. generic REST paths in `RELEASE/openapi.json` — with nothing in the repository indicating which is authoritative.

---

## 5. Runtime

No application server or backend framework code exists anywhere under `PRODUCTS/LTSA-BRAIN`, and a repository-wide search for the product's table names outside that folder found no runtime consumer (see Location Note).

The only executable "runtime" artifacts are n8n workflow JSON files (n8n is an already-hosted, external workflow-automation tool at `https://n8n.osa-system.com` — not part of this repository).

- **10 of 11** workflow files found (`BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/*.json` × 5, `BUILD-PACKS/BP-PUMP/WORKFLOWS/*.json` × 5) are factory-generated stubs: a single `Webhook` trigger node wired directly to a `Respond to Webhook` node returning a **hardcoded static JSON string** (e.g. `{"success": true, "product": "LTSA-BRAIN", ...}`), with no database node, no input validation, and no dependency on the actual request body. They do not read or write any data.
- **1 workflow** (`MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-REGISTRY-001.json`, pump "create") has real logic: a JS validation node (requires `tag_number`, `area`) → a PostgreSQL `INSERT ... RETURNING *` node → a JSON response node. This is the only workflow in the product with genuine business logic. It ships with an unresolved placeholder credential (`"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID"`) and cannot execute against a real database as committed.
- `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/` contains code-generation tooling (`compile_detail_workflow.py`, `generate_workflows.py`, `parse_template.py`) for producing more workflow JSON; no evidence it is wired into an actual execution pipeline or CI step.
- No evidence anywhere in the repository that any workflow has actually been imported into a live n8n instance. `TEST-REPORTS/FM-001.5-FACTORY-ACCEPTANCE-TEST.md` (the product's own acceptance report) explicitly marks "Import generated workflow into n8n" as **READY FOR MANUAL IMPORT** and "Verify endpoint against PostgreSQL" as **PENDING PRODUCTION TEST** — i.e., not done, by the product's own record.

---

## 6. UI

Exactly two UI files exist in the entire product: `MODULES/PUMP/UI/PumpRegistryPage.tsx` and `MODULES/PUMP/UI/PumpDetailPage.tsx`. **Both are 0 bytes.** No frontend application, build configuration, or routing was found anywhere under `PRODUCTS/LTSA-BRAIN` to host them. No UI exists for customer, seal, or any other module.

---

## 7. Tests

- `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/TEST/customer_registry_test.sh` — a single `curl` call against the external hosted URL `https://n8n.osa-system.com/webhook/ltsa/customer/create`, with no assertion on the response body or status code beyond a bare `set -e` (which does not fail on an HTTP error status without curl's `-f` flag). Not runnable from this repository without that external, unverifiable service.
- Each build pack's `verify.py` (present for BP-005; not found for BP-PUMP, BP-SEAL, BP-007, BP-EQUIPMENT) checks only that its declared output files **exist**, and that `.json` files **parse** — no functional or integration assertions.
- `TEST-REPORTS/` contains 4 hand-written Markdown status documents, not automated test-runner output; no CI configuration, pytest file, or test log was found anywhere under `PRODUCTS/LTSA-BRAIN` to substantiate their "PASSED" claims:
  - `FM-001.5-FACTORY-ACCEPTANCE-TEST.md` self-reports 2 of its own 7 acceptance criteria as unmet ("READY FOR MANUAL IMPORT", "PENDING PRODUCTION TEST") and a third as pending ("Commit and Push: PENDING").
  - `FM-001.9-MANUFACTURING-ENGINE-TEST.md` and `LT-004-FACTORY-REGRESSION-SUITE.md` verify only that the code-generation tooling produced well-formed files (valid JSON/SQL), not that the resulting system functions or that its schemas are mutually consistent — they would not have caught the table-name collisions in §3.
  - `BC-22-PRODUCTION-VERIFICATION.md` claims a live, successful production webhook verification (`https://n8n.osa-system.com/webhook/ltsa/pump/detail?tag_number=P-101`, table `public.ltsa_pumps`) for a workflow named `WF-LTSA-PUMP-DETAIL-001`. **No file by that name exists anywhere in `PRODUCTS/LTSA-BRAIN`** — the only pump workflow present is the CREATE workflow in `MODULES/PUMP/WORKFLOWS/`. This report references an artifact this audit could not locate.
- No unit tests exist for the BP-007 code-generation scripts.

---

## 8. Release Artifacts

- Root `VERSION` (branch tip): `0.1.0-dev` — **contradicts** `product.manifest.json`'s declared `"version": "1.0.0"` (§1).
- Root `CHANGELOG.md` (branch tip) is titled "LTSA Brain Changelog" and ends at **BP-004** ("Initialize LTSA Core SDK"). None of BP-001–BP-004 correspond by number to any directory that currently exists under `BUILD-PACKS/` (which contains BP-005, BP-007, BP-EQUIPMENT, BP-PUMP, BP-SEAL — no BP-001–004 or BP-006). The changelog's descriptions for BP-001–003 ("Pump Registry Database", "API Contract", "Pump Registry Service, PostgreSQL Integration, n8n Workflow") most plausibly correspond in content to what is now `MODULES/PUMP/`, but nothing in the repository states that mapping explicitly — it is inferred here from matching content only, not confirmed.
- No LTSA-BRAIN-specific release tag exists. The three tags reachable on this branch — `v0.1.0-rc1` ("AX-303: add Cross-Domain Intelligence Framework"), `beta-v1.0` ("CR-010: stabilize capability and integration tests"), `gamma-v1.0` ("AX-007: freeze kernel integration architecture") — are all cut at commits about unrelated platform/architecture milestones, not LTSA-BRAIN specifically.
- `RELEASES/ARCHIVE/` (repository root) contains only `AI5R-Repository-Pack-v1.0.zip`, an unrelated governance/constitution package — no packaged or versioned artifact of LTSA-BRAIN itself exists.
- `PRODUCTS/LTSA-BRAIN/RELEASE/` (`openapi.json`, `schema.json`, `database.sql`) is the closest thing to a release bundle, but per §3–4 its contents are generic/generated and inconsistent with the product's own build-pack- and module-level artifacts.

---

## 9. Deployment Assets

None found under `PRODUCTS/LTSA-BRAIN`: no Dockerfile, no CI/CD workflow definition, no infrastructure-as-code, no environment/config template. The product's only implied deployment dependencies — an n8n instance at `https://n8n.osa-system.com` and a PostgreSQL database (`ltsa_brain`, per `BC-22-PRODUCTION-VERIFICATION.md`) — are external and unprovisioned from anything in this repository or branch.

---

## Missing Features

| # | Feature | Evidence |
|---|---|---|
| M1 | Asset module (DB, API, workflow, UI) | Declared `enabled: true` in manifest; zero artifacts found (§2, §3, §4) |
| M2 | Inspection module (DB, API, workflow, UI) | Same as M1 |
| M3 | Maintenance module (DB, API, workflow, UI) | Same as M1 |
| M4 | Equipment module beyond a 3-line README | `BUILD-PACKS/BP-EQUIPMENT/README.md` only (§2) |
| M5 | Any UI beyond two empty files | §6 |
| M6 | Any deployment/CI asset | §9 |
| M7 | Pump list/detail/update/delete workflows | Only CREATE exists under `MODULES/PUMP/WORKFLOWS/` (§5) |

## Broken Features

| # | Feature | Evidence |
|---|---|---|
| B1 | `ltsa_pumps` table defined twice with incompatible schemas (SERIAL/generic vs. UUID/domain-specific) | §3, items 1 & 3 |
| B2 | Customer entity split across two non-corresponding table definitions (`customer_registry` UUID vs. `ltsa_customers` SERIAL) | §3, items 1 & 2 |
| B3 | Pump entity split across three non-corresponding table definitions (`pump_registry`, two `ltsa_pumps` variants) | §3, items 1, 3 & 4 |
| B4 | BP-PUMP's and BP-005's factory-generated workflows return hardcoded static success responses regardless of input — no persistence or query occurs despite their own release notes/test reports claiming functioning CRUD | §5, §7 |
| B5 | The one workflow with real DB logic ships with an unresolved placeholder PostgreSQL credential and cannot execute as committed | §5 |
| B6 | `BC-22-PRODUCTION-VERIFICATION.md` claims production verification of a workflow file (`WF-LTSA-PUMP-DETAIL-001`) that does not exist in the repository | §7 |

## Incomplete Features

| # | Feature | Evidence |
|---|---|---|
| I1 | Customer Registry: 5-operation contract documented, 0 operations have real logic behind them | §4, §5, §7 |
| I2 | Pump Registry (MODULES path): only create is implemented with real logic; list/detail/update/delete are documented but not built | §4, §5 |
| I3 | Seal Registry: DB schema internally consistent, but same stub-workflow pattern as BP-PUMP (no verified real logic; `LT-003` report only confirms artifacts were *generated*, not functional) | §3, §5, §7 |
| I4 | Version identity inconsistent (`product.manifest.json` 1.0.0 vs. `VERSION` file 0.1.0-dev) | §1, §8 |
| I5 | `CHANGELOG.md` stopped at BP-004; 5 later build packs undocumented | §8 |
| I6 | BP-007 workflow-generator tooling has no tests and no confirmed integration into the other build packs' generation flow | §5, §7 |

---

## Implementation Backlog (ordered by production impact)

### MWO-P-001-001 — Resolve the `ltsa_pumps` schema collision

**Objective:** Two independent DDL scripts create a table named `ltsa_pumps` with incompatible primary-key types and column sets (`RELEASE/database.sql`: SERIAL/generic; `MODULES/PUMP/DATABASE/001_create_pumps.sql`: UUID/domain-specific). Applying both to one database fails or silently corrupts the schema depending on execution order.
**Evidence Source:** §3, items 1 & 3; Broken Feature B1.
**Affected Components:** `PRODUCTS/LTSA-BRAIN/RELEASE/database.sql`, `PRODUCTS/LTSA-BRAIN/MODULES/PUMP/DATABASE/001_create_pumps.sql`.
**Dependencies:** None.
**Estimated Complexity:** M
**Priority:** Critical
**Category:** Database

---

### MWO-P-001-002 — Resolve the customer table duplication

**Objective:** `customer_registry` (UUID, 14 columns) and `ltsa_customers` (SERIAL, 6 columns) both represent "customer" with no reconciliation; pick one as authoritative and retire the other.
**Evidence Source:** §3, items 1 & 2; Broken Feature B2.
**Affected Components:** `PRODUCTS/LTSA-BRAIN/DATABASE/MIGRATIONS/005_create_customer_registry.sql`, `PRODUCTS/LTSA-BRAIN/RELEASE/database.sql`.
**Dependencies:** None.
**Estimated Complexity:** M
**Priority:** Critical
**Category:** Database

---

### MWO-P-001-003 — Replace the placeholder PostgreSQL credential in the pump-create workflow

**Objective:** The only workflow in the product with real logic (`MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-REGISTRY-001.json`) references an unresolved credential ID and cannot run as committed.
**Evidence Source:** §5; Broken Feature B5.
**Affected Components:** `PRODUCTS/LTSA-BRAIN/MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-REGISTRY-001.json`.
**Dependencies:** None.
**Estimated Complexity:** S
**Priority:** Critical
**Category:** Runtime

---

### MWO-P-001-004 — Correct or retract the BC-22 production-verification claim

**Objective:** `BC-22-PRODUCTION-VERIFICATION.md` asserts a successful production verification of a workflow file that does not exist in the repository (`WF-LTSA-PUMP-DETAIL-001`). Leaving this uncorrected misrepresents the product's actual production-readiness.
**Evidence Source:** §7; Broken Feature B6.
**Affected Components:** `PRODUCTS/LTSA-BRAIN/TEST-REPORTS/BC-22-PRODUCTION-VERIFICATION.md`.
**Dependencies:** None.
**Estimated Complexity:** S
**Priority:** Critical
**Category:** Testing

---

### MWO-P-001-005 — Consolidate the two pump implementations

**Objective:** `BUILD-PACKS/BP-PUMP/` (stub workflows, `pump_registry` table) and `MODULES/PUMP/` (real schema/workflow, `ltsa_pumps` table) are separate, non-reconciled implementations of the same module. Merge into one authoritative implementation.
**Evidence Source:** §2, §3, §5; Broken Feature B3.
**Affected Components:** `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-PUMP/`, `PRODUCTS/LTSA-BRAIN/MODULES/PUMP/`.
**Dependencies:** MWO-P-001-001.
**Estimated Complexity:** L
**Priority:** High
**Category:** Database

---

### MWO-P-001-006 — Implement real logic for the Customer Registry workflows

**Objective:** Replace the 5 stub workflows (webhook → hardcoded static response) with real validation, database read/write, and response logic, matching `API_CONTRACT.md`'s documented 5 operations.
**Evidence Source:** §4, §5, §7; Broken Feature B4; Incomplete Feature I1.
**Affected Components:** `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/*.json`.
**Dependencies:** MWO-P-001-002.
**Estimated Complexity:** L
**Priority:** High
**Category:** Runtime

---

### MWO-P-001-007 — Implement the missing pump list/detail/update/delete workflows

**Objective:** Only pump "create" has a real workflow. The spec doc (`PUMP_REGISTRY_SPEC.md`) lists 5 downstream consumers that require read/update access; build the remaining 4 operations.
**Evidence Source:** §4, §5; Missing Feature M7; Incomplete Feature I2.
**Affected Components:** `PRODUCTS/LTSA-BRAIN/MODULES/PUMP/WORKFLOWS/`, `PRODUCTS/LTSA-BRAIN/MODULES/PUMP/API/openapi.yaml`.
**Dependencies:** MWO-P-001-005.
**Estimated Complexity:** M
**Priority:** High
**Category:** Runtime

---

### MWO-P-001-008 — Establish one authoritative API contract per module

**Objective:** Resolve the webhook-path-vs-REST-path convention conflict for customer, and replace `RELEASE/openapi.json`'s empty-schema generic CRUD stubs with real, module-specific request/response schemas.
**Evidence Source:** §4.
**Affected Components:** `PRODUCTS/LTSA-BRAIN/API/customer-registry/API_CONTRACT.md`, `PRODUCTS/LTSA-BRAIN/RELEASE/openapi.json`, `PRODUCTS/LTSA-BRAIN/MODULES/PUMP/API/openapi.yaml`.
**Dependencies:** MWO-P-001-006, MWO-P-001-007.
**Estimated Complexity:** M
**Priority:** High
**Category:** API

---

### MWO-P-001-009 — Replace stub verification with real functional tests

**Objective:** Current `verify.py` scripts check only file existence/JSON validity; the one shell test performs an unassorted `curl` against an external, unverifiable host. Add tests that assert actual behavior (response bodies, DB state) against a controllable environment.
**Evidence Source:** §7.
**Affected Components:** `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/{verify.py,TEST/customer_registry_test.sh}`, and equivalent additions for BP-PUMP/BP-SEAL/MODULES/PUMP.
**Dependencies:** MWO-P-001-006, MWO-P-001-007.
**Estimated Complexity:** M
**Priority:** High
**Category:** Testing

---

### MWO-P-001-010 — Implement real logic for the Seal Registry workflows

**Objective:** Seal's DB schema is internally consistent, but its workflows follow the same stub pattern as BP-PUMP (hardcoded static response, no persistence).
**Evidence Source:** §3, §5, §7; Incomplete Feature I3.
**Affected Components:** `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-SEAL/WORKFLOWS/*.json`.
**Dependencies:** MWO-P-001-001 pattern (none direct, but should follow the consolidated pump approach from MWO-P-001-005).
**Estimated Complexity:** M
**Priority:** Medium
**Category:** Runtime

---

### MWO-P-001-011 — Implement the Pump Registry/Detail UI pages

**Objective:** `PumpRegistryPage.tsx` and `PumpDetailPage.tsx` exist as 0-byte placeholders with no surrounding frontend application.
**Evidence Source:** §6; Missing Feature M5.
**Affected Components:** `PRODUCTS/LTSA-BRAIN/MODULES/PUMP/UI/*.tsx`.
**Dependencies:** MWO-P-001-007.
**Estimated Complexity:** L
**Priority:** Medium
**Category:** Runtime

---

### MWO-P-001-012 — Build the asset, inspection, and maintenance module foundations

**Objective:** Three of five manifest-declared modules have zero DB/API/workflow artifacts. Either build their foundation (schema, contract, first workflow) or set `enabled: false` in `product.manifest.json` until they are built.
**Evidence Source:** §2, §3, §4; Missing Features M1–M3.
**Affected Components:** New `BUILD-PACKS/`/`MODULES/` entries for asset, inspection, maintenance; `PRODUCTS/LTSA-BRAIN/product.manifest.json`.
**Dependencies:** None (independent of pump/customer/seal work).
**Estimated Complexity:** XL
**Priority:** Medium
**Category:** Database

---

### MWO-P-001-013 — Reconcile `CHANGELOG.md` with the actual `BUILD-PACKS` inventory

**Objective:** The changelog stops at BP-004 while BP-005, BP-007, BP-EQUIPMENT, BP-PUMP, and BP-SEAL exist undocumented; the BP-001–004 entries' relationship to `MODULES/PUMP/` is inferred, not stated.
**Evidence Source:** §8; Incomplete Feature I5.
**Affected Components:** `CHANGELOG.md` (repository root, branch tip).
**Dependencies:** MWO-P-001-005 (numbering should reflect the consolidated pump implementation).
**Estimated Complexity:** S
**Priority:** Medium
**Category:** Documentation

---

### MWO-P-001-014 — Reconcile the product version identity

**Objective:** `product.manifest.json` declares version `1.0.0`; the root `VERSION` file declares `0.1.0-dev`. Pick one authoritative value.
**Evidence Source:** §1, §8; Incomplete Feature I4.
**Affected Components:** `PRODUCTS/LTSA-BRAIN/product.manifest.json`, `VERSION` (repository root, branch tip).
**Dependencies:** None.
**Estimated Complexity:** S
**Priority:** Medium
**Category:** Documentation

---

### MWO-P-001-015 — Add deployment assets for the PostgreSQL database and n8n workflow import

**Objective:** No Dockerfile, CI/CD definition, or infrastructure-as-code exists for the PostgreSQL database or n8n instance the workflows and test reports assume are already provisioned.
**Evidence Source:** §9.
**Affected Components:** New deployment configuration under `PRODUCTS/LTSA-BRAIN/` (none currently exists).
**Dependencies:** MWO-P-001-001, MWO-P-001-002 (schema must be settled before provisioning).
**Estimated Complexity:** L
**Priority:** Medium
**Category:** Deployment

---

### MWO-P-001-016 — Complete the Equipment module beyond its stub README

**Objective:** `BP-EQUIPMENT/README.md` is 3 lines with no database, API, or workflow content, and isn't declared in `product.manifest.json` at all.
**Evidence Source:** §2; Missing Feature M4.
**Affected Components:** `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-EQUIPMENT/`.
**Dependencies:** None.
**Estimated Complexity:** M
**Priority:** Low
**Category:** Database

---

### MWO-P-001-017 — Cut an LTSA-BRAIN-specific release tag

**Objective:** None of the three tags reachable on this branch are specific to LTSA-BRAIN; once the above items stabilize the product, cut a dedicated version tag/artifact for it.
**Evidence Source:** §8.
**Affected Components:** Git tags; `PRODUCTS/LTSA-BRAIN/RELEASE/`.
**Dependencies:** MWO-P-001-001 through MWO-P-001-009 (core correctness items).
**Estimated Complexity:** S
**Priority:** Low
**Category:** Release

---

## Summary Table

| ID | Title | Priority | Category | Complexity |
|---|---|---|---|---|
| MWO-P-001-001 | Resolve `ltsa_pumps` schema collision | Critical | Database | M |
| MWO-P-001-002 | Resolve customer table duplication | Critical | Database | M |
| MWO-P-001-003 | Fix placeholder PostgreSQL credential | Critical | Runtime | S |
| MWO-P-001-004 | Correct/retract BC-22 false verification claim | Critical | Testing | S |
| MWO-P-001-005 | Consolidate the two pump implementations | High | Database | L |
| MWO-P-001-006 | Implement real Customer Registry workflow logic | High | Runtime | L |
| MWO-P-001-007 | Implement missing pump list/detail/update/delete | High | Runtime | M |
| MWO-P-001-008 | Establish one authoritative API contract per module | High | API | M |
| MWO-P-001-009 | Replace stub verification with real functional tests | High | Testing | M |
| MWO-P-001-010 | Implement real Seal Registry workflow logic | Medium | Runtime | M |
| MWO-P-001-011 | Implement Pump Registry/Detail UI pages | Medium | Runtime | L |
| MWO-P-001-012 | Build asset/inspection/maintenance foundations | Medium | Database | XL |
| MWO-P-001-013 | Reconcile CHANGELOG.md with BUILD-PACKS inventory | Medium | Documentation | S |
| MWO-P-001-014 | Reconcile product version identity | Medium | Documentation | S |
| MWO-P-001-015 | Add deployment assets (DB + n8n provisioning) | Medium | Deployment | L |
| MWO-P-001-016 | Complete the Equipment module | Low | Database | M |
| MWO-P-001-017 | Cut an LTSA-BRAIN-specific release tag | Low | Release | S |

No item above has been implemented, executed, or committed. This document is evidence and backlog only.
