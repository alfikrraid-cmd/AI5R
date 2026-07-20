# MWO-LTSA-057 — Work Order Workspace

Status: **COMPLETED**
Type: Manufacturing Work Order (Implementation)
Role: Implementation Engineer
Architecture: FROZEN — this MWO must not modify Backend, API, Dashboard shell, Pump Workspace, Seal Workspace, Authentication, Notifications, or any design-system component.
Predecessor: `MWO-LTSA-056-Pump-Management-UI-Polish.md` (CLOSED — reviewed and approved by Chief Architect, 2026-07-20).
Basis: Direct read of `AI5R-STUDIO/dashboard/src/modules/ltsa/{pages/Pump.jsx,pages/Pump.css,components/Pump*.jsx,utils/pumpHealth.js}` and `pages/Seal.jsx` as the established module pattern; `AI5R-STUDIO/dashboard/src/design-system/*` read-only, for reuse (`PageHeader`, `SearchBox`, `Table`-equivalent semantic markup, `Badge`, `Card`, `EmptyState`, `Modal`, `Timeline`, `Button`).

---

## Goal

Build the Work Order Workspace for LTSA Demo v1.

## Scope

- Work Order List
- Work Order Detail
- Create Work Order
- Status
- Priority
- Assignment
- Timeline
- Search
- Filter
- Responsive UI
- Tests

## Out of Scope

- Backend
- API
- Dashboard
- Pump Workspace
- Seal Workspace
- Authentication
- Notifications

## Definition of Done

- Work Order Workspace fully functional using sample data.
- Tests passing.
- `ENGINEERING/history.log` updated.

---

## Implementation

Built as a new sibling module page under `modules/ltsa`, following the exact structural pattern already established by `Pump.jsx`/`Seal.jsx` (page + FilterBar + RegistryTable + DetailPanel + module-local `utils` + `data`), reusing the shared design-system components read-only. No new design-system component was introduced; `CreateWorkOrderModal` composes the existing `Modal` and `Button` components with plain styled form fields (`input`/`select`/`textarea`), matching the inline-styling convention already used by `PumpFilterBar`.

**Data model** (`data/sampleWorkOrders.js`, 8 sample records): `id`, `title`, `equipmentTag`, `area`, `workType` (closed set `CM`/`PM`/`INSPECTION`), `status` (closed set `OPEN`/`IN_PROGRESS`/`ON_HOLD`/`COMPLETED`), `priority` (closed set `CRITICAL`/`HIGH`/`MEDIUM`/`LOW`), `assignedTo`, `requestedBy`, `createdDate`, `dueDate`, `description`, `timeline` (array of `{date, event}`). Equipment tags/areas are independent literal values for demo realism — no import/coupling to `samplePumps.js` or `sampleSeals.js`, keeping the module isolated.

**Components:**
- `components/WorkOrderFilterBar.jsx` — search (by ID/title/equipment tag) + status filter, mirrors `PumpFilterBar.jsx` exactly.
- `components/WorkOrderRegistryTable.jsx` — Work Order List. Columns: Work Order (ID/title), Equipment (tag/area), Priority (badge), Assigned To, Due Date, Status (badge). Empty state via design-system `EmptyState` when no rows match, mirroring `PumpRegistryTable.jsx`.
- `components/WorkOrderDetailPanel.jsx` — Work Order Detail. Sections: Work Order Summary (all fields + Priority/Status badges), Description, and a Timeline section built on the existing (previously unused by this module family) design-system `Timeline` component, fed from each work order's `timeline` entries.
- `components/CreateWorkOrderModal.jsx` — Create Work Order (UI only), built on the existing design-system `Modal`. Form fields: Title (required), Equipment Tag, Area, Work Type, Priority, Assigned To, Due Date, Description. Submits raw form values to the parent page; no backend/API call. Cancel/Close reset the form.
- `utils/workOrderStatus.js` — `statusBadgeVariant`/`priorityBadgeVariant` mapping, mirrors `utils/pumpHealth.js`'s pattern for centralizing badge-variant mapping.
- `pages/WorkOrder.jsx` — composes the above; owns search/status-filter/selection state plus the in-memory `workOrders` list (initialized from sample data). `handleCreate` assigns the next sequential `WO-XXXX` id, defaults new work orders to `OPEN` with a seeded one-entry timeline, appends to local state, and selects the new entry — no persistence beyond the page's React state, per "UI only."
- `pages/WorkOrder.css` — two-column flex layout (registry/detail) with a `@media (max-width: 768px)` single-column stack, identical structure to `Pump.css`/`Seal.css`, for Responsive UI.

`WorkOrder.jsx` is not wired into `App.jsx` routing, consistent with `Pump.jsx`/`Seal.jsx`, which are likewise not routed there — the Dashboard shell was not modified, per scope.

## Tests

New test files, one per new source file, following the same testing-library conventions used throughout `modules/ltsa`:
- `utils/workOrderStatus.test.js`
- `components/WorkOrderFilterBar.test.jsx`
- `components/WorkOrderRegistryTable.test.jsx`
- `components/WorkOrderDetailPanel.test.jsx`
- `components/CreateWorkOrderModal.test.jsx`
- `pages/WorkOrder.test.jsx` (page-level integration: header, list rendering, selection, search filter, status filter, empty state, create-work-order flow end to end)
- `pages/WorkOrder.responsive.test.js` (CSS media-query assertion, mirrors `Pump.responsive.test.js`)

Full suite after implementation: **47 test files, 154 tests, all passing** (154 = 121 baseline + 33 new).

## Files Touched

- `AI5R-STUDIO/dashboard/src/modules/ltsa/data/sampleWorkOrders.js` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/utils/workOrderStatus.{js,test.js}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/WorkOrderFilterBar.{jsx,test.jsx}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/WorkOrderRegistryTable.{jsx,test.jsx}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/WorkOrderDetailPanel.{jsx,test.jsx}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/CreateWorkOrderModal.{jsx,test.jsx}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/pages/WorkOrder.{jsx,css}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/pages/WorkOrder.test.jsx` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/pages/WorkOrder.responsive.test.js` (new)
- `ENGINEERING/history.log` (completion entry appended)

No file under Backend, API, Dashboard shell (`App.jsx`), Pump Workspace, Seal Workspace, Authentication, Notifications, or `design-system/` was modified — confirmed by `git status` scoped to those paths (empty).

## Definition of Done — Status

- Work Order Workspace fully functional using sample data — **Met** (List, Detail, Create UI, Search, Filter, Priority, Status, Assignment, Timeline all implemented per §Implementation).
- Tests passing — **Met** (154/154 green).
- Engineering History updated — **Met** (`ENGINEERING/history.log`).

---

Reviewed and approved by Chief Architect (2026-07-20). MWO-LTSA-057 is CLOSED. No commit, no push (files remain uncommitted in the working tree pending separate commit approval). No successor MWO defined yet.
