# AI5R Studio — UI Track Roadmap

## Completed

- UI-007 Recover LTSA dashboard and stabilize studio shell
- UI-008 Activate AI5R workspace engine
- UI-009 Stabilize workspace integration
- UI-010 Add workspace lifecycle
- UI-011 Workspace persistence

## Next milestones

- UI-012 Workspace ordering/pinning — persist explicit tab order instead of
  registration/open order.
- UI-013 Multi-consumer workspace support — generalize the
  `hasSavedState()` / restore-before-default-open contract so any module
  (not just LTSA) adopting the workspace engine gets correct persistence
  by construction, rather than by convention.
- UI-014 Workspace storage versioning/migration — guard against stale
  `localStorage` shapes if the persisted schema changes again.
