# CR-000 — Customer Registry Canonicalization Report

Parent: MWO-P-003 — Customer Registry Functional Completion (WP-000)
Branch: `feature/ltsa-brain` (local; not committed)
Basis: `ENGINEERING/MWO/MWO-P-001-LTSA-Product-Audit.md`, `ENGINEERING/MWO/LTSA-Integrity-Recovery-Summary.md` — no new audit scope opened

---

## Method

Every Customer Registry artifact under `PRODUCTS/LTSA-BRAIN` was read in full: all 5 `BP-005-CUSTOMER-REGISTRY/WORKFLOWS/*.json` files, all 6 `BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-*.json` files, `API/customer-registry/API_CONTRACT.md`, `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/README.md`, and `DATABASE/MIGRATIONS/005_create_customer_registry.sql`. For each operation, the artifact whose webhook path/route already matches the product's own documented contract, and which already contains a real (non-empty) node graph to extend, was selected as canonical — the same "prefer the definition closest to product intent, evidenced by the artifact itself" rule IR-001 used for the pump/customer table dedup.

---

## Full Artifact Inventory

| # | Path | Content |
|---|---|---|
| 1 | `BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-CREATE-001.json` | 1 node: `Webhook` (`POST ltsa/customer/create`), no downstream logic, `connections: {}` |
| 2 | `BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-GET-001.json` | 1 node: `Webhook` (`GET ltsa/customer/get`), no downstream logic |
| 3 | `BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-LIST-001.json` | 1 node: `Webhook` (`GET ltsa/customer/list`), no downstream logic |
| 4 | `BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-UPDATE-001.json` | 1 node: `Webhook` (`PUT ltsa/customer/update`), no downstream logic |
| 5 | `BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-DELETE-001.json` | 1 node: `Webhook` (`DELETE ltsa/customer/delete`), no downstream logic |
| 6 | `BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-CREATE-001.json` | `"nodes": []`, `"connections": {}` — completely empty |
| 7 | `BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-DETAIL-001.json` | Empty, same as above |
| 8 | `BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-LIST-001.json` | Empty, same as above |
| 9 | `BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-UPDATE-001.json` | Empty, same as above |
| 10 | `BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-DELETE-001.json` | Empty, same as above |
| 11 | `BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-BY-CODE-001.json` | Empty, same as above; no BP-005 counterpart exists |

No Customer Registry workflow artifact was found anywhere outside these two build packs.

---

## Comparison and Decision, Per Operation

**Create, List, Update, Delete, and Get/Detail:** every BP-005 file already carries a live `Webhook` trigger node whose `httpMethod`/`path` matches `API_CONTRACT.md` and `README.md` exactly (e.g. `POST ltsa/customer/create`). Every corresponding BP-007 file is `"nodes": []` — a generator-produced empty shell with no trigger, no path, and no evidence it was ever wired to the documented contract. BP-005 is the closer-to-complete artifact and the one the product's own documentation, `verify.py`, and `TEST/customer_registry_test.sh` already reference. **BP-005 is selected canonical for all five documented operations.**

**Get/Detail naming:** BP-005 names this operation `GET` (`WF-LTSA-CUSTOMER-GET-001.json`, path `ltsa/customer/get`); BP-007's empty counterpart is named `DETAIL` (`WF-LTSA-CUSTOMER-DETAIL-001.json`). Since `GET` is what `API_CONTRACT.md` and `README.md` document, the canonical file **keeps its existing name and path** (`WF-LTSA-CUSTOMER-GET-001.json`, `GET ltsa/customer/get`) — no rename. The `DETAIL` name is retired along with the deprecated BP-007 file it belongs to.

**By Code:** no BP-005 equivalent exists — `WF-LTSA-CUSTOMER-BY-CODE-001.json` (BP-007) is the only artifact for this operation. It is canonical by default; there is no deprecated counterpart to mark.

---

## Customer Registry Canonical Map

| Operation | Canonical | Deprecated |
|---|---|---|
| Create | `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-CREATE-001.json` | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-CREATE-001.json` |
| Detail (documented as `get`) | `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-GET-001.json` | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-DETAIL-001.json` |
| List | `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-LIST-001.json` | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-LIST-001.json` |
| Update | `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-UPDATE-001.json` | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-UPDATE-001.json` |
| Delete | `BUILD-PACKS/BP-005-CUSTOMER-REGISTRY/WORKFLOWS/WF-LTSA-CUSTOMER-DELETE-001.json` | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-DELETE-001.json` |
| By Code | `BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-CUSTOMER-BY-CODE-001.json` | *(none — no BP-005 counterpart exists)* |

This map is **locked for the remainder of MWO-P-003** per the MWO's constraint. WP-001–WP-006 implement into the canonical column only.

---

## Marking Convention for Deprecated JSON Artifacts

`IR-001` marked deprecated SQL with a leading `-- DEPRECATED (...)` comment, since SQL supports comments. JSON does not. The equivalent used here, applied to each deprecated file in this map, is a set of additive top-level metadata keys that n8n does not read and will not act on:

```json
"_deprecated": true,
"_deprecatedBy": "MWO-P-003 / WP-000",
"_deprecatedReason": "Superseded by <canonical path>. Empty generator shell, never wired to the documented contract. Do not import into n8n.",
"_canonicalReplacement": "<canonical path>"
```

No node, connection, or existing field in any deprecated file is modified. No file is deleted.

---

## Summary

| Item | Result |
|---|---|
| Every Customer Registry artifact identified | PASS — 11 workflow files (5 BP-005, 6 BP-007), plus contract/schema docs |
| BP-005 vs BP-007 compared per operation | PASS |
| Canonical implementation determined for every operation | PASS |
| Deprecated implementation determined for every operation | PASS (5 of 6; By Code has none) |
| Canonical Map produced | PASS — see table above, mirrored into `MWO-P-003-Customer-Registry-Functional-Completion.md` |
| Exactly one canonical implementation per operation | PASS |
| Duplicate implementation left active | **No** — deprecated files marked in WP-001–WP-005 (see their reports), not in WP-000, since marking is destructive-adjacent and is done in the same work package that also builds the canonical replacement, not before it exists |
