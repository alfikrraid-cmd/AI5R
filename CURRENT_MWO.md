# Current MWO

Status: ACTIVE — always reflects the MWO currently being executed.

---

- **Current MWO:** `MWO-LTSA-061` — Dashboard Integration (`ENGINEERING/MWO/MWO-LTSA-061-Dashboard-Integration.md`)
- **Goal:** Integrate the completed LTSA workspaces into the AI5R Studio Dashboard so LTSA can be demonstrated as one connected product.
- **Scope:** Integrate `LTSAWorkspace` into the Dashboard shell, add a navigation entry for LTSA, make LTSA the accessible entry point for Pump/Work Order/PM/CM, preserve existing Dashboard behavior, update routing/navigation only where required, responsive layout, tests.
- **Out of Scope:** Backend, API, Maintenance History, KPI Dashboard, Reporting, Authentication, Permission system, Business logic changes.
- **Status at last update:** Definition of Done met. LTSA integrated into the AI5R Studio Dashboard via a top-level "LTSA" tab in `App.jsx` (reusing the existing design-system `Tabs` component), switching between the OS Command Center (default, unchanged) and `LTSAWorkspace`. Tests passing (264/264). Engineering History updated. Awaiting Chief Architect review.

- **Previous MWO:** `MWO-LTSA-060` — Demo Polish & Navigation (`ENGINEERING/MWO/MWO-LTSA-060-Demo-Polish-Navigation.md`) — Definition of Done met (Navigation Shell, Pump Quick Actions, Humanized Status Labels, Naming Consistency, Success Feedback, Accessibility), 260/260 tests passing — **not yet formally closed** (no explicit Chief Architect closure instruction received; carried forward as-is, not marked CLOSED).
- **Prior MWO:** `MWO-LTSA-059` — Corrective Maintenance Workspace (`ENGINEERING/MWO/MWO-LTSA-059-Corrective-Maintenance-Workspace.md`) — Definition of Done met, 237/237 tests passing — **not yet formally closed**.
- **Prior MWO:** `MWO-LTSA-058` — Preventive Maintenance Workspace (`ENGINEERING/MWO/MWO-LTSA-058-Preventive-Maintenance-Workspace.md`) — **CLOSED**, reviewed and approved by Chief Architect (2026-07-20), 196/196 tests passing.
