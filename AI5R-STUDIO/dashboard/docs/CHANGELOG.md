# AI5R Studio — UI Track Changelog

## UI-013 — Panel Framework (2026-07-16)

- Added `design-system/panels/`: `Panel.jsx`, `PanelHeader.jsx`, `PanelContainer.jsx`,
  `index.js`. A reusable, business-logic-free card primitive with optional collapse,
  styled to the UI-012 studio palette (`#0F172A`/`#1E293B`).
- `Panel` owns its own (uncontrolled) collapse state; `PanelHeader` is a pure
  presentational title bar; `PanelContainer` is a stack/grid layout wrapper for
  arranging multiple panels.
- No consumer wiring yet — `modules/ltsa/components/Panel.jsx` (the existing
  module-local card) is untouched; migrating it to the design-system version is a
  future MWO.

## UI-012 — Workspace Shell Upgrade (2026-07-16)

- Deleted dead legacy layout code: `design-system/layout/Workspace.jsx`,
  `design-system/layout/WorkspaceTabs.jsx`, `design-system/layout/MainLayout.backup.jsx`.
  These were hardcoded placeholder prototypes (static "DASHBOARD/PUMP/SEAL/+" tabs, no
  engine wiring), referenced only by the unused backup file and fully superseded by the
  real engine components in `design-system/workspace/components/`.
- Unified the shell chrome palette: `Topbar.jsx`, `Breadcrumb.jsx`, `StatusBar.jsx` now
  use the same `#0F172A` / `#1E293B` colors as `Sidebar.jsx` and the workspace-tabs CSS
  (previously `Breadcrumb` used `#111827` and `StatusBar` used `#151C33`/`#2A3558`,
  visually inconsistent with the rest of the shell).
- Replaced `Topbar`'s hardcoded "LTSA Engineering" title with generic "AI5R Studio" /
  "Digital Factory Shell" branding, since the topbar is shared shell chrome, not
  LTSA-specific.
- Investigated wiring the real `WorkspaceTabs` into `src/layouts/MainLayout.jsx` as an
  app-wide tab strip; rejected after confirming (via a render test) it produces a
  duplicate tab bar on `/ltsa`, since `LTSA.jsx` already owns its own nested
  `WorkspaceProvider`/`WorkspaceTabs`/`WorkspaceLayout` instance. No change made to
  `MainLayout.jsx`. See `UI_MWO.md` UI-012 and `TECHNICAL_DEBT.md` for detail.

## UI-011 — Workspace Persistence (2026-07-16)

- Added `services/WorkspaceStorage.js`: `localStorage`-backed persistence of
  `{ openedWorkspaces, activeWorkspace }` under key `ai5r.workspace.state`.
- `WorkspaceManager`: `openWorkspace`, `closeWorkspace`, and `activateWorkspace` now
  persist state on every call (previously `activateWorkspace` did not persist at all).
- `WorkspaceManager.restore()` now restores the previously active workspace (not just
  the first opened one), falling back to the first opened workspace if the saved
  active id is no longer open.
- Added `WorkspaceManager.hasSavedState()` / `WorkspaceProvider`'s `hasSavedState()` so
  consumers can detect prior persisted state without mutating it.
- Fixed an ordering bug where `modules/ltsa/bootstrap.js` unconditionally reopened all
  `defaultOpen` workspaces on every mount, overwriting persisted state before
  `restoreWorkspace()` could read it — closing a tab never actually stayed closed
  across a reload. `bootstrapLTSA` now skips default-open when `hasSavedState()` is
  true; `LTSA.jsx` passes `hasSavedState` through and still calls `restoreWorkspace()`
  after bootstrap.
- Verified via a component-level test driving the real `LTSA` page (open → close tab →
  simulated reload → tab stays closed; active tab persists; closing all-but-one +
  switching persists).

## UI-010 — Workspace Lifecycle

- `WorkspaceProvider`/`WorkspaceTabs`: open/close/activate lifecycle, tab rendering.

## UI-009 — Stabilize Workspace Integration

- Minor integration fixes between `index.js` exports and `LTSAWorkspace.jsx`.

## UI-008 — Activate AI5R Workspace Engine

- Introduced the Studio app shell (`app/Studio/*`), wired `WorkspaceProvider` into
  `app/providers.jsx` and `app/router.jsx`.
