# Technical Debt

Status: ACTIVE — records architectural debt, known issues, RCA findings, and deferred work.
Update whenever new technical debt is identified.

---

## Open Items

### TD-001 — `RELEASE/*` auto-generated stub schema (defect)
`PRODUCTS/LTSA-BRAIN/RELEASE/{database.sql,schema.json,openapi.json}` contain a second, parallel, column-less stub schema (`id SERIAL PRIMARY KEY` only) for every module in `product.manifest.json`, under mismatched, naively-pluralized names (e.g. `ltsa_knowledge_source_registrys`). Root cause: three unit tests in `AI5R-SDK/FACTORY/TESTS/{test_sql_generator,test_schema_generator,test_openapi_generator}.py` write to the real product path instead of a fixture/temp path, and re-run on every bare `pytest` invocation (`pytest.ini` sets `testpaths = AI5R-SDK`). Not attributable to, and does not affect, any Engineering Knowledge Acquisition MWO. See `ENGINEERING/MWO/RCA-001-RELEASE-Stub-Schema-Root-Cause-Analysis.md` for full analysis and two remediation options (retire vs. properly integrate). **Awaiting Chief Architect decision.**
**Re-triggered again during `MWO-LTSA-050` WP-001's own regression testing** (a bare `pytest -q` run, before this session adopted the `MWO-LTSA-049`-precedent scoped-invocation workaround): `database.sql`/`schema.json`/`openapi.json` mtimes advanced further, and two additional untracked stub artifacts appeared (`release.json`, `workflow.json`). Same known, disclosed, non-canonical side effect — not caused by, and not part of, this MWO's own Pump Factory Pack implementation. Not reverted (reverting generated test-hygiene noise without a retire/fix decision is not this MWO's call); recommended excluded from this MWO's commit.

### TD-002 — Workbook Acquisition does not conform to ADR-004 (known, tracked, not yet remediated)
`workbook` (MWO-LTSA-040C) has no `workbook_metadata`/`workbook_classification`, and its `acquisition_job` is shared with `mapping_profile_id` rather than dedicated. Retrofit fully specified in `ENGINEERING/MWO/MWO-LTSA-040C-R1-Workbook-Acquisition-Pattern-Alignment.md`, approved as specification only. **Awaiting Implementation Approval.**

### TD-003 — Minor naming inconsistency (pre-040-series, low priority)
`seal_pump_compatibility`'s FK references `ltsa_pumps` without a `public.` schema prefix, unlike every table from MWO-040A onward. Predates the Engineering Knowledge Acquisition epic (MWO-030 era); functionally harmless (same default schema) but inconsistent style. No MWO currently scopes fixing it.

### TD-004 — `CONSTITUTION/README.md` cross-reference drift (pre-existing, low priority)
`CONSTITUTION/README.md` lists a read order using hyphenated filenames (`00-VISION.md`, `01-MANIFESTO.md`, …) that do not match the actual files present in `CONSTITUTION/` (underscore-named: `00_IDENTITY.md`, `01_MISSION.md`, …, plus a mix of hyphen- and underscore-named files). Noted during documentation-contract work; not remediated here (documentation-only mission, out of the requested scope).

### TD-005 — Rename `MEMORY.md` → `ENGINEERING_MEMORY.md` (recommended, deferred)
`MEMORY.md` (frozen engineering decisions) shares its name with an already-overloaded AI5R platform term: `CONSTITUTION/10_MEMORY_POLICY.md` defines four platform Memory categories (Conversation/Organizational/Knowledge/Experience), `ROADMAP/MASTER_ROADMAP.md` lists MEMORY as a top-level platform pillar, and `ARCHITECTURE/MEMORY.md` (currently empty) is the more likely home for that future subsystem's documentation. Recommended in `ENGINEERING/MWO/EOPS-001-AI5R-Engineering-Operating-System-Review.md` §5. **Explicitly kept as technical debt only — do not rename now** (Chief Architect directive, `EOPS-002`). Low cost today (no inbound links from committed history); revisit if a real platform-Memory-subsystem document is about to be created under `ARCHITECTURE/MEMORY.md` or elsewhere.

### TD-006 — Duplicate `ManufacturingEvent` class definitions — **elevated, not ordinary debt**
Per explicit Chief Architect directive, this finding is **not classified as ordinary Technical Debt**. It is tracked as its own Architecture Review record: see `ENGINEERING/MWO/ARCH-REVIEW-002-Canonical-ManufacturingEvent.md` (Status: **DEFERRED**, Target: **After LTSA v1.0**). This entry exists only as a pointer, so `TECHNICAL_DEBT.md` and `ARCH-REVIEW-002` do not carry two independent descriptions of the same finding.

### TD-007 — `MissionRuntime` exception propagation on worker execution failure — **HIGH PRIORITY, deferred**
`MissionRuntime.run()` (`AI5R-SDK/RUNTIME/mission_runtime.py`) handles a "no worker available" task failure gracefully (`task.fail(...)`, then continues the loop), but has no exception handling around `TaskExecutionEngine.execute()`. Since `TaskExecutionEngine` re-raises after recording the failure on the task (`task_execution_engine.py:20-22`), any exception from a worker's `execute()` propagates uncaught, aborting the entire mission mid-loop — `mission.complete()` is never reached and all previously-accumulated results are lost. Confirmed by direct code/test re-read; untested by any existing test. Full analysis: `ENGINEERING/MWO/MWO-PLT-004-Worker-Runtime-Alignment.md` §5. **Classified HIGH PRIORITY by Chief Architect directive, but explicitly deferred — do not implement unless this becomes a direct blocker for LTSA v1.0.** Current objective is LTSA Manufacturing, not Worker Runtime hardening.

### TD-008 — Worker Runtime lifecycle gaps (lifecycle, reservation, recovery, observability, mutual exclusion) — **deferred**
Five related findings from `MWO-PLT-004`'s Worker Runtime Alignment research, all tracing to the same root cause — `EnterpriseWorker.status` is a decorative field nothing in the orchestration chain reads or writes:
1. **Worker status lifecycle** — no transitions exist, unlike `EnterpriseTask`/`EnterpriseMission`'s own guarded state machines.
2. **Worker reservation** — `WorkerAssignmentEngine.assign()` is pure selection, never marks a worker unavailable.
3. **Worker recovery** — no retry, requeue, or dead-letter mechanism exists anywhere in `RUNTIME/`.
4. **Worker observability** — no event bus, logging, or metrics in this chain, unlike `UMR-001`'s own `ManufacturingEventBus` on the Manufacturing side of the platform.
5. **Worker mutual exclusion** — nothing prevents the same worker from being selected for a second task while a prior one is still outstanding; currently masked only by `MissionRuntime`'s single-threaded sequential loop, not by any actual reservation mechanism.

Full analysis: `ENGINEERING/MWO/MWO-PLT-004-Worker-Runtime-Alignment.md` §1–§4, §6–§7. **Classified DEFERRED by Chief Architect directive — do not implement unless a finding becomes a direct blocker for LTSA v1.0.** Current objective is LTSA Manufacturing.

### TD-010 — `pump_identity_resolver.py`/`seal_identity_resolver.py` compute an incorrect `AI5R-SDK` path (latent bug, not yet blocking)
`PUMP-FACTORY-PACK/pump_identity_resolver.py` and `SEAL-FACTORY-PACK/seal_identity_resolver.py` both compute `Path(__file__).resolve().parents[2] / "AI5R-SDK"`, which resolves to `PRODUCTS/AI5R-SDK` (does not exist) instead of the real repo-root `AI5R-SDK` (would require `parents[3]`). Confirmed directly: `(Path(__file__).resolve().parents[2] / "AI5R-SDK").exists()` returns `False`. Harmless *in isolation* only because a nonexistent `sys.path` entry is silently skipped by Python's import system when another, correct entry is also present — discovered while building `PRODUCTS/LTSA-BRAIN/AI-EXTRACTION/resolve_identity_cli.py` (LTSA-BRAIN Document Upload MVP), which needed to import both resolver modules and worked around the bug by inserting the correct path itself before importing, rather than modifying either file (out of scope for that MWO). Not yet fixed anywhere. Low priority today since every current caller either provides its own correct path or (like `resolve_identity_cli.py`) works around it, but any future caller that imports these modules from a different working context without doing so will hit an `ImportError` for `FACTORY.FOUNDATION.manufacturing_context`/`FACTORY.RESOLUTION.identity_resolver`.

### TD-009 — `AI5R-SDK/MANUFACTURING`/`AI5R-SDK/FACTORY` namespace collision — **confirmed, future Architecture Review candidate, not elevated yet**
`AI5R-SDK/MANUFACTURING/{ORDERS/manufacturing_order.py, OBJECTS/manufacturing_object.py}` define `ManufacturingOrder` and `ManufacturingObject` classes that share their names with, but are structurally different from and unrelated to, `AI5R-SDK/FACTORY`'s own same-named classes that `UMC-001`/`UMR-001` govern — confirmed by direct field-level comparison (`MANUFACTURING.ManufacturingOrder`: `order_id`/`product_name`/`product_type`/`requested_by`/`recipe_id`/`dbom_id`/`priority`/`status` enum/`canonical_base`, vs. `FACTORY`'s own differently-shaped `ManufacturingOrder`). `AI5R-SDK/MANUFACTURING`'s system (`ManufacturingRecipe`/`ProductionLine`/`DigitalBillOfMaterials`/`DigitalFactory`) is used today only to manufacture organizational artifacts (Company/Department/Role via `{company,department,role}_recipe_registration.py`), a different domain than `UMC-001`'s LTSA/business-object manufacturing. Discovered during `MWO-LTSA-053` (Installation Factory Pack) research, §5/§7 Open Question 3. Same category of finding as `TD-006`/`ARCH-REVIEW-002`'s `ManufacturingEvent` collision. **Per explicit Chief Architect directive: confirmed real, but not resolved within `MWO-LTSA-053`, and not elevated to its own Architecture Review yet — recorded here as a future Architecture Review candidate only.** Current objective is LTSA Manufacturing.

### TD-011 — Remaining `plant_equip_no` attribution consumers (installation) — **known, not in LTSA_ASSET360_CURRENT_INSTALLATION_AND_SERVICE_AGE_R1 scope**
`LTSA_ASSET360_CURRENT_INSTALLATION_AND_SERVICE_AGE_R1` moved `EquipmentTimelineService` (Asset 360 / current seal / lifecycle / Equipment 360 / Copilot `current_seal`) to the governed `installation_report.pump_tag_number`. Still attributing by free-text `plant_equip_no`: Copilot's tag-scoped installation list and fleet "latest installation" answer (`copilot_ask_service.py`, `plant_equip_no == tag` / `asset_field="plant_equip_no"`), the `/api/ltsa/installations` area-scope filter (`routers/installation.py`), and `record_edit_service.py`'s scope field. For the 5 production reports whose `plant_equip_no` differs (INSTL-002/025/038/041/043) these surfaces can show a report under the sibling pump or hide it from its real pump's scope. Remediation: same attribution switch, separate MWO.

### TD-012 — Installation position evidence is structured on one report only
Only `installation_report.seal_location` is accepted as DE/NDE position evidence (1 of 42 rows: INSTL-043 = NDE). INSTL-003 (211-P-2A) says "(DE)" only in its source file name, so it resolves as a pump-level installation by design (position is never inferred from free text). Populating `seal_location` from the source documents would make DE/NDE currents per pump possible; data correction only, needs its own authorization.

### TD-013 — `asset_registry.area` label drift
Pump areas mix spellings for the same area (`SPK`/`S_PAKNING`, `OM`/`OIL MOVEMENT`, `UTL`/`UTILITIES`, `REAKTOR`/`Reaktor`, `FRAKSINASI`/`Fraksinasi`). Fleet breakdowns must normalize ad hoc. Found during the Asset 360 installation audit; not remediated.

### TD-014 — Pre-existing Asset 360 test drift (`knowledge-section-condition`)
`test_knowledge_workspace.test.jsx` and `test_knowledge_workspace_asset360.test.jsx` still expect a `condition` KnowledgeSection that the current `KnowledgeWorkspace.jsx` no longer renders; these fail on base `4f08c57` (part of the 98 pre-existing frontend failures) and were left failing, unchanged in cause, by `LTSA_ASSET360_CURRENT_INSTALLATION_AND_SERVICE_AGE_R1`, which added standalone tests for its own layout assertions.
### TD-015 — `ExecutiveDashboard.rc002.test.jsx` mock gap (order-dependent test failures)
Run on its own, the file fails 40/53 tests on base `4f08c57` and later: its `vi.mock("../../../api/ai5rClient")` lacks `getLtsaAnalyticsExecutive`. In full-suite runs the "routes the 'seal' key to the Seal page" test flips between pass and fail by execution order. Pre-existing, not caused by the Asset 360 installation work; left unfixed by explicit scope lock.


### TD-016 — Historical installation review queue (30 rows) unresolved
The 2024/2025 Service Activity evidence has 30 rows outside the approved manifest: 18 family tags without an A/B suffix, `702-P-4B SPARE`, 8 unmatched/non-pump tags, the possible duplicate `110-P-15A` (2024-11-13 / 2024-11-15) and 2 rows without a completion date. Owner: HUMAN_REVIEW_TAP_ENGINEERING. Resolution must produce a separate, hash-frozen correction/approval manifest; no fuzzy resolver, no automatic aliasing.

### TD-017 — Deprecated `historical_seal_service_activity_ingestion.py` still in the tree
Superseded by `historical_installation_manifest_executor.py`; `--apply` disabled. Kept only because `test_historical_seal_service_activity.py` imports its extraction helpers. Remove (with those tests reworked) in a cleanup MWO.

### TD-018 — Historical seal identity reads CHANGED for notation-only differences
Frozen R1 compares seal type/size verbatim, so historical `1.7/8''` / `3.1/2IN` vs report `1.7/8"` yields CHANGED (19 of 22 CHANGED intervals in the approved-manifest projection are notation-only; 3 are substantive). A comparator-only canonicalization was designed and tested in the audit but deliberately NOT wired into `seal_identity_status`; changing it needs an explicit decision.

### TD-019 — Frozen manifest and production baseline are external test inputs
`test_frozen_manifest_full_replay` is data-gated on `LTSA_HIST_INSTALL_MANIFEST` / `LTSA_HIST_INSTALL_BASELINE` (never committed: governed data). Custody copy: `AI5R-LTSA-HISTCM/TEMP/historical_installation_r1/` (untracked). CI without them skips that test (synthetic disposable-DB tests still run).

---

This file was created as part of a documentation-only mission (Chief Architect directive). No LTSA implementation, Runtime, or BUILD-PACK file was touched in producing it.
