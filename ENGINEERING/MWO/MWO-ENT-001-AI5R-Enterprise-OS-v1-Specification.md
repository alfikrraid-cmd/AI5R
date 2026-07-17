# MWO-ENT-001 — AI5R Enterprise OS v1 — Functional Specification

Status: SPECIFICATION ONLY — no implementation performed, no code written, no schema written, no BUILD-PACK created.
Type: Manufacturing Work Order (Specification / WP-000)
Role: Implementation Engineer, acting on Chief Architect ("AI5R Enterprise Architect") direction.
Architecture: FROZEN — nothing in this document redesigns AI5R's architecture. Every mechanism named below is an existing, already-established AI5R component (`ADR-001`, `ADR-002`, `ADR-003`, `ADR-004`, `UMC-001`, `UMR-001`, `CORE-SERVICES/API`, `CORE-SERVICES/BACKEND-API`) or a direct, structurally-consistent extension of one. Where no existing component covers a requirement, that gap is named explicitly as new, not disguised as reuse.
Scope: This document only. No `AI5R-SDK`, `PRODUCTS/LTSA-BRAIN`, `CORE-SERVICES`, or Runtime file is modified in producing it.

---

## Executive Summary

This is the first real customer deployment of **AI5R's own flagship product, OSA** (`ADR-001`), branded for this engagement as **AI5R Enterprise OS v1**. Per `ADR-001` Decision Topic 5, its three requested capabilities — LTSA, Finance, HR — are **Subsystems assembled into one delivered Product, not three separate products.** `PRODUCTS/LTSA-BRAIN` is direct precedent: it is already, today, exactly this kind of Product, and its own `product.manifest.json` already declares `maintenance` as one of its own modules, not a sibling product (`ADR-001` §Reason, item 2). LTSA OS in this specification **is** `PRODUCTS/LTSA-BRAIN`, renamed for the customer-facing business context, not a new build.

Four converging pieces of prior, real, already-committed work make most of this specification reuse rather than invention:

1. **`CORE-SERVICES/API`** already implements Pump/Work Order/Maintenance History Gateways, Role Manufacturing, Organization Registry, and — critically — a **Maintenance Execution Runtime, Command Center, Intelligence Service, and Copilot** (`MWO-019`–`022`, committed `07dba51`/`d911cc6`/`9be02bb`/`45a8d2e`). The Owner Dashboard requested below is not a new build; it is a direct extension of `maintenance_command_center.get_maintenance_command_center()`, which already returns exactly this shape (total pumps, active work orders, completed-today, recent work orders, recent maintenance, organization summary).
2. **`CORE-SERVICES/BACKEND-API`** (`MWO-DEP-001`, committed `d9f879e`) already exposes this over HTTP, and its own commit note **explicitly and deliberately deferred** free-text WhatsApp-style question routing: *"POST /copilot (free-text question routing) intentionally excluded per approval note: NLP/intent routing belongs to a future Agent Layer, not this Backend API."* The AI LTSA Operator specified below **is** that already-named, already-anticipated Agent Layer — not a new architectural concept.
3. **`PRODUCTS/LTSA-BRAIN/AI-ASSISTANT/maintenance_assistant.py`** (`MO-001`/`BP-AI-ASSISTANT`) already calls `BRAIN.EnterpriseCognitivePipeline` to turn a maintenance observation (findings text, vibration, temperature) into a recommendation. This is the working proof that BRAIN-driven natural-language maintenance reasoning is not hypothetical in this repository — it is the direct precedent the AI LTSA Operator's Understanding stage extends.
4. **`ADR-002`/`ADR-003`** already name the exact peer assets this specification needs: BRAIN (*"BRAIN decides"* — the Enterprise Cognitive Processor) and Capability (*"Capability executes"* — and **WhatsApp is already a named Capability**, under Capability's own `Communication` group: *"Email, WhatsApp, Telegram, Slack, Discord"*). Neither BRAIN's production use nor a WhatsApp Capability provider exists yet (confirmed — no `WhatsApp`/`WHATSAPP` reference exists anywhere in `AI5R-SDK` today); this specification is the first real consumer of both, not their invention.

The two-legal-entity business model (customer-facing **PT Tommy Adji Prasetyo**, internal-only **CV Razzan Teknik Mandiri**) is genuinely new — no existing AI5R component models multiple legal entities behind one Organization Registry today. §1 and §10 below specify it as a minimal extension of the existing Organization Registry / canonical-object pattern, not a new subsystem or runtime.

---

## 1. Enterprise Architecture

```
AI5R  (Digital Factory — manufacturer; ARCHITECTURE/AI5R-ARCHITECTURE-SPEC-v2.0.md, frozen)
   │
   ├── Knowledge   (peer asset — Enterprise Knowledge Base, ADR-002)
   ├── Capability  (peer asset — Universal Execution Layer, ADR-003; WhatsApp lives here)
   ├── BRAIN       (peer asset — Enterprise Cognitive Processor, ADR-002)
   ├── Factory     (peer asset — UMC-001/UMR-001, the Manufacturing Contract/Runtime)
   │
   ▼
OSA  (flagship product/platform — ADR-001)
   │
   ▼
AI5R Enterprise OS v1   ← this specification's own Product instance,
   │                       what PT Tommy Adji Prasetyo / CV Razzan requested and receives
   │                       (ADR-001 §Deliverable — Business Architecture)
   │
   ├── LTSA OS      (Subsystem = PRODUCTS/LTSA-BRAIN, already a real Product per
   │                  ADR-001's own precedent — renamed for this business context,
   │                  not rebuilt; see §3)
   ├── Finance OS    (Subsystem — new; see §4)
   └── HR OS         (Subsystem — new; see §5)
```

**Legal Entity layer.** Neither `ADR-001` nor the Organization Registry models more than one legal entity today. This specification adds one new, minimal Enterprise Object — **Legal Entity** — as a peer reference alongside Organization Registry's existing Department/Role objects, not a new subsystem or a new runtime:

```
Legal Entity
  ├── PT Tommy Adji Prasetyo   (customer_facing = true)
  └── CV Razzan Teknik Mandiri (customer_facing = false)
```

Every canonical, customer-visible object (Technical Report, Quotation, Invoice, WhatsApp message sent to a customer) carries an `issuing_entity` reference resolved to `PT Tommy Adji Prasetyo` by a fixed rule (§10), never by user choice. Every internal-only object (Work Order, Maintenance History, PM/CM record, Payroll, internal Cost) carries `owning_entity = CV Razzan Teknik Mandiri`. No user of any role ever chooses which entity a document belongs to — the rule is structural, enforced at Canonical Object Manufacturing time (Stage 6 of `UMC-001`), the same stage that already, today, writes every other canonical object's fixed fields.

**Existing components reused unchanged, no file touched by this specification:**
- `CORE-SERVICES/API/{pump_gateway,work_order_gateway,maintenance_history_gateway,role_manufacturing,organization_registry,maintenance_execution_runtime,maintenance_command_center,maintenance_intelligence_service,maintenance_copilot}.py`
- `CORE-SERVICES/BACKEND-API/*` (FastAPI HTTP layer)
- `PRODUCTS/LTSA-BRAIN/AI-ASSISTANT/maintenance_assistant.py` (BRAIN precedent)
- `AI5R-SDK/FACTORY/{CORE,FOUNDATION,RESOLUTION,PACKS,ORDERS,VALIDATION}` — `UMC-001`/`UMR-001`, and the Pump Factory Pack pattern (`MWO-LTSA-050` WP-001) as the template for any new canonical-object manufacturing this specification requires
- `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/*` — every existing canonical LTSA table and its n8n workflow (`ltsa_pumps`, `seal_registry`, `work_order`, `maintenance_history`, and the Engineering Acquisition tables)

**New, not yet built — named explicitly, not disguised as existing:**
- The **Agent Layer** (already named and deferred by `MWO-DEP-001`) — houses the AI LTSA Operator (§14)
- A **WhatsApp Capability provider** (already named by `ADR-003`, under `Communication`, never implemented)
- **Legal Entity** as a new Enterprise Object (this section)
- **PM Record, CM Record, Technical Report, Quotation, Invoice** as new canonical objects (§2, §13)
- **Finance OS and HR OS** subsystems in full (§4, §5)

---

## 2. Enterprise Objects

| Object | Status | Owning Layer |
|---|---|---|
| Pump (`ltsa_pumps`), Seal (`seal_registry`), Asset (`asset_registry`), Soot Blower (`soot_blower_registry`) | **Existing, reused unchanged** | LTSA OS |
| Work Order (`work_order`) | **Existing, reused unchanged** | LTSA OS |
| Maintenance History (`maintenance_history`) | **Existing, reused unchanged** | LTSA OS |
| Organization, Department, Role | **Existing, reused unchanged** (Organization Registry / Role Manufacturing) | Cross-cutting |
| Engineering Media (`engineering_media`/`media_metadata`/`media_classification`/`media_acquisition_job`) | **Existing, reused unchanged** (`ADR-004`, `MWO-LTSA-040E`) | LTSA OS — the canonical shape for every PM/CM photo attachment |
| **Legal Entity** | **New** — minimal reference object (§1) | Cross-cutting |
| **PM Record** | **New** — canonical object, one per inspection (§8) | LTSA OS |
| **CM Record** | **New** — canonical object, one per corrective action (§9) | LTSA OS |
| **Technical Report** | **New** — canonical, customer-facing, aggregates PM/CM (§11) | LTSA OS ↔ Finance OS boundary |
| **Quotation** | **New** — canonical, customer-facing (§10) | Finance OS |
| **Invoice** | **New** — canonical, customer-facing (§10) | Finance OS |
| **WhatsApp Message Thread** | **New** — raw intake log, pre-extraction (§7) | Agent Layer |
| Cash Transaction, Bank Transaction, Expense, Vendor, Purchase Order, Cost Center, Project Cost, Customer Billing Record, Inter-Entity Settlement | **New** | Finance OS (§4) |
| Employee, Attendance Record, Leave Request, Overtime Record, Payroll Record, Performance Review, Training Record, Competency Record | **New** | HR OS (§5) |

Every new canonical object above follows the **fixed canonical table shape** already frozen by this repository's own standing decision (`MEMORY.md`): `TEXT` primary key, `created_at`/`updated_at TIMESTAMP DEFAULT NOW()`, closed-set fields enforced by `CHECK` constraints, never a code branch — the same shape `seal_registry`, `work_order`, and every `BUILD-PACKS/BP-*` table already use. No new table-shape convention is introduced.

---

## 3. LTSA OS Modules

LTSA OS **is** `PRODUCTS/LTSA-BRAIN`. Its module inventory, existing vs. new:

| Module | Status |
|---|---|
| Asset Registry (Pump/Seal/Asset/Soot Blower) | **Existing** |
| Work Order Management | **Existing** (`BP-WORK-ORDER` + `WorkOrderGateway`) |
| Maintenance History | **Existing** (`BP-MAINTENANCE-HISTORY` + `MaintenanceHistoryGateway`) |
| Maintenance Execution Runtime | **Existing** (`maintenance_execution_runtime.execute_maintenance()`: Retrieve Pump → Create Work Order → Assign Role → Create Maintenance History) |
| Maintenance Command Center | **Existing** (`maintenance_command_center.get_maintenance_command_center()` — the Owner Dashboard's own backend, extended not replaced, §12) |
| Maintenance Intelligence Service | **Existing** (`get_pump_status`, `get_pump_history`, `get_active_work_orders`, `get_assigned_role`, `summarize_situation`) |
| Maintenance Copilot | **Existing, outbound only** (`show_pump`, `explain_pump_status`, `explain_pump_history`, `explain_work_orders`, `explain_assigned_role`, `summarize_maintenance_situation` — plain-language answers to *already-stored* data. Does **not** ingest new information; that is the AI LTSA Operator's job, not a duplicate of this module's) |
| **AI LTSA Operator** | **New** — the Agent Layer `MWO-DEP-001` deferred (§14) |
| **PM / CM Classification & Recording** | **New** — canonical objects manufactured per engineer report (§8, §9) |
| **Technical Report Generation** | **New** (§11) |
| **LTSA Knowledge / Pattern Detection** | **New** — the concrete LTSA instance of `ADR-002`'s Learning→Knowledge loop (repeated seal/bearing/vibration/leakage patterns across a Pump's PM→CM→PM history) |

**Open architecture question, not decided here** (already surfaced, unresolved, by `MWO-LTSA-054` WP-000, re-affirmed rather than re-litigated): should PM/CM records be manufactured through **System A** (the proven `Gateway` + n8n pattern Work Order/Maintenance History already use) or **System B** (`UMC-001`/`UMR-001`, the pattern this session's own `MWO-LTSA-050` WP-001 just proved for Pump)? Both are legitimate, existing, frozen patterns. This specification describes PM/CM's *data shape and workflow* (§8, §9) without resolving *which* manufacturing system builds them — that remains, per `MWO-LTSA-054`'s own standing disposition, "a shared, cross-Factory-Pack decision, not decided by [any single] MWO alone."

---

## 4. Finance OS Modules

New subsystem, assembled into AI5R Enterprise OS v1 per `ADR-001` Decision Topic 5 (Finance is a named Subsystem type in `ADR-001`'s own Deliverable — Business Architecture diagram). **Belongs to CV Razzan operationally; issues documents under PT Tommy Adji Prasetyo where customer-facing** (§1, §10).

| Module | Scope |
|---|---|
| Cash & Bank Management | Internal cash/bank ledgers, CV Razzan and PT Tommy Adji Prasetyo each carry their own accounts (two sets of books, one Product) |
| Expense Management | CV Razzan's operational expenses (parts, travel, tools) |
| Vendor & Purchase Management | CV Razzan's supplier relationships and purchase orders |
| Cost Center & Project Cost Tracking | Attributes CV Razzan's engineer time, parts, and overhead to a specific Work Order / Pump / customer project |
| Payroll Disbursement | Pays out amounts HR OS's Payroll module (§5) calculates — Finance owns the money movement, HR owns the calculation |
| Customer Billing (Quotation → Invoice → Payment) | Issued and received **only** under PT Tommy Adji Prasetyo (§10) |
| **Inter-Entity Settlement** | New concept, required by the dual-entity model: reconciles CV Razzan's incurred Project Cost against the revenue PT Tommy Adji Prasetyo actually billed and collected for that same Work Order — the mechanism that lets one Product's books stay separable into two entities' financial statements without the customer ever seeing CV Razzan (§10) |

---

## 5. HR OS Modules

New subsystem, `ADR-001`-named. **CV Razzan only — never customer-visible, never exposed via any customer-facing channel.**

| Module | Scope |
|---|---|
| Employee Master | Engineer, Supervisor, Admin, Finance Officer, HR Officer, Owner — one record per CV Razzan person |
| Attendance | Clock-in/out or field-presence tracking for Engineers |
| Leave | Leave request/approval |
| Overtime | Overtime request/approval, feeds Payroll |
| Payroll (calculation) | Computes pay per Employee per period; hands the payable amount to Finance OS's Payroll Disbursement (§4) — HR calculates, Finance pays, matching the same separation of concerns already used between LTSA OS's Command Center (presentation) and its Gateways (persistence) |
| Performance | Performance review records, may reference PM/CM completion quality as an input (LTSA OS → HR OS cross-reference, read-only) |
| Training | Training records per Employee |
| Competency | Skill/certification records — the natural extension point for LTSA OS's existing `role_manufacturing.retrieve_role_artifact()` (Work Order `assigned_to` resolution already goes through Role Manufacturing today; Competency is additional data *about* the role-holder, not a new assignment mechanism) |

---

## 6. User Roles

Reuses the existing Organization Registry / Role Manufacturing pattern (`role_manufacturing.py`, already resolving `work_order.assigned_to` today). Adds one new dimension — **Legal Entity scope** (§1) — as a role attribute, not a new authorization mechanism.

| Role | Entity Scope | Channel | Notes |
|---|---|---|---|
| Engineer | CV Razzan | **WhatsApp only** | No login, no form, no mobile app — per explicit instruction. Identified by phone number, resolved to an Employee/Role via Organization Registry |
| Supervisor | CV Razzan | Dashboard (internal) | Reviews AI-drafted PM/CM records and Technical Reports before customer release |
| Admin | CV Razzan | Dashboard (internal) | Manages Work Orders, Assets, org structure |
| Finance Officer | CV Razzan (operates), issues under PT Tommy Adji Prasetyo | Dashboard (internal) | Operates Finance OS; the only role that touches both entities' books directly, by job function, not by dashboard visibility |
| HR Officer | CV Razzan | Dashboard (internal) | Operates HR OS |
| **Owner** | **Both entities** | Dashboard (internal) | The **only** role with cross-entity visibility (§12) |
| Customer | PT Tommy Adji Prasetyo only | WhatsApp, Technical Reports, Quotations, Invoices | **Never logs in.** Never sees CV Razzan in any form |
| Website Visitor | PT Tommy Adji Prasetyo only | Public website | No LTSA/Finance/HR system access of any kind |

**Rule, structural not optional:** no interface, document, or message ever renders "CV Razzan Teknik Mandiri" to a Customer or Website Visitor. This is enforced the same way `issuing_entity` is fixed at Canonical Object Manufacturing time (§1) — not a display-layer filter applied after the fact.

---

## 7. WhatsApp Workflow

```
Engineer (WhatsApp)
   │  free text / image
   ▼
WhatsApp Capability            (ADR-003, Communication group — NEW provider, not yet built)
   │  raw inbound message
   ▼
WhatsApp Message Thread        (new object, §2 — the durable intake log, pre-extraction)
   │
   ▼
AI LTSA Operator / Agent Layer (NEW — the layer MWO-DEP-001 already deferred, §14)
   │
   ├─► BRAIN (Observation → Understanding)   [existing peer asset, ADR-002;
   │                                          precedent: maintenance_assistant.py's
   │                                          EnterpriseCognitivePipeline call]
   │        │
   │        ▼
   │   Extracted candidate fields + list of missing required fields
   │
   ├─► if fields missing:
   │        AI LTSA Operator composes a follow-up question
   │        (Tag Number? PM or CM? Pressure? Temperature? Leakage?
   │         Running hour? Equipment condition? Before/After photos?)
   │            │
   │            ▼
   │        WhatsApp Capability sends the question back to the Engineer
   │            │
   │            └──────────────► (loop back to top until complete)
   │
   └─► if complete:
            PM/CM Classification (§8/§9)
                │
                ▼
            Identity Resolution — candidate tag_number against ltsa_pumps
            (same pattern as PumpIdentityResolver, MWO-LTSA-050 WP-001)
                │
                ▼
            Canonical PM/CM Record manufactured
                │
                ▼
            Supervisor notified (existing Command Center dashboard surfaces
            it as a pending item, §12)
                │
                ▼
            Supervisor Review
                │
                ▼
            Technical Report drafted (§11)
                │
                ▼
            Customer Report sent — WhatsApp Capability, branded
            PT Tommy Adji Prasetyo (§1, §6)
                │
                ▼
            Finance OS notified if billing required (§10)
```

Photos ("Saya lampirkan 8 foto") are **not** a new attachment mechanism — each becomes an Engineering Media Acquisition Object (`ADR-004`, `MWO-LTSA-040E`, already real: `engineering_media`/`media_metadata`/`media_classification`/`media_acquisition_job`), related to its PM/CM record the same way any other cross-reference is resolved in this architecture (Relationship Resolution, `UMC-001` Stage 5).

---

## 8. PM Workflow (Preventive Maintenance)

**Trigger:** a scheduled or engineer-initiated inspection report over WhatsApp.

**Required structured fields** (per the brief, all confirmed mappable to either an existing schema field or a clearly new one):

| Field | Source |
|---|---|
| Inspection Date | New — defaults to message timestamp, engineer may override |
| Engineer | Resolved via Organization Registry / Role Manufacturing from the sending phone number |
| Equipment | Identity Resolution against `ltsa_pumps.tag_number` (or the relevant asset registry, per `asset_type`, same polymorphic pattern `MWO-LTSA-054` §3 already documented for Work Order/Maintenance History) |
| Pressure, Temperature, Leakage, Vibration | New — free-form/numeric fields on the new PM Record object |
| Condition | New — closed-set field (e.g. `GOOD`/`FAIR`/`POOR`/`CRITICAL`), `CHECK`-constrained per the frozen canonical table shape |
| Recommendation | New — free text, optionally BRAIN-assisted draft (same mechanism as `maintenance_assistant.get_maintenance_recommendation()`) |
| Photos | Engineering Media Acquisition Objects (§7), related, not embedded |

**Workflow:** WhatsApp Workflow (§7) → PM classified (engineer states "PM," or AI LTSA Operator infers from context/absence of a failure description) → PM Record manufactured → linked to the relevant Pump (Identity Resolution) and, if one is open, the active Work Order (Relationship Resolution, same optional/non-error-if-unresolved semantics `MWO-LTSA-054` §3 already established for `maintenance_history.work_order_code`) → contributes to LTSA Knowledge (§3) → surfaces on the Owner Dashboard's "PM Completed" count (§12).

---

## 9. CM Workflow (Corrective Maintenance)

**Trigger:** a failure/repair report over WhatsApp (the brief's own example: *"PUMP-001 selesai. Mechanical seal diganti. Bearing masih bagus. Pressure 4.8 bar."*).

**Required structured fields:**

| Field | Source |
|---|---|
| Failure | New — what failed/was found |
| Root Cause | New — free text, optionally BRAIN-assisted (a candidate for LTSA Knowledge pattern detection, §3) |
| Action Taken | New — maps conceptually to `maintenance_history.action_taken`, the one already-required field on the existing canonical `maintenance_history` table |
| Parts Used | New — free text/structured list for v1 (no Inventory subsystem exists yet to deduct against, see §15) |
| Duration | New |
| Engineer | Same resolution as PM (§8) |
| Recommendation | New — same mechanism as PM |
| Photos | Same Engineering Media Acquisition pattern as PM (§7) |

**Workflow:** identical shape to PM (§7→§8) with CM classification instead — AI LTSA Operator distinguishes PM from CM the same way it distinguishes any missing-field case: explicit engineer statement first, follow-up question ("PM atau CM?") if ambiguous. A CM Record's `Action Taken` and `Engineer` fields are structurally the closest new-object match to the existing `maintenance_history` table's own two required fields — this specification treats CM Record as the natural-language-intake front end to that same business concept, without pre-deciding (per §3's Open Question) whether it is literally the same canonical table or a new one manufactured through System B.

---

## 10. Billing Workflow

The dual-entity mechanism (§1, §4) made concrete:

```
CM/CM Record (owning_entity = CV Razzan, cost incurred)
   │
   ▼
Technical Report (§11) — Supervisor-approved
   │
   ├─► New work, not yet contracted:
   │        Quotation manufactured, issuing_entity = PT Tommy Adji Prasetyo
   │        │
   │        ▼
   │        sent to Customer (WhatsApp/Portal, §6)
   │        │
   │        ▼ (customer accepts)
   │
   └─► Already contracted, or Quotation accepted:
            Invoice manufactured, issuing_entity = PT Tommy Adji Prasetyo
                │
                ▼
            sent to Customer (WhatsApp/Portal)
                │
                ▼
            Payment received — recorded under PT Tommy Adji Prasetyo's
            own Cash/Bank (§4)
                │
                ▼
            Customer Billing Record created (PT Tommy Adji Prasetyo)
                │
                ▼
            Inter-Entity Settlement entry created — credits CV Razzan's
            Project Cost Tracking (§4) for the operational cost already
            incurred on this Work Order, reconciling the two entities'
            books for one piece of work without CV Razzan ever invoicing
            the customer directly
```

`issuing_entity`/`owning_entity` are fixed at manufacture time (§1) — no role, including Finance Officer, selects them per-document. This is what makes the two-company model a data-layer rule rather than a manual, error-prone bookkeeping discipline.

---

## 11. Technical Report Workflow

**Trigger:** one or more approved PM/CM Records for a Work Order (or a time period, for scheduled reporting).

```
PM/CM Record(s) (§8/§9, already manufactured)
   │
   ▼
AI LTSA Operator drafts a narrative Technical Report
   (extends the existing maintenance_assistant.get_maintenance_recommendation()
    pattern — BRAIN-assisted narrative generation from structured findings,
    not a new NLG mechanism)
   │
   ▼
Supervisor Review — edit/approve (Dashboard, §12)
   │
   ▼
Technical Report manufactured, issuing_entity = PT Tommy Adji Prasetyo,
linked back to its originating PM/CM Record(s) and Work Order (traceability)
   │
   ▼
sent to Customer (WhatsApp/Portal, §6)
   │
   ▼
if the report implies billable work → Billing Workflow (§10) triggered
```

---

## 12. Dashboard Design

Extends, not replaces, `maintenance_command_center.get_maintenance_command_center()` — its existing return shape (`summary`, `recent_work_orders`, `recent_maintenance`, `organization_summary`) is the direct precedent for every dashboard below.

**Owner Dashboard** (cross-entity — the only surface with visibility into both PT Tommy Adji Prasetyo and CV Razzan):
- Today's Inspection (new PM/CM-classified count, extending the existing `completed_today` computation)
- PM Completed / CM Completed (new, classification-split version of the existing `recent_maintenance` list)
- Open Findings (new — PM/CM Records not yet folded into an approved Technical Report)
- Critical Equipment (new — Pumps whose latest PM/CM `Condition` is `CRITICAL`/`POOR`)
- Assets Requiring Attention (new — same source, broader threshold)
- Technical Reports Waiting Approval (new — Supervisor Review queue, §11)
- Billing Waiting (new — Quotations/Invoices not yet sent or not yet paid, §10)
- Finance summary (CV Razzan cost side + PT Tommy Adji Prasetyo revenue side, reconciled via Inter-Entity Settlement, §4/§10 — Owner-only)

**Supervisor Dashboard** (CV Razzan only): the review/approval queues above (Open Findings, Technical Reports Waiting Approval), no Finance/HR content.

**Customer:** explicitly **not** a dashboard. WhatsApp + delivered documents only (§6), all branded PT Tommy Adji Prasetyo — consistent with "Customer never logs into LTSA."

---

## 13. Database Objects

**Existing, reused unchanged** (already canonical, already committed):
`ltsa_pumps`, `seal_registry`, `seal_stock`, `seal_pump_compatibility`, `seal_interchange_compatibility`, `seal_engineering_document`, `work_order`, `maintenance_history`, `knowledge_source_registry`, `workbook`/`worksheet`/`worksheet_table`/`mapping_profile`/`column_mapping`/`acquisition_job`, `engineering_media`/`media_metadata`/`media_classification`/`media_acquisition_job`, `pdf_document`/`pdf_metadata`/`document_classification`/`pdf_acquisition_job`, and Organization Registry's own department/role tables (referenced by `role_manufacturing.py`/`organization_registry.py`; exact table names not independently re-verified in producing this specification — flagged, not assumed).

**New, required for this specification** (all to follow the frozen canonical table shape, §2):
- `legal_entity` (§1)
- `pm_record`, `cm_record` — **or** a single `maintenance_finding` table with a `record_type CHECK (record_type IN ('PM','CM'))` discriminator column. **Not decided here** — this is exactly `MWO-LTSA-054`'s own still-open Question 1 ("one Factory Pack manufacturing two object types, or two separate Factory Packs"), restated at the schema level; this specification names both candidate shapes without choosing between them.
- `technical_report`
- `quotation`, `invoice`
- `whatsapp_message_thread` (raw intake log)
- `cash_transaction`, `bank_transaction`, `expense`, `vendor`, `purchase_order`, `cost_center`, `project_cost`, `customer_billing_record`, `inter_entity_settlement` (Finance OS, §4)
- `employee`, `attendance_record`, `leave_request`, `overtime_record`, `payroll_record`, `performance_review`, `training_record`, `competency_record` (HR OS, §5)

No column-level DDL is specified here — per instruction, this is a functional specification, not implementation.

---

## 14. AI Responsibilities

Split precisely along `ADR-002`/`ADR-003`'s own governing distinction — **BRAIN decides, Capability executes** — with the Agent Layer (`MWO-DEP-001`'s own deferred concept) as the new orchestration point that calls both:

| Responsibility | Owner | Status |
|---|---|---|
| Receive text/images from WhatsApp | WhatsApp Capability (`ADR-003`, Communication) | **New** — not yet built |
| Receive voice notes | WhatsApp Capability | **New — Future** (§15), explicitly deferred by the brief itself |
| Understand natural language, extract structured candidate fields | BRAIN (Observation → Understanding), precedent `maintenance_assistant.py` | **New consumption of an existing engine** |
| Identify missing required fields, compose follow-up questions | Agent Layer (AI LTSA Operator) | **New** |
| Classify PM vs. CM | Agent Layer, BRAIN-assisted | **New** |
| Resolve Equipment identity (tag_number → ltsa_pumps) | Identity Resolution, `UMC-001` Stage 4 — same pattern as `PumpIdentityResolver` (`MWO-LTSA-050` WP-001) | **New instance of an existing, proven pattern** |
| Manufacture PM/CM Record | Canonical Object Manufacturing, `UMC-001` Stage 6 (System B) or Gateway pattern (System A) — architecture decision open, §3 | **New**, pattern proven |
| Generate inspection records / maintenance history | Same as above | **New** |
| Draft Technical Report narrative | BRAIN, precedent `maintenance_assistant.get_maintenance_recommendation()` | **New consumption of an existing engine** |
| Notify Supervisor | Agent Layer → existing Command Center dashboard surface | **New notification, existing display target** |
| Notify Finance when billing required | Agent Layer → Finance OS (§4, new) | **New** |
| Detect PM/CM failure patterns (repeated seal/bearing/vibration/leakage) | LTSA Knowledge, the concrete instance of `ADR-002`'s Learning→Knowledge loop | **New — Future** (§15); `ADR-002`'s Migration Strategy Steps 1–6 are the prerequisite, not yet implemented for any product |

---

## 15. Future Expansion

Named explicitly so this v1 specification is not mistaken for the ceiling of AI5R's own architecture:

- **Inventory subsystem** (`ADR-001`-named, not yet built) — needed to make CM's "Parts Used" (§9) deduct against real stock rather than remain free text.
- **CRM subsystem** (`ADR-001`-named, not yet built) — richer customer relationship management beyond WhatsApp + Quotation/Invoice.
- **Marketing, Procurement, Project subsystems** (`ADR-001`-named, not yet built) — available to be assembled into a future version of this same Product, per `ADR-001`'s own Subsystem list, without requiring a new Product.
- **Voice Notes** — explicitly named as future by the brief itself; the WhatsApp Capability's eventual voice-input support, feeding the same BRAIN Understanding stage already specified for text (§7, §14).
- **Full BRAIN Learning → Knowledge closed loop** (`ADR-002` §2, Migration Strategy Steps 1–6) — today's LTSA Knowledge pattern detection (§3, §14) is the first real product-level motivation for actually implementing that loop, not a redesign of it.
- **Additional Capability Communication providers** (Email, Telegram, Slack, Discord — all already named by `ADR-003`, none built) — for channels beyond WhatsApp, should this Product's customer base need them.
- **Multi-customer, multi-tenant scaling** — this specification describes one customer opportunity (PT Tommy Adji Prasetyo / CV Razzan). `ADR-001`'s own architecture already anticipates OSA serving many such opportunities; nothing here forecloses a second, differently-branded AI5R Enterprise OS instance for a different customer.
- **Sibling AI5R products** (Education OS, Manufacturing OS, Healthcare OS, Robotics OS, DreamPath — all named in `ADR-002`) — BRAIN, Capability, and Knowledge are AI5R-level peer assets specifically so that any future product can reuse them exactly as this specification does, without going through OSA or LTSA OS first.

---

## Open Questions (for a future Architecture Decision — not decided here)

1. PM/CM manufacturing: System A (Gateway/n8n, proven for Work Order/Maintenance History) or System B (`UMC-001`/`UMR-001`, proven for Pump)? (§3, §13; restates `MWO-LTSA-054`'s own still-open Question 1.)
2. One `maintenance_finding` table with a PM/CM discriminator, or two separate tables (`pm_record`/`cm_record`)? (§13.)
3. `recipe.json` — if System B is chosen for PM/CM, this reuses the v1 minimal schema `MWO-LTSA-050` WP-001 already established, extended with PM/CM's own `identity_key`/`relationship_keys` — not a new format.
4. Exact Organization Registry table names/shape for Legal Entity's integration point — not independently re-verified in producing this specification (§13).
5. Whether Inter-Entity Settlement (§4, §10) is its own manufactured canonical object or a computed/reporting-only view over `project_cost` + `customer_billing_record` — a Finance OS design decision, not resolved here.

---

This is a specification only. No code, schema, or BUILD-PACK was created. No `AI5R-SDK`, `PRODUCTS/LTSA-BRAIN`, `CORE-SERVICES`, or Runtime file was modified in producing it.

Stopping here, per instruction. Awaiting Chief Architect review and approval before any implementation MWO is scoped from this document.
