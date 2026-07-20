# MWO-LTSA-056 — Pump Management UI Polish

Status: **COMPLETED**
Type: Manufacturing Work Order (Implementation)
Role: Implementation Engineer
Architecture: FROZEN — nothing in this MWO changes it; no design-system component, backend, API, or Seal Workspace file was modified.
Basis: Direct read of `AI5R-STUDIO/dashboard/src/modules/ltsa/{pages/Pump.jsx,pages/Pump.css,components/PumpRegistryTable.jsx,components/PumpDetailPanel.jsx,components/PumpFilterBar.jsx,data/samplePumps.js}` and their existing test files; `AI5R-STUDIO/dashboard/src/design-system/*` read-only, for reuse.
Identifier note: `MWO-LTSA-051` was already taken (`MWO-LTSA-051-Engineering-Knowledge-Graph-Research.md`) — per explicit Chief Architect decision, that document was left untouched and this work was assigned the next unused number in the existing `MWO-LTSA-0XX` sequence (`052`–`055` already taken; `056` free).

---

## Goal

Prepare the Pump Workspace for customer demonstration.

## Scope

- Pump Registry UI (`PumpRegistryTable.jsx`)
- Pump Detail Panel (`PumpDetailPanel.jsx`)
- Sample Pump Data enhancement (`data/samplePumps.js`)
- UI Tests (`*.test.jsx`, `*.test.js` under `modules/ltsa`)

## Out of Scope

Backend, Dashboard, Seal Workspace, Work Order, API, Architecture (design-system components consumed read-only, not modified).

---

## Baseline

Full dashboard suite green before any change: `npx vitest run` — 39 test files, 108 tests passed.

## Findings and Changes

1. **`PumpRegistryTable.jsx` — no feedback on an empty filtered result.** Searching or filtering to zero matches previously rendered a bare table with only column headers, no row and no message — a visible gap for a live customer demo. Fixed by reusing the existing `EmptyState` design-system component (already used elsewhere in this same module, e.g. `PumpDetailPanel`'s "no pump selected" state) when `pumps.length === 0`. No new component introduced.
2. **`PumpDetailPanel.jsx` — `tag` field missing from the detail view.** The Pump Registry table surfaces each pump's field tag (e.g. `211-P-1A`), but the Detail Panel never displayed it, despite `tag` already being present on every sample pump record. Added as a `Field` row directly under Pump Code.
3. **`PumpDetailPanel.jsx` — dead `STATUS_MODIFIER` map removed.** The file defined a `STATUS_MODIFIER` lookup that was never actually applied — the line computing it was a no-op ternary (`STATUS_MODIFIER[pump.status] ? pump.status : pump.status`, both branches identical), so it had zero effect on rendering. Removed as dead/misleading code; `StatusBadge` is still called exactly as before (`status={pump.status}`), matching the same calling convention already used by the sibling `SealDetailPanel.jsx` (out of scope, not modified) — no behavior change, no design-system change.
4. **`samplePumps.js` — sample data expanded.** Added three additional pumps (`PMP-011`–`PMP-013`: Reflux Pump + spare, Slurry Transfer Pump) covering ACTIVE/STANDBY/MAINTENANCE statuses and new manufacturers (Sundyne, Weir Minerals), for a fuller, more varied demo registry. Purely additive — none of the original ten records (`PMP-001`–`PMP-010`) were changed.

## Tests

- `PumpRegistryTable.test.jsx` — added: renders an empty state instead of a bare table when no pumps match.
- `PumpDetailPanel.test.jsx` — extended existing "renders every required field" test to assert the `tag` value is shown.
- `Pump.test.jsx` — renamed the "renders all 10 sample pumps" test (title would have gone stale the moment sample data grew) to "renders every sample pump," logic unchanged; added: shows an empty state in the registry when no pump matches the search.
- Full suite re-run after changes: **39 test files, 110 tests, all passing** (108 baseline + 2 new).

## Files Touched

- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/PumpRegistryTable.jsx`
- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/PumpRegistryTable.test.jsx`
- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/PumpDetailPanel.jsx`
- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/PumpDetailPanel.test.jsx`
- `AI5R-STUDIO/dashboard/src/modules/ltsa/pages/Pump.test.jsx`
- `AI5R-STUDIO/dashboard/src/modules/ltsa/data/samplePumps.js`
- `CURRENT_MWO.md` (created/updated)
- `ENGINEERING/history.log` (created, completion entry appended)

## Definition of Done — Status (Phase 1, UI Polish)

- Pump Registry polished — **Met** (§Findings 1).
- Pump Detail Panel polished — **Met** (§Findings 2–3).
- Sample data expanded — **Met** (§Findings 4).
- Tests passing — **Met** (110/110 green).
- Engineering History updated — **Met** (`ENGINEERING/history.log`).

Reviewed and accepted by Chief Architect. Same MWO continued below for Phase 2 — no new MWO created, per explicit instruction.

---

## Phase 2 — Product Quality Redesign

Status: **COMPLETED — Definition of Done met, reviewed and approved by Chief Architect.**
Objective shift, per Chief Architect direction: this phase is no longer about engineering completeness — it is about product quality for a customer-facing demo. Scope unchanged (Pump Registry, Pump Detail Panel, Sample Pump Data, UI Tests); Backend, Dashboard, Seal Workspace, Work Order, API, and Architecture remain out of scope and were not touched (confirmed by `git diff --stat` against `design-system/`, `SealDetailPanel.jsx`, `CORE-SERVICES/`, `AI5R-SDK/` — empty).

### 1. Pump Registry — redesigned

Replaced the engineering/database-oriented column set (`Code, Tag, Name, Manufacturer, Type, Status`) with a maintenance-oriented one: **Pump** (Tag/Name/Manufacturer grouped in one cell), **Area**, **Health Score** (color-coded — green ≥80, amber 50–79, red <50), **Next PM**, **Open Work Orders**, **Status** (badge). `pump.code` remains in the data model (used internally for row keys/selection) but is no longer rendered as its own column — the raw database primary key is exactly the kind of engineering-oriented detail the new objective asks to de-emphasize.

Implementation note: the shared design-system `Table` component only renders raw per-cell strings (no per-column render callback), and extending it would be a design-system/architecture change — out of scope. Instead, `PumpRegistryTable.jsx` now owns its own semantic `<table>` markup directly (still emitting the same native `table/row/columnheader/cell` ARIA roles), so the shared `Table` component itself remains completely unmodified and available to every other consumer exactly as before.

### 2. Pump Detail Panel — redesigned into four sections

- **Equipment Summary** — Pump Code, Tag, Manufacturer, Pump Type, Seal, Location, Area, Criticality (badge), Status (badge).
- **Maintenance Summary** — Health Score (color-coded), Availability, Runtime Hours, Last PM, Next PM, Open Work Orders.
- **AI Recommendation** — the existing free-text recommendation field, plus Knowledge Links (carried over unchanged — they are supporting evidence for the recommendation, not a fifth section not requested).
- **Quick Actions** — View History / Create PM / Create CM / Documents, rendered as disabled `Button`s (no backend exists to wire them to, per explicit scope — "Buttons may be disabled" was taken literally rather than fabricating fake handlers).

The pump's name, previously the single `Card`'s own title, is now shown as its own heading above the four sections (a real gap caught by the test suite during this phase: the first implementation dropped it entirely, silently regressing "which pump is this" — restored before completion).

`StatusBadge` (design-system) was replaced with `Badge` for both Registry and Detail Panel status display: `StatusBadge`'s internal modifier vocabulary (`active/warning/error/idle`) does not match this domain's status vocabulary (`RUNNING/STANDBY/MAINTENANCE/FAULT`), and modifying `StatusBadge` itself is a design-system/architecture change, out of scope. `Badge`'s existing variant set (`success/info/warning/danger`) was reused unmodified via a small local mapping — no design-system file was touched.

### 3. Sample Data — expanded per pump

Added `area`, `healthScore`, `availability`, `runtimeHours`, `lastPM`, `nextPM`, `openWO`, `criticality` to all 13 pumps, with realistic refinery-plausible values (health scores reflecting each pump's existing `recommendation` narrative — e.g. `PMP-009`, already FAULT with "repeat seal failures," now also carries `healthScore: 18`, `availability: 62.5`).

**Status vocabulary changed:** `ACTIVE → RUNNING` (customer-facing language, replacing the internal/engineering term); `ALERT` retired — the one pump that carried it (`PMP-006`) is now `RUNNING` with a depressed `healthScore` (61) and its original recommendation text intact, since Health Score + AI Recommendation now carry that nuance instead of a fifth status value. `STANDBY`, `MAINTENANCE`, `FAULT` unchanged. Final closed set is exactly the four requested: `RUNNING / STANDBY / MAINTENANCE / FAULT`.

New shared helper `AI5R-STUDIO/dashboard/src/modules/ltsa/utils/pumpHealth.js` (Pump-module-local, not design-system) centralizes the health-score color thresholds and the status/criticality → badge-variant mappings, so Registry and Detail Panel can't silently drift apart on what counts as "healthy" vs. "at risk."

### 4. Tests — updated, all green

- New: `utils/pumpHealth.test.js` (color/variant mapping).
- Rewritten: `PumpRegistryTable.test.jsx` (new columns, badge rendering, health-score coloring, empty state).
- Rewritten: `PumpDetailPanel.test.jsx` (four sections, all new fields, disabled Quick Action buttons).
- Updated: `Pump.test.jsx` — selection/search/filter assertions now target `pump.tag` (e.g. `"305-P-2"`) instead of `pump.code` (e.g. `"PMP-003"`), since the code is no longer rendered in the registry; filter-by-status assertion updated to the new `FAULT` tag.
- `Pump.jsx` itself required **no code changes** — its search/filter/selection logic was already generic over field names and status values.
- One environment-dependent defect caught and fixed during this phase: `runtimeHours.toLocaleString()` used the host's default locale, which rendered `31.450 hrs` (period thousands-separator) instead of the expected `31,450 hrs` on this machine — pinned to `toLocaleString("en-US")` for deterministic output regardless of host locale.
- Full suite after all fixes: **40 test files, 121 tests, all green** (121 = 110 prior + pumpHealth's 8 new tests + 3 net new assertions across the rewritten Pump-module tests).

### Files Touched (Phase 2)

- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/{PumpRegistryTable,PumpDetailPanel}.jsx` (redesigned)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/components/{PumpRegistryTable,PumpDetailPanel}.test.jsx` (rewritten)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/pages/Pump.test.jsx` (updated assertions only)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/data/samplePumps.js` (expanded)
- `AI5R-STUDIO/dashboard/src/modules/ltsa/utils/pumpHealth.{js,test.js}` (new)
- `ENGINEERING/history.log` (Phase 2 completion entry appended)

### Definition of Done — Status (Phase 2, Product Quality Redesign)

- Pump Registry redesigned to maintenance-oriented columns with color-coded health score and status badges — **Met**.
- Pump Detail Panel redesigned into the four requested sections with all requested fields — **Met**.
- Sample data expanded with all eight requested fields, realistic values — **Met**.
- Tests updated, everything green — **Met** (121/121).
- Engineering History updated — **Met** (`ENGINEERING/history.log`).

---

Reviewed and approved by Chief Architect (2026-07-20). MWO-LTSA-056 is CLOSED. No commit, no push (unchanged files remain uncommitted in the working tree pending separate commit approval). Superseded by `MWO-LTSA-057-Work-Order-Workspace.md`.
