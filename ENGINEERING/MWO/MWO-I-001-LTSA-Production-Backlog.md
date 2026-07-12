# MWO-I-001 — LTSA Production Backlog

Status: BACKLOG — READ-ONLY ANALYSIS, NO IMPLEMENTATION PERFORMED
Type: Mission Work Order (Implementation Backlog)
Role: Senior Software Engineer
Architecture: FROZEN — no architectural change proposed in this document
Sources (exhaustive): `ENGINEERING/REVIEWS/LTSA-Canonical-Definition-Review.md`, `ENGINEERING/ADR/ADR-006-Canonical-Product-Definition.md`, current repository state (`main`, `HEAD` = `92fa68f`)

---

## Scope Note

The source Review's Finding 1 established that the literal string "LTSA" has no current definition anywhere in the repository — tracked, legacy, or packaged — and its only historical occurrence (`"LTSA-BRAIN"`, test data) was reverted. The Review and ADR-006 do define a concrete, evidence-backed system that this backlog can act on: the **Canonical Product Definition** and the set of artifacts ADR-006 and the Review identify as currently claiming, partially backing, or blocking that SSOT role (`system_manifest.json`, `CONSTITUTION/`, `ADR/`, `ROADMAP/`, `BOOTSTRAP/`, the `REGISTRY/`/`registry/` case duplication, and the zip-packaged content).

This backlog is scoped to making that system production-ready. No new concept, component, or name is introduced beyond what the three cited sources already contain.

---

## Ordering

Items are ordered by production impact (highest first): correctness/data-integrity defects before missing-content gaps, foundational SSOT gaps before dependent cleanup, automated safeguards last (they prevent regression of defects fixed above them).

---

### MWO-I-001-001 — Resolve `REGISTRY/`/`registry/` case-duplication

**Objective:** Eliminate the two case-colliding top-level trees so checkout is deterministic on all platforms.
**Evidence Source:** Review, Finding 6 / Evidence Index #9; `ENGINEERING/RC/RC-002-Repository-Case-Normalization.md` (directly referenced by the Review).
**Affected Components:** `REGISTRY/` (13 tracked files + subtrees), `registry/` (legacy: `BOOTSTRAP`, `CONTITUTION`, `SYSTEM`, `workflow`, `readme2`, `test`).
**Dependencies:** None (blocking predecessor for MWO-I-001-004, -009, -011).
**Estimated Complexity:** L
**Priority:** Critical
**Category:** Deployment

---

### MWO-I-001-002 — Designate and populate the canonical Product Definition file

**Objective:** Create the single file ADR-006 requires but explicitly left undesignated, and populate it as the authoritative Product Definition for every AI5R product.
**Evidence Source:** ADR-006, Decision and Consequences ("Harder": *"no enforcement target... until the follow-up MWO designates and populates an actual file"*); Review, Finding 6 (no document anywhere is populated as "Product Definition").
**Affected Components:** New canonical file (location TBD as part of this item's execution); `REGISTRY/SYSTEM/system_manifest.json` (must reference it once it exists).
**Dependencies:** None.
**Estimated Complexity:** M
**Priority:** Critical
**Category:** Documentation

---

### MWO-I-001-003 — Populate the 13 empty root `CONSTITUTION/*.md` files

**Objective:** Fill the 13 constitution documents that `system_manifest.json` already cites by name as backing its "Canonical identity definition... single source of truth" claim, currently 2 bytes each.
**Evidence Source:** Review, Finding 3 (`9c006c9` scaffold, all 13 files empty at `HEAD`); Finding 2 (`system_manifest.json` self-declaration and `constitution_docs` list).
**Affected Components:** `CONSTITUTION/00_IDENTITY.md` through `CONSTITUTION/12_EXECUTION_PROTOCOL.md` (13 files).
**Dependencies:** MWO-I-001-005 (source content to migrate in from, if reused rather than authored fresh).
**Estimated Complexity:** L
**Priority:** Critical
**Category:** Documentation

---

### MWO-I-001-004 — Reconcile or retire the legacy `REGISTRY/CONTITUTION/` empty copies

**Objective:** Prevent two "constitutions" (one populated, one still empty) from co-existing once MWO-I-001-003 completes; the legacy tree currently holds byte-identical empty stubs of the same 13 files.
**Evidence Source:** Review, Finding 5 (md5 comparison, all 13 pairs identical, `721a8a4` migration).
**Affected Components:** `REGISTRY/CONTITUTION/*.md` (13 files, misspelled directory name).
**Dependencies:** MWO-I-001-001, MWO-I-001-003.
**Estimated Complexity:** S
**Priority:** High
**Category:** Deployment

---

### MWO-I-001-005 — Migrate populated Constitution/ADR content out of the zip package into tracked canonical locations

**Objective:** The only populated Constitution content (2.5–7.6 KB per file) and the only populated ADR (`ADR-0001`, plus its index) currently exist solely inside `AI5R-Repository-Pack-v1.0.zip` / its untracked extraction (`RepositoryPack/`), not in a reproducible, diffable, CI-visible tracked location.
**Evidence Source:** Review, Finding 4 (zip added in `2cb04e0`; extraction untracked; content sizes).
**Affected Components:** `AI5R-Repository-Pack-v1.0.zip`, `RepositoryPack/AI5R-Repository-Pack-v1.0/CONSTITUTION/*`, `RepositoryPack/AI5R-Repository-Pack-v1.0/ADR/*`.
**Dependencies:** None (feeds MWO-I-001-003, MWO-I-001-006).
**Estimated Complexity:** M
**Priority:** High
**Category:** Release

---

### MWO-I-001-006 — Populate the official tracked `ADR/ADR_INDEX.md` and `ADR/TEMPLATE.md`, register existing ADRs

**Objective:** The tracked, official ADR location (per repository folder convention) is currently empty (0 bytes, both files); register `ADR-0001` and `ADR-006` there so the canonical ADR trail is discoverable without opening the zip package.
**Evidence Source:** Review, Finding 4 (root `ADR/` both files 0 bytes vs. populated `RepositoryPack/.../ADR/ADR_INDEX.md`, 477 bytes).
**Affected Components:** `ADR/ADR_INDEX.md`, `ADR/TEMPLATE.md`.
**Dependencies:** MWO-I-001-005.
**Estimated Complexity:** S
**Priority:** High
**Category:** Documentation

---

### MWO-I-001-007 — Resolve `ADR-0002`, `ADR-0003`, `ADR-0004` stub references

**Objective:** The packaged `ADR_INDEX.md` lists these three ADRs by title and status (two `ACCEPTED`, one `PROPOSED`), but no file for any of them exists anywhere in the repository. Each must be authored to match its claimed status, or the index entry formally withdrawn.
**Evidence Source:** Review, Finding 4 (index table reproduced; only `ADR-0001`'s file located).
**Affected Components:** `ADR/` (target location per MWO-I-001-006), `RepositoryPack/.../ADR/ADR_INDEX.md`.
**Dependencies:** MWO-I-001-006.
**Estimated Complexity:** M
**Priority:** Medium
**Category:** Documentation

---

### MWO-I-001-008 — Populate `ROADMAP/PRODUCT.md` and sibling roadmap files

**Objective:** `ROADMAP/PRODUCT.md` is empty everywhere it exists in the repository (root: 0 bytes; packaged extraction: no file at all, only `.gitkeep`). This is the only file in the whole audited surface whose name most literally matches "product roadmap," yet it has zero content in any candidate location.
**Evidence Source:** Review, Finding 6 (table row for `ROADMAP/PRODUCT.md` and siblings).
**Affected Components:** `ROADMAP/PRODUCT.md`, `ROADMAP/FACTORY.md`, `ROADMAP/MASTER_ROADMAP.md`, `ROADMAP/PLATFORM.md`.
**Dependencies:** MWO-I-001-002 (roadmap content should trace back to the canonical Product Definition once it exists).
**Estimated Complexity:** M
**Priority:** Medium
**Category:** Documentation

---

### MWO-I-001-009 — Reconcile divergent `BOOTSTRAP/LOAD.md` content (root vs. legacy)

**Objective:** Unlike the Constitution files (identical-empty), `BOOTSTRAP/LOAD.md` (root, 7589 bytes) and `REGISTRY/BOOTSTRAP/LOAD.md` (legacy, 3395 bytes) both contain real but *different* content. Two divergent "current state" documents is a production risk in its own right.
**Evidence Source:** Review, Finding 6 (`diff` reports non-identical, explicit byte counts).
**Affected Components:** `BOOTSTRAP/LOAD.md`, `REGISTRY/BOOTSTRAP/LOAD.md`.
**Dependencies:** MWO-I-001-001.
**Estimated Complexity:** M
**Priority:** Medium
**Category:** Documentation

---

### MWO-I-001-010 — Populate remaining empty `ARCHITECTURE/` and `BOOTSTRAP/` scaffolding files

**Objective:** Fill the remaining 0-byte scaffold files from the original `9c006c9` structure commit not already covered above: `ARCHITECTURE/{FACTORY,KERNEL,MEMORY,PLATFORM}.md` and `BOOTSTRAP/{CHANGELOG,CURRENT_STATE,NEXT_ACTION,ROADMAP,SESSION}.md`.
**Evidence Source:** Review, Finding 6 (size table).
**Affected Components:** 9 files listed above.
**Dependencies:** MWO-I-001-002.
**Estimated Complexity:** L
**Priority:** Medium
**Category:** Documentation

---

### MWO-I-001-011 — Execute outstanding `CLEANUP_CHECKLIST.md` items

**Objective:** Close the unchecked items already recorded in the existing checklist: `System deferred to Runtime Sprint`, `Test pending review`, `Legacy removal deferred to PR #2`, and the full `Validation` section (`Git clean`, `No duplicate registry`, `Runtime valid`, `Bootstrap valid`). This is execution of already-planned work, not new scope.
**Evidence Source:** `REGISTRY/MIGRATIONS/CLEANUP_CHECKLIST.md` (current repository state, read directly); referenced by the Review's Evidence Index #9 via `RC-002`.
**Affected Components:** `REGISTRY/MIGRATIONS/CLEANUP_CHECKLIST.md` and everything it gates (`registry/` legacy removal, runtime/bootstrap validation).
**Dependencies:** MWO-I-001-001, MWO-I-001-009.
**Estimated Complexity:** M
**Priority:** High
**Category:** Deployment

---

### MWO-I-001-012 — Add CI check: fail build on case-duplicate top-level paths

**Objective:** Prevent recurrence of the defect fixed in MWO-I-001-001 by automatically failing any future build/PR that introduces two paths differing only by case.
**Evidence Source:** Review, Finding 6 (Evidence Index #9); Review confirms no such enforcement currently exists in the repository.
**Affected Components:** CI/build pipeline configuration (none currently observed in repository).
**Dependencies:** MWO-I-001-001.
**Estimated Complexity:** S
**Priority:** Medium
**Category:** Testing

---

### MWO-I-001-013 — Add CI check: fail build when SSOT-referenced files are empty or missing

**Objective:** Prevent recurrence of the defect fixed in MWO-I-001-002/003/006/008: a file self-declared or index-listed as canonical (e.g., anything in `system_manifest.json`'s `constitution_docs`, or any entry in `ADR_INDEX.md`) must not be permitted to sit at 0 or 2 bytes, or reference a non-existent file.
**Evidence Source:** Review, Findings 2, 3, 4, 6 (the empty-but-declared-canonical pattern repeated across `CONSTITUTION/`, `ADR/`, `ROADMAP/`).
**Affected Components:** CI/build pipeline configuration; `REGISTRY/SYSTEM/system_manifest.json`; `ADR/ADR_INDEX.md`.
**Dependencies:** MWO-I-001-002, MWO-I-001-003, MWO-I-001-006, MWO-I-001-007, MWO-I-001-008.
**Estimated Complexity:** M
**Priority:** Medium
**Category:** Testing

---

### MWO-I-001-014 — Add schema validation for `REGISTRY/SYSTEM/*.json` manifests

**Objective:** `registry.json`, `module_schema.json`, `dependency_graph.json`, `runtime.json`, `version.json`, and `system_manifest.json` are all self-declared single-source-of-truth manifests; none were observed to have an automated schema/consistency check in the current repository state.
**Evidence Source:** Current repository state (`REGISTRY/SYSTEM/` directory listing and file contents, read directly); pattern of unchecked SSOT self-declarations established in Review Finding 2.
**Affected Components:** `REGISTRY/SYSTEM/*.json` (6 files), CI/build pipeline configuration.
**Dependencies:** None.
**Estimated Complexity:** M
**Priority:** Low
**Category:** Testing

---

### MWO-I-001-015 — Remove the committed zip binary from version control after migration

**Objective:** Once MWO-I-001-005 has migrated all needed content out of `AI5R-Repository-Pack-v1.0.zip` into tracked canonical locations, remove the binary archive from the repository (or from active history per standard binary-cleanup practice) so it stops being the de facto source of truth for any file.
**Evidence Source:** Review, Finding 4 (zip identified as origin of all currently-populated Constitution/ADR content); current repository state (`git ls-files` confirms the zip is tracked at repo root).
**Affected Components:** `AI5R-Repository-Pack-v1.0.zip`.
**Dependencies:** MWO-I-001-005.
**Estimated Complexity:** S
**Priority:** Low
**Category:** Release

---

## Summary Table

| ID | Title | Priority | Category | Complexity |
|---|---|---|---|---|
| MWO-I-001-001 | Resolve `REGISTRY/`/`registry/` case-duplication | Critical | Deployment | L |
| MWO-I-001-002 | Designate and populate canonical Product Definition file | Critical | Documentation | M |
| MWO-I-001-003 | Populate 13 empty root `CONSTITUTION/*.md` files | Critical | Documentation | L |
| MWO-I-001-004 | Reconcile/retire legacy `REGISTRY/CONTITUTION/` empty copies | High | Deployment | S |
| MWO-I-001-005 | Migrate zip-packaged content into tracked canonical locations | High | Release | M |
| MWO-I-001-006 | Populate official `ADR/ADR_INDEX.md` + `TEMPLATE.md`, register existing ADRs | High | Documentation | S |
| MWO-I-001-007 | Resolve `ADR-0002`/`0003`/`0004` stub references | Medium | Documentation | M |
| MWO-I-001-008 | Populate `ROADMAP/PRODUCT.md` and siblings | Medium | Documentation | M |
| MWO-I-001-009 | Reconcile divergent `BOOTSTRAP/LOAD.md` content | Medium | Documentation | M |
| MWO-I-001-010 | Populate remaining empty `ARCHITECTURE/`/`BOOTSTRAP/` scaffolding | Medium | Documentation | L |
| MWO-I-001-011 | Execute outstanding `CLEANUP_CHECKLIST.md` items | High | Deployment | M |
| MWO-I-001-012 | CI check: fail build on case-duplicate paths | Medium | Testing | S |
| MWO-I-001-013 | CI check: fail build when SSOT files are empty/missing | Medium | Testing | M |
| MWO-I-001-014 | Schema validation for `REGISTRY/SYSTEM/*.json` | Low | Testing | M |
| MWO-I-001-015 | Remove committed zip binary after migration | Low | Release | S |

No item above has been implemented, executed, or committed. This document is a backlog only.
