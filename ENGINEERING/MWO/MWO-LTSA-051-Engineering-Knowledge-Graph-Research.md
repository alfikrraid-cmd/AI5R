# MWO-LTSA-051 — Engineering Knowledge Graph — WP-000 Research Report

Type: Research only — no implementation, no database changes, no runtime changes
Architecture: FROZEN — no new architecture proposed; this report maps existing, already-approved concepts (Enterprise Objects, Knowledge Foundation, Capability Foundation, BRAIN, the ADR-002 cognitive loop) onto the LTSA engineering domain

---

## Chief Approval — WP-000

**Status: APPROVED.** Research PASS. Architecture PASS. Knowledge Model PASS.

**Confirmed finding, recorded per Chief instruction:** the missing link identified in §6 of this report —

```
LearningObject
    ↓
KnowledgeObject
```

— is confirmed as the specific, named gap between what MO-001 already proved works (a real `LearningObject` produced by `BRAIN.EnterpriseCognitivePipeline`, per the Basic AI Assistant) and durable Engineering Knowledge (a persisted, queryable `KnowledgeObject` in `KNOWLEDGE/`'s registry, per ADR-002 Migration Step 5). This is the single missing link this WP-000 was scoped to find, and it is now the confirmed, recorded basis for any future Knowledge Manufacturing work.

**Decision on next steps:**
- **No Knowledge Engine is authorized at this time.** This finding is recorded, not implemented.
- **Current priority remains LTSA Manufacturing** (the Manufacturing Layer, per `MANUFACTURING/MANUFACTURING_BACKLOG.md`).
- **Knowledge Manufacturing — closing the `LearningObject → KnowledgeObject` link — becomes a future MWO, scheduled after LTSA v1.0.** It is deferred, not dropped; this report is the durable record a future MWO will resume from.

---

## Errata (official — factual correction only, no research reopened, no approval changed)

**Per explicit Chief Architect directive:** repository verification has confirmed that `seal_pump_compatibility`, `seal_interchange_compatibility`, and `seal_stock` have existed since `MWO-LTSA-030` — evidenced directly in `CANONICAL_SCHEMA.sql` (`seal_pump_compatibility` line 228, `seal_interchange_compatibility` line 239, `seal_stock` lines 213-220) and as complete, on-disk build packs (`BUILD-PACKS/BP-SEAL-PUMP-COMPATIBILITY/`, `BP-SEAL-INTERCHANGE-COMPATIBILITY/`, `BP-SEAL-STOCK/`). §1's grounding table below (as originally drafted) stated "Not modeled anywhere" for the "Seal Stock" and "Compatibility" rows — this is incorrect and is corrected below as a factual correction only. **The architectural conclusions of this report remain unchanged** (Installation and the Compatibility-as-a-rule/Compatibility-Reasoning gap this report identified are unaffected), and the Chief Approval above is not reopened or altered.

> **OLD:** Compatibility data does not exist.
> **NEW:** Compatibility data already exists. The remaining gap is Compatibility Reasoning and Compatibility Resolution over the existing data.

This is the same Errata applied to `MWO-LTSA-052` (Mechanical Seal Factory Pack Research), where the identical factual statement appeared independently. No `UMC-001`, `UMR-001`, or approval is changed by this Errata. No new architecture is introduced.

---

## 1. Grounding — what already exists (evidence, not assumption)

Before analyzing the eight named concepts, here is what this repository already has in place for them, confirmed by direct read of existing artifacts (no new data source was found — `mcp__filesystem__list_allowed_directories` confirms the same repository root already in use):

| Concept | Existing artifact | Status |
|---|---|---|
| Pump | `ltsa_pumps` (`DATABASE/CANONICAL_SCHEMA.sql`), `MODULES/PUMP/`, `BUILD-PACKS/BP-PUMP/` | Canonical, real |
| Mechanical Seal | `seal_registry`, `BUILD-PACKS/BP-SEAL/` | Canonical, real |
| Seal Stock | `seal_stock` (`CANONICAL_SCHEMA.sql:213-220`, `BUILD-PACKS/BP-SEAL-STOCK/`, manufactured under `MWO-LTSA-030`) | **Corrected per Errata above — canonical, real, not a gap.** Originally stated "Not modeled anywhere"; this was incorrect. |
| Installation | — | **Not modeled anywhere** — no table or event records "seal X installed into pump Y at time T" (unaffected by the Errata — this row was correct as originally drafted) |
| Maintenance | `work_order`, `maintenance_history` (`BUILD-PACKS/BP-WORK-ORDER`, `BP-MAINTENANCE-HISTORY`, manufactured under MO-001) | Canonical, real |
| Inspection | Only informally, inside `REALITY/reality_processing_station.py`'s regex-based finding extraction (vibration/temperature/leak keywords) and `BRAIN/observation_engine.py`'s signal derivation from the same shape | **Not a first-class Engineering Object** — folded into Reality/Observation's dict shape, no dedicated registry |
| Compatibility | `seal_pump_compatibility`, `seal_interchange_compatibility` (`CANONICAL_SCHEMA.sql:228-246`, both with complete build packs, manufactured under `MWO-LTSA-030`) | **Corrected per Errata above — the per-instance data is canonical and real, not a gap.** Originally stated "Not modeled anywhere"; this was incorrect. The remaining gap is Compatibility Reasoning/Resolution — a general rule ("which seal types fit which pump types") evaluated over this existing data — not the data itself. |
| Relationships | Implicit only, via the polymorphic `(asset_code, asset_type)` pattern already used by `work_order` and `maintenance_history` (documented in `BP-WORK-ORDER/DATABASE/001_create_table.sql`) | Pattern exists; no explicit relationship/edge table exists anywhere |

**Corrected per Errata:** only one of eight named concepts (Installation) has no existing artifact at all. Seal Stock and Compatibility both have real, existing per-instance data (`seal_stock`, `seal_pump_compatibility`, `seal_interchange_compatibility`); what remains open for Compatibility is a reasoning/resolution capability over that data, not the data itself. This research report's job remains determining *how these relate to the rest*, not building Installation or the Compatibility reasoning capability.

---

## 2. Nodes (Engineering Objects)

Each is an **Enterprise Object** in the Blueprint's precise sense (Vol. II, Ch.5: "a defined unit of business meaning that OSA Systems and AI Workforce reason about consistently, regardless of which System is doing the reasoning"):

- **Pump** — a physical asset, identified by `tag_number` (existing).
- **Mechanical Seal** — a physical component type/instance, identified by `seal_code` (existing).
- **Seal Stock** — the inventory-on-hand quantity of a given seal type at a given location. Distinct from Mechanical Seal itself the same way a product SKU is distinct from a warehouse's count of it — this is a **new node**, not a duplicate of `seal_registry`.
- **Installation** — the record of a specific seal instance placed into a specific pump at a specific point in time. This is an **event-shaped node** (has a timestamp, is not mutated after the fact), not a static registry entry.
- **Work Order / Maintenance History** — already the Maintenance nodes (existing, manufactured under MO-001).
- **Inspection** — a reading/observation taken against a Pump or Seal at a point in time (vibration, temperature, visual finding). Also **event-shaped**, like Installation.
- **Compatibility** — a rule, not an instance: "seal type X fits pump type Y." This is a **reference/rule node**, unlike the instance-shaped nodes above.

---

## 3. Relationships (Edges)

| Relationship | From → To | Nature |
|---|---|---|
| installed_into | Installation → Pump, Installation → Mechanical Seal | An Installation event references exactly one Pump and one Seal — this is the concrete instantiation of the `(asset_code, asset_type)` polymorphic pattern already used by Work Order/Maintenance History, applied to a Pump↔Seal pairing specifically |
| stocked_as | Seal Stock → Mechanical Seal | Seal Stock counts instances of a seal *type* (`seal_code`), the same catalog key `seal_registry` already uses — no new identifier scheme needed |
| compatible_with | Compatibility → Pump (by type), Compatibility → Mechanical Seal (by type) | A rule relationship, evaluated at *decision* time (e.g., "is this replacement seal compatible with this pump?"), not a per-instance relationship |
| inspected | Inspection → Pump or Mechanical Seal | Same polymorphic pattern as Installation |
| maintained_via | Work Order → Pump/Seal/Asset/Soot Blower (existing) | Already implemented exactly this way |
| logged_as | Maintenance History → Work Order | Already implemented |

**One structural finding worth flagging explicitly:** every relationship above either already uses, or should use for consistency, the same polymorphic `(asset_code, asset_type)` pattern this repository already committed to and documented under MO-001 — not a new relationship-modeling mechanism. This is a direct, evidence-based argument for extending the existing pattern rather than inventing a graph-native relationship mechanism, addressed further in §6.

---

## 4. Knowledge Objects vs. Engineering Objects — the central distinction this WP-000 asks for

An **Engineering Object** is a raw record: a specific Pump row, a specific Installation event, a specific Inspection reading. It answers "what is true right now, or what happened at this moment."

A **Knowledge Object** — per `KNOWLEDGE/`'s already-existing Foundation (`KF-005`, frozen spec) — is a distilled, retrievable unit of *understanding*, derived from the accumulated history of many Engineering Objects, not any single one of them. It answers "what have we learned that generalizes."

Example, grounded in the actual manufactured Basic AI Assistant (MO-001) and its real, executed output: a single Inspection reading (`vibration: 11.2, temperature: 92`) run through `BRAIN`'s pipeline produced a real `LearningObject` — `"Execution completed successfully. Current enterprise reasoning is reinforced."` with `confidence_delta: 0.10`. That single `LearningObject` is **not yet Engineering Knowledge** — it is one Knowledge Event about one Inspection. Engineering Knowledge (a `KnowledgeObject` in `KNOWLEDGE/`'s registry) would be the *generalization* across many such events — e.g., "Pumps in Area X consistently show `mechanical_instability` hypotheses confirmed when vibration exceeds 10 mm/s" — a pattern only visible after accumulating multiple Knowledge Events of the same shape.

---

## 5. Knowledge Events

A **Knowledge Event** is any discrete, timestamped occurrence that produces or updates understanding about an Engineering Object:

- An Inspection reading taken.
- An Installation performed.
- A Maintenance History record logged (an action taken, per MO-001's `maintenance_history` table).
- A Work Order closed.
- A BRAIN `Learning` stage output produced (already real and executable, per MO-001's Basic AI Assistant).

This Object/Event distinction is not a new concept invented for this report — it is exactly the distinction this repository's own (currently unwired) Foundation Reports already draw, in almost identical language: `WAREHOUSE/DOCS/WF-008` states *"Warehouse stores observed reality input"* (object-shaped), while `EXPERIENCE/DOCS/EF-008` states *"Experience observes and interprets source material"* (event-shaped). Engineering Objects here are Warehouse-shaped; Engineering Events (Installation, Inspection, a Learning output) are Experience-shaped, in this repository's own already-established vocabulary — reused, not reinvented.

---

## 6. Knowledge Manufacturing

This is the mechanism by which accumulated Knowledge Events become durable Engineering Knowledge — and it is not a new mechanism to design. It is the **same closed loop ADR-002 already specifies**: `Learning improves Knowledge. Knowledge improves Capability. Capability improves future reasoning [in BRAIN].`

Concretely, applied to this domain:

```
Inspection / Installation / Maintenance action (Engineering Event, real, timestamped)
        │
        ▼
BRAIN.EnterpriseCognitivePipeline.run(reality_dict)   ← already real, already executed (MO-001)
        │
        ▼
LearningObject (a Knowledge Event — one occurrence of new understanding)
        │
        ▼
KNOWLEDGE.KnowledgeIngestionEngine                    ← ADR-002 Migration Step 5, not yet implemented
        │
        ▼
KnowledgeObject, persisted, queryable, generalized     ← "Engineering Knowledge" proper
        │
        ▼
CapabilityValidationEngine resolves required_knowledge_ids  ← ADR-002/003, not yet implemented
        │
        ▼
Future BRAIN reasoning is informed by accumulated Engineering Knowledge
```

**Knowledge Manufacturing, precisely defined for this domain:** the accumulation of many Installation/Inspection/Maintenance-derived `LearningObject`s into `KNOWLEDGE/`'s registry, such that a future Inspection on a *different* pump can be reasoned about using what was learned from *prior* pumps — e.g., a Compatibility rule or a failure-mode pattern becoming a queryable `KnowledgeObject` rather than being re-derived from scratch by BRAIN every single time. This is the ADR-002 loop's Step 5 (Learning → Knowledge) and Step 6 (Knowledge → Capability, ongoing), applied specifically to engineering domain events rather than described only in the abstract.

---

## 7. Engineering Knowledge Graph (research-level diagram, not an implementation)

```
                         ┌────────────────┐
                         │  Compatibility  │  (rule node)
                         └───────┬────────┘
                                 │ compatible_with
              ┌──────────────────┼──────────────────┐
              ▼                                      ▼
        ┌──────────┐                           ┌──────────────┐
        │   Pump    │◄──────installed_into──────│ Mechanical    │
        │ (existing)│                           │ Seal (existing)│
        └─────┬─────┘                           └───────┬────────┘
              │                                          │
     inspected│         installed_into (event)  stocked_as│
              ▼                  ▼                        ▼
        ┌───────────┐    ┌───────────────┐         ┌────────────┐
        │ Inspection │    │  Installation  │         │ Seal Stock  │
        │  (event,   │    │    (event,     │         │ (new node)  │
        │  new node) │    │   new node)    │         └────────────┘
        └─────┬──────┘    └───────┬────────┘
              │                   │
              └─────────┬─────────┘
                        │ maintained_via (existing pattern)
                        ▼
                 ┌─────────────┐        logged_as       ┌─────────────────────┐
                 │ Work Order   │────────────────────────►│ Maintenance History  │
                 │  (existing)  │                          │     (existing)       │
                 └──────┬───────┘                          └──────────┬───────────┘
                        │                                             │
                        └──────────────────┬──────────────────────────┘
                                            ▼
                             BRAIN.EnterpriseCognitivePipeline
                                    (real, executed — MO-001)
                                            │
                                            ▼
                                   LearningObject (Knowledge Event)
                                            │
                              KNOWLEDGE.KnowledgeIngestionEngine
                                  (ADR-002 Step 5 — not yet built)
                                            │
                                            ▼
                                KnowledgeObject (Engineering Knowledge)
                                            │
                          informs future Capability / BRAIN reasoning
                                (ADR-002/003 — not yet built)
```

---

## 8. What this research does and does not conclude

**Does conclude:**
- Two of the three previously-unmodeled concepts (Seal Stock, Compatibility) are naturally **reference/inventory nodes**, not events, and would extend the existing `seal_registry`/pump-type vocabulary rather than requiring new identifier schemes.
- The third (Installation), together with the already-informal Inspection, is naturally an **event node**, following the exact polymorphic `(asset_code, asset_type)` pattern already committed to under MO-001 for Work Order and Maintenance History — the same convention, not a new one.
- "Engineering Objects becoming Engineering Knowledge" is not a new mechanism to invent — it is ADR-002's already-approved Knowledge/Capability/BRAIN loop, and this domain's Inspection/Installation/Maintenance events are simply real instances of the Reality-shaped input that loop already, actually, successfully processes (per MO-001's genuinely executed Basic AI Assistant).

**Does not conclude, and is explicitly out of this WP-000's scope:**
- Whether Seal Stock, Installation, Compatibility, or a first-class Inspection registry should actually be built, in what order, or as which specific tables/workflows — that is implementation planning, for a future, separately-approved work package.
- Any schema, migration, or workflow file — none was created or modified in producing this report.

---

Nothing was implemented. No database was changed. No runtime was changed. Stopping here as instructed. Waiting for Chief approval before WP-001 (if approved) begins.
