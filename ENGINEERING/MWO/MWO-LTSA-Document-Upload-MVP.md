Status: IMPLEMENTED — awaiting Chief Architect review, Engineering Audit, and separate Commit/Push Approval
Type: Manufacturing Work Order (Feature — Implementation Mode)
Product: LTSA-BRAIN
Role: Implementation Engineer
Architecture: FROZEN — no new architectural pattern introduced beyond explicit Chief Architect rulings recorded below
Basis: Chief Architect directive (chat), issued directly as an MWO with an inline Requirements/UI/Processing Flow/Minimum Fields/Review Screen/Save/Architecture/Deliverables/Definition of Done specification
Scope: Engineering Document Upload pipeline (Upload → OCR → AI Field Extraction → Review → Save) for LTSA-BRAIN

---

## 1. Objective (as given)

Implement the first production-ready MVP of the LTSA-BRAIN Engineering
Document Upload pipeline: a maintenance engineer uploads a PDF/JPG/JPEG/PNG
engineering document, the system extracts structured fields via OCR + AI,
the engineer reviews and edits the extracted values, and on Save the
document is indexed and linked to the appropriate Pump/Seal registry
records when matches exist.

## 2. Research (WP-000, scoped to LTSA-BRAIN + canonical platform specs)

Before implementation, a scoped reuse inventory was performed against
`PRODUCTS/LTSA-BRAIN/` (not the whole repository, per explicit instruction).
Findings:

- **No OCR or AI field-extraction capability existed anywhere in the
  repository.** `CANONICAL_SCHEMA.sql` explicitly disclaims it in 7+ places
  ("No OCR, text/table/image extraction, AI, or knowledge extraction is
  performed here").
- **No REST/FastAPI backend existed in LTSA-BRAIN** — every module is an
  n8n workflow + embedded-SQL Postgres node.
- **No frontend existed in `PRODUCTS/LTSA-BRAIN`** (two empty `.tsx` stub
  files). `AI5R-STUDIO/osa-web` (Vite + React 19) is the only real,
  installed frontend in the platform.
- **No blob-storage convention existed** — `file_reference`/`file_name`/
  `file_hash` on existing acquisition tables are pointer/metadata columns
  by explicit design, never a storage backend.
- **Reusable as-is:** `knowledge_source_registry`, `pdf_document`,
  `engineering_media` (upload provenance + acquisition-object records);
  `PumpIdentityResolver`/`SealIdentityResolver` (registry matching); the
  Factory Pack shape (identity resolver / relationship resolver /
  manufacturing station), though not directly applicable here since this
  feature adds an extraction record, not a new canonical business object.

This MWO's own extraction step directly fulfils the roadmap item both
`BUILD-PACKS/BP-PDF-DOCUMENT` and `BUILD-PACKS/BP-ENGINEERING-MEDIA` named
as explicitly deferred ("extraction of any kind is deferred to future
MWOs").

## 3. Architecture Decisions (explicit Chief Architect rulings)

Given multiple genuine architectural gaps (no OCR/extraction capability, no
REST backend, no frontend, no storage convention), these were STOPped and
reported per the Constitution's Canonical Rule rather than decided
unilaterally. Chief Architect rulings, verbatim intent:

1. **Backend mechanism:** implement as an n8n workflow, using existing
   Postgres/HTTP/Code nodes — "Architecture consistency takes priority over
   introducing a second runtime." No new Python/FastAPI backend introduced.
2. **OCR + AI Field Extraction:** Claude API (vision/document input,
   structured output) as the **initial provider only** — "Claude is the
   first provider, not the architecture." A reusable `ExtractionProvider`
   interface isolates all Anthropic-SDK-specific code so a future provider
   requires no LTSA workflow change.
3. **Frontend:** reuse `AI5R-STUDIO/osa-web` as a presentation-only client.
   "No engineering rules, OCR, extraction, registry logic, or business
   processing may reside inside Studio." No second frontend app was
   created.
4. **Storage:** original-file (binary) persistence is **explicitly out of
   scope**, deferred to a future Platform Storage MWO. Temporary local
   files during processing are acceptable; no new top-level `DATA/`,
   `STORAGE/`, or other repository storage convention was introduced from
   within LTSA scope. Only OCR text and structured JSON are persisted.

## 4. What Was Built

- **`BUILD-PACKS/BP-DOCUMENT-EXTRACTION`** — new table
  `document_field_extraction` (additive to `CANONICAL_SCHEMA.sql`).
  Polymorphic `(source_document_id, source_document_type)` reference to
  `pdf_document`/`engineering_media` (same pattern as `work_order`'s
  `(asset_code, asset_type)`). JSONB `extracted_fields`/`reviewed_fields`
  (the Minimum Fields set is document-type-dependent, unlike every
  fixed-shape business object elsewhere in this schema).
  `extraction_provider` records which provider ran. `pump_tag_number`/
  `seal_code` are nullable, populated only at Save.
- **`PRODUCTS/LTSA-BRAIN/AI-EXTRACTION`** — the AI Extraction Capability:
  `extraction_provider.py` (interface), `claude_extraction_provider.py`
  (first provider — `claude-opus-4-8`, `output_config.format` structured
  JSON schema covering document-type detection + OCR text + all 20 Minimum
  Fields in one call), `models.py` (normalized `ExtractionResult`),
  `cli.py` (the sole n8n integration boundary), `resolve_identity_cli.py`
  (reuses `PumpIdentityResolver`/`SealIdentityResolver` unmodified).
- **`WF-LTSA-DOCUMENT-UPLOAD-001.json`** / **`WF-LTSA-DOCUMENT-SAVE-001.json`**
  (n8n) — Upload registers provenance/acquisition rows, writes the upload
  to an OS-temp path (discarded after the request — not a repository
  convention), invokes the AI Extraction Capability, inserts the
  extraction row. Save updates `reviewed_fields`, resolves pump/seal
  matches via the identity-resolver CLI wrapper, finalizes `status=SAVED`.
- **`AI5R-STUDIO/osa-web`** — `DocumentUpload.jsx` (drag & drop, file
  picker, progress bar) and `DocumentReview.jsx` (editable fields,
  low-confidence highlighting, Save), wired into `App.jsx` additively
  (existing Blueprint demo untouched).

## 5. Out of Scope (explicitly, per Chief Architect ruling)

- Physical storage of the original uploaded document (deferred to a future
  Platform Storage MWO).
- Any new top-level repository storage directory.
- Any change to the existing n8n/Postgres architecture pattern.

See `MWO-LTSA-Document-Upload-MVP-Completion-Report.md` for validation
results, PASS/WARNING/BLOCKER status, and known limitations.
