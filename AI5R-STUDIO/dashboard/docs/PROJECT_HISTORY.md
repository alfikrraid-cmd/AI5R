# AI5R Studio — UI Track Milestone History

| MWO | Title | Summary |
|---|---|---|
| UI-007 | Recover LTSA dashboard and stabilize studio shell | Recovery baseline for the LTSA dashboard/studio shell after prior instability. |
| UI-008 | Activate AI5R workspace engine | Introduced the Studio app shell and wired `WorkspaceProvider` into the app. |
| UI-009 | Stabilize workspace integration | Fixed export/integration mismatches between the workspace engine and `LTSAWorkspace.jsx`. |
| UI-010 | Add workspace lifecycle | Implemented open/close/activate lifecycle and tab rendering. |
| UI-011 | Workspace persistence | Added `localStorage`-backed persistence of opened/active workspaces across reloads, and fixed a bootstrap-ordering bug that was silently defeating persistence for `defaultOpen` workspaces. |
| UI-012 | Workspace shell upgrade | Unified shell chrome palette (`Topbar`/`Breadcrumb`/`StatusBar`), removed dead legacy layout placeholders, and confirmed (by testing, then rejecting) that an app-wide `WorkspaceTabs` in `MainLayout.jsx` is wrong — `LTSA.jsx` already owns its own workspace runtime instance. |
| UI-013 | Panel framework | Added `design-system/panels/` (`Panel`, `PanelHeader`, `PanelContainer`) — a reusable, business-logic-free card primitive with optional collapse. No consumer wiring yet. |
| UI-014 | Docking system v1 | Added `design-system/docking/` (`DockRegistry`, `DockManager`, `DockPanel`, `DockLayout`) supporting fixed `left`/`center`/`right`/`bottom` areas. No drag-drop, no persistence, no consumer wiring yet. |
| UI-015 | Inspector framework v1 | Added `design-system/inspector/` (`Inspector`, `InspectorHeader`, `InspectorSection`, `InspectorField`) — a titled panel with an action slot and collapsible sections of label/value fields. Read-only, no consumer wiring yet. |
| UI-016 | DataGrid framework v1 | Added `design-system/datagrid/` (`DataGrid`, `DataGridHeader`, `DataGridRow`, `DataGridCell`, `DataGridPagination`) — columns/rows rendering with sorting, row selection, and pagination as uncontrolled UI-only state. Domain-agnostic, no consumer wiring yet. |
| UI-017 | Command toolbar framework v1 | Added `design-system/toolbar/` (`Toolbar`, `ToolbarGroup`, `ToolbarSeparator`, `ToolbarButton`) — grouped buttons with icons, disabled state, and action callbacks. Fully stateless, icon-library-agnostic, no consumer wiring yet. |

Each row is a milestone in the Workspace Engine's evolution; see `CHANGELOG.md` for
change-level detail and `CURRENT_STATE.md` for the engine's present shape.
