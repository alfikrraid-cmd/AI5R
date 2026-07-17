# MWO-LTSA-049 — Universal Manufacturing Runtime

Status: WP-000 DRAFTED (Research Only) — awaiting separate, explicit Implementation Approval
Type: Manufacturing Work Order (Cross-Product Runtime — Research/Specification Layer)
Epic: AI5R Digital Factory — Universal Manufacturing Contract execution (successor to MWO-LTSA-048)
Role: Implementation Engineer
Architecture: FROZEN — this document proposes reuse and minimal extension only; no new runtime, no redesign
Foundation: v1.0 — LOCKED, unchanged
Engineering Standard: v1.0 — LOCKED, unchanged
Basis: Direct read of every file under `AI5R-SDK/FACTORY/{CORE,FOUNDATION,ORDERS,MANUFACTURING,RESOLUTION,RESOLVERS,VALIDATION,PACKS,EXECUTION,RUNTIME,PIPELINE,STATIONS}`; `MWO-LTSA-048`'s own WP-000 Rev. 3 and Completion Report (UMC-001's definition and implementation).
Scope: Research only, per explicit instruction. No file created or modified under `AI5R-SDK/FACTORY`, `PRODUCTS/LTSA-BRAIN`, or anywhere else.

---

## 1. Existing Runtime Inventory

Direct read of every orchestration-shaped file in `AI5R-SDK/FACTORY` found **four distinct, already-built execution chains**, not one. They are not redundant copies of the same thing — each solves a different problem — but their coexistence, undeclared and undocumented until now, is itself a finding (§8).

| Chain | Entry Point | Steps | Produces |
|---|---|---|---|
| **A — Manufacturing Runtime chain** | `FOUNDATION.manufacturing_runtime.ManufacturingRuntime.run(definition, workspace_root)` | `BuildWorkspace.create()` → publish `BUILD_STARTED` (`ManufacturingEventBus`) → `FactoryOrchestrator.manufacture(definition)` [`FactoryValidator.validate()` → `FactoryCompiler.compile()` running a `ManufacturingPipeline` of `BaseManufacturingStation`s → `FactoryFreeze.freeze()`] → publish `BUILD_COMPLETED` → `BuildReport.write_all()` | A validated, compiled, frozen manufacturing result + a written build report + a captured event log |
| **B — Manufacturing Engine chain** | `MANUFACTURING.manufacturing_engine.ManufacturingEngine.manufacture(unit, output_dir)` | `StationDiscovery.discover("GENERATORS")` → `StationRegistry` → `DependencyGraph`/`TopologicalSorter` → runs each generator station's `run(unit, target)` | `database.sql`, `schema.json`, `openapi.json`, `workflow.json`, `release.json` at `output_dir` — **confirmed, this session, to be the actual origin of `PRODUCTS/LTSA-BRAIN/RELEASE/*`'s full 5-file set** (a strictly stronger finding than `RCA-001`/`RCA-002`, which only traced 3 of the 5 to individual unit tests and left `workflow.json`/`release.json` as "unconfirmed origin" — this chain, run with `output_dir="PRODUCTS/LTSA-BRAIN/RELEASE"`, would produce all 5) |
| **C — Manufacturing Service chain** | `MANUFACTURING.service.ManufacturingService.manufacture_module(module_name, product)`, invoked by `factory.py build <product>` / `ProductBuilder.build()` | Loads a registry entry (`REGISTRY/loader.py`) → hand-rolled SQL/schema/workflow generation methods → writes to `PRODUCTS/<product>/BUILD-PACKS/BP-<module>/*` | A scaffolded build pack (currently only wired for `PUMP`/`SEAL` registry entries — the real LTSA-BRAIN build packs in this epic were hand-authored per MWO, not produced by this chain) |
| **D — Factory Runtime chain** | `RUNTIME.factory_runtime.FactoryRuntime.run(production_plan, output_root="BUILD")` | `FactoryExecutionEngine.execute()` (templated artifact generation, `TEMPLATE_MAP` covers a FastAPI login-app scaffold) → `BuildValidator.validate()` → `ZipExporter.export()` | A generated FastAPI project skeleton + zip, under `BUILD/RUN-<hash>/` — **confirmed, this session, to be the actual origin of the 162 `BUILD/RUN-*` directories** `EOPS-003`/`RCA-002` flagged as generated artifacts of unknown mechanism |

**Two incidental findings, noted and not pursued further (research only, per instruction):** Chain B's and Chain D's default output paths are the direct, confirmed explanation for two open items in `RCA-001`/`RCA-002`/`EOPS-003` (`RELEASE/workflow.json`+`release.json`, and `BUILD/RUN-*`). This closes those open questions with more precision than previously available, but remediating either is outside this MWO's scope.

**Supporting primitives, already inventoried in `MWO-LTSA-048` WP-000, not re-derived here:** `ManufacturingOrder` (+ `VALIDATION.manufacturing_order_validator.ManufacturingOrderValidator`, newly found — validates and stamps `status = "VALIDATED"`), `ManufacturingContext`, `BaseManufacturingStation`, `ManufacturingObject`, `ManufacturingEvent`/`ManufacturingEventBus`, `ManufacturingResult`, `ManufacturingPipeline`, `FactoryPack`/`FactoryPackContract`/`FactoryPackLoader`, `ProductResolver`.

**A fifth, unrelated pipeline, explicitly distinguished so it is not mistaken for a UMC-001 candidate:** `PIPELINE.ltsa_ai_pipeline.build_ltsa_ai_pipeline()` chains the cognitive `STATIONS/*` (Reality→Warehouse→Experience→Memory→Knowledge→Capability→Context→Reasoning→Decision→Recommendation→Action, per Constitution Principle 7) via `PIPELINE.pipeline_orchestrator.PipelineOrchestrator`. This is AI5R's **cognitive/BRAIN pipeline** — a different system solving a different problem (turning observations into decisions) than UMC-001 (manufacturing canonical business objects from acquisition data). It reuses `BaseManufacturingStation` (the same base class Chain A's stations use), which is legitimate shared infrastructure, not evidence these two pipelines are the same thing. Not a candidate for UMC-001 execution.

---

## 2. UMC-001 Compliance Matrix

Checked stage-by-stage against **Chain A** (`ManufacturingRuntime` → `FactoryOrchestrator` → `FactoryCompiler`/`ManufacturingPipeline`), the only chain that threads Manufacturing-domain concepts together end-to-end:

| # | UMC-001 Stage | Primitive Exists? | Actually Executed by Chain A Today? | Evidence |
|---|---|---|---|---|
| 1 | Manufacturing Request | Yes — `ManufacturingOrder` + `ManufacturingOrderValidator` | **No.** `ManufacturingRuntime.run(definition: dict, ...)` takes a raw `dict`, never constructs or accepts a `ManufacturingOrder`. `ManufacturingOrderValidator`/`ProductResolver` are only exercised by their own unit tests. | Direct read of `manufacturing_runtime.py`; repository-wide `grep` confirms `ManufacturingOrder` is never imported by `manufacturing_runtime.py`, `factory_orchestrator.py`, `factory_compiler.py`, or `manufacturing_pipeline.py`. |
| 2 | Manufacturing Context | Yes — `ManufacturingContext` dataclass | **No.** `ManufacturingRuntime.run()` extracts `build_id`/`product` as local variables from `definition`; it never instantiates `ManufacturingContext` or passes one through the pipeline. | Direct read of `manufacturing_runtime.py` — no `ManufacturingContext(` construction anywhere in the chain. |
| 3 | Manufacturing Validation | Yes — `BaseManufacturingStation.validate()`, plus a separate `FactoryValidator` at the definition level | **Partially.** `FactoryValidator.validate(definition)` checks `product`/`version`/`factory` are present (definition-level, coarse). Per-station `BaseManufacturingStation.validate()` runs only if the pipeline's stations are themselves `BaseManufacturingStation` subclasses — true for `STATIONS/*` (cognitive pipeline), **not yet exercised by Chain A with any Manufacturing-object station**, since no such station has been registered in `StationRegistry` for this purpose. | Direct read of `factory_validator.py`, `factory_compiler.py`, `station_registry.py`. |
| 4 | Identity Resolution | Yes, as of `MWO-LTSA-048` — `IdentityResolver` (interface only) | **No.** Confirmed by repository-wide search: `IdentityResolver` is referenced only inside its own defining file and its own test — zero references from any of the four chains. | `grep -rl "IdentityResolver"` — 2 hits, both from `MWO-LTSA-048`'s own deliverables. |
| 5 | Relationship Resolution | Yes, as of `MWO-LTSA-048` — `RelationshipResolver` (interface only) | **No.** Same evidence as above. | `grep -rl "RelationshipResolver"` — 2 hits, both from `MWO-LTSA-048`'s own deliverables. |
| 6 | Canonical Object Manufacturing | Yes — `ManufacturingObject`, produced by `BaseManufacturingStation.manufacture()` | **Yes, but only within `STATIONS/*`'s cognitive-object context** (`KNOWLEDGE_OBJECT`, etc.), never yet for a business-domain canonical object (Pump, Seal, etc.) — no station of that kind has been written. | Direct read of `STATIONS/knowledge_manufacturing_station.py` and siblings, all subclass `BaseManufacturingStation` and do produce a `ManufacturingObject`-shaped result via `.manufacture()`. |
| 7 | Event Publication | Yes — `ManufacturingEvent`/`ManufacturingEventBus` | **Yes.** `ManufacturingRuntime.run()` publishes `BUILD_STARTED`/`BUILD_COMPLETED` through a real `ManufacturingEventBus` instance, and every `BaseManufacturingStation.manufacture()` call independently emits its own event (currently only captured within that call's own `ManufacturingResult.events`, not re-published to the shared bus — a wiring gap, not a missing primitive). | Direct read of `manufacturing_runtime.py`, `manufacturing_station.py`. |
| 8 | Manufacturing Result | Yes — `ManufacturingResult` | **Yes**, at the per-station level (`BaseManufacturingStation.manufacture()` returns one); Chain A's own top-level return value is a differently-shaped dict (`{"status": "RUNTIME_COMPLETED", "workspace", "manufacturing", "events"}`), not a `ManufacturingResult` instance itself. | Direct read of both files. |
| 9 | Manufacturing Lifecycle | Yes — `ManufacturingRuntime`/`FactoryOrchestrator`/`ManufacturingPipeline`/`PipelineBuilder`/`StationRegistry` | **Yes.** This is the one stage fully, genuinely exercised end-to-end today — a `ManufacturingRuntime.run()` call really does drive validate → compile (pipeline of stations) → freeze → report, with real event publication around it. | Direct read, traced call by call. |

**Summary: 2 of 9 stages fully compliant (7, 9); 2 partially compliant (3, 8); 5 not compliant (1, 2, 4, 5, 6 — the last only compliant in an unrelated domain).**

---

## 3. Missing Components (for full UMC-001 compliance)

Precisely, not generally:

1. **`ManufacturingRuntime.run()` must accept and validate a `ManufacturingOrder`, not a raw `dict`**, as its actual entry point — wiring in the already-existing, already-tested `ManufacturingOrderValidator`. *(Closes Stage 1.)*
2. **`ManufacturingRuntime.run()` must construct a real `ManufacturingContext` and thread it through `FactoryOrchestrator`/`FactoryCompiler`/each station**, rather than passing loose `build_id`/`product` locals. *(Closes Stage 2.)*
3. **A registered, callable `IdentityResolver` and `RelationshipResolver` extension point must be added to the pipeline**, positioned between Validation and Canonical Object Manufacturing, exactly as `MWO-LTSA-048` WP-000 §2 design decision 1 specifies. Today there is no hook of any kind — not a wrong hook, an absent one. *(Closes Stages 4–5.)*
4. **At least one `BaseManufacturingStation` subclass for a real canonical business object** (the first being LTSA-BRAIN's own, e.g. Pump) must exist and be registered in `StationRegistry`, to prove Stage 6 executes for a business object, not only for cognitive objects. **This is LTSA-BRAIN's own future implementation work, not this MWO's** (per `MWO-LTSA-048` WP-000 §6 and the Chief Architect's own framing: "LTSA is only the first Factory Pack that consumes it"). *(Closes Stage 6 — outside this MWO.)*
5. **Per-station events should re-publish to the shared `ManufacturingEventBus`** Chain A already constructs, rather than remaining trapped inside each station's own `ManufacturingResult.events` list. *(Completes Stage 7's wiring — the primitive already works, this is an integration gap, not a missing primitive.)*
6. **Chain A's own top-level return value should be expressible as (or alongside) a `ManufacturingResult`**, so a caller receives one consistent result shape regardless of whether they call a single station or a full runtime pass. *(Completes Stage 8's wiring.)*
7. **A `FactoryPack`-to-Runtime integration point.** Today `FactoryPackLoader.load()` produces a validated `FactoryPack` object that is never passed to any of the four chains. Some explicit call — most plausibly `ManufacturingRuntime` accepting an optional `FactoryPack` alongside the `ManufacturingOrder`, to know which pack's stations/resolvers to invoke — does not exist yet. *(Answers Research Task 4: there is no integration today; one must be added.)*

**None of items 1–3, 5–7 require a new runtime, a new pipeline, or a new engine.** Every one is an extension of `ManufacturingRuntime`/`FactoryOrchestrator`'s own existing call chain (Chain A) — adding parameters, adding two resolver-invocation steps, and re-threading an event bus reference that already exists. Item 4 is explicitly out of this MWO's scope.

---

## 4. Runtime Lifecycle (as it exists today, Chain A traced end-to-end)

```
ManufacturingRuntime.run(definition: dict, workspace_root)
  -> BuildWorkspace(workspace_root).create()
  -> ManufacturingEventBus.publish(BUILD_STARTED)
  -> FactoryOrchestrator.manufacture(definition)
       -> FactoryValidator.validate(definition)            [coarse, definition-level]
       -> FactoryCompiler.compile(definition)
            -> ManufacturingPipeline.run(payload)
                 -> for each station: BaseManufacturingStation.manufacture(payload)
                      -> validate() -> ManufacturingObject -> ManufacturingEvent -> ManufacturingResult
       -> FactoryFreeze.freeze(product, version, result)
  -> ManufacturingEventBus.publish(BUILD_COMPLETED)
  -> BuildReport.write_all({build.json, workspace.json, manufacturing.json, events.json})
```

This is the lifecycle UMR-001 would extend, not replace.

---

## 5. FactoryPack Integration (today: none)

Directly answering Research Task 4: **`FactoryPack` does not currently plug into any runtime.** `FactoryPackLoader.load(path)` reads and validates a pack definition JSON into a `FactoryPack` object and returns it — nothing downstream consumes that object. No chain (A–D) accepts a `FactoryPack` parameter or looks one up. This is a genuine integration gap, not a misconfigured or partially-working integration.

## 6. Runtime Extension Points (where UMR-001 would attach, without redesigning Chain A)

- **`ManufacturingRuntime.__init__`** already accepts an injected `orchestrator`/`event_bus` (constructor injection pattern already used throughout this codebase, e.g. `BaseManufacturingStation`, `ManufacturingService`) — the natural place to also accept an optional `identity_resolver: IdentityResolver`, `relationship_resolver: RelationshipResolver`, and `factory_pack: FactoryPack`, defaulting to `None` (no resolution attempted) to preserve every existing caller's behavior unchanged.
- **`FactoryCompiler.compile()`**, which already runs `ManufacturingPipeline`, is the natural place to invoke the two resolvers between validation and each station's `manufacture()` call — consistent with `MWO-LTSA-048`'s own specified stage ordering.
- **`StationRegistry`/`PipelineBuilder`** already support registering arbitrary `BaseManufacturingStation` subclasses by name — no change needed here at all; a future LTSA-BRAIN Pump-manufacturing station simply registers into this existing mechanism.

---

## 7. UMR-001 Artifact Definition

| Field | Value |
|---|---|
| **Artifact ID** | UMR-001 |
| **Artifact Name** | Universal Manufacturing Runtime |
| **Artifact Type** | Canonical Platform Runtime |
| **Owner** | AI5R Platform |
| **Consumers** | All Factory Packs |

UMR-001, as this research recommends it be scoped, **is not a new runtime** — it is Chain A (`ManufacturingRuntime`/`FactoryOrchestrator`/`FactoryCompiler`/`ManufacturingPipeline`), extended per §3 items 1–3 and 5–7, formally re-designated as the runtime that executes UMC-001. Chains B, C, D remain untouched, continuing to serve their own, different purposes (release-artifact generation, build-pack scaffolding, FastAPI project scaffolding respectively).

---

## 8. Architecture Validation

**No architectural conflict rises to the level of "stop, report only, do nothing further"** — the four chains are not duplicate implementations of the same responsibility (which would violate the Constitution's Canonical Rule); they are four different tools for four different jobs, confirmed by tracing each to a distinct output. However, **one finding is surfaced for Chief Architect confirmation before implementation, not decided unilaterally here**, per this mission's own instruction ("If an architectural conflict is found, stop. Report only."):

> **This research selects Chain A as UMC-001's runtime, over Chains B/C/D, on the grounds that Chain A is the only one already built around Manufacturing-domain concepts (Order, Context, Event, Result, Pipeline of Stations) rather than around a specific artifact-generation task (release files, build-pack scaffolds, FastAPI scaffolds). This is a judgment call this research is confident in, given the evidence in §1–§2, but it is still a selection among four pre-existing, undeclared-relationship-to-each-other chains that no prior document has named or ranked. If the Chief Architect's own mental model of "the Runtime" refers to a different one of the four (or to a fifth I have not found), that should be corrected before WP-001 begins, not discovered during implementation.**

No other conflict was found. `PIPELINE.ltsa_ai_pipeline`'s reuse of `BaseManufacturingStation` alongside Chain A's own use of it is compatible, shared infrastructure, not a conflict (§1).

---

## 9. Migration Strategy (Chief Architect directive)

Per explicit decision, this section names the target state before implementation begins. No file is renamed; this is a labeling/positioning decision recorded for the historical record, not a code change in itself.

| Chain (this document's own naming) | Becomes | Change |
|---|---|---|
| Chain A — `ManufacturingRuntime` / `FactoryOrchestrator` | **UMR-001 — Universal Manufacturing Runtime** | Extended per §3 items 1–3, 5–7 (this MWO's implementation) |
| Chain B — `ManufacturingEngine` | **Release Engine** | Unchanged — remains scoped to release-artifact generation (`database.sql`/`schema.json`/`openapi.json`/`workflow.json`/`release.json`) |
| Chain C — `ManufacturingService` | **Factory Generator** | Unchanged — remains scoped to build-pack scaffolding (`factory.py build <product>`) |
| Chain D — `FactoryRuntime` / `FactoryExecutionEngine` | **Project Generator** | Unchanged — remains scoped to templated project scaffolding (e.g. the FastAPI login-app template) |

No second Runtime is created. Chains B, C, D are not touched, not merged, not deprecated — they retain their own, already-legitimate purposes under their new names. Only Chain A is extended, becoming UMR-001.

---

## Deliverables (this document only)

- This WP-000 document. No `AI5R-SDK/FACTORY` file, `PRODUCTS/LTSA-BRAIN` file, or any other repository file was created or modified in producing it.

## Definition of Done

- WP-000 complete, submitted for approval.
- No implementation performed.
- Nothing committed or pushed.
- The §8 architecture-selection question awaits explicit Chief Architect confirmation before WP-001 (extending Chain A) may begin.

---

Stopping here. Research complete. No implementation performed. Awaiting Implementation Approval.
