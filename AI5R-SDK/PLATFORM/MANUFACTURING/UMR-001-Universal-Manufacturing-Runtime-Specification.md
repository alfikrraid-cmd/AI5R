# UMR-001 — Universal Manufacturing Runtime Specification

Status: CANONICAL — the reference specification for UMR-001.
Artifact ID: UMR-001
Artifact Name: Universal Manufacturing Runtime
Artifact Type: Canonical Platform Runtime
Owner: AI5R Platform
Consumers: All Factory Packs
Established by: `MWO-LTSA-049` (implementation); this document (specification)
Governs: `AI5R-SDK/FACTORY/FOUNDATION/{manufacturing_runtime,factory_orchestrator,factory_compiler,manufacturing_pipeline}.py`
Known open item: Runtime Result (§9) does not yet fully satisfy this specification — see `MA-002-Manufacturing-Audit-Report.md` §2; kept as a disclosed WARNING, not silently implemented, per Chief Architect directive.
Related: `AI5R-SDK/PLATFORM/MANUFACTURING/UMC-001-Universal-Manufacturing-Contract.md` (the contract this Runtime executes), `ENGINEERING/MWO/MWO-LTSA-048-Canonical-Manufacturing-Contract.md` (UMC-001's own origin/research/approval record), `MWO-LTSA-049-Universal-Manufacturing-Runtime.md` (this Runtime's own research/WP-000), `ARCH-REVIEW-002-Canonical-ManufacturingEvent.md` (a related, separately-tracked open architecture question — not part of this specification's own scope)

Documentation only. This specification describes the Runtime as implemented by `MWO-LTSA-049`; it does not redesign it, and no implementation file is modified in producing it.

**Relocation note:** this document was authored under `ENGINEERING/MWO/` and has been relocated to `AI5R-SDK/PLATFORM/MANUFACTURING/` per the Platform Artifact placement rule established in `MWO-PLATFORM-001-AI5R-Command-Language.md` — Engineering stores work, Platform stores artifacts. Content unchanged by this move.

---

## 1. Purpose

UMR-001 is the one platform-level runtime that executes UMC-001 (the Universal Manufacturing Contract) for any Factory Pack. It exists so that every Factory Pack — LTSA, Auditor, School OS, Hospital, and future products — manufactures canonical objects through the same lifecycle, the same request/context/result shapes, and the same extension points, rather than each product inventing its own manufacturing orchestration.

UMR-001 is not a new runtime. It is `AI5R-SDK/FACTORY/FOUNDATION.ManufacturingRuntime` (identified as "Chain A" during `MWO-LTSA-049`'s own research), extended to genuinely execute UMC-001's stages. Three sibling execution chains exist in the same codebase, serve different purposes, and are explicitly not UMR-001:

| Chain | Formal Name | Purpose |
|---|---|---|
| `FOUNDATION.ManufacturingRuntime` | **UMR-001 — Universal Manufacturing Runtime** | Executes UMC-001 for any Factory Pack |
| `MANUFACTURING.ManufacturingEngine` | Release Engine | Generates release artifacts (`database.sql`, `schema.json`, `openapi.json`, `workflow.json`, `release.json`) from a manifest |
| `MANUFACTURING.ManufacturingService` | Factory Generator | Scaffolds a build pack's file structure for a registered module |
| `RUNTIME.FactoryRuntime` | Project Generator | Scaffolds a templated project (e.g. a FastAPI application) from a production plan |

No code path may route UMC-001 execution through any of these three. No second Runtime may be created without a new Chief Architect decision, per `MWO-LTSA-049`'s own Migration Strategy.

---

## 2. Responsibilities

UMR-001 is responsible for, and only for:

1. Accepting a manufacturing request and turning it into a validated `ManufacturingOrder` (§4).
2. Constructing and propagating a `ManufacturingContext` to every station in the pipeline (§5).
3. Validating the request at both the order level and the definition level before any manufacturing is attempted (§6).
4. Exposing Identity Resolution and Relationship Resolution as pluggable capabilities, without performing either itself (§7, §8).
5. Executing a `ManufacturingPipeline` of stations in sequence, producing canonical objects.
6. Publishing events — both runtime-level (`BUILD_STARTED`/`BUILD_COMPLETED`) and per-station (`STATION_COMPLETED`) — to a shared event bus (§9).
7. Producing a runtime-level result and a durable build report (§10).
8. Treating a `FactoryPack`, when supplied, as a first-class citizen of the same rigor as a `ManufacturingOrder` (§6).

UMR-001 is explicitly **not** responsible for: concrete identity/relationship matching logic (a Factory Pack's own responsibility); generating release artifacts, build-pack scaffolds, or project scaffolds (Release Engine/Factory Generator/Project Generator's own responsibilities); or manufacturing any specific canonical business object (a Factory Pack's own station's responsibility).

---

## 3. Lifecycle

```
ManufacturingRuntime.run(definition: dict, workspace_root)
  │
  ├─ 1. BuildWorkspace(workspace_root).create()
  │
  ├─ 2. Construct ManufacturingOrder(order_id=build_id, requested_product=product,
  │       customer_request=<supplied or synthesized>)
  │    → ManufacturingOrderValidator().validate(order)   [raises on malformed input]
  │
  ├─ 3. If a FactoryPack was supplied: factory_pack.validate()  [raises on malformed pack]
  │
  ├─ 4. Construct ManufacturingContext(build_id, product, version, manifest=definition,
  │       metadata={identity_resolver, relationship_resolver, factory_pack})
  │
  ├─ 5. event_bus.publish(BUILD_STARTED)
  │
  ├─ 6. FactoryOrchestrator.manufacture(definition, context=context)
  │      ├─ FactoryValidator.validate(definition)         [definition-level: product/version/factory present]
  │      │    └─ if INVALID → return MANUFACTURING_REJECTED, skip remaining steps
  │      ├─ FactoryCompiler.compile(definition, context=context)
  │      │      └─ ManufacturingPipeline.run(payload={product, definition, status, context})
  │      │             for each station:
  │      │               result = station.run(result)
  │      │               station_events.append(STATION_COMPLETED event)
  │      └─ FactoryFreeze.freeze(product, version, result=compiled)
  │
  ├─ 7. event_bus.publish(BUILD_COMPLETED)
  │
  ├─ 8. BuildReport.write_all({build.json, workspace.json, manufacturing.json, events.json})
  │
  └─ 9. return RuntimeResult (§10)
```

Every step above executes unconditionally except step 6's internal validation branch and steps 2–3's validation raises, which halt the lifecycle immediately (fail-fast, consistent with `ManufacturingOrder`'s and `FactoryPack`'s own pre-existing `validate()` contracts).

---

## 4. Manufacturing Request

UMR-001 does not define its own request shape. It reuses `AI5R-SDK/FACTORY/ORDERS.ManufacturingOrder` (`order_id`, `requested_product`, `customer_request`, `status`, `metadata`, `created_at`) and `AI5R-SDK/FACTORY/VALIDATION.ManufacturingOrderValidator` unchanged.

A caller supplies a `definition: dict` (containing at minimum `build_id` and `product`; `version`/`factory` are required only for the definition to pass `FactoryValidator`, a separate, coarser check at step 6). UMR-001 derives the order from this dict: `order_id = definition["build_id"]`, `requested_product = definition["product"]`, `customer_request` is taken from `definition["customer_request"]` if present, or synthesized (`"Manufacture {product} (build {build_id})"`) if absent — ensuring the order always validates on this field regardless of caller completeness.

The order's `status` progresses `CREATED → VALIDATED` within `run()`; UMR-001 does not itself progress it further (`RESOLVED`/`RUNNING`/`COMPLETED`/`FAILED` remain available for a Factory Pack's own use, e.g. via `ProductResolver`, which UMR-001 does not currently call — see §11).

---

## 5. Manufacturing Context

UMR-001 constructs one `AI5R-SDK/FACTORY/FOUNDATION.ManufacturingContext` per `run()` call: `build_id`, `product`, `version` (from the definition, defaulting to an empty string if absent), `manifest=definition` (the full original request, preserved), and `metadata` carrying three keys: `identity_resolver`, `relationship_resolver`, `factory_pack` (each `None` unless supplied to the constructor).

This context is passed to `FactoryOrchestrator.manufacture(definition, context=context)` → `FactoryCompiler.compile(definition, context=context)`, which places it into the pipeline payload under the `"context"` key. Any station in the pipeline (a plain object with a `.run(payload: dict) -> dict` method) may read `payload.get("context")` to access build metadata, the resolvers, and the factory pack — this is the mechanism by which Stage 2 of UMC-001 reaches every station, verified by direct test (`ContextReadingStation`, `MWO-LTSA-049`).

`context` is optional at every layer (`compile()`, `manufacture()` both default it to `None`); a caller that never supplies one reproduces the exact pre-`MWO-LTSA-049` payload shape.

---

## 6. Validation

Two distinct validation layers, kept separate — matching the Engineering Standard's own general Validation Standard distinction (Structural vs. Runtime), applied here at the request level:

1. **Order/Pack-level validation** (step 2–3 in §3): `ManufacturingOrder.validate()` (order_id/requested_product/customer_request non-empty, status in the allowed set) and, if supplied, `FactoryPack.validate()` (pack_code/pack_name/product_type/capabilities/recipe_path non-empty). Both raise (`ValueError`) immediately on failure, before any workspace, event, or manufacturing work begins.
2. **Definition-level validation** (step 6a): `FactoryValidator.validate(definition)` checks `product`/`version`/`factory` are present in the raw definition dict. Failure here does not raise — it returns a structured `MANUFACTURING_REJECTED` result, allowing the caller to inspect `validation["errors"]` without an exception.

A caller should expect: a malformed order/pack is a programming error (exception); a malformed manufacturing definition is an expected, structured rejection (no exception).

---

## 7. Identity Resolution

UMC-001 Stage 4. Interface only — **no concrete matching or deduplication logic exists in the platform**, by explicit Chief Architect directive, and this specification does not change that.

`AI5R-SDK/FACTORY/RESOLUTION.IdentityResolver` (`ABC`) declares one abstract method: `resolve(object_type: str, candidate_key: dict, context: ManufacturingContext) -> IdentityResolution`, where `IdentityResolution` is `(matched: bool, canonical_id: str | None, confidence: float | None)`.

UMR-001's role is limited to **making an `IdentityResolver` instance reachable**, via `context.metadata["identity_resolver"]`, to whichever station needs it. UMR-001 itself never calls `.resolve()` — it has no per-object natural key to resolve against at the runtime-orchestration level (it operates on a whole build/manufacturing request, not a single candidate canonical object). A Factory Pack's own station, which does know the natural key of the specific object it is manufacturing (e.g. a Pump's `tag_number`), is the correct caller of `.resolve()`. LTSA-BRAIN is expected to be the first Factory Pack to write such a station; that station does not yet exist.

---

## 8. Relationship Resolution

UMC-001 Stage 5. Same treatment as Identity Resolution (§7): `AI5R-SDK/FACTORY/RESOLUTION.RelationshipResolver` (`ABC`), one abstract method `resolve(object_type: str, candidate_relationships: dict, context: ManufacturingContext) -> RelationshipResolution`, where `RelationshipResolution` is `(resolved: dict[str, str], unresolved: list[str])`. Reachable via `context.metadata["relationship_resolver"]`, never invoked by UMR-001 itself, for the same reason: relationship resolution requires knowledge of a specific object's cross-references, which belongs to the manufacturing station, not the generic runtime.

---

## 9. Event Publication

UMC-001 Stage 7. Two levels, both using `AI5R-SDK/FACTORY/FOUNDATION.ManufacturingEvent` (`event_type`, `station`, `build_id`, `product`, `timestamp`, `payload`) and `ManufacturingEventBus` (`publish`/`all`/`clear`):

1. **Runtime-level events**, published directly by `ManufacturingRuntime.run()`: exactly one `BUILD_STARTED` and one `BUILD_COMPLETED` per `run()` call, to `self.event_bus` (constructed internally if not supplied). These are the only events counted in the runtime's own returned `events` list and written to `events.json`.
2. **Station-level events**, published by `ManufacturingPipeline.run()`: one `STATION_COMPLETED` event per station executed, collected into a separate `station_events` list returned as part of the pipeline's own result (nested under `manufacturing.compiled.pipeline.station_events` in the runtime's overall result) — additive, and deliberately **not** merged into the runtime-level `events` count, to avoid changing that count's pre-existing, tested meaning.

**Caution for implementers:** `AI5R-SDK/FACTORY/CORE.ManufacturingEvent` is a *different, incompatible* class with the same name (`event_type`, `station`, `object_id`, `created_at` — no `build_id`/`product`/`payload`), used by `CORE.BaseManufacturingStation`. UMR-001 uses exclusively the `FOUNDATION` variant throughout. Do not mix the two into the same `ManufacturingEventBus` instance. This duplication is tracked separately — see `ARCH-REVIEW-002-Canonical-ManufacturingEvent.md` — and is out of this specification's own scope to resolve.

---

## 10. Runtime Result

`ManufacturingRuntime.run()` returns:

```
{
    "status": "RUNTIME_COMPLETED",
    "workspace": <BuildWorkspace.create() result>,
    "manufacturing": <FactoryOrchestrator.manufacture() result>,
    "events": [<BUILD_STARTED>.to_dict(), <BUILD_COMPLETED>.to_dict()],
    "order_status": order.status,
    "factory_pack": factory_pack.pack_code if supplied else None,
}
```

**Known gap, disclosed and accepted as a standing WARNING, not silently implemented** (per Chief Architect directive following `MA-002`): this result is a bespoke dict, not an instance of (or wrapping) `AI5R-SDK/FACTORY/CORE.ManufacturingResult`. `MWO-LTSA-049`'s own WP-000 proposed this as a closing item; it was not completed during that MWO's implementation, was caught during that MWO's own Manufacturing Audit, and remains open by explicit instruction. A future MWO may close it; this specification describes the Runtime **as it exists today**, including this gap, not as it would exist if the gap were closed.

A durable copy of the same information (plus the full pipeline history and every station event) is written to `<workspace_root>/REPORT/{build.json,workspace.json,manufacturing.json,events.json}` via `BuildReport`.

---

## 11. FactoryPack Integration

`AI5R-SDK/FACTORY/PACKS.FactoryPack` (`pack_code`, `pack_name`, `product_type`, `capabilities`, `recipe_path`, `metadata`) is accepted as an optional constructor argument to `ManufacturingRuntime`. When supplied:

- It is validated (§6) with the same fail-fast placement as the order.
- It is threaded into `ManufacturingContext.metadata["factory_pack"]`, reachable by any station.
- It is surfaced in the runtime result (`result["factory_pack"]`).

**Not yet integrated, and out of this specification's own scope to add:** `AI5R-SDK/FACTORY/PACKS.FactoryPackLoader` (which loads a `FactoryPack` from a JSON file) is not called anywhere within UMR-001 — a caller must load the pack itself and pass the resulting object in. `AI5R-SDK/FACTORY/RESOLUTION.ProductResolver` (which resolves a `ManufacturingOrder` to a Factory Pack by product type) is also not called by UMR-001 — a caller currently supplies the `FactoryPack` directly rather than having UMR-001 resolve it from the order. Both are legitimate future integration points, not implemented here, not silently assumed to exist.

---

## Definition of Done (for this specification document)

- Describes Purpose, Responsibilities, Lifecycle, Extension Points, FactoryPack Integration, Identity Resolution, Relationship Resolution, Event Publication, and Runtime Result, each grounded in the actual implemented code, not aspirational design. **Met.**
- Does not redesign the Runtime — every statement above is a description of `MWO-LTSA-049`'s own delivered implementation. **Met.**
- No implementation file modified in producing this document. **Met.**
- The known Runtime Result gap (§10) is stated, not hidden or silently closed. **Met.**

---

Documentation only. Stopping here. Awaiting approval.
