# AI5R Studio — UI Track Roadmap

## Completed

- UI-007 Recover LTSA dashboard and stabilize studio shell
- UI-008 Activate AI5R workspace engine
- UI-009 Stabilize workspace integration
- UI-010 Add workspace lifecycle
- UI-011 Workspace persistence
- UI-012 Workspace shell upgrade
- UI-013 Panel framework
- UI-014 Docking system v1

## Next milestones

Note: these were previously numbered UI-012–UI-014, then UI-013–UI-016, then
UI-014–UI-018; renumbered again to UI-015–UI-019 to avoid colliding with the
now-completed UI-014 (Docking System v1).

- UI-015 Workspace ordering/pinning — persist explicit tab order instead of
  registration/open order.
- UI-016 Multi-consumer workspace support — generalize the
  `hasSavedState()` / restore-before-default-open contract so any module
  (not just LTSA) adopting the workspace engine gets correct persistence
  by construction, rather than by convention.
- UI-017 Workspace storage versioning/migration — guard against stale
  `localStorage` shapes if the persisted schema changes again.
- UI-018 Clarify/remove the inert app-level `WorkspaceProvider` in
  `app/providers.jsx` (see `TECHNICAL_DEBT.md`, found in UI-012).
- UI-019 Migrate `modules/ltsa/components/Panel.jsx` to the new design-system
  `Panel` (from UI-013), once a module is ready to adopt it.
- UI-020 Docking drag-drop + persistence — generalize `DockManager` (from UI-014)
  with panel↔area reassignment and a storage layer, once a consumer needs it.
