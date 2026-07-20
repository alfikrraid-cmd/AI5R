# MWO-LTSA-064 — Reporting

Status: **COMPLETED**
Type: Manufacturing Work Order (Implementation)
Role: Implementation Engineer
Architecture: FROZEN — this MWO must not introduce architecture changes, Backend, API, or a chart library.
Predecessor: `MWO-LTSA-063-Executive-Dashboard.md` (CLOSED — reviewed and approved by Product Owner, 2026-07-20).

---

## Goal

Export executive and operational reports from existing LTSA sample data.

## Business Context

LTSA Demo v1 now includes an Executive Dashboard, Pump Management, Work Orders, Preventive Maintenance, Corrective Maintenance, and Asset 360 (Maintenance History), all driven by local sample data. This MWO adds a reporting layer on top of that same data — printable/exportable views of what the workspaces already show, not a new data source or system.

## Scope

- Executive Summary Report
- Pump History Report
- Work Order Report
- PM Report
- CM Report
- Print-friendly layout
- PDF-ready UI (no backend)
- Reuse existing components

## Rules

- No architecture changes.
- No backend.
- No API.
- No chart library.
- Derived data only.

## Out of Scope

- Backend
- API
- Database
- Chart libraries (Recharts, ApexCharts, D3, or equivalent)
- Authentication
- Live data / synchronization
- Server-side or headless PDF generation

## Definition of Done

- Reports implemented.
- Tests green.
- `CURRENT_MWO.md` updated.
- `ENGINEERING/history.log` updated.

---

## Product Owner Refinement (applied to implementation)

Received before implementation began: reporting is for managers, not engineers. Priority order: (1) Executive Summary Report, (2) Pump History Report, (3) Work Order Report, (4) Preventive Maintenance Report, (5) Corrective Maintenance Report. Rules reaffirmed as above, plus: reports must stay readable on A4.

## Implementation — Delivered Capabilities

- **`ReportsWorkspace.jsx`** — new workspace hosting all five reports, mirroring `LTSAWorkspace`'s own internal `Tabs` navigation pattern. Wired into `LTSAWorkspace.jsx` as a seventh tab ("Reports").
- **Executive Summary Report** — reuses `KpiCardGrid` / `MaintenanceHealthPanel` / `AttentionAssetList` / `UpcomingMaintenanceList` and their existing `utils/executiveDashboard.js` data functions verbatim (built under `MWO-LTSA-063`) — no new aggregation logic.
- **Pump History Report** — reuses `AssetSummaryCard` + `buildAssetSummary`/`buildAssetTimeline`/`listAssets` (built under `MWO-LTSA-062`), applied across every pump.
- **Work Order / Preventive Maintenance / Corrective Maintenance Reports** — each directly reuses the existing `WorkOrderRegistryTable` / `PMScheduleTable` / `CMReportTable` components read-only (`selectedId={null}`, no-op `onSelect`) — no new table markup written for any of the three.
- **`PrintButton.jsx`** — triggers the browser's native print dialog (`window.print()`), which is also how a user saves the report as a PDF ("Print" → "Save as PDF"). No PDF library introduced.
- **`ReportGeneratedOn.jsx`** — small "Generated: \<date\>" stamp, reused by every report.
- **`Reports.css`** — print styling: an opt-out `.no-print` class plus `@page { size: A4; margin: 15mm; }`. Deliberately **not** the common "hide everything in `body`, reveal one subtree" trick — that trick was considered and rejected because component CSS bundles globally in this app regardless of which tab is active, so it would silently blank out printing on every other page in the app once loaded. `LTSAWorkspace`'s own outer `Tabs` bar is marked `.no-print` so it doesn't appear in a printed report.
- Five `ReportsWorkspace` tab labels use full report names ("Work Order Report", not "Work Order") to avoid duplicate tab labels with `LTSAWorkspace`'s own outer tabs, which are both mounted simultaneously whenever "Reports" is the active outer tab.

**Known, documented limitation:** `App.jsx` (the AI5R Studio Dashboard shell) was not modified — out of this MWO's scope. Its outermost "OS Command Center / LTSA" section-switcher tabs are not marked `.no-print`, so they will still appear at the top of a printed report. Fixing this would require Dashboard-shell scope this MWO does not have.

No PM/CM/WO/Pump component, page, or sample data file was modified; no chart library or other external dependency was introduced.

## Tests

**89 test files, 368 tests, all passing** (368 = 346 baseline + 22 new). New test files for every new component/page; `LTSAWorkspace.test.jsx` updated for the new Reports tab.

## Definition of Done — Status

- Reports implemented — **Met** (all five, in Product Owner priority order).
- Tests green — **Met** (368/368).
- `CURRENT_MWO.md` updated — **Met**.
- `ENGINEERING/history.log` updated — **Met**.

## Closure

Reviewed and approved by Product Owner (2026-07-20). MWO-LTSA-064 is CLOSED. Committed to `feature/repository-hygiene` (see commit history for hash). No push performed as part of closure. No successor MWO defined yet.
