# AI5R Studio UI Manufacturing Work Orders (MWO)

## Purpose

This document tracks AI5R Studio UI development milestones.

AI5R Studio UI is built as a reusable platform layer.

Principle:

- Design System = Framework
- Modules = Business Capability
- Workspace = Application Runtime

Do not mix Factory Pack business logic into Design System.

---

# Completed MWO

---

## UI-008 — Workspace Engine Foundation

Status:
✅ Completed

Commit:
8ce5873

Objective:

Create the first Workspace Framework.

Implemented:

- WorkspaceRegistry
- WorkspaceManager
- WorkspaceProvider
- WorkspaceContext
- WorkspaceTabs
- WorkspaceLayout

Architecture:

---

## UI-012 — Workspace Shell Upgrade

Status:
✅ Completed

Objective:

Transform the dashboard layout chrome into a consistent AI5R Studio shell and
remove dead/legacy layout code, without touching the Workspace Engine API.

Scope:

- `design-system/layout/**`
- `design-system/workspace/**`
- `src/layouts/MainLayout.jsx` (scope expanded mid-MWO; see below)

Implemented:

- Deleted `design-system/layout/Workspace.jsx`, `design-system/layout/WorkspaceTabs.jsx`,
  and `design-system/layout/MainLayout.backup.jsx` — dead legacy placeholders (hardcoded
  static tabs, no engine wiring), referenced only by the unused backup file, fully
  superseded by the real `design-system/workspace/components/*`.
- Restyled `Topbar.jsx`, `Breadcrumb.jsx`, `StatusBar.jsx` to the same studio palette
  already used by `Sidebar.jsx` and the workspace-tabs CSS (`#0F172A` / `#1E293B` /
  `#2563EB`). Dropped the hardcoded "LTSA Engineering" label from `Topbar` in favor of
  generic "AI5R Studio" / "Digital Factory Shell" branding.

Investigated and explicitly rejected:

- Wiring the real `WorkspaceTabs` (from `design-system/workspace`) into
  `src/layouts/MainLayout.jsx` as an app-wide tab strip. `modules/ltsa/pages/LTSA.jsx`
  already mounts its own nested `WorkspaceProvider` + `WorkspaceTabs` + `WorkspaceLayout`
  — a working, self-contained workspace runtime for that module. Adding a second,
  app-level `WorkspaceTabs` bound to the outer (inert) `WorkspaceProvider` from
  `app/providers.jsx` produced a duplicate tab bar (one empty, one populated) when
  navigating to `/ltsa`, confirmed via a component-render test. Reverted. Confirms the
  intended architecture: "Workspace = Application Runtime" means each business module
  owns its own workspace runtime; there is no shared, app-wide tab strip.

Not changed:

- `WorkspaceManager`, `WorkspaceRegistry`, `WorkspaceStorage` — Engine API/logic untouched.
- `CORE-SERVICES`, `PRODUCTS`, `AI5R-SDK` — untouched.

See `TECHNICAL_DEBT.md` for the follow-up item this investigation surfaced.

