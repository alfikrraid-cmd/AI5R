# MWO-LTSA-068 — CV Razzan Enterprise Preparation

Status: **COMPLETED**
Type: Manufacturing Work Order (Discovery — reclassified by Product Owner refinement from Implementation to Discovery-only; see below)
Role: Senior Enterprise Consultant (per Product Owner direction, not Implementation Engineer, for this MWO's deliverable)
Architecture: FROZEN — this MWO must not introduce architecture changes or duplicate engines.
Predecessor: `MWO-LTSA-067-Demo-Candidate.md` (CLOSED — reviewed and approved by Product Owner, 2026-07-20).

Note: this MWO supersedes a cancelled draft of the same number, `MWO-LTSA-068-Repository-Governance-Synchronization.md` (discarded before implementation or approval — never committed).

---

## Goal

Prepare LTSA Demo v1 for real operation at CV Razzan Teknik Mandiri.

## Scope

- Enterprise master data
- Customer registry
- Project registry
- Asset hierarchy
- Workforce registry
- Real deployment preparation

## Rules

- Reuse existing LTSA architecture.
- No duplicate engines.
- No Finance.
- No HR.
- No Inventory.
- No Purchasing.
- No Accounting.

## Definition of Done

- LTSA can receive real CV Razzan operational data.
- Existing demo capabilities remain functional.
- Clear migration path from sample data to production data.

---

## Product Owner Refinement — Discovery Reframing

Received before any deliverable was produced: **this MWO is NOT an implementation MWO.** Role: Senior Enterprise Consultant, not a software engineer — think from the business first, the software must follow the business. Objective: understand how CV Razzan Teknik Mandiri actually operates before proposing any system changes. Seven deliverables requested: Business Model, Business Process Map, Organization Map, Enterprise Object Discovery, Operational Workflow, Gap Analysis, Deployment Roadmap. Rules: discovery only, no implementation, no UI, no backend, no database, no architecture redesign, do not invent workflows that cannot be justified, and — the rule this report follows most deliberately — **if information about CV Razzan is missing, explicitly identify the unknowns instead of guessing.** Success: a deployment blueprint answering "What must happen before CV Razzan can operate entirely on AI5R?"

## A Note on Method — Grounding, Not Guessing

Before drafting a single section below, this repository was searched for existing CV Razzan material rather than assuming none existed. **A substantial amount already exists**, and this report is built on it rather than around it:

- `PRODUCTS/LTSA-BRAIN/product.manifest.json` names CV Razzan Teknik Mandiri as the customer of `MO-001` ("OSA Maintenance v0.1").
- `MANUFACTURING/MO-001/*` (Specification, Deployment Guide, Demo Script, Manufacturing Report) is a real manufacturing order built for CV Razzan, with a working demo script referencing "Boiler House," feedwater tanks, and soot blowers.
- `ENGINEERING/MWO/MWO-ENT-001-AI5R-Enterprise-OS-v1-Specification.md` (approved, 436 lines) is an **already-approved** enterprise architecture specification that names CV Razzan Teknik Mandiri explicitly, including a two-legal-entity business model, a named role/access table, and full WhatsApp/PM/CM/Billing/Technical Report workflow diagrams.
- `ENGINEERING/MWO/MWO-ENT-002-AI5R-Enterprise-Object-Model.md` (approved, 807 lines) is an already-approved 38-object Enterprise Object Model built directly on top of MWO-ENT-001.
- `ENGINEERING/MWO/MWO-ENT-003-Enterprise-Sprint-1-Architecture.md` (262 lines) already breaks a first implementation sprint into six Execution Packages.
- `AI5R-STUDIO/dashboard/src/modules/ltsa/data/samplePumps.js` (the actual LTSA Demo v1 sample data) independently corroborates the same domain — "Boiler Feedwater Pump," "Boiler House" — without having been written with CV Razzan's name anywhere in it.

**Every fact below is labeled by provenance:**

- **[CONFIRMED]** — stated directly in an existing, approved repository document, cited by file.
- **[INFERRED]** — a reasonable conclusion drawn from confirmed facts (e.g., domain inference from "Boiler House"/"Soot Blower" sample data), not itself stated anywhere, and not to be treated as fact until validated.
- **[UNKNOWN]** — no repository evidence exists; this requires a real conversation with CV Razzan, not an assumption. Per the explicit rule above, these are named, not silently filled in.

One structural tension is disclosed up front rather than smoothed over: **this MWO's own Rules** ("No Finance. No HR. No Inventory. No Purchasing. No Accounting.") **scope out exactly the subsystems MWO-ENT-001 already designed** (Finance OS, HR OS) to carry Quotation, Invoice, Payment, Billing, Employee, Payroll, and more. This report treats that as a real, intentional boundary — LTSA Demo v1's own deployment track stops at the edge of Finance OS/HR OS, which remain a separate, already-specified, not-yet-built workstream — not a contradiction to silently resolve either way.

---

## 1. Business Model

**What does CV Razzan sell?** **[INFERRED, from converging evidence]** Industrial rotating-equipment maintenance and technical services — inspection, preventive maintenance (PM), and corrective maintenance (CM) for pumps, mechanical seals, and boiler-area equipment (soot blowers, tanks), most plausibly serving power-generation or heavy-process-industry plants. Evidence: the Enterprise Object Model's own registries are Pump, Seal, Asset, Soot Blower — nothing resembling a manufacturing, trading, or construction object exists anywhere; `MO-001`'s demo script exercises a "Feedwater Tank" and a "Retractable Blower Unit" in a "Boiler House" (`MANUFACTURING/MO-001/DEMO.md`); LTSA Demo v1's own sample data independently uses "Boiler Feedwater Pump," "Boiler House," John Crane/Sulzer/Flowserve-branded rotating equipment (`samplePumps.js`) — written separately, without reference to CV Razzan, yet landing on the same domain. **[UNKNOWN]** Whether CV Razzan also does new-equipment installation/commissioning (as opposed to maintaining installed equipment only), and whether it is single-site-service or multi-plant.

**Two-legal-entity structure — [CONFIRMED, `MWO-ENT-001-AI5R-Enterprise-OS-v1-Specification.md:22,54-59`]:** CV Razzan Teknik Mandiri is the *internal, operating* entity — it employs the people, incurs the cost, does the actual work — and is **never shown to a customer, in any interface, document, or message** (a structural rule, not a display filter: `MWO-ENT-001:170`). Every customer-facing artifact (Quotation, Technical Report, Invoice, WhatsApp message) is issued under a second, distinct legal entity, **PT Tommy Adji Prasetyo**, the customer-facing brand. This is not a minor naming detail — it means the correct answer to "who is CV Razzan's customer" is really "who is PT Tommy Adji Prasetyo's customer," and any object modeled as `owning_entity` (Work Order, Maintenance History, PM/CM, internal cost) belongs to CV Razzan, while anything `issuing_entity` (Technical Report, Quotation, Invoice) belongs to PT Tommy Adji Prasetyo, fixed by rule, never chosen per-document.

**Who are the customers?** **[UNKNOWN]** No customer list, industry sector, or account size exists anywhere in this repository. `MO-001`'s only registered customer is a synthetic demo record (`RAZZAN-001`, the company itself, used as its own test fixture — not a real client). The Enterprise Object Model's `Customer` object (`MWO-ENT-002 §3`) has a lifecycle `PROSPECT → ACTIVE → (future) INACTIVE/CHURNED` but zero real instances anywhere in the repository.

**Revenue streams.** **[INFERRED from the already-approved Billing Workflow, `MWO-ENT-001 §10`]** Service revenue, billed per completed, Supervisor-approved Technical Report: either (a) new/one-off work quoted in advance (Quotation → accepted → work performed → Invoice), or (b) work performed under an existing contract/agreement (work performed → Invoice directly, no separate Quotation step). **[UNKNOWN]** Whether CV Razzan also resells or marks up spare parts (no Inventory subsystem exists anywhere in the repository — `MWO-ENT-001 §15` names Inventory explicitly as future/not-yet-built, and this MWO's own Rules exclude it), whether pricing is time-and-materials, fixed-fee per Work Order, or a retainer/contract-based model, and what the actual price list or rate card looks like.

**Types of projects.** **[CONFIRMED pattern, `MWO-ENT-001 §8-9`]** Two categories already have full workflow specifications: **Preventive Maintenance (PM)** — scheduled, planned inspection/service; and **Corrective Maintenance (CM)** — reactive, triggered by a reported failure (the spec's own worked example: *"PUMP-001 selesai. Mechanical seal diganti. Bearing masih bagus. Pressure 4.8 bar."*, `MWO-ENT-001:~L?`, an Indonesian-language field WhatsApp report). **[UNKNOWN]** Whether CV Razzan also runs larger, multi-Work-Order **Projects** in the everyday sense (e.g., a plant turnaround, a multi-week overhaul) — the Enterprise Object Model does name a `Project` object (`MWO-ENT-002 §22`, Finance-OS-owned, "the reconciliation key... a Project may span many Work Orders") but it is spec-only, never built, and this MWO's own Deliverables explicitly ask for a "Project registry," suggesting the business reality is not yet captured even at the object-catalog level.

**How projects start.** Two distinct, both-plausible entry points exist in the source material, and neither has been reconciled with the other before now:
1. **Reactive/field-triggered** — **[CONFIRMED, fully spec'd]** An Engineer, in the field, reports a finding via WhatsApp (no login, no form — `MWO-ENT-001 §6-7`); the AI LTSA Operator classifies it PM or CM and a Work Order/Inspection record is created directly, no prior sales step.
2. **Sales-led/new-business** — **[REQUESTED BY THIS MWO, NOT YET MODELED ANYWHERE]** Lead → Quotation → PO/SPK → Project, per this MWO's own Deliverables framing. No object named "Lead," "SPK," or "PO" (as a customer-issued work-authorization document, distinct from Finance OS's internal `Purchase`) exists anywhere in `MWO-ENT-002`'s 38-object catalog, nor in any schema, workflow, or test in the repository (confirmed by repository-wide search). This is a genuine, confirmed gap, not an oversight in this report — see Gap Analysis §6.

**How projects finish.** **[CONFIRMED, `MWO-ENT-001 §11`]** PM/CM records aggregate into a Technical Report, drafted by AI, reviewed and approved by a Supervisor, sent to the customer branded as PT Tommy Adji Prasetyo, and — if billable — feeds the Billing Workflow (§10) through to Invoice and Payment. This MWO's own Scope explicitly lists Invoice as "reference only," consistent with the Rules excluding Finance.

**Success criteria.** **[UNKNOWN]** No stated KPI, SLA, or definition of a successful engagement exists anywhere in the repository — not turnaround time, not first-time-fix rate, not customer satisfaction, not repeat-business rate, not equipment uptime improvement. This is a direct question for CV Razzan leadership, not something inferable from existing artifacts.

---

## 2. Business Process Map

**[CONFIRMED, back half]** / **[GAP, front half]** — the process below is presented as one continuous flow, but the seam between "confirmed, already spec'd" and "requested here, not modeled anywhere yet" is marked explicitly, because collapsing it into one uniform-looking diagram would misrepresent how much of this is actually known.

```
Prospect / Lead                                    [UNMODELED — no object, no workflow, anywhere]
     ↓  (decision: is this a real opportunity?)
Meeting / Site Survey                               [UNMODELED]
     ↓
Quotation                                           [named in MWO-ENT-001 narrative + MWO-ENT-002
     ↓                                                Finance OS catalog; ZERO schema/workflow exists]
Negotiation                                          [UNMODELED]
     ↓  (decision: accepted? — if not, Lead closes lost, no further object created)
PO / SPK  (customer's formal work authorization)     [UNMODELED — not a single mention anywhere in
     ↓                                                the repository outside this MWO's own request]
════════════════════ everything above this line is a confirmed, named gap ════════════════════
Project                                              [named object, MWO-ENT-002 §22 — spec only]
     ↓
Work Order (LTSA OS, reused unchanged: `work_order` table)
     ↓  (decision: PM — scheduled — or CM — reactive? Inspection object classifies which, 1:1)
Engineer Assignment  (via Role → Employee, WhatsApp-only channel, no login)
     ↓
Maintenance execution (PM or CM record — AI-drafted from field data, Supervisor-gated later)
     ↓  (decision: does this require Supervisor escalation now, or only at report time? — not
     ↓   specified; assumed report-time only, per MWO-ENT-001's own workflow diagram)
Service Report → here called "Technical Report"      [CONFIRMED terminology: this MWO's Deliverables
     ↓                                                 use "Service Report"; the approved spec uses
     ↓                                                 "Technical Report" for the identical artifact —
     ↓                                                 reconciled here as the same object, two names;
     ↓                                                 see Enterprise Object Discovery §4 for the
     ↓                                                 disambiguation]
     ↓  (decision: Supervisor approves, or sends back for revision)
Customer Approval
     ↓  (decision: billable, or warranty/goodwill work? — not specified anywhere; assumed billable
     ↓   by default per the Billing Workflow's own framing)
Invoice  (reference only, per this MWO's Scope — Finance OS territory, out of this MWO's Rules)
     ↓
Payment  (out of this MWO's Rules entirely — Finance OS)
```

**Decision points, named explicitly (per the Rules — none invented beyond what the source material supports):**

| Decision | Where | Basis |
|---|---|---|
| Is this a real sales opportunity? | Lead → Meeting | **[UNKNOWN]** no qualification criteria exist anywhere |
| Accept the Quotation? | Negotiation → PO/SPK | **[UNKNOWN]** — if declined, presumably the Lead/opportunity closes; not modeled |
| PM or CM? | Inspection classification | **[CONFIRMED]** `Inspection.status: IN_PROGRESS → CLASSIFIED → COMPLETED`, `MWO-ENT-002 §12` |
| Which Engineer? | Assignment | **[CONFIRMED]** resolved via Role Manufacturing (`retrieve_role_artifact()`), not a free assignment — `MWO-ENT-002 §23` |
| Approve or revise the Technical Report? | Supervisor Review | **[CONFIRMED]** `DRAFT → SUPERVISOR_REVIEW → APPROVED → SENT_TO_CUSTOMER`, `MWO-ENT-002 §16` |
| Billable or not? | Post-approval | **[UNKNOWN]** no rule found anywhere distinguishing billable from warranty/goodwill work |

---

## 3. Organization Map

This MWO's Deliverables ask for a specific role set: **Director, Project Manager, Supervisor, Engineer, Technician, Administration.** The already-**approved** Enterprise OS specification (`MWO-ENT-001 §6`) independently defines a *different* role set for the same company: **Owner, Supervisor, Admin, Engineer, Finance Officer, HR Officer.** These do not fully overlap, and reconciling them is itself a finding, not something to paper over:

| Requested here | Closest match in `MWO-ENT-001` | Match quality |
|---|---|---|
| Director | **Owner** (the only role with cross-entity, both-legal-entities visibility) | **[UNKNOWN]** whether "Director" and the spec's "Owner" are the same person/role under two names, or genuinely distinct — a real, structural business-title question |
| Project Manager | *(no equivalent role exists in the approved spec)* | **[GAP]** — either PM-level coordination is currently done by the Supervisor or Owner informally, or this is a role the business has that the spec never captured |
| Supervisor | Supervisor (exact match) | Confirmed |
| Engineer | Engineer (exact match, but see constraint below) | Confirmed, with a hard constraint attached |
| Technician | *(no equivalent — "Engineer" is the spec's only field-work role)* | **[UNKNOWN]** whether Technician is a distinct, junior field role under Engineer, or another name for the same thing |
| Administration | Admin (very likely the same role, different capitalization/phrasing) | Likely match, treated as equivalent below |

For each role below: Responsibilities / Inputs / Outputs / Decisions. Where the role has a **[CONFIRMED]** spec entry, that is used directly; where it does not, the entry is marked **[INFERRED]** or **[UNKNOWN]** rather than invented wholesale.

**Director** — **[UNKNOWN / mapped to Owner, tentatively]**
- Responsibilities: cross-entity oversight (both CV Razzan's internal operations and PT Tommy Adji Prasetyo's customer-facing business) — the only role the approved spec gives this scope (`MWO-ENT-001:167,354-362`).
- Inputs: Owner Dashboard — today's inspections, PM/CM completed, open findings, critical equipment, assets requiring attention, Technical Reports waiting approval, billing waiting, finance summary (`MWO-ENT-001:355-362`).
- Outputs: **[UNKNOWN]** — no decision/approval authority is assigned to Owner anywhere in the spec beyond visibility; whether Director actually approves anything (vs. Supervisor doing all approvals) is unconfirmed.
- Decisions: **[UNKNOWN]**.

**Project Manager** — **[UNKNOWN — no confirmed basis at all]**
- Responsibilities, Inputs, Outputs, Decisions: none of these can be stated from repository evidence. This is the single largest organizational unknown in this report. If CV Razzan genuinely has a Project Manager function, it is not reflected in the only approved organizational specification that exists.

**Supervisor** — **[CONFIRMED, `MWO-ENT-001:162-163`, `MWO-ENT-002 §16`]**
- Responsibilities: reviews AI-drafted PM/CM records and Technical Reports before customer release; the sole approval gate between field work and the customer.
- Inputs: AI-drafted PM/CM records (from Engineer WhatsApp reports, via the AI LTSA Operator); AI-drafted Technical Report narrative.
- Outputs: approved (or sent-back-for-revision) PM/CM record; approved Technical Report, which then becomes customer-visible.
- Decisions: approve vs. revise, at two separate gates (PM/CM record; Technical Report).

**Engineer** — **[CONFIRMED, `MWO-ENT-001 §6-7`, `MWO-ENT-002 §28`]**
- Responsibilities: field inspection and maintenance execution (both PM and CM).
- Inputs: Work Order assignment (via Role resolution, not a free pick); a structured set of follow-up questions from the AI LTSA Operator when a field report is missing required data (tag number, PM or CM, pressure, temperature, leakage, running hours, condition, before/after photos — `MWO-ENT-001:~L200s`).
- Outputs: a free-text (Indonesian-language, per the spec's own worked example) WhatsApp report of work performed.
- Decisions: none formally — the Engineer reports; the AI LTSA Operator classifies; the Supervisor approves. A hard structural constraint, not incidental: **Engineers have no login, no dashboard, no mobile app — WhatsApp only, identified purely by phone number** (`MWO-ENT-001:161`). This is a deliberate business decision already made, not a gap.

**Technician** — **[UNKNOWN]**
- No repository evidence distinguishes a "Technician" from "Engineer." **[INFERRED, weakly]** In many Indonesian industrial-service organizations, "Teknisi" (Technician) is a junior/assistant field role reporting to an "Engineer" (more senior, may hold a formal engineering qualification) — but this is an industry-pattern guess, not a CV Razzan-specific fact, and is flagged as exactly that rather than asserted.

**Administration** — **[LIKELY match to Admin, `MWO-ENT-001:163`]**
- Responsibilities: manages Work Orders, Assets, org structure (per the spec's Admin role).
- Inputs: raw Work Order/Asset data entry needs (e.g., registering a new pump, correcting an assignment).
- Outputs: maintained Work Order/Asset/org records.
- Decisions: operational/data-entry level, not approval-level (Supervisor holds the approval gate, not Admin).

---

## 4. Enterprise Object Discovery

Every object this MWO's Deliverables name, cross-referenced against the already-approved 38-object Enterprise Object Model (`MWO-ENT-002`) and against what LTSA Demo v1 (the actual React dashboard, `AI5R-STUDIO/dashboard`) implements today.

| Object (as named in this MWO) | Status in `MWO-ENT-002` | Status in LTSA Demo v1 (frontend) | Status in LTSA-BRAIN backend |
|---|---|---|---|
| Customer | **[CONFIRMED]** §3, Core, Finance-OS-owned/LTSA-consumed | **Absent.** No Customer concept exists anywhere in the dashboard UI or sample data (confirmed: `sampleWorkOrders.js` has no customer field at all) | `customer_registry` table + `BUILD-PACKS/BP-005` exist, but only as stubs — no real query logic (`product.manifest.json`) |
| Project | **[CONFIRMED]** §22, Core, Finance-OS-owned | Absent | Spec-only, no schema, no build pack |
| Contract | **[CONFIRMED]** §4, Core, Finance OS | Absent | Spec-only |
| PO / SPK | **Absent from the 38-object catalog entirely** | Absent | Absent — zero mentions anywhere in the repository outside this MWO's own text |
| Site | **[CONFIRMED]** §5, closes a disclosed gap ("no location hierarchy exists above `asset_code`/`asset_type`") | Absent (dashboard uses a flat `area` string field only) | Spec-only |
| Area | **[CONFIRMED]** §7 — matches `ltsa_pumps.area` | **Present** (`samplePumps.js: area`) | **Present**, real column |
| Equipment | **[CONFIRMED]** §8, new supertype closing a disclosed "no common supertype" gap | Absent as a concept; the dashboard has Pump as its only equipment type wired into navigation | Four separate registries (pump/seal/asset/soot_blower), no common supertype table (disclosed constraint, `MO-001-SPECIFICATION.md §2`) |
| Pump | **[CONFIRMED]** §10, reuses `ltsa_pumps` unchanged | **Present, fully built** — the most mature module in the dashboard | **Present**, canonical, partially real (create/detail real, list/update/delete stubs) |
| Motor | **Not a named object anywhere** | Absent — no motor field on Pump or elsewhere | Absent |
| Seal | **[CONFIRMED]** §11, reuses `seal_registry` unchanged | **Present in code** (`Seal.jsx` + full component set) **but not wired into navigation** — disclosed, unresolved finding from `MWO-LTSA-067` | **Present**, canonical, real workflow logic |
| Work Order | **[CONFIRMED]** §23, reuses `work_order` unchanged | **Present, fully built** | **Present**, canonical, real logic per MO-001 |
| PM | **[CONFIRMED]** §13, new object, lifecycle `DRAFT → PENDING_SUPERVISOR_REVIEW → APPROVED → INCLUDED_IN_REPORT` | **Present** as its own workspace (`PM.jsx`) but with a *different*, dashboard-local lifecycle (schedule/status-based, not the Supervisor-review lifecycle above) | Not separately modeled — composed from `work_order` + `maintenance_history` only (`product.manifest.json: "maintenance"` note) |
| CM | **[CONFIRMED]** §14, same lifecycle shape as PM | **Present** as its own workspace (`CM.jsx`), same local-lifecycle mismatch as PM | Same as PM — composed, not separate |
| Inspection | **[CONFIRMED]** §12, new object, `IN_PROGRESS → CLASSIFIED → COMPLETED` | **Absent as a distinct concept** — the dashboard has no "raw field report awaiting classification" state; PM/CM are created directly, already classified | **`"missing"` — explicitly flagged in `product.manifest.json`: "no database, API, or workflow artifact exists anywhere in the product"** |
| Service Report | Named "**Technical Report**" in the approved spec (§16) — same object, different name | **Present**, as the Reports workspace (`ReportsWorkspace.jsx`, five report types) — but purely presentational (print/PDF), no Supervisor-approval workflow behind it | Absent as a workflow; no approval gate exists in the backend either |
| Engineer | **[CONFIRMED]** §28 — explicitly *not* a separate record, a Role-scoped view of Employee | Absent as a role/access concept — the dashboard has no login, no roles, no users at all (anyone who opens it sees everything) | Absent — no Employee/Role/User implementation exists in LTSA-BRAIN |
| Supervisor | **[CONFIRMED]** role, not a registry object of its own (a Role value) | Absent (see Engineer, above) | Absent |
| Vendor | **[CONFIRMED]** §29, Supporting, Finance OS | Absent | Absent |
| Manufacturer | **Not a registry object — a free-text attribute** on Pump/Seal/Asset (`manufacturer` column) | **Present as a field only** (`samplePumps.js: manufacturer`, e.g. "Sulzer," "Flowserve") — not a separate registry, no manufacturer-level data (catalogs, contacts, warranty terms) | Same — field only, not a registry |

---

## 5. Operational Workflow

The requested flow, walked end to end against confirmed evidence:

```
Customer                                    [ABSENT from LTSA Demo v1 entirely — see §4/§6]
   ↓
Project                                     [spec-only object, MWO-ENT-002 §22 — not built anywhere]
   ↓
Asset (Equipment / Pump / Seal / Asset / Soot Blower)
   ↓  — real today: Pump (frontend + backend), Seal (backend real, frontend built-but-unwired),
   ↓    Asset/Soot Blower (backend only, no frontend workspace exists for either)
Work Order
   ↓  — real today, both frontend and backend, though disconnected from each other (see §6)
Engineer  (assignment, via Role — resolved by `retrieve_role_artifact()` in the backend)
   ↓  — real in the backend's Role Manufacturing capability; entirely absent from the frontend,
   ↓    which has no login/role/user concept of any kind
Maintenance  (PM or CM execution)
   ↓  — real in both frontend (as its own workspaces) and backend (composed from work_order +
   ↓    maintenance_history), but the two do not share a lifecycle or a data source
Service Report / Technical Report
   ↓  — real as a presentational artifact in the frontend (print/PDF); real as a *workflow concept*
   ↓    (with a Supervisor approval gate) only in the approved spec, not built anywhere yet
Customer Approval
   ↓  — **[UNMODELED anywhere]** — no object, field, or workflow step captures customer
   ↓    acceptance/rejection of a Technical Report, in either the frontend or the backend
Project Completion
   ↓  — **[UNMODELED anywhere]** — Project itself does not exist as a real object yet, so nothing
        can be "completed" against it today
```

**The single most consequential finding of this section:** even setting aside every object that is merely spec-only, **the LTSA-BRAIN backend and the LTSA Dashboard frontend (LTSA Demo v1) are not connected to each other at all.** The frontend renders exclusively from static, local, in-memory sample data (`src/modules/ltsa/data/sample*.js`) with zero HTTP calls to the backend's n8n webhooks anywhere in its source. Confirmed by direct inspection: no `fetch`, no API client, and no environment-configured backend URL exists anywhere under `AI5R-STUDIO/dashboard/src/modules/ltsa/`. This means a real Work Order created through the frontend today does not, and structurally cannot, reach the backend's `work_order` table, and vice versa. This is not a bug in either side — both were built correctly for their own stated scope (the frontend explicitly as a "no backend, no API" UI-only demonstration per its own code comments; the backend explicitly credential-blocked from runtime verification, per `MO-001-MANUFACTURING-REPORT.md §3.3`) — but it is the largest single fact standing between "LTSA Demo v1" and "CV Razzan operating on AI5R for real," and no item in the Gap Analysis below matters until this is addressed.

---

## 6. Gap Analysis

**LTSA Demo v1** below means specifically the certified release candidate from `MWO-LTSA-067` — the React dashboard at `AI5R-STUDIO/dashboard`, sample-data-driven, no backend connection. Where the LTSA-BRAIN backend has relevant real capability the frontend lacks, it is noted separately — it is adjacent capability, not currently part of "LTSA Demo v1" as certified.

| Capability | Classification | Why |
|---|---|---|
| Pump registry, detail, health scoring | **Already supported** | Fully built in LTSA Demo v1; most mature module in the product |
| Work Order create/list/detail/status | **Already supported** | Fully built in LTSA Demo v1, with local persistence within a session |
| PM / CM scheduling and reporting | **Already supported** | Fully built as dedicated workspaces; UI-level lifecycle differs from the approved spec's Supervisor-gated lifecycle (see below) |
| Maintenance History / Asset 360 view | **Already supported** | Built under `MWO-LTSA-062` |
| Manager reporting (print/PDF) | **Already supported** | Built under `MWO-LTSA-064`; presentational only, not a workflow |
| Manager analytics (KPIs, trends, recommended actions) | **Already supported** | Built under `MWO-LTSA-065` |
| Seal registry | **Needs adaptation** | Fully coded but not wired into navigation — a one-step activation, not new development (disclosed in `MWO-LTSA-067`) |
| PM/CM Supervisor-approval gate (`DRAFT → SUPERVISOR_REVIEW → APPROVED`) | **Needs adaptation** | The frontend's PM/CM status model is schedule/status-based, not approval-gated; the *data shape* is close, the *lifecycle* is not the one the approved spec requires |
| Frontend ↔ backend connectivity | **Missing** | Confirmed zero integration in either direction (§5) — the precondition for everything else on this list to matter for real operation |
| Customer registry (frontend) | **Missing** | No Customer concept anywhere in the dashboard; backend has a stub table with no real query logic |
| Project registry | **Missing** | Not a real object anywhere — spec-only entry in `MWO-ENT-002`, not built, not in the frontend |
| Site / Area / Equipment location hierarchy above the flat `area` field | **Missing** | Spec'd (`MWO-ENT-002 §5-8`) to close a disclosed gap, not implemented anywhere |
| Asset / Soot Blower registries (frontend) | **Missing** | Real in the backend (`BUILD-PACKS/BP-ASSET`, `BP-SOOT-BLOWER`), no equivalent frontend workspace exists |
| Inspection as a distinct, classifiable object | **Missing** | Explicitly flagged `"missing"` even in the backend's own manifest |
| Engineer WhatsApp channel / AI LTSA Operator | **Missing** | Fully specified (`MWO-ENT-001 §6-7`, `MWO-ENT-003` EP-002/EP-003) but zero implementation exists — no WhatsApp Capability, no AI LTSA Operator code, anywhere |
| Employee / Role / User / login / access control | **Missing** | Spec'd at the object level (`MWO-ENT-002 §20,24,32-33`) and partially implemented as generic Company/Department/Role file-artifact manufacturing (`organization_registry.py`, `role_manufacturing.py`, `department_manufacturing.py`) — but **no Employee object exists at all**, and the frontend has zero concept of login or role-based visibility |
| PO / SPK (customer work authorization document) | **Missing** | Zero repository evidence of this object anywhere, confirmed by direct search — see §1/§2 |
| Quotation (as a real, working object) | **Missing** | Named in the approved spec's narrative and in a *completely separate, unconnected* generic AI5R-SDK commercial capability (`AI5R-SDK/BUSINESS/COMMERCIAL/QUOTATION/`) that has never been wired to LTSA or CV Razzan at all |
| Motor as a distinct registry/object | **Not required** | No evidence CV Razzan needs Motor tracked separately from Pump; treat as a Pump attribute unless CV Razzan says otherwise |
| Manufacturer as a distinct registry (catalog, contacts, warranty terms) | **Not required, unless CV Razzan says otherwise** | Currently a free-text field only; sufficient for a demo, unconfirmed whether real operation needs more |
| Vendor registry | **Not required under this MWO's own Rules** | Named in the approved Enterprise Object Model, but Vendor/Purchase live under Finance OS, and this MWO's Rules explicitly exclude Purchasing |
| Invoice / Payment / Billing (real, working) | **Not required under this MWO's own Rules** | "Invoice — reference only" per this MWO's own Scope; the full Billing Workflow is already spec'd under `MWO-ENT-001 §10` but explicitly belongs to a Finance OS workstream this MWO does not authorize |
| Employee Payroll, Attendance, HR OS generally | **Not required under this MWO's own Rules** | Explicitly excluded ("No HR") |
| Inventory / spare parts tracking | **Not required under this MWO's own Rules** | Explicitly excluded ("No Inventory"), and already named as a standing future gap in `MWO-ENT-001 §15` regardless |

---

## 7. Deployment Roadmap

Ordered by business value, and constrained by this MWO's own Rules (reuse existing LTSA architecture, no duplicate engines, no Finance/HR/Inventory/Purchasing/Accounting). Each item is scoped to be independently reviewable and approvable, consistent with this repository's MWO discipline — **none of these are authorized by this report**; this is a proposed sequence for the Chief Architect / Product Owner to approve or reorder.

| MWO | Title | Business value | Depends on |
|---|---|---|---|
| `MWO-LTSA-069` | **Frontend–Backend Connectivity** | Without this, nothing else on this list can reach real data — the single highest-leverage item, per §5's own finding | None |
| `MWO-LTSA-070` | **Customer & Project Foundation** | Introduces Customer and Project as real, first-class objects in both frontend and backend — the object model already exists on paper (`MWO-ENT-002 §3,22`), it has never been built | `069` |
| `MWO-LTSA-071` | **Enterprise Asset Hierarchy (Site / Area / Equipment)** | Closes the disclosed location-hierarchy gap; lets Asset/Soot Blower/Seal join Pump as first-class, navigable workspaces | `070` |
| `MWO-LTSA-072` | **Workforce & Access Foundation (Employee / Role / basic login)** | The precondition for any real Supervisor-approval gate or Engineer-assignment logic to mean anything outside a demo | `070` |
| `MWO-LTSA-073` | **Inspection & Supervisor-Gated PM/CM Lifecycle** | Replaces the frontend's current schedule/status-based PM/CM model with the approved `DRAFT → SUPERVISOR_REVIEW → APPROVED` lifecycle; introduces Inspection as its own classifiable object | `072` |
| `MWO-LTSA-074` | **Service (Technical) Report Approval Workflow** | Turns today's print-only Reports workspace into a real, Supervisor-gated, customer-delivered artifact | `073` |
| `MWO-LTSA-075` | **Customer Approval & Project Completion** | Closes the loop the Operational Workflow (§5) identifies as fully unmodeled today | `074` |
| *(deferred, separate workstream)* | Engineer WhatsApp Channel / AI LTSA Operator | High value, but a materially larger, separately-architected effort (`MWO-ENT-003` already scopes it as its own Sprint 1, EP-001 through EP-003) — not sequenced into this list, flagged for separate authorization | — |
| *(deferred, separate workstream)* | Lead → Quotation → PO/SPK | Cannot be scoped responsibly until CV Razzan confirms whether this sales-led process is real, and if so, how it actually works today (§1) — recommended as a discovery follow-up, not a build item, until the **[UNKNOWN]**s in §1/§2 are resolved | — |
| *(explicitly out of this roadmap)* | Finance OS, HR OS, Inventory, Purchasing, Accounting | Already specified at the architecture level (`MWO-ENT-001`), explicitly excluded by this MWO's own Rules — a separate track, not sequenced here | — |

---

## Answering the Success Question

**"What must happen before CV Razzan can operate entirely on AI5R?"**

In order: (1) connect the frontend to a real backend — today they are two fully-built, fully-disconnected systems; (2) give the product a Customer and a Project, neither of which exist as real objects anywhere despite being spec'd; (3) extend the asset model beyond Pump to the full Site/Area/Equipment hierarchy already designed but unbuilt; (4) give the business its people — Employee, Role, and enough access control that "Supervisor approves" and "Engineer is assigned" are real, not implied; (5) only then does the PM/CM/Service-Report/Customer-Approval lifecycle this MWO asked about become something CV Razzan could actually run a business on, rather than demonstrate. The sales-led Lead→Quotation→PO/SPK front half, and the Engineer WhatsApp channel, are both real, valuable, and both **larger and less understood** than anything else in this report — recommended as the next two discovery conversations with CV Razzan directly, not the next two build items.

---

Discovery only — no implementation, no UI, no backend, no database, and no architecture redesign performed in producing this report.

## Definition of Done — Status

Per the Product Owner refinement, this MWO's success criterion superseded its original Definition of Done: a complete deployment blueprint answering "What must happen before CV Razzan can operate entirely on AI5R?"

- Business Model documented — **Met** (§1), with every unresolved question named explicitly rather than guessed.
- Business Process Map produced — **Met** (§2), with the confirmed/spec'd back half and the unmodeled front half (Lead → Quotation → PO/SPK) explicitly distinguished.
- Organization Map produced — **Met** (§3), reconciling the requested role set against the already-approved `MWO-ENT-001` role set rather than silently substituting one for the other.
- Enterprise Object Discovery produced — **Met** (§4), cross-referencing every requested object against the 38-object `MWO-ENT-002` catalog, LTSA Demo v1 (frontend), and the LTSA-BRAIN backend independently.
- Operational Workflow documented — **Met** (§5), including the headline finding that the frontend and backend are fully built but entirely disconnected.
- Gap Analysis produced — **Met** (§6), every capability classified Already supported / Needs adaptation / Missing / Not required, with reasoning.
- Deployment Roadmap produced — **Met** (§7), `MWO-LTSA-069`–`075` proposed in priority order, none authorized by this report itself.
- Discovery only, no implementation/UI/backend/database/architecture change — **Met**, confirmed via `git status` scoped to source/UI/backend/database paths (empty).

## Closure

Reviewed and approved by Product Owner (2026-07-20). MWO-LTSA-068 is CLOSED. The discovery blueprint stands as the durable record for CV Razzan Teknik Mandiri's real operating model; no part of it is self-authorizing — the proposed `MWO-LTSA-069` (Frontend–Backend Connectivity) and successors remain unapproved until the Chief Architect / Product Owner separately authorizes them. Committed to `feature/repository-hygiene` (see commit history for hash). No push performed as part of closure. Successor MWO not yet defined — awaiting a decision on which proposed roadmap item, if any, becomes the next MWO.
