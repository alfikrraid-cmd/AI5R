# PM-000 — Pump Registry Canonicalization Report

Parent: MWO-P-004 — Pump Registry Functional Completion (WP-000)
Branch: `feature/ltsa-brain` (local; not committed)
Basis: `ENGINEERING/MWO/MWO-P-001-LTSA-Product-Audit.md`, `ENGINEERING/MWO/LTSA-Integrity-Recovery-Summary.md` (+ `IR-001`, `IR-002`, `IR-003`) — no new audit scope opened

---

## Method

Every Pump-related artifact under `PRODUCTS/LTSA-BRAIN` was located and read in full: all 5 `BP-PUMP/WORKFLOWS/*.json` files (including their embedded `settings.registry` metadata), `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-REGISTRY-001.json`, `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-PUMP-DETAIL-001.json`, `MODULES/PUMP/DATABASE/001_create_pumps.sql`, all 4 `BP-PUMP/DATABASE/*.sql` files, `MODULES/PUMP/API/openapi.yaml`, `BUILD-PACKS/BP-PUMP/SCHEMAS/pump.openapi.json`, `BP-PUMP/README.md`, and `MODULES/PUMP/DOCS/PUMP_REGISTRY_SPEC.md`. State was re-verified immediately before this report (`git status` against `PRODUCTS/LTSA-BRAIN` shows no drift since MWO-P-004 was drafted). For each operation, the artifact whose logic already targets the IR-001-canonical `ltsa_pumps` schema was selected as canonical — the same rule used in `CR-000-Canonicalization-Report.md` for Customer Registry.

---

## Full Artifact Inventory

| # | Path | Content |
|---|---|---|
| 1 | `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-REGISTRY-001.json` | Real: webhook → validate → `INSERT INTO ltsa_pumps (...) RETURNING *` → response. Resolved credential (`hzgFaX04t1nL01vF`, per IR-003). |
| 2 | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-PUMP-DETAIL-001.json` | Real: webhook → parse/validate `tag_number` → `SELECT * FROM public.ltsa_pumps WHERE tag_number = ...` → 200/404. Resolved credential. |
| 3 | `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-CREATE-001.json` | Stub: webhook → hardcoded static JSON (`"table": "pump_registry"`). No Postgres node. |
| 4 | `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-DETAIL-001.json` | Stub: same pattern, `"table": "pump_registry"`. |
| 5 | `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-LIST-001.json` | Stub: same pattern, `"table": "pump_registry"`. |
| 6 | `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-UPDATE-001.json` | Stub: same pattern, `"table": "pump_registry"`. |
| 7 | `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-DELETE-001.json` | Stub: same pattern, `"table": "pump_registry"`. |

No Pump Registry workflow artifact was found anywhere outside these three locations (`MODULES/PUMP/WORKFLOWS/`, `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/`, `BUILD-PACKS/BP-PUMP/WORKFLOWS/`).

---

## Comparison and Decision, Per Operation

**Every one of the five `BP-PUMP/WORKFLOWS/*.json` files carries identical `settings.registry` metadata**: `"table": "pump_registry"`, `"primary_key": "pump_code"`, fields `pump_code, pump_name, manufacturer, model, serial_number, location, status`. This is a different table, a different primary-key type (`TEXT` vs. canonical `UUID`), and a different field set than canonical `ltsa_pumps` (`tag_number, area, location, pump_type, api_plan, seal_type, status, manufacturer, model, drawing_ref, notes`). `BUILD-PACKS/BP-PUMP/README.md` independently confirms "Table: pump_registry, Primary Key: pump_code." All four `BP-PUMP/DATABASE/*.sql` files already carry `DEPRECATED (MWO-P-002 / IR-001)` headers, confirmed by direct read of `001_create_table.sql`, `002_seed.sql`, `003_indexes.sql`, `999_rollback.sql`.

**This means all five BP-PUMP workflows — not just the three this MWO implements — are structurally incompatible with the canonical schema, not merely unfinished.** They target a table that has no canonical status.

**Create and Detail:** already real, credentialed, and targeting canonical `ltsa_pumps` — `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-REGISTRY-001.json` and `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-PUMP-DETAIL-001.json` respectively. Per MWO-P-004's approved Out of Scope section, neither file — nor their `BP-PUMP` stub counterparts — may be touched by this MWO. The map below records the deprecated counterpart for completeness only; **no action is taken on it in this MWO.**

**List, Update, Delete:** no canonical implementation exists yet for any of the three. `MODULES/PUMP/WORKFLOWS/` is the only existing location for real, canonical-schema-aligned Pump logic (it already holds Create), so it is designated as the target location for the three new canonical files — not a new location, not a new pattern. The corresponding `BP-PUMP` stub for each is designated deprecated.

**Canonical database object:** `ltsa_pumps` (`MODULES/PUMP/DATABASE/001_create_pumps.sql`, mirrored in `DATABASE/CANONICAL_SCHEMA.sql`) — already canonicalized and locked by IR-001 (MWO-P-002). This work package confirms and inherits that decision; it is not re-derived or re-opened.

**Canonical API (identification only — no file modified by this or any other work package in this MWO):** `MODULES/PUMP/API/openapi.yaml` is the only Pump API specification with real, schema-correct field definitions (`Pump` schema matches `ltsa_pumps` columns exactly). `BUILD-PACKS/BP-PUMP/SCHEMAS/pump.openapi.json` is an empty generic stub (`{"PUMP": {"type": "object"}}`) with no real field information — deprecated-adjacent by the same reasoning as its workflows. Per MWO-P-004's approved constraints, this identification is recorded for reference only; updating or extending any API specification is deferred to a dedicated future API Freeze MWO and is not actioned here.

---

## Pump Registry Canonical Map

| Operation | Canonical | Deprecated | Status |
|---|---|---|---|
| Create | `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-REGISTRY-001.json` | `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-CREATE-001.json` | Already complete — **not touched by this MWO, including its deprecated counterpart** |
| Detail | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-PUMP-DETAIL-001.json` | `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-DETAIL-001.json` | Already complete — **not touched by this MWO, including its deprecated counterpart** |
| List | `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-LIST-001.json` *(new — does not exist yet)* | `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-LIST-001.json` | Incomplete — WP-001 |
| Update | `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-UPDATE-001.json` *(new — does not exist yet)* | `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-UPDATE-001.json` | Incomplete — WP-002 |
| Delete | `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-DELETE-001.json` *(new — does not exist yet)* | `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-DELETE-001.json` | Incomplete — WP-003 |

**This map is now locked for the remainder of MWO-P-004**, per the Canonical Mapping Lock in the MWO's Constraints. WP-001–WP-003 implement into the canonical column only, for List/Update/Delete only.

---

## Known Gap Outside This MWO's Authority (documented, not actioned)

`BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-CREATE-001.json` and `WF-LTSA-BRAIN-PUMP-DETAIL-001.json` remain entirely unmarked — no `DEPRECATED` comment header (they are JSON, which has no comment syntax, same as the Customer BP-007 files before MWO-P-003) and no additive `_deprecated` metadata field, unlike their `DATABASE/*.sql` counterparts which IR-001 already marked. This is because MWO-P-002 only touched `BP-PUMP/DATABASE/*.sql`, not `BP-PUMP/WORKFLOWS/*.json`, and MWO-P-004's approved scope explicitly excludes touching any Create/Detail file, deprecated counterpart included. **Recommendation only, per the Engineering Execution Protocol's "document unrelated problems, do not fix them" rule: a future MWO should mark these two files the same way WP-001–WP-003 will mark their List/Update/Delete counterparts, for consistency.** Not actioned here.

---

## Summary

| Item | Result |
|---|---|
| Every Pump Registry workflow artifact identified | PASS — 7 workflow files (1 `MODULES/PUMP`, 1 `BP-007` OUTPUTS, 5 `BP-PUMP`), plus API/schema/doc artifacts |
| BP-PUMP compared against canonical schema for every operation | PASS — confirmed via direct read of each file's `settings.registry` block |
| Canonical implementation determined for every operation | PASS |
| Deprecated implementation determined for every operation | PASS (Create/Detail's noted for completeness, not actioned; List/Update/Delete's to be marked in WP-001–WP-003) |
| Canonical database object confirmed | PASS — inherits IR-001's `ltsa_pumps` designation, not re-derived |
| Canonical API identified | PASS (identification only — `MODULES/PUMP/API/openapi.yaml`; no file modified, per MWO-P-004 constraint) |
| Canonical Map produced and locked | PASS — see table above, mirrored into `MWO-P-004-Pump-Registry-Functional-Completion.md` |
| Exactly one canonical implementation per operation | PASS |
| Duplicate implementation left active | No — none activated; marking of List/Update/Delete's deprecated files deferred to WP-001–WP-003 (same sequencing precedent as `CR-000`); Create/Detail's deprecated files intentionally left unmarked, out of this MWO's authorized scope |

**Structural Validation only.** No live n8n execution, no database connection, no test — none were in scope for this work package.

No workflow file was created or modified by this work package. This is identification and confirmation only, per WP-000's Deliverables ("to be formally confirmed by WP-000 execution — not implementation").
