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

