# MWO-P-007 — LTSA Python Adapter

Status: DRAFT — WORK ORDER ONLY, NO IMPLEMENTATION PERFORMED
Type: Manufacturing Work Order (Integration Adapter)
Role: Implementation Engineer
Architecture: FROZEN — no new architecture, service, table, framework, registry, or runtime proposed
Phase: LTSA Runtime — Pump Registry Python exposure (dependency gap identified during the LTSA Work Order Runtime dependency verification, Sprint 018)
Basis: `ENGINEERING/MWO/MWO-P-004-Pump-Registry-Functional-Completion.md` (Pump Registry's locked canonical map) — no new audit scope opened
Scope: `CORE-SERVICES/API` adapter only

---

## Executive Summary

During the LTSA Work Order Runtime effort (Sprint 018), dependency verification found that Pump Registry has no Python-callable interface: it exists only as n8n workflow JSON (`PRODUCTS/LTSA-BRAIN/MODULES/PUMP/WORKFLOWS/*.json`), invoked over HTTP webhook, backed by the canonical `ltsa_pumps` Postgres table (`MODULES/PUMP/DATABASE/001_create_pumps.sql`). LTSA Runtime implementation was correctly not attempted against that gap.

This MWO closes the gap with the smallest possible addition: a stateless Python pass-through that calls each already-deployed, already-canonical Pump webhook and returns its response unchanged. It does not reimplement Pump Registry, does not talk to Postgres directly, and does not introduce a second implementation of any Pump operation.

---

## Objective

Expose the existing, already-canonical Pump Registry (Create / Detail / List / Update / Delete, per MWO-P-004's locked canonical map) to Python callers, by wrapping each canonical n8n webhook call in a single call-through function per operation. No new logic, no new storage, no new registry.

---

## Scope

- One new file: `CORE-SERVICES/API/pump_adapter.py` — one function per canonical Pump operation. Each function does exactly: accept the same input the corresponding webhook already accepts → invoke that webhook → return its response unchanged.
- One matching test file: `CORE-SERVICES/API/TESTS/test_pump_adapter.py`, exercising call-through behavior against a fake/stub transport (no live n8n or Postgres, consistent with this product's established Structural-Validation-only pattern).

## Out of Scope

- No new Registry object, dataclass, or artifact model for Pump — this is not a second Pump Registry.
- No new Runtime — the adapter does not touch `ManufacturingOrder`, `DigitalFactory`, or `ManufacturingRecipe`. A Pump is not manufactured; it already exists.
- No new Manufacturing capability, recipe, or production line.
- No business logic — no default values, no derived fields, no validation rules beyond what invoking the webhook already requires. The adapter must not branch on Pump field values or compute anything.
- No direct SQL and no database connection from Python — the adapter calls the existing workflow; it does not re-implement or duplicate the SQL already embedded in `MODULES/PUMP/WORKFLOWS/*.json`.
- No change to any `MODULES/PUMP/WORKFLOWS/*.json`, `MODULES/PUMP/DATABASE/*.sql`, or `DATABASE/CANONICAL_SCHEMA.sql` file.
- No OpenAPI / API specification work.
- No UI.
- No Organization Registry, Organization Dashboard, Company, Department, or Role code touched.
- No Work Order or Maintenance History integration — those remain blocked pending their own equivalent adapter MWOs, not addressed here.

## Reuse

- **Existing SQL**: `ltsa_pumps` (`MODULES/PUMP/DATABASE/001_create_pumps.sql`, canonical per MWO-P-004 WP-000) — reached only through the workflow, never queried directly by the adapter.
- **Existing Pump workflow** — canonical map locked by MWO-P-004:
  - Create: `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-REGISTRY-001.json`
  - Detail: `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-PUMP-DETAIL-001.json`
  - List: `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-LIST-001.json`
  - Update: `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-UPDATE-001.json`
  - Delete: `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-DELETE-001.json`
- **Existing credential**: `hzgFaX04t1nL01vF` / "Postgres account" — already resolved inside the workflows; the adapter never handles it, since it only calls each workflow's webhook rather than connecting to Postgres itself.

## Dependencies

- **MWO-P-004** — this MWO depends entirely on its locked Pump Registry Canonical Map (Create/Detail/List/Update/Delete file identities above). That map is inherited, not re-derived or re-litigated.
- **LTSA Work Order Runtime dependency verification (Sprint 018)** — the finding that motivated this MWO: no Python-callable Pump interface exists. Accepted as the problem statement, not re-investigated.

## Constraints

- Architecture is frozen — no new table, service, credential mechanism, registry, or runtime.
- The adapter owns no state: no artifact files, no new directories, no persistence of any kind.
- The adapter contains no business logic beyond what is mechanically required to invoke a webhook and return its response.
- The adapter must not become a second source of truth or a second implementation of any Pump operation — call-through only.
- No modification to any file outside `CORE-SERVICES/API/` (the adapter and its test).
- **Canonical Mapping Lock inherited from MWO-P-004**: if any Pump workflow file appears inconsistent with MWO-P-004's locked map during implementation, STOP. Document the evidence. Recommend a new MWO. Wait for approval. Do not fix, do not choose a different canonical file, do not continue implementation.

---

## Deliverables

- `CORE-SERVICES/API/pump_adapter.py`
- `CORE-SERVICES/API/TESTS/test_pump_adapter.py`
- This MWO document

## Acceptance Criteria

- Each exposed function corresponds 1:1 to an existing canonical Pump operation from MWO-P-004's locked map; no operation is invented.
- No SQL string appears anywhere in the adapter or its tests.
- No new persistent file, directory, or table is created by the adapter itself.
- Tests exercise call-through behavior only, via a fake/stub transport — no live n8n or Postgres interaction, consistent with MWO-P-004/MWO-P-005's Structural-Validation-only precedent.

## Definition of Done

- Adapter implemented exactly as scoped above — no more, no less.
- Tests pass.
- Full existing regression suite (`AI5R-SDK/MANUFACTURING`, `CORE-SERVICES/API`) still passes unchanged.
- Nothing committed or pushed without explicit, separate approval.

---

**Status: WAITING FOR APPROVAL. No implementation performed. No file other than this MWO document has been created or modified.**
