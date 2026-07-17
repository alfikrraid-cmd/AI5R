# MWO-ENT-003 — Enterprise Sprint 1 Architecture

Status: ARCHITECTURE ONLY — no implementation, no code, no SQL, no API. No file outside `ENGINEERING/MWO/` touched in producing this document.
Type: Manufacturing Work Order (Architecture / WP-000)
Role: Implementation Engineer, acting on Chief Enterprise Architect direction.
Architecture: FROZEN. Every Execution Package (EP) below is placed against objects and mechanisms already established by `ADR-001`–`004`, `UMC-001`/`UMR-001`, `MWO-ENT-001` (approved), and `MWO-ENT-002` (approved, the canonical Enterprise Object Model). None of it is reopened here.
Parent: `MWO-ENT-002-AI5R-Enterprise-Object-Model.md` (approved). Every Enterprise Object an EP below reads or writes is one already defined there — no new top-level object is introduced by this document.
Goal: Transform LTSA into AI5R Enterprise LTSA — the WhatsApp-native, dual-entity-billing, Owner-visible Enterprise LTSA described in `MWO-ENT-001`.
Scope: This document only. No `AI5R-SDK`, `PRODUCTS/LTSA-BRAIN`, `CORE-SERVICES`, or Runtime file is modified in producing it.

---

## Executive Summary, Including One Disclosed Discrepancy

Before anything else: this document's own repository check found the stated "LTSA Foundation" build-pack list does not match what actually exists on disk. `BP-001` through `BP-004` (Pump Database, API Contract, Pump Create Service, Core SDK) are confirmed real, matching `ROADMAP.md`'s own "Completed" section. `BP-005` is confirmed real but is **`BP-005-CUSTOMER-REGISTRY`**, not "Asset Registry." No `BP-006`, `BP-007-*` other than the already-existing `BP-007-AI5R-WORKFLOW-GENERATOR`, `BP-008`, or `BP-009` matching "Seal Registry," "PM Planner," "CM Work Order," or "LTSA Dashboard" exists anywhere in the repository (confirmed by direct search — no file, directory, or test path matches). The `67 tests passing` figure was not independently re-verified against these specific names, since the named artifacts do not exist to test.

**This does not block Sprint 1 design.** Every EP below is instead grounded in what this session has itself already directly verified as real and committed: the canonical `ltsa_pumps`/`seal_registry`/`work_order`/`maintenance_history` tables, `CORE-SERVICES/API`'s Pump/Work Order/Maintenance History Gateways, Role Manufacturing, Organization Registry, Maintenance Execution Runtime, Maintenance Command Center, Maintenance Intelligence Service, and Maintenance Copilot (`MWO-019`–`022`), `CORE-SERVICES/BACKEND-API` (`MWO-DEP-001`, which explicitly deferred WhatsApp/NLP routing to "a future Agent Layer" — exactly what `EP-003` now specifies), `PRODUCTS/LTSA-BRAIN/AI-ASSISTANT/maintenance_assistant.py` (the working BRAIN precedent), and the full 38-object Enterprise Object Model (`MWO-ENT-002`). Naming a Dependency below on a real, verified component rather than the stated-but-unverified `BP-005`–`009` list is a substitution made in the interest of accuracy, not a redesign of Sprint 1's goal.

**Sprint 1's own shape**, per the Chief Enterprise Architect's own EP list: a straight pipeline from raw WhatsApp identity (EP-001) through message receipt (EP-002) through AI understanding and LTSA action (EP-003) through customer-facing reporting (EP-004) through dual-entity billing (EP-005), observed end-to-end by one executive summary surface (EP-006). Each EP is scoped to reuse exactly the Enterprise Objects `MWO-ENT-002` already defines — no EP introduces a new object.

---

## EP-001 — Identity Registry

**Purpose:** Map WhatsApp Number → Employee → Role → Department → Area → Permission — the single resolution chain every other EP in this sprint depends on before it can trust who is speaking.

**Responsibilities:**
- Resolve an inbound phone number to exactly one Employee, or a structured "unresolved" result — never a silent default or a guess.
- Resolve that Employee's held Role(s), owning Department, and entity scope (`MWO-ENT-002` §25 — every Role except Owner is scoped to exactly one of Brand or OperatingCompany).
- Resolve the Employee's Area responsibility — which Area(s) this person is authorized to report on. **New relationship, not yet present in `MWO-ENT-002`'s own object list:** an Employee↔Area assignment. This is a new *relationship* between two already-canonical objects (Employee, Area), not a new object — consistent with "no redesign," since neither Employee nor Area itself changes shape.
- Resolve the effective Permission set (via Role → Permission, `MWO-ENT-002` §25/§34) so downstream EPs (especially EP-003) know what this Employee is authorized to trigger.
- Return a single, structured Identity bundle — never partial/ambiguous results silently passed downstream.

**Enterprise Objects:** Employee (§20), Role (§25), Department (§21), Area (§7), Permission (§34) — all read-only. Explicitly does **not** touch User (§24), since Engineers, this sprint's primary caller, structurally have no User account (`MWO-ENT-001` §6, `MWO-ENT-002` §24).

**Dependencies:** Organization Registry / Role Manufacturing (`CORE-SERVICES/API/{organization_registry,role_manufacturing}.py`, existing, reused unchanged — already the object `retrieve_role_artifact()` resolves against for Work Order's `assigned_to` today). No dependency on EP-002 or later — Identity Registry is a pure lookup service, callable independently of any specific channel.

**Inputs:** a phone number (string), and the object type context requesting resolution (initially only `WHATSAPP`/Engineer lookups; not channel-agnostic in this sprint).

**Outputs:** an Identity bundle `{ employee, roles[], department, areas[], permissions[] }`, or a structured `UNRESOLVED` result carrying the raw phone number for audit/follow-up, never an exception surfaced to a caller.

**Acceptance Criteria:**
- A known Engineer's phone number resolves to the correct Employee, Role(s), Department, Area(s), and Permission set, matching Organization Registry's own existing data.
- An unknown phone number returns `UNRESOLVED`, not a crash and not a default/guessed identity.
- Resolution has no WhatsApp, BRAIN, or network dependency — it is a pure data lookup, independently testable without any live channel.
- No User/login record is created, read, or required by this resolution — Engineers remain login-free per `MWO-ENT-001` §6.

**Future Expansion:** multi-role Employees with role-specific Area scopes; Area reassignment workflow; identity resolution for a future Customer Contact channel (`MWO-ENT-002` §26 Future Expansion), reusing this same chain shape.

---

## EP-002 — WhatsApp Capability

**Purpose:** Receive WhatsApp messages. Identify sender. Load identity. Forward to AI LTSA Operator. The concrete implementation of the Capability `ADR-003` already named, under its `Communication` group, and never built.

**Responsibilities:**
- Receive an inbound WhatsApp message (text or image) from the WhatsApp provider.
- Create or continue exactly one Conversation (`MWO-ENT-002` §36) per sender phone number.
- Call EP-001 to resolve sender identity; attach the resulting Identity bundle (or `UNRESOLVED`) to the Conversation.
- Forward the normalized message event to the Agent Layer (EP-003) — Capability's own governing rule (`ADR-003`: "BRAIN decides, Capability executes") means EP-002 **must not** itself decide what the message means or what to do about it.
- Expose an outbound send function other EPs (EP-003, EP-004) call to deliver a message/question/report back to a WhatsApp number — Capability executing an action decided elsewhere, never deciding on its own.

**Enterprise Objects:** Conversation (§36, created/continued), Employee (§20, read via EP-001), Notification (§35, when the outbound path is used to deliver one).

**Dependencies:** EP-001 (identity resolution, hard dependency — no message is forwarded to the Agent Layer without an identity-resolution attempt). Capability Runtime (`ADR-003`'s own dependency direction: `Products → Capability Runtime → Capability` — LTSA OS consumes this Capability through Capability Runtime, never directly). Must never depend on LTSA OS or any other Product (`ADR-003` Rule-001) — a WhatsApp Capability provider is reusable by any future AI5R product, not LTSA-private.

**Inputs:** raw inbound WhatsApp payload (sender number, message text/media); for outbound use, a `{ recipient phone number, message content }` pair from a calling EP.

**Outputs:** a normalized message event `{ conversation reference, identity bundle or UNRESOLVED, message content, timestamp }` handed to EP-003; a delivery confirmation/failure result for outbound sends.

**Acceptance Criteria:**
- Every inbound message resolves to exactly one Conversation, never creating a duplicate thread for the same ongoing exchange.
- Identity resolution (EP-001) is attempted before forwarding — an `UNRESOLVED` identity is still forwarded (as `UNRESOLVED`), never silently dropped.
- Contains zero business-decision logic (PM/CM classification, follow-up question wording, report drafting) — that is EP-003's exclusive responsibility, per `ADR-003`'s own separation.
- Provider-replaceable without changing LTSA OS or any EP that calls it (`ADR-003` Rule-004) — the interface this Capability exposes is stable regardless of which WhatsApp provider (Business API, BSP, etc.) sits behind it.

**Future Expansion:** additional Communication Capability providers (Email, Telegram, Slack, Discord — all already named by `ADR-003`, none built), reusing this same Capability Runtime seam; voice note ingestion (`MWO-ENT-001` §15).

---

## EP-003 — AI LTSA Operator

**Purpose:** The Engineer's only interface to LTSA OS. Understands Employee, Department, Area, the current Conversation, and LTSA objects; decides which LTSA capability to call. The Agent Layer `MWO-DEP-001`'s own commit note already named and explicitly deferred ("NLP/intent routing belongs to a future Agent Layer, not this Backend API").

**Responsibilities:**
- Consume the normalized message event and Identity bundle from EP-002.
- Maintain Conversation Memory (`MWO-ENT-002` §37) across a multi-turn exchange — which fields are already collected, which remain missing.
- Call BRAIN (Observation → Understanding, `ADR-002`; precedent: `maintenance_assistant.py`'s `EnterpriseCognitivePipeline` call) to extract structured candidate fields from free text.
- Classify the resulting Inspection (`MWO-ENT-002` §12) as PM or CM, or ask which, if genuinely ambiguous.
- Compose and send (via EP-002) follow-up questions for missing required fields (Tag Number, PM or CM, Pressure, Temperature, Leakage, Running Hour, Equipment Condition, Before/After Photos) — asking only what is actually missing, never re-asking an already-known field.
- Resolve Equipment identity (tag_number → Pump/Equipment, `UMC-001` Stage 4 — the exact pattern `PumpIdentityResolver`, `MWO-LTSA-050` WP-001, already proves).
- On completion, invoke the appropriate LTSA capability: existing query capabilities (Maintenance Copilot / Intelligence Service, already committed, unchanged) for questions about existing data; existing or new write capabilities (Maintenance Execution Runtime / Gateways, or a future Manufacturing station per `UMC-001`/`UMR-001` — the System A/System B choice `MWO-ENT-002` §13 left open, not decided by this sprint either) for producing a PM or CM record.
- Notify the Supervisor (via Notification, `MWO-ENT-002` §35) on every completed PM/CM.

**Enterprise Objects:** Conversation (§36), Conversation Memory (§37), Inspection (§12), PM (§13), CM (§14), Equipment/Pump/Seal/Asset (§8–11, read via Identity Resolution), Work Order (§23, optional linkage), Notification (§35, written on completion).

**Dependencies:** EP-002 (message in/out, hard dependency — the Operator has no channel of its own). EP-001 (via EP-002's own identity attachment — the Operator trusts, does not re-resolve, the Identity bundle EP-002 already attached). BRAIN (`ADR-002`, existing peer asset). Existing `CORE-SERVICES/API` query/execution layer (Maintenance Copilot, Maintenance Intelligence Service, Maintenance Execution Runtime, Pump/Work Order/Maintenance History Gateways) as the concrete "LTSA capabilities" it decides among.

**Inputs:** normalized message event + Identity bundle (from EP-002); prior Conversation Memory state, if the Conversation is already in progress.

**Outputs:** outbound follow-up questions (via EP-002); an updated Conversation Memory; on completion, a manufactured PM or CM record (§13/§14) and its resulting Maintenance History entry (§15); a Supervisor Notification.

**Acceptance Criteria:**
- Given a complete engineer report (the brief's own example: *"PUMP-001 selesai. Mechanical seal diganti. Bearing masih bagus. Pressure 4.8 bar."*), correctly classifies CM and produces a complete, valid CM record with no unnecessary follow-up question.
- Given an incomplete report, asks only for the fields genuinely missing, never fields already stated.
- Never resolves Equipment identity by guessing — an unresolved tag number is a follow-up question, not an assumed match.
- Never itself sends a WhatsApp message directly — every outbound message is delegated to EP-002 (`ADR-003`'s "BRAIN decides, Capability executes" honored structurally, not just by convention).
- Every completed PM/CM triggers exactly one Supervisor Notification.

**Future Expansion:** voice note understanding (`MWO-ENT-001` §15); multi-language extraction; Failure Pattern (`MWO-ENT-002` §27) detection triggered from within the Operator's own completion flow, once the underlying `ADR-002` Learning→Knowledge loop exists.

---

## EP-004 — Technical Report Generator

**Purpose:** Generate LTSA reports automatically — the customer-facing aggregation of PM/CM/Maintenance History that EP-003 produces.

**Responsibilities:**
- Aggregate one or more approved PM/CM records (and their resulting Maintenance History entries) for a Work Order or reporting period.
- Draft a narrative Technical Report, BRAIN-assisted (extends the existing `maintenance_assistant.get_maintenance_recommendation()` narrative-generation pattern — not a new NLG mechanism).
- Route the draft to Supervisor Review before any customer release — a structural gate, never optional or bypassable.
- On approval, manufacture the final Technical Report, fixed `issuing_entity = Brand (PT Tommy Adji Prasetyo)` — never selectable, never CV Razzan (`MWO-ENT-002` §16).
- Deliver the approved report to the Customer Contact via WhatsApp Capability (EP-002) or portal-equivalent channel.
- Signal EP-005 (Billing Bridge) when the underlying work is chargeable.

**Enterprise Objects:** Technical Report (§16, manufactured), PM (§13), CM (§14), Maintenance History (§15, all read as source material), Work Order (§23), Brand (§1, fixed issuer), Employee (§20, the approving Supervisor), Customer Contact (§26, delivery target).

**Dependencies:** EP-003 (source PM/CM records — hard dependency, a Technical Report is never authored from anything but already-completed, approved PM/CM). EP-002 (delivery channel for the approved report, and for any Supervisor-facing clarification round-trip, reused not duplicated). Existing Maintenance Command Center / Intelligence Service (`CORE-SERVICES/API`, aggregation source for "which PM/CM belong to this Work Order/period," already committed).

**Inputs:** a Work Order reference or reporting-period boundary; the set of approved PM/CM records within it.

**Outputs:** a DRAFT Technical Report → (Supervisor edits/approves) → APPROVED → SENT_TO_CUSTOMER Technical Report; a chargeable-work signal to EP-005.

**Acceptance Criteria:**
- No Technical Report reaches SENT_TO_CUSTOMER without a recorded Supervisor approval (§16 Business Rules).
- Every Technical Report's `issuing_entity` is Brand = PT Tommy Adji Prasetyo, with zero code path that could set it to CV Razzan.
- Report content is fully traceable back to its source PM/CM/Maintenance History record ids — no report exists whose source material cannot be re-derived.
- Report generation never blocks on, or requires, Billing/Invoice data existing yet — a report can be approved and sent before any billing determination is made (§18 Billing is downstream, not a prerequisite).

**Future Expansion:** scheduled/periodic report generation (monthly summaries, not only Work-Order-triggered); multi-language reports; richer photo/media layout drawn from the Engineering Media Acquisition objects already attached to source PM/CM records.

---

## EP-005 — Billing Bridge

**Purpose:** Create billing data for PT Tommy Adji Prasetyo. Operational work belongs to CV Razzan. Customer only ever sees PT Tommy. Payment is received by PT Tommy. The concrete implementation of the dual-entity Billing Workflow `MWO-ENT-001` §10 and `MWO-ENT-002` §17–19 already specified.

**Responsibilities:**
- On a chargeable-work signal from EP-004, determine the billable amount for the underlying Technical Report/Work Order, checked against the governing Contract's terms.
- Manufacture a Billing record (`MWO-ENT-002` §17) — the internal, pre-customer-facing determination.
- On confirmation, manufacture an Invoice (§18), fixed `issuing_entity = Brand (PT Tommy Adji Prasetyo)`.
- Deliver the Invoice to the Customer Contact (via EP-002/portal-equivalent), never exposing any CV Razzan cost detail in that delivery.
- On Payment receipt (§19), record it under Brand = PT Tommy Adji Prasetyo.
- Create an Inter-Entity Settlement entry crediting CV Razzan's own Project Cost Tracking for the operational cost already incurred on the originating Work Order/Project — the mechanism that reconciles the two entities' books without CV Razzan ever billing the customer directly (`MWO-ENT-001` §10, `MWO-ENT-002` §22 Business Rules).

**Enterprise Objects:** Billing (§17), Invoice (§18), Payment (§19), Contract (§4), Project (§22), Brand (§1), OperatingCompany (§2), Technical Report (§16, the trigger).

**Dependencies:** EP-004 (chargeable-work signal — hard dependency, no Billing exists without a source Technical Report). Contract (rate/terms check, existing object, no new mechanism). Project (cost attribution for Inter-Entity Settlement).

**Inputs:** a chargeable Technical Report reference; the governing Contract; the originating Project/Work Order's accumulated cost.

**Outputs:** Billing (DRAFT → CONFIRMED → INVOICED) → Invoice (DRAFT → SENT → PAID) → Payment (RECEIVED → RECONCILED) → an Inter-Entity Settlement entry against Project.

**Acceptance Criteria:**
- `issuing_entity` on every Billing/Invoice/Payment record produced by this EP is Brand = PT Tommy Adji Prasetyo — structurally fixed, with no field or role able to set it to CV Razzan (`MWO-ENT-002` §1 rule, enforced here concretely).
- No CV Razzan cost breakdown (Expense, Purchase, Payroll, internal labor rate) is ever present in the Invoice or Payment record's own customer-facing fields.
- Every Payment produces exactly one Inter-Entity Settlement entry, correctly attributed to the originating Project.
- A Billing record referencing an expired or inactive Contract is rejected, not silently processed (`MWO-ENT-002` §4 Business Rules).

**Future Expansion:** multi-currency invoicing; partial-payment schedules; automated bank-feed reconciliation for Payment records (`MWO-ENT-002` §19 Future Expansion).

---

## EP-006 — Owner Dashboard

**Purpose:** An executive dashboard. Only summarized information. No operational details. The Owner's own cross-entity view (`MWO-ENT-001` §12, `MWO-ENT-002` §25 — Owner is the sole Role scoped to both Brand and OperatingCompany).

**Responsibilities:**
- Aggregate, read-only, across LTSA OS and Finance OS objects into one executive summary.
- Present exactly the categories `MWO-ENT-001` §12 already specified: Today's Inspection, PM Completed, CM Completed, Open Findings, Critical Equipment, Assets Requiring Attention, Technical Reports Waiting Approval, Billing Waiting, and a reconciled Finance summary (CV Razzan cost side + PT Tommy Adji Prasetyo revenue side, via Inter-Entity Settlement).
- Enforce summarization as a structural property, not a display-layer filter: this EP never exposes an individual Engineer's raw WhatsApp Conversation, an individual Employee's Payroll amount, or a line-item Expense/Purchase detail — those remain Supervisor/Finance Officer/HR Officer-only, per each object's own Role scope (`MWO-ENT-002` §6/§25).
- Restrict the cross-entity (both Brand and OperatingCompany) view to the Owner Role alone; every other Role sees only its own entity's summary, if any.

**Enterprise Objects:** read-only across Work Order (§23), PM/CM (§13/14), Technical Report (§16), Billing/Invoice/Payment (§17–19), Employee/Department (§20/21, counts only), Failure Pattern/Knowledge Record (§27/38, trend indicators once they exist). Writes nothing — no object above is created or mutated by this EP.

**Dependencies:** extends `maintenance_command_center.get_maintenance_command_center()` (`CORE-SERVICES/API`, already committed — its existing return shape, `summary`/`recent_work_orders`/`recent_maintenance`/`organization_summary`, is the direct precedent this EP adds PM/CM-classification, Technical Report, and Billing status onto). EP-004 (Technical Report status feed). EP-005 (Billing/Invoice/Payment status feed, and the Inter-Entity Settlement reconciliation for the Finance summary).

**Inputs:** aggregate read queries across the objects above; the requesting User's Role (to gate cross-entity visibility).

**Outputs:** a single, read-only summarized view — no object created, no object mutated, matching the existing Command Center's own already-committed design intent ("manufactures nothing, persists nothing, modifies nothing").

**Acceptance Criteria:**
- No response from this EP ever includes a single Engineer's raw Conversation content, a single Employee's Payroll figure, or a line-item Expense/Purchase record — every figure is a count, sum, or status, never a raw record (§Purpose, explicit "No operational details").
- Only a User holding the Owner Role receives the combined CV Razzan + PT Tommy Adji Prasetyo Finance summary; every other Role's view, if any, is scoped to its own entity only.
- This EP performs zero writes under any code path — verified the same way the existing Command Center already documents itself.
- Every summarized figure is independently reproducible from the underlying objects it aggregates (no invented/estimated numbers) — matching this EP's own existing precedent, which already refuses to invent an "overdue work orders" figure it cannot derive from real data rather than fabricate one.

**Future Expansion:** trend charts over time; delegated, permission-scoped drill-down for future executive roles beyond Owner; Failure Pattern/Knowledge Record trend surfacing once `ADR-002`'s Learning→Knowledge loop is implemented.

---

## Sprint 1 Dependency Graph

```
EP-001 Identity Registry
   │  (identity lookup, no channel dependency)
   ▼
EP-002 WhatsApp Capability  ──────────────┐
   │  (message in/out)                    │ (outbound send,
   ▼                                       │  reused by EP-004)
EP-003 AI LTSA Operator                    │
   │  (completed PM/CM)                    │
   ▼                                       │
EP-004 Technical Report Generator ─────────┘
   │  (chargeable-work signal)
   ▼
EP-005 Billing Bridge
   │
   ▼
(Payment / Inter-Entity Settlement)

EP-006 Owner Dashboard
   reads: EP-003's PM/CM/Work Order state, EP-004's Technical
   Report status, EP-005's Billing/Invoice/Payment status —
   writes nothing, depends on all four for its own read feed,
   none of them depend on it.
```

**Build order implication (architecture only — no implementation sequencing decided here beyond what this graph structurally requires):** EP-001 has no upstream dependency and is buildable first. EP-002 requires EP-001. EP-003 requires EP-002 (and therefore EP-001). EP-004 requires EP-003. EP-005 requires EP-004. EP-006 requires read access to EP-003/EP-004/EP-005's outputs but may be scaffolded early against the existing, already-committed Command Center and extended incrementally as each upstream EP lands.

---

## Sprint 1 Enterprise Object Coverage

Every object touched by this sprint, cross-referenced to `MWO-ENT-002`:

| Object | Touched by | New relationship introduced this sprint |
|---|---|---|
| Employee, Role, Department, Permission | EP-001 | — |
| Area | EP-001 | Employee↔Area responsibility assignment (new relationship, not a new object) |
| Conversation, Conversation Memory | EP-002, EP-003 | — |
| Inspection, PM, CM | EP-003 | — |
| Equipment, Pump, Seal, Asset | EP-003 (Identity Resolution) | — |
| Work Order | EP-003, EP-004 | — |
| Maintenance History | EP-003 (produced) | — |
| Notification | EP-003 (Supervisor), EP-004/EP-005 (implicit, via delivery) | — |
| Technical Report | EP-004 | — |
| Brand | EP-004, EP-005 | — |
| Billing, Invoice, Payment | EP-005 | — |
| Contract, Project | EP-005 | — |
| OperatingCompany | EP-005 (Inter-Entity Settlement) | — |
| Customer Contact | EP-004, EP-005 (delivery target) | — |
| User | *not touched* | Engineers remain login-free throughout this sprint, by design |
| Failure Pattern, Knowledge Record | *not touched this sprint* | named as EP-003/EP-006 Future Expansion only |

No object outside `MWO-ENT-002`'s existing 38 is introduced. The one new item (Employee↔Area responsibility) is a relationship between two already-canonical objects, not a 39th object.

---

This is architecture only. No implementation, code, SQL, or API was written. No `AI5R-SDK`, `PRODUCTS/LTSA-BRAIN`, or `CORE-SERVICES` file was modified in producing it.

Stop.
