# RCA-002 — Generated Artifacts Policy

Status: Analysis complete. Policy recommendation only. No source code modified. No commit performed.
Requested by: Chief Architect — EOPS-003 Repository Hygiene mission, Task 1
Scope: Every generated (non-hand-authored) artifact found in the repository, classified and given a commit-worthiness recommendation.

---

## Classification Legend

- **Source** — hand-authored, the canonical origin of truth for its subject.
- **Generated** — mechanically produced from a Source artifact by a script/tool/test.
- **Temporary** — produced as a side effect of running something (a test, a build), with no standing purpose once produced.
- **Commit-worthy** — should be tracked in git regardless of how it was produced (e.g., a generated artifact that IS the deliverable).
- **Ignore** — should not be tracked in git (regenerable, or not meaningful outside the machine/run that produced it).

---

## 1. `PRODUCTS/LTSA-BRAIN/RELEASE/{database.sql,schema.json,openapi.json}`

- **Classification:** Generated, Temporary, **Ignore**.
- **Origin (from `RCA-001`):** three unit tests — `AI5R-SDK/FACTORY/TESTS/{test_sql_generator,test_schema_generator,test_openapi_generator}.py` — write directly to these real product paths on every bare `pytest` run, reading `product.manifest.json` and emitting one column-less `id SERIAL PRIMARY KEY` stub table/schema-entry per manifest module.
- **Why not Commit-worthy:** they are not the canonical schema (`CANONICAL_SCHEMA.sql` and each BUILD-PACK's own `SCHEMAS/*.schema.json` are), they are not reviewed or authored by any MWO, and their content is fully re-derivable at any time by re-running the three tests against the current manifest — the definition of a regenerable artifact. Committing them risks a reader mistaking them for real schema (the exact duplication risk `EA-001` flagged).
- **Recommendation:** exclude from every commit; add to `.gitignore` (see `GITIGNORE-RECOMMENDATION.md`). The underlying test-hygiene defect (`TD-001`) remains open pending a separate Chief Architect decision on whether this generation pipeline should be retired or properly redesigned.

## 2. `PRODUCTS/LTSA-BRAIN/RELEASE/{release.json,workflow.json}`

- **Classification:** Generated (unconfirmed exact origin), **Ignore**.
- **Origin:** no live code path in the current repository was found that produces either file (`RCA-001` §2 already noted this). `AI5R-SDK/FACTORY/GENERATORS/{release_generator,workflow_generator}.py` define classes capable of producing this shape, but neither is called from any test, CLI command, or other module today — they are orphaned code. Most plausibly, an earlier, manual invocation of those classes (a REPL session or one-off script) produced these two files and they were never cleaned up.
- **Recommendation:** same as item 1 — exclude, `.gitignore`. If the Chief Architect later authorizes properly integrating the Digital Factory release pipeline (`RCA-001` §5 option b), these two files' real generation path should be re-established deliberately at that time, not left as unexplained leftovers.

## 3. `BUILD/RUN-*` (162 directories + matching `.zip` files, 819 files, ~913 KB)

- **Classification:** Generated, Temporary, **Ignore**.
- **Origin:** each `RUN-<hash>` directory contains a near-identical generated FastAPI application scaffold (`app/main.py`, `app/routers/auth.py`, `app/schemas.py`, `openapi.json`, `tests/`, `README.md`, `requirements.txt`), paired with a `.zip` of the same content. This is the output shape of a code-generation/build-run process executed many times (162 runs) — not hand-authored source, and not a single deliverable but an accumulation of historical runs.
- **Recommendation:** exclude from every commit; add `BUILD/` to `.gitignore`. If any single run's output is actually wanted as a real deliverable, it should be promoted deliberately (copied to a named, permanent location under the relevant product or `AI5R-SDK/FACTORY`), not left inside a directory whose own naming convention (`RUN-<hash>`) signals disposability.

## 4. Generated OpenAPI / SQL / Schema files inside `BUILD-PACKS/*/SCHEMAS/*.json` and `*/DATABASE/*.sql` (all 040-series and prior build packs)

- **Classification:** **Source** (despite being "generated" in the sense of being written by an engineer following a template), **Commit-worthy**.
- **Distinction from items 1–3:** these files were authored by hand, per an approved MWO, following a proven, human-reviewed pattern (cloned from `BP-SEAL`'s shape, per the Engineering Standard's Canonicalization Standard) — not mechanically produced from `product.manifest.json` or any other single source of truth. Each one carries real column/constraint/CRUD-operation content matching its table's actual canonical definition, verified structurally (`bash -n`, JSON parse) and cross-checked against `CANONICAL_SCHEMA.sql` during each MWO's own validation (`EA-001` §4/§6).
- **Recommendation:** commit as part of their respective MWO's own commit (per `COMMIT_PLAN.md` Groups 2–4). These are exactly the kind of generated-looking-but-actually-authored artifact that should **not** be confused with items 1–3 above — the test for the difference is provenance (an approved MWO vs. an unreviewed test side effect), not surface appearance.

## 5. `.bak` files found in the repository

- **`AI5R-SDK/FACTORY/MANUFACTURING/service.py.bak`, `service.py.fm0015.bak`** — **already committed to git history** (confirmed via `git ls-files`), zero current diff. Classification: **Temporary, should never have been Commit-worthy**, but is already committed — this is existing repo debt, not new uncommitted work. No action taken by this analysis (out of scope: this mission produces policy and recommendations only, not remediation of already-committed history).
- **`claude_desktop_config.json.bak.json`** (repo root, untracked) — machine-local application config backup, covered in `REPOSITORY_CLEANUP_AUDIT.md` §5. Classification: **Temporary, Ignore.**
- **Recommendation:** add a `*.bak` / `*.bak.*` pattern to `.gitignore` going forward (see `GITIGNORE-RECOMMENDATION.md`) so future `.bak` files are never accidentally tracked again. Whether to purge the two already-committed `.bak` files from history is a separate, more invasive decision (rewriting tracked history) — flagged as a `TECHNICAL_DEBT.md` candidate, not decided here.

---

## Policy Going Forward (recommendation, not enacted)

1. **Any artifact whose content is a deterministic function of another file already in this repository, and which is not the reviewed, canonical output of an approved MWO, should never be committed.** This is the single rule that distinguishes items 1–3 (Ignore) from item 4 (Commit-worthy) above.
2. **A test must never write to a real product path.** This is the root cause of items 1–2 and should be fixed at the source (`TD-001`) rather than managed indefinitely through `.gitignore`.
3. **Any directory whose own naming convention signals disposability** (`RUN-<hash>`, `*.tmp`, `*.bak`) **should be gitignored by pattern**, not evaluated file-by-file as it grows.
4. **Promotion path:** if a generated artifact is ever genuinely wanted as a permanent deliverable, it must be copied to a deliberately-named, permanent location and reviewed like any other MWO output — never left in place inside a generated-output directory and committed from there.

---

Stopping here as instructed. No file was modified, deleted, or committed in producing this analysis.
