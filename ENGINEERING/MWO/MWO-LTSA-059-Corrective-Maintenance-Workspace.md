# MWO-LTSA-059 — Corrective Maintenance Workspace

Status: **ACTIVE → Definition of Done met, awaiting review.**
Type: Manufacturing Work Order (Implementation)
Role: Implementation Engineer
Architecture: FROZEN — this MWO must not modify Backend, API, Workflow Engine, Notifications, Authentication, Dashboard KPI, Analytics, or any design-system component.
Predecessor: `MWO-LTSA-058-Preventive-Maintenance-Workspace.md` (CLOSED — reviewed and approved by Chief Architect, 2026-07-20).
Basis: Direct read of the Pump, Work Order, and Preventive Maintenance modules (`pages/{Pump,WorkOrder,PM}.jsx`, their `components/*.jsx`, and `utils/{pumpHealth,workOrderStatus,pmStatus}.js`) as the established architecture to follow exactly; `AI5R-STUDIO/dashboard/src/design-system/*` read-only, for reuse.

---

## Goal

Build the Corrective Maintenance Workspace for LTSA Demo v1.

## Business Context

This workspace manages reactive maintenance activities after equipment failures. It should naturally integrate with the existing Pump, Work Order, and Preventive Maintenance modules through consistent UI patterns, while remaining UI-only in this sprint.

## Scope

- Corrective Maintenance List
- Corrective Maintenance Detail
- Create Corrective Maintenance Report (UI only)
- Failure Category
- Failure Severity
- Root Cause
- Immediate Action
- Corrective Action
- Downtime
- Priority
- Assigned Technician
- Related Pump
- Related Work Order
- Timeline
- Search
- Filter
- Responsive UI
- 8 realistic sample records
- Tests

## Out of Scope

- Backend
- API
- Workflow engine
- Notifications
- Authentication
- Dashboard KPI
- Analytics
- Automatic WO generation

## Definition of Done

- Corrective Maintenance Workspace fully functional using sample data.
- UI follows existing LTSA module architecture.
- Responsive layout.
- Tests passing.
- `ENGINEERING/history.log` updated.
- `CURRENT_MWO.md` updated.

---

## Implementation

Built as a fourth sibling module page under `modules/ltsa`, following the Pump/Work Order/PM structural pattern exactly (page + FilterBar + list Table + DetailPanel + Create modal + module-local `utils`/`data`), reusing shared design-system components read-only (`PageHeader`, `SearchBox`, `Badge`, `Card`, `EmptyState`, `Modal`, `Timeline`, `Button`) — no design-system file modified.

**Data model** (`data/sampleCMReports.js`, 8 sample records): `id`, `equipmentTag`, `area`, `failureCategory` (closed set `MECHANICAL`/`ELECTRICAL`/`SEAL_FAILURE`/`INSTRUMENTATION`/`PROCESS`), `severity` (closed set `MINOR`/`MODERATE`/`MAJOR`/`CRITICAL`), `priority` (closed set `CRITICAL`/`HIGH`/`MEDIUM`/`LOW`, same shape as Work Order's priority for cross-module consistency), `failureDescription`, `rootCause`, `immediateAction`, `correctiveAction`, `downtimeHours`, `assignedTechnician`, `relatedPump` (equipment-tag string), `relatedWorkOrder` (WO-id string or `null`), `status` (closed set `OPEN`/`IN_PROGRESS`/`RESOLVED`/`CLOSED`), `timeline` (array of `{date, event}`). `relatedPump`/`relatedWorkOrder` are literal reference strings — no import/coupling to `samplePumps.js` or `sampleWorkOrders.js`, keeping the module isolated per the same judgment already applied between Pump, Work Order, and PM.

**Components:**
- `components/CMFilterBar.jsx` — search (by CM ID/failure description/equipment tag) + status filter, mirrors `PMFilterBar.jsx`/`WorkOrderFilterBar.jsx`/`PumpFilterBar.jsx` exactly.
- `components/CMReportTable.jsx` — Corrective Maintenance List. Columns exactly as specified: CM ID, Equipment, Failure Category (human-readable label), Severity (badge), Priority (badge), Downtime, Assigned Technician, Status (badge). Empty state via design-system `EmptyState`.
- `components/CMDetailPanel.jsx` — Corrective Maintenance Detail. Sections: Corrective Maintenance Summary (Equipment, Assigned Technician, Downtime, Failure Category, Severity badge, Priority badge, Status badge — Status added beyond the literal field list as CMMS-realism enrichment, following the same precedent set in the Work Order and PM Detail Panels), Root Cause & Actions (Root Cause, Immediate Action, Corrective Action), Related Records (Related Pump / Related Work Order, each a UI placeholder badge or a "No related …" fallback, no navigation wired — mirrors the PM Detail Panel's Related Work Orders placeholder pattern), and a Timeline section built on the design-system `Timeline` component.
- `components/CreateCMReportModal.jsx` — Create Corrective Maintenance Report (UI only), built on the design-system `Modal`. Form fields exactly as specified: Equipment (required), Failure Category, Severity, Priority, Failure Description (required), Immediate Action, Assigned Technician, Save button — no backend. Root Cause, Corrective Action, Downtime, Related Pump, Related Work Order, and Timeline are not collected by the Create form (matching the real-world workflow: a freshly reported failure has no known root cause or corrective action yet, no accrued downtime, and no work order raised, per Out-of-Scope "Automatic WO generation"); the page defaults these to `"Pending investigation."` / `"Not yet determined."` / `0` / the entered equipment tag / `null` respectively when constructing the new record.
- `utils/cmStatus.js` — `statusBadgeVariant`/`severityBadgeVariant`/`priorityBadgeVariant`/`failureCategoryLabel`, mirrors the `pumpHealth.js`/`workOrderStatus.js`/`pmStatus.js` pattern for centralizing badge-variant/label mapping.
- `pages/CM.jsx` — composes the above; owns search/status-filter/selection state plus the in-memory `cmReports` list (initialized from sample data). `handleCreate` assigns the next sequential `CM-XXXX` id, defaults new reports to `OPEN` with a seeded one-entry timeline, appends to local state, and selects the new entry — no persistence beyond the page's React state, per "UI only."
- `pages/CM.css` — two-column flex layout (list/detail) with a `@media (max-width: 768px)` single-column stack, identical structure to `Pump.css`/`WorkOrder.css`/`PM.css`, for Responsive UI.

`CM.jsx` is not wired into `App.jsx` routing, consistent with `Pump.jsx`/`Seal.jsx`/`WorkOrder.jsx`/`PM.jsx`, which are likewise not routed there — the Dashboard shell was not modified, per scope.

## Tests

New test files, one per new source file, following the same testing-library conventions used throughout `modules/ltsa`:
- `utils/cmStatus.test.js`
- `components/CMFilterBar.test.jsx`
- `components/CMReportTable.test.jsx`
- `components/CMDetailPanel.test.jsx`
- `components/CreateCMReportModal.test.jsx`
- `pages/CM.test.jsx` (page-level integration: header, list rendering, selection, search filter, status filter, empty state, create-report flow end to end)
- `pages/CM.responsive.test.js` (CSS media-query assertion)

Full suite after implementation: **61 test files, 237 tests, all passing** (237 = 196 baseline + 41 new).

## Files Touched

- `AI5R-STUDIO/dashboard/src/modules/ltsa/data/sampleCMReports.js` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/utils/cmStatus.{js,test.js}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/CMFilterBar.{jsx,test.jsx}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/CMReportTable.{jsx,test.jsx}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/CMDetailPanel.{jsx,test.jsx}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/CreateCMReportModal.{jsx,test.jsx}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/pages/CM.{jsx,css}` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/pages/CM.test.jsx` (new)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/pages/CM.responsive.test.js` (new)
- `ENGINEERING/history.log` (completion entry appended)

No file under Backend, API, Workflow engine, Notifications, Authentication, Dashboard KPI/shell (`App.jsx`), Analytics, or `design-system/` was modified; the Pump, Seal, Work Order, and PM modules were not touched — confirmed by `git status` scoped to those paths (empty aside from the pre-existing, unrelated `CORE-SERVICES/MODULE-MANAGER/DATA/modules.json` diff already flagged in the prior classification report).

## Definition of Done — Status

- Corrective Maintenance Workspace fully functional using sample data — **Met** (Corrective Maintenance List, Detail, Create Report UI, Failure Category, Severity, Root Cause, Immediate/Corrective Action, Downtime, Priority, Assigned Technician, Related Pump, Related Work Order, Timeline, Search, Filter all implemented per §Implementation).
- UI follows existing LTSA module architecture — **Met** (identical structural pattern to Pump/Work Order/PM, verified above).
- Responsive layout — **Met** (`CM.css` two-column layout collapsing under 768px, verified by `CM.responsive.test.js`).
- Tests passing — **Met** (237/237 green).
- Engineering History updated — **Met** (`ENGINEERING/history.log`).
- `CURRENT_MWO.md` updated — **Met**.

---

Stopping here as instructed. No commit, no push. No new MWO created. Awaiting Chief Architect review.
