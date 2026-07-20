# MWO-LTSA-058 — Preventive Maintenance Workspace

Status: **COMPLETED**
Type: Manufacturing Work Order (Implementation)
Role: Implementation Engineer
Architecture: FROZEN — this MWO must not modify Backend, API, Scheduler Engine, Notifications, Authentication, Dashboard KPI, Work Order Workspace, Pump Workspace, or any design-system component.
Predecessor: `MWO-LTSA-057-Work-Order-Workspace.md` (CLOSED — reviewed and approved by Chief Architect, 2026-07-20).
Basis: Direct read of the Pump (`pages/Pump.jsx`, `components/Pump*.jsx`, `utils/pumpHealth.js`) and Work Order (`pages/WorkOrder.jsx`, `components/WorkOrder*.jsx`, `components/CreateWorkOrderModal.jsx`, `utils/workOrderStatus.js`) modules as the established architecture to follow exactly; `AI5R-STUDIO/dashboard/src/design-system/*` read-only, for reuse.

---

## Goal

Build the Preventive Maintenance Workspace for LTSA Demo v1.

## Scope

- PM Schedule List
- PM Detail
- Create PM Schedule (UI only)
- Frequency (Daily, Weekly, Monthly, Runtime-based)
- Next Due
- Last Performed
- Assigned Technician
- Search
- Filter
- Status
- Responsive UI
- Sample data
- Tests

## Out of Scope

- Backend
- API
- Scheduler engine
- Notifications
- Authentication
- Dashboard KPI
- Work Order
- Pump Workspace

## Definition of Done

- PM Workspace fully functional using sample data.
- Responsive UI.
- Tests passing.
- `ENGINEERING/history.log` updated.
- `CURRENT_MWO.md` updated.

---

## Implementation

Built as a third sibling module page under `modules/ltsa`, following the Pump/Work Order structural pattern exactly (page + FilterBar + list Table + DetailPanel + Create modal + module-local `utils`/`data`), reusing shared design-system components read-only (`PageHeader`, `SearchBox`, `Badge`, `Card`, `EmptyState`, `Modal`, `Timeline`, `Button`) — no design-system file modified.

**Data model** (`data/samplePMSchedules.js`, 8 sample records): `id`, `equipmentTag`, `area`, `procedure`, `frequency` (closed set `DAILY`/`WEEKLY`/`MONTHLY`/`RUNTIME_BASED`), `triggerType` (closed set `CALENDAR`/`METER`), `checklist` (array), `lastPerformed`, `nextDue`, `assignedTechnician`, `estimatedDurationHours`, `relatedWorkOrders` (array of WO-id strings — literal values, no import/coupling to `sampleWorkOrders.js`, keeping the module isolated per the same judgment already applied between Pump and Work Order), `status` (closed set `ACTIVE`/`DUE_SOON`/`OVERDUE`/`ON_HOLD`), `timeline` (array of `{date, event}`).

**Components:**
- `components/PMFilterBar.jsx` — search (by PM ID/procedure/equipment tag) + status filter, mirrors `WorkOrderFilterBar.jsx`/`PumpFilterBar.jsx` exactly.
- `components/PMScheduleTable.jsx` — PM Schedule List. Columns exactly as specified: PM ID, Equipment, Frequency (badge, human-readable label), Next Due, Last Performed (falls back to "Not yet performed"), Assigned Technician, Status (badge). Empty state via design-system `EmptyState`.
- `components/PMDetailPanel.jsx` — PM Detail. Sections: PM Schedule Summary (Equipment, Trigger Type, Last Performed, Next Due, Assigned Technician, Estimated Duration, Frequency badge, Status badge — Trigger Type and Status added beyond the literal field list as CMMS-realism enrichment, following the same precedent set in the Work Order Detail Panel), Checklist (rendered as a semantic list), Related Work Orders (UI placeholder — badges, or a "No related work orders." fallback, no navigation wired), and a Timeline section built on the design-system `Timeline` component.
- `components/CreatePMScheduleModal.jsx` — Create PM Schedule (UI only), built on the design-system `Modal`. Form fields exactly as specified: Equipment (required), Frequency, Trigger Type, Technician, Start Date, Estimated Duration, Checklist Template (a fixed set of 4 named templates, e.g. "Standard Lubrication Checklist", each resolving to a concrete checklist array — no backend). Submits resolved values to the parent page; Save/Cancel reset the form. No `Procedure` field exists in the Create form per the specified field list, so the new schedule's `procedure` title is derived from the selected Checklist Template name (e.g. "Standard Lubrication Checklist" → "Standard Lubrication").
- `utils/pmStatus.js` — `statusBadgeVariant`/`frequencyBadgeVariant`/`frequencyLabel`/`triggerTypeLabel`, mirrors the `pumpHealth.js`/`workOrderStatus.js` pattern for centralizing badge-variant/label mapping.
- `pages/PM.jsx` — composes the above; owns search/status-filter/selection state plus the in-memory `pmSchedules` list (initialized from sample data). `handleCreate` assigns the next sequential `PM-XXXX` id, defaults new schedules to `ACTIVE` with `lastPerformed: null` and a seeded one-entry timeline, appends to local state, and selects the new entry — no persistence beyond the page's React state, per "UI only."
- `pages/PM.css` — two-column flex layout (list/detail) with a `@media (max-width: 768px)` single-column stack, identical structure to `Pump.css`/`Seal.css`/`WorkOrder.css`, for Responsive UI.

`PM.jsx` is not wired into `App.jsx` routing, consistent with `Pump.jsx`/`Seal.jsx`/`WorkOrder.jsx`, which are likewise not routed there — the Dashboard shell was not modified, per scope.

## Tests

New test files, one per new source file, following the same testing-library conventions used throughout `modules/ltsa`:
- `utils/pmStatus.test.js`
- `components/PMFilterBar.test.jsx`
- `components/PMScheduleTable.test.jsx`
- `components/PMDetailPanel.test.jsx`
- `components/CreatePMScheduleModal.test.jsx`
- `pages/PM.test.jsx` (page-level integration: header, list rendering, selection, search filter, status filter, empty state, create-PM-schedule flow end to end)
- `pages/PM.responsive.test.js` (CSS media-query assertion)

Full suite after implementation: **54 test files, 196 tests, all passing** (196 = 154 baseline + 42 new).

## Files Touched

- `AI5R-STUDIO/dashboard/src/modules/ltsa/data/samplePMSchedules.js` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/utils/pmStatus.{js,test.js}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/PMFilterBar.{jsx,test.jsx}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/PMScheduleTable.{jsx,test.jsx}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/PMDetailPanel.{jsx,test.jsx}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/CreatePMScheduleModal.{jsx,test.jsx}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/pages/PM.{jsx,css}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/pages/PM.test.jsx` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/pages/PM.responsive.test.js` (new)
- `ENGINEERING/history.log` (completion entry appended)

No file under Backend, API, Scheduler engine, Notifications, Authentication, Dashboard KPI/shell (`App.jsx`), Work Order Workspace, Pump Workspace, or `design-system/` was modified — confirmed by `git status` scoped to those paths (empty aside from a pre-existing, unrelated `CORE-SERVICES/MODULE-MANAGER/DATA/modules.json` diff already flagged in the prior classification report and not touched in this MWO).

## Definition of Done — Status

- PM Workspace fully functional using sample data — **Met** (PM Schedule List, PM Detail, Create PM Schedule UI, Frequency, Next Due, Last Performed, Assigned Technician, Search, Filter, Status all implemented per §Implementation).
- Responsive UI — **Met** (`PM.css` two-column layout collapsing under 768px, verified by `PM.responsive.test.js`).
- Tests passing — **Met** (196/196 green).
- Engineering History updated — **Met** (`ENGINEERING/history.log`).
- `CURRENT_MWO.md` updated — **Met**.

---

Reviewed and approved by Chief Architect (2026-07-20). MWO-LTSA-058 is CLOSED. No commit, no push in this step (files remain uncommitted in the working tree pending separate commit approval). No successor MWO defined yet.
