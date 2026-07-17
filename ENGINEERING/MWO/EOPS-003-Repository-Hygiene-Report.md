# EOPS-003 — Repository Hygiene Report

Status: Review complete. Policy and recommendations only. No source code changed, no implementation, no cleanup performed, no commit made.
Requested by: Chief Architect — final governance task before LTSA Manufacturing begins.
Scope: Review `REPOSITORY_CLEANUP_AUDIT.md`, `COMMIT_PLAN.md`, `EOPS-002`; inspect the live repository; resolve generated-artifact policy, `.gitignore` gaps, local-machine files, identifier collisions, possible supersedence, and structural hygiene.

---

## 1. Generated Artifacts

Full classification and per-artifact reasoning in the companion document, **`RCA-002-Generated-Artifacts-Policy.md`**. Summary:

| Artifact | Classification | Disposition |
|---|---|---|
| `PRODUCTS/LTSA-BRAIN/RELEASE/{database.sql,schema.json,openapi.json}` | Generated, Temporary | Ignore |
| `PRODUCTS/LTSA-BRAIN/RELEASE/{release.json,workflow.json}` | Generated (unconfirmed exact origin) | Ignore |
| `BUILD/RUN-*` (162 runs, 819 files) | Generated, Temporary | Ignore |
| `BUILD-PACKS/*/SCHEMAS/*.json`, `*/DATABASE/*.sql` (all MWO-authored build packs) | Source (hand-authored, MWO-reviewed) | Commit-worthy |
| `.bak` files (2 already committed, 1 untracked at root) | Temporary | Ignore going forward; already-committed ones are pre-existing debt, not remediated here |

**Governing rule, stated once, applied consistently:** an artifact is Ignore-worthy when its content is a deterministic function of another file already in the repository *and* it was not produced through an approved MWO's review. It is Commit-worthy when an approved MWO authored and validated it, regardless of how template-like or "generated-looking" its shape is. Surface appearance ("this file looks machine-written") is not the test; provenance is.

---

## 2. `.gitignore` Review

Full recommendation, with per-entry rationale, in the companion document, **`GITIGNORE-RECOMMENDATION.md`**. Summary of gaps found: the current `.gitignore` covers Python bytecode and common local-env files, but has **no entry** for build-cache directories, generated release artifacts, backup files, local Claude Code configuration, IDE files, or `node_modules`. Six additions recommended (`BUILD/`, `PRODUCTS/*/RELEASE/`, `*.bak`/`*.bak.*`/`*.tmp`/`*.old`/`*~`, `.claude/`, `.vscode/`/`.idea/`, `node_modules/`) — five evidence-driven (a real instance was found), one precautionary (`node_modules/`, `AI5R-STUDIO` already handles its own case via a nested `.gitignore`, but the root repo has no general protection for a future JS product). **`.gitignore` itself was not modified.**

---

## 3. Local Machine Files

| Path | Determination |
|---|---|
| `.claude/launch.json`, `.claude/settings.local.json` | **Gitignore** — per-machine, `.local.json` is Claude Code's own "never commit" naming convention |
| `CONSTITUTION/.claude/launch.json`, `CONSTITUTION/.claude/settings.local.json` | **Gitignore** — a second, apparently accidental copy of the same local config, one directory level down; same rule covers it once `.claude/` is added to `.gitignore` (the pattern matches at any depth) |
| `claude_desktop_config.json.bak.json` | **Gitignore** — Claude Desktop application config backup containing only local UI-preference keys (verified by key name only, not value, for privacy); not project source |
| `*.bak` files (`AI5R-SDK/FACTORY/MANUFACTURING/service.py.bak`, `.fm0015.bak`) | **Already committed** (pre-existing debt) — not newly relevant to this uncommitted-work review, but the same `.gitignore` gap that let them in should be closed going forward |

No file in this category is recommended for **Commit**.

---

## 4. Identifier Collision — `MWO-P-007`

Re-confirmed via `git log`/`git show` (816 commits searched, exactly one collision found):

- **Committed:** `5d67c16` — "MWO-P-007: implement Pump Gateway" (`CORE-SERVICES/API/pump_gateway.py` + test) — a transport-only layer forwarding requests to existing n8n Pump workflows.
- **Uncommitted:** `ENGINEERING/MWO/MWO-P-007-LTSA-Python-Adapter.md` — status line reads "DRAFT — WORK ORDER ONLY, NO IMPLEMENTATION PERFORMED," describing the same underlying need (a Python-callable interface for Pump Registry) that the committed work already fulfilled, under a different name ("LTSA Python Adapter" vs. "Pump Gateway").

**Determination: Superseded.** Reading both in full, the uncommitted document is the original planning draft for a need that was subsequently met by the committed implementation — not a second, independent work order that happens to share a number by coincidence. Of the four options (Rename / Archive / Superseded / Keep):
- **Rename** is not appropriate — renaming implies the document still describes open, distinct future work, which it does not; the need it describes is already met.
- **Archive** (physically relocating the file) is unnecessary — the document's content remains historically informative in place, and moving it adds a `MOVE` action this mission was not asked to perform.
- **Keep, unmodified** is not appropriate either — leaving its status line as "DRAFT... NO IMPLEMENTATION PERFORMED" is factually stale now that the underlying need has been met under the same identifier by different work.
- **Superseded** is the correct determination: before this document is ever committed, its status line should be corrected to state plainly that the need it identifies was met by commit `5d67c16` ("MWO-P-007: implement Pump Gateway"), under a different name, and that this document is retained as historical planning context, not an open work order. This is a text correction, not an implementation — **not performed by this report**, per the no-source-code-changes instruction; recommended for the Chief Architect's explicit authorization.

---

## 5. Supersedence Review — `maintenance_assistant.py` vs. `MWO-022`

`REPOSITORY_CLEANUP_AUDIT.md` §4 flagged this as a lower-confidence possible-supersession based on name similarity alone. This mission read both files' actual content directly, which **reverses that flag**:

- **`CORE-SERVICES/API/maintenance_copilot.py`** (committed, `07dba51`, "MWO-022: implement Maintenance Copilot") is explicitly a **presentation-only layer**: it imports from a sibling `maintenance_intelligence_service` module and formats/explains already-computed output (`show_pump`, explain status/history/role, summarize situation). Its own commit message states plainly: "No AI model integration."
- **`PRODUCTS/LTSA-BRAIN/AI-ASSISTANT/maintenance_assistant.py`** (untracked, MO-001/BP-AI-ASSISTANT) is explicitly a **BRAIN-integrated decision layer**: its own module docstring states it is "the first real product use of BRAIN" (`AI5R-SDK/BRAIN`), calling BRAIN's Observation→decision pipeline per `ADR-002`/`ADR-003`, building the "reality" dict shape BRAIN's `observation_engine.py` expects.

These are two structurally different components solving different problems — one formats already-decided output for a human reader, the other performs actual AI-driven observation and decision-making. Name similarity ("assistant" vs. "copilot") is coincidental, not evidence of duplication.

**Supersedence recommendation: `maintenance_assistant.py` is NOT superseded by `MWO-022`.** It should be evaluated for commit-worthiness on its own terms (per `COMMIT_PLAN.md` Group 5, now cleared to proceed as ordinary commit-worthy work, not held pending supersession review) — this correction updates the earlier, lower-confidence flag in `REPOSITORY_CLEANUP_AUDIT.md`, disclosed here as a finding that changed with better evidence, per the Engineering Standard's Evidence Standard, not silently dropped. **No file was removed or modified in reaching this conclusion.**

---

## 6. Repository Structure — Duplicates, Legacy Folders, Obsolete Scaffolding

Reviewed the whole repository tree, not only the uncommitted-work scope, per this task's own framing ("review repository structure").

**Duplicate folders / mirrored content (already noted in `EOPS-001`, reconfirmed):**
- `BOOTSTRAP/{CHANGELOG,CURRENT_STATE,ROADMAP,NEXT_ACTION,SESSION}.md` — all empty (0 bytes).
- `REGISTRY/BOOTSTRAP/{CURRENT_STATE,ROADMAP}.md` — empty, mirrors the above.
- `RepositoryPack/AI5R-Repository-Pack-v1.0/BOOTSTRAP/CURRENT_STATE.md` — empty, a third mirror.

**New finding this mission — `REGISTRY/` legacy/duplicate content (already committed, tracked, zero current diff — a structural finding, not an uncommitted-work finding):**
- **`REGISTRY/LEGACY/README.md`** — a folder explicitly named "LEGACY," containing only a `README.md`. Self-declared as legacy by its own name; worth a deliberate decision on whether it should be archived elsewhere or removed, rather than continuing to exist ambiguously inside the active `REGISTRY/` tree.
- **`REGISTRY/CONTITUTION/`** (sic — missing the "S" in "CONSTITUTION") — a full 13-file mirror of `CONSTITUTION/`'s numbered documents (`00_IDENTITY.md` through `12_EXECUTION_PROTOCOL.md`). This is both a **duplicate** (same content class as the real `CONSTITUTION/` at repo root) and contains an evident **typo in the directory name itself**. This is the clearest single duplicate-documentation finding of this entire hygiene review — a second, misnamed copy of the platform Constitution sitting inside `REGISTRY/`.
- **`REGISTRY/WORKFLOWS/` vs. `REGISTRY/workflow/`** — two similarly-named directories (`WORKFLOWS`, plural/uppercase, vs. `workflow`, singular/lowercase), each containing an `ai5r-contract-registry-001` and `ai5r-notification-001` subdirectory. Likely a casing/pluralization duplicate of the same underlying content — worth a deliberate consolidation decision.

**Obsolete scaffolding (already noted in `EOPS-001`, reconfirmed, not expanded):**
- `ROADMAP/{FACTORY,PLATFORM,PRODUCT}.md`, `ARCHITECTURE/{FACTORY,KERNEL,MEMORY,PLATFORM}.md` — all empty, unwritten sub-volumes of otherwise-real documentation trees.

**Report only — nothing above was renamed, merged, archived, or deleted by this review.**

---

## 7. Commit / Ignore / Technical Debt / Architecture Review — Final Recommendation

| Item | Recommendation |
|---|---|
| AI5R Engineering Operating System (Group 1, `COMMIT_PLAN.md`) | **Commit** — ready now, this mission's own authorized scope |
| LTSA Acquisition Epic + Governance (Groups 2–3) | **Commit** — recommended, separate approval required (unchanged from `EA-001`) |
| MO-001/prior products, Verification Infra, Enterprise Backend extension, Platform docs (Groups 4, 7, 9) | **Commit** — recommended, separate approval required, not audited for internal correctness |
| `AI-ASSISTANT/maintenance_assistant.py` (Group 5) | **Commit** — cleared this mission (§5); no longer held pending supersession review |
| `RepositoryPack/` (Group 10) | **Commit, pending confirmation of intent** — real content, but confirm whether it belongs in this repository before committing |
| `RELEASE/*`, `BUILD/RUN-*`, `.claude/*`, `claude_desktop_config.json.bak.json` (Group 11) | **Ignore** — add the `.gitignore` entries in `GITIGNORE-RECOMMENDATION.md`, exclude from every commit |
| `ENGINEERING/MWO/MWO-P-007-LTSA-Python-Adapter.md` (Group 6) | **Technical Debt** until its status line is corrected to "Superseded by `5d67c16`" — then Commit. Recommend adding as a new `TECHNICAL_DEBT.md` item (e.g. `TD-006`) rather than committing with a stale status line. |
| `RELEASE/*` generation pipeline itself (the three test files' real-path side effect) | **Technical Debt** — already `TD-001`; this mission's `RCA-002` reinforces the same finding, does not change its status |
| `REGISTRY/CONTITUTION/` (duplicate + typo), `REGISTRY/LEGACY/`, `REGISTRY/WORKFLOWS/` vs. `REGISTRY/workflow/` casing duplicate | **Architecture Review required** — these are already-committed, tracked, structural duplications inside a shared platform registry, not a single MWO's uncommitted work; correcting them (rename, merge, or removal) changes tracked history and shared structure, which per `ADR-000`/the Constitution's Architecture Freeze rule is exactly the class of change that needs a named trigger and Chief Architect decision, not an ad hoc fix folded into an unrelated commit. |
| Empty `BOOTSTRAP/`-family and `ARCHITECTURE/`/`ROADMAP/` sub-volume stubs | **Technical Debt** (low priority) — dormant, non-conflicting, no urgency; a candidate for a future documentation-hygiene pass, not Architecture Review (no structural ambiguity, just unfinished/empty content). |
| Already-committed `.bak` files in `AI5R-SDK/FACTORY/MANUFACTURING/` | **Technical Debt** — purging them requires rewriting tracked history, a more invasive action than this hygiene review's scope; the `.gitignore` fix prevents recurrence, the existing two files remain a separate, explicit decision. |

---

## Definition of Done — Status

- Reviewed `REPOSITORY_CLEANUP_AUDIT.md`, `COMMIT_PLAN.md`, `EOPS-002`, and inspected the live repository directly (not re-cited). **Met.**
- Every generated artifact classified (Source/Generated/Temporary/Commit-worthy/Ignore) with reasoning — `RCA-002`. **Met.**
- `.gitignore` reviewed, additions recommended, not applied — `GITIGNORE-RECOMMENDATION.md`. **Met.**
- Local machine files reviewed and determined (Commit/Ignore/Gitignore) — §3. **Met.**
- `MWO-P-007` collision reviewed, determination made (Superseded) — §4. **Met.**
- `maintenance_assistant.py` supersedence reviewed against `MWO-022`, recommendation produced, nothing removed — §5. **Met.**
- Repository structure reviewed for duplicates/legacy/obsolete scaffolding, reported only — §6. **Met.**
- Commit / Ignore / Technical Debt / Architecture Review recommendation produced — §7. **Met.**
- No source code changed, no implementation, no cleanup, no commit. **Met.**

---

Stopping here as instructed. Awaiting approval. Per instruction, the next mission after approval is `MWO-LTSA-048` (Canonical Manufacturing Contract).
