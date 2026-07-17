# Enterprise Object Model v1.0

Status: ARCHITECTURE — no implementation, no SQL, no code
Basis: Blueprint Vol. II, Ch.5 (Enterprise Object definition) and Ch.4 (OSA Systems catalog) — this document enumerates concrete Enterprise Objects within that already-approved model; it does not redefine what an Enterprise Object is, and does not introduce a System, layer, or mechanism the Blueprint does not already name.
Reuse discipline: where an object is already canonically built (Customer, Pump, Asset, Work Order, Maintenance History — all from `PRODUCTS/LTSA-BRAIN`), its Required/Optional Fields below match the existing canonical schema exactly — no field is renamed or reshaped.

---

## 1. Company

**Purpose:** The tenant organization operating an OSA Instance — the entity OSA Maintenance (and every other OSA System) is manufactured for. Distinct from Customer (§3), which is the tenant's *own* customer.
**Relationships:** Owns Brand (§2), Site (§5), Contract (§4), Employee (§12), Department (§13). Root of the physical/organizational hierarchy.
**Required Fields:** company_code, company_name, status.
**Optional Fields:** legal_name, tax_id, industry, address, country, metadata.
**Business Rules:** Exactly one Company per OSA Instance today (single-tenant, per current LTSA-BRAIN scope); multi-Company support is Future Expansion, not current scope. A Company must exist before any Site, Contract, or Employee is created.
**Lifecycle:** `DRAFT → ACTIVE → SUSPENDED → ARCHIVED`.
**Future Expansion:** Multi-company (holding-company) support; Company-level AI Workforce staffing configuration (Blueprint Vol. II Ch.7).

## 2. Brand

**Purpose:** A named commercial identity a Company operates under, when it operates more than one (e.g., distinct service brands for different customer segments).
**Relationships:** Belongs to Company (§1). May be referenced by Contract (§4) and Invoice (§20) for brand-specific billing presentation.
**Required Fields:** brand_code, brand_name, company_code, status.
**Optional Fields:** logo_ref, description, metadata.
**Business Rules:** A Brand cannot exist without a parent Company. Optional object — an OSA Instance with one Company and no distinct Brands operates without ever creating one.
**Lifecycle:** `ACTIVE → RETIRED`.
**Future Expansion:** Brand-specific Dashboard theming; brand-level reporting rollups.

## 3. Customer

**Purpose:** The Company's own client — who a Contract, Work Order, and Invoice are performed and billed for. **Already canonical** (`PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-005-CUSTOMER-REGISTRY`, `DATABASE/MIGRATIONS/005_create_customer_registry.sql`).
**Relationships:** Has Contract (§4), Site (§5), Work Order (§14), Invoice (§20). Referenced by Work Order via `customer_code`.
**Required Fields (as already canonical):** customer_code, customer_name.
**Optional Fields (as already canonical):** customer_type, industry, tax_id, billing_email, phone, address, city, province, country, notes.
**Business Rules:** `customer_code` is the natural key (unique). A Customer may have zero Contracts (prospect stage) but a Contract cannot exist without a Customer.
**Lifecycle:** `active → inactive` (per existing `status` field, already canonical).
**Future Expansion:** Customer-level dashboard rollup (extending `BP-DASHBOARD`'s existing aggregation pattern); Customer-specific AI Workforce recommendations via the Basic AI Assistant (already manufactured under MO-001).

## 4. Contract

**Purpose:** The formal agreement governing work performed for a Customer. Directly named in the frozen Blueprint (Vol. II, Ch.5): *"LTSA Contract — a Long Term Service Agreement, one example among many possible contract types."*
**Relationships:** Belongs to Customer (§3) and Company (§1); may reference Brand (§2). Governs which Sites/Plants/Assets are in scope; referenced by Work Order (§14) and Billing (§19) for entitlement checks.
**Required Fields:** contract_code, customer_code, contract_type, start_date, status.
**Optional Fields:** end_date, scope_description, billing_terms, sla_terms, metadata.
**Business Rules:** A Work Order performed outside an active Contract's scope/date range is a business exception to flag, not silently permit (design intent; enforcement is future implementation). `contract_type` is open-ended — LTSA is one value, not the only one.
**Lifecycle:** `DRAFT → ACTIVE → EXPIRED / TERMINATED → RENEWED (new Contract, references prior via metadata)`.
**Future Expansion:** SLA breach detection feeding the Basic AI Assistant; automatic Invoice generation on Contract billing milestones.

## 5. Site

**Purpose:** A physical customer location (e.g., a refinery, a factory complex) — the top of the physical asset hierarchy.
**Relationships:** Belongs to Customer (§3) (or Company §1, for the tenant's own sites). Contains Plant (§6). Referenced by Work Order for location context.
**Required Fields:** site_code, site_name, customer_code, status.
**Optional Fields:** address, city, province, country, gps_coordinates, metadata.
**Business Rules:** A Site belongs to exactly one Customer (or the operating Company). Formalizes what is today an informal `area`/location string on `ltsa_pumps`/`asset_registry`/`soot_blower_registry` — this is additive structure, not a redesign of those existing tables' fields.
**Lifecycle:** `ACTIVE → INACTIVE`.
**Future Expansion:** Site-level Dashboard rollup; geofencing for field technician dispatch.

## 6. Plant

**Purpose:** A production unit within a Site (e.g., "Boiler Plant," "Utility Plant").
**Relationships:** Belongs to Site (§5). Contains Area (§7).
**Required Fields:** plant_code, plant_name, site_code, status.
**Optional Fields:** plant_type, description, metadata.
**Business Rules:** A Plant cannot exist without a parent Site. Optional intermediate layer — a small Site may go directly to Area without a named Plant.
**Lifecycle:** `ACTIVE → DECOMMISSIONED`.
**Future Expansion:** Plant-level production/downtime correlation with Work Order history.

## 7. Area

**Purpose:** A named zone within a Plant (e.g., "Boiler House," matching the `boiler_area` field already used by `soot_blower_registry`, and the `area` field already used by `ltsa_pumps`/`asset_registry`). Formalizes an existing informal string field into a first-class object.
**Relationships:** Belongs to Plant (§6). Contains Asset (§8), Equipment (§9), Pump (§10).
**Required Fields:** area_code, area_name, plant_code, status.
**Optional Fields:** description, metadata.
**Business Rules:** Existing `area`/`boiler_area` TEXT columns on already-canonical tables remain free-text today; this object is the future canonical target those columns would resolve against (a Relationship Resolution use case, per UMC-001 Stage 5 — see MWO-LTSA-052's research). No existing column is renamed by this document.
**Lifecycle:** `ACTIVE → INACTIVE`.
**Future Expansion:** Formal `area_code` foreign-key resolution from the existing free-text `area` columns, once an Area Identity/Relationship Resolver is implemented (per UMC-001/UMR-001).

## 8. Asset

**Purpose:** General equipment not covered by a more specific type (Pump, Soot Blower). **Already canonical** (`BUILD-PACKS/BP-ASSET`, manufactured under MO-001).
**Relationships:** Belongs to Area (§7) (today, informally, via its own `area` TEXT field). Referenced by Work Order (§14) and Maintenance History via the documented polymorphic `(asset_code, asset_type)` pair.
**Required Fields (as already canonical):** asset_code, asset_name.
**Optional Fields (as already canonical):** asset_type, area, manufacturer, model, status.
**Business Rules:** `asset_code` is the natural key. `asset_type` distinguishes this row from Pump/Soot Blower at the polymorphic-reference layer (per MO-001's documented design constraint — no common supertype table exists, and none is introduced here).
**Lifecycle:** `ACTIVE → DECOMMISSIONED` (per existing `status` field).
**Future Expansion:** Promoting Asset/Pump/Soot Blower to genuinely share an `Equipment` supertype (§9) is a real future architectural question — named here, not resolved.

## 9. Equipment

**Purpose:** The conceptual umbrella type that Pump (§10), Asset (§8), and (elsewhere) Seal and Soot Blower specialize — consistent with Blueprint Vol. II Ch.10's already-approved rule that a System may hold *"System-specific specializations of Enterprise Objects"* while remaining one shared underlying concept.
**Relationships:** Generalizes Asset (§8), Pump (§10); conceptually also Seal and Soot Blower Registry (already canonical, not in this 30-object list). Located in Area (§7).
**Required Fields:** *(conceptual umbrella only — no canonical table of its own exists or is proposed here)*.
**Optional Fields:** *(none — see Business Rules)*.
**Business Rules:** Equipment is **not** proposed as a new canonical table today — MO-001's Work Order/Maintenance History design deliberately avoided inventing a supertype table (documented constraint, not an oversight). This entry records Equipment as the *conceptual* category the other specific objects already instantiate, for modeling completeness, matching how UMC-001's own Relationship Resolution stage is specified against natural-key cross-references rather than a supertype join.
**Lifecycle:** N/A — conceptual category, not an instantiated object.
**Future Expansion:** If a real supertype table is ever justified by evidence (e.g., cross-equipment reporting needs that the polymorphic pattern cannot serve), that would be a new ADR-level architectural decision, not an incremental addition — flagged, not decided, here.

## 10. Pump

**Purpose:** A rotating equipment asset, the product's original and most complete domain object. **Already canonical** (`MODULES/PUMP/DATABASE/001_create_pumps.sql`, table `ltsa_pumps`).
**Relationships:** Belongs to Area (§7) (via existing `area` field). Referenced by Work Order, Maintenance History (`asset_type="pump"`). Has a Compatibility relationship to Mechanical Seal (already-identified gap, see MWO-LTSA-051/052).
**Required Fields (as already canonical):** tag_number, area.
**Optional Fields (as already canonical):** location, pump_type, api_plan, seal_type, status, manufacturer, model, drawing_ref, notes.
**Business Rules:** `tag_number` is the natural key (unique). `seal_type` is a not-yet-resolved relationship reference to Mechanical Seal's canonical `seal_code` — an open, named gap (MWO-LTSA-052 §3/§6), not resolved by this document.
**Lifecycle:** `UNKNOWN → <operational status values>` (per existing `status` field, default `'UNKNOWN'`).
**Future Expansion:** Concrete `IdentityResolver`/`RelationshipResolver` implementation against `tag_number`/`seal_type`, per UMC-001 Stage 4/5 — already scoped as LTSA-BRAIN's first intended implementation in the platform's own specs.

## 11. Engineer

**Purpose:** A specialized Employee (§12) role — technical staff who perform Inspection (§15), PM Record (§16), and CM Record (§17) work, and are assigned to Work Orders.
**Relationships:** Specializes Employee (§12). Assigned to Work Order (`assigned_to`, already an existing field on the canonical `work_order` table). Performs Inspection, PM Record, CM Record.
**Required Fields:** engineer_code, employee_code, discipline, status.
**Optional Fields:** certification, specialization, metadata.
**Business Rules:** An Engineer record cannot exist without a corresponding Employee record — it is a role overlay, not a parallel person record (avoids duplicating name/contact data).
**Lifecycle:** `ACTIVE → INACTIVE` (tied to the underlying Employee's employment status).
**Future Expansion:** Skill-based Work Order auto-assignment (an AI Workforce capability, per Blueprint Vol. II Ch.7); Engineer performance analytics.

## 12. Employee

**Purpose:** A person employed by the Company (§1) — the general HR record every specialized role (Engineer, and future roles) overlays.
**Relationships:** Belongs to Company (§1) and Department (§13). Specialized by Engineer (§11) where applicable. Referenced by Payroll (§25), Leave (§26), Attendance (§27), User (§28).
**Required Fields:** employee_code, employee_name, department_code, status.
**Optional Fields:** position_title, hire_date, contact_email, contact_phone, metadata.
**Business Rules:** `employee_code` is the natural key. An Employee belongs to exactly one Department at a time (transfers create a new department assignment, not a rewrite of history — design intent, not yet implemented).
**Lifecycle:** `ONBOARDING → ACTIVE → ON_LEAVE → TERMINATED`.
**Future Expansion:** Mapping Employee to AI Workforce's six-level hierarchy (Blueprint Vol. II Ch.7) for human/AI Workforce collaboration, per Volume I Ch.7's stated principle that a human may direct the same Manager/Employee AI roles an AI Director would.

## 13. Department

**Purpose:** An organizational unit within the Company (§1) that Employees belong to (e.g., "Maintenance," "Finance," "HR").
**Relationships:** Belongs to Company (§1). Contains Employee (§12).
**Required Fields:** department_code, department_name, company_code, status.
**Optional Fields:** parent_department_code (for nested departments), cost_center, metadata.
**Business Rules:** `parent_department_code` allows a department hierarchy (mirroring the already-real `DepartmentRegistry.hierarchy()` pattern found in `AI5R-SDK/ORGANIZATION/department_registry.py` during this session's earlier architecture audits — reused conceptually here, not as a code dependency).
**Lifecycle:** `ACTIVE → MERGED / DISSOLVED`.
**Future Expansion:** Department-level OSA System staffing (which AI Workforce roles are assigned per department, per Blueprint Vol. II Ch.7).

## 14. Work Order

**Purpose:** A unit of maintenance work against an Asset/Equipment. **Already canonical** (`BUILD-PACKS/BP-WORK-ORDER`, manufactured under MO-001).
**Relationships:** References Customer (`customer_code`) and a polymorphic Asset reference (`asset_code`, `asset_type` — pump/seal/asset/soot_blower). Produces Maintenance History (§16/§17 relate here) on closure. May reference Contract (§4) for billing entitlement (not yet wired).
**Required Fields (as already canonical):** work_order_code, description.
**Optional Fields (as already canonical):** customer_code, asset_code, asset_type, priority, status, assigned_to, closed_at.
**Business Rules:** `work_order_code` is the natural key. Status defaults `OPEN`, priority defaults `NORMAL` (already-canonical defaults). Closing a Work Order should produce a Maintenance History record — currently a manual, separate call (per MO-001's Demo script), not an enforced trigger.
**Lifecycle:** `OPEN → IN_PROGRESS → CLOSED` (`CANCELLED` also possible; `closed_at` timestamp on closure).
**Future Expansion:** Automatic Maintenance History creation on Work Order closure; Basic AI Assistant-generated recommendation attached at creation time (the reasoning capability already exists per MO-001, wiring it to Work Order creation does not).

## 15. Inspection

**Purpose:** A scheduled or ad hoc examination of an Asset/Equipment, producing findings that may generate a Work Order. **Declared but not built** — `product.manifest.json` lists `inspection` as `"missing"` (confirmed by MWO-P-001's audit; unchanged since).
**Relationships:** Performed by Engineer (§11) against an Asset/Equipment (polymorphic reference, same pattern as Work Order). May produce Work Order (§14) or Technical Report (§18).
**Required Fields:** inspection_code, asset_code, asset_type, inspection_date, status.
**Optional Fields:** engineer_code, findings, severity, notes, metadata.
**Business Rules:** An Inspection's `findings` field is the natural input to the Basic AI Assistant's `get_maintenance_recommendation()` (already manufactured, per MO-001) — this is a direct, evidence-grounded reuse opportunity, not a new mechanism.
**Lifecycle:** `SCHEDULED → IN_PROGRESS → COMPLETED → (Work Order raised, optional)`.
**Future Expansion:** Direct wiring to the Basic AI Assistant (`asset_code`, `findings_text`, `vibration`, `temperature` map cleanly onto the Assistant's existing parameters); this is the single most evidence-supported near-term expansion in this entire model.

## 16. PM Record

**Purpose:** A Preventive Maintenance record — planned, scheduled maintenance performed on a fixed interval. A specialization of the already-canonical Maintenance History (§17 shares this parent) distinguishing planned from reactive work.
**Relationships:** Specializes Maintenance History (already canonical, `BUILD-PACKS/BP-MAINTENANCE-HISTORY`). References Work Order (§14) and Asset/Equipment (polymorphic).
**Required Fields:** pm_record_code, asset_code, asset_type, scheduled_date, status.
**Optional Fields:** work_order_code, performed_by, interval_days, notes.
**Business Rules:** A PM Record's completion should write a Maintenance History row with `action_taken` reflecting the planned task — reuses the existing table, does not duplicate it.
**Lifecycle:** `SCHEDULED → DUE → COMPLETED / OVERDUE`.
**Future Expansion:** Interval-based auto-generation of the next PM Record on completion (a scheduling capability not yet present anywhere in this product).

## 17. CM Record

**Purpose:** A Corrective Maintenance record — reactive maintenance performed in response to a failure or Inspection finding, as opposed to PM Record's (§16) planned cadence. Also a specialization of Maintenance History.
**Relationships:** Specializes Maintenance History (already canonical). References Work Order (§14), Inspection (§15) (as the likely trigger), and Asset/Equipment (polymorphic).
**Required Fields:** cm_record_code, asset_code, asset_type, failure_date, status.
**Optional Fields:** work_order_code, inspection_code, root_cause, performed_by, notes.
**Business Rules:** Distinguished from PM Record by trigger, not by table — both write to the same canonical `maintenance_history` table with a `record_type` distinction (an additive field, not a new table) in a future implementation.
**Lifecycle:** `REPORTED → IN_PROGRESS → COMPLETED`.
**Future Expansion:** Root-cause pattern analysis across CM Records, feeding BRAIN's existing hypothesis-generation logic (`AI5R-SDK/BRAIN/hypothesis_engine.py`, already real and tested, per this session's MWO-OSA-006 audit) with real historical failure data rather than a single observation.

## 18. Technical Report

**Purpose:** A formal document summarizing Inspection findings, Work Order outcomes, or CM Record root-cause analysis for customer or internal record. Corresponds to the `Document` Enterprise Object already named as an example in the frozen Blueprint (Vol. II, Ch.5: *"Cognitive and Governance: Knowledge, Document..."*).
**Relationships:** References Inspection (§15), Work Order (§14), CM Record (§17), Customer (§3).
**Required Fields:** report_code, report_type, subject_reference, issued_date, status.
**Optional Fields:** author_employee_code, summary, attachment_ref, metadata.
**Business Rules:** A Technical Report is a read-facing artifact — it summarizes other objects' data, it does not itself trigger business logic. `subject_reference` is polymorphic (may point to an Inspection, Work Order, or CM Record).
**Lifecycle:** `DRAFT → ISSUED → SUPERSEDED`.
**Future Expansion:** Auto-drafting a Technical Report summary from the Basic AI Assistant's `rationale`/`recommendation` output (already produced today, per MO-001's captured real output) — a direct, low-effort reuse once Inspection (§15) is built.

## 19. Billing

**Purpose:** The aggregation point between completed billable work (Work Order, Contract terms) and Invoice generation — the record of *what* is billable, before an Invoice formalizes *how much, to whom*.
**Relationships:** References Contract (§4), Customer (§3), Work Order (§14). Produces Invoice (§20).
**Required Fields:** billing_code, customer_code, billing_period, status.
**Optional Fields:** contract_code, line_items, notes.
**Business Rules:** Billing aggregates zero or more Work Orders/Contract milestones into one billing cycle; it does not itself represent money owed (that is Invoice's job).
**Lifecycle:** `OPEN → FINALIZED → INVOICED`.
**Future Expansion:** Automatic Billing aggregation from closed Work Orders within a Contract's billing terms.

## 20. Invoice

**Purpose:** A formal request for payment issued to a Customer, derived from Billing (§19).
**Relationships:** Belongs to Customer (§3), derived from Billing (§19). Referenced by Payment (§21).
**Required Fields:** invoice_code, customer_code, invoice_date, amount, status.
**Optional Fields:** billing_code, due_date, tax_amount, notes.
**Business Rules:** An Invoice's `amount` is set at issuance and not silently altered — a correction requires a credit note (Future Expansion), not an in-place edit.
**Lifecycle:** `DRAFT → ISSUED → PAID / OVERDUE / VOID`.
**Future Expansion:** Credit note object; automated overdue-invoice alerting (an AI Workforce notification capability).

## 21. Payment

**Purpose:** A record of money received against an Invoice.
**Relationships:** Belongs to Invoice (§20).
**Required Fields:** payment_code, invoice_code, payment_date, amount, status.
**Optional Fields:** payment_method, reference_number, notes.
**Business Rules:** Sum of Payments against an Invoice should not exceed the Invoice's `amount` (a validation rule for future implementation, stated here as intent). Multiple partial Payments may close one Invoice.
**Lifecycle:** `PENDING → CONFIRMED → RECONCILED`.
**Future Expansion:** Bank reconciliation integration (an external-service dependency, out of current scope).

## 22. Vendor

**Purpose:** A third-party supplier the Company purchases goods or services from (e.g., seal/pump parts suppliers).
**Relationships:** Referenced by Purchase (§23) and Expense (§24).
**Required Fields:** vendor_code, vendor_name, status.
**Optional Fields:** contact_email, contact_phone, address, tax_id, metadata.
**Business Rules:** `vendor_code` is the natural key. A Vendor is independent of Customer (§3) — a single external company could, in principle, be both, but this model does not merge the two object types.
**Lifecycle:** `ACTIVE → INACTIVE / BLACKLISTED`.
**Future Expansion:** Vendor performance scoring against Purchase Order lead time and quality.

## 23. Purchase

**Purpose:** A purchase order raised against a Vendor (e.g., ordering a replacement seal or pump part).
**Relationships:** References Vendor (§22). May reference Work Order (§14) or PM Record (§16) as the originating need (e.g., a part required to complete scheduled maintenance).
**Required Fields:** purchase_code, vendor_code, order_date, status.
**Optional Fields:** line_items, expected_delivery_date, work_order_code, notes.
**Business Rules:** A Purchase should reference the Work Order/PM Record that necessitated it when one exists, for traceability — not enforced today, a documented intent.
**Lifecycle:** `DRAFT → ORDERED → RECEIVED → CLOSED`.
**Future Expansion:** Auto-generating a Purchase draft from a Work Order's parts requirement, once parts/BOM data exists on Asset/Equipment (not modeled yet).

## 24. Expense

**Purpose:** A recorded cost not tied to a formal Purchase Order (e.g., incidental field expenses, travel for an Engineer's site visit).
**Relationships:** May reference Employee (§12) (who incurred it), Vendor (§22) (who was paid), Work Order (§14) (what it was for).
**Required Fields:** expense_code, amount, expense_date, status.
**Optional Fields:** employee_code, vendor_code, work_order_code, category, notes.
**Business Rules:** Expense is deliberately lighter-weight than Purchase (§23) — no vendor relationship or delivery tracking required, since it covers incidental costs, not procurement.
**Lifecycle:** `SUBMITTED → APPROVED / REJECTED → REIMBURSED`.
**Future Expansion:** Expense-to-Work-Order cost rollup for true job costing.

## 25. Payroll

**Purpose:** A periodic compensation record for an Employee.
**Relationships:** Belongs to Employee (§12).
**Required Fields:** payroll_code, employee_code, pay_period, gross_amount, status.
**Optional Fields:** deductions, net_amount, notes.
**Business Rules:** Payroll is computed per pay period per Employee; it references but does not modify Leave (§26)/Attendance (§27) records — those are inputs to a (future) payroll calculation, not owned by Payroll itself.
**Lifecycle:** `DRAFT → APPROVED → PAID`.
**Future Expansion:** Automated payroll computation incorporating Attendance and approved Leave.

## 26. Leave

**Purpose:** A record of an Employee's approved time off.
**Relationships:** Belongs to Employee (§12).
**Required Fields:** leave_code, employee_code, leave_type, start_date, end_date, status.
**Optional Fields:** reason, approved_by, notes.
**Business Rules:** Overlapping Leave records for the same Employee are a data-integrity concern for future validation, not enforced by this architecture document.
**Lifecycle:** `REQUESTED → APPROVED / REJECTED → TAKEN`.
**Future Expansion:** Leave-aware Work Order/Engineer assignment (do not assign a Work Order to an Engineer on approved Leave).

## 27. Attendance

**Purpose:** A daily record of an Employee's presence/absence, distinct from Leave (§26), which is a planned, approved absence.
**Relationships:** Belongs to Employee (§12).
**Required Fields:** attendance_code, employee_code, attendance_date, status.
**Optional Fields:** check_in_time, check_out_time, notes.
**Business Rules:** Attendance is a daily-granularity record; it is the input Payroll (§25) would eventually reconcile against Leave.
**Lifecycle:** `RECORDED` (a log entry; no further state transitions in this model).
**Future Expansion:** Mobile/field check-in for Engineers at Site (§5), tying Attendance to physical location.

## 28. User

**Purpose:** A system login identity — the platform-access counterpart to a human Employee (or, per Blueprint Vol. II Ch.7, potentially an AI Workforce role's operating identity).
**Relationships:** Usually corresponds 1:1 to an Employee (§12), but is a distinct object — a User account can be deactivated independently of an Employee's HR status (e.g., access suspended pending investigation, employment otherwise continuing). Has Role (§29).
**Required Fields:** user_code, username, employee_code, status.
**Optional Fields:** email, last_login_at, metadata.
**Business Rules:** A User must reference exactly one Employee (or, in the AI Workforce case, one AI role identity — a future extension, not modeled here). Authentication mechanics are explicitly out of scope for this architecture document (no such mechanism exists anywhere in this repository today, confirmed across multiple prior audits this session).
**Lifecycle:** `ACTIVE → SUSPENDED → DEACTIVATED`.
**Future Expansion:** Mapping User to AI Workforce identities for human/AI collaborative sessions (Blueprint Vol. I Ch.7's "a human employee may work alongside Employee AI").

## 29. Role

**Purpose:** A named collection of Permissions (§30) assignable to a User (§28) — e.g., "Engineer," "Finance Clerk," "Administrator."
**Relationships:** Assigned to User (§28). Composed of Permission (§30).
**Required Fields:** role_code, role_name, status.
**Optional Fields:** description, metadata.
**Business Rules:** A Role is a named bundle, not a per-user customization — individual permission overrides per User are Future Expansion, not modeled here.
**Lifecycle:** `ACTIVE → RETIRED`.
**Future Expansion:** Mapping Role to the Blueprint's six-level AI Workforce hierarchy (Vol. II Ch.7) for a unified human+AI permission model — a genuinely open architectural question this document does not resolve.

## 30. Permission

**Purpose:** The atomic, named grant of ability to perform an action on an Enterprise Object or invoke a Capability (Blueprint Vol. II, Ch.6) — e.g., "Work Order: Close," "Invoice: Issue."
**Relationships:** Composed into Role (§29). Conceptually adjacent to, but distinct from, Capability (already defined and canonical per `AI5R-SDK/CAPABILITY/` and ADR-003) — a Permission gates *who may invoke* a Capability or act on an object; it is not itself a unit of executable business function.
**Required Fields:** permission_code, permission_name, resource_type, action, status.
**Optional Fields:** description, metadata.
**Business Rules:** `resource_type` names the Enterprise Object this Permission governs (e.g. `"work_order"`); `action` names the operation (e.g. `"close"`). No enforcement mechanism exists in the repository today — this is a data model for a future authorization layer, not a working one.
**Lifecycle:** `ACTIVE → DEPRECATED`.
**Future Expansion:** Wiring Permission checks into the existing n8n workflow pattern (a validation node ahead of each Update/Delete workflow, following the same structural convention already proven for conflict-checks under MO-001); reconciling Permission with Capability (ADR-003) so that "may invoke this Capability" and "has this Permission" are one coherent authorization model, not two parallel ones.

---

## Cross-Cutting Notes

- **No object above requires modification to a canonical schema that already exists.** Customer, Pump, Asset, Work Order, and Maintenance History are described exactly as already built; every other object is new architecture-only definition, not yet implemented.
- **Polymorphic references** (Work Order/Maintenance History/Inspection/PM Record/CM Record → Asset/Equipment/Pump) consistently reuse the `(asset_code, asset_type)` pattern already established and documented under MO-001 — no new cross-reference mechanism is introduced.
- **Two genuinely open architectural questions are named, not resolved, by this document:** (1) whether Equipment (§9) ever becomes a real supertype table, and (2) how Role/Permission (§29/§30) reconciles with the already-canonical Capability model (ADR-003). Both require a future ADR-level decision, not an implementation shortcut.

---

Architecture only. No code, no SQL, no implementation performed in producing this document.
