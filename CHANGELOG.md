# LTSA Brain Changelog

## BP-001
- Pump Registry Database

## BP-002
- API Contract
- Documentation

## BP-003
- Pump Registry Service
- PostgreSQL Integration
- n8n Workflow

## BP-004
- Initialize LTSA Core SDK

## MWO-LTSA-030
- Mechanical Seal Knowledge Manufacturing: `seal_registry`, `seal_stock`, `seal_pump_compatibility`, `seal_interchange_compatibility`, `seal_engineering_document`

## MWO-LTSA-040A
- Knowledge Source Registry (`knowledge_source_registry`) — provenance registry for engineering knowledge sources

## MWO-LTSA-040B
- Engineering Document Acquisition — extended `seal_engineering_document` with acquisition-layer metadata and a `knowledge_source_registry` FK

## MWO-LTSA-040C
- Universal Tabular Data Acquisition (Workbook Acquisition): `workbook`, `worksheet`, `worksheet_table`, `mapping_profile`, `column_mapping`, `acquisition_job`

## MWO-LTSA-040D
- Engineering PDF Acquisition: `pdf_document`, `pdf_metadata`, `document_classification`, `pdf_acquisition_job`

## MWO-LTSA-040E
- Engineering Media Acquisition: `engineering_media`, `media_metadata`, `media_classification`, `media_acquisition_job` — third canonical Acquisition Object, conforming to `ADR-004`

## Governance
- `ADR-004`: Engineering Acquisition Pattern — Acquisition Object → Metadata → Classification → Acquisition Job, now mandatory for every Acquisition Object type
- `MWO-LTSA-040C-R1`: Workbook Acquisition Pattern Alignment retrofit — specification only, approved, not implemented
- `EA-001`: Engineering Audit Report covering MWO-LTSA-030/040A–040E
- `RCA-001`: Root Cause Analysis of `RELEASE/*` auto-generated stub schema (test-hygiene defect, not attributable to any 040-series MWO)
- Documentation Contract established (`DOCUMENTATION_CONTRACT.md`), integrated into `ENGINEERING/AI5R_ENGINEERING_STANDARD_v1.0.md` §18
- `EOPS-003`, `RCA-002`, `GITIGNORE-RECOMMENDATION.md`: Repository hygiene review — generated-artifact policy, `.gitignore` gap analysis, `MWO-P-007` collision resolved to Superseded, `maintenance_assistant.py` cleared of supersession
- `ARCH-REVIEW-001`: Architecture Integrity Review — `REGISTRY/CONTITUTION`, `REGISTRY/workflow` duplicate-folder findings; Architecture Status PASS, AI5R Architecture confirmed Structurally Stable for LTSA Manufacturing

## MWO-LTSA-048
- **UMC-001 — Universal Manufacturing Contract** established: the nine-stage contract every Manufacturing Pipeline must implement, formalized in `AI5R-SDK/FACTORY/CORE/universal_manufacturing_contract.py`. Seven stages (Manufacturing Request, Context, Validation, Canonical Object Manufacturing, Event Publication, Manufacturing Result, Manufacturing Lifecycle) cite and reuse existing `AI5R-SDK/FACTORY` primitives unchanged. Two stages — Identity Resolution and Relationship Resolution — added as new, platform-wide interfaces only (`AI5R-SDK/FACTORY/RESOLUTION/{identity_resolver,relationship_resolver}.py`), no concrete resolution logic. Platform-wide (all Factory Packs), not an LTSA-BRAIN-only artifact; LTSA-BRAIN is its first intended consumer, not implemented by this MWO.

## MWO-LTSA-049
- **UMR-001 — Universal Manufacturing Runtime** established: `AI5R-SDK/FACTORY/FOUNDATION.ManufacturingRuntime` (Chain A) extended, not replaced, to execute UMC-001. `ManufacturingRuntime`/`FactoryOrchestrator`/`FactoryCompiler`/`ManufacturingPipeline` now construct and validate a real `ManufacturingOrder` and `ManufacturingContext` as their actual entry point (UMC-001 Stages 1–2), thread `ManufacturingContext` through the full pipeline so any station can read it, expose `IdentityResolver`/`RelationshipResolver` as pluggable, uninvoked platform hooks via `context.metadata` (Stages 4–5, still interfaces only, per Chief Architect directive), publish per-station `STATION_COMPLETED` events additively (Stage 7 wiring), and treat `FactoryPack` as a first-class, validated Runtime citizen. Chain B (`ManufacturingEngine`), Chain C (`ManufacturingService`), Chain D (`FactoryRuntime`) formally renamed in documentation only — **Release Engine**, **Factory Generator**, **Project Generator** respectively — and left entirely untouched. One incidental fix: `FOUNDATION.BuildReport.write()` gained a `default=str` JSON-serialization fallback, needed because `ManufacturingContext` is not natively JSON-serializable and now legitimately appears in build reports. One new technical debt item discovered and recorded (`TD-006`): `CORE.ManufacturingEvent` and `FOUNDATION.ManufacturingEvent` are two different, incompatible classes sharing one name — pre-existing, not remediated, Architecture Review recommended.

## MWO-LTSA-050 WP-001
- **Pump Factory Pack — the first concrete Factory Pack implementation of UMC-001/UMR-001**, per `MWO-LTSA-048` §6 and `MWO-LTSA-050` WP-000's own anticipation. New product-layer module, `PRODUCTS/LTSA-BRAIN/PUMP-FACTORY-PACK/` (following the `PRODUCTS/LTSA-BRAIN/AI-ASSISTANT/` precedent: plain Python, no package namespace, `TEST/` subdirectory, `sys.path` bridges to `AI5R-SDK`). No `AI5R-SDK/FACTORY` (Platform Artifact) file modified.
  - `pump_identity_resolver.py` — `PumpIdentityResolver(IdentityResolver)`: resolves a candidate pump by `tag_number` against a caller-supplied `known_pumps` collection (shaped like `ltsa_pumps`). UMC-001 Stage 4's first concrete implementer.
  - `pump_relationship_resolver.py` — `PumpRelationshipResolver(RelationshipResolver)`: resolves a pump's free-text `seal_type` against a caller-supplied `seal_registry` collection's `seal_name`, returning `seal_code` — the same cross-reference already load-bearing via `seal_pump_compatibility` (`MWO-LTSA-030`). UMC-001 Stage 5's first concrete implementer.
  - `pump_manufacturing_station.py` — `PumpManufacturingStation(BaseManufacturingStation)`: subclasses `FACTORY.CORE.manufacturing_station.BaseManufacturingStation` directly (Chief Architect directive — Manufacturing Station is a Factory concept, not an `ADR-003` Capability). Exposes `.run(payload) -> dict` (the `FACTORY.FOUNDATION.ManufacturingPipeline`-compatible station shape, UMR-001 §5) which wires UMC-001 Stage 4 → Stage 5 → the inherited `manufacture()` (Stage 3/6-8) in contract order, reading both resolvers from `context.metadata`. A pump whose `tag_number` already resolves is rejected as a duplicate (`PUMP_ALREADY_EXISTS`) rather than re-manufactured.
  - `pump.factory-pack.json` / `recipe.json` — the Pump `FactoryPack` definition (`pack_code=FP-PUMP-001`) and the first `recipe.json` to ever exist in this repository. `FactoryPack.recipe_path` previously pointed at no real file anywhere; **recipe.json v1** (minimal, Chief-Architect-approved schema — `recipe_id`, `recipe_version`, `object_type`, `identity_key`, `relationship_keys`, `stations`) is recorded as data only, not interpreted by any loader/engine this MWO — future Factory Packs (Seal, Maintenance, Installation) may reuse and extend it.
  - `TEST/` — 17 new tests: resolver unit tests, station unit tests (including the duplicate-rejection path), `FactoryPack`/`recipe.json` load tests, and two end-to-end tests running a real pump through the actual, unmodified `ManufacturingRuntime.run()`.
- Tracked as `MWO-LTSA-050` WP-001 (implementation phase of the already-approved WP-000 research), per Chief Architect decision — one continuous MWO audit trail, not a new MWO number.

## MWO-LTSA-052 WP-001
- **Mechanical Seal Factory Pack** — second concrete Factory Pack implementation of UMC-001/UMR-001, built using `MWO-LTSA-050` (Pump) as the canonical implementation pattern. New product-layer module, `PRODUCTS/LTSA-BRAIN/SEAL-FACTORY-PACK/` (identical shape to `PUMP-FACTORY-PACK/`). No `AI5R-SDK/FACTORY`/`PLATFORM` file modified.
  - `seal_identity_resolver.py` — `SealIdentityResolver(IdentityResolver)`: resolves a candidate seal by `seal_code` (already the primary key) against a caller-supplied `known_seals` collection.
  - `seal_relationship_resolver.py` — `SealRelationshipResolver(RelationshipResolver)`: resolves `compatible_seal_name` against a caller-supplied `seal_registry` collection's `seal_name`, returning `seal_code` — the interchange cross-reference `seal_interchange_compatibility` (`MWO-LTSA-030`) already requires. `ltsa_pumps.seal_type` resolution remains Pump-owned, not duplicated here.
  - `seal_manufacturing_station.py` — `SealManufacturingStation(BaseManufacturingStation)`: same wiring shape as `PumpManufacturingStation`; a seal whose `seal_code` already resolves is rejected as a duplicate (`SEAL_ALREADY_EXISTS`).
  - `seal.factory-pack.json` / `recipe.json` — `FactoryPack` definition (`pack_code=FP-SEAL-001`) and `RECIPE-SEAL-001`, reusing the same recipe.json v1 schema Pump established, extended (not redefined) per the schema's own stated intent.
  - `TEST/` — 17 new tests, same structure as Pump's suite.
- Tracked as `MWO-LTSA-052` WP-001 (implementation phase of the already-approved, merged WP-000 research). Full regression: 157/157 (17 new + 140 `AI5R-SDK/FACTORY`+`PLATFORM`).
