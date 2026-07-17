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

---

This file was created as part of a documentation-only mission (Chief Architect directive). No LTSA implementation, Runtime, or BUILD-PACK file was touched in producing it.
