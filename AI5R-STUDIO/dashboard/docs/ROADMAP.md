# AI5R Studio — UI Track Roadmap

## Completed

- UI-007 Recover LTSA dashboard and stabilize studio shell
- UI-008 Activate AI5R workspace engine
- UI-009 Stabilize workspace integration
- UI-010 Add workspace lifecycle
- UI-011 Workspace persistence
- UI-012 Workspace shell upgrade
- UI-013 Panel framework

## Next milestones

Note: these were previously numbered UI-012–UI-014, then UI-013–UI-016; renumbered
again to UI-014–UI-017 to avoid colliding with the now-completed UI-013 (Panel
Framework).

- UI-014 Workspace ordering/pinning — persist explicit tab order instead of
  registration/open order.
- UI-015 Multi-consumer workspace support — generalize the
  `hasSavedState()` / restore-before-default-open contract so any module
  (not just LTSA) adopting the workspace engine gets correct persistence
  by construction, rather than by convention.
- UI-016 Workspace storage versioning/migration — guard against stale
  `localStorage` shapes if the persisted schema changes again.
- UI-017 Clarify/remove the inert app-level `WorkspaceProvider` in
  `app/providers.jsx` (see `TECHNICAL_DEBT.md`, found in UI-012).
- UI-018 Migrate `modules/ltsa/components/Panel.jsx` to the new design-system
  `Panel` (from UI-013), once a module is ready to adopt it.
