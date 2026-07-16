# AI5R Studio — UI Track Technical Debt

## Workspace engine

- **Convention-based consumer contract.** `hasSavedState()` must be checked by every
  consumer's bootstrap logic before auto-opening `defaultOpen` workspaces. Nothing in
  the engine enforces this — a new module that copies the old (pre-UI-011) pattern
  will silently reintroduce the persistence bug. Consider a higher-level
  `bootstrapWorkspaces(descriptors, workspace)` helper in the engine itself so the
  correct order isn't left to each consumer to rediscover (tracked as UI-015).
- **No storage schema versioning.** `WorkspaceStorage` reads/writes a fixed shape
  (`{ openedWorkspaces, activeWorkspace }`) with no version tag. If the shape changes
  again, old `localStorage` entries could be misread rather than cleanly migrated or
  discarded (tracked as UI-016).
- **No persisted tab order.** `openedWorkspaces` order reflects open/registration
  order, not any user-driven reordering (no reordering UI exists yet either).
- **Single global storage key.** `ai5r.workspace.state` is shared process-wide; if two
  independent `WorkspaceProvider` instances are ever mounted at once (not the case
  today), they would clobber each other's persisted state.
- **Inert app-level `WorkspaceProvider` (found in UI-012).** `app/providers.jsx` mounts
  a `WorkspaceProvider` wrapping the whole app, but nothing ever registers a workspace
  to it — the only real consumer, `modules/ltsa/pages/LTSA.jsx`, mounts its own nested
  `WorkspaceProvider` instead (shadowing the outer one for its subtree). The outer
  provider currently does nothing. Either remove it if no future module is meant to
  share it, or document/enforce that it's the intended per-module pattern so the next
  engineer doesn't try to wire `WorkspaceTabs` into the app-level `MainLayout.jsx` again
  (this was attempted and reverted in UI-012 — it produces a duplicate, empty tab bar
  alongside LTSA's real one). Touching `app/providers.jsx` was out of scope for UI-012.
