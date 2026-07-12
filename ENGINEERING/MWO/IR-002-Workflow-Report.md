# IR-002 — Workflow Verification Report

Parent: MWO-P-002 — LTSA Integrity Recovery
Branch: `feature/ltsa-brain` (local, tracking `origin/feature/ltsa-brain`)

**Audit-trail note:** This report does not rewrite `ENGINEERING/MWO/MWO-P-001-LTSA-Product-Audit.md`. Where evidence gathered here refines or corrects a finding recorded there, that finding is quoted and marked *"Superseded by evidence collected during IR-002"* or *"Clarified during implementation"* below. MWO-P-001 remains the unmodified historical record of what was found at audit time.

---

## Full Workflow Inventory

23 deployed/product workflow files were found (1 additional file, `TEMPLATES/WF-TEMPLATE-CRUD-V1.json`, is generator source material, not a deployed workflow, and is listed separately).

| # | Path | Size | Logic |
|---|---|---|---|
| 1–5 | `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-{CREATE,DELETE,GET,LIST,UPDATE}-001.json` | ~517–529 B | Stub: webhook trigger only, no downstream node |
| 6–11 | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-{BY-CODE,CREATE,DELETE,DETAIL,LIST,UPDATE}-001.json` | ~134–137 B | **Empty**: `"nodes": []`, `"connections": {}` — no trigger, no logic at all |
| 12 | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-PUMP-DETAIL-001.json` | 5525 B | **Real**: webhook → validate → `SELECT * FROM public.ltsa_pumps WHERE tag_number = ...` → 200/404 response. Real, non-placeholder credential (`hzgFaX04t1nL01vF`) |
| 13–17 | `BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-{CREATE,DELETE,DETAIL,LIST,UPDATE}-001.json` | ~2093–2105 B | Stub: webhook → hardcoded static JSON response (e.g. `{"success": true, ..., "table": "pump_registry"}`); no Postgres node |
| 18–22 | `BUILD-PACKS/BP-SEAL/WORKFLOWS/WF-LTSA-BRAIN-SEAL-{CREATE,DELETE,DETAIL,LIST,UPDATE}-001.json` | ~2119–2131 B | Stub: same static-response pattern as BP-PUMP; no Postgres node |
| 23 | `MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-REGISTRY-001.json` | 3321 B | **Real**: webhook → validate → `INSERT INTO ltsa_pumps (...) RETURNING *` → response. Placeholder credential (`REPLACE_WITH_POSTGRES_CREDENTIAL_ID`) — see `IR-003-Credential-Report.md` |
| — | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/TEMPLATES/WF-TEMPLATE-CRUD-V1.json` (not a deployed workflow) | 5494 B | Template source for a customer-detail workflow; carries the same real credential (`hzgFaX04t1nL01vF`) that `compile_detail_workflow.py` copied into item 12 |

**Functional summary:** of 23 workflow files, **1** is fully real and immediately executable as committed (item 12), **1** is real but blocked by a placeholder credential (item 23), **15** are non-functional static-response stubs (items 1–5, 13–22), and **6** are completely empty shells with no nodes at all (items 6–11).

---

## Correction to MWO-P-001 (Broken Feature B6)

MWO-P-001 recorded:

> "B6 — `BC-22-PRODUCTION-VERIFICATION.md` claims production verification of a workflow file (`WF-LTSA-PUMP-DETAIL-001`) that does not exist in the repository."

**Superseded by evidence collected during IR-002.** The file exists at `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-PUMP-DETAIL-001.json` (item 12 above) — it was missed in the original audit because it was not searched for outside `MODULES/PUMP/WORKFLOWS/` and `BUILD-PACKS/BP-PUMP/WORKFLOWS/`. On inspection, this file contains real query logic against `public.ltsa_pumps` keyed on `tag_number`, and a real (non-placeholder) PostgreSQL credential — consistent with, not contradicting, `BC-22`'s claimed verified response shape (`tag_number`, `area`, `location`, `pump_type`, `status`). This audit cannot confirm from repository evidence alone that the external n8n instance actually returned that response in production (that remains an external, unverifiable claim), but the specific defect recorded as B6 — "the workflow file does not exist" — is incorrect and is withdrawn as stated. MWO-P-001 itself is left unmodified; this correction is recorded here per the audit-trail preservation instruction.

**Result: WARNING** (not BLOCKER) — the original finding was a research gap, not a product defect; the underlying workflow is in fact real and credentialed.

---

## Documentation ↔ Workflow Mapping

| Document | Claims | Workflow file(s) it maps to | Match? |
|---|---|---|---|
| `API/customer-registry/API_CONTRACT.md` | 5 customer operations (create/list/get/update/delete) | Items 1–5 (BP-005 stubs) | Files present; **not functional** (stub only) |
| `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/README.md` | Same 5 endpoints | Items 1–5 | Same as above |
| `TEST-REPORTS/FM-001.5-FACTORY-ACCEPTANCE-TEST.md` | Lists 5 exact `BP-PUMP/WORKFLOWS/*.json` paths as "generated" | Items 13–17 | Files present and match by path; report itself marks import/DB-verification steps as pending — consistent with stub reality |
| `TEST-REPORTS/FM-001.9-MANUFACTURING-ENGINE-TEST.md` | Lists the same 5 `WF-LTSA-BRAIN-PUMP-*` files + 4 SQL files as "generated" | Items 13–17 | Files present; report's claim is scoped to generation/validity, not function — consistent |
| `TEST-REPORTS/LT-004-FACTORY-REGRESSION-SUITE.md` | "Verified modules: PUMP, SEAL" | Items 13–22 | Files present for both modules; claim scoped to generation, consistent |
| `BUILD-PACKS/BP-SEAL/REPORTS/LT-003-SEAL-MANUFACTURING-REPORT.md` | "Factory generated... CRUD workflow files" for seal | Items 18–22 | Files present, consistent |
| `TEST-REPORTS/BC-22-PRODUCTION-VERIFICATION.md` | Verified `WF-LTSA-PUMP-DETAIL-001` in production | Item 12 | File present with matching real logic (see correction above) |
| `MODULES/PUMP/DOCS/PUMP_REGISTRY_SPEC.md` | Implies list/detail/update/delete access ("Used By: Seal Registry, PM Planner, ...") | Only item 23 (create) and item 12 (detail, in a different build pack) exist with real logic | **Partial** — list/update/delete have no real-logic counterpart anywhere in the product, only the non-functional BP-PUMP stubs (items 14–16) |

---

## Missing Workflows

No documented CRUD operation is missing a *file* entirely — every operation named in `API_CONTRACT.md`, `PUMP_REGISTRY_SPEC.md`, or the build-pack READMEs has at least one corresponding JSON file. What is missing is **real logic** behind most of them:

| Gap | Detail |
|---|---|
| Customer: list/get/update/delete/create | No version anywhere with real query logic; only stubs (items 1–5) and empty shells (items 6–10) exist |
| Pump: list/update/delete | Only the non-functional `BP-PUMP` stub versions exist (items 14, 16, 17); no real-logic counterpart |
| Seal: create/list/get/update/delete | No version anywhere with real query logic; only stubs (items 18–22) exist |

**Result: WARNING** — files exist for every documented operation (acceptance criterion "every documented workflow maps to a real workflow file" is met at the *file* level); real-logic completeness is a functional gap already tracked in `MWO-P-001-LTSA-Product-Audit.md`'s backlog (items 006, 007, 010) and is out of IR-002's scope (verification, not implementation of new logic).

---

## Orphan / Undocumented Workflows

| Item | Finding |
|---|---|
| `WF-LTSA-CUSTOMER-BY-CODE-001.json` (item 6) | A "by-code" customer lookup operation exists (as an empty shell) but is **not documented anywhere** — not in `API_CONTRACT.md`'s 5 operations, not in `CHANGELOG.md`. Orphan workflow file with no matching documentation. |
| `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/` (whole build pack) | Has no `README.md` or `RELEASE-NOTES.md` of its own (every other build pack has at least a `README.md`). Its outputs (items 6–12) are undocumented at the build-pack level. |

**Result: WARNING** — no orphan *verification document* remains after the BC-22 correction above; these two items are orphan *workflow/build-pack* artifacts lacking documentation, the inverse case. Recorded here since IR-002 also asks to "detect orphan verification documents" and these are the closest matching class of inconsistency found.

---

## Summary

| Item | Result |
|---|---|
| Every workflow file enumerated (23 deployed + 1 template) | PASS |
| Every documented operation maps to at least one file | PASS |
| Every workflow file has real, functioning logic | **WARNING** — only 2 of 23 do (items 12, 23); tracked as pre-existing feature-completeness gap, not a new defect |
| MWO-P-001 Broken Feature B6 (missing workflow file) | **WARNING** — Superseded by evidence collected during IR-002; file exists, claim is not orphan |
| Orphan verification documents | PASS — none remain |
| Orphan/undocumented workflow artifacts | **WARNING** — `WF-LTSA-CUSTOMER-BY-CODE-001.json` and BP-007 as a whole lack documentation |
