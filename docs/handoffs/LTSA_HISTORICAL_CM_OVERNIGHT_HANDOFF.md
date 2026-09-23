# LTSA Historical CM — Overnight Handoff (RYZEN → Laptop)

Status: CHECKPOINT (overnight run 2026-09-23 → 2026-09-24, worker RYZEN)
Phase gate reached: `LTSA_PDF_CM_PARSER_GENERALIZATION_R1` complete; `LTSA_HISTORICAL_CM_PRODUCTION_RECONCILIATION` **not started** (blocked, see §4).

## 1. Checkpoint fields

| Field | Value |
|---|---|
| LAST_COMPLETED_PHASE | LTSA_PDF_CM_PARSER_GENERALIZATION_R1 (parser + tests + full archive dry run + validation + quarantine + manifests) |
| CURRENT_PHASE | LTSA_HISTORICAL_CM_PRODUCTION_RECONCILIATION — NOT STARTED (production read access denied by permission control) |
| SOURCE_PDFS_DISCOVERED | 37 (2025: 9, 2026: 28) — all text-based, all contain a CM section |
| SOURCE_CM_ROWS | 5,749 |
| PARSED_CM_ROWS | 5,000 |
| REJECTED_ROWS | 749 (all from the 6 HSC & SPK documents — NEW_ADAPTER_REQUIRED, raw rows preserved) |
| QUARANTINED_ROWS | 293 = 14 (HOC Jan 2026, dated `06-Jan-25`) + 279 (HCC Dec 2025 file stored in the HOC folder) |
| IMPORT-ELIGIBLE SOURCE ROWS | 4,707 (structural eligibility only — asset match / production dedupe DEFERRED) |
| YEARS_PROCESSED | 2025, 2026 |
| AREAS_PROCESSED | HCC, HOC, OM_UTL (parsed); HSC_SPK (discovered, quarantined) |
| MONTHS_PROCESSED | 2025-10, 2025-11, 2025-12, 2026-01 … 2026-07 (2026-05 = turnaround, no CM data in any area) |
| ALREADY_PRESENT | NOT_EVALUATED (reconciliation blocked) |
| SAFE_NEW | NOT_EVALUATED |
| IMPORTED | 0 |
| REMAINING_SAFE_NEW | NOT_EVALUATED |
| POTENTIAL_DUPLICATE | NOT_EVALUATED |
| CONFLICT | NOT_EVALUATED |
| TOTAL_CM_BEFORE | UNKNOWN — production not readable from RYZEN |
| TOTAL_CM_AFTER | UNKNOWN — unchanged by this run (no write attempted) |
| BACKUP_PATH | NONE — no production write was attempted, so no backup was taken |
| BACKUP_VERIFIED | N/A |
| IDEMPOTENCY_RESULT | NOT_RUN (no import) |
| PARSER_COMMIT | `3af4a464e22b506e1b58be3485d51a72ff8ffb58` |
| HANDOFF_COMMIT | the commit that adds this file (next commit after `3af4a464` on the same branch) |
| LOCAL_BRANCH | `feature/ltsa-historical-cm-pdf-parser-r1` (branched from `feature/ltsa-dashboard-diagram-r1` @ `975a167e`) |
| REMOTE_BRANCH | **NOT PUSHED** — `git push` was denied by the RYZEN session's permission control. The branch exists only on RYZEN. |
| REMOTE_HEAD | `origin/feature/ltsa-dashboard-diagram-r1` = `975a167e` (unchanged); `origin/feature/ltsa-historical-cm-pdf-parser-r1` does not exist yet |

Safety: SOURCE_MUTATED=NO · DATABASE_MUTATED=NO · PRODUCTION_MUTATED=NO · DATA_IMPORTED=NO · DEPLOYED=NO · OCR_USED=NO.

## 2. What was built (commit `3af4a464`)

All under `PRODUCTS/LTSA-BRAIN/INGESTION/`:

- `historical_cm_pdf_parser.py` — the canonical PDF CM parser. CM pages found by text markers; column identity from each page's own header words; cell bounds from the page's drawn table rules. Raw layer (literal cells, source labels, page/row provenance, SHA-256) + canonical layer (`condition_monitoring_reading` field names, `api_plan_snapshot`). Blank → NULL, leak Y/N/blank → true/false/NULL, no fill/copy/inference.
- `historical_cm_pdf_archive_dry_run.py` — read-only archive runner that writes the manifest/validation/occurrence artifacts.
- `TEST/test_historical_cm_pdf_parser.py` — synthetic geometry/semantics tests plus the OM & UTL Oct 2025 reference regression (skips when the source PDF is absent, e.g. on the laptop).
- `historical_pm_cmon_extraction.extract_cm_measuring_candidates()` — marked deprecated (DeprecationWarning), not deleted; it had no callers. It matched the new parser exactly on the reference report (123 rows, 0 value differences).

Reference regression (OM & UTL Oct 2025, SHA-256 `981221…e3bf`): 123 raw / 123 parsed / 0 rejected, rows 1..123 continuous, API plan 11/61=84 · 11/62=22 · 23/61=10 · 02=6 · 11/53=1, leak DE N=107/Y=11/NULL=5, leak NDE N=27/NULL=96. **PASS.**

Tests run on RYZEN:
- New parser tests: 45/45 pass (incl. reference regression).
- Existing ingestion tests (non-Docker): 164 pass, 2 skipped (pre-existing skips).
- `BACKEND-API/TESTS/test_historical_ingestion_dependency_closure.py`: pass.
- Docker-backed migration tests: could not run (Docker Desktop daemon not running on RYZEN).
- Pre-existing failures, reproduced on an untouched HEAD checkout and unrelated to this change: `test_pump_area_scope.py` (2), `test_basic_fleet_overview_service.py` (1), `test_historical_seal_service_activity.py` (2), `test_cmon_detailed_history.py` (collection error, `No module named 'API'`).

## 3. Archive results

Document classes: FORMAT_A_COMPATIBLE 27 · NEW_ADAPTER_REQUIRED 6 · NO_CM_DATA 4 · NO_CM_SECTION 0 · TEXT_EXTRACTION_UNSUPPORTED 0 · PARSER_FAILED 0.
Row numbering: no gaps and no duplicate row numbers in any parsed document. Distinct source tags (parsed): 207. Duplicate source files (same hash): none. Same tag+date across different eligible documents: none.

Coverage by area (docs / source rows / eligible rows): HCC 10 / 2,396 / 2,117 · HOC 10 / 1,414 / 1,400 · OM_UTL 10 / 1,190 / 1,190 · HSC_SPK 7 / 749 / 0.

| Year | Mo | Area | Class | CM pages | Raw | Parsed | Rej | Quar | Eligible | Tags | Date min | Date max | SHA-256 (12) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025 | 10 | HCC | FORMAT_A | 41-43 | 47 | 47 | 0 | 0 | 47 | 23 | 2025-10-01 | 2025-10-10 | 973cb69118ea |
| 2025 | 10 | HOC | FORMAT_A | 38-45 | 134 | 134 | 0 | 0 | 134 | 40 | 2025-10-08 | 2025-10-31 | a75011c13f50 |
| 2025 | 10 | OM_UTL | FORMAT_A | 40-45 | 123 | 123 | 0 | 0 | 123 | 31 | 2025-10-01 | 2025-10-31 | 981221136e52 |
| 2025 | 11 | HCC | FORMAT_A | 16-26 | 217 | 217 | 0 | 0 | 217 | 66 | 2025-11-03 | 2025-11-28 | 96d93fd9db94 |
| 2025 | 11 | HOC | FORMAT_A | 37-43 | 127 | 127 | 0 | 0 | 127 | 33 | 2025-11-03 | 2025-11-28 | 6a8fbb06d65f |
| 2025 | 11 | OM_UTL | FORMAT_A | 40-44 | 101 | 101 | 0 | 0 | 101 | 27 | 2025-11-03 | 2025-11-27 | 8d863ca93e4e |
| 2025 | 12 | HCC ⚠ | FORMAT_A | 16-29 | 279 | 279 | 0 | 0 | 0 | 64 | 2025-12-01 | 2025-12-31 | 01a657d22bdd |
| 2025 | 12 | HOC | FORMAT_A | 37-43 | 143 | 143 | 0 | 0 | 143 | 33 | 2025-12-03 | 2025-12-31 | 81abded376b1 |
| 2025 | 12 | OM_UTL | FORMAT_A | 40-45 | 117 | 117 | 0 | 0 | 117 | 26 | 2025-12-01 | 2025-12-30 | afdd384d3525 |
| 2026 | 01 | HCC | FORMAT_A | 21-37 | 322 | 322 | 0 | 0 | 322 | 99 | 2026-01-05 | 2026-01-29 | bc136f898b3c |
| 2026 | 01 | HOC ⚠ | FORMAT_A | 37-42 | 112 | 112 | 0 | 14 | 98 | 36 | 2025-01-06 | 2026-01-28 | 195687b8bad3 |
| 2026 | 01 | HSC_SPK | NEW_ADAPTER | 14-17 | 89 | 0 | 89 | 0 | 0 | 0 | - | - | 24ea11d4b4ce |
| 2026 | 01 | OM_UTL | FORMAT_A | 40-45 | 103 | 103 | 0 | 0 | 103 | 32 | 2026-01-05 | 2026-01-29 | 8eb2fead869b |
| 2026 | 02 | HCC | FORMAT_A | 21-37 | 351 | 351 | 0 | 0 | 351 | 98 | 2026-02-02 | 2026-02-27 | a5ba51f9fdfa |
| 2026 | 02 | HOC | FORMAT_A | 37-48 | 228 | 228 | 0 | 0 | 228 | 57 | 2026-02-03 | 2026-02-25 | 1760987b6e6c |
| 2026 | 02 | HSC_SPK | NEW_ADAPTER | 14-21 | 213 | 0 | 213 | 0 | 0 | 0 | - | - | 2400d514dab3 |
| 2026 | 02 | OM_UTL | FORMAT_A | 40-49 | 188 | 188 | 0 | 0 | 188 | 44 | 2026-02-03 | 2026-02-26 | 22ffcf0b5ae6 |
| 2026 | 03 | HCC | FORMAT_A | 21-36 | 324 | 324 | 0 | 0 | 324 | 98 | 2026-03-02 | 2026-03-30 | 71546e013917 |
| 2026 | 03 | HOC | FORMAT_A | 42-51 | 197 | 197 | 0 | 0 | 197 | 57 | 2026-03-03 | 2026-03-30 | 5bb8f32f2c70 |
| 2026 | 03 | HSC_SPK | NEW_ADAPTER | 14-19 | 163 | 0 | 163 | 0 | 0 | 0 | - | - | eee6158f5326 |
| 2026 | 03 | OM_UTL | FORMAT_A | 40-48 | 170 | 170 | 0 | 0 | 170 | 46 | 2026-03-02 | 2026-03-27 | e38e5c2a0e93 |
| 2026 | 04 | HCC | FORMAT_A | 21-39 | 395 | 395 | 0 | 0 | 395 | 99 | 2026-04-02 | 2026-04-30 | a0e29609a841 |
| 2026 | 04 | HOC | FORMAT_A | 42-52 | 223 | 223 | 0 | 0 | 223 | 56 | 2026-04-08 | 2026-04-27 | 0d528df5709d |
| 2026 | 04 | HSC_SPK | NEW_ADAPTER | 14-19 | 155 | 0 | 155 | 0 | 0 | 0 | - | - | 368b1ce63905 |
| 2026 | 04 | OM_UTL | FORMAT_A | 40-48 | 181 | 181 | 0 | 0 | 181 | 46 | 2026-04-01 | 2026-04-24 | f3e18d665683 |
| 2026 | 05 | HCC | NO_CM_DATA | 21 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | a526d7c43e02 |
| 2026 | 05 | HOC | NO_CM_DATA | 42 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | 67da20e2a98b |
| 2026 | 05 | HSC_SPK | NO_CM_DATA | 14 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | 2f797ea8bc3d |
| 2026 | 05 | OM_UTL | NO_CM_DATA | 40 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | 57a3714cd757 |
| 2026 | 06 | HCC | FORMAT_A | 21-30 | 182 | 182 | 0 | 0 | 182 | 91 | 2026-06-12 | 2026-06-29 | 9bc53e1fc1c1 |
| 2026 | 06 | HOC | FORMAT_A | 42-47 | 113 | 113 | 0 | 0 | 113 | 57 | 2026-06-15 | 2026-06-30 | ac12adbc3542 |
| 2026 | 06 | HSC_SPK | NEW_ADAPTER | 14-15 | 40 | 0 | 40 | 0 | 0 | 0 | - | - | 69ad5de34e5e |
| 2026 | 06 | OM_UTL | FORMAT_A | 47-51 | 91 | 91 | 0 | 0 | 91 | 39 | 2026-06-09 | 2026-06-25 | a9a04932db56 |
| 2026 | 07 | HCC | FORMAT_A | 21-35 | 279 | 279 | 0 | 0 | 279 | 102 | 2026-07-06 | 2026-07-29 | 6f4aa08bba29 |
| 2026 | 07 | HOC | FORMAT_A | 42-48 | 137 | 137 | 0 | 0 | 137 | 56 | 2026-07-01 | 2026-07-30 | d1b04bdef111 |
| 2026 | 07 | HSC_SPK | NEW_ADAPTER | 14-16 | 89 | 0 | 89 | 0 | 0 | 0 | - | - | 8efbeed554b4 |
| 2026 | 07 | OM_UTL | FORMAT_A | 47-52 | 116 | 116 | 0 | 0 | 116 | 39 | 2026-07-02 | 2026-07-31 | f8853c157073 |

### Quarantine register (decisions needed — nothing was "fixed")

1. **HSC & SPK, Jan–Apr, Jun, Jul 2026 (749 rows): NEW_ADAPTER_REQUIRED.** In the body of the table, each LBI / LBO / Cooling Water In / Cooling Water Out DE and NDE cell is split into two drawn sub-cells, but the header labels only DE/NDE. The paired XLSX has the same structure: merged DE/NDE header cells spanning two columns, with no sub-label. Mapping those values would be a guess. Example (Jan p14, row 21, 100-P-6B): LBI DE `43 | 47`, LBI NDE `41 | 47`. **Chief Architect decision needed on what the two sub-values mean** before any adapter is built. Jun/Jul also print "API PLAN" / "Mechanical Seal Leak" as squeezed fragments; the parser recognises those by exact letters, but that alone is not the blocker.
2. **`2025/HOC/…HCC DECEMBER 2025.pdf` (279 rows): folder says HOC, file name says HCC.** Evidence: all 64 of its tags appear in other HCC reports and none in HOC reports, and no other HCC Dec 2025 file exists. It is most likely a misfiled HCC report. It stays quarantined until you confirm, because any metadata warning quarantines the document.
3. **HOC Jan 2026, page 37, rows 1–14 (14 rows): dated `06-Jan-25` inside a January 2026 report.** This is probably a source typo for `06-Jan-26`. The date is kept as printed and quarantined; the parser never corrects it.
4. **May 2026, all 4 areas: NO_CM_DATA.** The CM table is empty with a large "TA" (turnaround) marker. Nothing to import.

### Source-precedence note for reconciliation

The existing `historical_pm_cmon_extraction.py` docstring records XLSX as the primary CM path when a matched XLSX exists. PDF CM extraction is the cross-validation path, and the only path when no XLSX exists. The archive has **no XLSX for 2025** (PDF is the only source) and **30 XLSX for 2026**, including two extra `Laporan PM (actual lapangan)…MARET` workbooks. The reconciliation gate must decide PDF vs XLSX precedence for 2026 before importing, so that the same row is never imported twice from two sources.

## 4. Why production phases (P4–P6) did not run

- The production read (`ssh ai5r` → `docker exec ai5ros-prod-postgres-1 psql`, read-only transaction) was **denied by the Claude Code permission classifier** on RYZEN. It was not retried or worked around.
- Without a production read, none of the required gates can be met: asset match, ALREADY_PRESENT/SAFE_NEW classification, verified backup, before/after counts, idempotency. So no production write was attempted.
- `git push` was also denied, so this work is **local to RYZEN**.

## 5. Artifacts (untracked, RYZEN only — regenerable)

In `d:\PROJECT\AI5R-RYZEN-LTSA\TEMP\` (not committed):
`ltsa_pdf_cm_archive_manifest.json`, `ltsa_pdf_cm_archive_manifest.csv`, `ltsa_pdf_cm_archive_validation.json`, `ltsa_pdf_cm_archive_occurrences.jsonl` (5,000 canonical occurrences with `import_eligible` / `quarantine_reasons`), `ltsa_pdf_cm_archive_raw_rows.jsonl` (5,749 raw rows), plus the earlier POC files `om_utl_oct2025_cm_*.json`.

The dry run is deterministic. Any machine with the source archive can regenerate the artifacts:

```
cd PRODUCTS/LTSA-BRAIN/INGESTION
python historical_cm_pdf_archive_dry_run.py --root "D:\PROJECT\Source-documents\LTSA\PM_CM_HISTORY" --years 2025 2026 --out "<repo>\TEMP"
```

## 6. REMAINING_WORK

1. Publish the branch: `git push -u origin feature/ltsa-historical-cm-pdf-parser-r1`. This needs the push permission that was denied overnight.
2. Chief Architect decisions: (a) meaning of the HSC & SPK sub-values (§3 item 1); (b) release of the misfiled HCC Dec 2025 file (item 2); (c) handling of the 14 `06-Jan-25` rows (item 3); (d) PDF vs XLSX precedence for 2026.
3. `LTSA_HISTORICAL_CM_PRODUCTION_RECONCILIATION`, with read-only production access authorised: classify the 207 source tags (EXACT_PUMP / EXACT_NON_PUMP / NOT_FOUND / AMBIGUOUS, reusing `match_pump_tag` and its curated DMI aliases), then classify the eligible occurrences (ALREADY_PRESENT / SAFE_NEW / POTENTIAL_DUPLICATE / CONFLICT) against `condition_monitoring_reading`.
4. SAFE_NEW import only under the defined gates: verified backup, exact asset match, SAFE_NEW only, transactional batches, no overwrite, post-import invariants, final idempotency dry run.
5. Optionally run the Docker-backed migration tests on a machine with Docker running.

## 7. EXACT_RESUME_INSTRUCTION

On **RYZEN** (the commits exist only here):

```
cd d:\PROJECT\AI5R-RYZEN-LTSA
git switch feature/ltsa-historical-cm-pdf-parser-r1
git log --oneline -3          # expect the handoff commit, then 3af4a464, then 975a167e
git push -u origin feature/ltsa-historical-cm-pdf-parser-r1
```

Then on the **laptop**:

```
git fetch origin
git switch feature/ltsa-historical-cm-pdf-parser-r1
python -m pytest PRODUCTS/LTSA-BRAIN/INGESTION/TEST/test_historical_cm_pdf_parser.py -q
# the reference regression skips unless LTSA_PM_CM_HISTORY_ROOT points at the source archive
```

Do not re-run parser generalization. Start at `LTSA_HISTORICAL_CM_PRODUCTION_RECONCILIATION` once the §6 item 2 decisions are made and read-only production access is authorised. Regenerate the TEMP artifacts with the §5 command if the laptop has the source archive; otherwise run reconciliation on RYZEN.
