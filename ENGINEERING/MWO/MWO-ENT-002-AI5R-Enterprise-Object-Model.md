# MWO-ENT-002 — AI5R Enterprise OS v1 — Enterprise Object Model

Status: SPECIFICATION ONLY — no SQL, no code, no API. No implementation performed.
Type: Manufacturing Work Order (Specification / WP-000)
Role: Implementation Engineer, acting on Chief Enterprise Architect direction.
Architecture: FROZEN. This document does not redesign anything decided by `ADR-001`–`004`, `UMC-001`/`UMR-001`, or `MWO-ENT-001` (approved). It is the canonical Enterprise Object Model that specification authorized but did not itself enumerate.
Parent: `MWO-ENT-001-AI5R-Enterprise-OS-v1-Specification.md` (approved). Every object below is placed inside that document's already-approved structure (Brand/Legal Entity split, LTSA OS/Finance OS/HR OS subsystems, Agent Layer) — none of it is reopened here.
Scope: This document only. No `AI5R-SDK`, `PRODUCTS/LTSA-BRAIN`, `CORE-SERVICES`, or Runtime file is modified in producing it.

---

## Executive Summary

`MWO-ENT-001` named the objects this Enterprise OS would need without formally specifying them (its own §2 listed them, its own §1 introduced a single provisional "Legal Entity" object). This document is that formal specification: **38 Enterprise Objects**, each with a fixed Purpose, Owner Module, Relationships, Required/Optional Fields, Business Rules, Lifecycle, Validation Rules, and Future Expansion — the canonical reference every future module (LTSA OS, Finance OS, HR OS, and anything assembled into this Product later) must reuse rather than re-derive.

Two refinements from `MWO-ENT-001`, both elaborations of what that document already flagged as new/undecided, not redesigns of anything frozen:

1. **Legal Entity is split into `Brand` and `OperatingCompany`.** `MWO-ENT-001` §1 introduced "Legal Entity" as a single new object with a `customer_facing` boolean. The Chief Enterprise Architect's own object list distinguishes them explicitly (`Brand`, `OperatingCompany` as two separate required objects) — a more precise version of the same, already-approved concept, not a new one.
2. **`Equipment` is introduced as the common supertype `Pump`/`Seal`/`Asset` specialize.** The existing canonical schema's own header comments (`ltsa_pumps`, `seal_registry`, `asset_registry` — cited directly in `MWO-LTSA-054` WP-000 §3) already state an asset's type is "resolved at the application/workflow layer... four separate tables with no common supertype in this schema" — a disclosed, standing gap, not a decision this document reverses. `Equipment` is the target canonical supertype that gap has always implied; existing tables are unchanged, per this repository's own standing Canonical Promotion Strategy (`ADR-AR-003`: promote the preferred shape to canonical, maintain compatibility, migrate gradually — never a forced, immediate rewrite).

No object below duplicates another. Where two of the Chief Enterprise Architect's named objects are the same underlying concept viewed from two roles (`Engineer` is a `Role`-scoped view of `Employee`, not a second person-record; `User` is the login identity some `Employee`s and no `Engineer`s hold), that relationship is stated explicitly in both entries rather than silently creating two tables for one thing.

---

## Part 1 — Enterprise Object Catalog

| # | Object | Category | Owner Module | Purpose (one line) |
|---|---|---|---|---|
| 1 | Brand | Core | Enterprise (cross-cutting) | The customer-visible identity — PT Tommy Adji Prasetyo — every customer-facing document/message is issued under |
| 2 | OperatingCompany | Core | Enterprise (cross-cutting) | The internal, never-customer-visible legal entity — CV Razzan Teknik Mandiri — that performs the work |
| 3 | Customer | Core | Finance OS (owner), LTSA OS (consumer) | An organization AI5R Enterprise OS serves, always under a Brand |
| 4 | Customer Contact | Supporting | Finance OS | A named person at a Customer, for communication and document delivery |
| 5 | Contract | Core | Finance OS | The commercial agreement governing what/how a Customer is billed |
| 6 | Site | Core | LTSA OS | A Customer's physical location |
| 7 | Plant | Core | LTSA OS | A production unit within a Site |
| 8 | Area | Core | LTSA OS | A zone within a Plant where Equipment is installed |
| 9 | Equipment | Core | LTSA OS | The common supertype for every maintainable physical item (Pump, Seal, Asset, and future types) |
| 10 | Asset | Core | LTSA OS | A generic Equipment specialization for physical items with no dedicated object yet |
| 11 | Pump | Core | LTSA OS | The primary maintained Equipment type — reuses `ltsa_pumps` unchanged |
| 12 | Seal | Core | LTSA OS | A sealing component, tracked both as its own registry item and as a Pump attribute |
| 13 | Inspection | Core | LTSA OS | An Engineer's field visit/report to a piece of Equipment, the parent event PM or CM classifies |
| 14 | Preventive Maintenance (PM) | Core | LTSA OS | A completed, scheduled maintenance action recorded from an Inspection |
| 15 | Corrective Maintenance (CM) | Core | LTSA OS | A completed, failure-driven repair action recorded from an Inspection |
| 16 | Maintenance History | Core | LTSA OS | The immutable historical ledger entry — reuses `maintenance_history` unchanged — produced by every completed PM or CM |
| 17 | Failure Pattern | Supporting | LTSA OS | A detected recurrence across an Equipment's CM history (repeated seal/bearing/vibration/leakage) |
| 18 | Technical Report | Core | LTSA OS ↔ Finance OS boundary | The customer-facing document aggregating PM/CM/Maintenance History for a Work Order or period |
| 19 | Billing | Core | Finance OS | The internal determination that a Technical Report/Work Order is chargeable, and for how much |
| 20 | Invoice | Core | Finance OS | The formal customer-facing billing document generated from a Billing record, issued under Brand |
| 21 | Payment | Core | Finance OS | Money received against an Invoice, under Brand |
| 22 | Engineer | Supporting | LTSA OS / HR OS boundary | The WhatsApp-only, no-login field Role an Employee holds — not a second person-record |
| 23 | Employee | Core | HR OS | The master record for every person working for OperatingCompany |
| 24 | Department | Core | HR OS (owner), Enterprise (consumer) | An organizational unit within OperatingCompany — reuses Organization Registry unchanged |
| 25 | Attendance | Supporting | HR OS | An Employee's presence record for a period |
| 26 | Payroll | Supporting | HR OS (calculates), Finance OS (disburses) | An Employee's computed pay for a period |
| 27 | Expense | Supporting | Finance OS | An OperatingCompany operational cost |
| 28 | Purchase | Supporting | Finance OS | An OperatingCompany purchase order to a Vendor |
| 29 | Vendor | Supporting | Finance OS | An OperatingCompany supplier |
| 30 | Project | Core | Finance OS (owner), LTSA OS (consumer) | A cost/time-bounded body of work for a Customer, grouping Work Orders |
| 31 | Work Order | Core | LTSA OS | A planned, assignable unit of work — reuses `work_order` unchanged |
| 32 | User | Core | Enterprise (cross-cutting) | The login/authentication identity for every Employee who needs dashboard access |
| 33 | Role | Core | Enterprise (cross-cutting) | A function/permission-set — reuses Organization Registry / Role Manufacturing unchanged |
| 34 | Permission | Supporting | Enterprise (cross-cutting) | A single authorized action, granted to a Role |
| 35 | Notification | Supporting | Agent Layer | An outbound alert to a User/Employee/Customer Contact about another object's state change |
| 36 | Conversation | Supporting | Agent Layer | One WhatsApp message thread with an Engineer (or, future, a Customer) |
| 37 | Conversation Memory | Supporting | Agent Layer | BRAIN's retained context for an in-progress Conversation |
| 38 | Knowledge Record | Supporting | Knowledge (AI5R peer asset) | A durable, AI5R-level unit of accumulated maintenance knowledge, derived from Failure Pattern/Maintenance History |

**Core = 25. Supporting = 13.**

---

## Part 2 — Enterprise Relationships

| From | Relationship | To | Cardinality |
|---|---|---|---|
| Customer | is served under | Brand | many : 1 |
| Customer | has | Customer Contact | 1 : many |
| Customer | has | Contract | 1 : many |
| Customer | has | Site | 1 : many |
| Customer | has | Project | 1 : many |
| Customer | is billed via | Billing → Invoice → Payment | 1 : many |
| Customer | receives | Technical Report | 1 : many |
| Contract | governs | Billing | 1 : many |
| Site | has | Plant | 1 : many |
| Plant | has | Area | 1 : many |
| Area | contains | Equipment | 1 : many |
| Equipment | is specialized by | Pump, Seal, Asset (and future types) | 1 : 1 (is-a) |
| Pump | uses | Seal (via `seal_type` → `seal_code`, existing Relationship Resolution) | many : 1 |
| Equipment | is the subject of | Inspection | 1 : many |
| Equipment | is the subject of | Work Order | 1 : many |
| Work Order | belongs to | Customer, Project (optional) | many : 1 |
| Work Order | is assigned to | Employee (via Role) | many : 1 |
| Work Order | has | Inspection, Maintenance History | 1 : many |
| Inspection | is classified as | PM or CM | 1 : 1 |
| Inspection | is performed by | Engineer (Employee) | many : 1 |
| Inspection | originates from | Conversation | 1 : 1 |
| PM, CM | produce | Maintenance History | 1 : 1 |
| CM | contributes to | Failure Pattern (many CM → one Pattern, over time) | many : 1 |
| Failure Pattern | contributes to | Knowledge Record | many : 1 |
| Maintenance History | contributes to | Knowledge Record | many : 1 |
| PM, CM, Maintenance History | are aggregated by | Technical Report | many : 1 |
| Technical Report | is issued under | Brand | many : 1 |
| Technical Report | leads to | Billing (if chargeable) | 1 : 0..1 |
| Billing | produces | Invoice | 1 : 1 |
| Invoice | is issued under | Brand | many : 1 |
| Invoice | receives | Payment | 1 : many (partial payments) |
| Employee | belongs to | OperatingCompany, Department | many : 1 |
| Employee | holds | Role (one or more) | many : many |
| Employee | has | Attendance, Payroll | 1 : many |
| Engineer | is a Role-scoped view of | Employee | 1 : 1 (not a separate record) |
| User | belongs to | Employee | 1 : 1 |
| User | holds | Role (via Employee) | many : many |
| Role | grants | Permission | 1 : many |
| Department | belongs to | OperatingCompany | many : 1 |
| Expense, Purchase | belong to | OperatingCompany, Project (optional), Vendor (Purchase only) | many : 1 |
| Vendor | belongs to | OperatingCompany | many : 1 |
| Project | belongs to | Customer (external) and OperatingCompany (internal cost) | many : 1 each |
| Conversation | is held with | Engineer (by phone number) | many : 1 |
| Conversation | has | Conversation Memory | 1 : 1 |
| Notification | references | any object (polymorphic: Work Order, Technical Report, Billing, PM, CM, ...) | many : 1 |
| Notification | is sent to | User, Employee, or Customer Contact | many : 1 |

---

## Part 3 — Object Dependency Diagram

Layered by dependency depth — an object in Layer N may reference objects in Layer < N only. No cycle exists.

```
Layer 0  (no dependencies)
  Brand
  OperatingCompany

Layer 1
  Customer            (→ Brand)
  Department          (→ OperatingCompany)
  Vendor              (→ OperatingCompany)

Layer 2
  Customer Contact    (→ Customer)
  Contract            (→ Customer)
  Site                (→ Customer)
  Employee            (→ OperatingCompany, Department)
  Role                (→ OperatingCompany or Brand, entity scope)

Layer 3
  Plant               (→ Site)
  User                (→ Employee, Role)
  Permission          (→ Role)
  Engineer            (→ Employee, Role)   [view, not a new record]

Layer 4
  Area                (→ Plant)

Layer 5
  Equipment           (→ Area)
    ├── Pump          (is-a Equipment; → Seal)
    ├── Seal          (is-a Equipment)
    └── Asset         (is-a Equipment)

Layer 6
  Work Order          (→ Customer, Equipment, Employee/Role, Project)
  Project             (→ Customer, OperatingCompany)
  Conversation        (→ Engineer)

Layer 7
  Inspection          (→ Equipment, Engineer, Work Order, Conversation)
  Conversation Memory (→ Conversation)
  Attendance          (→ Employee)
  Payroll             (→ Employee, Attendance)
  Expense             (→ OperatingCompany, Project, Vendor)
  Purchase            (→ OperatingCompany, Vendor, Project)

Layer 8
  PM                  (→ Inspection)
  CM                  (→ Inspection)

Layer 9
  Maintenance History (→ PM or CM, Work Order)
  Notification        (→ any object, polymorphic)

Layer 10
  Failure Pattern     (→ many CM, Equipment)
  Technical Report    (→ PM, CM, Maintenance History, Work Order, Brand)

Layer 11
  Knowledge Record    (→ Failure Pattern, Maintenance History)

Layer 12
  Billing             (→ Technical Report, Contract)

Layer 13
  Invoice             (→ Billing, Brand)

Layer 14
  Payment             (→ Invoice, Brand)
```

---

## Part 4 — Core Objects

### 1. Brand

**Purpose:** The single customer-visible identity — PT Tommy Adji Prasetyo — every customer-facing artifact is issued under.
**Description:** A lightweight reference object, not an operating company. Exists so "which name appears on this document" is a structural field, never a per-document choice. Per `MWO-ENT-001` §1/§6, exactly one Brand is customer-visible in this Product's v1; the object supports more without requiring a redesign, per `ADR-001`'s own multi-customer-opportunity framing.
**Owner Module:** Enterprise (cross-cutting).
**Relationships:** Customer is served under a Brand; Technical Report, Invoice, Payment, and every customer-facing Notification are issued under a Brand.
**Required Fields:** brand code; brand legal/display name; customer-facing flag.
**Optional Fields:** logo/asset reference; contact details (address, phone, email) shown on customer documents.
**Business Rules:** exactly one Brand has `customer_facing = true` in this Product's v1. No role ever selects a Brand manually on a document — it is resolved structurally (`MWO-ENT-001` §1).
**Lifecycle:** ACTIVE → (future) RETIRED. No delete — a Brand referenced by any historical Invoice/Technical Report is never removable.
**Validation Rules:** brand code unique; display name required; at most one `customer_facing = true` Brand active at a time in this Product.
**Future Expansion:** a second AI5R Enterprise OS deployment for a different customer would introduce its own Brand set — this object already supports that without change.

---

### 2. OperatingCompany

**Purpose:** The internal, never-customer-visible legal entity — CV Razzan Teknik Mandiri — that performs the operational work.
**Description:** The counterpart to Brand. Owns Employee, Department, Payroll, Expense, Purchase, Vendor, and the internal cost side of Work Order/Project. Never referenced by any customer-facing document.
**Owner Module:** Enterprise (cross-cutting).
**Relationships:** Employee, Department, Vendor, Expense, Purchase belong to an OperatingCompany; Work Order/Project carry an `owning_entity` reference to it (§1 `MWO-ENT-001`).
**Required Fields:** operating company code; legal name; tax/registration identifiers.
**Optional Fields:** registered address; internal contact details.
**Business Rules:** never rendered on any Customer-, Website-, or Portal-facing surface (`MWO-ENT-001` §6, structural rule, not a display filter). Exactly one OperatingCompany exists in this Product's v1.
**Lifecycle:** ACTIVE → (future) RETIRED. No delete.
**Validation Rules:** operating company code unique.
**Future Expansion:** a future engagement with a second internal operating entity (e.g., a second workshop/branch) is representable without redesign — Employee/Department/Vendor already reference OperatingCompany by id, not by assumption of a single row.

---

### 3. Customer

**Purpose:** An organization AI5R Enterprise OS serves — the party a Work Order, Technical Report, and Invoice are ultimately for.
**Description:** The root of the commercial relationship. Every Customer is served under exactly one Brand context (v1: always PT Tommy Adji Prasetyo). Corresponds conceptually to `work_order.customer_code`, already a field on the existing canonical `work_order` table — this object gives that reference a formal identity rather than a free-text code.
**Owner Module:** Finance OS (owns the record); consumed by LTSA OS (Work Order, Technical Report) and Agent Layer (WhatsApp routing, future customer channel).
**Relationships:** has Customer Contact, Contract, Site, Project; is billed via Billing → Invoice → Payment; receives Technical Report; is served under Brand.
**Required Fields:** customer code; customer legal name.
**Optional Fields:** billing address; industry/segment; notes.
**Business Rules:** a Customer never has direct system access (`MWO-ENT-001` §6 — "Customer never logs into LTSA"). All Customer-facing communication flows through WhatsApp or delivered documents, never a login.
**Lifecycle:** PROSPECT → ACTIVE → (future) INACTIVE/CHURNED.
**Validation Rules:** customer code unique; must resolve to exactly one Brand context at document-issue time.
**Future Expansion:** CRM subsystem (`ADR-001`-named, `MWO-ENT-001` §15) would extend this object with relationship-management fields, not replace it.

---

### 4. Contract

**Purpose:** The commercial agreement governing what and how a Customer is billed.
**Description:** Sits between Customer and Billing. Defines the terms (rate basis, payment terms, scope) a Billing record is checked against.
**Owner Module:** Finance OS.
**Relationships:** belongs to Customer; governs Billing; may scope a Project.
**Required Fields:** contract code; Customer reference; effective start date; status.
**Optional Fields:** end date; rate/pricing terms; payment terms; scope description.
**Business Rules:** a Billing record referencing an expired or not-yet-effective Contract is a validation failure, not a silent pass.
**Lifecycle:** DRAFT → ACTIVE → EXPIRED / TERMINATED.
**Validation Rules:** contract code unique per Customer; end date, if present, after start date.
**Future Expansion:** contract renewal/amendment history; multi-tier rate schedules.

---

### 5. Site

**Purpose:** A Customer's physical location.
**Description:** The top of the physical asset hierarchy this specification introduces (Site → Plant → Area → Equipment), closing the gap `MWO-LTSA-054` flagged: no location hierarchy exists above `asset_code`/`asset_type` today.
**Owner Module:** LTSA OS.
**Relationships:** belongs to Customer; has Plant.
**Required Fields:** site code; Customer reference; site name.
**Optional Fields:** address; geolocation.
**Business Rules:** every Plant/Area/Equipment resolves to exactly one Site via its Plant ancestry — no orphaned Equipment without a Site.
**Lifecycle:** ACTIVE → (future) DECOMMISSIONED.
**Validation Rules:** site code unique per Customer.
**Future Expansion:** multi-site consolidated reporting for a Customer with several Sites.

---

### 6. Plant

**Purpose:** A production unit within a Site.
**Description:** The middle tier of the location hierarchy — a refinery unit, a factory building, a processing line.
**Owner Module:** LTSA OS.
**Relationships:** belongs to Site; has Area.
**Required Fields:** plant code; Site reference; plant name.
**Optional Fields:** description; capacity/type metadata.
**Business Rules:** none beyond structural containment.
**Lifecycle:** ACTIVE → (future) DECOMMISSIONED.
**Validation Rules:** plant code unique per Site.
**Future Expansion:** plant-level KPIs/dashboards.

---

### 7. Area

**Purpose:** A zone within a Plant where Equipment is physically installed.
**Description:** The bottom tier of the location hierarchy — matches `ltsa_pumps.area`, an existing required field on the canonical Pump table, now given a formal parent object instead of a free-text value.
**Owner Module:** LTSA OS.
**Relationships:** belongs to Plant; contains Equipment.
**Required Fields:** area code; Plant reference; area name.
**Optional Fields:** description.
**Business Rules:** `Equipment.area` (and therefore `ltsa_pumps.area`) should resolve to an Area record, not remain free text, once this model is adopted by a future implementation MWO — **not** a retroactive change to the existing table (`ADR-AR-003` compatibility-first migration).
**Lifecycle:** ACTIVE → (future) DECOMMISSIONED.
**Validation Rules:** area code unique per Plant.
**Future Expansion:** none beyond what Plant/Site already anticipate.

---

### 8. Equipment

**Purpose:** The common supertype for every maintainable physical item — closes the "no common supertype" gap the existing schema's own comments already disclose.
**Description:** Not a new registry replacing `ltsa_pumps`/`seal_registry`/`asset_registry` — a canonical target supertype those (and future) tables specialize, per the Executive Summary's `ADR-AR-003` framing. `Pump`, `Seal`, and `Asset` are each an Equipment specialization; a future Equipment type (e.g., Soot Blower, already present as `soot_blower_registry` but outside this document's required-object list) would specialize it the same way.
**Owner Module:** LTSA OS.
**Relationships:** belongs to Area; is specialized by Pump, Seal, Asset; is the subject of Inspection, Work Order, PM, CM, Maintenance History, Failure Pattern.
**Required Fields:** equipment code (the natural key — e.g. `tag_number` for Pump); equipment type (discriminator: `PUMP`/`SEAL`/`ASSET`/future); Area reference.
**Optional Fields:** manufacturer; model; drawing/documentation reference.
**Business Rules:** `equipment_type` determines which specialization's own required fields apply — the same polymorphic-dispatch concept `MWO-LTSA-054` §3 already documented for `asset_code`/`asset_type`, now given a formal discriminator instead of an unresolved comment.
**Lifecycle:** ACTIVE → UNDER_MAINTENANCE → (future) DECOMMISSIONED.
**Validation Rules:** equipment code unique across all specializations combined (a Pump and a Seal must never share a code); equipment type must be a known specialization.
**Future Expansion:** additional specializations (Soot Blower, Compressor, Motor, Tank) as the physical inventory grows, each reusing this same supertype rather than introducing a fifth unrelated table.

---

### 9. Asset

**Purpose:** A generic Equipment specialization for physical items with no dedicated object yet.
**Description:** Reuses the existing `asset_registry` table's role unchanged — the catch-all specialization for equipment not (yet) important enough to warrant its own dedicated object the way Pump has.
**Owner Module:** LTSA OS.
**Relationships:** is-a Equipment; belongs to Area (via Equipment); is the subject of Inspection, Work Order, PM, CM.
**Required Fields:** (inherited from Equipment) equipment code, equipment type = `ASSET`, Area reference; asset category/description.
**Optional Fields:** manufacturer; model; install date.
**Business Rules:** an Asset that accumulates enough maintenance history/business importance is a candidate for promotion to its own dedicated Equipment specialization (as Pump already is) — a future data-migration decision, not a rule enforced by this object itself.
**Lifecycle:** same as Equipment.
**Validation Rules:** inherited from Equipment.
**Future Expansion:** promotion path to a dedicated specialization, as above.

---

### 10. Pump

**Purpose:** The primary maintained Equipment type in this LTSA OS deployment.
**Description:** Reuses `ltsa_pumps` unchanged (`tag_number`, `area`, `location`, `pump_type`, `api_plan`, `seal_type`, `status`, `manufacturer`, `model`, `drawing_ref`, `notes`) — already canonical, already the subject of this session's own Pump Factory Pack (`MWO-LTSA-050` WP-001, `PumpIdentityResolver`/`PumpRelationshipResolver`/`PumpManufacturingStation`). This entry formalizes it as an Equipment specialization; the underlying table is not touched.
**Owner Module:** LTSA OS.
**Relationships:** is-a Equipment; belongs to Area; uses Seal (via `seal_type` → `seal_code`, the exact relationship `PumpRelationshipResolver` already resolves); is the subject of Inspection, Work Order, PM, CM, Maintenance History, Failure Pattern.
**Required Fields:** `tag_number` (natural key); `area`.
**Optional Fields:** `location`, `pump_type`, `api_plan`, `seal_type`, `status`, `manufacturer`, `model`, `drawing_ref`, `notes` — exactly the existing table's own optional columns.
**Business Rules:** `tag_number` uniqueness is Identity Resolution's own concern (`UMC-001` Stage 4), already implemented (`PumpIdentityResolver`). `seal_type` is free text resolved to `seal_registry.seal_code` at Relationship Resolution time (`UMC-001` Stage 5, `PumpRelationshipResolver`) — an unresolved `seal_type` is a valid, non-error outcome, not a rejection.
**Lifecycle:** same as Equipment (`status` column already models this today: default `UNKNOWN`, no enum enforced — target lifecycle ACTIVE → UNDER_MAINTENANCE → DECOMMISSIONED, not yet `CHECK`-enforced in the existing table).
**Validation Rules:** `tag_number` unique (already a `UNIQUE NOT NULL` constraint); `area` required (already `NOT NULL`).
**Future Expansion:** none beyond what Equipment already anticipates — Pump is intentionally the most mature specialization already.

---

### 11. Seal

**Purpose:** A sealing component — both a standalone tracked item and a Pump attribute.
**Description:** Reuses `seal_registry` unchanged (`seal_code`, `seal_name`, `manufacturer`, `model`, `shaft_size`, `material`, `temperature_limit`, `pressure_limit`, `status`). Plays a dual role, both already real: (1) an Equipment specialization in its own right, and (2) the resolution target for `Pump.seal_type` via `seal_pump_compatibility` (`MWO-LTSA-030`) and `PumpRelationshipResolver` (`MWO-LTSA-050` WP-001).
**Owner Module:** LTSA OS.
**Relationships:** is-a Equipment (when tracked standalone); is referenced by Pump (`seal_type` → `seal_code`); related to Pump via `seal_pump_compatibility` (many-to-many compatibility, not ownership).
**Required Fields:** `seal_code` (natural key); `seal_name`.
**Optional Fields:** `manufacturer`, `model`, `shaft_size`, `material`, `temperature_limit`, `pressure_limit`, `status` — the existing table's own optional columns.
**Business Rules:** the compatibility relationship to Pump (`seal_pump_compatibility`) is a separate cross-reference, not a foreign key on either table — a Seal may be compatible with many Pumps and vice versa.
**Lifecycle:** ACTIVE → (future) OBSOLETE/SUPERSEDED.
**Validation Rules:** `seal_code` unique (already a `TEXT PRIMARY KEY`).
**Future Expansion:** seal interchange compatibility (`seal_interchange_compatibility`, already an existing table from `MWO-LTSA-030`) — cross-seal substitutability, already modeled, reusable unchanged.

---

### 12. Inspection

**Purpose:** An Engineer's field visit/report to a piece of Equipment — the parent event that PM or CM classifies.
**Description:** New object. Represents the raw, classified-but-not-yet-typed engineer report, as received via WhatsApp Workflow (`MWO-ENT-001` §7) before it becomes specifically a PM or a CM record. Every PM and every CM originates from exactly one Inspection.
**Owner Module:** LTSA OS.
**Relationships:** belongs to Equipment; performed by Engineer (Employee); optionally belongs to Work Order; originates from Conversation; is classified as PM or CM (1:1, exactly one).
**Required Fields:** inspection code; Equipment reference; Engineer reference; inspection date; classification (`PM`/`CM`).
**Optional Fields:** Work Order reference; running hour; equipment condition (free text, pre-classification); notes.
**Business Rules:** classification is required before an Inspection is considered complete — an Inspection with no PM/CM classification remains in the AI LTSA Operator's follow-up-question loop (`MWO-ENT-001` §7), not silently defaulted.
**Lifecycle:** IN_PROGRESS (AI LTSA Operator still collecting fields) → CLASSIFIED (PM or CM determined) → COMPLETED (PM/CM record manufactured).
**Validation Rules:** Equipment reference must resolve via Identity Resolution before COMPLETED; Engineer must be a valid Role assignment, not an unrecognized phone number.
**Future Expansion:** scheduled (calendar-driven) Inspections, not only engineer-initiated ones — a future PM scheduling capability, not built here.

---

### 13. Preventive Maintenance (PM)

**Purpose:** A completed, scheduled maintenance action recorded from an Inspection.
**Description:** New object, per `MWO-ENT-001` §8's field list. Whether this is manufactured through System A (Gateway pattern) or System B (`UMC-001`/`UMR-001`, the Pump Factory Pack pattern) remains the open question `MWO-ENT-001` §Open Questions #1 and `MWO-LTSA-054` already left unresolved — this object's *shape* does not depend on that choice.
**Owner Module:** LTSA OS.
**Relationships:** originates from Inspection (1:1); belongs to Equipment, Engineer, Work Order (optional); produces exactly one Maintenance History entry.
**Required Fields:** PM record code; Inspection reference; inspection date; Engineer; Equipment; condition (closed-set); recommendation.
**Optional Fields:** pressure; temperature; leakage; vibration; Work Order reference; photo references (Engineering Media Acquisition Objects, `ADR-004`).
**Business Rules:** `condition` is a closed set (e.g. `GOOD`/`FAIR`/`POOR`/`CRITICAL`), `CHECK`-constrained per the frozen canonical table shape, never a free-text field or a code branch.
**Lifecycle:** DRAFT (AI-extracted) → PENDING_SUPERVISOR_REVIEW → APPROVED → INCLUDED_IN_REPORT.
**Validation Rules:** condition must be one of the closed set; Equipment/Engineer references must resolve.
**Future Expansion:** scheduled-PM compliance tracking (was this PM performed on schedule) once a PM calendar exists (§Inspection Future Expansion).

---

### 14. Corrective Maintenance (CM)

**Purpose:** A completed, failure-driven repair action recorded from an Inspection.
**Description:** New object, per `MWO-ENT-001` §9's field list. Structurally the closest match to the one required field (`action_taken`) the existing canonical `maintenance_history` table already has — this object is the natural-language-intake front end to that same business concept (`MWO-ENT-001` §9).
**Owner Module:** LTSA OS.
**Relationships:** originates from Inspection (1:1); belongs to Equipment, Engineer, Work Order (optional); produces exactly one Maintenance History entry; contributes to Failure Pattern (many CM, same Equipment, over time).
**Required Fields:** CM record code; Inspection reference; Equipment; Engineer; failure description; action taken.
**Optional Fields:** root cause; parts used (free text/list, no Inventory deduction in v1); duration; recommendation; Work Order reference; photo references.
**Business Rules:** `action_taken` is required — mirrors the existing `maintenance_history.action_taken NOT NULL` constraint exactly, so a CM record can never fail to produce a valid Maintenance History entry downstream.
**Lifecycle:** DRAFT → PENDING_SUPERVISOR_REVIEW → APPROVED → INCLUDED_IN_REPORT.
**Validation Rules:** action taken required and non-empty; Equipment/Engineer references must resolve.
**Future Expansion:** Parts Used deducting against a future Inventory subsystem (`MWO-ENT-001` §15).

---

### 15. Maintenance History

**Purpose:** The immutable historical ledger entry for a completed maintenance action.
**Description:** Reuses `maintenance_history` unchanged (`maintenance_record_code`, `work_order_code` optional/non-FK, `asset_code`, `asset_type`, `action_taken`, `performed_by`, `performed_at`, `notes`). Per this model, one Maintenance History row is produced automatically whenever a PM or CM record reaches APPROVED — it is not independently authored by any role.
**Owner Module:** LTSA OS.
**Relationships:** produced by exactly one PM or CM; optionally references Work Order (deliberately non-FK, per the existing table's own documented intent — "to keep this table independently queryable even if a work order record is absent"); contributes to Failure Pattern and Knowledge Record.
**Required Fields:** `maintenance_record_code` (natural key); `action_taken`.
**Optional Fields:** `work_order_code`, `asset_code`, `asset_type`, `performed_by`, `notes` — exactly the existing table's own optional columns.
**Business Rules:** append-only — once created, a Maintenance History row is not edited or deleted, consistent with its role as an audit ledger (mirrors this repository's own standing "no Delete on an immutable registry" principle, `MEMORY.md`, applied here to a historical record rather than an Acquisition Object).
**Lifecycle:** CREATED (terminal — no further states).
**Validation Rules:** `maintenance_record_code` unique (already `TEXT PRIMARY KEY`); `action_taken` required (already `NOT NULL`).
**Future Expansion:** none — this object is intentionally the simplest, most stable one in the model; its value is exactly its unchanging shape.

---

### 16. Technical Report

**Purpose:** The customer-facing document aggregating PM/CM/Maintenance History for a Work Order or reporting period.
**Description:** New object, per `MWO-ENT-001` §11. The point where LTSA OS's internal records become a Brand-issued customer artifact.
**Owner Module:** LTSA OS ↔ Finance OS boundary (LTSA OS authors it; Finance OS's Billing consumes it).
**Relationships:** aggregates one or more PM/CM/Maintenance History records; belongs to Work Order and/or Customer; issued under Brand; approved by an Employee holding the Supervisor Role; may lead to Billing.
**Required Fields:** report code; Customer; issuing Brand; reporting period or Work Order reference; approving Employee (Supervisor); narrative content.
**Optional Fields:** attached photos (via the aggregated PM/CM records' own Engineering Media references); recommendations summary.
**Business Rules:** `issuing_entity` is always Brand = PT Tommy Adji Prasetyo, fixed at manufacture time, never chosen per-document (`MWO-ENT-001` §1/§10). A Technical Report cannot be SENT_TO_CUSTOMER without Supervisor approval.
**Lifecycle:** DRAFT (AI-drafted) → SUPERVISOR_REVIEW → APPROVED → SENT_TO_CUSTOMER.
**Validation Rules:** at least one PM or CM record aggregated; approving Employee must hold the Supervisor Role.
**Future Expansion:** scheduled/periodic report generation (e.g. monthly summary reports) beyond the current Work-Order-triggered model.

---

### 17. Billing

**Purpose:** The internal determination that a Technical Report/Work Order is chargeable, and for how much.
**Description:** New object, per `MWO-ENT-001` §10. The pre-Invoice internal financial event — Finance OS's own record of "this is billable," checked against Contract terms, before any customer-facing document is generated.
**Owner Module:** Finance OS.
**Relationships:** derived from Technical Report; checked against Contract; belongs to Customer; produces exactly one Invoice; references the originating Project/Work Order for Inter-Entity Settlement (`MWO-ENT-001` §4/§10).
**Required Fields:** billing code; Technical Report reference; Customer; Contract reference; billable amount.
**Optional Fields:** cost breakdown (parts/labor); notes.
**Business Rules:** Billing amount is checked against the referenced Contract's rate terms before CONFIRMED; a Billing record referencing an inactive Contract cannot progress (§4 Contract).
**Lifecycle:** DRAFT → CONFIRMED → INVOICED.
**Validation Rules:** Technical Report and Contract references must resolve; billable amount non-negative.
**Future Expansion:** whether Inter-Entity Settlement is its own object or a computed view over Billing + Payment remains open (`MWO-ENT-001` §Open Questions #5) — not decided here.

---

### 18. Invoice

**Purpose:** The formal customer-facing billing document, issued under Brand.
**Description:** New object, per `MWO-ENT-001` §10. Generated from exactly one Billing record.
**Owner Module:** Finance OS.
**Relationships:** produced from Billing; issued under Brand; belongs to Customer; receives Payment (one or many, for partial payments).
**Required Fields:** invoice code; Billing reference; Customer; issuing Brand; amount; due date.
**Optional Fields:** payment terms note; line-item breakdown.
**Business Rules:** `issuing_entity` always Brand = PT Tommy Adji Prasetyo, fixed at manufacture time (§1). Invoice amount must equal its source Billing record's confirmed amount — no independent adjustment at Invoice stage.
**Lifecycle:** DRAFT → SENT → PARTIALLY_PAID → PAID / OVERDUE / CANCELLED.
**Validation Rules:** amount must match source Billing; due date required.
**Future Expansion:** recurring/subscription invoicing, multi-currency support.

---

### 19. Payment

**Purpose:** Money received against an Invoice, under Brand.
**Description:** New object, per `MWO-ENT-001` §10. The terminal event of the Billing Workflow, and the trigger for the Inter-Entity Settlement that credits OperatingCompany's own Project Cost Tracking.
**Owner Module:** Finance OS.
**Relationships:** belongs to Invoice; received under Brand; triggers Inter-Entity Settlement crediting the originating Project/Work Order's OperatingCompany-side cost record.
**Required Fields:** payment code; Invoice reference; amount received; date received; receiving Brand.
**Optional Fields:** payment method; reference/transaction number; notes.
**Business Rules:** received always under Brand = PT Tommy Adji Prasetyo (§1/§6) — CV Razzan never receives a customer payment directly. A Payment whose total against an Invoice reaches the Invoice amount transitions that Invoice to PAID.
**Lifecycle:** RECEIVED → RECONCILED (matched against Invoice and, downstream, Inter-Entity Settlement).
**Validation Rules:** amount positive; Invoice reference must resolve and not already be CANCELLED.
**Future Expansion:** automated bank-feed reconciliation.

---

### 20. Employee

**Purpose:** The master record for every person working for OperatingCompany.
**Description:** New object (HR OS Employee Master, `MWO-ENT-001` §5). The person-record every Role assignment, User account, and the Engineer view all ultimately point back to.
**Owner Module:** HR OS.
**Relationships:** belongs to OperatingCompany and Department; holds one or more Roles; has Attendance, Payroll; may have a User account; may be viewed as Engineer (if holding that Role).
**Required Fields:** employee code; full name; OperatingCompany reference; Department reference; hire date.
**Optional Fields:** phone number (required in practice for anyone holding the Engineer Role — that is where WhatsApp identity resolution reads from); email; position title.
**Business Rules:** an Employee's phone number, if present, is the identity WhatsApp Workflow (`MWO-ENT-001` §7) resolves an inbound message against — not a separate "Engineer phone directory."
**Lifecycle:** ACTIVE → ON_LEAVE → TERMINATED.
**Validation Rules:** employee code unique; Department must belong to the same OperatingCompany.
**Future Expansion:** Performance, Training, Competency records (named in `MWO-ENT-001` §5, not separately required by this document's own 38-object list — cross-referenced here as natural Employee extensions, not invented as new top-level objects).

---

### 21. Department

**Purpose:** An organizational unit within OperatingCompany.
**Description:** Reuses Organization Registry unchanged — already the object `role_manufacturing.retrieve_role_artifact()` resolves against today for Work Order's `assigned_to` field.
**Owner Module:** HR OS (owns the record); Enterprise-wide consumer (Role scoping, Organization Registry).
**Relationships:** belongs to OperatingCompany; has Employee.
**Required Fields:** department code; department name; OperatingCompany reference.
**Optional Fields:** description; parent department (for sub-departments, if needed).
**Business Rules:** none beyond structural containment — reused exactly as Organization Registry already defines it.
**Lifecycle:** ACTIVE → (future) DISSOLVED/MERGED.
**Validation Rules:** department code unique per OperatingCompany.
**Future Expansion:** none — intentionally stable, matching Organization Registry's own existing maturity.

---

### 22. Project

**Purpose:** A cost/time-bounded body of work for a Customer, grouping Work Orders.
**Description:** New object, per `MWO-ENT-001` §4 (Project Cost Tracking). Where CV Razzan's operational cost (Expense, Purchase, Employee time via Work Order) and PT Tommy Adji Prasetyo's revenue (via Billing/Invoice) are both attributable to the same underlying customer engagement, for Inter-Entity Settlement to reconcile.
**Owner Module:** Finance OS (owns the record); LTSA OS (Work Order references it).
**Relationships:** belongs to Customer (external) and OperatingCompany (internal cost); has Work Order, Expense, Purchase; may be scoped by Contract.
**Required Fields:** project code; Customer reference; OperatingCompany reference; project name; start date.
**Optional Fields:** end date; budget; Contract reference.
**Business Rules:** every cost (Expense, Purchase, Employee time) and every revenue event (Billing/Invoice/Payment) attributable to this Project is the basis for Inter-Entity Settlement — Project is the reconciliation key, not Work Order alone (a Project may span many Work Orders).
**Lifecycle:** PLANNED → ACTIVE → COMPLETED → CLOSED.
**Validation Rules:** project code unique; end date, if present, after start date.
**Future Expansion:** project-level profitability reporting (Owner Dashboard, `MWO-ENT-001` §12).

---

### 23. Work Order

**Purpose:** A planned, assignable unit of work.
**Description:** Reuses `work_order` unchanged (`work_order_code`, `customer_code`, `asset_code`, `asset_type`, `description`, `priority`, `status`, `assigned_to`, `created_at`, `updated_at`, `closed_at`).
**Owner Module:** LTSA OS.
**Relationships:** belongs to Customer, Project (optional); references Equipment (`asset_code`/`asset_type`, resolving through the Equipment supertype, §8); assigned to Employee via Role (`assigned_to`); has Inspection, PM, CM, Maintenance History.
**Required Fields:** `work_order_code` (natural key); `description`.
**Optional Fields:** `customer_code`, `asset_code`, `asset_type`, `priority` (default `NORMAL`), `assigned_to` — exactly the existing table's own optional columns.
**Business Rules:** `assigned_to` resolution already goes through Role Manufacturing (`retrieve_role_artifact()`, `MWO-019`) — this model does not duplicate that as a separate Relationship Resolver, per `MWO-LTSA-054` §3's own disclosed choice point (treated here as: keep in System A, do not duplicate).
**Lifecycle:** the existing table enforces no enum (`status TEXT DEFAULT 'OPEN'`, no `CHECK`, disclosed by `MWO-LTSA-054` §5). **Target lifecycle, not yet enforced:** OPEN → IN_PROGRESS → COMPLETED → CLOSED (`closed_at` set only on closure, mirroring the existing nullable column's own intent).
**Validation Rules:** `work_order_code` unique (already `TEXT PRIMARY KEY`); `description` required (already `NOT NULL`).
**Future Expansion:** enforcing the target lifecycle as an actual `CHECK` constraint is future implementation work, not performed by this specification.

---

### 24. User

**Purpose:** The login/authentication identity for every Employee who needs dashboard access.
**Description:** New object. Distinct from Employee (the person) and from Role (the function) — a User is the credential/session identity. Deliberately **not** created for Engineers (`MWO-ENT-001` §6: "No login required for engineers" — Engineers are identified by phone number through WhatsApp, never a User account).
**Owner Module:** Enterprise (cross-cutting).
**Relationships:** belongs to exactly one Employee; holds Role (inherited from Employee's Role assignment, or independently grantable — not decided further here).
**Required Fields:** user id; Employee reference; login credential reference (out of scope for this document — no auth mechanism specified, per "No SQL, No Code, No API").
**Optional Fields:** last login timestamp; account status note.
**Business Rules:** an Employee holding only the Engineer Role never has a User account created for them — this is a structural absence, not a disabled/locked account.
**Lifecycle:** ACTIVE → SUSPENDED → DEACTIVATED.
**Validation Rules:** one User per Employee at most (1:1, not 1:many).
**Future Expansion:** a future Customer Portal (currently explicitly out of scope — "Customer never logs in") would introduce User records tied to Customer Contact instead of Employee — a distinct future extension, not implied by this v1 model.

---

### 25. Role

**Purpose:** A function/permission-set an Employee (and, via Employee, a User) can hold.
**Description:** Reuses Organization Registry / Role Manufacturing unchanged — already the object `retrieve_role_artifact()` resolves today for Work Order's `assigned_to`. This model adds the entity-scope attribute `MWO-ENT-001` §6 specifies (every Role except Owner is scoped to exactly one of Brand or OperatingCompany's visibility).
**Owner Module:** Enterprise (cross-cutting).
**Relationships:** belongs to Department (organizational placement); is held by Employee; grants Permission; scoped to Brand or OperatingCompany (entity visibility, §6 `MWO-ENT-001`) — Owner is the sole exception, scoped to both.
**Required Fields:** role code; role name; Department reference; entity scope (Brand / OperatingCompany / Both).
**Optional Fields:** description.
**Business Rules:** the named roles from `MWO-ENT-001` §6 (Engineer, Supervisor, Admin, Finance Officer, HR Officer, Owner) are the initial closed set; Engineer's entity scope is OperatingCompany with the additional structural constraint of no User account (§24).
**Lifecycle:** ACTIVE → (future) RETIRED.
**Validation Rules:** role code unique; entity scope required and must be one of the defined values.
**Future Expansion:** finer-grained role variants as the org grows (e.g. Senior Engineer, Finance Manager) — additive to the existing closed set, not a redesign of it.

---

## Part 5 — Supporting Objects

### 26. Customer Contact

**Purpose:** A named person at a Customer, for communication and document delivery.
**Description:** New object. Where Technical Report/Invoice delivery details (who at the Customer receives WhatsApp updates) are recorded, distinct from the Customer organization itself.
**Owner Module:** Finance OS.
**Relationships:** belongs to Customer; is the delivery target for Notification (Technical Report, Invoice, Quotation equivalents).
**Required Fields:** contact code; Customer reference; full name; phone number (for WhatsApp delivery).
**Optional Fields:** email; role/title at Customer; preferred contact channel.
**Business Rules:** every outbound customer Notification resolves to a Customer Contact, not directly to "the Customer" as an abstract organization.
**Lifecycle:** ACTIVE → INACTIVE.
**Validation Rules:** phone number required if WhatsApp is the delivery channel.
**Future Expansion:** future Customer Portal login identity (§24 User Future Expansion).

---

### 27. Failure Pattern

**Purpose:** A detected recurrence across an Equipment's CM history.
**Description:** New object, per `MWO-ENT-001` §3/§14 — the concrete LTSA instance of `ADR-002`'s Learning → Knowledge loop, not yet implemented for any product (`ADR-002` Migration Strategy Steps 1–6, still open).
**Owner Module:** LTSA OS.
**Relationships:** derived from many CM records for the same Equipment; contributes to Knowledge Record.
**Required Fields:** pattern code; Equipment reference; pattern description (e.g. "repeated seal failure"); occurrence count; first-detected date.
**Optional Fields:** confidence/severity indicator; recommended action.
**Business Rules:** detection logic itself (what counts as "repeated") is not specified here — a future BRAIN/Knowledge implementation concern, per `ADR-002` §2's own closed-loop description, not this object's own field.
**Lifecycle:** DETECTED → CONFIRMED (Supervisor-reviewed) → (feeds) Knowledge Record.
**Validation Rules:** occurrence count ≥ 2 (a single CM is not yet a pattern).
**Future Expansion:** this entire object is itself future-facing — its detection mechanism is `MWO-ENT-001` §15's own named gap.

---

### 28. Engineer

**Purpose:** The WhatsApp-only, no-login field Role an Employee holds.
**Description:** **Not a separate person-record.** Included in this catalog because the Chief Enterprise Architect's own object list names it explicitly, and because its constraints (no User account, phone-number identity, WhatsApp-only channel) are distinct enough from generic Employee/Role to warrant its own documented entry — but it resolves entirely to an Employee holding the Engineer Role (§20, §25), never a duplicate table.
**Owner Module:** LTSA OS / HR OS boundary.
**Relationships:** is Employee + Role="Engineer" (view, not a new record); performs Inspection; is identified by Conversation (phone number).
**Required Fields:** (none of its own — inherits Employee's required fields, with phone number effectively required in practice).
**Optional Fields:** (none of its own).
**Business Rules:** no User account exists for an Employee solely in this Role (§24). Identified in WhatsApp Workflow purely by phone number → Employee lookup, never by a separate Engineer login or ID entry.
**Lifecycle:** follows Employee's own lifecycle.
**Validation Rules:** an Inspection's Engineer reference must resolve to an Employee currently holding the Engineer Role.
**Future Expansion:** none of its own — any future Engineer-specific capability (e.g. skill/certification, §5 Competency) is modeled as an Employee/Competency extension, not a new Engineer table.

---

### 29. Attendance

**Purpose:** An Employee's presence record for a period.
**Description:** New object, per `MWO-ENT-001` §5.
**Owner Module:** HR OS.
**Relationships:** belongs to Employee; feeds Payroll (hours worked, overtime basis).
**Required Fields:** Employee reference; date; status (present/absent/leave, closed set).
**Optional Fields:** clock-in/out time (if tracked); notes.
**Business Rules:** field Engineers, who have no login and no app, are not expected to self-report Attendance through the same mechanism office-based roles would — the specific capture mechanism (e.g. inferred from WhatsApp activity, or a separate process) is not decided here.
**Lifecycle:** RECORDED (per day; not further mutated once the day passes, except by an explicit correction workflow, not specified here).
**Validation Rules:** one Attendance record per Employee per date.
**Future Expansion:** the field-Attendance capture mechanism itself (flagged above).

---

### 30. Payroll

**Purpose:** An Employee's computed pay for a period.
**Description:** New object, per `MWO-ENT-001` §5. HR OS calculates; Finance OS disburses — the same separation of concerns already used between LTSA OS's Command Center (presentation) and its Gateways (persistence).
**Owner Module:** HR OS (calculates); Finance OS (disburses, via Expense/Payment-equivalent mechanism not further specified here).
**Relationships:** belongs to Employee; references Attendance (hours/overtime basis) for the same period.
**Required Fields:** Employee reference; pay period; gross amount.
**Optional Fields:** deductions; overtime amount; notes.
**Business Rules:** Payroll disbursement is an OperatingCompany-internal cash movement — never billed to, or visible to, any Customer.
**Lifecycle:** DRAFT → APPROVED → DISBURSED.
**Validation Rules:** one Payroll record per Employee per pay period; gross amount non-negative.
**Future Expansion:** tax/statutory deduction rules, specific to jurisdiction — not specified here.

---

### 31. Expense

**Purpose:** An OperatingCompany operational cost.
**Description:** New object, per `MWO-ENT-001` §4.
**Owner Module:** Finance OS.
**Relationships:** belongs to OperatingCompany; optionally attributed to Project (for Inter-Entity Settlement, §22); optionally references Vendor.
**Required Fields:** expense code; OperatingCompany reference; amount; date; category.
**Optional Fields:** Project reference; Vendor reference; description; receipt/attachment reference.
**Business Rules:** an Expense attributed to a Project is a candidate input to that Project's Inter-Entity Settlement reconciliation (§22 Project, §Open Questions #5).
**Lifecycle:** SUBMITTED → APPROVED → PAID.
**Validation Rules:** amount positive; category required (closed set recommended, not enforced by this specification).
**Future Expansion:** expense category taxonomy, approval-threshold routing.

---

### 32. Purchase

**Purpose:** An OperatingCompany purchase order to a Vendor.
**Description:** New object, per `MWO-ENT-001` §4.
**Owner Module:** Finance OS.
**Relationships:** belongs to OperatingCompany; references Vendor; optionally attributed to Project/Work Order.
**Required Fields:** purchase order code; OperatingCompany reference; Vendor reference; items/description; total amount.
**Optional Fields:** Project or Work Order reference; expected delivery date.
**Business Rules:** a Purchase referencing an inactive Vendor is a validation concern, not silently allowed.
**Lifecycle:** REQUESTED → APPROVED → ORDERED → RECEIVED.
**Validation Rules:** purchase order code unique; total amount positive.
**Future Expansion:** integration with a future Inventory subsystem (§CM Future Expansion) so Purchase receipt can feed stock, which future CM Parts Used could then deduct against.

---

### 33. Vendor

**Purpose:** An OperatingCompany supplier.
**Description:** New object, per `MWO-ENT-001` §4.
**Owner Module:** Finance OS.
**Relationships:** belongs to OperatingCompany; referenced by Purchase, optionally by Expense.
**Required Fields:** vendor code; vendor name; OperatingCompany reference.
**Optional Fields:** contact details; payment terms; category.
**Business Rules:** none beyond standard reference-object integrity.
**Lifecycle:** ACTIVE → INACTIVE.
**Validation Rules:** vendor code unique per OperatingCompany.
**Future Expansion:** vendor performance/rating tracking.

---

### 34. Permission

**Purpose:** A single authorized action, granted to a Role.
**Description:** New object. The atomic unit Role's authorization is built from — deliberately minimal, since no authorization mechanism is specified beyond the object model itself ("No API" per instruction).
**Owner Module:** Enterprise (cross-cutting).
**Relationships:** belongs to Role.
**Required Fields:** permission code; description; Role reference.
**Optional Fields:** none.
**Business Rules:** Owner's Role is the only one whose Permission set includes both-entity visibility (§25 Role).
**Lifecycle:** ACTIVE → (future) RETIRED.
**Validation Rules:** permission code unique per Role.
**Future Expansion:** the actual enforcement mechanism (an authorization engine) is explicitly out of this document's scope ("No API").

---

### 35. Notification

**Purpose:** An outbound alert to a User/Employee/Customer Contact about another object's state change.
**Description:** New object. Polymorphic — references any other object (Work Order assignment, Technical Report ready for review, Billing waiting, PM/CM completion) as its source, per `MWO-ENT-001` §14 ("Notify Supervisor," "Notify Finance when billing required").
**Owner Module:** Agent Layer.
**Relationships:** references a source object (polymorphic — Work Order, Technical Report, Billing, PM, CM, Invoice, etc.); sent to User, Employee, or Customer Contact.
**Required Fields:** notification code; source object type + id; recipient reference; message content; channel (Dashboard/WhatsApp).
**Optional Fields:** priority; read timestamp.
**Business Rules:** a Notification's channel and branding follow the recipient's own entity scope exactly (§1/§6) — a Customer Contact notification is always WhatsApp, always branded Brand = PT Tommy Adji Prasetyo; an internal recipient's notification is always Dashboard-channel, never customer-branded.
**Lifecycle:** PENDING → SENT → READ.
**Validation Rules:** recipient reference must resolve; source object reference must resolve.
**Future Expansion:** additional channels (email, per `MWO-ENT-001` §15's named future Capability providers).

---

### 36. Conversation

**Purpose:** One WhatsApp message thread with an Engineer (or, future, a Customer).
**Description:** New object — the formalization of `MWO-ENT-001` §2/§7's "WhatsApp Message Thread," the durable intake log an Inspection originates from.
**Owner Module:** Agent Layer.
**Relationships:** held with Engineer (by phone number, resolved to Employee); has Conversation Memory; produces Inspection (which becomes PM or CM).
**Required Fields:** conversation id; phone number; Engineer/Employee reference (once resolved); start timestamp; channel (`WHATSAPP`).
**Optional Fields:** end timestamp; raw message log reference.
**Business Rules:** a Conversation from an unrecognized phone number does not resolve to an Employee — the AI LTSA Operator's handling of that case (reject, or a future self-registration flow) is not specified here.
**Lifecycle:** OPEN → (Inspection produced) → CLOSED / RESOLVED.
**Validation Rules:** phone number required; channel currently only `WHATSAPP` (future channels per §15).
**Future Expansion:** Customer-side Conversations (future — Customer never logs in today, but WhatsApp-based customer updates already flow one-way per `MWO-ENT-001` §6; a two-way Customer Conversation is a future extension of this same object, not a new one).

---

### 37. Conversation Memory

**Purpose:** BRAIN's retained context for an in-progress Conversation.
**Description:** New object. Where the AI LTSA Operator's multi-turn state (which fields are already collected, which follow-up question was last asked) is held across a Conversation's turns — the concrete data object behind BRAIN's Observation→Understanding loop (`ADR-002`) persisting mid-conversation, distinct from the Conversation's own raw message log.
**Owner Module:** Agent Layer.
**Relationships:** belongs to exactly one Conversation (1:1).
**Required Fields:** Conversation reference; current extracted-field state (structured, PM/CM-shaped); list of still-missing required fields.
**Optional Fields:** classification hypothesis (PM/CM) if not yet confirmed.
**Business Rules:** cleared/archived once the Conversation's Inspection reaches COMPLETED — it is working state, not a permanent record (the permanent record is the resulting Inspection/PM/CM itself).
**Lifecycle:** ACTIVE (while Conversation is OPEN) → ARCHIVED (on Conversation CLOSED).
**Validation Rules:** exactly one active Conversation Memory per open Conversation.
**Future Expansion:** longer-horizon memory (e.g., "this Engineer usually reports vibration in mm/s, not the unit BRAIN defaults to") — an `ADR-002` Knowledge-level concern, not this object's own v1 scope.

---

### 38. Knowledge Record

**Purpose:** A durable, AI5R-level unit of accumulated maintenance knowledge.
**Description:** New object. The LTSA-specific instance of `ADR-002`'s Knowledge peer asset — owned at the AI5R level (per `ADR-002` §2: "Knowledge is the Enterprise Knowledge Base... owned at the AI5R level, not scoped to any one product"), not privately owned by LTSA OS, even though LTSA OS is its first real contributor. Conceptually parallel to the existing Acquisition Layer's `knowledge_source_registry` (`MWO-LTSA-040A`) but for derived/learned knowledge rather than acquired source documents.
**Owner Module:** Knowledge (AI5R peer asset) — not LTSA OS-owned, per `ADR-002`.
**Relationships:** derived from Failure Pattern, Maintenance History; available, per `ADR-002`, to any future AI5R product's own BRAIN-driven reasoning, not only LTSA OS's.
**Required Fields:** knowledge record code; source reference (Failure Pattern or Maintenance History); knowledge statement (structured or narrative); confidence.
**Optional Fields:** applicable Equipment type/category (for generalization beyond one specific Pump); supporting evidence references.
**Business Rules:** never privately scoped to LTSA OS or to this Customer — per `ADR-002`'s explicit ownership rule, any future AI5R product consuming Knowledge may read it.
**Lifecycle:** DRAFT → VALIDATED (Supervisor or BRAIN-confidence-threshold reviewed) → PUBLISHED.
**Validation Rules:** source reference must resolve; confidence within a defined range.
**Future Expansion:** this object is itself the concrete first step of `ADR-002`'s still-unimplemented Learning → Knowledge closed loop (Migration Strategy Steps 5–6) — its own future is that loop's eventual completion.

---

## Part 6 — Cross Module Usage

| Object | LTSA OS | Finance OS | HR OS | Agent Layer | Enterprise (cross-cutting) |
|---|:---:|:---:|:---:|:---:|:---:|
| Brand | reads | owns | — | reads | owns |
| OperatingCompany | reads | reads | owns | — | owns |
| Customer | reads | owns | — | — | — |
| Customer Contact | reads | owns | — | reads (Notification) | — |
| Contract | — | owns | — | — | — |
| Site / Plant / Area | owns | — | — | — | — |
| Equipment / Asset / Pump / Seal | owns | — | — | — | — |
| Work Order | owns | reads | — | — | — |
| Inspection / PM / CM | owns | — | — | writes (via AI LTSA Operator) | — |
| Maintenance History | owns | — | — | — | — |
| Failure Pattern | owns | — | — | — | reads (Knowledge) |
| Technical Report | owns | reads | — | writes (draft) | — |
| Billing / Invoice / Payment | reads | owns | — | — | — |
| Project | reads | owns | — | — | — |
| Employee | reads (assigned_to) | reads (Payroll disbursement) | owns | reads (identity resolution) | — |
| Department | reads | — | owns | — | reads (Role scoping) |
| Engineer | owns (Inspection performer) | — | — (view of Employee) | reads (Conversation identity) | — |
| Attendance / Payroll | — | reads (disbursement) | owns | — | — |
| Expense / Purchase / Vendor | — | owns | — | — | — |
| User / Role / Permission | reads | reads | reads | — | owns |
| Notification | writes (triggers) | writes (triggers) | writes (triggers) | owns | — |
| Conversation / Conversation Memory | reads (Inspection origin) | — | — | owns | — |
| Knowledge Record | writes (Failure Pattern) | — | — | reads (future BRAIN reasoning) | owns (AI5R peer asset, not any one module's) |

---

This is a specification only. No SQL, code, or API was written. No `AI5R-SDK`, `PRODUCTS/LTSA-BRAIN`, `CORE-SERVICES`, or Runtime file was modified in producing it.

Stop.
