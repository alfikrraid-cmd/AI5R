# MWO-LTSA-048 — Canonical Manufacturing Contract

Status: WP-000 ARCHITECTURE APPROVED (Rev. 3) — awaiting separate, explicit Implementation Approval before any code is written
Type: Manufacturing Work Order (Cross-Product Manufacturing Contract — Specification Layer)
Epic: AI5R Digital Factory — Canonical Manufacturing Contract (platform-wide; LTSA-BRAIN is its first consumer, not its scope boundary)
Role: Implementation Engineer
Architecture: FROZEN — this revision reuses existing AI5R-SDK/FACTORY primitives exhaustively; it introduces no new architecture, service, or framework, per Chief Architect correction of Rev. 1
Foundation: v1.0 — LOCKED, unchanged by this MWO
Engineering Standard: v1.0 — LOCKED, unchanged by this MWO
Basis: Chief Architect's Rev. 2 correction (quoted in full in §0 below); direct read of `AI5R-SDK/FACTORY/{CORE,FOUNDATION,ORDERS,MANUFACTURING,PACKS}/*.py` — the existing, real, tested Manufacturing framework this contract formalizes rather than replaces.
Scope: **Platform-wide contract definition** (`AI5R-SDK/FACTORY`), not an LTSA-BRAIN-only artifact. LTSA-BRAIN's Workbook Acquisition family is this contract's first named consumer (§6), not its scope boundary.

---

## 0. Revision Note — Why Rev. 1 Was Rejected, Verbatim

> "The proposed contract is centered on column mapping. That is only one implementation detail inside Manufacturing. MWO-LTSA-048 must define the canonical Manufacturing Contract, not the canonical Mapping Contract. The contract must be reusable by every Factory Pack... Column Mapping is only one capability inside Manufacturing. It must not become the Manufacturing Contract itself."

Rev. 1 (superseded, not deleted — see §7) proposed `canonical_attribute_contract`, a Workbook-Acquisition-specific validation table. That was a category error: it defined one capability's implementation detail (how a spreadsheet column name maps to a database column) and mistook it for the contract every Manufacturing Pipeline must satisfy. This revision corrects that by stepping up one abstraction level, as instructed, and grounding the correction in code that already exists — not inventing a new abstraction to replace the old, narrow one.

---

## 1. Research: The Contract Already Exists, Mostly Unformalized

Per Constitution Principle 3 ("Reuse before Create... if an existing module can be extended, extend it. Do not create another one") and Principle 9 ("Factory First... never duplicate Factory logic"), this MWO's first obligation was to determine whether AI5R-SDK/FACTORY already implements the nine concerns the Chief Architect named. Direct read of every file below, not assumed from name alone:

| Chief Architect's Required Concern | Existing Implementation | File |
|---|---|---|
| Manufacturing request | `ManufacturingOrder` — `order_id`, `requested_product`, `customer_request`, `status`, lifecycle `CREATED→VALIDATED→RESOLVED→RUNNING→COMPLETED→FAILED` | `AI5R-SDK/FACTORY/ORDERS/manufacturing_order.py` |
| Manufacturing context | `ManufacturingContext` — "canonical context flowing through every manufacturing station": `build_id`, `product`, `version`, `manifest`, `generated_assets`, `validation_report`, `reports`, `frozen` | `AI5R-SDK/FACTORY/FOUNDATION/manufacturing_context.py` |
| Manufacturing validation | `BaseManufacturingStation.validate(payload)`, raising `ManufacturingValidationError` | `AI5R-SDK/FACTORY/CORE/manufacturing_station.py`, `CORE/exceptions.py` |
| Canonical object manufacturing | `ManufacturingObject(object_type, object_id, payload, metadata, created_at)` | `AI5R-SDK/FACTORY/CORE/manufacturing_object.py` |
| Event publication | `ManufacturingEvent(event_type, station, object_id, created_at)` + `ManufacturingEventBus` (publish/all/clear) | `AI5R-SDK/FACTORY/CORE/manufacturing_event.py`, `FOUNDATION/manufacturing_event_bus.py` |
| Manufacturing result | `ManufacturingResult(status, station, manufactured_object, object_id, manufactured_at, events)` | `AI5R-SDK/FACTORY/CORE/manufacturing_result.py` |
| Manufacturing lifecycle | `ManufacturingPipeline` (sequential station execution + history), `ManufacturingRuntime` (full build flow: workspace → orchestrator → event bus → report), `ManufacturingEngine` (dependency-graph-ordered station execution via `StationDiscovery`/`StationRegistry`/`DependencyGraph`/`TopologicalSorter`) | `AI5R-SDK/FACTORY/FOUNDATION/manufacturing_pipeline.py`, `manufacturing_runtime.py`, `MANUFACTURING/manufacturing_engine.py` |
| (the reusability unit itself) | `FactoryPack(pack_code, pack_name, product_type, capabilities, recipe_path)` and `FactoryPackContract` (`pack_id`, `version`, `product_type`, `blueprint`, `recipe`, `templates_path`, `validation_module`, `manifest_path`) — the formal definition of "a Factory Pack" the Chief Architect's own language refers to | `AI5R-SDK/FACTORY/PACKS/factory_pack.py`, `PACKS/CONTRACTS/pack_contract.py` |
| **Identity resolution** | **Not found.** `ManufacturingID.generate()` (`CORE/manufacturing_id.py`) only *mints new* identity (a UUID) — it never resolves whether an incoming payload already corresponds to an existing manufactured object. `ProductResolver` (`RESOLUTION/product_resolver.py`) resolves which Factory Pack answers an order, not object identity. No file, class, or function anywhere in `AI5R-SDK` performs identity matching/deduplication. | — (gap) |
| **Relationship resolution** | **Not found.** `DependencyResolver` (`RESOLVERS/dependency_resolver.py`) resolves *entity dependency graphs* for build sequencing (which generator runs before which), not business relationships between manufactured objects (e.g., "this row's `seal_type` text names an existing `seal_registry.seal_code`"). No file anywhere performs this. | — (gap) |

**Finding, stated plainly: seven of the nine required concerns already exist as real, working AI5R-SDK/FACTORY code and must be reused, not reinvented. Two — Identity Resolution and Relationship Resolution — are genuine, confirmed gaps in the platform today.** This MWO's job is to (a) formally name and cite the seven existing pieces as the Canonical Manufacturing Contract's fulfilled obligations, and (b) specify — not implement — the interface shape for the two missing pieces, so that any future Factory Pack (LTSA, Auditor, School OS, Hospital) has a single, complete contract to implement against.

**Incidental finding, explicitly not pursued further (out of this mission's scope, per instruction "do not expand scope"):** `MANUFACTURING/manufacturing_engine.py`'s `self.targets` dict (`sql→database.sql`, `schema→schema.json`, `openapi→openapi.json`, `workflow→workflow.json`, `release→release.json`) is very likely the actual origin of `PRODUCTS/LTSA-BRAIN/RELEASE/workflow.json` and `release.json`, whose origin `RCA-001`/`RCA-002` could not pin down beyond "unconfirmed, likely manual." This is noted here as a cross-reference for whoever next revisits `TD-001`, not investigated further in this document.

---

## 1.5 Artifact Produced

| Field | Value |
|---|---|
| **Artifact ID** | UMC-001 |
| **Artifact Name** | Universal Manufacturing Contract |
| **Artifact Type** | Canonical Platform Contract |
| **Owner** | AI5R Platform |
| **Consumers** | All Factory Packs (LTSA, Auditor, School OS, Hospital, and future products) |

UMC-001 is this document's formal deliverable: the nine-stage interface specified in §2, backed by the seven existing `AI5R-SDK/FACTORY` primitives cited in §1 and the two proposed platform-interface stages in §3. It is a specification artifact, not a code artifact — no file under `AI5R-SDK/FACTORY` is created or modified in producing UMC-001; implementing it (as concrete `IdentityResolver`/`RelationshipResolver` code, and as LTSA-BRAIN's own first consumption of it) remains separately scoped, future work per §3 and §6.

## 2. WP-000 — The Canonical Manufacturing Contract, Defined

**The Contract is an interface, not a table.** Consistent with the fact that seven of nine obligations are already Python dataclasses/classes, not database rows, the Canonical Manufacturing Contract is specified here as **the set of stages and data shapes every Manufacturing Pipeline must pass a payload through**, expressed in terms of the existing `AI5R-SDK/FACTORY` primitives plus the two new ones this MWO proposes. No new database table is proposed for the contract itself — a correction from Rev. 1, which wrongly reached for a table where an interface was needed.

**The nine required stages, in pipeline order:**

1. **Manufacturing Request** — `ManufacturingOrder` (existing, reused as-is). A Factory Pack receives a request as an order: `order_id`, `requested_product`, `customer_request`.
2. **Manufacturing Context** — `ManufacturingContext` (existing, reused as-is). The order's context (`build_id`, `product`, `version`, `manifest`) flows through every subsequent stage.
3. **Manufacturing Validation** — `BaseManufacturingStation.validate()` / `ManufacturingValidationError` (existing, reused as-is). Every station validates its own required input before proceeding.
4. **Identity Resolution** — **gap, specified below (§3), not implemented.**
5. **Relationship Resolution** — **gap, specified below (§3), not implemented.**
6. **Canonical Object Manufacturing** — `ManufacturingObject` (existing, reused as-is). The actual canonical business object, once identity and relationships are resolved.
7. **Event Publication** — `ManufacturingEvent` + `ManufacturingEventBus` (existing, reused as-is).
8. **Manufacturing Result** — `ManufacturingResult` (existing, reused as-is).
9. **Manufacturing Lifecycle** — `ManufacturingPipeline` / `ManufacturingRuntime` / `ManufacturingEngine` (existing, reused as-is) — the orchestration that runs stages 1–8 in order for any given Factory Pack.

**Design decision 1 — Identity Resolution and Relationship Resolution slot in between Validation and Canonical Object Manufacturing, not before or after.** Basis: a payload must first pass validation (stage 3) to even be well-formed enough to attempt matching; it must be resolved (stages 4–5) *before* a canonical object is manufactured (stage 6), because manufacturing a duplicate object or a dangling relationship is exactly the failure mode identity/relationship resolution exists to prevent. This ordering is the one substantive new architectural fact this MWO introduces — flagged explicitly, not buried, since everything else in this contract is a citation of existing code, not a new decision.

**Design decision 2 — this MWO specifies but does not implement stages 4–5.** Basis: explicit instruction ("Revise WP-000. No implementation. Wait for approval") plus the Constitution's MWO Authority rule (never optimize beyond requested scope). What follows in §3 is a proposed interface shape, offered for approval, not committed code.

---

## 3. Proposed Specification for the Two Missing Stages (not implemented — for approval only)

### `IdentityResolver` (new, proposed)

```
class IdentityResolver:
    def resolve(self, object_type: str, candidate_key: dict, context: ManufacturingContext) -> IdentityResolution:
        """
        Given a candidate natural key (e.g. {"tag_number": "P-101"} for a Pump,
        {"seal_code": "SC-9"} for a Mechanical Seal), determine whether a
        canonical object of this object_type already exists.
        Returns IdentityResolution(matched: bool, canonical_id: str | None, confidence: float | None).
        Never mutates anything -- read-only lookup.
        """
```

Grounded in evidence already present in this product: `ltsa_pumps.tag_number` (`UNIQUE`), `seal_registry.seal_code` (PK), `customer_registry`'s own code column — every existing canonical table in `PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql` already has exactly one natural-key column suited to this role; this proposal generalizes that existing pattern into a named contract stage, it does not invent a new keying scheme.

### `RelationshipResolver` (new, proposed)

```
class RelationshipResolver:
    def resolve(self, object_type: str, candidate_relationships: dict, context: ManufacturingContext) -> RelationshipResolution:
        """
        Given candidate relationship references by natural key (e.g. a Pump
        Compatibility row's {"seal_type": "Type 21"} needing to resolve to an
        existing seal_registry row), resolve each to a canonical foreign key
        or report it unresolvable.
        Returns RelationshipResolution(resolved: dict[str, str], unresolved: list[str]).
        """
```

Grounded in evidence already present in this product: `seal_pump_compatibility`/`seal_interchange_compatibility` (MWO-030) already join two canonical tables by code; `mapping_profile`/`column_mapping` (MWO-040C) already carry a `canonical_attribute` concept for exactly this kind of cross-reference, informally. This proposal is the generalized version of what those tables already do ad hoc, per object type — it does not propose a new relationship model, only a named, reusable resolution stage.

Both classes are proposed to live in `AI5R-SDK/FACTORY/RESOLUTION/`, alongside the existing `ProductResolver` — the same directory, same architectural layer, not a new one.

---

## 4. Relationship to Rev. 1's Column Mapping Concern

Rev. 1 was not wrong that Workbook Acquisition needs *something* like `column_mapping.canonical_attribute` validated — it was wrong that this validation *is* the Manufacturing Contract. Correctly placed: `mapping_profile`/`column_mapping` (MWO-040C) are a **Workbook-Acquisition-specific input-normalization capability**, sitting *before* this contract's stage 1 (Manufacturing Request) — they are how a Workbook's raw columns become a well-formed `ManufacturingOrder.customer_request` payload in the first place. They are one Factory Pack's (LTSA's) own capability, not a required stage of the contract every Factory Pack must implement. This MWO does not alter `mapping_profile`/`column_mapping` in any way.

---

## 5. MWO-Number-vs-Scope Question — Resolved by Chief Architect

Rev. 2 flagged, without deciding, that this contract's platform-wide scope reads like ADR material under `ADR-000`'s own governance model, despite sitting in an LTSA-prefixed MWO. **Resolved:** the Chief Architect has confirmed the identifier `MWO-LTSA-048` is retained regardless of the contract's cross-product scope. This document stands as drafted, under this number, as UMC-001's origin record.

---

## 6. LTSA-BRAIN as First Consumer (not this MWO's own scope to implement)

Once this contract is approved, LTSA-BRAIN's own future manufacturing MWOs (per `MWO-LTSA-040C` item 6's deferred promise) would implement it per canonical business object: a Pump-manufacturing MWO would resolve identity via `ltsa_pumps.tag_number`, relationships via `seal_type`→`seal_registry.seal_code`, then manufacture the canonical `ltsa_pumps` row. **None of that implementation is proposed or performed by this document.** This section exists only to show the contract is concretely satisfiable by LTSA-BRAIN's own already-built tables, not to schedule that work.

---

## Deliverables (this document only, Rev. 2)

- This WP-000 document — the Canonical Manufacturing Contract's specification, citing seven existing `AI5R-SDK/FACTORY` primitives and proposing two new ones (interface only).
- No code, schema, or build pack. No `AI5R-SDK/FACTORY` file modified. No `PRODUCTS/LTSA-BRAIN` file modified.

## Acceptance Criteria (for this WP-000 document itself)

- Every "existing" claim in §1's table is backed by a direct file citation, not assumed.
- The two gaps (Identity Resolution, Relationship Resolution) are specified as interfaces only, not implemented.
- Rev. 1's column-mapping-centered error is explicitly named and corrected, not silently dropped (Evidence Standard: "a finding that later proves wrong must be disclosed as a finding that proved wrong").
- UMC-001 is formally named as this MWO's Artifact Produced (§1.5).
- The MWO-number-vs-cross-product-scope tension was surfaced (Rev. 2), then resolved by explicit Chief Architect decision (§5, Rev. 3) — not decided unilaterally.

## Definition of Done

- WP-000 Rev. 3 complete. **Architecture Approved** by Chief Architect.
- No implementation performed.
- Nothing committed or pushed.
- Implementation of UMC-001 (concrete `IdentityResolver`/`RelationshipResolver` code, and LTSA-BRAIN's own first consumption of the contract) awaits a separate, explicit Implementation Approval.

---

## 7. Revision History

- **Rev. 1** (superseded): proposed `canonical_attribute_contract`, a Workbook-Acquisition-specific mapping-validation table — rejected by Chief Architect for conflating one capability (Column Mapping) with the Manufacturing Contract itself. Not separately archived; its content and the rejection are summarized in §0 and §4.
- **Rev. 2**: stepped up one abstraction level per Chief Architect's correction. Researched and cited seven existing `AI5R-SDK/FACTORY` primitives; specified two platform-interface gaps (Identity Resolution, Relationship Resolution); surfaced, without deciding, the MWO-number-vs-cross-product-scope question.
- **Rev. 3** (this version): Chief Architect approved Rev. 2's direction; added the Artifact Produced section naming the deliverable **UMC-001 — Universal Manufacturing Contract** (§1.5); resolved the MWO-number question — `MWO-LTSA-048` retained (§5). **Status: WP-000 Architecture Approved.**

This document revises in place (same filename), per this session's established convention — see `MWO-LTSA-040A` through `040E`'s own "revisions incorporated in place" precedent, Engineering Standard §9.

---

Architecture Approved. Stopping here. No implementation performed. Awaiting separate, explicit Implementation Approval.
