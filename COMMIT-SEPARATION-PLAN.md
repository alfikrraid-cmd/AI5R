# Commit Separation Plan

Status: Plan only. No files modified, staged, or committed.
Requested by: Chief Architect — Commit Separation Review, prior to `MWO-LTSA-049`.
Scope: Classify every currently modified/untracked file against three named milestones — EOPS-001 (AI5R Engineering Operating System), LTSA Acquisition v1.0 (040A–040E), MWO-LTSA-048 (UMC-001) — plus a residual class for everything outside all three.

---

## 1. Classification — Every File

Legend: **EOPS** = Exclusive to EOPS-001 · **LTSA** = Exclusive to LTSA Acquisition v1.0 · **048** = Exclusive to MWO-LTSA-048 · **SHARED** = Shared Documentation · **DEFER** = outside all three named milestones, not addressed by this plan.

### EXCLUSIVE TO EOPS (AI5R Engineering Operating System)

| File |
|---|
| `CLAUDE.md` |
| `TECHNICAL_DEBT.md` |
| `DOCUMENTATION_CONTRACT.md` |
| `ENGINEERING/AI5R_ENGINEERING_STANDARD_v1.0.md` |
| `ENGINEERING/MWO/DOC-001-Documentation-Integration-Report.md` |
| `ENGINEERING/MWO/EOPS-001-AI5R-Engineering-Operating-System-Review.md` |
| `ENGINEERING/MWO/EOPS-002-Governance-Finalization-Report.md` |
| `ENGINEERING/MWO/EOPS-003-Repository-Hygiene-Report.md` |
| `ENGINEERING/MWO/RCA-002-Generated-Artifacts-Policy.md` |
| `ENGINEERING/MWO/ARCH-REVIEW-001-Architecture-Integrity-Report.md` |
| `GITIGNORE-RECOMMENDATION.md` |
| `REPOSITORY_CLEANUP_AUDIT.md` |
| `COMMIT_PLAN.md` |

**Basis for exclusivity:** each was created and only ever edited during an EOPS-series turn (`EOPS-001`/`002`/`003` and their direct deliverables). None was touched by any LTSA Acquisition or `MWO-LTSA-048` implementation turn. `TECHNICAL_DEBT.md`'s content *references* LTSA topics (`TD-001`, `TD-002`) but the file itself was only ever written to during EOPS turns — the same distinction that keeps an audit document "belonging to" the audit, not to what it audits.

### EXCLUSIVE TO LTSA (Acquisition v1.0, 040A–040E)

| File / Directory |
|---|
| `PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql` |
| `PRODUCTS/LTSA-BRAIN/product.manifest.json` |
| `PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-{KNOWLEDGE-SOURCE,SEAL-ENGINEERING-DOCUMENT,WORKBOOK,WORKSHEET,WORKSHEET-TABLE,MAPPING-PROFILE,COLUMN-MAPPING,ACQUISITION-JOB,PDF-DOCUMENT,PDF-METADATA,DOCUMENT-CLASSIFICATION,PDF-ACQUISITION-JOB,ENGINEERING-MEDIA,MEDIA-METADATA,MEDIA-CLASSIFICATION,MEDIA-ACQUISITION-JOB}/` (16 directories) |
| `ADR/ADR-004-Engineering-Acquisition-Pattern.md` |
| `ADR/ADR_INDEX.md` |
| `ENGINEERING/MWO/MWO-LTSA-030-Mechanical-Seal-Knowledge-Manufacturing.md`, `-Completion-Report.md` |
| `ENGINEERING/MWO/MWO-LTSA-040A-Knowledge-Source-Registry.md`, `-Completion-Report.md` |
| `ENGINEERING/MWO/MWO-LTSA-040B-Engineering-Document-Acquisition.md`, `-Completion-Report.md` |
| `ENGINEERING/MWO/MWO-LTSA-040C-Universal-Tabular-Data-Acquisition.md`, `-Completion-Report.md` |
| `ENGINEERING/MWO/MWO-LTSA-040C-R1-Workbook-Acquisition-Pattern-Alignment.md` |
| `ENGINEERING/MWO/MWO-LTSA-040D-Engineering-PDF-Acquisition.md`, `-Completion-Report.md` |
| `ENGINEERING/MWO/MWO-LTSA-040E-Engineering-Media-Acquisition.md`, `-Completion-Report.md` |
| `ENGINEERING/MWO/EA-001-LTSA-Acquisition-Engineering-Audit-Report.md` |
| `ENGINEERING/MWO/RCA-001-RELEASE-Stub-Schema-Root-Cause-Analysis.md` |

**Basis:** `ADR_INDEX.md`'s only change is the `ADR-004` row, added during LTSA Acquisition governance work — exclusive to this milestone despite `ADR/` sounding EOPS-adjacent.

### EXCLUSIVE TO MWO-048 (UMC-001)

| File |
|---|
| `AI5R-SDK/FACTORY/CORE/universal_manufacturing_contract.py` |
| `AI5R-SDK/FACTORY/CORE/__init__.py` (modified) |
| `AI5R-SDK/FACTORY/RESOLUTION/identity_resolver.py` |
| `AI5R-SDK/FACTORY/RESOLUTION/relationship_resolver.py` |
| `AI5R-SDK/FACTORY/TESTS/test_universal_manufacturing_contract.py` |
| `AI5R-SDK/FACTORY/TESTS/test_identity_resolver.py` |
| `AI5R-SDK/FACTORY/TESTS/test_relationship_resolver.py` |
| `ENGINEERING/MWO/MWO-LTSA-048-Canonical-Manufacturing-Contract.md` |
| `ENGINEERING/MWO/MWO-LTSA-048-Completion-Report.md` |
| `ENGINEERING/MWO/EA-002-MWO-LTSA-048-Engineering-Audit.md` |
| `ENGINEERING/MWO/MA-001-Manufacturing-Audit-Report.md` |

### SHARED DOCUMENTATION

| File | Touched during |
|---|---|
| `CURRENT_STATE.md` | EOPS-001 (created), EOPS-002 (Governance FROZEN update), MWO-LTSA-048 (Current MWO update) |
| `CHANGELOG.md` | EOPS-001 (created, backfilled LTSA 030/040A–E history), MWO-LTSA-048 (new entry + backfilled EOPS-003/ARCH-REVIEW-001 entries) |
| `PROJECT_HISTORY.md` | EOPS-001 (created), MWO-LTSA-048 (new milestones added) |
| `ROADMAP.md` | EOPS-001 (created, backfilled LTSA history), MWO-LTSA-048 (moved to Completed, added Planned item) |
| `MEMORY.md` | EOPS-001 (created), MWO-LTSA-048 (two new frozen-decision entries) |

Each of these five was created once (EOPS-001) and extended at least once more (`MWO-LTSA-048`); several also carry LTSA Acquisition history that was *backfilled* into them by the EOPS-001 turn, not written by the original 040A–E implementation turns themselves (those turns predate these files' existence). No line in any of the five can be attributed to exactly one milestone without also touching lines attributable to another — they are genuinely interleaved, not merely co-located.

### DEFER (outside all three named milestones — not addressed by this plan)

| File | Why deferred |
|---|---|
| `AI5R-SDK/FACTORY/TESTS/test_manifest_loader.py` (M) | Pre-existing modification, predates this session (`RCA-001` finding) |
| `AI5R-SDK/MANUFACTURING_CENTER/TESTS/test_mfg_003b_execute_step.py`, `test_mfg_003b_step_creation.py` (M) | Unrelated portability fix (`/tmp` → `tempfile.gettempdir()`), flagged in `REPOSITORY_CLEANUP_AUDIT.md` §2 |
| `PRODUCTS/LTSA-BRAIN/RELEASE/{database.sql,openapi.json,schema.json}` (M) | Generated artifacts, `TD-001`, never to be committed per `RCA-002` |
| `ENGINEERING/MWO/MWO-P-001-LTSA-Product-Audit.md`, `MWO-P-006-Runtime-Verification-Infrastructure.md`, `MWO-P-006-Completion-Report.md`, `RV-004-Verification-Report.md` | Pre-existing MO-001-era documents, part of `COMMIT_PLAN.md`'s own separate Group 4 |
| `ENGINEERING/MWO/MWO-P-007-LTSA-Python-Adapter.md` | Identifier collision, determined **Superseded** in `EOPS-003` §4 — needs a status-line correction before it can be committed under any grouping |

None of these five items block or entangle the three named milestones' own commits — confirmed via `git status`, each sits in a directory untouched by any of the three.

---

## 2. Shared Documentation Strategy

**Recommendation: Option A wording applies — the five shared files remain in the latest commit, because their own Status lines already declare them "always reflects the current repository."**

Reasoning:
- `CURRENT_STATE.md`'s own header states: "Status: ACTIVE — always reflects the current repository. Must be updated after every completed MWO." This is not incidental phrasing — it is the file's stated purpose. A file whose entire reason to exist is "the current answer, not a history of past answers" cannot be meaningfully split into per-milestone historical slices without contradicting its own design.
- `CHANGELOG.md`, `PROJECT_HISTORY.md`, `ROADMAP.md`, `MEMORY.md` are additive logs by design (`DOCUMENTATION_CONTRACT.md`'s own table: "Records implementation changes only," "Records major milestones only," etc.) — their value is the complete, accumulated record, not a snapshot frozen at one milestone's boundary.
- Attempting to split them (e.g., committing `CHANGELOG.md` with only its EOPS-001-authored lines present, then a second commit adding only the LTSA lines, then a third adding only the `048` lines) would require **fabricating an intermediate file state that never actually existed as such** — the EOPS-001 turn's own version of `CHANGELOG.md` already included backfilled LTSA history in the same edit. Reconstructing a "pure EOPS-only" version of that commit would misrepresent what was actually written, when — precisely the "inaccurate repository history" this mission's own Objective warns against producing.

## 3. Recommended Commit Sequence

Consistent with, and not re-litigating, the granularity already recommended in `EA-001` §8 and `MWO-LTSA-048`'s own Completion Report — this plan adds the classification and shared-doc handling, it does not reopen those two documents' own internal sequencing:

1. **EOPS-001** — one commit: every file in the EOPS-exclusive table above.
2. **LTSA Acquisition v1.0** — internally six commits, per `EA-001` §8 (unchanged): `040A`, `040B`, `040C`, `040D`, `040E`, and one shared-schema/manifest commit (`CANONICAL_SCHEMA.sql` + `product.manifest.json`, cumulative across all five, not hunk-split — same reasoning as §2 applied at the schema-file level). A seventh commit bundles `ADR-004`/`ADR_INDEX.md`/`040C-R1`/`EA-001`/`RCA-001` as this milestone's own governance layer.
3. **MWO-LTSA-048** — one commit: every file in the 048-exclusive table above.
4. **Shared Documentation** — folded into commit 3 (the chronologically last of the three milestones), per §2. This keeps the total commit count at 8 (1 + 6 + 1) rather than introducing a ninth, purely-cosmetic "docs sync" commit.

**Total: 8 commits across the three named milestones.** This is the smallest set that (a) gives each MWO its own commit per the Constitution's "One MWO, one commit" rule, (b) does not force the two genuinely cumulative artifacts (shared docs, shared schema/manifest) into a false historical split, and (c) does not bundle unrelated milestones together.

---

## 4. Risks

| Risk | Mitigation |
|---|---|
| Folding shared docs into the `048` commit makes that commit's diff look larger than "just UMC-001" to a future reader of `git log`. | Low severity — the commit message can enumerate that it also carries the cumulative documentation sync, exactly as `MWO-LTSA-048-Completion-Report.md`'s own Commit Recommendation already does. |
| If `EOPS-001`'s commit is created *before* `LTSA Acquisition`'s, but `CHANGELOG.md`/`ROADMAP.md` (committed later, with `048`) already contain LTSA-epic entries, a reader diffing `EOPS-001`'s commit in isolation will see governance-only files with no contradiction — but the *shared docs* won't appear until the `048` commit, meaning `EOPS-001`'s own commit will not yet "prove" the LTSA entries it implies exist. | Accepted — this is the direct, unavoidable consequence of choosing Option A over Option B, disclosed here rather than hidden. If this is unacceptable, Option B (§5) is the alternative, at the cost described there. |
| The internal LTSA six/seven-commit sequence still carries the schema/manifest hunk-splitting caveat first raised in `EA-001` §8 (git shows it as 1–2 large hunks, not per-MWO). | Unchanged from `EA-001`'s own disclosure — not re-solved by this plan, since this mission's scope is classification and shared-doc strategy, not re-deriving `EA-001`'s own sequencing. |
| `MWO-P-007-LTSA-Python-Adapter.md`'s Superseded status-line correction (`EOPS-003` §4) is still outstanding — if committed later without that correction, it would carry a factually stale claim ("NO IMPLEMENTATION PERFORMED") into history. | Out of this plan's scope (it is in the DEFER bucket) — flagged again here so it is not forgotten before any future commit touches it. |

---

## 5. Decision: Option A vs. Option B

**Recommendation: Option A — keep cumulative documentation, create clean milestone commits for everything else.**

**Option B (split documentation historically) is rejected**, for one decisive reason: doing it correctly would require *inventing* file states that never existed in the working tree at any point — `CHANGELOG.md` was never, at any moment during this engagement, in a state containing only EOPS-001's own lines (it was created already containing backfilled LTSA history in the same edit that established it). Splitting it into "what EOPS-001 alone would have looked like" is not reconstructing history — it is fabricating a version of events that did not occur, which directly contradicts this mission's own instruction: **"Do not force separation if it would produce an inaccurate repository history."** Option A accepts a small, disclosed cost (§4, risk 2) in exchange for a `git log` that reflects what actually happened, in the order it actually happened, which is the more valuable property for a "clean engineering history" than perfect per-commit documentation isolation would be.

---

Stopping here as instructed. No file was modified, staged, or committed. Awaiting approval.
