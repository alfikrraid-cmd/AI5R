# AI5R Studio — UI Track Roadmap

## Completed

- UI-007 Recover LTSA dashboard and stabilize studio shell
- UI-008 Activate AI5R workspace engine
- UI-009 Stabilize workspace integration
- UI-010 Add workspace lifecycle
- UI-011 Workspace persistence
- UI-012 Workspace shell upgrade

## Next milestones

Note: these were previously numbered UI-012–UI-014; renumbered to UI-013–UI-015 to
avoid colliding with the now-completed UI-012 (Workspace Shell Upgrade).

- UI-013 Workspace ordering/pinning — persist explicit tab order instead of
  registration/open order.
- UI-014 Multi-consumer workspace support — generalize the
  `hasSavedState()` / restore-before-default-open contract so any module
  (not just LTSA) adopting the workspace engine gets correct persistence
  by construction, rather than by convention.
- UI-015 Workspace storage versioning/migration — guard against stale
  `localStorage` shapes if the persisted schema changes again.
- UI-016 Clarify/remove the inert app-level `WorkspaceProvider` in
  `app/providers.jsx` (see `TECHNICAL_DEBT.md`, found in UI-012).
