# MWO-LTSA-061 — Dashboard Integration

Status: **ACTIVE → Definition of Done met, awaiting review.**
Type: Manufacturing Work Order (Implementation)
Role: Implementation Engineer
Architecture: FROZEN — this MWO must not modify Backend, API, Authentication, the Permission system, or introduce business logic changes.
Predecessor: `MWO-LTSA-060-Demo-Polish-Navigation.md` (Definition of Done met 2026-07-20, awaiting Chief Architect review — not yet formally closed).

---

## Goal

Integrate the completed LTSA workspaces into the AI5R Studio Dashboard so LTSA can be demonstrated as one connected product.

## Business Context

Pump Management, Work Order, Preventive Maintenance, Corrective Maintenance, and Demo Polish are complete. This MWO introduces the first production entry point.

## Scope

- Integrate `LTSAWorkspace` into the Dashboard shell.
- Add a navigation entry for LTSA.
- Make LTSA the accessible entry point for: Pump, Work Order, Preventive Maintenance, Corrective Maintenance.
- Preserve existing Dashboard behavior.
- Update routing/navigation only where required.
- Responsive layout.
- Tests.

## Out of Scope

- Backend
- API
- Maintenance History
- KPI Dashboard
- Reporting
- Authentication
- Permission system
- Business logic changes

## Definition of Done

- LTSA is reachable from the Dashboard.
- Navigation works correctly.
- Existing Dashboard functionality remains intact.
- Tests passing.
- `ENGINEERING/history.log` updated.
- `CURRENT_MWO.md` updated.

---

## Implementation

**Approach chosen — minimal, reuse-only:** `App.jsx` gained one top-level `Tabs` (the same existing, unmodified design-system component already reused by `LTSAWorkspace.jsx` itself, so no new pattern is introduced) switching between two sections: `"OS Command Center"` (default) and `"LTSA"`. No router, no new page-composition mechanism, no restructuring of the existing flat single-file `App.jsx` — the entire pre-existing panel tree (`AgentPanel`, `BrainActivity`, `LiveRuntimeStatus`, the UMKM_OS product panels, etc.) is wrapped, unmodified, inside the default branch of a single conditional (`activeSection === "ltsa" ? <LTSAWorkspace /> : <>...existing content...</>`). When "LTSA" is selected, `LTSAWorkspace` (built under MWO-LTSA-060, itself already providing Pump/Work Order/PM/CM sub-navigation) renders in its place.

**Why this satisfies "Preserve existing Dashboard behavior" exactly:** the default `activeSection` is `"os"`, so a user who never touches the new tab sees the identical panel tree, in the identical order, with identical `useEffect`-driven data fetching (`getSystemStatus`/`getDashboardData` still run unconditionally on mount, unchanged) — nothing about the existing panels' logic, props, or rendering was touched, only wrapped in a conditional branch.

**Alternative considered and rejected:** appending `<LTSAWorkspace />` inline at the bottom of the existing flat panel list (mirroring how `UMKM_OS`'s components are integrated) was considered as an even smaller diff, but rejected because it would not satisfy the MWO's explicit, separate "Add navigation entry for LTSA" and "Make LTSA the accessible entry point" scope items — inline appending provides no navigation, just more scroll content buried among dozens of unrelated panels.

One small supporting CSS rule (`.dashboard-nav { margin: 20px 0; }`) was added to the existing `index.css` (the file `App.jsx` already relies on for its `.dashboard`/`.grid` classes) to space the new tab bar — no new stylesheet, no design-system change.

## Tests

New `App.test.jsx` (previously did not exist): asserts the OS Command Center renders by default (existing `<h1>`, an existing `MetricCard`, "OS Command Center" tab marked selected), that an "LTSA" tab exists, that clicking it renders the LTSA workspace (`Pump Workspace` heading, the default LTSA Workspace tab) while the OS-only content is no longer present, and that clicking back restores the OS Command Center. No mocking required — `getSystemStatus`/`getDashboardData` already fail closed to safe offline defaults in a `fetch`-less test environment (pre-existing behavior, unchanged), and `LiveStreamProvider` already fails closed to `"UNAVAILABLE"` without a mocked `EventSource` (same pattern already exercised by `LiveRuntimeStatus.test.jsx` and siblings).

Full suite after implementation: **64 test files, 264 tests, all passing** (264 = 260 baseline + 4 new).

## Files Touched

- `AI5R-STUDIO/dashboard/src/App.jsx` (modified — Tabs added, existing content wrapped in a conditional branch, otherwise unchanged)
- `AI5R-STUDIO/dashboard/src/index.css` (modified — one new `.dashboard-nav` rule added)
- `AI5R-STUDIO/dashboard/src/App.test.jsx` (new)

No other file was touched by this MWO. (The `modules/ltsa/*` files showing as modified in the working tree belong to the still-uncommitted MWO-LTSA-060 work, not this MWO.) `design-system/`, Backend, API, Authentication, and the Permission system were not modified — confirmed by `git status` scoped to those paths (empty aside from the pre-existing, unrelated `CORE-SERVICES/MODULE-MANAGER/DATA/modules.json` diff already flagged in the prior classification report).

## Definition of Done — Status

- LTSA is reachable from the Dashboard — **Met** (via the new "LTSA" tab in `App.jsx`).
- Navigation works correctly — **Met** (Tabs switch both directions; LTSA's own internal Pump/Work Order/PM/CM navigation, built under MWO-LTSA-060, is unaffected).
- Existing Dashboard functionality remains intact — **Met** (default view unchanged; verified by `App.test.jsx`).
- Tests passing — **Met** (264/264 green).
- Engineering History updated — **Met** (`ENGINEERING/history.log`).
- `CURRENT_MWO.md` updated — **Met**.

---

Stopping here as instructed. No commit, no push. No new MWO created. Awaiting Chief Architect review.
