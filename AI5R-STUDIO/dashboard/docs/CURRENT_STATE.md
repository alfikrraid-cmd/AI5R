# AI5R Studio — Workspace Engine: Current State

_Last updated: UI-012 (2026-07-16)_

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
