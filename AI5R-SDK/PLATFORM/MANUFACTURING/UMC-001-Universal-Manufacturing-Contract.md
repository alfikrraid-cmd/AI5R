# UMC-001 — Universal Manufacturing Contract Specification

```
Status: CANONICAL — the reference specification for UMC-001.
Artifact ID: UMC-001
Artifact Name: Universal Manufacturing Contract
Artifact Type: Canonical Platform Contract
Owner: AI5R Platform
Consumers: All Factory Packs (LTSA, Auditor, School OS, Hospital, and future products)
Established by: `MWO-LTSA-048` (origin/research/approval record); this document (canonical specification)
Governs: the nine-stage interface every Manufacturing Pipeline must satisfy, executed by UMR-001
Known open item: Identity Resolution (§4) and Relationship Resolution (§5) are specified as
                  interfaces only — no concrete implementation exists in the platform, by
                  explicit Chief Architect directive. Kept as a disclosed gap, not silently
                  implemented.
Related: AI5R-SDK/PLATFORM/MANUFACTURING/UMR-001-Universal-Manufacturing-Runtime-Specification.md
         (the Runtime that executes this Contract); ENGINEERING/MWO/MWO-LTSA-048-Canonical-
         Manufacturing-Contract.md (this Contract's own origin, research, and Chief Architect
         approval record — not moved; remains the audit trail)
```

Documentation only. This specification describes the Contract exactly as approved by `MWO-LTSA-048` (Rev. 3, Architecture Approved by Chief Architect); it does not redesign it, and no implementation file is modified in producing it.

---

## 1. Purpose

UMC-001 is the platform-wide contract every Manufacturing Pipeline must satisfy, for any Factory Pack. **The Contract is an interface, not a table** — the set of stages and data shapes a payload must pass through, expressed in terms of existing `AI5R-SDK/FACTORY` primitives. `UMR-001-Universal-Manufacturing-Runtime-Specification.md` is the runtime that executes it.

Seven of UMC-001's nine stages already exist as real, working `AI5R-SDK/FACTORY` code and are reused as-is, not reinvented. Two — Identity Resolution and Relationship Resolution — are specified interfaces with no concrete implementation in the platform today: a genuine, confirmed, disclosed gap, not an oversight.

## 2. The Nine Stages

| # | Stage | Fulfilled By | File |
|---|---|---|---|
| 1 | Manufacturing Request | `ManufacturingOrder` (existing, reused as-is) | `AI5R-SDK/FACTORY/ORDERS/manufacturing_order.py` |
| 2 | Manufacturing Context | `ManufacturingContext` (existing, reused as-is) | `AI5R-SDK/FACTORY/FOUNDATION/manufacturing_context.py` |
| 3 | Manufacturing Validation | `BaseManufacturingStation.validate()` / `ManufacturingValidationError` (existing, reused as-is) | `AI5R-SDK/FACTORY/CORE/manufacturing_station.py`, `CORE/exceptions.py` |
| 4 | Identity Resolution | **Gap — interface only, §4** | — |
| 5 | Relationship Resolution | **Gap — interface only, §5** | — |
| 6 | Canonical Object Manufacturing | `ManufacturingObject` (existing, reused as-is) | `AI5R-SDK/FACTORY/CORE/manufacturing_object.py` |
| 7 | Event Publication | `ManufacturingEvent` + `ManufacturingEventBus` (existing, reused as-is) | `AI5R-SDK/FACTORY/CORE/manufacturing_event.py`, `FOUNDATION/manufacturing_event_bus.py` |
| 8 | Manufacturing Result | `ManufacturingResult` (existing, reused as-is) | `AI5R-SDK/FACTORY/CORE/manufacturing_result.py` |
| 9 | Manufacturing Lifecycle | `ManufacturingPipeline` / `ManufacturingRuntime` / `ManufacturingEngine` (existing, reused as-is) | `AI5R-SDK/FACTORY/FOUNDATION/manufacturing_pipeline.py`, `manufacturing_runtime.py`, `MANUFACTURING/manufacturing_engine.py` |

**Stage ordering rule:** Identity Resolution and Relationship Resolution (4–5) sit between Validation (3) and Canonical Object Manufacturing (6). A payload must be well-formed (validated) before matching is attempted, and must be resolved before a canonical object is manufactured — manufacturing a duplicate object or a dangling relationship is exactly the failure mode Stages 4–5 exist to prevent.

## 3. The Reusability Unit

`FactoryPack` (`pack_code`, `pack_name`, `product_type`, `capabilities`, `recipe_path`) and `FactoryPackContract` (`pack_id`, `version`, `product_type`, `blueprint`, `recipe`, `templates_path`, `validation_module`, `manifest_path`) — `AI5R-SDK/FACTORY/PACKS/factory_pack.py`, `PACKS/CONTRACTS/pack_contract.py` — the formal definition of "a Factory Pack," the unit that implements UMC-001.

## 4. Identity Resolution (Stage 4 — specified, not implemented)

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

No concrete matching or deduplication logic exists in the platform, by explicit Chief Architect directive. Proposed to live in `AI5R-SDK/FACTORY/RESOLUTION/`, alongside the existing `ProductResolver` — the same architectural layer, not a new one.

## 5. Relationship Resolution (Stage 5 — specified, not implemented)

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

No concrete implementation exists in the platform. Proposed to live alongside `IdentityResolver` in `AI5R-SDK/FACTORY/RESOLUTION/`.

## 6. Relationship to Workbook Acquisition's Column Mapping

`mapping_profile`/`column_mapping` (LTSA-BRAIN's own Workbook Acquisition capability) is not part of this contract. It is a Factory-Pack-specific input-normalization step that runs *before* Stage 1 (Manufacturing Request) — how a Workbook's raw columns become a well-formed `ManufacturingOrder.customer_request` payload. It is one Factory Pack's own capability, not a required contract stage.

## 7. Consumption

LTSA-BRAIN is UMC-001's first concretely satisfiable consumer, not its scope boundary: identity via `ltsa_pumps.tag_number`, relationships via `seal_type` → `seal_registry.seal_code`, canonical object = the `ltsa_pumps` row. This section states satisfiability; it does not schedule or perform that implementation.

---

## Definition of Done (for this specification document)

- Describes the nine-stage contract, the reusability unit, and both specified-not-implemented gap interfaces, each grounded in `MWO-LTSA-048`'s own Chief-Architect-approved research. **Met.**
- Does not redesign the contract — every statement is drawn from `MWO-LTSA-048` Rev. 3 as approved. **Met.**
- No implementation file modified in producing this document. **Met.**
- Both open gaps (Identity Resolution, Relationship Resolution) stated as disclosed, not hidden or silently closed. **Met.**

---

Documentation only. Stopping here. Awaiting approval.
