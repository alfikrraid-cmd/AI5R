# AI5R Studio — UI Track Changelog

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
