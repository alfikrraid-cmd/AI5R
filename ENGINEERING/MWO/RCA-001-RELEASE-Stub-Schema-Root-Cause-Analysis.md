# RCA-001 — Root Cause Analysis: `RELEASE/` Stub Auto-Generated Tables

Status: Investigation complete. Read-only. No source code modified. No commit performed.
Requested by: Chief Architect, Root Cause Analysis mission (follow-up to EA-001 §2 WARNING finding)
Subject: `PRODUCTS/LTSA-BRAIN/RELEASE/{database.sql,schema.json,openapi.json}` containing stub, one-column tables for every `product.manifest.json` module

---

## 1. Executive Summary

The stub tables are produced by three **unit tests** — `AI5R-SDK/FACTORY/TESTS/{test_sql_generator,test_schema_generator,test_openapi_generator}.py` — that write directly to the **real, live** `PRODUCTS/LTSA-BRAIN/RELEASE/*` files instead of a temporary/fixture path. Every time any of these three tests runs (individually or via a bare `pytest`/`python -m pytest` from the repo root, which this repo's own `pytest.ini` configures to auto-discover them), it re-reads the current `product.manifest.json`, builds one column-less entity per enabled module, and overwrites the corresponding `RELEASE/*` file — regardless of whether any human or MWO asked for that. This is a **defect**: both a test-hygiene defect (a "unit test" with a real, permanent production-file side effect) and a symptom of an unfinished, unintegrated, and unauthorized parallel code-generation pipeline (`AI5R-SDK/FACTORY`, the "AI5R Digital Factory") that has no connection to, and was never invoked by, any of the MWO-LTSA-030/040A–040E work that actually built LTSA-BRAIN's real schema.

---

## 2. Who Generated Them — Exact Chain of Custody

```
product.manifest.json  (modules[])
        │
        ▼
AI5R-SDK/FACTORY/manifest_loader.py :: ManifestLoader.load()
        │  reads manifest.modules[], for every entry with enabled != false:
        │  creates EntityIR(name=module["name"], fields=[])   <- fields ALWAYS empty
        │  returns a CompilationUnit(product, entities=[...])
        ▼
AI5R-SDK/FACTORY/GENERATORS/sql_generator.py     :: SQLGenerator.run(unit, target)
AI5R-SDK/FACTORY/GENERATORS/schema_generator.py  :: SchemaGenerator.run(unit, target)
AI5R-SDK/FACTORY/GENERATORS/openapi_generator.py :: OpenAPIGenerator.run(unit, target)
        │  for each entity: table_name = f"ltsa_{entity.name.lower()}s"
        │  emits `CREATE TABLE IF NOT EXISTS {table_name} (id SERIAL PRIMARY KEY);`
        │  (schema/openapi generators emit the analogous stub JSON shape)
        ▼
Invoked by, and ONLY by, these three files:
  AI5R-SDK/FACTORY/TESTS/test_sql_generator.py      -> writes PRODUCTS/LTSA-BRAIN/RELEASE/database.sql
  AI5R-SDK/FACTORY/TESTS/test_schema_generator.py   -> writes PRODUCTS/LTSA-BRAIN/RELEASE/schema.json
  AI5R-SDK/FACTORY/TESTS/test_openapi_generator.py  -> writes PRODUCTS/LTSA-BRAIN/RELEASE/openapi.json
```

Verbatim from `test_sql_generator.py` (the other two are structurally identical, differing only in generator class and assertions):

```python
manifest_path = Path("PRODUCTS/LTSA-BRAIN/product.manifest.json")
output_path = Path("PRODUCTS/LTSA-BRAIN/RELEASE/database.sql")

loader = ManifestLoader()
unit = loader.load(str(manifest_path))

generator = SQLGenerator()
sql = generator.generate(unit, str(output_path))   # <-- writes the REAL file, not a tmp path
```

There is no fixture, no `tmp_path`, no mock — `output_path` is the actual product path. Every run overwrites it with whatever `product.manifest.json` currently contains.

**Confirmed this is the only mechanism.** A repo-wide search for any other reference to `RELEASE/database.sql`, `RELEASE/schema.json`, `RELEASE/openapi.json`, or the `"Auto Generated"` marker string found no other producer. `AI5R-SDK/FACTORY/MANUFACTURING/service.py` (the CLI's `factory build <product>` path) is a **separate, unrelated** generation system — it targets `PRODUCTS/<product>/BUILD-PACKS/BP-<module>/*` using a different, hand-rolled SQL/workflow template and a tiny, separate registry (`AI5R-SDK/FACTORY/REGISTRY/MODULES/{PUMP,SEAL}.json` — only 2 entries, not connected to `product.manifest.json` at all, and containing none of the 040-series modules). `factory.py`/`factory_cli.py`/`ManufacturingService` never call `ManifestLoader`, `SQLGenerator.run()`, `SchemaGenerator.run()`, or `OpenAPIGenerator.run()` — those four classes' `run()`/`generate()` methods (the ones with the `unit`/`target` signature that actually produced the RELEASE/* stubs) are called **only** from the three test files above and their own unit test blocks. This was verified by grepping every `.py` file under `AI5R-SDK` for references to these four class names outside `TESTS/`; none exist.

**`RELEASE/workflow.json` and `RELEASE/release.json` are a separate, unexplained case.** No test file, no generator invocation, and no code path anywhere in the current repository references either path (`workflow_generator.py`'s `WorkflowGenerator` and `release_generator.py`'s `ReleaseGenerator` classes exist but are not called from any test, CLI command, or other module — they are entirely orphaned code). These two files are most plausibly leftover output from a manual, ad hoc invocation of those generator classes in an earlier session (e.g. a Python REPL or a one-off script), not from a reproducible, currently-live mechanism. This RCA does not claim to know their origin with the same confidence as the three files traced above — stated honestly, not guessed.

## 3. When and How (Trigger)

- `pytest.ini` at the repo root sets `testpaths = AI5R-SDK` and `python_files = test_*.py` — meaning **a bare `pytest` or `python -m pytest` invocation from the repository root, with no arguments or path filter, auto-discovers and executes all three side-effecting tests** as an ordinary part of the suite. No special flag, CI job, or hook is required to trigger this — it is pytest's *default* behavior given this repo's own config.
- File `mtime` evidence: `RELEASE/database.sql`, `schema.json`, and `openapi.json` were all last written at `2026-07-14 23:07:27`, **exactly one write batch** (all three within 6 seconds of each other, consistent with a single test-suite run executing all three tests back to back) — **15 minutes after** `product.manifest.json`'s own last edit at `22:52:28` (the MWO-LTSA-040E manifest update performed earlier in this same session).
- This assistant's own actions during MWO-LTSA-040D/040E implementation (traceable in this conversation) never invoked `pytest`, `python -m pytest`, `factory.py`, or `factory_cli.py` — only `bash -n`, direct `python3 -c "import json..."` parsing, and bounded `psql` connection attempts were run. The 23:07:27 regeneration was **not caused by any tool call visible in this conversation.**
- **The specific invoking actor/process cannot be determined from repository state alone.** The evidence conclusively identifies *what* ran (the three test files, most likely via a bare `pytest` collection run) and *why* it had this effect (their hard-coded real-path writes), but not *who or what process* issued that command in the ~15-minute window — that would require shell history or process-level logging outside what a repository-state investigation can observe. Stated as a limitation, not filled in with a guess.
- Corroborating, not conclusive: `.claude/settings.local.json` already allow-lists `Bash(python -m pytest --version)` — confirming `pytest` is a tool actively used against this repository in prior sessions, consistent with (but not proof of) a full suite run being the trigger.
- Further corroborating evidence found during this investigation (pre-existing, not caused by this RCA — confirmed via `git diff`, and this RCA only read the file): `AI5R-SDK/FACTORY/TESTS/test_manifest_loader.py` is also a tracked, committed-baseline file currently showing an uncommitted change, where its assertion `unit.metadata["product"]["display_name"] == "LTSA Brain"` was edited to `== "OSA Maintenance"` — i.e. **updated to match `product.manifest.json`'s actual current value**, rather than the manifest being kept consistent with a fixed test expectation. This shows the same `AI5R-SDK/FACTORY/TESTS/` suite has a standing pattern of being reactively adjusted to track live manifest drift, not run against a pinned fixture — the same structural property that let `test_sql_generator.py` et al. silently absorb all 15 new 040-series module names without any assertion failing.

## 4. Is This Expected or a Defect?

**Defect.** Reasoned against the Constitution (`CONSTITUTION/13_ENGINEERING_EXECUTION_PROTOCOL.md`) and `ADR-000`'s governance model:

1. **Tests must not have production side effects.** A "unit test" that permanently overwrites a real product's release artifacts on every run is a test-design defect independent of anything else — this would be flagged in any engineering review regardless of what the generator itself is trying to do.
2. **No architecture or MWO authorizes this.** None of `ADR-000` through `ADR-004`, the Engineering Standard, or any of MWO-LTSA-030/040A–040E's own Scope/Deliverables sections mentions `AI5R-SDK/FACTORY`, `ManifestLoader`, or any of the four generator classes. Per the Constitution's Canonical Rule ("There must be exactly ONE canonical implementation... If canonical ambiguity appears: STOP. Report. Wait. Do not decide"), a second, un-decided schema representation silently appearing alongside the real one is exactly the condition that rule exists to prevent — it happened by accident, not by decision.
3. **The generator is structurally incapable of being a real release artifact today.** `ManifestLoader.load()` hard-codes `fields=[]` for every entity — it never reads column/constraint data from `CANONICAL_SCHEMA.sql`, any BUILD-PACK's `SCHEMAS/*.schema.json`, or anywhere else. Even if this pipeline were intentionally wired into the release process, it cannot currently produce anything beyond `id SERIAL PRIMARY KEY` stubs, so it could not have been "working as designed" toward a real release artifact — there is no design path from its current inputs to real output.
4. **Naming does not correspond to the real schema.** `f"ltsa_{name.lower()}s"` naive pluralization produces a name that matches neither the real canonical table (e.g. `public.knowledge_source_registry`, no `ltsa_` prefix, already correctly singular) nor correct English (`ltsa_knowledge_source_registrys`). Even read as documentation, these files describe tables that do not exist under those names anywhere else in the product.
5. This is best characterized as **orphaned technical debt from a separate, incomplete platform-level initiative** (`AI5R-SDK/FACTORY`, the "AI5R Digital Factory" — evidently a real, in-progress effort per its FM-xxx spec numbering and substantial test coverage) whose test suite happens to collide with LTSA-BRAIN's real release directory, not an intentional, approved piece of this product's release architecture.

## 5. Recommended Correct Architecture (analysis only — not implemented by this RCA)

1. **Immediate test-hygiene fix (low-risk, mechanical):** change the three tests to write to pytest's `tmp_path` fixture (or any non-product-tree temp location) instead of the real `PRODUCTS/LTSA-BRAIN/RELEASE/*` paths. This alone stops all future silent regeneration without touching any generator's logic or any product file. (Same fix should be applied to any other `AI5R-SDK/FACTORY/TESTS/*` file found writing to a real path — this RCA checked the three confirmed offenders; a full audit of the remaining ~20 test files in that directory was not performed and is a reasonable next investigation, not assumed clean.)
2. **Architectural decision required, at ADR level, on the Digital Factory's relationship to LTSA-BRAIN release artifacts** — per `ADR-000` §2, this is exactly the kind of ownership/dependency-direction question an ADR exists to resolve, not something to infer from test behavior. Two honest options for the Chief Architect to choose between, not decided here:
   - **(a) Retire/quarantine:** `RELEASE/database.sql`, `schema.json`, `openapi.json` (and the `workflow.json`/`release.json` files of unknown origin) are not part of this product's real release process; mark the whole `RELEASE/` stub path deprecated or remove the three generator invocations, and treat `CANONICAL_SCHEMA.sql` + each BUILD-PACK's own `SCHEMAS/*.json` as the only canonical release-adjacent artifacts.
   - **(b) Integrate properly:** if a generated release rollup is genuinely wanted, `ManifestLoader` must be redesigned to source real field/constraint data (from `CANONICAL_SCHEMA.sql` or each module's own `SCHEMAS/*.schema.json`), and the naming convention must be reconciled with the real canonical table names — this is nontrivial new work, not a one-line fix, and would need its own MWO once the ADR decision is made.
3. Until that decision is made, recommend `RELEASE/*` be excluded from routine `git status`-based scope checks (e.g. via `.gitignore` or a clear README note marking it non-canonical/experimental) so it stops appearing as ambiguous noise in future audits — this is a documentation/hygiene recommendation, not a code change, and is not being performed by this RCA.

## 6. Scope Note — What This RCA Confirms About the 040-Series Work

This finding does not implicate any of MWO-LTSA-030/040A–040E. None of their Completion Reports claim, reference, or depend on `RELEASE/*`; the real, canonical, hand-authored schema those MWOs produced lives entirely in `CANONICAL_SCHEMA.sql` and each `BUILD-PACKS/BP-*` directory, independently of this generator. The stub files are a parallel, accidental artifact — evidence of a defect elsewhere in the repository, not of any defect in the Engineering Knowledge Acquisition work EA-001 already reviewed.

---

Stopping here as instructed. No source code was modified, nothing was deleted, nothing was committed. Awaiting review.
