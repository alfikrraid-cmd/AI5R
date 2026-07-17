# Commit Plan

Status: Plan only. Not executed. No commit performed.
Companion to: `REPOSITORY_CLEANUP_AUDIT.md` (full findings and evidence)
Classification legend: **KEEP** (leave uncommitted, no action now) · **COMMIT** (stage and commit as part of the named group) · **MOVE** (relocate before committing) · **RESTORE** (recover from history — none needed, see below) · **DELETE** (remove — none recommended by this plan, see below) · **IGNORE** (add to `.gitignore`, exclude from every commit)

**RESTORE: not applicable.** Zero deletions were found anywhere in the repository (`REPOSITORY_CLEANUP_AUDIT.md` §6). No file needs restoring.

**DELETE: not recommended by this plan.** Per the standing instruction not to modify or delete anything during audit missions, every candidate for removal (dead `BOOTSTRAP/` stubs, generated `BUILD/RUN-*` output, `RELEASE/*` stubs) is classified `IGNORE` (excluded from commits, added to `.gitignore`) rather than `DELETE` — deletion remains a separate, explicit decision for the Chief Architect.

---

## Group 1 — AI5R Engineering Operating System (this mission's own authorized scope)

**Classification: COMMIT**

| Path | Classification |
|---|---|
| `CLAUDE.md` | COMMIT |
| `CURRENT_STATE.md` | COMMIT |
| `CHANGELOG.md` | COMMIT |
| `PROJECT_HISTORY.md` | COMMIT |
| `ROADMAP.md` | COMMIT |
| `MEMORY.md` | COMMIT (rename to `ENGINEERING_MEMORY.md` remains `TD-005`, deferred — commit under current name) |
| `TECHNICAL_DEBT.md` | COMMIT |
| `DOCUMENTATION_CONTRACT.md` | COMMIT |
| `ENGINEERING/AI5R_ENGINEERING_STANDARD_v1.0.md` | COMMIT |
| `ENGINEERING/MWO/DOC-001-Documentation-Integration-Report.md` | COMMIT |
| `ENGINEERING/MWO/EOPS-001-AI5R-Engineering-Operating-System-Review.md` | COMMIT |
| `ENGINEERING/MWO/EOPS-002-Governance-Finalization-Report.md` | COMMIT |
| `REPOSITORY_CLEANUP_AUDIT.md` (this mission's own deliverable) | COMMIT — bundle with this group |
| `COMMIT_PLAN.md` (this file) | COMMIT — bundle with this group |

**Commit title:** `EOPS-001: establish AI5R Engineering Operating System`
**Commit body:** as drafted in `EOPS-002` §8, extended with one line noting the Repository Cleanup Audit and Commit Plan are included.

---

## Group 2 — LTSA Acquisition Epic (5 sub-commits, per `EA-001` §8 — recommended, not this mission's own scope to execute)

| Sub-group | Paths | Classification |
|---|---|---|
| 2a. MWO-LTSA-040A | `BUILD-PACKS/BP-KNOWLEDGE-SOURCE/`, `ENGINEERING/MWO/MWO-LTSA-040A-*.md` | COMMIT |
| 2b. MWO-LTSA-040B | `BUILD-PACKS/BP-SEAL-ENGINEERING-DOCUMENT/`, `ENGINEERING/MWO/MWO-LTSA-040B-*.md` | COMMIT |
| 2c. MWO-LTSA-040C | `BUILD-PACKS/BP-{WORKBOOK,WORKSHEET,WORKSHEET-TABLE,MAPPING-PROFILE,COLUMN-MAPPING,ACQUISITION-JOB}/`, `ENGINEERING/MWO/MWO-LTSA-040C-Universal-Tabular-Data-Acquisition.md`, `-Completion-Report.md` | COMMIT |
| 2d. MWO-LTSA-040D | `BUILD-PACKS/BP-{PDF-DOCUMENT,PDF-METADATA,DOCUMENT-CLASSIFICATION,PDF-ACQUISITION-JOB}/`, `ENGINEERING/MWO/MWO-LTSA-040D-*.md` | COMMIT |
| 2e. MWO-LTSA-040E | `BUILD-PACKS/BP-{ENGINEERING-MEDIA,MEDIA-METADATA,MEDIA-CLASSIFICATION,MEDIA-ACQUISITION-JOB}/`, `ENGINEERING/MWO/MWO-LTSA-040E-*.md` | COMMIT |
| 2f. Shared schema & manifest | `PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql`, `PRODUCTS/LTSA-BRAIN/product.manifest.json` | COMMIT (as one commit — cumulative across 040A–040E, hunk-splitting not attempted per `EA-001` §8) |

Also part of MWO-LTSA-030 (predates the epic's own numbering scheme but part of the same Mechanical Seal Knowledge foundation):

| Path | Classification |
|---|---|
| `ENGINEERING/MWO/MWO-LTSA-030-*.md` | COMMIT — bundle with 2b (both reference `seal_engineering_document`) |

**Not this mission's scope to execute** — recommended for a separate, later Chief Architect approval, per `EA-001` §8.

---

## Group 3 — LTSA Acquisition Governance (1 commit, per `EA-001` §8)

| Path | Classification |
|---|---|
| `ADR/ADR-004-Engineering-Acquisition-Pattern.md` | COMMIT |
| `ADR/ADR_INDEX.md` | COMMIT |
| `ENGINEERING/MWO/MWO-LTSA-040C-R1-Workbook-Acquisition-Pattern-Alignment.md` | COMMIT (specification only, no implementation — commit the document, not code) |
| `ENGINEERING/MWO/EA-001-LTSA-Acquisition-Engineering-Audit-Report.md` | COMMIT |
| `ENGINEERING/MWO/RCA-001-RELEASE-Stub-Schema-Root-Cause-Analysis.md` | COMMIT |

**Not this mission's scope to execute.**

---

## Group 4 — MO-001 / Prior LTSA-BRAIN Products (not this mission's scope; recommended for separate approval)

| Path | Classification |
|---|---|
| `BUILD-PACKS/BP-{ASSET,SOOT-BLOWER,WORK-ORDER,MAINTENANCE-HISTORY,DASHBOARD,SEAL-STOCK,SEAL-PUMP-COMPATIBILITY,SEAL-INTERCHANGE-COMPATIBILITY}/` | COMMIT |
| `BUILD-PACKS/BP-PUMP/TEST/`, `BUILD-PACKS/BP-SEAL/TEST/` | COMMIT — bundle with `MWO-P-006` (Verification Infrastructure), since these are the runtime-verification test additions to already-tracked packs |
| `PRODUCTS/LTSA-BRAIN/VERIFICATION/` | COMMIT — bundle with `MWO-P-006` |
| `ENGINEERING/MWO/MWO-P-001-LTSA-Product-Audit.md` | COMMIT |
| `ENGINEERING/MWO/MWO-P-006-Runtime-Verification-Infrastructure.md`, `MWO-P-006-Completion-Report.md` | COMMIT — bundle with `BP-PUMP/TEST`, `BP-SEAL/TEST`, `VERIFICATION/` above |
| `ENGINEERING/MWO/RV-004-Verification-Report.md` | COMMIT — bundle with the same group |

## Group 5 — LTSA-BRAIN AI-ASSISTANT (hold pending confirmation)

| Path | Classification |
|---|---|
| `PRODUCTS/LTSA-BRAIN/AI-ASSISTANT/` | **KEEP** — possibly superseded by the already-committed `MWO-022` (Maintenance Copilot). Do not commit until the Chief Architect confirms this is distinct, still-relevant work (`REPOSITORY_CLEANUP_AUDIT.md` §4). |

## Group 6 — `MWO-P-007-LTSA-Python-Adapter.md` (identifier collision)

| Path | Classification |
|---|---|
| `ENGINEERING/MWO/MWO-P-007-LTSA-Python-Adapter.md` | **KEEP** — do not commit as-is. The identifier `MWO-P-007` is already used by a committed, different piece of work (`5d67c16`, "implement Pump Gateway"). Needs its status line corrected to reflect supersession, or a Chief Architect decision on reconciling the collision, before this file is committed under any identifier. |

## Group 7 — Enterprise Backend API / Manufacturing Extension (not this mission's scope)

| Path | Classification |
|---|---|
| `CORE-SERVICES/API/company_manufacturing.py`, `digital_factory_bootstrap.py`, and their `TESTS/*` | COMMIT |
| `AI5R-SDK/MANUFACTURING/company_recipe_registration.py` and its `TESTS/*` | COMMIT — bundle with the above (imported by `company_manufacturing.py`) |
| `AI5R-SDK/MANUFACTURING_CENTER/manufacturing_scheduler.py` | COMMIT — bundle with the above, or its own commit if unrelated on closer inspection (not verified functionally by this audit) |

## Group 8 — Unrelated Portability Fix

| Path | Classification |
|---|---|
| `AI5R-SDK/MANUFACTURING_CENTER/TESTS/test_mfg_003b_execute_step.py` | COMMIT — its own small, standalone commit |
| `AI5R-SDK/MANUFACTURING_CENTER/TESTS/test_mfg_003b_step_creation.py` | COMMIT — same commit as above |

**Suggested commit title:** `Fix hardcoded /tmp path for cross-platform test compatibility`

## Group 9 — Platform Documentation (not this mission's scope; each its own commit)

| Path | Classification |
|---|---|
| `BLUEPRINT/` | COMMIT (own commit — OSA Blueprint Foundation, frozen per `MWO-BP-008`) |
| `FACTORY/` | COMMIT (own commit — Factory Knowledge base) |
| `MANUFACTURING/` | COMMIT (own commit — MO-001 specification/report, Manufacturing Backlog, templates) |
| `MARKETING/` | COMMIT (own commit) |
| `OPERATIONS/` | COMMIT (own commit) |
| `ENGINEERING/CAPABILITIES/` | COMMIT (own commit — Capability library, e.g. DOCKER capability) |
| `ENGINEERING/RUNTIME/` | COMMIT (own commit — AI5R Runtime engine) |
| `ENGINEERING/__init__.py` | COMMIT — bundle with `ENGINEERING/RUNTIME/` (empty package marker) |
| `PRODUCTS/AI5R_UMKM_OS/` | COMMIT (own commit) |
| `PRODUCTS/DEMO_OS/` | COMMIT (own commit) |

None of these were audited for internal correctness (out of this mission's documentation/governance scope) — classified for commit-grouping purposes only.

## Group 10 — RepositoryPack (confirm intent first)

| Path | Classification |
|---|---|
| `RepositoryPack/AI5R-Repository-Pack-v1.0/` | **KEEP** — real, versioned content, but confirm with the Chief Architect whether this is meant to be tracked in this repository at all (it may be intended as a separately-distributed package) before committing. |

## Group 11 — Generated Artifacts and Non-Source Content (IGNORE)

| Path | Classification |
|---|---|
| `PRODUCTS/LTSA-BRAIN/RELEASE/database.sql` | IGNORE — add to `.gitignore`; pending `TD-001` resolution |
| `PRODUCTS/LTSA-BRAIN/RELEASE/schema.json` | IGNORE — same |
| `PRODUCTS/LTSA-BRAIN/RELEASE/openapi.json` | IGNORE — same |
| `PRODUCTS/LTSA-BRAIN/RELEASE/release.json` | IGNORE — unknown origin, non-canonical (`RCA-001` §2) |
| `PRODUCTS/LTSA-BRAIN/RELEASE/workflow.json` | IGNORE — same |
| `BUILD/RUN-*` (162 directories + `.zip` files) | IGNORE — add `BUILD/` to `.gitignore` |
| `.claude/launch.json`, `.claude/settings.local.json` | IGNORE — add `.claude/` to `.gitignore` |
| `CONSTITUTION/.claude/launch.json`, `CONSTITUTION/.claude/settings.local.json` | IGNORE — same rule covers this nested copy |
| `claude_desktop_config.json.bak.json` | IGNORE — add explicit `.gitignore` entry (or a `*.bak.json` pattern) |

**Recommended `.gitignore` additions** (not applied by this plan — a code/config change requires its own approval):
```
BUILD/
.claude/
PRODUCTS/LTSA-BRAIN/RELEASE/
claude_desktop_config.json.bak.json
```

---

## Execution Order (recommended, once each group is separately approved)

1. **Group 1** — AI5R Engineering Operating System (this mission's authorized scope; ready now)
2. **Group 2** (2a–2f) — LTSA Acquisition Epic, five MWO commits + one shared schema/manifest commit
3. **Group 3** — LTSA Acquisition Governance
4. **Group 8** — Unrelated portability fix (trivial, no dependencies, can happen anytime)
5. **Group 4** — MO-001 / prior products
6. **Group 7** — Enterprise Backend API extension
7. **Group 9** — Platform documentation (Blueprint, Factory, Manufacturing, Marketing, Operations, Capabilities, Runtime, other products) — ten independent commits, any order
8. **Groups 5, 6, 10** — held pending Chief Architect confirmation, not scheduled
9. **Group 11** — not committed; `.gitignore` update proposed as its own, separate, explicit change

**Only Group 1 is within this mission's authorized scope to execute, and even Group 1 is not committed by this plan — it is a recommendation awaiting approval, per instruction.**

---

Stopping here as instructed. No commit performed.
