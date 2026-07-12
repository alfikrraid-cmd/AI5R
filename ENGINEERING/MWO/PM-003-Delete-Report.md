# PM-003 — Pump Delete Implementation Report

Parent: MWO-P-004 — Pump Registry Functional Completion (WP-003)
Canonical file (per `PM-000-Canonicalization-Report.md`, locked): `PRODUCTS/LTSA-BRAIN/MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-DELETE-001.json`
Deprecated file: `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-DELETE-001.json`

---

## Implementation

New canonical file created at `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-DELETE-001.json`:

`DELETE /ltsa/pump/delete` → `Parse Pump Tag Number` (reads `$json.query?.tag_number`) → `IF Valid Tag Number` → **false:** `Respond 400` / **true:** `Delete Pump` (parameterized `DELETE FROM ltsa_pumps WHERE tag_number = $1 RETURNING *`) → `Check Delete Result` (`$input.first()`-safe; 404 if zero rows) → `Respond Delete`.

The webhook path (`ltsa/pump/delete`) and HTTP method (`DELETE`) are unchanged from the deprecated `BP-PUMP` stub, per the Protocol's "never change public contracts."

**Credential and parameterization:** `hzgFaX04t1nL01vF` / `"Postgres account"`; genuine `$1` positional placeholder bound via `queryReplacement`, the corrected pattern from MWO-P-003.

**Deprecation marking:** `BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-DELETE-001.json` now carries additive `_deprecated`, `_deprecatedReason`, `_canonicalReplacement` metadata, identical convention to WP-001/WP-002's marking. No node, connection, or existing field in that file was modified or removed.

**Not touched, per approved scope:** List, Update (WP-001/WP-002's output, already approved — not re-opened), Create, Detail, and their `BP-PUMP` counterparts. `MODULES/PUMP/API/openapi.yaml` and every other API specification file.

---

## Pattern Source

Structurally identical to **MWO-P-003 WP-005 — Customer Delete** (`CR-005-Delete-Report.md` / `WF-LTSA-CUSTOMER-DELETE-001.json`): same node sequence (`Parse ID → IF Valid → [400 / Delete → Check Result → Respond]`), same zero-row-safe check, same 400/404 response shape. Two adaptations, both required by repository evidence rather than by preference:

1. **Identifier is `tag_number`, not a surrogate `id`.** This continues WP-002's already-approved rationale (`PM-002`): every real Pump workflow — Create's validation, Detail's lookup, and now Update — keys on `tag_number`, so Delete follows the same module-internal convention rather than Customer Registry's `id`-based one.
2. **Identifier is read from a `tag_number` query parameter, not `id`.** This mirrors `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-PUMP-DETAIL-001.json`'s real, already-functioning parsing logic (`const tag_number = $json.query?.tag_number;`) directly — the closest and only real precedent for how a Pump identifier is actually passed as a request parameter in this product.

No new node type, no new response envelope, no new validation style was introduced. Where Customer Registry's Delete pattern and Pump's own established conventions agreed, Customer's pattern was followed exactly (per Chief Architect's instruction to use the validated Customer Registry pattern where applicable, and adapt only where evidence requires it).

---

## Evidence Used

- `PM-000-Canonicalization-Report.md` — locked canonical/deprecated file pair for Delete.
- `PM-002-Update-Report.md` — established and already-approved `tag_number`-as-identifier rationale, reused here rather than re-derived from scratch.
- `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-PUMP-DETAIL-001.json` — read directly to confirm the real, existing `tag_number` query-parameter parsing convention this work package's `Parse Pump Tag Number` node mirrors.
- `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-DELETE-001.json` — read directly (pre- and post-marking) to preserve its exact webhook path/method and confirm, per `PM-000`, that it targets the deprecated `pump_registry`/`pump_code` schema.
- `ENGINEERING/MWO/CR-005-Delete-Report.md` (MWO-P-003) — the Customer Delete pattern this work package reuses structurally.
- `PRODUCTS/LTSA-BRAIN/MODULES/PUMP/DOCS/PUMP_REGISTRY_SPEC.md` — confirms `tag_number` as the module's stated identifying field.
- `ENGINEERING/MWO/MWO-P-004-Pump-Registry-Functional-Completion.md` — WP-003's approved Scope/Deliverables/Acceptance Criteria/Known Risks, followed exactly.

---

## Structural Validation

| Check | Result |
|---|---|
| JSON validation — canonical file | PASS |
| JSON validation — deprecated file, post-marking | PASS |
| Node graph validation | PASS — 7 nodes, fully connected (verified programmatically: every node is a connection source or target); two terminal nodes (`Respond 400`, `Respond Delete`), both `respondToWebhook` nodes — both branches of `IF Valid Tag Number` correctly terminate in a response, no dead branch |
| Canonical validation | PASS — implemented into the exact file `PM-000`'s locked map designates canonical for Delete, and no other |
| Static review — query correctness | PASS — `DELETE FROM ltsa_pumps WHERE tag_number = $1 RETURNING *` targets the canonical table and its confirmed `NOT NULL UNIQUE` column; by construction, at most one row can ever be affected |
| Scope check | PASS — `git status` confirms exactly 2 files touched this work package (1 new, 1 modified); List, Update, Create, and Detail unchanged since their respective approvals |

## Runtime Verification

**Out of scope for this work package**, per the approved MWO-P-004 constraints. No live n8n execution, no PostgreSQL connection. Delete's logic is the least structurally complex of the three operations in this MWO (no dynamic query construction, unlike Update), which somewhat lowers the residual risk of an undetected static-review gap — but this is not a substitute for execution, which remains unperformed and unclaimed.

---

## PASS / WARNING / BLOCKER

**PASS** (Structural Validation, this work package's entire scope). No BLOCKER. No WARNING.

## Known Limitations

- **No Runtime Verification performed** — deliberate, approved scope boundary, not an oversight.
- **No referential-integrity concern was found, but the underlying reason is an absence of consumers, not a checked-and-cleared dependency**: `PUMP_REGISTRY_SPEC.md` lists Seal Registry, PM Planner, CM Work Order, Inspection History, and Billing Report as consumers of Pump data, none of which exist as real artifacts anywhere in this product (per `MWO-P-001`). If any of those modules are built in the future, Pump Delete's lack of any cascade/restrict behavior should be re-examined at that time — noted here so it is not silently forgotten, per `MWO-P-004` WP-003's own pre-identified Known Risk.
- Same pre-existing, out-of-scope gap as `PM-000`/`PM-001`/`PM-002`: `BP-PUMP`'s Create and Detail stubs remain unmarked; unchanged by this work package.

---

This completes all three implementation work packages (WP-001, WP-002, WP-003) approved under MWO-P-004. Stopping here as instructed — no summary/aggregate report has been produced, and none is anticipated, without explicit Chief Architect instruction to do so. Nothing was committed or pushed.
