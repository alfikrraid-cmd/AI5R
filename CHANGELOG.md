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

## LTSA-BRAIN Document Upload MVP
- Document Field Extraction (`document_field_extraction`) — fulfils the extraction step MWO-LTSA-040D/040E both explicitly deferred: Upload → OCR → AI Field Extraction → Review → Save pipeline for engineering documents (PDF/JPG/JPEG/PNG)
- AI Extraction Capability (`PRODUCTS/LTSA-BRAIN/AI-EXTRACTION`) — reusable provider interface; Claude (`claude-opus-4-8`, structured outputs) is the first provider, isolated behind the interface per Chief Architect ruling
- `resolve_identity_cli.py` — reuses `PumpIdentityResolver`/`SealIdentityResolver` (unmodified) at Save time instead of reimplementing registry-matching logic
- `WF-LTSA-DOCUMENT-UPLOAD-001`, `WF-LTSA-DOCUMENT-SAVE-001` (n8n) — backend stays entirely within the existing n8n/Postgres pattern, no new REST API introduced, per Chief Architect ruling
- Upload/Review pages added to `AI5R-STUDIO/osa-web` — presentation-only client of the LTSA workflows, no business logic in Studio
- Original-file (binary) persistence explicitly deferred to a future Platform Storage MWO, per Chief Architect ruling — only OCR text and structured JSON are persisted in this MVP

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

## LTSA_ASSET360_CURRENT_INSTALLATION_AND_SERVICE_AGE_R1
- **Canonical Current Installation contract** (`CORE-SERVICES/API/current_installation_contract.py`, pure functions): current installation = latest valid `installation_report` per pump (and per explicitly evidenced DE/NDE position, from `seal_location` only — never inferred from free text), attributed by the governed `installation_report.pump_tag_number`; ties on the same date break on `installation_code DESC`; a later `seal_lifecycle_event` REMOVE/SCRAP/RETURN_TO_STOCK makes it `REMOVED`. No evidence = `NOT_RECORDED`. Configured seal (`ltsa_pumps`), compatibility and stock rows are never installation evidence.
- **Attribution defect fixed**: `EquipmentTimelineService._list_installations()` filtered on free-text `plant_equip_no`, so sibling pumps consumed each other's reports (INSTL-025 101-P-2A→101-P-3B, INSTL-038 945-P-7A→945-P-7B, INSTL-041 140-P-26A→140-P-26B) and annotated tags (INSTL-043 "940-P-2A (NDE)", INSTL-002 "212-P-25A SPARE") matched no pump. Now `pump_tag_number` on both paths; new `InstallationReportRepository.list_by_pump_tag()` also requires a registered PUMP and orders `report_date DESC, installation_code DESC` (re-sorted by the contract, never row order). `current_seal`, `/lifecycle` `current_installation`/`elapsed_service_days`, Copilot and Equipment 360 all follow the same rule.
- **Time Since Installation** (calculated, never persisted): calendar days in plant-local Asia/Jakarta (fixed UTC+07:00); hours = days × 24 for DATE_ONLY evidence (all 42 production reports), exact elapsed hours only for TIMESTAMP evidence; `time_basis=CALENDAR_TIME`. Actual Operating Hours = N/A (no runtime/hour-meter source exists). Not MTBF, not running hours.
- **`GET /api/ltsa/pumps/{tag}/knowledge`**: additive keys `current_installation`, `current_installations` (per position), `installation_history`.
- **Asset 360 UI**: new main-column Mechanical Seal section (Configured / Design, Current Installation, Time Since Installation, Actual Operating Hours, Compatible Seals, Lifecycle / Installation History); Mechanical Seal and Compatible Seals removed from the inspector rail (Inventory, Drawings, Documents retained). Header KPI "Current Seal / Seal Status" (seal code + seal_registry catalog status) replaced by "Configured Seal" and "Installed Seal" + "Installation Status" (type-only flagged as not a tracked unit).
- Production read-only replay (2026-09-25): 254 pumps · 39 INSTALLED · 215 NOT_RECORDED · 0 seal units · 36 installed-type-only · 39 with Time Since Installation; every one of the 42 reports now attributed to exactly one pump. No migration, no data change.

## LTSA_ASSET360_INSTALLED_SEAL_SIZE_R1_1
- **Installed Seal Size** added to the Current Installation contract and Asset 360: `installed_seal_size` on `InstallationEvent` and `CurrentInstallation`, taken only from `installation_report.seal_size` of the same report the R1 contract selects (each history event keeps its own report's size). Source text is preserved verbatim (trimmed only; e.g. `4.1/2"`, `2.375"`, `55 MM`), blank/NOT_RECORDED/REMOVED → null; no normalization, no numeric size field. Never derived from `ltsa_pumps`, compatibility/`seal_registry` shaft size, stock application, seal type/code parsing, drawing/BOM or a sibling report (e.g. 101-P-3B shows its own `2.375"`, not compatibility 2.75; 101-P-2A stays Not Recorded despite sharing drawing GA-243047).
- UI: "Installed Seal Size" row immediately after "Installed Seal Type" (Not Recorded when absent); size on each installation-history entry; compact "Size: …" on the Installed Seal header KPI's secondary line when installed.
- Production read-only replay: 42 reports / 34 with size; 39 current installations / 33 with size / 6 without (101-P-2A, 200-P-4B, 211-P-2A, 212-P-13AR, 212-P-25A, 220-P-3A). Current Installation selection, attribution, service age and CM unchanged. No schema change, no backfill.

## LTSA_INSTALLATION_BASED_MTBF_R1
- **MTBF — Installation-based · Calendar time** (temporary, pump-level only): new pure `CORE-SERVICES/API/installation_interval_contract.py` builds completed intervals between consecutive valid installations of the same pump and same structured position (DE→DE, NDE→NDE, pump-level→pump-level), reusing `current_installation_contract.valid_installation_events` (pump_tag_number attribution, date validation, seal_location-only position). Order report_date ASC, installation_code ASC tie-break only; days = plant-local date difference, hours = days × 24 for DATE_ONLY; same-day pairs excluded as unresolved (never 0 days); mixed positions reported as non-comparable transitions; pump MTBF = mean of completed comparable intervals, null when none. `seal_identity_status` CONFIRMED_SAME / CHANGED / UNKNOWN, never inferred. Installations are a proxy boundary, not confirmed failures; CM/PM/findings/work orders never create boundaries.
- `GET /api/ltsa/pumps/{tag}/knowledge`: additive `installation_based_mtbf` (intervals, counts, mean days/hours, basis, precision). Failure-based `mtbf_days`/`mttr_hours`/`fleet_mtbf_days`/availability untouched; no area/fleet numeric MTBF exposed (coverage 3/254 pumps, 1.18%).
- Asset 360 Mechanical Seal: new "MTBF · Installation-based · Calendar time" group directly after Time Since Installation (Current Service Age stays separate and is never averaged in), with sample size and completed-interval history.
- Production read-only replay: 3 eligible pumps / 3 pump-level intervals — 945-P-9B 20 d / 480 h (CONFIRMED_SAME), 200-P-4B 56 d / 1,344 h (UNKNOWN), 220-P-3A 64 d / 1,536 h (UNKNOWN); 251 pumps Not Available. No persistence, no migration.

## LTSA_INSTALLATION_BASED_MTBF_R1 — Closure (documentation only)
- **Closed and frozen** 2026-09-27 at production `7b9edb3db9873e193ee06eb2b845b5e973a2f944`: technical deployment PASS, authenticated browser UAT PASS, rollback not required, no database change, no migration. No code changed by this entry.
- Locked definition: "MTBF — Installation-based · Calendar time"; completed intervals only within the same pump and same structured position stream (DE→DE, NDE→NDE, PUMP_LEVEL→PUMP_LEVEL); DE → NDE → DE yields one DE→DE interval, mixed transitions are non-comparable audit evidence. Current Service Age (latest installation → today) is separate and never part of the MTBF mean.
- Closure evidence: 254 pumps · 3 eligible · 3 completed intervals · 1.18% coverage; 945-P-9B 20 d / 480 calendar h (CONFIRMED_SAME), 200-P-4B 56 d / 1,344 h (UNKNOWN), 220-P-3A 64 d / 1,536 h (UNKNOWN); 211-P-1A and 701-P-1A Not Available. UAT: 945-P-9B service age 143 d / 3,432 h vs MTBF 20 d / 480 h (1 interval); 211-P-1A service age 128 d / 3,072 h vs MTBF Not Available (0 intervals), Actual Operating Hours N/A.
- Not exposed: fleet/area Installation-Based MTBF numeric KPI (deferred pending coverage and explicit authorization). Failure-based MTBF (`executive_metrics.mtbf_days`, `fleet_mtbf_days`) unchanged; MTTR Unavailable.
- Verification limitation: pre-deploy backup checksum / `pg_restore --list` / table checks passed; disposable restore not performed (local Docker unavailable) — recorded, non-blocking.
- Frozen stack: Current Installation R1, Installed Seal Size R1.1, Service Age, Installation-Based MTBF R1. Open: TD-011–TD-015; 6 current installations without recorded seal size.

## LTSA_HISTORICAL_INSTALLATION_2024_2025_IMPORT_IMPLEMENTATION_R1
- **Migration 039** (`039_extend_historical_seal_service_activity_governed_evidence.sql`, additive only, not applied to production): extends `historical_seal_service_activity` (036) with governed provenance — `historical_event_id` (UNIQUE), `source_hash`, `source_fingerprint` (UNIQUE), `event_fingerprint`, `position` (DE/NDE/PUMP_LEVEL) + `position_source_raw`/`position_extraction_reason`, `source_date_raw`/`parsed_source_date`/`corrected_event_date`/`date_correction_status` (NOT_REQUIRED/APPROVED)/`date_correction_reason`, `evidence_grade` (DIRECT_EVIDENCE/CORROBORATED), `deduplication_status`, `import_manifest_sha256`, `imported_at`; CHECKs for event type (INSTALLATION / REINSTALLATION_REFURBISHED_SEAL), approved-correction consistency and complete governed provenance; **append-only** triggers rejecting UPDATE/DELETE/TRUNCATE; documented (commented) rollback.
- **Governed executor** `PRODUCTS/LTSA-BRAIN/INGESTION/historical_installation_manifest_executor.py`: raw-byte SHA-256 before parsing; strict row validation (review-queue rows, unresolved assets, unapproved corrections, unsupported grade/type/position, duplicate IDs/fingerprints all rejected; IDs and fingerprints recomputed); read-only preflight → PROPOSED_INSERT / ALREADY_IMPORTED / CONFLICT (incl. same pump+date as a governed installation_report); dry run by default; apply only for the approved manifest hash with `--expected-rows`, `--expected-inserts` and `--confirm-historical-installation-import <sha256>`; one atomic insert-only transaction with in-database pre/post checks; post-import field-identical verification; idempotent re-run.
- **MTBF read model** (MTBF R1 reopened for input wiring only): `EquipmentTimelineService.build_installation_based_mtbf` feeds `installation_report` + governed historical evidence (new adapter `API/historical_installation_evidence.py`) into the unchanged `installation_interval_contract`; formula, positions, same-day, right-censoring and seal-identity semantics unchanged. Current Installation and Service Age still read only `installation_report`. Degrades to report-only input if migration 039 is absent.
- Repository: `HistoricalSealServiceActivityRepository.list_governed_installation_events_by_pump` (governed rows only; `list_by_pump` unchanged). Lifecycle timeline labels: "Historical Service Activity" / "Reinstallation (Refurbished Seal)".
- `historical_seal_service_activity_ingestion.py` marked **DEPRECATED** (labels every row as installation, ignores the governed manifest, stores swapped dates, no review separation, obsolete execution targets); its `--apply` is disabled.
- Verified in a disposable Postgres (canonical schema + 018 + 036 + 039): frozen approved manifest (88 rows, sha256 `6bae2f11…`) dry run 88 proposed → apply 88 inserted, field-identical → re-run 0 proposed / 88 already imported; UPDATE/DELETE/TRUNCATE rejected; combined MTBF 29 pumps / 36 intervals / 11.42% (35 pump-level + 1 NDE; 5 non-comparable transitions; 0 same-day); Current Installation 39 resolved, examples and service ages unchanged. **Not imported into production.** Review queue (30 rows) stays outside the database.

## LTSA_HISTORICAL_INSTALLATION_2024_2025 — Production closure (documentation only)
- **Closed and frozen** 2026-09-27 at production runtime `7ccea618c7e4119bca4e015840a2b06cf5453fc7`. No code changed by this entry.
- **Migration 039** applied to production 2026-09-27T10:34:17Z (release file sha256 `4b136e53…`), recorded CONFIRMED_APPLIED in `schema_migration_history`; 53 columns, 8 `hssa_*` constraints, append-only UPDATE/DELETE/TRUNCATE triggers; no business data changed.
- **Governed import COMPLETE:** true production dry run 88 proposed / 0 already imported / 0 conflict / 0 rejected; apply inserted 88 in one atomic transaction, 88/88 field-identical, 88 distinct `historical_event_id` and `source_fingerprint`, all carrying manifest sha256 `6bae2f11…`; post-apply dry run 0 / 88 / 0 / 0 (idempotent). Evidence: `production_apply_r1.json` (`c607d996…`), `production_dryrun_post_apply_r1.json` (`f884aad9…`). Review queue imported: 0.
- **Minimal API deployment COMPLETE:** API image rebuilt from `7ccea61` (9/9 key files match release blobs) and replaced alone; dashboard image unchanged; rollback tag `ai5r/api:rollback-7b9edb3` (`da04bcc7…`) retained.
- **Production UAT PASS:** API health; served Installation-Based MTBF 130 events → 29 pumps / 36 intervals / 11.42% (35 PUMP_LEVEL, 1 NDE, 5 non-comparable, 0 same-day); 110-P-8B 392 d (CHANGED) + 69 d (CONFIRMED_SAME), mean 230.5 d; 101-P-2A no completed interval; Current Installation 39 resolved, 0 historical-sourced, all-254-pump digest identical before/after; Service Age unchanged; lifecycle labels "Historical Service Activity" / "Reinstallation (Refurbished Seal)"; CM 4999 rows / 16 active leaks.
- Known pre-existing failure recorded, not fixed: executive analytics `wo.work_type` (`TD-020`). New build-hygiene item `TD-021`. `TD-018` stays open (22/36 intervals CHANGED).

## LTSA_MECHANICAL_SEAL_UNIFIED_NAVIGATION_FIX_R1 / RELEASE_INTEGRATION_R1
- **One Mechanical Seal workspace:** the sidebar exposes only "Mechanical Seal"; the separate "Mechanical Seal Stock" primary item and the "Open Mechanical Seal Stock" Quick Action are removed. Transplanted unified workspace `2871ebd` (cherry-picked alone as `7d16da7`; its side branch was not merged) plus release-lineage follow-ups.
- **Complete-seal stock retained inside it:** every `mechanical_seal_stock_pool` row is its own configuration row (verified against production: 44/44 pools, 107 sets, 226 applications, 0 field mismatches); Inventory tab shows available / on hand / reserved, physical and nominal size, location, verification status, complete-seal GPN, pool compatibility status and per-application GPNs (GPN still role-gated by the API); application equipment tags are searchable.
- **Per-seal stock label:** registry seals without a pool now list their own `seal_stock` quantity (same resolution as the detail view; 0 = "0 sets", null quantity = "Unknown", no source = "N/A"). KIMAP/GPN "Updated By / Updated" attribution preserved in the unified list.
- **Compatibility route:** `/ltsa/inventory` (direct load, reload, bookmark, back/forward) resolves to the unified Mechanical Seal workspace instead of falling back to the Executive Dashboard; in-app navigation to the legacy key lands on `/ltsa/seal`.
- Dashboard only: no database, schema, migration or backend change. The legacy stock page is no longer routed or bundled; its source, test and `TAB_PERMISSIONS.inventory` are kept temporarily. Stock pool retrieval >100 pools recorded as `TD-022`. BOM, usage history and additional document read paths are NOT part of this release.
- **Production:** deployed 2026-09-27 at `20eb68c` (dashboard only; image `29c2d088…`, rollback `ai5r/dashboard:rollback-7ccea61` → `edc0fc76…`; API and database unchanged).

## LTSA_MECHANICAL_SEAL_STOCK_FILTER_HOTFIX_R1 — Production closure
- **Closed and frozen** 2026-09-28. Hotfix `b18f355` (frontend only) deployed dashboard-only: image `sha256:8c135eb814391287ba57999ce66dafc8a4dc29d8ff064c116f5c69a2138c6b07`; rollback `ai5r/dashboard:rollback-20eb68c` → `sha256:29c2d088454b639cbb965c398dbed0a96ad1c4c0f9ca5995ac82b91a99cb338e`; API remained `sha256:623f955c…` (same start time); no DB mutation, no migration, no backend deployment.
- **Root cause:** `seal_stock` quantities arrive from n8n as numeric strings (`"0"`); the "Out of Stock" filter and low-stock highlight compared strictly with the number `0`, so `"0"` never matched although the label correctly read "0 sets".
- **Fix:** one canonical `parseStockQuantity` / `stockStatus` (`sealMapping.js`) used by label, KPI fallback sum, filter pills and highlight — OUT_OF_STOCK (≤ 0), IN_STOCK (> 0), UNKNOWN (null/undefined/empty/whitespace/non-numeric; never coerced to zero), NO_STOCK (no record, "N/A"); the "Unknown / N/A" pill keeps grouping UNKNOWN + NO_STOCK.
- **Production validation (data level):** 61 registry seals, 65 unified configuration rows; In Stock 42 / Out of Stock 8 / Unknown or N/A 15 (partition 65/65); the 8 Out of Stock rows are the `seal_stock`-fallback registry seals carrying `"0"` (e.g. LTSA-SEAL-T15WT-1-3-4 → "0 sets" → OUT_OF_STOCK); no unknown quantity classified Out of Stock.
- **UAT:** technical deploy PASS · data-level UAT PASS · authenticated browser UAT PENDING (pill click, rendered red highlight, sidebar rendering, in-app routing); the pending checks do not reopen the stock normalization.
- Open, kept separate: `TD-022` (pool retrieval cap 100; 44 pools), `TD-023` (migration 013 identifier schema drift; not applied at closure).

## LTSA_SEAL_IDENTIFIER_SCHEMA_REMEDIATION_R1 — migration 013 applied late (production schema only)
- **Finding:** migration `013_alter_seal_registry_identifiers_attribution.sql` was authored 2026-08-18 (`92a9af3`) but never applied to the existing production database (production `seal_registry` was provisioned 2026-08-17 in its pre-013 shape; every other migration 005–039 with detectable objects is present).
- **Remediation 2026-09-28:** the original, unmodified 013 from release `1acd237` (sha256 `ab9c75ccc5cd08d06ea4e22b0d9a9eab249179fb31de9dbbdb08a4d6c04b64c6`) applied once at 03:21:42Z (psql exit 0). Preceded by backup `/home/unikom666/AI5R-PROD-BACKUPS/ltsa_brain_pre_migration_013_seal_identifiers_remediation_20260928T032013Z.dump` (812,126 bytes, sha256 `3176413b9fa8fd207621df91b2d8b5f12bf1e8bfa870a88cd2cd68d44b671c06`; `pg_restore --list` PASS; disposable restore PASS; rehearsal of 013 on the restore PASS and idempotent).
- **Result:** four nullable, default-less columns added — `kimap_pertamina`, `gpn_john_crane` (TEXT), `created_by`, `updated_by` (UUID); no backfill, no values invented; 61 existing rows intact (11-column digest unchanged) and NULL in the new columns; PK, indexes, triggers and 11 inbound FKs unchanged.
- **History:** `schema_migration_history` row for 013 with status `CONFIRMED_APPLIED`, the actual execution time as `applied_at`, and a `LATE_APPLICATION` verification note (6 rows now). 005–012 / 014–033 bookkeeping NOT reconstructed; 038 remains applied-but-unrecorded (separate known issue).
- **Contract:** `/api/ltsa/seals` returns the four fields (all NULL) → UI still shows "—" / "Imported / system data" until genuine values are entered; the KIMAP/GPN PATCH path now references existing columns (schema-compatible; production write UAT not performed). No API/dashboard deploy, no restart, no code change. `TD-023` closed.
