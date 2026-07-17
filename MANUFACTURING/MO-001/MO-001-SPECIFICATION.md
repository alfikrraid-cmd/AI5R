# MO-001 — OSA Maintenance v0.1 — Specification

Manufacturing Order: MO-001
Product: OSA Maintenance v0.1
Customer: CV Razzan Teknik Mandiri
Status: SPECIFICATION
Architecture: FROZEN — no new architecture, service, table pattern, or framework introduced
Reuse basis: `PRODUCTS/LTSA-BRAIN` (already an "Industrial Asset Reliability Platform" per its own manifest, with a canonicalized Customer Registry and Pump Registry already manufactured under MWO-P-002 through MWO-P-006)

---

## 1. Manufacturing Vehicle

OSA Maintenance v0.1 is manufactured **as `PRODUCTS/LTSA-BRAIN`**, not as a new product tree. Reasoning, evidenced:

- `PRODUCTS/LTSA-BRAIN/product.manifest.json` already declares itself an "Industrial Asset Reliability Platform," already declares `customer` and `pump` modules as `partial`, and already has a canonicalized schema (`DATABASE/CANONICAL_SCHEMA.sql`, produced by MWO-P-002) and a proven verification framework (`VERIFICATION/`, produced by MWO-P-006).
- Two of the eight required modules (Customer, Pump Registry) already exist in canonical, real form — Customer Registry (`BUILD-PACKS/BP-005-CUSTOMER-REGISTRY`) and Pump Registry (`MODULES/PUMP` schema + `BUILD-PACKS/BP-PUMP` tests, canonicalized under MWO-P-004).
- `AI5R-SDK/PRODUCT_RUNTIME`'s "Product Runtime/Factory/Registry" chain does not read or write any real product code on disk (confirmed across MWO-OSA-004/005 this session) — it manufactures an in-memory, synthetic artifact from a domain list only. It is therefore **not** the vehicle capable of producing a real, demonstrable product, and using it would not satisfy "must be capable of being demonstrated and used internally." The one proven, working manufacturing pattern in this repository that produces real, demonstrable artifacts is the `BUILD-PACKS/BP-XXX` convention already used for Customer, Pump, and Seal. This specification reuses that pattern exclusively, per the order's own principle: "Reuse existing runtime... Do not redesign."

## 2. Module-by-Module Reuse Decision

| # | Required Module | Manufacturing Decision |
|---|---|---|
| 1 | Dashboard | New `BUILD-PACKS/BP-DASHBOARD` — one aggregation workflow (`GET /ltsa/dashboard/summary`) counting rows across all six registries below, plus a minimal static HTML page consuming it. No frontend framework introduced (none exists anywhere in this repository to reuse — `MODULES/PUMP/UI/*.tsx` are 0-byte placeholders per MWO-P-001 — building a framework from scratch would be new architecture, out of scope). |
| 2 | Customer | **Already manufactured.** `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY` + `DATABASE/CANONICAL_SCHEMA.sql`'s `customer_registry` table. Reused as-is; not touched by this order. |
| 3 | Asset Registry | New `BUILD-PACKS/BP-ASSET` — general (non-pump, non-seal) equipment, following the exact Seal Registry pattern (MWO-P-005), the most recently proven convention. |
| 4 | Pump Registry | **Already manufactured.** `MODULES/PUMP` + `BUILD-PACKS/BP-PUMP`, canonicalized under MWO-P-004. Reused as-is; not touched by this order. |
| 5 | Soot Blower Registry | New `BUILD-PACKS/BP-SOOT-BLOWER` — same pattern as Asset Registry. |
| 6 | Work Order | New `BUILD-PACKS/BP-WORK-ORDER` — references `customer_registry.customer_code` and a polymorphic `(asset_code, asset_type)` pair, since assets span four separate registries (pump, seal, asset, soot_blower) with no common supertype table in this repository; a cross-table foreign key is not possible without introducing one, which would be new architecture. Documented as a known constraint, not silently worked around. |
| 7 | Maintenance History | New `BUILD-PACKS/BP-MAINTENANCE-HISTORY` — references `work_order.work_order_code` and the same polymorphic asset pair, recording completed maintenance actions. |
| 8 | Basic AI Assistant | New `PRODUCTS/LTSA-BRAIN/AI-ASSISTANT/maintenance_assistant.py` — a thin module that imports `AI5R-SDK/BRAIN`'s `EnterpriseCognitivePipeline` **unmodified** and feeds it an asset-observation dict, returning BRAIN's own `LearningObject` as a maintenance recommendation. This is the first real use of BRAIN by any AI5R product, consistent with ADR-002/003: BRAIN is consumed, not owned, not modified, not redesigned. |

## 3. Schema Design (new tables only — additive to `CANONICAL_SCHEMA.sql`, nothing existing altered)

```sql
-- ASSET (general equipment, distinct from Pump/Seal)
asset_registry(asset_code PK TEXT, asset_name TEXT NOT NULL, asset_type TEXT, area TEXT,
                manufacturer TEXT, model TEXT, status TEXT, created_at, updated_at)

-- SOOT BLOWER
soot_blower_registry(soot_blower_code PK TEXT, soot_blower_name TEXT NOT NULL, boiler_area TEXT,
                      blower_type TEXT, manufacturer TEXT, model TEXT, steam_pressure NUMERIC,
                      status TEXT, created_at, updated_at)

-- WORK ORDER
work_order(work_order_code PK TEXT, customer_code TEXT, asset_code TEXT, asset_type TEXT,
           description TEXT NOT NULL, priority TEXT DEFAULT 'NORMAL', status TEXT DEFAULT 'OPEN',
           assigned_to TEXT, created_at, updated_at, closed_at TIMESTAMP)

-- MAINTENANCE HISTORY
maintenance_history(maintenance_record_code PK TEXT, work_order_code TEXT, asset_code TEXT,
                     asset_type TEXT, action_taken TEXT NOT NULL, performed_by TEXT,
                     performed_at TIMESTAMP DEFAULT NOW(), notes TEXT, created_at)
```

## 4. Conflict-Check Convention

Every new Create workflow uses the graceful pre-insert conflict-check pattern (`Check Existing → IF Exists → 409`) established by Seal Registry under MWO-P-005 — the more complete of the two patterns already present in this repository (Pump Create relies on a raw unique-constraint failure instead). Chosen for consistency with the most recently proven convention, per the Engineering Standard's Correctness-over-speed principle.

## 5. Manufacturing Process (per this order)

```
Specification (this document)
     ↓
Assembly     — DATABASE + SCHEMAS + WORKFLOWS + TEST per new module (BP-ASSET, BP-SOOT-BLOWER,
                BP-WORK-ORDER, BP-MAINTENANCE-HISTORY, BP-DASHBOARD, AI-ASSISTANT)
     ↓
Verification — Structural validation only (bash -n, JSON parse, py_compile); Runtime Verification
                remains blocked on the same standing condition documented in RV-004
                (no credentialed PostgreSQL connection in this session) — reported honestly,
                not implied
     ↓
Testing      — Smoke test scripts written for every module, structurally validated
     ↓
Release Candidate — this order's stop point
```

## 6. Out of Scope for v0.1 (MMP boundary, stated explicitly)

- No CI/CD pipeline or deployment automation beyond a written Deployment Guide.
- No authentication/authorization layer (none exists anywhere in this repository to reuse; adding one would be new architecture).
- No frontend framework — the Dashboard is a single static page, not a full application.
- Runtime Verification (live database execution) is not performed in this order, for the same reason it was not performed in MWO-P-006/RV-004: no credentialed PostgreSQL connection is available in this session. This is stated as a known limitation of the Release Candidate, not hidden.
