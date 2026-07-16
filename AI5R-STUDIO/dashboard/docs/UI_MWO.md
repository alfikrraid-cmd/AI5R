# AI5R Studio UI Manufacturing Work Orders (MWO)

## Purpose

This document tracks AI5R Studio UI development milestones.

AI5R Studio UI is built as a reusable platform layer.

Principle:

- Design System = Framework
- Modules = Business Capability
- Workspace = Application Runtime

Do not mix Factory Pack business logic into Design System.

---

# Completed MWO

---

## UI-008 — Workspace Engine Foundation

Status:
✅ Completed

Commit:
8ce5873

Objective:

Create the first Workspace Framework.

Implemented:

- WorkspaceRegistry
- WorkspaceManager
- WorkspaceProvider
- WorkspaceContext
- WorkspaceTabs
- WorkspaceLayout

Architecture:

---

## UI-012 — Workspace Shell Upgrade

Status:
✅ Completed

Objective:

Transform the dashboard layout chrome into a consistent AI5R Studio shell and
remove dead/legacy layout code, without touching the Workspace Engine API.

Scope:

- `design-system/layout/**`
- `design-system/workspace/**`
- `src/layouts/MainLayout.jsx` (scope expanded mid-MWO; see below)

Implemented:

- Deleted `design-system/layout/Workspace.jsx`, `design-system/layout/WorkspaceTabs.jsx`,
  and `design-system/layout/MainLayout.backup.jsx` — dead legacy placeholders (hardcoded
  static tabs, no engine wiring), referenced only by the unused backup file, fully
  superseded by the real `design-system/workspace/components/*`.
- Restyled `Topbar.jsx`, `Breadcrumb.jsx`, `StatusBar.jsx` to the same studio palette
  already used by `Sidebar.jsx` and the workspace-tabs CSS (`#0F172A` / `#1E293B` /
  `#2563EB`). Dropped the hardcoded "LTSA Engineering" label from `Topbar` in favor of
  generic "AI5R Studio" / "Digital Factory Shell" branding.

Investigated and explicitly rejected:

- Wiring the real `WorkspaceTabs` (from `design-system/workspace`) into
  `src/layouts/MainLayout.jsx` as an app-wide tab strip. `modules/ltsa/pages/LTSA.jsx`
  already mounts its own nested `WorkspaceProvider` + `WorkspaceTabs` + `WorkspaceLayout`
  — a working, self-contained workspace runtime for that module. Adding a second,
  app-level `WorkspaceTabs` bound to the outer (inert) `WorkspaceProvider` from
  `app/providers.jsx` produced a duplicate tab bar (one empty, one populated) when
  navigating to `/ltsa`, confirmed via a component-render test. Reverted. Confirms the
  intended architecture: "Workspace = Application Runtime" means each business module
  owns its own workspace runtime; there is no shared, app-wide tab strip.

Not changed:

- `WorkspaceManager`, `WorkspaceRegistry`, `WorkspaceStorage` — Engine API/logic untouched.
- `CORE-SERVICES`, `PRODUCTS`, `AI5R-SDK` — untouched.

See `TECHNICAL_DEBT.md` for the follow-up item this investigation surfaced.

---

## UI-013 — Panel Framework

Status:
✅ Completed

Objective:

Add a reusable, business-logic-free Panel primitive to the design system for
consuming modules to build page content with.

Scope:

- `design-system/panels/**` (new)

Implemented:

- `Panel.jsx` — card container. Props: `title` (optional), `children`, `collapsible`
  (default `false`), `defaultCollapsed` (default `false`). Owns its own collapse state
  (uncontrolled). Renders `PanelHeader` only when `title` is given; otherwise renders a
  body-only card.
- `PanelHeader.jsx` — presentational title bar with an optional collapse chevron
  (`lucide-react` `ChevronUp`/`ChevronDown`). No internal state; driven entirely by
  props (`title`, `collapsible`, `collapsed`, `onToggle`).
- `PanelContainer.jsx` — layout wrapper for arranging multiple panels: single-column
  flex stack by default, or a CSS grid when `columns` is given. Props: `children`,
  `columns` (optional), `gap` (default `20`).
- `index.js` — barrel export of `Panel`, `PanelHeader`, `PanelContainer`.
- Styled with the same studio palette established in UI-012
  (`#0F172A` background / `#1E293B` border / `#F1F5F9` title text).

Verified via a component-render test (removed after passing, per this repo's
convention of not committing throwaway smoke tests): title+children render, title-less
body-only card, collapse/expand toggle, `defaultCollapsed`, and `PanelContainer`
arranging multiple panels.

Not changed:

- Workspace Engine, `modules/ltsa`, `CORE-SERVICES`, `PRODUCTS`, `AI5R-SDK` — untouched.
- No wiring into any consumer yet (e.g. `modules/ltsa/components/Panel.jsx` still exists
  and is unrelated/untouched) — that migration is a future MWO's job, not this one's.

---

## UI-014 — Docking System v1

Status:
✅ Completed

Objective:

Add a generic, design-system-level docking capability supporting four fixed dock
areas (`left`, `center`, `right`, `bottom`), with no drag-drop and no persistence —
a deliberately minimal first cut.

Scope:

- `design-system/docking/**` (new)

Implemented:

- `DockRegistry.js` — plain class, mirrors `WorkspaceRegistry`. Exports
  `DOCK_AREAS = ["left", "center", "right", "bottom"]`; `register()` validates a
  descriptor's `area` against this list.
- `DockManager.js` — plain class, mirrors `WorkspaceManager`. Tracks open/active
  panels **per area independently** (each area behaves like its own tab strip). A
  panel's area is fixed at registration — there is no "move to another area" API,
  since there is no drag-drop yet. No persistence (no `WorkspaceStorage` equivalent).
- `DockPanel.jsx` — presentational. Renders a tab strip (title + optional close `×`)
  for the panels open in one area, plus the active panel's `component`. Renders
  `null` when nothing is open in that area, so the layout can collapse it.
- `DockLayout.jsx` — consumer-facing entry point. Takes a flat `panels` descriptor
  array (`{ id, title, area, component, closable?, defaultOpen? }`), builds its own
  `DockRegistry`/`DockManager` internally via `useRef` (same idiom as
  `design-system/panels/Panel.jsx` and `WorkspaceProvider`'s ref-init pattern) —
  these instances are **not** exposed to children via context/provider, per explicit
  instruction for this MWO. Registers + opens `defaultOpen` panels on mount. Lays out
  left/right as fixed-width columns and bottom as a fixed-height row, all three
  collapsing to nothing when empty; center always renders and flexes to fill the
  remaining space.
- `index.js` — barrel export of `DockManager`, `DockRegistry`, `DOCK_AREAS`,
  `DockLayout`, `DockPanel`.
- Styled with the same studio palette from UI-012/UI-013
  (`#0F172A` background / `#1E293B` border / `#2563EB` active-tab accent).

Verified via a component/unit test (removed after passing, per this repo's convention
of not committing throwaway smoke tests): `DOCK_AREAS` shape, `DockRegistry` rejects
an invalid area, `DockManager` tracks open/active state per area independently
(closing the active tab in one area doesn't affect another area), `DockLayout` renders
all four areas with `defaultOpen` panels, collapses areas with nothing open, and
switches the active tab within an area on click.

Not changed:

- Workspace Engine, `modules/ltsa`, `design-system/panels`, `CORE-SERVICES`,
  `PRODUCTS`, `AI5R-SDK` — untouched.
- No drag-drop (panel↔area reassignment), no persistence, no context/provider exposing
  the manager — all explicitly deferred past v1.

---

## UI-015 — Inspector Framework v1

Status:
✅ Completed

Objective:

Add a generic, design-system-level property-inspector capability: a titled panel
with an action slot, containing collapsible sections of label/value fields.

Scope:

- `design-system/inspector/**` (new)

Implemented:

- `Inspector.jsx` — outer card. Props: `title`, `actions` (ReactNode, the action
  slot), `children` (sections). Renders `InspectorHeader` then a scrollable body.
  Owns layout only — no state of its own.
- `InspectorHeader.jsx` — presentational title bar with an action slot on the right
  (mirrors `Topbar`'s left-title/right-actions layout). No internal state.
- `InspectorSection.jsx` — a labeled, optionally-collapsible group of fields. Props:
  `title` (optional), `children`, `collapsible` (default `false`), `defaultCollapsed`
  (default `false`). Owns its own collapse state locally (same uncontrolled pattern
  as `design-system/panels/Panel.jsx`) — independent per section, so collapsing one
  section has no effect on others.
- `InspectorField.jsx` — a single label/value row. Props: `label`, `value`
  (string/number, optional), `children` (optional — overrides `value` rendering for
  custom content, e.g. a control instead of plain text).
- `index.js` — barrel export of `Inspector`, `InspectorHeader`, `InspectorSection`,
  `InspectorField`.
- Styled with the same studio palette from UI-012–UI-014
  (`#0F172A` background / `#1E293B` border / `#F1F5F9` primary text / `#94A3B8`
  secondary text).
- Self-contained: does not import from `design-system/panels` or
  `design-system/docking` despite conceptual similarity to `Panel`/`PanelHeader` —
  kept independent per this repo's established pattern of each design-system MWO
  being strictly additive/isolated.

Verified via a component-render test (removed after passing, per this repo's
convention of not committing throwaway smoke tests): title/action-slot/sections/
fields render together, `InspectorField` children override `value`, sections
collapse/expand independently of each other, `defaultCollapsed` starts collapsed,
and a section renders correctly with no title (body-only).

Not changed:

- Workspace Engine, Docking System, `design-system/panels`, `modules/ltsa`,
  `CORE-SERVICES`, `PRODUCTS`, `AI5R-SDK` — untouched.
- No business logic, no Factory Pack dependency, no field editing/`onChange` (v1 is
  read-only display) — all explicitly deferred past v1.

---

## UI-016 — DataGrid Framework v1

Status:
✅ Completed

Objective:

Add a generic, design-system-level tabular data capability: columns/rows rendering
with sorting, row selection, and pagination — all as UI-only internal state, with
no domain-specific behavior of any kind.

Scope:

- `design-system/datagrid/**` (new)

Implemented:

- `DataGrid.jsx` — orchestrator. Props: `columns`, `rows`, `rowKey` (default `"id"`),
  `selectable` (default `false`), `pageSize` (optional — omitting it disables
  pagination), `onSortChange`/`onSelectionChange` (optional observer callbacks; state
  is owned internally and uncontrolled, no provider/context in v1). Owns `sort`
  (`{ key, direction }`, cycles asc→desc→none per column click), `selectedIds`
  (`Set`, toggle row / select-all-on-current-page), and `page` (0-indexed) as local
  `useState`. Default sort comparator is numeric-or-`localeCompare`; a column may
  override via `column.sortFn(rowA, rowB)`. Renders a `<table>` wrapping
  `DataGridHeader` + `DataGridRow`s, and `DataGridPagination` only when `pageSize`
  is given.
- `DataGridHeader.jsx` — presentational `<thead>`. Column titles, click-to-sort with
  a chevron indicator (`lucide-react`), select-all checkbox when `selectable`. Driven
  entirely by props.
- `DataGridRow.jsx` — presentational `<tr>`. Row-selection checkbox (if `selectable`)
  + one `DataGridCell` per column.
- `DataGridCell.jsx` — presentational `<td>`. Renders `column.render(row)` if given,
  else `row[column.key]`, respecting `column.align`.
- `DataGridPagination.jsx` — presentational footer: total row count, "Page X of Y",
  prev/next buttons.
- `index.js` — barrel export of `DataGrid`, `DataGridHeader`, `DataGridRow`,
  `DataGridCell`, `DataGridPagination`.
- Styled with the same studio palette from UI-012–UI-015.
- Self-contained: no imports from `design-system/panels`, `design-system/docking`, or
  `design-system/inspector`, matching this repo's pattern of each design-system MWO
  being strictly additive/isolated. No Pump/Invoice/Product-specific logic anywhere —
  columns are opaque `{ key, title, sortable?, align?, render?, sortFn? }`
  descriptors, rows are opaque objects.

Verified via a component-render test (removed after passing, per this repo's
convention of not committing throwaway smoke tests): columns/rows render, the
asc→desc→none sort cycle reorders rows correctly on repeated header clicks, row
selection + select-all-on-current-page work and report ids via
`onSelectionChange`, pagination slices rows and navigates between pages (Next
disabled on the last page), and no pagination footer renders when `pageSize` is
omitted.

Not changed:

- Workspace Engine, Docking System, Inspector Framework, Panel Framework,
  `modules/ltsa`, `CORE-SERVICES`, `PRODUCTS`, `AI5R-SDK` — untouched.
- No controlled state/provider/context, no server-side sort/page hooks, no column
  resize/reorder — all explicitly deferred past v1.

---

## UI-017 — Command Toolbar Framework v1

Status:
✅ Completed

Objective:

Add a generic, design-system-level command toolbar: grouped buttons with icons,
disabled state, and action callbacks — fully stateless, since a toolbar's state
(which button is active/disabled, what an action does) is the consumer's concern,
not the framework's.

Scope:

- `design-system/toolbar/**` (new)

Implemented:

- `Toolbar.jsx` — outer container. Props: `children` only (groups/buttons/
  separators). Purely a styled flex-row wrapper, no state.
- `ToolbarGroup.jsx` — visual clustering of related buttons (tighter internal gap
  than the outer toolbar). Props: `children` only.
- `ToolbarSeparator.jsx` — a vertical divider between groups. No props.
- `ToolbarButton.jsx` — the button. Props: `icon` (ReactNode, optional — the
  framework is icon-library-agnostic; the consumer renders their own icon, e.g. a
  `lucide-react` icon), `label` (string, optional — icon-only button when omitted),
  `onClick`, `disabled` (default `false`, native `<button disabled>`), `active`
  (default `false`, accent-background "pressed" styling for toggle-style buttons),
  `title` (native tooltip).
- `index.js` — barrel export of `Toolbar`, `ToolbarButton`, `ToolbarGroup`,
  `ToolbarSeparator`.
- Styled with the same studio palette from UI-012–UI-016.
- All four components are fully stateless (no `useState`, no context) — the simplest
  tier of this design-system track, unlike the stateful `Panel`/`InspectorSection`/
  `DataGrid`, because a toolbar has no internal UI state of its own to own.
- Self-contained: no imports from `design-system/panels`, `design-system/docking`,
  `design-system/inspector`, or `design-system/datagrid`. No business logic, no
  Factory Pack dependency.

Verified via a component-render test (removed after passing, per this repo's
convention of not committing throwaway smoke tests): groups/separators/icons/labels
render together, `onClick` fires on an enabled button, a `disabled` button's native
`disabled` attribute is set and its `onClick` never fires, icon-only buttons render
without a label, and `active` applies the accent-background styling.

Not changed:

- Workspace Engine, Docking System, Inspector Framework, DataGrid Framework, Panel
  Framework, `modules/ltsa`, `CORE-SERVICES`, `PRODUCTS`, `AI5R-SDK` — untouched.
- No dropdown/menu buttons, no keyboard-shortcut display, no right-aligned slot on
  `Toolbar` — all explicitly deferred past v1.

---

## UI-018 — Feedback System v1

Status:
✅ Completed

Objective:

Add a generic, design-system-level feedback capability: success/warning/error/info
messaging plus loading/empty/error placeholder states. Fully stateless — no
Provider/Context, no timers, no API calls, no navigation, no global state. Every
component renders UI purely from its props.

Scope:

- `design-system/feedback/**` (new)

Implemented:

- `Toast.jsx` — a small message card (positioning/stacking/auto-dismiss timing is
  left to the consumer — no queue/manager here). Props: `variant`
  (`"success" | "warning" | "error" | "info"`, default `"info"`), `message`, `icon`
  (optional override), `onClose` (optional — renders a `×` button when given).
- `Notification.jsx` — a wider inline banner/alert for in-page persistent messages
  (vs. `Toast`'s floating-popup feel). Props: `variant`, `title` (optional),
  `message`, `icon` (optional override), `actions` (ReactNode, optional action
  slot), `onClose` (optional).
- Both `Toast` and `Notification` map `variant` to an icon/color locally (duplicated
  small lookup per file, not a shared util — consistent with keeping each file
  self-contained): success → `CheckCircle` `#22C55E` (matches the existing "Runtime
  Online" green in `Topbar.jsx`), warning → `AlertTriangle` `#F59E0B`, error →
  `XCircle` `#EF4444`, info → `Info` `#38BDF8`.
- `LoadingState.jsx` — centered spinner + message. Props: `message` (default
  `"Loading..."`), `size` (default `24`). Uses a `lucide-react` `Loader2` icon with
  a CSS `@keyframes` spin declared via a scoped inline `<style>` tag inside the
  component itself (no JS-driven animation state; and no other file, e.g.
  `index.css`, was touched — out of scope).
- `EmptyState.jsx` — centered "nothing here" placeholder. Props: `icon` (ReactNode,
  optional, no forced default since context varies), `title`, `description`
  (optional), `action` (ReactNode, optional).
- `ErrorState.jsx` — centered failure placeholder. Props: `title` (default
  `"Something went wrong"`), `description` (optional), `action` (ReactNode,
  optional), `icon` (optional override; defaults to `AlertTriangle` since "error"
  has one canonical visual identity, unlike `EmptyState`).
- `index.js` — barrel export of `Toast`, `Notification`, `LoadingState`,
  `EmptyState`, `ErrorState`.
- Styled with the same studio palette from UI-012–UI-017.
- All five components are fully stateless (no `useState`, no context, no timers, no
  API calls, no navigation, no global state) — same tier as `design-system/toolbar`.
- Self-contained: no imports from `design-system/panels`, `design-system/docking`,
  `design-system/inspector`, `design-system/datagrid`, or `design-system/toolbar`.

Verified via a component-render test (removed after passing, per this repo's
convention of not committing throwaway smoke tests): `Toast` renders its message and
fires `onClose` when clicked, and renders with no close button when `onClose` is
omitted; `Notification` renders title/message/actions slot together;
`LoadingState` renders its default and a custom message; `EmptyState` renders
title/description/action; `ErrorState` renders its default title plus a custom
description/action.

Not changed:

- Workspace Engine, Docking System, Inspector Framework, DataGrid Framework,
  Toolbar Framework, Panel Framework, `modules/ltsa`, `CORE-SERVICES`, `PRODUCTS`,
  `AI5R-SDK` — untouched.
- No Provider/Context, no auto-dismiss timers, no toast stacking/manager — all
  explicitly deferred past v1.

