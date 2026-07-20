# MWO-LTSA-065 — Analytics

Status: **COMPLETED**
Type: Manufacturing Work Order (Implementation)
Role: Implementation Engineer
Architecture: FROZEN — this MWO must not introduce architecture changes, Backend, API, or a chart library.
Predecessor: `MWO-LTSA-064-Reporting.md` (CLOSED — reviewed and approved by Product Owner, 2026-07-20).

---

## Goal

Provide manager-focused maintenance analytics using existing LTSA sample data.

## Business Context

LTSA Demo v1 now includes an Executive Dashboard, Pump Management, Work Orders, Preventive Maintenance, Corrective Maintenance, Asset 360 (Maintenance History), and Reporting, all driven by local sample data. This MWO adds an Analytics workspace on top of that same data — deeper, still-static analytical views distinct from the Executive Dashboard's at-a-glance KPIs and the Reporting module's printable documents.

## Scope

- PM Compliance
- Open vs Closed Work Orders
- Maintenance Activity Trend
- Asset Criticality Distribution
- Maintenance KPIs

## Rules

- Derived data only.
- Reuse existing components.
- No backend.
- No API.
- No new architecture.
- No chart library.

## Out of Scope

- Backend
- API
- Database
- Chart libraries (Recharts, ApexCharts, D3, or equivalent)
- Authentication
- Live data / synchronization
- Reporting/PDF export (already delivered under `MWO-LTSA-064`)

## Definition of Done

- Analytics workspace implemented.
- Tests green.
- `CURRENT_MWO.md` updated.
- `ENGINEERING/history.log` updated.

---

## Product Owner Refinement (applied to implementation)

Received before implementation began: Analytics must answer four questions — Are we healthy? What needs attention? What is getting worse? What should managers do next? Priority order: (1) Maintenance KPIs, (2) PM Compliance, (3) Open vs Closed Work Orders, (4) Maintenance Activity Trend, (5) Asset Criticality Distribution. Rules reaffirmed as above, plus: manager-first.

## Implementation — Delivered Capabilities

- **`AnalyticsWorkspace.jsx`** — new workspace wired into `LTSAWorkspace.jsx` as an eighth tab ("Analytics"), structured around the four Product Owner questions in order.
- **"Are we healthy?"** — `KpiCardGrid`/`buildKpiSummary` and `MaintenanceHealthPanel`/`buildMaintenanceHealth`, both reused verbatim from `MWO-LTSA-063` — satisfies Maintenance KPIs, PM Compliance, and Open vs Closed Work Orders (priorities 1–3) with no new aggregation code.
- **"What needs attention?"** — new `CriticalityDistributionList` (priority 5: Asset Criticality Distribution, counting pumps by criticality level actually present in sample data), plus `AttentionAssetList` reused from `MWO-LTSA-063` — not one of the five named scope items, but reused because it already answers this exact question precisely.
- **"What is getting worse?"** — new Maintenance Activity Trend (priority 4), via `utils/analytics.js:buildActivityTrend()`: four weekly buckets of plant-wide PM/CM/WO counts (oldest → "This Week"), rendered as a table (`ActivityTrendTable.jsx`), with a simple UP/DOWN/FLAT badge comparing the two most recent weeks' corrective-maintenance counts. No chart.
- **"What should managers do next?"** — new `RecommendedActionsList`, driven by `buildRecommendedActions()`: conditional, data-driven bullets (e.g. "Schedule 3 overdue preventive maintenance tasks"), each carrying the real count it was derived from — never static text.
- **Supporting refactor:** `REFERENCE_DATE` and `daysBeforeReference()` were exported from `executiveDashboard.js` (previously private) so `analytics.js` anchors "today" identically instead of duplicating the constant — confirmed behavior-preserving against the existing `executiveDashboard` tests.

No PM/CM/WO/Pump component, page, or sample data file was modified; `App.jsx` was not touched; no chart library or other external dependency was introduced.

## Tests

**94 test files, 393 tests, all passing** (393 = 368 baseline + 25 new). New test files for every new component/page; `LTSAWorkspace.test.jsx` updated for the new Analytics tab; `executiveDashboard.test.js` re-verified unchanged after the export refactor.

## Definition of Done — Status

- Analytics workspace implemented — **Met**, structured around the four Product Owner questions in priority order.
- Tests green — **Met** (393/393).
- `CURRENT_MWO.md` updated — **Met**.
- `ENGINEERING/history.log` updated — **Met**.

## Closure

Reviewed and approved by Product Owner (2026-07-20). MWO-LTSA-065 is CLOSED. Committed to `feature/repository-hygiene` (see commit history for hash). No push performed as part of closure. No successor MWO defined yet.
