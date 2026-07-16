# AI5R Studio — UI Track Architectural Decisions

## Workspace persistence lives behind `hasSavedState()`, not an implicit ordering rule

**Decision (UI-011):** consumers must explicitly check `hasSavedState()` before running
default-open logic, rather than relying on call order between bootstrap and restore.

**Why:** the original UI-011 draft had `LTSA.jsx` call `bootstrapLTSA()` (which
unconditionally opened all `defaultOpen` workspaces) and then `restoreWorkspace()`.
Because `openWorkspace()` persists on every call, the bootstrap step silently
overwrote any real persisted state before `restore()` could read it — the feature
looked implemented but never actually kept a closed tab closed. Making the check
explicit (`hasSavedState()`) instead of implicit-through-ordering means the bug
surfaces immediately in any new consumer that forgets it, rather than passing code
review while being broken at runtime.

## `WorkspaceManager` and `WorkspaceStorage` stay framework-agnostic

**Decision:** neither class imports React; only `WorkspaceProvider` does.

**Why:** keeps the lifecycle/persistence logic unit-testable without a DOM and
reusable if a non-React consumer ever needs it.

## Active-workspace persistence, not just opened-list persistence

**Decision (UI-011):** `WorkspaceStorage` persists `{ openedWorkspaces,
activeWorkspace }`, and `activateWorkspace()` now writes to storage (it previously
didn't).

**Why:** persisting only the opened list without the active tab meant switching
tabs and reloading always snapped back to the first opened workspace — not what a
user would expect from "workspace persistence."
