# AI5R Studio — Workspace Engine: Current State

_Last updated: UI-011 (2026-07-16)_

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
