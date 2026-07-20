# MWO-LTSA-060 — Demo Polish & Navigation

Status: **ACTIVE → Definition of Done met, awaiting review.**
Type: Manufacturing Work Order (Implementation)
Role: Implementation Engineer
Architecture: FROZEN — this MWO must not modify Backend, API, Authentication, Notifications, or redesign the Design System.
Predecessor: `MWO-LTSA-059-Corrective-Maintenance-Workspace.md` (CLOSED — reviewed and approved by Chief Architect, 2026-07-20).
Basis: Product Readiness Review for LTSA Demo v1 (conducted 2026-07-20, no file produced — findings delivered inline), which recommended one UX Polish sprint before further module work.

---

## Goal

Prepare LTSA Demo v1 so it feels like a single enterprise product instead of separate workspaces.

## Business Context

Pump Management, Work Order, Preventive Maintenance, and Corrective Maintenance are complete. This sprint focuses only on UX consistency, navigation, and demo quality. No new business functionality should be introduced.

## Scope

1. **Navigation Shell**
   - Provide navigation between: Pump, Work Order, Preventive Maintenance, Corrective Maintenance.
   - Reuse existing Design System navigation components where appropriate.
   - Do not redesign the Design System.

2. **Pump Quick Actions**
   - Wire: Create PM, Create CM.
   - Open the existing Create dialogs.
   - No backend.

3. **Humanized Status Labels**
   - Replace raw enum values with human-friendly labels.

4. **Naming Consistency**
   - Standardize: Assigned Technician.
   - Standardize Create button wording: Create Work Order, Create PM Schedule, Create CM Report.

5. **Success Feedback**
   - Lightweight success toast/banner after Create actions.

6. **Accessibility**
   - Keyboard activation for table rows.
   - Horizontal scrolling for wide tables.

## Out of Scope

- Maintenance History
- Dashboard KPI
- Reporting
- Backend
- APIs
- Authentication
- Notifications
- Timeline enhancements
- CM heading redesign

## Definition of Done

- Navigation connects all completed LTSA workspaces.
- Pump Quick Actions open the correct dialogs.
- Status labels are humanized.
- Naming is consistent.
- Success feedback implemented.
- Accessibility improvements completed.
- Tests updated and passing.
- `ENGINEERING/history.log` updated.
- `CURRENT_MWO.md` updated.

---

## Implementation

### 1. Navigation Shell

New `pages/LTSAWorkspace.jsx` composes the existing design-system `Tabs` component (read-only, unmodified) with the four existing workspace pages (`Pump`, `WorkOrder`, `PM`, `CM`), switching between them via local `useState` — no router, no new architecture. **Deliberately not wired into `App.jsx`**: `App.jsx`/the Dashboard shell is a separate, unrelated product surface (OS Command Center — AgentPanel, BrainActivity, etc., nothing LTSA-related) that no MWO to date (056–059) has ever touched, and this MWO's Out-of-Scope list does not grant that access. `LTSAWorkspace.jsx` resolves navigation **between the four LTSA workspaces** (satisfying Scope item 1 literally); connecting it into the wider AI5R OS Dashboard remains a distinct, larger integration decision for the Chief Architect, exactly as flagged in the MWO-LTSA-059 Product Readiness Review ("this necessarily touches the Dashboard shell... needs its own explicit MWO/scope grant").

### 2. Pump Quick Actions

`PumpDetailPanel.jsx` now accepts `onCreatePM`/`onCreateCM` callback props; the "Create PM"/"Create CM" buttons are no longer `disabled` and call them. `Pump.jsx` owns the two modal-open booleans and renders the **existing** `CreatePMScheduleModal`/`CreateCMReportModal` (imported directly — reusing them rather than building parallel Pump-local versions, per Reuse Before Create). "View History" and "Documents" remain disabled — out of scope.

**Known limitation, stated explicitly rather than glossed over:** the Definition of Done requires only that Quick Actions "open the correct dialogs." Submitting either modal from Pump Detail closes it without appending a record anywhere — the PM/CM workspaces' sample data lives in their own pages' independent local state (each unmounted while inactive in `LTSAWorkspace`), and lifting that state into a shared parent so a pump-initiated create could actually land in the PM/CM lists would be a structural change to already-completed modules, which is explicitly out of scope ("No architecture changes"). Equipment-tag prefill from the selected pump was considered and deliberately deferred for the same reason (added complexity beyond the literal DoD wording).

### 3. Humanized Status Labels

Added `statusLabel()` to `utils/workOrderStatus.js`, `utils/pmStatus.js`, and `utils/cmStatus.js` (mirroring the existing `frequencyLabel`/`failureCategoryLabel` pattern), mapping every multi-word closed-set status (`IN_PROGRESS`, `ON_HOLD`, `DUE_SOON`, etc.) to a human-readable label (`"In Progress"`, `"On Hold"`, `"Due Soon"`). Applied everywhere those statuses render: all three modules' RegistryTable/DetailPanel status badges, **and** their FilterBar status-filter dropdown option text (the `<option>` `value` stays the raw enum so filtering logic is untouched — only the visible label changed). Pump's own status vocabulary (`RUNNING`/`STANDBY`/`MAINTENANCE`/`FAULT`) was left as-is — already human-readable, not part of the verified finding, no change needed. Priority/Severity (`CRITICAL`/`HIGH`/`MEDIUM`/`LOW`, `MINOR`/`MODERATE`/`MAJOR`/`CRITICAL`) were also left as-is — single ALL-CAPS words, consistent with Pump's own convention, not the verified problem (which was specifically multi-word `SNAKE_CASE`).

### 4. Naming Consistency

- **Assigned Technician:** Work Order's `assignedTo` field/label/column/form-id was renamed to `assignedTechnician` throughout (`sampleWorkOrders.js`, `WorkOrderRegistryTable.jsx`, `WorkOrderDetailPanel.jsx`, `CreateWorkOrderModal.jsx`, and their tests), aligning it with PM and CM, which already used `assignedTechnician`.
- **Create button wording:** standardized so each module's header action, modal title, and modal submit button all agree:
  - Work Order: `"+ Create Work Order"` / `"Create Work Order"` / `"Create Work Order"` — already consistent, unchanged.
  - PM: `"+ Create PM Schedule"` / `"Create PM Schedule"` / submit button changed `"Save"` → `"Create PM Schedule"`.
  - CM: `"+ Create CM Report"` / modal title changed `"Create Corrective Maintenance Report"` → `"Create CM Report"` / submit button changed `"Save"` → `"Create CM Report"`.

### 5. Success Feedback

New `components/SuccessToast.jsx` — a local, module-scoped presentational component (not added to `design-system/`, styled with existing theme tokens only, same precedent as `PumpFilterBar`'s raw `<select>`). Auto-dismisses after 4s or on manual click; `role="status"`. Wired into `WorkOrder.jsx`, `PM.jsx`, and `CM.jsx`: each `handleCreate` now also sets a success message (e.g. `"Work Order WO-1009 created."`) shown above the FilterBar. **Not wired into the Pump Quick Actions flow** — since nothing is actually persisted from that entry point (see §2), showing a success message there would misrepresent what happened.

### 6. Accessibility

- **Keyboard activation:** every list table (`PumpRegistryTable`, `WorkOrderRegistryTable`, `PMScheduleTable`, `CMReportTable`) row now has `tabIndex={0}` and an `onKeyDown` handler that activates `onSelect` on Enter or Space, without changing the row's implicit ARIA `row` semantics (no `role="button"` override, to avoid conflicting with table semantics for assistive tech).
- **Horizontal scroll:** every list table is now wrapped in a `<div style={{overflowX: "auto"}}>`, so wide tables (CM's 8 columns) no longer risk clipping on narrow viewports.

## Tests

Existing tests updated in place wherever behavior/labels/wording changed (43 files); new tests added for every new behavior (keyboard activation × 4 tables, humanized-label assertions, renamed-field assertions, button-wording assertions, Pump Quick Action wiring, success-toast assertions). New test files: `components/SuccessToast.test.jsx`, `pages/LTSAWorkspace.test.jsx`.

Full suite after implementation: **63 test files, 260 tests, all passing** (260 = 237 baseline + 23 new).

## Files Touched

48 files under `AI5R-STUDIO/dashboard/src/modules/ltsa/` — 43 modified (Pump/WorkOrder/PM/CM components, pages, utils, and their tests, per §Implementation above) and 5 new (`components/SuccessToast.{jsx,test.jsx}`, `pages/LTSAWorkspace.{jsx,css,test.jsx}`). Full list in `ENGINEERING/history.log`.

No file under `design-system/`, `App.jsx`, Backend, API, or the Seal module was modified — confirmed by `git status` scoped to those paths (empty aside from the pre-existing, unrelated `CORE-SERVICES/MODULE-MANAGER/DATA/modules.json` diff already flagged in the prior classification report).

## Definition of Done — Status

- Navigation connects all completed LTSA workspaces — **Met** (`LTSAWorkspace.jsx`, tab-based; Dashboard-level integration explicitly out of scope, see §1).
- Pump Quick Actions open the correct dialogs — **Met** (does not persist created records into PM/CM lists — see §2 limitation).
- Status labels are humanized — **Met**.
- Naming is consistent — **Met**.
- Success feedback implemented — **Met** (WorkOrder/PM/CM create flows; deliberately not on the non-persisting Pump Quick Action flow).
- Accessibility improvements completed — **Met**.
- Tests updated and passing — **Met** (260/260 green).
- Engineering History updated — **Met** (`ENGINEERING/history.log`).
- `CURRENT_MWO.md` updated — **Met**.

---

Stopping here as instructed. No commit, no push. No new MWO created. Awaiting Chief Architect review.
