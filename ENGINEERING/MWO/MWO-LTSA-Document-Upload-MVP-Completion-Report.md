Status: COMPLETE (Implementation) — awaiting Chief Architect Engineering Audit and separate Commit/Push Approval
MWO: `MWO-LTSA-Document-Upload-MVP.md`

---

## Executive Summary

Implemented the Upload → OCR → AI Field Extraction → Review → Save pipeline
for LTSA-BRAIN engineering documents, per explicit Chief Architect
architecture rulings issued during this session (n8n-only backend, Claude
as first-and-isolated extraction provider, Studio as presentation-only
client, original-file storage explicitly deferred). One new database table,
one new reusable Python capability module, two new n8n workflows, two new
React components, and full documentation-contract updates. 11/11 unit
tests green. No commit was made — implementation only, per Golden Rules
(commit/push require separate explicit approval).

## Files Modified / Created

**New:**
- `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-DOCUMENT-EXTRACTION/` (DATABASE, SCHEMAS, WORKFLOWS, TEST, README.md)
- `PRODUCTS/LTSA-BRAIN/AI-EXTRACTION/` (extraction_provider.py, claude_extraction_provider.py, models.py, cli.py, resolve_identity_cli.py, requirements.txt, README.md, TEST/*)
- `AI5R-STUDIO/osa-web/src/components/DocumentUpload.jsx`
- `AI5R-STUDIO/osa-web/src/components/DocumentReview.jsx`
- `ENGINEERING/MWO/MWO-LTSA-Document-Upload-MVP.md`, this report

**Modified (additive only):**
- `PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql` — added `document_field_extraction` table + indexes
- `PRODUCTS/LTSA-BRAIN/product.manifest.json` — added `document_field_extraction` module entry
- `AI5R-STUDIO/osa-web/src/App.jsx`, `src/style.css` — wired in new components, existing Blueprint demo untouched
- `CHANGELOG.md`, `CURRENT_STATE.md`, `TECHNICAL_DEBT.md` — per Documentation Contract

## Validation Performed

| Check | Method | Result |
|---|---|---|
| Python unit tests (models, Claude provider, CLI, identity-resolver CLI wrapper) | `pytest PRODUCTS/LTSA-BRAIN/AI-EXTRACTION/TEST` | **PASS** — 11/11 green. Claude API fully mocked (`unittest.mock`); no live API key or network call used. |
| `document_field_extraction` DDL | Read against existing canonical schema conventions; JSON/SQL hand-reviewed for consistency with `pdf_document`/`work_order` patterns | **PASS** (structural) |
| n8n workflow JSON syntax | `json.load()` on both workflow files | **PASS** — both parse as valid JSON |
| `document_field_extraction.schema.json` | `json.load()` | **PASS** |
| `product.manifest.json` | `json.load()` after edits | **PASS** |
| Identity-resolver reuse (`resolve_identity_cli.py` against real `PumpIdentityResolver`/`SealIdentityResolver`) | Subprocess-invoked in `test_resolve_identity_cli.py` against the actual, unmodified resolver classes | **PASS** — confirms the sys.path workaround for TD-010 is effective |
| n8n workflow execution against a live n8n instance | Not performed | **WARNING (disclosed)** — no credentialed n8n/Postgres instance available in this session, the same standing condition disclosed for every other n8n/Postgres module in this product (per `product.manifest.json`'s existing entries) |
| `document_field_extraction` DDL applied to a live Postgres instance | Not performed | **WARNING (disclosed)** — same standing condition |
| `osa-web` frontend build (`npm run build`) | Attempted, failed at the `vite`/`rolldown` native-binding load step | **WARNING (disclosed, pre-existing, unrelated to this MWO)** — `node_modules` in this checkout contain Linux-only native bindings (`@rolldown/binding-linux-x64-gnu`, `lightningcss-linux-x64-gnu`) and cannot run on this Windows machine; confirmed the failure occurs before any of my files are touched (bare `vite --version`-level invocation fails identically). JSX was manually re-read for syntactic correctness instead. |
| Claude API call shape (model, structured-output schema, document/image content block selection) | Verified against `claude-api` skill reference documentation, not live-called | **PASS** (structural — matches documented API shape for `output_config.format` + document/image content blocks on `claude-opus-4-8`) |

**No BLOCKER-level findings.** All WARNING items are disclosed environment
limitations, not defects in the delivered code, and match the pattern
already disclosed for every other n8n/Postgres module in this product.

## Known Limitations / Disclosed Findings

1. **Runtime verification blocked** — no credentialed n8n or Postgres
   instance available in this session. Structural validation only.
2. **`osa-web` build verification blocked** — pre-existing Linux-only
   native bindings in this Windows checkout's `node_modules`; unrelated to
   this MWO's changes.
3. **TD-010 (new, disclosed in `TECHNICAL_DEBT.md`)** — `pump_identity_resolver.py`/
   `seal_identity_resolver.py` each compute an incorrect `AI5R-SDK` path
   (`parents[2]` instead of `parents[3]`), a pre-existing latent bug found
   while integrating them. Not fixed (out of scope for this MWO); worked
   around in the new `resolve_identity_cli.py` by inserting the correct
   path before import, without modifying either resolver file.
4. **Seal identity matching is a heuristic, not an exact-field match** —
   the MVP's Minimum Fields set has no dedicated `seal_code` field (only
   `seal_type`, a free-text description); `WF-LTSA-DOCUMENT-SAVE-001`
   matches the reviewed `seal_type` value against `seal_registry.seal_code`
   OR `seal_registry.seal_name`. This is a reasonable MVP heuristic, not a
   guaranteed-correct match, and should be revisited if seal auto-linking
   accuracy becomes a concern.
5. **Claude extraction accuracy is unverified against a real scanned
   document** — the Claude API was not actually called (no live key used
   in this session); the request/response shape was validated structurally
   against the documented API contract and exercised in tests via mocks
   only.

## Architecture Impact

None beyond the four explicit Chief Architect rulings recorded in the MWO
document — no new runtime, no new backend framework, no new frontend app,
no new repository storage convention. The extraction capability's provider
interface is additive infrastructure, not a redesign of any existing
component.

## Production Impact

None — no code path in this MWO is wired into an active, running system;
all artifacts are net-new files plus additive schema/documentation changes.
Nothing was committed or pushed.

## Remaining Risks

- Original-file (binary) persistence is not implemented in this MVP by
  explicit Chief Architect design — a maintenance engineer cannot yet
  retrieve the original document after upload, only its OCR text and
  extracted fields. This is expected to be addressed by a future Platform
  Storage MWO.
- The n8n Execute Command / temp-file mechanics (writing the uploaded
  binary to `os.tmpdir()`, invoking the Python CLI, cleaning up afterward)
  depend on the target n8n instance permitting `fs`/`os`/`child_process`
  usage in Code nodes and having Python 3 + the `anthropic` package
  available on its host — an operational prerequisite, not verified here.

## Recommended Next MWO (analysis only, not implemented)

1. Platform Storage MWO — define the platform-wide runtime storage
   convention and wire `document_field_extraction`'s original-file
   persistence to it.
2. Runtime verification of both new n8n workflows once a credentialed
   n8n/Postgres instance is available.
3. Consider a dedicated seal-matching field (e.g. a caller/AI-supplied
   `seal_code` candidate) if seal auto-linking accuracy from free-text
   `seal_type` proves insufficient in practice.
