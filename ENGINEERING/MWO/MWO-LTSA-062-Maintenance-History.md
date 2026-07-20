# MWO-LTSA-062 — Maintenance History

Status: **COMPLETED**
Type: Manufacturing Work Order (Implementation)
Role: Implementation Engineer
Architecture: FROZEN — this MWO must not modify Backend, API, Database, Reporting, KPI Dashboard, Live synchronization, or Authentication.
Predecessor: `MWO-LTSA-061-Dashboard-Integration.md` (Definition of Done met 2026-07-20, awaiting Chief Architect review — not yet formally closed).

---

## Goal

Provide a complete asset-centric maintenance history so engineers can understand everything that has happened to a pump from a single screen.

## Business Context

LTSA Demo v1 now includes: Dashboard Integration, Pump Management, Work Order, Preventive Maintenance, and Corrective Maintenance. Users should now be able to inspect one pump and immediately understand its operational maintenance history.

## Scope

Create a new Maintenance History workspace. The workspace should present one consolidated timeline for a selected Pump.

Include:

1. **Asset Summary** — Pump, Tag, Area, Status, Criticality.
2. **Preventive Maintenance History**
3. **Corrective Maintenance History**
4. **Work Order History**
5. **Unified chronological timeline**
6. **Filter** — Date range, Event type, Status.
7. **Detail panel** — selecting any event should show its details.

### Implementation Requirements

- Reuse existing Design System.
- Reuse existing LTSA patterns.
- Use local sample data only.
- Do not duplicate PM/CM/WO components.
- Do not redesign previous modules.

## Out of Scope

- Backend
- API
- Database
- Reporting
- KPI Dashboard
- Live synchronization
- Editing history
- Authentication

## Definition of Done

- Maintenance History workspace implemented.
- Timeline correctly merges PM, CM and WO sample events.
- Filters work.
- Detail panel works.
- Responsive layout.
- Tests added.
- `ENGINEERING/history.log` updated.
- `CURRENT_MWO.md` updated.

---

## Product Owner Refinement (incorporated)

Before implementation began, the Product Owner provided implementation guidance reframing this workspace as an **Asset 360 View** rather than another registry page — the selected pump is the center of the screen, and everything else explains its life. That guidance is reflected throughout §Implementation below: a single unified timeline and a single unified detail renderer (not three parallel detail panels), an extended Asset Summary (adding Last PM/Last CM/Open Work Orders/Last Activity on top of the base MWO's Pump/Tag/Area/Status/Criticality), and an added Assigned Technician filter alongside Date Range/Event Type/Status. No MWO field was changed — this section documents guidance that shaped implementation, per the Product Owner's explicit instruction not to change the MWO itself.

## Implementation

**New, self-contained workspace — no existing module modified except one line of registration.** Only `LTSAWorkspace.jsx`/`.test.jsx` (the navigation shell) were touched, to add a fifth "Maintenance History" tab, mirroring exactly how Pump/Work Order/PM/CM were each registered. No PM/CM/WO/Pump component, page, or sample data file was modified.

### 1–2. Asset Summary + Unified Timeline

`utils/maintenanceHistory.js` is the single aggregation layer — pure functions only, no new data model, no persistence:
- `listAssets()`/`findAssetByTag()` — read `samplePumps.js` directly (read-only).
- `buildAssetTimeline(equipmentTag)` — filters `samplePMSchedules`, `sampleCMReports`, and `sampleWorkOrders` by `equipmentTag` (the join key already shared identically across all three, confirmed by inspection of the sample data), maps each into one common event shape (`id`, `type`, `date`, `title`, `status`, `assignedTechnician`, `raw`), and sorts descending by date. Anchor date per type: PM uses `lastPerformed` (falling back to its own timeline/`nextDue`), CM uses its `timeline[0].date` (first-reported date), WO uses `createdDate`.
- `buildAssetSummary(pump, timeline)` — derives Last Preventive Maintenance / Last Corrective Maintenance (most recent event of each type), Open Work Orders (count of WO events not `COMPLETED`), and Last Activity (`timeline[0].date`) from the already-built timeline; Pump/Tag/Area/Status/Criticality come straight from the pump record.
- `components/MaintenanceTimelineTable.jsx` — one unified list (Date, Type badge, Event, Status badge, Assigned Technician), reusing the exact List pattern (and MWO-060's keyboard-activation + horizontal-scroll accessibility standard) already established by `PumpRegistryTable`/`WorkOrderRegistryTable`/etc., applied here to merged events instead of one record type. Type badges (`PM`=info, `CM`=warning, `Work Order`=purple) give each row an immediate visual identity per the Product Owner's "clearly identify PM/CM/WO" guidance.

### 3. Unified Detail Panel

`components/MaintenanceEventDetailPanel.jsx` is the single event detail renderer requested — **not** three separate panels and **not** a reuse of `PumpDetailPanel`/`WorkOrderDetailPanel`/etc. (which are full standalone workspace panels, not built for this merged-event shape). It renders one common "Event Summary" Card (type, status, date, technician) always, then an internal `PMDetails`/`CMDetails`/`WODetails` sub-section chosen by `event.type`, reusing the existing per-module labeling utilities (`frequencyLabel`, `triggerTypeLabel`, `failureCategoryLabel`, `severityBadgeVariant`, `priorityBadgeVariant`, etc.) so formatting stays identical to each source workspace without duplicating their components.

### 4. Filters

`components/MaintenanceHistoryFilterBar.jsx` — Date From / Date To (native date inputs), Event Type (ALL/PM/CM/Work Order), Status (dynamically computed from the current asset's timeline, humanized via a new `filterStatusLabel()` that tries each module's existing `statusLabel()` in turn — safe because PM/CM/WO already agree on the label for every status value they share), and Assigned Technician (dynamically computed from the current asset's timeline). Filtering itself is a plain array `.filter()` in `MaintenanceHistory.jsx` — no new state-management pattern.

### 5. Architecture

No global state, no shared service layer, no context, no backend/API/database. `MaintenanceHistory.jsx` owns its own local `useState` (selected asset, selected event, filters) exactly like every other LTSA page, and imports the four existing sample data modules directly through `maintenanceHistory.js` — the only difference from prior workspaces is that this one's entire purpose is cross-module aggregation, so importing all four sample data files (rather than avoiding cross-module imports, as Pump/WO/PM/CM deliberately did for isolation) is inherent to the requirement, not a new pattern.

### 6. UX

Nothing renders until a pump is picked (`AssetSelector.jsx`, a plain `<select>` matching the existing FilterBar dropdown styling) — the workspace opens on an explicit "select a pump" empty state, then leads with the Asset Summary before anything else, so the selected asset is unambiguously the center of the screen per the Product Owner's framing.

## Tests

New test files for every new module: `utils/maintenanceHistory.test.js`, `components/AssetSelector.test.jsx`, `components/AssetSummaryCard.test.jsx`, `components/MaintenanceTimelineTable.test.jsx`, `components/MaintenanceHistoryFilterBar.test.jsx`, `components/MaintenanceEventDetailPanel.test.jsx`, `pages/MaintenanceHistory.test.jsx`, `pages/MaintenanceHistory.responsive.test.js`. `LTSAWorkspace.test.jsx` extended with a test for the new tab. Page-level tests exercise the full flow against pump `641-P-5` (which has exactly one PM, one CM, and one WO in sample data): asset selection, merged timeline rendering, event selection showing the correct detail sub-section, all four filters, and filter/selection reset on asset change.

Full suite after implementation: **72 test files, 311 tests, all passing** (311 = 264 baseline + 47 new).

## Files Touched

16 new files under `AI5R-STUDIO/dashboard/src/modules/ltsa/` (`utils/maintenanceHistory.{js,test.js}`; `components/{AssetSelector,AssetSummaryCard,MaintenanceTimelineTable,MaintenanceHistoryFilterBar,MaintenanceEventDetailPanel}.{jsx,test.jsx}`; `pages/MaintenanceHistory.{jsx,css,test.jsx,responsive.test.js}`), plus `pages/LTSAWorkspace.{jsx,test.jsx}` modified to register the new tab.

No PM/CM/WO/Pump component, page, or sample data file was modified; no file under `design-system/`, `App.jsx`, Backend, API, Database, or Authentication was touched — confirmed by `git status` scoped to those paths (empty aside from the pre-existing, unrelated `CORE-SERVICES/MODULE-MANAGER/DATA/modules.json` diff already flagged in the prior classification report).

## Definition of Done — Status

- Maintenance History workspace implemented — **Met**.
- Timeline correctly merges PM, CM and WO sample events — **Met**, verified against pump `641-P-5`'s exactly-one-of-each sample records.
- Filters work — **Met** (Date Range, Event Type, Status, Assigned Technician).
- Detail panel works — **Met** (one unified renderer, type-dispatched).
- Responsive layout — **Met** (`MaintenanceHistory.css`, verified by `MaintenanceHistory.responsive.test.js`).
- Tests added — **Met** (311/311 green).
- Engineering History updated — **Met** (`ENGINEERING/history.log`).
- `CURRENT_MWO.md` updated — **Met**.

---

## Closure

Reviewed and approved by Product Owner (2026-07-20). MWO-LTSA-062 is CLOSED. Committed to `feature/repository-hygiene` (see commit history for hash). No push performed as part of closure. No successor MWO defined yet.
