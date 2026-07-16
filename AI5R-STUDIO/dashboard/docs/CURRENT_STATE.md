# AI5R Studio — Workspace Engine: Current State

_Last updated: UI-017 (2026-07-16)_

## Command Toolbar Framework (as of UI-017)

- `design-system/toolbar/` — `Toolbar.jsx`, `ToolbarGroup.jsx`,
  `ToolbarSeparator.jsx`, `ToolbarButton.jsx`, `index.js`. Pure design-system, v1:
  no Workspace/Docking/Panels/Inspector/DataGrid dependency, no Factory Pack /
  module dependency, no business logic.
- Fully stateless — no `useState`/context anywhere in this module. The consumer
  owns `active`/`disabled` state and what `onClick` does.
- `ToolbarButton` is icon-library-agnostic: `icon` is any ReactNode the caller
  supplies.
- Not yet wired into any consumer.

## DataGrid Framework (as of UI-016)

- `design-system/datagrid/` — `DataGrid.jsx`, `DataGridHeader.jsx`,
  `DataGridRow.jsx`, `DataGridCell.jsx`, `DataGridPagination.jsx`, `index.js`. Pure
  design-system, v1: no Workspace/Docking/Panels/Inspector dependency, no Factory
  Pack / module dependency, no business logic — columns/rows are opaque.
- `DataGrid` owns sort/selection/pagination state internally (uncontrolled): sort
  cycles asc→desc→none, selection is a `Set` with select-all scoped to the current
  page, pagination is optional via `pageSize` (0-indexed page state).
- No controlled-state/provider/context mode exists yet (same v1 scoping choice as
  Docking's `DockLayout`).
- Not yet wired into any consumer.

## Inspector Framework (as of UI-015)

- `design-system/inspector/` — `Inspector.jsx`, `InspectorHeader.jsx`,
  `InspectorSection.jsx`, `InspectorField.jsx`, `index.js`. Pure design-system, v1:
  read-only display, no Workspace/Docking/Panels dependency, no Factory Pack /
  module dependency, no business logic.
- `Inspector` supports `title`, an `actions` slot (ReactNode, rendered in the
  header), and `children` (sections). `InspectorSection` supports `collapsible`/
  `defaultCollapsed`, each section collapsing independently. `InspectorField`
  supports `label`/`value`, with `children` overriding `value` for custom content.
- Not yet wired into any consumer.

## Docking System (as of UI-014)

- `design-system/docking/` — `DockRegistry.js`, `DockManager.js`, `DockPanel.jsx`,
  `DockLayout.jsx`, `index.js`. Pure design-system, v1: no Workspace Engine
  dependency, no Factory Pack / module dependency, no persistence, no drag-drop.
- Four fixed areas: `left`, `center`, `right`, `bottom` (exported as `DOCK_AREAS`). A
  panel's area is fixed at registration; `DockManager` tracks open/active state per
  area independently (like an isolated tab strip per area).
- `DockLayout` owns its `DockRegistry`/`DockManager` privately via `useRef` — they are
  **not** exposed through a context/provider (no `DockProvider`/`useDock` exists yet,
  unlike the Workspace Engine's `WorkspaceProvider`/`useWorkspace`).
- Not yet wired into any consumer or page.

## Panel Framework (as of UI-013)

- `design-system/panels/` — `Panel.jsx`, `PanelHeader.jsx`, `PanelContainer.jsx`,
  `index.js`. Pure design-system primitives: no Workspace Engine dependency, no
  Factory Pack / module dependency, no persistence.
- `Panel` supports `title`, `children`, and optional `collapsible`/`defaultCollapsed`.
  Styled with the UI-012 studio palette.
- Not yet wired into any consumer. `modules/ltsa/components/Panel.jsx` (an older,
  module-local, non-collapsible card with a different palette) still exists separately
  and is unaffected — migrating LTSA to the design-system `Panel` is a future MWO.

## Shell chrome (as of UI-012)

- `design-system/layout/{Topbar,Sidebar,Breadcrumb,StatusBar}.jsx` are the live shell
  chrome, rendered by `src/layouts/MainLayout.jsx` (the app's actual routed layout).
  All four now share one palette (`#0F172A` background, `#1E293B` borders, `#2563EB`
  accent) matching the workspace-tabs CSS in `index.css`.
- `design-system/layout/Workspace.jsx`, `design-system/layout/WorkspaceTabs.jsx`, and
  `design-system/layout/MainLayout.backup.jsx` no longer exist — they were dead
  placeholder prototypes, not the real engine.
- `src/layouts/MainLayout.jsx` does **not** render `WorkspaceTabs`/`WorkspaceLayout` and
  should not — see "Per-module workspace runtimes" below.

## Per-module workspace runtimes (as of UI-012)

- The `WorkspaceProvider` mounted in `app/providers.jsx` wraps the whole app but has
  nothing registered to it — it is effectively inert at the app level.
- `modules/ltsa/pages/LTSA.jsx` mounts its **own** nested `WorkspaceProvider` +
  `WorkspaceTabs` + `WorkspaceLayout`, registers its own workspace descriptors
  (`modules/ltsa/workspace.js`), and is the only real, working consumer of the engine
  today. This is intentional: "Workspace = Application Runtime" means each Factory Pack
  / module owns its own workspace runtime instance, not a shared app-wide one.

## Location

`AI5R-STUDIO/dashboard/src/design-system/workspace`

## Components

- `core/WorkspaceRegistry.js` — in-memory `id → descriptor` map. No persistence, no React.
- `core/WorkspaceManager.js` — lifecycle (`open`/`close`/`activate`) plus persistence
  (`restore`, `hasSavedState`). Framework-agnostic, no React.
- `core/WorkspaceProvider.jsx` — React context wiring. Builds one `WorkspaceRegistry` +
  `WorkspaceManager` + `WorkspaceStorage` per mount (via refs) and exposes the manager's
  API through `WorkspaceContext`.
- `core/WorkspaceContext.jsx` / `hooks/useWorkspace.js` — context plumbing.
- `services/WorkspaceStorage.js` — `localStorage` persistence under key
  `ai5r.workspace.state`. Stores `{ openedWorkspaces, activeWorkspace }`.
- `components/WorkspaceTabs.jsx`, `components/WorkspaceLayout.jsx` — UI.
- `contracts/WorkspaceDescriptor.js` — descriptor shape (`id`, `title`, `component`,
  `icon?`, `order?`, `closable?`, `defaultOpen?`, `metadata?`).

## Persistence behavior (as of UI-011)

- Opening, closing, or activating a workspace persists `openedWorkspaces` and
  `activeWorkspace` to `localStorage` immediately.
- `WorkspaceManager.restore()` reads persisted state back and merges it into the live
  manager, restoring the previously active tab if it is still open.
- `WorkspaceManager.hasSavedState()` lets a consumer check, without mutating anything,
  whether there is prior persisted state before deciding to run its own default-open
  logic.

## Consumer contract

A consumer (e.g. `modules/ltsa/pages/LTSA.jsx` + `modules/ltsa/bootstrap.js`) must:

1. Register all workspace descriptors.
2. Only auto-open `defaultOpen` descriptors when `hasSavedState()` is `false` (first
   run / cleared storage). If saved state exists, skip default-open — it would
   otherwise re-open everything and immediately overwrite the persisted "closed"
   state before `restore()` gets a chance to read it.
3. Call `restoreWorkspace()` to apply whatever was persisted.

This contract is implemented today by `bootstrapLTSA` (checks `hasSavedState()`) and
`LTSA.jsx` (calls `bootstrapLTSA` then `restoreWorkspace()` in a mount effect).

## Known limitations

See `TECHNICAL_DEBT.md`.
