# MWO-LTSA-050 — Pump Factory Pack — WP-000 Research

Status: RESEARCH ONLY — no implementation performed
Type: Manufacturing Work Order (Research)
Role: Implementation Engineer
Architecture: FROZEN — nothing proposed here changes it
Scope: Research only, per explicit instruction. No `AI5R-SDK/FACTORY`, `PRODUCTS/LTSA-BRAIN`, or Runtime file is modified in producing this document.

---

## Executive Summary

A significant finding, disclosed before anything else: this research surfaced that `CURRENT_STATE.md`, `ROADMAP.md`, and several `ENGINEERING/MWO/` documents (`MWO-LTSA-040D`, `MWO-LTSA-040E`, `MWO-LTSA-048`, `MWO-LTSA-049`, plus a full `AI5R-SDK/PLATFORM` and `AI5R-SDK/FACTORY/RESOLUTION` tree) describe and implement substantially more repository state than this session had previously accounted for — including a working Universal Manufacturing Contract (UMC-001) and Universal Manufacturing Runtime (UMR-001) at the platform level, and real PDF/Media Acquisition build packs (confirmed present on disk: `BP-PDF-DOCUMENT`, `BP-PDF-METADATA`, `BP-PDF-ACQUISITION-JOB`, `BP-ENGINEERING-MEDIA`, `BP-MEDIA-METADATA`, `BP-MEDIA-CLASSIFICATION`, `BP-MEDIA-ACQUISITION-JOB`). This is not a contradiction of this session's own `MWO-LTSA-030`/`040A`/`040B`/`040C` work — it is consistent with and builds on it (UMC-001 §6 explicitly names `mapping_profile`/`column_mapping` as this session's own capability; `MWO-LTSA-048` §6 explicitly anticipates a future "Pump-manufacturing MWO" using exactly `ltsa_pumps.tag_number` and `seal_type`→`seal_registry.seal_code`). It simply means richer platform context exists than this research pass had previously surfaced, and this document is grounded in that fuller picture.

**The single most important finding:** "Factory Pack" is not a fresh concept to invent for Pump. It is an existing, precisely specified, partially-implemented platform contract — `UMC-001` (nine-stage contract) executed by `UMR-001` (the runtime) — and `MWO-LTSA-048` §6 and `UMC-001` §7 both explicitly name Pump as the anticipated first concrete consumer: *"a Pump-manufacturing MWO would resolve identity via `ltsa_pumps.tag_number`, relationships via `seal_type`→`seal_registry.seal_code`, then manufacture the canonical `ltsa_pumps` row."* **`MWO-LTSA-050` reads as that anticipated MWO.** This reframes the research: the question is not "what should a Pump Factory Pack look like," it's "what does implementing UMC-001's two disclosed gaps (Identity Resolution, Relationship Resolution) concretely for Pump require," within a contract and runtime that already exist and must not be redesigned.

---

## 1. Canonical Pump Object

**Table:** `public.ltsa_pumps` (`PRODUCTS/LTSA-BRAIN/MODULES/PUMP/DATABASE/001_create_pumps.sql`), confirmed canonical by `DATABASE/CANONICAL_SCHEMA.sql`'s own header comment (selected over two other candidate definitions because it is the table genuinely queried by real, non-stub workflows — runtime evidence, per `MWO-P-002`).

```sql
id UUID PK, tag_number VARCHAR(100) UNIQUE NOT NULL, area VARCHAR(100) NOT NULL,
location VARCHAR(150), pump_type VARCHAR(100), api_plan VARCHAR(50),
seal_type VARCHAR(150), status VARCHAR(50) DEFAULT 'UNKNOWN',
manufacturer VARCHAR(150), model VARCHAR(150), drawing_ref TEXT, notes TEXT,
created_at, updated_at
```

`tag_number` is the natural key (`UNIQUE NOT NULL`) — the exact field `MWO-LTSA-048`/`UMC-001` name for Identity Resolution. `seal_type` is free text today (not an FK) — the exact field named for Relationship Resolution, to be resolved against `seal_registry.seal_code`.

**Existing consumers:** `seal_pump_compatibility.pump_tag_number` (this session's own `MWO-LTSA-030`) already FKs to `ltsa_pumps.tag_number` — confirming `tag_number` as the correct natural key was already load-bearing before this research, not a new proposal.

**Existing workflows:** `MODULES/PUMP/WORKFLOWS/*.json` (Create, real embedded SQL) and `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-PUMP-DETAIL-001.json` (Detail, real) — both n8n-workflow-shaped, per the LTSA BUILD-PACK convention this session used throughout. List/Update/Delete exist only as non-functional stubs in the deprecated `BUILD-PACKS/BP-PUMP`.

## 2. Pump Registry

Confirmed, consistent with this session's prior findings: `BUILD-PACKS/BP-PUMP/DATABASE/001_create_table.sql` carries an explicit `DEPRECATED (MWO-P-002/IR-001)` header — its `pump_registry` table (TEXT PK `pump_code`) is not canonical and not queried by any real workflow. `PRODUCTS/LTSA-BRAIN/REGISTRIES/` contains only `SEAL.json` — no `PUMP.json` exists. `AI5R-SDK/FACTORY/REGISTRY/MODULES/PUMP.json` (the older, unrelated `AI5R-SDK/FACTORY` legacy tree, out of LTSA-BRAIN scope per `MWO-P-001`) was not read in this pass — flagged as unexplored, low priority given `MWO-P-001`'s standing exclusion.

## 3. Pump Knowledge

The one existing real cross-reference is `seal_pump_compatibility` (`BUILD-PACKS/BP-SEAL-PUMP-COMPATIBILITY`, this session's `MWO-LTSA-030`): `(seal_code, pump_tag_number)` composite key, FK'd to both `seal_registry` and `ltsa_pumps`. `PUMP_MASTER` is one of the 11 `workbook_type` enum values (`BUILD-PACKS/BP-WORKBOOK`, `MWO-LTSA-040C`). `BUILD-PACKS/BP-COLUMN-MAPPING/DATABASE/002_seed.sql`'s seed example maps three plausible source-column names (`TAG NO`, `Equipment`, `Pump Number`) to a single `canonical_attribute` value, `"Pump Tag"` — a human-readable label, not a literal match to the `ltsa_pumps.tag_number` column name. **Gap, flagged, not resolved here:** the `canonical_attribute` vocabulary used by `column_mapping` today is illustrative seed data, not a governed mapping to real column names — a Pump Factory Pack's Identity Resolution would need a defined translation from `canonical_attribute` strings to actual `ltsa_pumps` columns, and no such translation table or convention exists yet.

## 4. Pump Capability

`ADR/ADR-003-Capability-as-Universal-Execution-Layer.md` establishes "Capability" as a formal, generic execution-layer concept (not read in full this pass; referenced in this session's `MWO-LTSA-040A` research as one of AI5R's "four peer strategic assets" alongside Knowledge, BRAIN, and OSA). `ENGINEERING/CAPABILITIES/DOCKER/` is the one concrete example implementation. **No Pump-specific Capability exists anywhere in the repository.** Whether a Pump Factory Pack's manufacturing station should itself be expressed as a Capability (per `ADR-003`'s own execution model) or as a plain `BaseManufacturingStation` (the `AI5R-SDK/FACTORY/CORE` pattern UMC-001 Stage 3 already reuses) is an open question this research does not resolve — both are real, existing patterns in the platform, and choosing between them is an architecture decision, not a research finding.

## 5. Pump Manufacturing

This is the largest area, and where the two coexisting "manufacturing" systems this repository has must be distinguished:

**System A — the LTSA BUILD-PACK convention** (`BUILD-PACKS/BP-<NAME>`, n8n workflow JSON + embedded SQL + Postgres table): what every MWO this session performed (`030`, `040A`, `040B`, `040C`) and what `MANUFACTURING/MO-001` established. Simple, proven, but purely a CRUD-registry pattern — no identity/relationship resolution, no event bus, no pipeline.

**System B — UMC-001 / UMR-001** (`AI5R-SDK/FACTORY`, Python, platform-wide): a nine-stage contract (Request → Context → Validation → **Identity Resolution** → **Relationship Resolution** → Canonical Object Manufacturing → Event Publication → Result → Lifecycle), seven of nine stages already real and reused (`ManufacturingOrder`, `ManufacturingContext`, `BaseManufacturingStation.validate()`, `ManufacturingObject`, `ManufacturingEvent`/`ManufacturingEventBus`, `ManufacturingResult`, `ManufacturingPipeline`/`ManufacturingRuntime`/`ManufacturingEngine`), executed by `UMR-001` (`FOUNDATION.ManufacturingRuntime`, established `MWO-LTSA-049`). Two stages — Identity Resolution (`AI5R-SDK/FACTORY/RESOLUTION/identity_resolver.py`) and Relationship Resolution (`.../relationship_resolver.py`) — exist only as `ABC` interfaces, by explicit, twice-recorded Chief Architect directive: *"no concrete matching or deduplication logic exists in the platform"* (`UMC-001` §4-5, `UMR-001` §7-8). **Both specs name LTSA-BRAIN, and specifically Pump, as the expected first concrete implementer.**

**The reusability unit** is `FactoryPack` (`AI5R-SDK/FACTORY/PACKS/factory_pack.py`): `pack_code`, `pack_name`, `product_type`, `capabilities: list[str]`, `recipe_path`, `metadata`, with a `validate()` requiring all five non-`metadata` fields non-empty. `FactoryPackLoader` (`.../factory_pack_loader.py`) loads one from a JSON file at `recipe_path`-adjacent location. **Gap, flagged:** the only example `FactoryPack` instances in the repository are test fixtures (`FP-WEBSITE-001`, `recipe_path: "PRODUCTS/WEBSITE/recipe.json"`) — no actual `recipe.json` file exists anywhere, and the shape of a "recipe" is not defined by any code or spec read in this pass. A Pump Factory Pack would need this format either defined or discovered to not exist and require its own decision.

**Naming collision, flagged (same class as this session's earlier `AI5R-SDK/KNOWLEDGE` finding):** `AI5R-SDK/FACTORY_PACKS/WEBSITE/website_factory_pack.py`'s `WebsiteFactoryPack` class is an older, unrelated, `MWO-004.1`-era static-site generator — it has nothing to do with UMC-001's `FactoryPack` dataclass despite the near-identical name. Do not use it as a template.

`ManufacturingObject` (`object_type`, `object_id`, `payload`, `metadata`, `created_at`) is the shape a manufactured Pump would take at Stage 6. `ManufacturingEvent` — the `FOUNDATION` variant specifically, **not** the incompatible `CORE` variant of the same name (`UMR-001` §9's own explicit caution) — is the shape of every Stage-7 event.

**Known, disclosed, unclosed gap in UMR-001 itself:** Stage 8 (`ManufacturingRuntime.run()`'s return value) is a bespoke dict, not a `ManufacturingResult` instance — recorded as a standing WARNING in `MA-002-Manufacturing-Audit-Report.md`, explicitly "not to be silently implemented." A Pump Factory Pack consumes UMR-001's actual current return shape and must not attempt to close this gap itself — that is a separate, UMR-001-owned decision.

## 6. Pump Validation

Two validation layers already established by UMR-001 (§6), reused as-is by any Factory Pack: (1) order/pack-level (`ManufacturingOrder.validate()`, `FactoryPack.validate()` — raises `ValueError`, fail-fast, before any work begins) and (2) definition-level (`FactoryValidator.validate(definition)` — returns a structured rejection, no exception). No Pump-specific validation exists in this system today. Compare to this session's own n8n-workflow-layer validation pattern (required-field JS checks + Postgres `CHECK` constraints, used throughout `BUILD-PACKS/BP-*`) — that pattern is System A's validation, not System B's; a Pump Factory Pack's Stage 3 validation would need its own `BaseManufacturingStation.validate()`-shaped implementation, a different code path than every workflow built this session.

---

## Factory Analysis

**Inputs (candidate):** either (a) a caller-supplied `definition: dict` (`build_id`, `product`, `customer_request` or synthesizable equivalent) fed directly to `ManufacturingRuntime.run()`, or (b) — the more interesting, acquisition-connected path — a completed `acquisition_job` (`READY_FOR_MANUFACTURING` status, `MWO-LTSA-040C`) whose normalized, mapped workbook rows become the `customer_request` payload. **No adapter between `acquisition_job` and `ManufacturingOrder.customer_request` exists yet** — this is a real design gap between the two systems, not resolved here.

**Outputs:** a canonical `ltsa_pumps` row (Stage 6), a runtime-level result dict (Stage 8, per its disclosed bespoke shape), a durable `BuildReport` (`build.json`/`workspace.json`/`manufacturing.json`/`events.json`), and the `ManufacturingEvent` sequence below.

**Manufacturing Objects:** one `ManufacturingObject(object_type="pump", object_id=<tag_number or a canonical UUID>, payload={the ltsa_pumps row's fields})` per manufactured Pump — the concrete instantiation of Stage 6 for this object type.

**Manufacturing Events:** `BUILD_STARTED` (runtime-level, once) → per-station `STATION_COMPLETED` (one per pipeline station — plausibly a Pump Identity Resolution station, a Pump Relationship Resolution station, and a Pump Canonical Object Manufacturing station, though the exact station decomposition is an implementation decision, not researched here) → `BUILD_COMPLETED` (runtime-level, once).

**Factory Pack Boundaries — what a Pump Factory Pack would own vs. reuse, based on evidence gathered:**

| Owns (new, Pump-specific) | Reuses unchanged |
|---|---|
| A concrete `IdentityResolver` implementation matching `{"tag_number": ...}` against `ltsa_pumps` | `UMR-001` runtime itself — no Runtime file touched |
| A concrete `RelationshipResolver` implementation matching `{"seal_type": ...}` against `seal_registry.seal_code` | `UMC-001` contract itself — no redesign |
| A manufacturing station (or station sequence) that writes the canonical `ltsa_pumps` row | The Acquisition Layer (`knowledge_source_registry`, `workbook`, `acquisition_job`, etc.) — reused as an upstream input source, not rebuilt |
| A `FactoryPack` definition (`pack_code`, `product_type="pump"` or similar, `capabilities`, `recipe_path`) | `ltsa_pumps`'s own schema — already canonical, untouched |
| Whatever "recipe" format `recipe_path` requires — currently undefined anywhere in the repo | `ManufacturingOrder`/`ManufacturingContext`/`ManufacturingEvent`/`ManufacturingObject`/`ManufacturingPipeline` — all reused as-is |

---

## Open Questions (for a future Architecture Decision — not decided here)

1. Does "Pump Factory Pack" mean a concrete UMC-001/UMR-001 implementation (System B, Python `IdentityResolver`/`RelationshipResolver`/station), or something else? Evidence (`MWO-LTSA-048` §6, `UMC-001` §7, `ROADMAP.md`) strongly points to System B, but this has not been said in so many words in `MWO-LTSA-050`'s own mission text and should be confirmed before WP-001.
2. What is the "recipe" (`recipe_path`) format? No example exists anywhere in the repository today.
3. How should a completed `acquisition_job` feed a Pump Factory Pack run — is a `customer_request` adapter this MWO's own scope, the Acquisition Layer's, or a third, new component?
4. Should `BUILD-PACKS/BP-PUMP` (the deprecated stub) be formally retired as part of this work, or remain untouched?
5. What is the governed translation from `column_mapping.canonical_attribute` strings (e.g. `"Pump Tag"`) to actual `ltsa_pumps` column names (`tag_number`)? Currently undefined.
6. Should a Pump Factory Pack's manufacturing station be expressed as an `ADR-003` Capability, or a plain `BaseManufacturingStation`? Both patterns exist in the platform today; neither has been chosen for this use case.

---

## Deliverables (this document only)

- This WP-000 research document, citing every claim to a direct file read.
- No code, schema, or build pack. No `AI5R-SDK/FACTORY`, `PRODUCTS/LTSA-BRAIN`, or Runtime file modified in producing it.

## Definition of Done (for this research)

- All six requested research areas (Canonical Pump Object, Pump Registry, Pump Knowledge, Pump Capability, Pump Manufacturing, Pump Validation) addressed with direct evidence. **Met.**
- Factory Analysis (Inputs, Outputs, Manufacturing Objects, Manufacturing Events, Factory Pack Boundaries) produced. **Met.**
- No implementation performed; no Factory Pack, Manufacturing Runtime, or LTSA Runtime file touched. **Met.**
- Open questions surfaced, not silently decided. **Met.**
- The significant contextual discovery (fuller platform state than previously accounted for) disclosed up front, not buried. **Met.**

---

Research only. Stopping here after WP-000, as instructed. Awaiting approval.
