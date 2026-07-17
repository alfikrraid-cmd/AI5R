# ARCH-REVIEW-002 — Canonical ManufacturingEvent

Status: **DEFERRED**
Target: **After LTSA v1.0**
Raised by: `MWO-LTSA-049` (discovered during implementation, 2026-07-15)
Category: Architecture Review Required — explicitly **not** ordinary Technical Debt, per Chief Architect directive.

---

## Why This Is Not Ordinary Technical Debt

Per the Constitution's Canonical Rule (`CONSTITUTION/13_ENGINEERING_EXECUTION_PROTOCOL.md`: *"There must be exactly ONE canonical implementation... If canonical ambiguity appears: STOP. Report. Wait. Do not decide"*), this finding is a live violation of that rule inside the platform's own Manufacturing framework — the same framework `UMC-001`/`UMR-001` now formally govern. A duplicate-class naming collision at this level is an architecture-integrity question (which of two classes is *the* canonical `ManufacturingEvent`, and what happens to every existing consumer of the other one), not a scoped, single-file cleanup item a routine technical-debt entry adequately represents. It is tracked here, as its own Architecture Review record, so it receives the review weight the Canonical Rule requires before any resolution — deciding it inside an ordinary debt-paydown pass would itself violate "Do not decide."

---

## The Finding

Two classes, both named `ManufacturingEvent`, exist in `AI5R-SDK/FACTORY`, structurally incompatible:

| | `AI5R-SDK/FACTORY/CORE/manufacturing_event.py` | `AI5R-SDK/FACTORY/FOUNDATION/manufacturing_event.py` |
|---|---|---|
| Fields | `event_type`, `station`, `object_id`, `created_at` | `event_type`, `station`, `build_id`, `product`, `timestamp` (auto), `payload` |
| Used by | `CORE.BaseManufacturingStation` (via `.manufacture()`) | `FOUNDATION.ManufacturingRuntime`, `FOUNDATION.ManufacturingPipeline` (as of `MWO-LTSA-049`), i.e. **UMR-001 itself** |
| Currently published to `ManufacturingEventBus`? | No — never observed publishing to any bus | Yes — the only variant UMR-001 publishes |

**Current state (verified, not assumed):** the two variants occupy entirely separate code paths that do not currently interact. `CORE.BaseManufacturingStation.manufacture()` returns its event embedded only in its own `ManufacturingResult.events` list; it is never published to `FOUNDATION.ManufacturingEventBus`. No file in the repository publishes both variants to the same bus. This is why the finding did not block `MWO-LTSA-049`'s own implementation — UMR-001 was built using exclusively the `FOUNDATION` variant, consistent with `ManufacturingRuntime`'s own pre-existing convention, deepening nothing.

**Why it still matters:** `CORE.BaseManufacturingStation` is the base class `AI5R-SDK/FACTORY/STATIONS/*` (the cognitive Reality→Warehouse→Experience→Memory→Knowledge→Capability→Context→Reasoning→Decision→Recommendation→Action pipeline) already extends, and is cited in `UNIVERSAL_MANUFACTURING_CONTRACT` (`CORE/universal_manufacturing_contract.py`) as the fulfiller of UMC-001 Stage 3 (Manufacturing Validation). If a future Factory Pack station built on `BaseManufacturingStation` is ever run inside a UMR-001 pipeline and its events need to reach the shared event bus (closing the same kind of wiring gap `MWO-LTSA-049` closed for plain `.run()`-style stations), the two incompatible `ManufacturingEvent` shapes will collide the moment someone tries to publish both to one bus.

---

## Options (not decided here)

1. **Standardize on the `FOUNDATION` variant** (`build_id`/`product`/`payload`) as canonical; migrate `CORE.BaseManufacturingStation` to use it, deprecating `CORE.ManufacturingEvent`.
2. **Standardize on the `CORE` variant** (`object_id`/`created_at`) as canonical; migrate `FOUNDATION.ManufacturingRuntime`/`ManufacturingPipeline` to use it, deprecating `FOUNDATION.ManufacturingEvent`.
3. **Keep both, formally distinguished by rename** (e.g. `CORE.StationEvent` vs. `FOUNDATION.BuildEvent`), accepting that "an event" means two different things at two different layers of the platform, each documented and never conflated.

Each option has real consequences for already-tested code (`CORE/TESTS/test_manufacturing_framework_core.py`, `FOUNDATION/TESTS/test_manufacturing_event.py`, and every `STATIONS/*` test) and for `UNIVERSAL_MANUFACTURING_CONTRACT`'s own citations. None is selected by this document.

---

## Deferral Rationale

Per Chief Architect directive: this review is explicitly deferred until **after LTSA v1.0** is complete. LTSA-BRAIN's own consumption of UMR-001 (its future Identity/Relationship Resolution station work) does not require either `ManufacturingEvent` variant to change, and forcing this decision now would risk destabilizing already-tested, already-shipping platform code (`STATIONS/*`, the cognitive pipeline) for a conflict that is not yet actively causing harm. Deferring is a decision about sequencing, not a decision to ignore — this document exists precisely so it is not forgotten.

---

## Cross-References

- `TECHNICAL_DEBT.md` — `TD-006` now points here rather than carrying its own full description, avoiding two sources of truth for the same finding.
- `ENGINEERING/MWO/MWO-LTSA-049-Universal-Manufacturing-Runtime.md`, `MWO-LTSA-049-Completion-Report.md`, `EA-003-MWO-LTSA-049-Engineering-Audit.md` — where this was first discovered and disclosed.
- `AI5R-SDK/PLATFORM/MANUFACTURING/UMR-001-Universal-Manufacturing-Runtime-Specification.md` §9 — documents UMR-001's own exclusive use of the `FOUNDATION` variant and flags this same caution to future implementers. (Relocated from `ENGINEERING/MWO/` under the Platform Artifact placement rule established in `MWO-PLATFORM-001-AI5R-Command-Language.md`.)

---

Documentation only. No source code modified in producing this record. Status remains **DEFERRED** until explicitly reopened by the Chief Architect, targeted for after LTSA v1.0.
