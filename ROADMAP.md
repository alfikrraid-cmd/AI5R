# LTSA Brain Roadmap

## Completed
- BP-001 Pump Database
- BP-002 API Contract
- BP-003 Pump Create Service
- BP-004 Core SDK
- Asset Registry, Seal Registry, Soot Blower Registry, Work Order, Maintenance History (MO-001)
- MWO-LTSA-030 — Mechanical Seal Knowledge Manufacturing
- MWO-LTSA-040A — Knowledge Source Registry
- MWO-LTSA-040B — Engineering Document Acquisition
- MWO-LTSA-040C — Workbook Acquisition (Universal Tabular Data Acquisition)
- MWO-LTSA-040D — PDF Acquisition
- MWO-LTSA-040E — Engineering Media Acquisition (third canonical Acquisition Object, per `ADR-004`)
- Engineering Operating System established, Repository Hygiene reviewed, Architecture Integrity confirmed PASS (`EOPS-001`–`003`, `RCA-002`, `ARCH-REVIEW-001`)
- MWO-LTSA-048 — Canonical Manufacturing Contract: UMC-001 (Universal Manufacturing Contract) established platform-wide in `AI5R-SDK/FACTORY`
- MWO-LTSA-049 — Universal Manufacturing Runtime: UMR-001 established — `ManufacturingRuntime` (Chain A) extended to execute UMC-001; Release Engine/Factory Generator/Project Generator (Chains B/C/D) formally named, untouched
- MWO-LTSA-050 WP-001 — Pump Factory Pack implementation: `PumpIdentityResolver`/`PumpRelationshipResolver` (first concrete UMC-001 Stage 4/5 implementers) and `PumpManufacturingStation` (`FACTORY.CORE.BaseManufacturingStation` subclass), manufacturing a real pump end-to-end through the unmodified UMR-001 runtime; `recipe.json` v1 minimal schema established as the first real `FactoryPack.recipe_path` target (`PRODUCTS/LTSA-BRAIN/PUMP-FACTORY-PACK/`, 17 new tests, all green). WP-000 research (approved, no implementation) superseded by this completed WP-001.
- MWO-LTSA-053 — Installation Factory Pack, WP-000 research (approved) — no implementation; confirmed no canonical Installation object exists (none to be invented speculatively) and surfaced `TD-009` (`AI5R-SDK/MANUFACTURING`/`AI5R-SDK/FACTORY` namespace collision, future Architecture Review candidate)
- MWO-LTSA-052 WP-001 — Mechanical Seal Factory Pack implementation, using `MWO-LTSA-050` (Pump) as the canonical pattern: `SealIdentityResolver`/`SealRelationshipResolver` (Stage 4/5) and `SealManufacturingStation` (`FACTORY.CORE.BaseManufacturingStation` subclass), manufacturing a real seal end-to-end through the unmodified UMR-001 runtime; reuses `recipe.json` v1 schema (`PRODUCTS/LTSA-BRAIN/SEAL-FACTORY-PACK/`, 17 new tests, all green; full regression 157/157). WP-000 research (merged/canonical, approved) superseded by this completed WP-001.

## In Progress / Pending Approval
- MWO-LTSA-040C-R1 — Workbook Acquisition Pattern Alignment (retrofit specification approved; implementation not yet authorized)
- Commit grouping for MWO-LTSA-030/040A–040E (see `ENGINEERING/MWO/EA-001-LTSA-Acquisition-Engineering-Audit-Report.md` §8), the Engineering Operating System, MWO-LTSA-048/UMC-001, and MWO-LTSA-049/UMR-001 (see each MWO's own Completion Report §Commit Recommendation)

## Planned (per MWO-LTSA-040A's own roadmap, WP-000 item 10, and each MWO's Future Dependencies)
- MWO-LTSA-040F — Video Acquisition
- MWO-LTSA-046 through 047 — Engineering OCR, Table Extraction (deferred by MWO-LTSA-040D)
- **Correction (caught during `MWO-LTSA-053` documentation pass; updated again for `MWO-LTSA-052`):** the "MWO-LTSA-050 through 053 — Engineering Media analysis" line previously here was stale — those numbers are now taken by real MWOs: `050` (Pump Factory Pack, completed above), `051` (`ENGINEERING/MWO/MWO-LTSA-051-Engineering-Knowledge-Graph-Research.md`, exists — status not independently re-verified in this session), `052` (Mechanical Seal Factory Pack, WP-001 completed above), `053` (Installation Factory Pack, completed above). Engineering Media (image/video/audio) analysis, if still wanted, needs a new, un-taken MWO number.
- `RELEASE/*` stub-schema reconciliation or retirement (`ENGINEERING/MWO/RCA-001-RELEASE-Stub-Schema-Root-Cause-Analysis.md` §5) — Chief Architect decision pending
- `CORE`/`FOUNDATION` `ManufacturingEvent` duplicate-class reconciliation — tracked as `ENGINEERING/MWO/ARCH-REVIEW-002-Canonical-ManufacturingEvent.md`, Status **DEFERRED**, Target **After LTSA v1.0** (not ordinary Technical Debt, per Chief Architect directive)
- `AI5R-SDK/MANUFACTURING`/`AI5R-SDK/FACTORY` namespace collision (`TD-009`) — confirmed, future Architecture Review candidate, not yet elevated; not resolved within `MWO-LTSA-053`
- Worker Runtime hardening (`TD-007` `MissionRuntime` exception propagation — HIGH PRIORITY; `TD-008` Worker lifecycle/reservation/recovery/observability/mutual-exclusion gaps — DEFERRED), per `ENGINEERING/MWO/MWO-PLT-004-Worker-Runtime-Alignment.md` — paused pending LTSA v1.0; resumes only if a finding becomes a direct blocker
- A canonical Installation object, if pursued — per `MWO-LTSA-053` and explicit Chief Architect directive, must be derived from existing LTSA implementation, not speculative design
- ~~LTSA-BRAIN's own implementation of UMC-001's `IdentityResolver`/`RelationshipResolver` interfaces against UMR-001~~ — **done, see `MWO-LTSA-050` WP-001 above.** Remaining, still-open items from `MWO-LTSA-050` WP-000's own Open Questions, none required by WP-001's scope: an `acquisition_job` → `ManufacturingOrder.customer_request` adapter; retiring the deprecated `BUILD-PACKS/BP-PUMP` stub; a governed translation from `column_mapping.canonical_attribute` strings to real `ltsa_pumps` column names.
