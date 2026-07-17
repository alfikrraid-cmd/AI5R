# MWO-LTSA-054 — Maintenance Factory Pack — WP-000 Research

Status: **WP-000 APPROVED** ("Research PASS. Architecture PASS. Maintenance Domain PASS."). Chief Architect confirmations: Maintenance consists of two canonical objects (Work Order, Maintenance History) — not to be merged, independent identities maintained. System A and System B coexist today and are not to be reconciled within this MWO. All implementation gaps (§Implementation Gaps) are to be recorded, not resolved. `recipe.json` remains a shared, cross-Factory-Pack decision, not decided by this MWO alone. Current priority remains LTSA Manufacturing. No implementation performed.
Type: Manufacturing Work Order (Research)
Role: Implementation Engineer
Architecture: FROZEN — nothing proposed here changes it
Scope: Research only, per explicit instruction. No `AI5R-SDK/FACTORY`, `PRODUCTS/LTSA-BRAIN`, or Runtime file is modified in producing this document.
Reuse: `UMC-001` (`AI5R-SDK/PLATFORM/MANUFACTURING/UMC-001-Universal-Manufacturing-Contract.md`), `UMR-001` (`AI5R-SDK/PLATFORM/MANUFACTURING/UMR-001-Universal-Manufacturing-Runtime-Specification.md`) — both re-read directly for this research, neither redesigned.
Precedent: `MWO-LTSA-050-Pump-Factory-Pack-Research.md` — this document follows its structure and rigor exactly, adapted for the Maintenance domain.

---

## Executive Summary

Two findings disclosed up front, before anything else, matching `MWO-LTSA-050`'s own practice of surfacing significant context first:

**Finding 1 — "Maintenance" is not one canonical object; it is two, related but distinct.** `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-WORK-ORDER` (`public.work_order`) and `BUILD-PACKS/BP-MAINTENANCE-HISTORY` (`public.maintenance_history`) are separate canonical tables with separate natural keys, connected by an optional, non-FK-enforced reference (`maintenance_history.work_order_code`). Any Maintenance Factory Pack must decide whether it manufactures one canonical object type or two — this research treats them as two, since that is what the schema actually shows, not an assumption.

**Finding 2 — a real, working manufacturing/orchestration stack for both objects already exists in this session's own prior work, and it is not UMC-001/UMR-001.** `MWO-P-008` (Work Order Gateway, Maintenance History Gateway), `MWO-019` (Maintenance Execution Runtime), `MWO-020`–`MWO-022` (Command Center, Intelligence Service, Copilot) together form a complete, tested, transport-based path: Python code → n8n webhook → embedded SQL → `work_order`/`maintenance_history` tables. This is **System A** in `MWO-LTSA-050`'s own terminology (the LTSA BUILD-PACK convention) — real, proven, and already reused correctly throughout. It is **not** an implementation of UMC-001/UMR-001 (**System B** — the platform-wide, Python, Identity-Resolution/Relationship-Resolution manufacturing contract) and does not close either of UMC-001's two disclosed gaps, because none of that work ever touched `AI5R-SDK/FACTORY`. This MWO's explicit instruction to "reuse UMC-001, reuse UMR-001" is therefore a request to research a **second, parallel manufacturing path** for the same two canonical tables — not an extension of the Gateway/Runtime stack already built.

Everything else below follows `MWO-LTSA-050`'s exact research areas, substituting Work Order and Maintenance History for Pump.

---

## 1. Canonical Maintenance Objects

**Table 1 — `public.work_order`** (`PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-WORK-ORDER/DATABASE/001_create_table.sql`, mirrored in `DATABASE/CANONICAL_SCHEMA.sql`):

```sql
work_order_code TEXT PK NOT NULL, customer_code TEXT, asset_code TEXT, asset_type TEXT,
description TEXT NOT NULL, priority TEXT DEFAULT 'NORMAL', status TEXT DEFAULT 'OPEN',
assigned_to TEXT, created_at, updated_at, closed_at TIMESTAMP
```

**Table 2 — `public.maintenance_history`** (`BUILD-PACKS/BP-MAINTENANCE-HISTORY/DATABASE/001_create_table.sql`, mirrored in `CANONICAL_SCHEMA.sql`):

```sql
maintenance_record_code TEXT PK NOT NULL, work_order_code TEXT, asset_code TEXT, asset_type TEXT,
action_taken TEXT NOT NULL, performed_by TEXT, performed_at TIMESTAMP DEFAULT NOW(),
notes TEXT, created_at TIMESTAMP DEFAULT NOW()
```

**Canonicity confirmed by direct read, matching `MWO-LTSA-050`'s own method:** neither table carries a `DEPRECATED` header (checked directly, both files), and neither has a duplicate/stub counterpart anywhere else in the repository (no `MODULES/WORK-ORDER` or `MODULES/MAINTENANCE` directory exists — only `MODULES/PUMP` does). This matches the **Seal Registry pattern** (`MWO-P-005`): one canonical location per operation, nothing to deprecate, not the **Pump pattern** (`MWO-P-004`: three locations, two deprecated).

**Existing workflows (System A, already real):** `BUILD-PACKS/BP-WORK-ORDER/WORKFLOWS/WF-LTSA-BRAIN-WORK-ORDER-{CREATE,DETAIL,LIST,UPDATE,DELETE}-001.json` and the equivalent five for `BP-MAINTENANCE-HISTORY` — all real, canonical-schema-aligned n8n workflows (confirmed by this session's own `MWO-P-008` direct read of their embedded SQL and validate-node field lists), each already exposed to Python via `WorkOrderGateway`/`MaintenanceHistoryGateway` (`CORE-SERVICES/API/work_order_gateway.py`, `maintenance_history_gateway.py`).

## 2. Identity

- **Work Order**: `work_order_code` — `TEXT PRIMARY KEY NOT NULL`, the natural key. Exactly analogous to `ltsa_pumps.tag_number` in `MWO-LTSA-050` §1 and the field UMC-001 Stage 4 (Identity Resolution) would resolve against.
- **Maintenance History**: `maintenance_record_code` — `TEXT PRIMARY KEY NOT NULL`, the natural key, same role.
- Both existing n8n workflows already enforce identity uniqueness at the Create operation (`Check Work Order Conflict` / `Check Maintenance History Conflict` nodes, confirmed by this session's `MWO-P-008` read) — but this is System A's own conflict-check logic, not an invocation of UMC-001's `IdentityResolver`. No `IdentityResolver` implementation exists for either object, consistent with `MWO-LTSA-050`'s finding that none exists anywhere in the platform for any object type.

## 3. Relationships

Both tables share the identical, intentional polymorphic-reference pattern, confirmed by direct read of each table's own SQL header comment (nearly word-for-word identical in both files):

- **`asset_code` / `asset_type`** — "an asset may live in `pump_registry` (`ltsa_pumps`), `seal_registry`, `asset_registry`, or `soot_blower_registry` — four separate tables with no common supertype in this schema... `asset_type` records which registry `asset_code` belongs to, resolved at the application/workflow layer." This is confirmed, by the schema's own comment, to be **unresolved anywhere in code today** — "resolved at the application/workflow layer" is aspirational language in the SQL comment, not a description of an existing resolver. This is precisely UMC-001 Stage 5 (Relationship Resolution)'s gap, for both objects.
- **`maintenance_history.work_order_code`** — explicitly **not** FK-enforced, and for a different, disclosed reason than `asset_code`: "to keep this table independently queryable even if a work order record is absent (e.g. maintenance performed without a formal work order)" (direct quote, table's own header comment). This is a *deliberately optional* relationship, not merely an unresolved one — a distinction UMC-001's `RelationshipResolution(resolved: dict, unresolved: list[str])` shape already accommodates (an item can legitimately be reported unresolved without that being an error).
- **`work_order.assigned_to`** — a free-text field. **This one relationship is already resolved today, but not through UMC-001/UMR-001**: this session's own `MWO-019` (Maintenance Execution Runtime) resolves it via Organization Registry / Role Manufacturing's `retrieve_role_artifact()` before constructing the Work Order Create payload — a real, working, tested relationship resolution, entirely within System A, with no `RelationshipResolver` involved. Any Maintenance Factory Pack (System B) built for Work Order would need its own decision on whether to duplicate this resolution via a `RelationshipResolver`, or treat `assigned_to` as already-resolved input by the time a System-B manufacturing request is made — not decided here.

## 4. Maintenance History Model

Business meaning, confirmed by the table's own fields and its Create workflow's validate-node field list (`BUILD-PACKS/BP-MAINTENANCE-HISTORY/WORKFLOWS/WF-LTSA-BRAIN-MAINTENANCE-HISTORY-CREATE-001.json`, re-confirmed this session in `MWO-P-008`): an **executed, historical record** of a maintenance action. `action_taken` is the only other required field besides identity (`maintenance_record_code`); `work_order_code`, `asset_code`, `asset_type`, `performed_by`, `notes` are all optional; `performed_at` defaults to `NOW()`. There is no `status` field — a Maintenance History record, once created, is not modeled as progressing through states (unlike Work Order's `status`).

## 5. Work Order Model

Business meaning: a **planned, assignable unit of work**, not yet necessarily executed. `description` is the only other required field besides identity; `customer_code`, `asset_code`, `asset_type`, `priority` (default `NORMAL`), `assigned_to` are all optional; `status` defaults to `OPEN` and is mutable (this session's own `MWO-P-008` Update workflow allows changing it, among other fields); `closed_at` is nullable, set only on closure. Unlike Maintenance History, Work Order **does** model a lifecycle (`OPEN` → ... → closed, via `status`/`closed_at`), though no enumerated set of valid `status` values is enforced anywhere in the schema or workflows (confirmed — `status TEXT DEFAULT 'OPEN'`, no `CHECK` constraint, no enum).

---

## Factory Analysis

**Inputs (candidate):** a caller-supplied `definition: dict` fed to `ManufacturingRuntime.run()`, per UMR-001 §4 — for Work Order, minimally `{work_order_code, description}` (the two required fields); for Maintenance History, `{maintenance_record_code, action_taken}`. No adapter exists from this session's own System A (e.g. a `WorkOrderGateway.create_work_order()` call, or an `execute_maintenance()` Runtime result) into a UMC-001 `ManufacturingOrder.customer_request` — the same class of gap `MWO-LTSA-050` §Factory Analysis found between `acquisition_job` and Pump.

**Outputs:** a canonical `work_order` or `maintenance_history` row (Stage 6), a bespoke runtime-level result dict (Stage 8, per UMR-001 §10's disclosed, still-open gap — unresolved by this research, not to be closed here), a durable `BuildReport`, and the Manufacturing Event sequence below.

**Manufacturing Objects:** one `ManufacturingObject(object_type="work_order", object_id=work_order_code, payload={...})` per manufactured Work Order; one `ManufacturingObject(object_type="maintenance_record", object_id=maintenance_record_code, payload={...})` per manufactured Maintenance History record — the concrete Stage-6 instantiation for each object type, naming chosen to match each table's own natural-key field name, not invented terminology.

**Manufacturing Events:** `BUILD_STARTED` (runtime-level, once) → per-station `STATION_COMPLETED` (plausibly one Identity Resolution station and one Relationship Resolution station per object type, plus a Canonical Object Manufacturing station — exact decomposition is an implementation decision, not researched here, matching `MWO-LTSA-050`'s own position) → `BUILD_COMPLETED` (runtime-level, once).

**Factory Pack Boundaries — what a Maintenance Factory Pack would own vs. reuse:**

| Owns (new, Maintenance-specific) | Reuses unchanged |
|---|---|
| A concrete `IdentityResolver` implementation matching `{"work_order_code": ...}` against `work_order`, and a second matching `{"maintenance_record_code": ...}` against `maintenance_history` (two objects, plausibly two resolver instances or one parameterized by `object_type`) | `UMR-001` runtime itself — no Runtime file touched |
| A concrete `RelationshipResolver` implementation matching `{"asset_code", "asset_type"}` against whichever of the four asset registries `asset_type` names | `UMC-001` contract itself — no redesign |
| A second `RelationshipResolver` concern (or the same one, parameterized): `maintenance_history.work_order_code` against `work_order` — with **unresolved being a valid, non-error outcome**, per the schema's own documented intent (§3 above) | This session's own `WorkOrderGateway`/`MaintenanceHistoryGateway`/`MaintenanceExecutionRuntime` (System A) — reused as an upstream data source / alternate write path, not rebuilt or replaced |
| A manufacturing station (or station sequence) per object type that writes the canonical row | `work_order`/`maintenance_history`'s own schema — already canonical, untouched |
| A `FactoryPack` definition per object type (`pack_code`, `product_type="work_order"` / `"maintenance_record"`, `capabilities`, `recipe_path`) | `ManufacturingOrder`/`ManufacturingContext`/`ManufacturingEvent`/`ManufacturingObject`/`ManufacturingPipeline` — all reused as-is |
| Whatever "recipe" format `recipe_path` requires — still undefined anywhere in the repo (confirmed, re-checked this session: no `recipe.json` exists) | Organization Registry / Role Manufacturing, if `assigned_to` relationship resolution is kept in System A rather than duplicated into a Stage-5 `RelationshipResolver` (open question, §Open Questions) |

---

## Recipe Candidates

No `recipe.json` exists anywhere in the repository (re-confirmed this session; unchanged since `MWO-LTSA-050`'s own finding) — there is no existing format to reuse, and none is invented here. What can be stated without inventing one: `FactoryPack.recipe_path` (`AI5R-SDK/FACTORY/PACKS/factory_pack.py`) is a required, non-empty string field pointing to wherever such a file would live; nothing in `FactoryPackLoader` or `FactoryPack.validate()` inspects the *contents* of the file the path points to — only that `recipe_path` itself is present. Two Work-Order/Maintenance-History-specific candidate recipe *contents* (not formats — no format is chosen here) would need to express, at minimum: which fields are required vs. optional for Canonical Object Manufacturing (already fully known from §4/§5 above, reusable verbatim regardless of format chosen), and which relationship(s) (§3) this recipe expects a station to resolve before manufacturing. Choosing the actual recipe file format is an architecture decision, not a research finding, exactly as `MWO-LTSA-050` Open Question 2 left it for Pump.

---

## Implementation Gaps

1. **Identity Resolution and Relationship Resolution remain interface-only platform-wide** (UMC-001 §4–§5, UMR-001 §7–§8) — nothing in this session's Gateway/Runtime work for Work Order or Maintenance History closes either gap, since none of it touches `AI5R-SDK/FACTORY/RESOLUTION`.
2. **No `recipe.json` format is defined anywhere** — identical gap to `MWO-LTSA-050`'s Pump finding, now confirmed to also apply to Maintenance.
3. **No adapter exists between System A (Gateway/Runtime results) and System B (`ManufacturingOrder.customer_request`)** — a caller wanting to manufacture a Work Order or Maintenance History record via UMC-001/UMR-001 today would have to construct the `definition: dict` by hand; nothing bridges from `WorkOrderGateway.create_work_order()`'s return shape or `execute_maintenance()`'s runtime result into that input.
4. **`assigned_to`'s relationship resolution (§3) already happens in System A, redundantly with what a Stage-5 `RelationshipResolver` would do** — if a Maintenance Factory Pack is built, whether it re-implements this resolution as a `RelationshipResolver` or treats `assigned_to` as pre-resolved input is undecided; building both without reconciling them risks two independent, possibly diverging paths to the same answer.
5. **UMR-001's own disclosed Runtime Result gap** (§10, "bespoke dict, not a `ManufacturingResult`") applies unchanged to any Maintenance Factory Pack run — not this MWO's own gap to close, carried forward as UMR-001's standing, accepted WARNING.
6. **Documentation drift, flagged, not resolved:** `ROADMAP.md` line 26 labels the `MWO-LTSA-050`–`053` number range as "Engineering Media analysis (image/video/audio) (deferred by MWO-LTSA-040E)" — but the actual files on disk at those numbers are `050 = Pump Factory Pack Research` and `051 = Engineering Knowledge Graph Research`, neither about media analysis. This is a pre-existing inconsistency in `ROADMAP.md`, not introduced by this research, and not corrected here (out of this WP-000's scope — a documentation-maintenance concern, not a Maintenance Factory Pack research finding).

---

## Open Questions (for a future Architecture Decision — not decided here)

1. **Does "Maintenance Factory Pack" mean one Factory Pack manufacturing two object types (Work Order and Maintenance History), or two separate Factory Packs?** Both are structurally possible under `FactoryPack`'s own shape (`product_type` is a single string field) — nothing in UMC-001/UMR-001 resolves this for a two-object domain, and `MWO-LTSA-050`'s own precedent (Pump) only ever addressed one object type.
2. **What is the `recipe_path` file format?** Unresolved for Pump in `MWO-LTSA-050`; still unresolved here, for the same underlying platform gap.
3. **Should `assigned_to`'s relationship resolution be migrated from System A (`MWO-019`'s direct `retrieve_role_artifact()` call) into a UMC-001 `RelationshipResolver`, kept as-is and treated as pre-resolved input to System B, or intentionally duplicated for two independent call paths?** Not decided here — this is the Maintenance-specific analog of `MWO-LTSA-050`'s Open Question 3 (how an `acquisition_job` feeds a Pump Factory Pack).
4. **Should the four-registry `asset_type` polymorphic dispatch (§3) be resolved by one shared `RelationshipResolver` reused across Pump, Work Order, and Maintenance History Factory Packs, or a separate implementation per Factory Pack?** This question did not arise in `MWO-LTSA-050` (Pump's own relationship, `seal_type` → `seal_registry`, is a single-table lookup, not a four-way polymorphic dispatch) — it is new to this research and, if a shared resolver is later chosen, has cross-Factory-Pack architectural implications beyond Maintenance alone.
5. **Should Maintenance History's optional, non-FK `work_order_code` relationship be modeled as a `RelationshipResolver` call that may legitimately return "unresolved," or excluded from Relationship Resolution entirely and left as free-text linkage, as it is today in System A?** Not decided here.
6. **Should a Maintenance Factory Pack's manufacturing station(s) be expressed as an `ADR-003` Capability or a plain `BaseManufacturingStation`?** Same open question `MWO-LTSA-050` left for Pump (§Open Questions item 6 there); not re-resolved here, not object-specific.

---

## Deliverables (this document only)

- This WP-000 research document, citing every claim to a direct file read, including this session's own prior Gateway/Runtime work where relevant.
- No code, schema, or build pack. No `AI5R-SDK/FACTORY`, `PRODUCTS/LTSA-BRAIN`, or Runtime file modified in producing it.

## Definition of Done (for this research)

- All requested research areas (Canonical Maintenance object(s), Identity, Relationships, Maintenance History model, Work Order model, Factory Pack boundary, Recipe candidates, Implementation gaps) addressed with direct evidence. **Met.**
- `UMC-001` and `UMR-001` re-read directly and reused, not redesigned. **Met.**
- No implementation performed; no Factory Pack, Manufacturing Runtime, or LTSA Runtime file touched. **Met.**
- Open questions surfaced, not silently decided. **Met.**
- The two significant up-front findings (two objects, not one; an existing System A stack that UMC-001/UMR-001 reuse does not subsume) disclosed first, not buried. **Met.**

---

**WP-000 disposition:** **APPROVED** — Research PASS, Architecture PASS, Maintenance Domain PASS. Confirmed by Chief Architect: two independent canonical objects (Work Order, Maintenance History), not merged; System A and System B coexist, not reconciled within this MWO; all Implementation Gaps recorded, none resolved; `recipe.json` format remains an open, shared Factory Pack decision, not made here or by this MWO alone.

Research only. No implementation performed. Stopping here, per instruction. Current priority remains LTSA Manufacturing.
