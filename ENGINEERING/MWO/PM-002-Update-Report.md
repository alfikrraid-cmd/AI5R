# PM-002 — Pump Update Implementation Report

Parent: MWO-P-004 — Pump Registry Functional Completion (WP-002)
Canonical file (per `PM-000-Canonicalization-Report.md`, locked): `PRODUCTS/LTSA-BRAIN/MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-UPDATE-001.json`
Deprecated file: `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-UPDATE-001.json`

---

## Implementation

New canonical file created at `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-UPDATE-001.json`:

`PUT /ltsa/pump/update` → `Validate Update Input` (code: requires `tag_number` as the identifier; accepts any subset of the 10 remaining editable columns — `area, location, pump_type, api_plan, seal_type, status, manufacturer, model, drawing_ref, notes`; throws if `tag_number` is missing or no updatable field is present) → `Build Update Statement` (code: constructs a parameterized `UPDATE ltsa_pumps SET col = $1, ... WHERE tag_number = $N RETURNING *` statement and a matching ordered `params` array, from only the fields actually supplied — a partial update) → `Update Pump` (`executeQuery` with the built query/params passed through via expressions) → `Check Update Result` (code: `$input.first()`-safe, 404 if zero rows affected) → `Respond Update`.

This is a direct reuse of MWO-P-003 WP-004's Customer Update pattern, with one deliberate, evidence-based adaptation: **the identifier is `tag_number`, not a surrogate `id`.** `tag_number` is excluded from the updatable-fields list (it is the lookup key, not an editable attribute), matching the same logic Customer Update used to exclude `id`. Rationale for using `tag_number` specifically: `MODULES/PUMP/DOCS/PUMP_REGISTRY_SPEC.md` and every other real Pump workflow already key on `tag_number` — Create's validation requires it, Detail's `SELECT` looks up by it — using `id` here would be inconsistent with the module's own established convention, not with Customer's.

The webhook path (`ltsa/pump/update`) and HTTP method (`PUT`) are unchanged from the deprecated `BP-PUMP` stub, per the Protocol's "never change public contracts."

**Credential and parameterization:** `hzgFaX04t1nL01vF` / `"Postgres account"`; genuine `$1..$N` positional placeholders bound via `queryReplacement` (the corrected pattern from MWO-P-003, not the vestigial `{{ }}`-interpolation-plus-`queryReplacement` combination found in the original `WF-LTSA-PUMP-DETAIL-001.json`). No new node type, no new pattern.

**Deprecation marking:** `BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-UPDATE-001.json` now carries additive `_deprecated`, `_deprecatedReason`, `_canonicalReplacement` metadata, identical convention to WP-001's List marking. No node, connection, or existing field in that file was modified or removed.

**Not touched, per approved scope:** List (WP-001's output, already approved — not re-opened), Create, Detail, and their `BP-PUMP` counterparts. `MODULES/PUMP/API/openapi.yaml` and every other API specification file.

---

## Evidence Used

- `PM-000-Canonicalization-Report.md` — locked canonical/deprecated file pair for Update.
- `PRODUCTS/LTSA-BRAIN/MODULES/PUMP/DATABASE/001_create_pumps.sql` — read directly to derive the exact 10-column updatable-field list (all `ltsa_pumps` columns except `id`, `tag_number`, `created_at`, `updated_at`) and to confirm `tag_number` carries the schema's `NOT NULL UNIQUE` constraint, making it a safe, stable lookup key.
- `PRODUCTS/LTSA-BRAIN/MODULES/PUMP/DOCS/PUMP_REGISTRY_SPEC.md` — read directly to confirm `tag_number` and `area` are the module's own stated required identifiers, supporting the choice of `tag_number` as the Update identifier.
- `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-UPDATE-001.json` — read directly (pre- and post-marking) to preserve its exact webhook path/method and to confirm, per `PM-000`, that its `settings.registry` block targets the deprecated `pump_registry`/`pump_code` schema.
- `ENGINEERING/MWO/CR-004-Update-Report.md` (MWO-P-003) — the Customer Update pattern this work package reuses node-for-node, including the mid-MWO-P-003 query-parameterization correction, applied here from the start rather than re-discovered.
- `ENGINEERING/MWO/MWO-P-004-Pump-Registry-Functional-Completion.md` — WP-002's approved Scope/Deliverables/Acceptance Criteria/Known Risks, followed exactly.

---

## Structural Validation

| Check | Result |
|---|---|
| JSON validation — canonical file | PASS |
| JSON validation — deprecated file, post-marking | PASS |
| Node graph validation | PASS — 6 nodes, fully connected (verified programmatically: every node is a connection source or target), exactly one terminal node (`Respond Update`), a `respondToWebhook` node |
| Canonical validation | PASS — implemented into the exact file `PM-000`'s locked map designates canonical for Update, and no other |
| Static review — updatable-field list vs. schema | PASS — the 10 fields in `Validate Update Input` (`area, location, pump_type, api_plan, seal_type, status, manufacturer, model, drawing_ref, notes`) match `001_create_pumps.sql`'s column list exactly, excluding `id`/`tag_number`/`created_at`/`updated_at` |
| Static review — parameter ordering | PASS — `Build Update Statement`'s `params` array order (`keys.map(...)` then `tag_number` appended last) matches the `$1..$N` placeholder order the same function generates in the query string; the final placeholder used in `WHERE tag_number = $${params.length}` is confirmed to always resolve to the last (tag_number) element |
| Scope check | PASS — `git status` confirms exactly 2 files touched this work package (1 new, 1 modified); List, Create, Detail, and their counterparts unchanged since WP-001's approval |

## Runtime Verification

**Out of scope for this work package**, per the approved MWO-P-004 constraints. No live n8n execution, no PostgreSQL connection. Unlike WP-001 (no user-supplied field list), Update's dynamic query-building logic is exactly the class of code where MWO-P-003 previously found a latent defect only through careful static reading — that same standard of review was applied here (see Static Review rows above), but it is not a substitute for actual execution, which remains unperformed and unclaimed.

---

## PASS / WARNING / BLOCKER

**PASS** (Structural Validation, this work package's entire scope). No BLOCKER. No WARNING.

## Known Limitations

- **No Runtime Verification performed** — deliberate, approved scope boundary, not an oversight.
- **The `tag_number`-as-identifier design decision has not been executed against a real database**, so the dynamically-built `UPDATE` statement's correctness rests entirely on static review (confirmed above), the same class of risk flagged in advance in `MWO-P-004`'s WP-002 Known Risks.
- **No conflict handling exists for the case where an update would violate a uniqueness or NOT NULL constraint on a field other than the identifier** (`ltsa_pumps` has no other unique constraints today besides `tag_number`, which is excluded from the updatable set, so this risk is currently theoretical, not active — noted for completeness, not as a defect).
- Same pre-existing, out-of-scope gap as `PM-000`/`PM-001`: `BP-PUMP`'s Create and Detail stubs remain unmarked; unchanged by this work package.

---

Stopping here as instructed. WP-003 (Delete) has not been anticipated, started, or prepared. Nothing was committed or pushed.
