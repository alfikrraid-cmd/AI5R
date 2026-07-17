# Repository Cleanup Audit

Status: Audit complete. Read-only. No source code modified. No commit performed.
Requested by: Chief Architect — Repository Cleanup Audit mission
Scope: Every modified/untracked path in the repository (not limited to LTSA-BRAIN), per `git status` against the current `feature/ltsa-brain` branch tip (`d9f879e`).

---

## 1. Method

`git status --porcelain=v1` (whole repository, no path filter) was the ground truth. Findings below are grounded in direct file reads, `git log`/`git show` on colliding identifiers, and `git diff` on every modified tracked file — not assumed from filenames alone.

**Raw counts:** 11 modified (tracked) files, 88 top-level untracked paths (several of which are entire directory trees). **Zero deletions, zero renames** detected anywhere in the repository (`git status` shows no `D`/`R` entries) — stated explicitly per Task 4, not omitted.

---

## 2. Modified (Tracked) Files — Full List and Disposition

| File | Nature of change | Milestone |
|---|---|---|
| `ADR/ADR_INDEX.md` | Added the `ADR-004` row | Engineering Operating System |
| `AI5R-SDK/FACTORY/TESTS/test_manifest_loader.py` | One assertion updated (`"LTSA Brain"` → `"OSA Maintenance"`, tracking live `product.manifest.json` drift) | Unrelated — pre-existing, not caused by this session (see `RCA-001`) |
| `AI5R-SDK/MANUFACTURING_CENTER/TESTS/test_mfg_003b_execute_step.py` | `Path("/tmp")` → `Path(tempfile.gettempdir())` | **Unrelated, legitimate cross-platform portability fix** — not LTSA, not governance |
| `AI5R-SDK/MANUFACTURING_CENTER/TESTS/test_mfg_003b_step_creation.py` | Same fix as above | Same as above |
| `CHANGELOG.md` | Extended with MWO-030/040A–040E + governance entries | Engineering Operating System |
| `PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql` | 15 new tables appended (040A–040E) | LTSA Acquisition Epic |
| `PRODUCTS/LTSA-BRAIN/RELEASE/database.sql` | Auto-regenerated stub schema (test side effect) | **Generated artifact — see §5** |
| `PRODUCTS/LTSA-BRAIN/RELEASE/openapi.json` | Same | **Generated artifact — see §5** |
| `PRODUCTS/LTSA-BRAIN/RELEASE/schema.json` | Same | **Generated artifact — see §5** |
| `PRODUCTS/LTSA-BRAIN/product.manifest.json` | 15 new module entries (040A–040E) | LTSA Acquisition Epic |
| `ROADMAP.md` | Extended to reflect current state | Engineering Operating System |

Two of these (the `MANUFACTURING_CENTER` test files) belong to neither LTSA nor Governance — a real, correct, small fix, unrelated to every mission run this session. Flagged per Task 3 (unrelated changes).

---

## 3. Logical Milestone Groups (untracked trees)

| Milestone | Paths | File count (approx.) | Nature |
|---|---|---|---|
| **LTSA Acquisition Epic** (MWO-LTSA-030/040A–040E) | 16 `BUILD-PACKS/BP-{KNOWLEDGE-SOURCE,SEAL-ENGINEERING-DOCUMENT,WORKBOOK,WORKSHEET,WORKSHEET-TABLE,MAPPING-PROFILE,COLUMN-MAPPING,ACQUISITION-JOB,PDF-DOCUMENT,PDF-METADATA,DOCUMENT-CLASSIFICATION,PDF-ACQUISITION-JOB,ENGINEERING-MEDIA,MEDIA-METADATA,MEDIA-CLASSIFICATION,MEDIA-ACQUISITION-JOB}` dirs; `ENGINEERING/MWO/MWO-LTSA-{030,040A,040B,040C,040D,040E}-*.md` (10 docs) | ~350 | Real, already audited in full (`EA-001`) |
| **LTSA Acquisition Governance** | `ADR/ADR-004-*.md`, `ENGINEERING/MWO/MWO-LTSA-040C-R1-*.md`, `EA-001-*.md`, `RCA-001-*.md` | 4 | Real, already recommended as its own commit (`EA-001` §8) |
| **AI5R Engineering Operating System** | `CLAUDE.md`, `CURRENT_STATE.md`, `PROJECT_HISTORY.md`, `MEMORY.md`, `TECHNICAL_DEBT.md`, `DOCUMENTATION_CONTRACT.md`, `ENGINEERING/AI5R_ENGINEERING_STANDARD_v1.0.md`, `ENGINEERING/MWO/{DOC-001,EOPS-001,EOPS-002}-*.md` | 10 | Real, already recommended as its own commit (`EOPS-002` §8) |
| **MO-001 / prior LTSA-BRAIN products** | `BUILD-PACKS/BP-{ASSET,SOOT-BLOWER,WORK-ORDER,MAINTENANCE-HISTORY,DASHBOARD,SEAL-STOCK,SEAL-PUMP-COMPATIBILITY,SEAL-INTERCHANGE-COMPATIBILITY}`, `BUILD-PACKS/BP-{PUMP,SEAL}/TEST` | ~90 | Real, functioning, matches `product.manifest.json`'s own "manufactured under MO-001" narrative — coherent and complete |
| **LTSA-BRAIN Verification Infrastructure** | `PRODUCTS/LTSA-BRAIN/VERIFICATION/*` | 3 | Real (`MWO-P-006`); referenced by every 040-series test script already committed-in-spirit via `EA-001`'s validation runs |
| **LTSA-BRAIN AI-ASSISTANT** | `PRODUCTS/LTSA-BRAIN/AI-ASSISTANT/*` | 3 (+ ignored `__pycache__`) | **Possibly superseded — see §4** |
| **Enterprise Backend API / Manufacturing extension** | `CORE-SERVICES/API/{company_manufacturing,digital_factory_bootstrap}.py` + their `TESTS/`, `AI5R-SDK/MANUFACTURING/company_recipe_registration.py` + `TESTS/`, `AI5R-SDK/MANUFACTURING_CENTER/manufacturing_scheduler.py` | 6 | Real, coherent follow-on to the already-committed `MWO-DEP-001` — untested by this audit for functional correctness (out of scope; documentation/governance audit only) |
| **Loose engineering documents (pre-Acquisition-epic)** | `ENGINEERING/MWO/{MWO-P-001-LTSA-Product-Audit,MWO-P-006-Runtime-Verification-Infrastructure,MWO-P-006-Completion-Report,RV-004-Verification-Report}.md` | 4 | Real, historical, no naming collision found in `git log` |
| **Loose engineering document (possible collision)** | `ENGINEERING/MWO/MWO-P-007-LTSA-Python-Adapter.md` | 1 | **Identifier collision — see §4** |
| **Platform documentation (Blueprint, Factory Knowledge, Manufacturing, Marketing, Operations, Architecture Capabilities)** | `BLUEPRINT/*` (9), `FACTORY/*` (16), `MANUFACTURING/*` (8), `MARKETING/*` (14), `OPERATIONS/*` (14), `ENGINEERING/CAPABILITIES/*` (19), `ENGINEERING/RUNTIME/*` (31, minus ignored `__pycache__`), `PRODUCTS/{AI5R_UMKM_OS,DEMO_OS}/*` (4 each) | ~120 | Each is its own coherent, self-contained, real body of work, entirely independent of LTSA-BRAIN and of each other. Not audited for internal correctness (out of this mission's scope) — grouped and classified as-is. |
| **RepositoryPack** | `RepositoryPack/AI5R-Repository-Pack-v1.0/*` | 30 | A versioned, packaged export mirroring `ADR/`/`BOOTSTRAP/`/`ARCHITECTURE/` structure — **see §5** |
| **Local/personal configuration** | `.claude/{launch.json,settings.local.json}`, `CONSTITUTION/.claude/{launch.json,settings.local.json}`, `claude_desktop_config.json.bak.json` | 5 | **Not project source — see §5** |
| **Generated artifacts** | `PRODUCTS/LTSA-BRAIN/RELEASE/{release.json,workflow.json}` (untracked, unknown origin per `RCA-001`), `BUILD/RUN-*` (162 run dirs + zips, 819 files, 913K) | 821 | **See §5** |

---

## 4. Identifier Collisions and Possibly Superseded Work

### `MWO-P-007` — reused identifier
`git log` shows commit `5d67c16` — **"MWO-P-007: implement Pump Gateway"** (`CORE-SERVICES/API/pump_gateway.py` + test) — already committed. The untracked `ENGINEERING/MWO/MWO-P-007-LTSA-Python-Adapter.md` is a **different document under the same identifier**: status line reads "DRAFT — WORK ORDER ONLY, NO IMPLEMENTATION PERFORMED," describing the same underlying need (a Python-callable interface for Pump Registry, "LTSA Python Adapter"). Reading both together, the untracked document is almost certainly the **original planning draft** for work that was later implemented and committed as "Pump Gateway" — i.e. it is a stale, superseded draft, not a second, independent MWO-P-007. **Recommend: do not commit as new/open work.** Either update its status line to "Superseded by commit `5d67c16`" before committing, or hold it out of this commit round entirely for the Chief Architect to reconcile the identifier collision. Not deleted, not modified by this audit.

### `AI-ASSISTANT/maintenance_assistant.py` — possibly superseded by MWO-022
`git log` shows commit `07dba51` — **"MWO-022: implement Maintenance Copilot"** — a distinctly-named, already-committed module (`CORE-SERVICES/API` test references `maintenance_copilot`). The untracked `PRODUCTS/LTSA-BRAIN/AI-ASSISTANT/maintenance_assistant.py` is a **different file, different path, similar concept** ("assistant" vs. "copilot"). Lower confidence than the `MWO-P-007` case (no identical identifier collision, just naming/conceptual similarity) — flagged for the Chief Architect to confirm whether this is superseded prototype work or a genuinely distinct, still-relevant module before it is committed as new.

No other identifier collisions were found against 816 commits in `git log --oneline --all`.

---

## 5. Generated Artifacts and Non-Source Content

- **`PRODUCTS/LTSA-BRAIN/RELEASE/{database.sql,schema.json,openapi.json}`** — confirmed, per `RCA-001`, mechanically regenerated by three test files' real-path side effect on every bare `pytest` run. Not hand-authored, not canonical. **Generated artifact.**
- **`PRODUCTS/LTSA-BRAIN/RELEASE/{release.json,workflow.json}`** — untracked, same directory, no live code path found that produces them (`RCA-001` §2). Same category by association; origin unconfirmed but behavior (silently regenerable, non-canonical) is the same. **Generated artifact, unconfirmed origin.**
- **`BUILD/RUN-*` (162 directories + matching `.zip` files, 819 files, 913 KB)** — each `RUN-<hash>` directory contains an near-identical generated FastAPI app scaffold (`app/main.py`, `app/routers/auth.py`, `openapi.json`, `tests/`) plus a zip of the same content. This is unmistakably **build/run output from a code-generation process**, not hand-authored source — the pattern (many near-duplicate timestamped/hashed run folders, each zipped) is the same shape as a build cache or CI artifact directory. **Generated artifact — recommend excluding from version control entirely (gitignore), not committing.**
- **`RepositoryPack/AI5R-Repository-Pack-v1.0/*`** — a versioned (`v1.0`), packaged mirror of `ADR/`/`BOOTSTRAP/`-shaped content (`ADR-0001-AI5R-Lives-In-Repository.md`, its own `ADR_INDEX.md`, `BOOTSTRAP/BOOTSTRAP.md`, etc.). This reads as a deliberate, versioned **export/distribution package** (a "repository starter pack" product), not accidental generator output — real content, not stubs. Recommend treating it as its own legitimate deliverable (own commit), but flagged for the Chief Architect to confirm it is meant to be tracked in this repository at all, versus published/distributed separately.
- **`.claude/{launch.json,settings.local.json}`, `CONSTITUTION/.claude/{launch.json,settings.local.json}`** — local Claude Code session configuration. `settings.local.json` is, by Claude Code's own naming convention, per-machine/personal and never intended for commit; `launch.json` (dev-server preview config) is typically also machine-specific. The duplicate `CONSTITUTION/.claude/` (a second copy, one directory level down) appears to be an artifact of having run Claude Code from within `CONSTITUTION/` at some point. **Not project source — recommend `.gitignore` entry for `.claude/`, exclude from commit.**
- **`claude_desktop_config.json.bak.json`** (repo root) — a Claude Desktop application config backup, containing only local UI-preference keys (verified by key names only, not values, out of privacy caution) such as `remoteToolsDeviceName`, `coworkUserFilesPath`. **Not project source, potentially machine-specific — recommend `.gitignore` entry, exclude from commit.**

---

## 6. Accidental Deletions

**None found.** `git status --porcelain=v1` (whole repository) returns zero `D` (deleted) and zero `R` (renamed) entries. This was checked directly, not assumed from the absence of a report elsewhere.

---

## 7. Summary Table — Milestone → Recommended Action Class

| Milestone | Action Class |
|---|---|
| LTSA Acquisition Epic (040A–040E) | COMMIT (5 sub-commits, per `EA-001` §8) |
| LTSA Acquisition Governance (ADR-004/040C-R1/EA-001/RCA-001) | COMMIT (1 commit, per `EA-001` §8) |
| AI5R Engineering Operating System | COMMIT (1 commit, per `EOPS-002` §8 — **this mission's own scope**) |
| MO-001 / prior LTSA-BRAIN products | COMMIT (1 commit — out of this mission's scope to execute, recommended for a future, separate approval) |
| LTSA-BRAIN Verification Infrastructure | COMMIT (bundle with MO-001/prior products, or its own — Chief Architect's call) |
| LTSA-BRAIN AI-ASSISTANT | KEEP — hold pending supersession check (§4) |
| Enterprise Backend API / Manufacturing extension | COMMIT (its own commit — out of this mission's scope to execute) |
| Loose engineering documents (no collision) | COMMIT (bundle with their respective MWO's own commit where identifiable) |
| `MWO-P-007-LTSA-Python-Adapter.md` | KEEP — do not commit as-is; needs status correction or Chief Architect reconciliation (§4) |
| Platform documentation (Blueprint/Factory/Manufacturing/Marketing/Operations/Capabilities/Runtime/other products) | COMMIT (each its own commit — out of this mission's scope to execute) |
| RepositoryPack | KEEP — confirm intent before committing (§5) |
| `AI5R-SDK/MANUFACTURING_CENTER` test portability fix | COMMIT (its own small, unrelated commit) |
| `PRODUCTS/LTSA-BRAIN/RELEASE/*` | IGNORE (exclude from every commit; add to `.gitignore` pending `TD-001`'s resolution) |
| `BUILD/RUN-*` | IGNORE (add to `.gitignore`) |
| `.claude/*`, `claude_desktop_config.json.bak.json` | IGNORE (add to `.gitignore`) |

Full per-path classification (`KEEP` / `COMMIT` / `MOVE` / `RESTORE` / `DELETE` / `IGNORE`) is in the companion document, `COMMIT_PLAN.md`.

---

Stopping here as instructed. No source code was modified, nothing was deleted, nothing was committed. Awaiting approval.
