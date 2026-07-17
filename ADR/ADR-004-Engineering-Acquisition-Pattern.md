# ADR-004 — Engineering Acquisition Pattern

## Status

Approved

---

## Context

MWO-LTSA-040C (Universal Tabular Data Acquisition), MWO-LTSA-040D (Engineering PDF Acquisition), and the pending MWO-LTSA-040E (Engineering Media Acquisition) each manufacture a distinct Acquisition Object type inside `PRODUCTS/LTSA-BRAIN`. Until now, no document stated whether these three (and any future Acquisition Object) must share one structural pattern, or whether each is free to shape its own pipeline independently — 040C and 040D were each designed from their own original work order's text in isolation (per MWO-LTSA-040D's own WP-000, which treated "Reuse Engineering Document Registry" as pattern-reuse, not literal-table-reuse, without a governing cross-cutting rule to check against). The Chief Architect has now stated the general pattern explicitly and approved it. Per ADR-000 §2, that decision is recorded here, not left inline in an MWO or inferred from source code.

---

## 1. Current Repository Architecture (Descriptive)

This section states only what exists today, as evidence. It contains no "should," no target, no recommendation.

- **PDF (MWO-LTSA-040D)** fully matches the four-stage shape: `pdf_document` (Acquisition Object) → `pdf_metadata` (Metadata, 1:1, `UNIQUE` on `pdf_document_id`) → `document_classification` (Classification, repeatable, no uniqueness constraint) → `pdf_acquisition_job` (Acquisition Job, FK to both `knowledge_source_registry` and `pdf_document`).
- **Workbook (MWO-LTSA-040C)** does **not** match this shape. It manufactures `workbook` (Acquisition Object), `worksheet` and `worksheet_table` (structural children, not a Metadata/Classification pair), `mapping_profile` and `column_mapping` (a separate, reusable mapping-configuration concept with no PDF-side analogue), and `acquisition_job` — a table shared between `workbook_id` and `mapping_profile_id`, not a dedicated "Workbook Acquisition Job" scoped to `workbook` alone. There is no `workbook_metadata` or `workbook_classification` table anywhere in `DATABASE/CANONICAL_SCHEMA.sql`.
- **Engineering Media (MWO-LTSA-040E)** has no schema representation yet — an MWO document exists (`ENGINEERING/MWO/MWO-LTSA-040E-Engineering-Media-Acquisition.md`) but, per repository convention, this ADR does not read its unapproved contents as authority for anything.

Nothing above is altered by this ADR.

---

## 2. Target Architecture (Normative)

Every Acquisition Object manufactured under the Engineering Knowledge Acquisition epic must follow the same four-stage pattern, stated verbatim from the Chief Architect's approved decision:

```
Acquisition Object
    ↓
Metadata
    ↓
Classification
    ↓
Acquisition Job
```

Named instances, as approved:

| Acquisition Object | Metadata | Classification | Acquisition Job |
|---|---|---|---|
| Workbook | Workbook Metadata | Workbook Classification | Workbook Acquisition Job |
| PDF | PDF Metadata | Document Classification | PDF Acquisition Job |
| Engineering Media | Media Metadata | Media Classification | Media Acquisition Job |

This is a structural pattern, not a naming coincidence: for every Acquisition Object type —
1. The **Acquisition Object** table registers the source's identity, never its content (immutable, Create/List/Detail only, no OCR/parsing/extraction performed by its own build pack).
2. The **Metadata** table records the source's own container-level properties, one row per Acquisition Object (immutable, Create/List/Detail only).
3. The **Classification** table records a repeatable classification attempt against the Acquisition Object — multiple rows per object are expected and are not an error (Create/List/Detail only, no Update).
4. The **Acquisition Job** table is a dedicated job-log scoped to that Acquisition Object type (and, where applicable, its Knowledge Source), Create/List/Detail/Update, no Delete.

Future Acquisition Objects (Engineering Media and beyond) must be manufactured against this same four-stage shape from their first implementation, not retrofitted after the fact.

---

## 3. Migration Strategy (Step-by-Step Evolution)

- **PDF requires no migration.** MWO-LTSA-040D already conforms.
- **Engineering Media (MWO-LTSA-040E)** must be designed against this pattern from WP-000 onward: `engineering_media` (Acquisition Object), `media_metadata`, `media_classification`, `media_acquisition_job` (dedicated, not shared).
- **Workbook (MWO-LTSA-040C) is non-conforming** and requires a future retrofit MWO to: (a) add `workbook_metadata` (1:1 with `workbook`) and `workbook_classification` (repeatable), mirroring `pdf_metadata`/`document_classification`; and (b) resolve `acquisition_job`'s dual-FK shape (`workbook_id` + `mapping_profile_id`) against the now-normative "dedicated Acquisition Job per Acquisition Object type" rule — a design question this ADR does not resolve unilaterally, since `mapping_profile` has no analogue in PDF or (so far) Engineering Media, and the retrofit MWO's own WP-000 must decide it with evidence, not this ADR by inference. This ADR authorizes no source-code change itself, per ADR-000 §2 ("An ADR describes target and/or current-state architecture; it does not itself change source code") — the retrofit is deferred to its own future MWO.

---

## Consequences

### Positive
- Every future Acquisition Object MWO now has a single, explicit structural contract to design against, instead of re-deriving one from whichever prior MWO's text it happens to read first.
- Makes the Workbook/PDF divergence a named, tracked discrepancy rather than an implicit inconsistency future engineers would have to rediscover from source code.

### Negative
- Declares `workbook`'s current schema non-conforming to an architecture approved after it was built — a real gap that persists until a retrofit MWO is authorized and executed. Until then, Workbook remains functionally complete under MWO-LTSA-040C's own (still valid) Definition of Done; it is only non-conforming to this newer, broader pattern.
- `mapping_profile`/`column_mapping` have no named place in the four-stage pattern as stated; a future retrofit MWO must decide whether they remain Workbook-specific additions alongside the four generic stages, or whether the pattern itself needs a documented per-object-type extension point. This ADR does not resolve that question.

## Alternatives Considered

- **Leave each Acquisition Object free to define its own pipeline shape**, as 040C and 040D each did independently. Rejected per Chief Architect's explicit instruction — this was the exact ambiguity the ADR was requested to close, and its cost (Workbook and PDF converging on different shapes for the same kind of thing) was already visible before Engineering Media was designed.
- **Silently retrofit Workbook as part of this ADR.** Rejected — an ADR does not itself change source code (ADR-000 §2); a retrofit is implementation work requiring its own MWO, Work Package Lifecycle, and separate approval.

## Future Impact

This ADR becomes the canonical reference for MWO-LTSA-040E and every future Acquisition Object MWO in `PRODUCTS/LTSA-BRAIN`. A future retrofit MWO for `workbook` is required to bring it into conformance; until authorized, Workbook's divergence from this pattern is a stated, tracked fact, not a silent inconsistency.

## Supersedes

None.
