# MWO-LTSA-053 — Installation Factory Pack — WP-000 Research

Status: **WP-000 APPROVED — Research PASS, Architecture PASS.** Chief Architect confirmations: (1) No canonical Installation object currently exists — **do not invent one**; any future Installation object must be derived from existing LTSA implementation, not speculative design. (2) The `AI5R-SDK/MANUFACTURING`/`AI5R-SDK/FACTORY` namespace collision (§5, §7 Open Question 3) is **confirmed real, not resolved within this MWO** — recorded as a future Architecture Review candidate (`TECHNICAL_DEBT.md` `TD-009`), not elevated to its own review yet. This MWO is paused here; LTSA Manufacturing continues elsewhere.
Type: Manufacturing Work Order (Research)
Role: Implementation Engineer
Architecture: FROZEN — nothing proposed here changes it
Basis: Direct read of `PRODUCTS/LTSA-BRAIN/{product.manifest.json,DATABASE/CANONICAL_SCHEMA.sql}`; `AI5R-SDK/FACTORY/{CORE/universal_manufacturing_contract.py,FOUNDATION/manufacturing_runtime.py,PACKS/{factory_pack.py,factory_pack_loader.py,CONTRACTS/pack_contract.py},RESOLUTION/{identity_resolver.py,relationship_resolver.py}}`; `AI5R-SDK/MANUFACTURING/{__init__.py,RECIPES/manufacturing_recipe.py,ORDERS/manufacturing_order.py,FACTORY/digital_factory.py,company_recipe_registration.py}`; `ENGINEERING/MWO/MWO-LTSA-050-Pump-Factory-Pack-Research.md` (closest sibling precedent, same research shape).
Scope: Research only, per explicit instruction. No `AI5R-SDK/FACTORY`, `AI5R-SDK/MANUFACTURING`, `PRODUCTS/LTSA-BRAIN`, or Runtime file is modified in producing this document.

---

## Executive Summary

**Significant finding, disclosed first, per this session's own established practice:** a repository-wide search confirms **no canonical Installation object exists anywhere in the repository today** — not in `product.manifest.json`'s module list, not in `CANONICAL_SCHEMA.sql`, not as a `REGISTRIES/*.json` file, not as any `BUILD-PACKS/BP-INSTALLATION*`. The only occurrence of the word is `seal_engineering_document.document_type`'s `INSTALLATION_GUIDE` enum value (a document classification, not a business object). This MWO is therefore genuinely originative for the canonical object itself — unlike `MWO-LTSA-050` (Pump), which found a real, already-implemented `ltsa_pumps` table to ground its research in.

**Second significant finding:** researching "Manufacturing Recipe candidates" surfaced a **third, previously-undocumented manufacturing meta-model** in this repository: `AI5R-SDK/MANUFACTURING/{RECIPES,ORDERS,OBJECTS,STATIONS,LINES,BOM,FACTORY}` defines a real, working `ManufacturingRecipe` class — but it belongs to an entirely separate system (`DigitalFactory`/`ProductionLine`/`DigitalBillOfMaterials`, consumed today only by `company_recipe_registration.py`/`department_recipe_registration.py`/`role_recipe_registration.py` to manufacture **organizational** artifacts — Company, Department, Role) whose own `ManufacturingOrder`, `ManufacturingObject`, and `ManufacturingStation` classes **share names with, but are structurally different from and unrelated to**, `AI5R-SDK/FACTORY`'s own same-named classes that UMC-001/UMR-001 govern. This is the same class of finding as `ARCH-REVIEW-002`'s `ManufacturingEvent` duplication, now confirmed to extend to at least three more class names, in a different subsystem. Flagged in full at §5 and §7; not resolved here.

---

## 1. Canonical Installation Object (does not yet exist — candidate shape only)

No table, schema, or module named "Installation" exists. The closest analogous, already-canonical precedents in `CANONICAL_SCHEMA.sql` are:

- `public.asset_registry` (`asset_code` TEXT PK, `asset_name`, `asset_type`, `area`, `manufacturer`, `model`, `status`) — a physical-asset registry.
- `public.work_order` (`work_order_code` TEXT PK, `customer_code`, `asset_code`/`asset_type` — a **polymorphic-by-convention pair, explicitly documented as not a real FK**, per `product.manifest.json`'s own `work_order` entry — `description`, `priority`, `status`, `assigned_to`).
- `public.seal_pump_compatibility` (composite PK `seal_code` + `pump_tag_number`, both real FKs to `seal_registry`/`ltsa_pumps`) — the established pattern for a real, FK-enforced relationship table between two canonical objects, as opposed to `work_order`'s looser polymorphic convention.
- `public.ltsa_pumps` (`tag_number` VARCHAR UNIQUE NOT NULL as natural key, `seal_type` free text — the exact field `MWO-LTSA-048`/`UMC-001` name as the Relationship Resolution target).

**Inferred candidate shape (not decided — grounded in the above precedents only):** an "Installation" in this domain most plausibly records **the fact that a specific Seal (or Pump) was installed at a specific Asset/site on a specific date** — distinct from `seal_pump_compatibility` (which records a compatibility *rule* — "this seal type may be used with this pump type" — not an installation *event*). Candidate fields, by analogy: an identity field (see §2), FKs to `seal_registry.seal_code` and `ltsa_pumps.tag_number` (following `seal_pump_compatibility`'s real-FK pattern, not `work_order`'s polymorphic convention), an `asset_code` reference (following `work_order`'s polymorphic convention, since Installation may need to reference `asset_registry` OR other physical-location concepts not yet unified in this schema), `installed_at`/`installed_by`, and `status`. **This is inference for research purposes, not a schema proposal** — no table is created here.

## 2. Identity

No natural key exists today because no table exists. By analogy with every other canonical object in this schema (`ltsa_pumps.tag_number`, `seal_registry.seal_code`, `asset_registry.asset_code`, `knowledge_source_registry.knowledge_source_id`), an Installation would need its own natural or synthetic identity — candidates: a synthetic `installation_id` (following the acquisition-family tables' UUID-PK convention, e.g. `pdf_document_id`, `engineering_media_id`), or a composite natural key of `(pump_tag_number, seal_code, installed_at)` (following `seal_pump_compatibility`'s composite-PK convention, but with a timestamp component since the same Pump+Seal pair could plausibly be installed, removed, and reinstalled over time — something `seal_pump_compatibility`'s own compatibility-rule semantics never needed to represent). **Not decided here** — this is squarely a Stage 1 (Manufacturing Request/Identity Resolution) design question for a future WP-001, per UMC-001's own stage ordering.

## 3. Relationships

Per `UMC-001`'s Stage 5 (Relationship Resolution), an Installation's relationships would need to resolve against:
- `seal_registry.seal_code` (real FK precedent: `seal_pump_compatibility`, `seal_stock`, `seal_interchange_compatibility`, `seal_engineering_document`).
- `ltsa_pumps.tag_number` (real FK precedent: `seal_pump_compatibility`).
- `asset_registry.asset_code` — **no existing table has a real FK to this column**; every current reference (`work_order`, `maintenance_history`) uses the same polymorphic-by-convention `(asset_code, asset_type)` pair, not a database-enforced FK. An Installation Factory Pack's Relationship Resolution would need to either adopt this same convention (consistent with existing practice) or introduce a real FK (a schema-design decision, not made here).
- Possibly `knowledge_source_registry` (if an Installation is documented by an Engineering Document/PDF, per the acquisition family's own precedent) — speculative, not evidenced by any existing pattern specific to Installation.

**Concrete precedent for the Relationship Resolution interface itself:** `AI5R-SDK/FACTORY/RESOLUTION/relationship_resolver.py`'s `RelationshipResolver` (ABC only, no concrete logic anywhere in the platform, confirmed) is the exact extension point `UMC-001`/`UMR-001` already define for this — an Installation Factory Pack would implement it, not invent a new mechanism.

## 4. Factory Pack Boundary

Following `MWO-LTSA-050` §"Factory Pack Boundaries" exactly, using the same evidence base (`FactoryPack` at `AI5R-SDK/FACTORY/PACKS/factory_pack.py`: `pack_code`, `pack_name`, `product_type`, `capabilities: list[str]`, `recipe_path`, `metadata`):

| Owns (new, Installation-specific) | Reuses unchanged |
|---|---|
| A concrete `IdentityResolver` for whatever identity §2 settles on | `UMR-001` runtime itself — no Runtime file touched |
| A concrete `RelationshipResolver` matching against `seal_registry`/`ltsa_pumps`/`asset_registry` per §3 | `UMC-001` contract itself — no redesign |
| A manufacturing station (or sequence) writing a new, not-yet-existing canonical Installation table | `ltsa_pumps`, `seal_registry`, `asset_registry` — all reused as relationship targets, untouched |
| The Installation table's own schema (does not exist yet — this MWO's own future WP-001+ concern) | `ManufacturingOrder`/`ManufacturingContext`/`ManufacturingEvent`/`ManufacturingObject`/`ManufacturingPipeline` (the `FACTORY` variants) — reused as-is |
| A `FactoryPack` definition (`pack_code`, `product_type="installation"` or similar) | The Acquisition Layer, if an Installation is ever sourced from a scanned engineering document — reused, not rebuilt |
| Whatever `recipe_path` format is ultimately chosen — see §5, genuinely unresolved | — |

## 5. Manufacturing Recipe Candidates — the Central Open Finding

`MWO-LTSA-050` §"Open Questions" item 2 asked: *"What is the 'recipe' (`recipe_path`) format? No example exists anywhere in the repository."* This research found a candidate answer, with an important caveat:

**`AI5R-SDK/MANUFACTURING/RECIPES/manufacturing_recipe.py`'s `ManufacturingRecipe`** is a real, working, tested (`TESTS/test_mf_004_manufacturing_recipe.py`) frozen dataclass: `recipe_id`, `recipe_name`, `product_type`, `dbom_id`, `production_line_id`, `qa_policy_id`, `packaging_id`, `deployment_id`, `version`, `metadata`, `canonical_base: str = "ManufacturingObject"` — with `validate()` and `to_manufacturing_object()`. It is consumed today by `DigitalFactory` (`AI5R-SDK/MANUFACTURING/FACTORY/digital_factory.py`), which registers a `(ManufacturingRecipe, ProductionLine)` pair and executes orders against a `RuntimeEngine` (`AI5R-SDK/RUNTIME/runtime_engine.py`) via `ManufacturingRuntimeAdapter`. Concretely used, today, only for **organizational artifacts**: `company_recipe_registration.py` (Company), `department_recipe_registration.py` (Department), `role_recipe_registration.py` (Role) — confirmed by direct read of `company_recipe_registration.py`, which produces a `company_artifact` dict, not any LTSA business object.

**The caveat, confirmed by direct read, not assumed:** this `ManufacturingRecipe`'s own `to_manufacturing_object()` constructs `MANUFACTURING.OBJECTS.ManufacturingObject` — a **different class** from `AI5R-SDK/FACTORY/CORE`'s own `ManufacturingObject` that `UMC-001` Stage 6 governs. Likewise, `AI5R-SDK/MANUFACTURING/ORDERS/manufacturing_order.py`'s `ManufacturingOrder` (fields: `order_id`, `product_name`, `product_type`, `requested_by`, `recipe_id`, `dbom_id`, `priority` enum, `status` enum `DRAFT→...→COMPLETED`, `canonical_base: str = "ManufacturingObject"`) is a **different class** from `AI5R-SDK/FACTORY/ORDERS`'s own `ManufacturingOrder` that `UMC-001` Stage 1 governs — confirmed by direct field-level comparison, they do not share a definition. This is the **same category of finding as `ARCH-REVIEW-002`** (the `CORE`/`FOUNDATION` `ManufacturingEvent` duplication), now confirmed to extend to at least `ManufacturingOrder`, `ManufacturingObject`, and (by the same pattern, not yet field-verified in this pass) `ManufacturingStation` between `AI5R-SDK/FACTORY` and `AI5R-SDK/MANUFACTURING`.

**Consequence for this research:** `MANUFACTURING.RECIPES.ManufacturingRecipe` is a real, working recipe format — but adopting it as `FactoryPack.recipe_path`'s format would mean an Installation Factory Pack's "recipe" is expressed in a vocabulary (`ManufacturingOrder`/`ManufacturingObject` from `AI5R-SDK/MANUFACTURING`) that is name-identical to, but not interchangeable with, the vocabulary `UMC-001`/`UMR-001` actually execute (`AI5R-SDK/FACTORY`'s own `ManufacturingOrder`/`ManufacturingObject`). Whether this is (a) an acceptable, purely coincidental naming collision between two legitimately separate systems (organizational-artifact manufacturing vs. LTSA business-object manufacturing) — the same disposition `ARCH-REVIEW-002` reached for `ManufacturingEvent` — or (b) a sign that `recipe_path`'s intended format was always meant to be this `MANUFACTURING.RECIPES` system and the two should be reconciled, is **not decided here**. It is surfaced as a finding requiring the same weight `ARCH-REVIEW-002` gave the `ManufacturingEvent` collision, not resolved unilaterally.

## 6. Implementation Gaps

Precisely, following `MWO-LTSA-050`'s own evidentiary standard:

1. **No canonical Installation table, schema, or BUILD-PACK exists anywhere** — confirmed by direct search of `product.manifest.json`, `CANONICAL_SCHEMA.sql`, `REGISTRIES/`, and `BUILD-PACKS/`. This is the largest gap: every other Factory Pack research this session has performed (Pump) had a real table to research; Installation has none.
2. **No concrete `IdentityResolver`/`RelationshipResolver` implementation exists for any object yet, Pump included** — both remain `ABC` interfaces only, confirmed unchanged since `MWO-LTSA-048`. An Installation Factory Pack would be the platform's first concrete implementation of either, if built before Pump's own (sequencing question, not decided here).
3. **No adapter exists between a completed `acquisition_job` and `ManufacturingOrder.customer_request`** — the same gap `MWO-LTSA-050` §"Factory Analysis" found for Pump, applying identically here if Installation records are ever meant to be acquired from scanned engineering documents rather than entered directly.
4. **`recipe_path`'s format remains genuinely undefined** — §5's finding does not close this gap, it complicates it: a real candidate format exists, but adopting it imports a name-colliding vocabulary requiring its own disclosed decision.
5. **No governed translation exists from acquisition-layer vocabulary (e.g. `column_mapping.canonical_attribute` strings) to any Installation-specific column names** — moot until §1's candidate schema is itself decided, but noted as the same class of gap `MWO-LTSA-050` §3 found for Pump.
6. **Whether an Installation Factory Pack's station should be expressed as an `ADR-003` Capability or a plain `BaseManufacturingStation`** — the identical open question `MWO-LTSA-050` §4 raised for Pump, still unresolved platform-wide, not specific to either object.

---

## Open Questions (for a future Architecture Decision — not decided here)

1. Is "Installation" the correct name/scope for this canonical object, or does it belong as a new column/state on an existing table (e.g. `seal_pump_compatibility` gaining an `installed_at` field) rather than a wholly new table? Not decided — §1's candidate shape assumes a new table, but this is itself a decision, not a foregone conclusion.
2. Should `asset_registry.asset_code` be related to Installation via a real FK (a schema change to how Installation is designed) or the existing polymorphic-by-convention pattern (`work_order`/`maintenance_history`'s own precedent)?
3. **Is the `AI5R-SDK/MANUFACTURING`/`AI5R-SDK/FACTORY` name collision (`ManufacturingOrder`, `ManufacturingObject`, and likely `ManufacturingStation`) a second instance of the `ARCH-REVIEW-002` category of finding, warranting its own Architecture Review, or is it dispositioned by the same reasoning already applied there (separate, legitimate systems, coincidental name reuse)?** This is the most consequential open question this research raises — it affects not only Installation but any future Factory Pack research that touches "recipe" format.
4. Does an Installation Factory Pack come before or after Pump's own first concrete `IdentityResolver`/`RelationshipResolver` implementation? Pump was named as the anticipated first consumer in `MWO-LTSA-048`/`UMC-001`'s own text; Installation was not.
5. What is the correct identity scheme for Installation — synthetic UUID, or a composite natural key including a timestamp (since Pump+Seal pairing can recur over time, unlike `seal_pump_compatibility`'s single-instance compatibility rule)?

---

## Deliverables (this document only)

- This WP-000 research document, citing every claim to a direct file read.
- No code, schema, or build pack. No `AI5R-SDK/FACTORY`, `AI5R-SDK/MANUFACTURING`, `PRODUCTS/LTSA-BRAIN`, or Runtime file modified in producing it.

## Definition of Done (for this research)

- All six requested research areas (Canonical Installation object, Identity, Relationships, Factory Pack boundary, Manufacturing Recipe candidates, Implementation gaps) addressed with direct evidence. **Met.**
- The significant contextual discoveries (no canonical Installation object exists; a second, `AI5R-SDK/MANUFACTURING`-based manufacturing meta-model with name-colliding classes exists) disclosed up front, not buried. **Met.**
- No implementation performed; no Factory, Manufacturing, or LTSA Runtime file touched. **Met.**
- Open questions surfaced, not silently decided. **Met.**

---

Research only. Stopping here after WP-000, as instructed. Awaiting approval.
