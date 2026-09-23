# LTSA Historical CM — Overnight Handoff (RYZEN → Laptop)

Status: FINAL CHECKPOINT (overnight run 2026-09-23 → 2026-09-24, worker RYZEN)
Phase gate reached: `LTSA_HISTORICAL_CM_RYZEN_FINAL_CHECKPOINT_R1`: parser generalization complete, branch pushed, **read-only** production reconciliation complete. No production write of any kind.
Next gate: `LTSA_HISTORICAL_CM_CONTROLLED_PRODUCTION_IMPORT` (laptop), after the decisions in §6.

## 1. Checkpoint fields

| Field | Value |
|---|---|
| LAST_COMPLETED_PHASE | LTSA_HISTORICAL_CM_RYZEN_FINAL_CHECKPOINT_R1 (push + source decisions + PDF/XLSX + asset + occurrence reconciliation, all read-only) |
| CURRENT_PHASE | none running; next = LTSA_HISTORICAL_CM_CONTROLLED_PRODUCTION_IMPORT |
| SOURCE_PDFS_DISCOVERED | 37 (2025: 9, 2026: 28) — all text-based, all contain a CM section |
| TOTAL_SOURCE_ROWS | 5,749 |
| PARSED_ROWS | 5,000 |
| EXTRACTION_REJECTED (initial rejected) | 749 — all HSC & SPK. These same 749 rows are the SEMANTIC_QUARANTINE (not a second count). |
| SEMANTIC_QUARANTINE | 749 — HSC & SPK, classified SEMANTIC_MAPPING_REQUIRED; raw evidence preserved |
| AREA_SOURCE_CONFLICT | 279 (HCC Dec 2025 file stored under the HOC folder) |
| DATE_CONTEXT_CONFLICT | 14 (HOC Jan 2026, raw_date `06-Jan-25`) |
| STRUCTURALLY_ELIGIBLE | 4,707 (= 5,000 − 279 − 14) |
| PDF_XLSX: SAME_OCCURRENCE_MATCH / COMPLEMENT / SOURCE_CONFLICT / PDF_ONLY / XLSX_ONLY | 3,712 / 0 / 0 / 1,288 (all 2025; no 2025 XLSX exists) / 0 |
| ASSET (207 distinct eligible tags): EXACT_PUMP / EXACT_NON_PUMP / NOT_FOUND / AMBIGUOUS | 202 / 2 / 2 / 1 |
| ALREADY_PRESENT | 1,748 |
| SAFE_NEW | 2,907 |
| POTENTIAL_DUPLICATE | 10 |
| CONFLICT | 0 |
| NOT_IMPORTABLE (asset gate) | 42 = 27 NOT_FOUND + 12 EXACT_NON_PUMP + 3 AMBIGUOUS |
| IMPORTED | 0 |
| REMAINING_SAFE_NEW | 2,907 |
| **PRODUCTION_DATA_CONFLICT** | **244 existing production rows (HSC & SPK Apr + Jul 2026) are column-shifted** — see §4 |
| TOTAL_CM_BEFORE | 2,092 (production `condition_monitoring_reading`, 0 soft-deleted; read 2026-09-24 ~05:00) |
| TOTAL_CM_AFTER | 2,092 (unchanged — no write) |
| BACKUP_PATH | NONE — no write attempted; the import gate must take and verify its own backup |
| BACKUP_VERIFIED | N/A |
| IDEMPOTENCY_RESULT | NOT_RUN (no import) |
| PARSER_COMMIT | `3af4a464e22b506e1b58be3485d51a72ff8ffb58` |
| HANDOFF_COMMIT | `0764603b` (first version); this final update is the next commit on the branch |
| BRANCH | `feature/ltsa-historical-cm-pdf-parser-r1` (branched from `feature/ltsa-dashboard-diagram-r1` @ `975a167e`) |
| REMOTE_BRANCH | `origin/feature/ltsa-historical-cm-pdf-parser-r1` — pushed (push approved 2026-09-24) |
| REMOTE_HEAD | equals local HEAD after the final push; verify with `git ls-remote --heads origin feature/ltsa-historical-cm-pdf-parser-r1` |

Safety: SOURCE_MUTATED=NO · DATABASE_MUTATED=NO · PRODUCTION_MUTATED=NO · DATA_IMPORTED=NO · DEPLOYED=NO · OCR_USED=NO.
Production access was read-only only: the session was set to `default_transaction_read_only=on`, and only `SELECT` statements were run against `asset_registry` and `condition_monitoring_reading`.

## 2. What was built (commit `3af4a464`)

All under `PRODUCTS/LTSA-BRAIN/INGESTION/`:

- `historical_cm_pdf_parser.py` — the canonical PDF CM parser. CM pages found by text markers; column identity from each page's own header words; cell bounds from the page's drawn table rules. Raw layer (literal cells, source labels, page/row provenance, SHA-256) + canonical layer (`condition_monitoring_reading` field names, `api_plan_snapshot`). Blank → NULL, leak Y/N/blank → true/false/NULL, no fill/copy/inference.
  - Guards: pages whose body has unlabelled sub-columns are rejected (NEW_ADAPTER_REQUIRED); rows dated outside the report period are quarantined; empty "TA" pages are classified NO_CM_DATA.
- `historical_cm_pdf_archive_dry_run.py` — read-only archive runner that writes the manifest/validation/occurrence artifacts.
- `TEST/test_historical_cm_pdf_parser.py` — synthetic geometry/semantics tests plus the OM & UTL Oct 2025 reference regression (skips when the source PDF is absent).
- `historical_pm_cmon_extraction.extract_cm_measuring_candidates()` — marked deprecated, not deleted; it had no callers. It matched the new parser exactly on the reference report.

Reference regression (OM & UTL Oct 2025, SHA-256 `981221…e3bf`): 123 raw / 123 parsed / 0 rejected, rows 1..123 continuous, API plan 11/61=84 · 11/62=22 · 23/61=10 · 02=6 · 11/53=1, leak DE N=107/Y=11/NULL=5, leak NDE N=27/NULL=96. **PASS.**

Tests on RYZEN:
- New parser tests: 45/45 pass.
- Existing ingestion tests (non-Docker): 164 pass, 2 skipped.
- `BACKEND-API/TESTS/test_historical_ingestion_dependency_closure.py`: pass.
- Docker-backed migration tests: not runnable (Docker daemon down).
- Pre-existing failures, reproduced on an untouched HEAD checkout and unrelated to this change: `test_pump_area_scope.py`, `test_basic_fleet_overview_service.py`, `test_historical_seal_service_activity.py`, `test_cmon_detailed_history.py` (collection error).

## 3. Archive and reconciliation results

Document classes: FORMAT_A_COMPATIBLE 27 · NEW_ADAPTER_REQUIRED 6 (HSC & SPK) · NO_CM_DATA 4 (May 2026 turnaround "TA") · NO_CM_SECTION 0 · TEXT_EXTRACTION_UNSUPPORTED 0 · PARSER_FAILED 0.
- No row-number gaps or duplicate row numbers in any parsed document.
- No duplicate source files, and no tag+date collisions across documents.

Coverage by area (docs / source rows / structurally eligible): HCC 10 / 2,396 / 2,117 · HOC 10 / 1,414 / 1,400 · OM_UTL 10 / 1,190 / 1,190 · HSC_SPK 7 / 749 / 0.

| Year | Mo | Area | Class | CM pages | Raw | Parsed | Rej | Quar | Eligible | Tags | Date min | Date max | SHA-256 (12) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025 | 10 | HCC | FORMAT_A | 41-43 | 47 | 47 | 0 | 0 | 47 | 23 | 2025-10-01 | 2025-10-10 | 973cb69118ea |
| 2025 | 10 | HOC | FORMAT_A | 38-45 | 134 | 134 | 0 | 0 | 134 | 40 | 2025-10-08 | 2025-10-31 | a75011c13f50 |
| 2025 | 10 | OM_UTL | FORMAT_A | 40-45 | 123 | 123 | 0 | 0 | 123 | 31 | 2025-10-01 | 2025-10-31 | 981221136e52 |
| 2025 | 11 | HCC | FORMAT_A | 16-26 | 217 | 217 | 0 | 0 | 217 | 66 | 2025-11-03 | 2025-11-28 | 96d93fd9db94 |
| 2025 | 11 | HOC | FORMAT_A | 37-43 | 127 | 127 | 0 | 0 | 127 | 33 | 2025-11-03 | 2025-11-28 | 6a8fbb06d65f |
| 2025 | 11 | OM_UTL | FORMAT_A | 40-44 | 101 | 101 | 0 | 0 | 101 | 27 | 2025-11-03 | 2025-11-27 | 8d863ca93e4e |
| 2025 | 12 | HCC ⚠ area | FORMAT_A | 16-29 | 279 | 279 | 0 | 279 | 0 | 64 | 2025-12-01 | 2025-12-31 | 01a657d22bdd |
| 2025 | 12 | HOC | FORMAT_A | 37-43 | 143 | 143 | 0 | 0 | 143 | 33 | 2025-12-03 | 2025-12-31 | 81abded376b1 |
| 2025 | 12 | OM_UTL | FORMAT_A | 40-45 | 117 | 117 | 0 | 0 | 117 | 26 | 2025-12-01 | 2025-12-30 | afdd384d3525 |
| 2026 | 01 | HCC | FORMAT_A | 21-37 | 322 | 322 | 0 | 0 | 322 | 99 | 2026-01-05 | 2026-01-29 | bc136f898b3c |
| 2026 | 01 | HOC ⚠ date | FORMAT_A | 37-42 | 112 | 112 | 0 | 14 | 98 | 36 | 2025-01-06 | 2026-01-28 | 195687b8bad3 |
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

### Source decisions (Chief Architect, 2026-09-24) — applied, nothing mutated or corrected

- **HSC & SPK, 749 rows → SEMANTIC_MAPPING_REQUIRED.**
  - Why: in the PDF, each LBI / LBO / Cooling Water In / Out DE and NDE cell is split into two sub-cells. The paired XLSX has merged DE/NDE headers spanning two columns with no sub-label.
  - Handling: nothing collapsed, no sub-value selected, raw rows preserved.
- **HCC Dec 2025 under HOC, 279 rows → AREA_SOURCE_CONFLICT.**
  - Evidence: folder_area=HOC; document_area=HCC (file name); 64/64 tags occur in HCC reports and 0 in HOC reports.
  - Handling: excluded from automatic import.
- **HOC Jan 2026, 14 rows → DATE_CONTEXT_CONFLICT.**
  - Evidence: raw_date=`06-Jan-25`, REPORT_PERIOD=JAN_2026, SOURCE_DATE_YEAR=2025.
  - Handling: excluded from automatic import.
- **PDF vs XLSX precedence.** XLSX is primary when the same occurrence exists in validated XLSX; the PDF is documentary evidence and never creates a second occurrence.

### PDF ↔ XLSX (2026)

18 paired workbooks were compared (HCC / HOC / OM_UTL × Jan–Apr, Jun, Jul).
- Each workbook's `CM Measuring Report` header was checked as FORMAT_A (DE/NDE in columns E..V) before its rows were projected with the existing `ltsa_hoc_pm_cm_ingestion.project_cm_reading_rows`.
- **All 3,712 parsed 2026 PDF rows matched their XLSX row exactly** (same normalized tag, date and all 20 measurement fields). 0 complements, 0 conflicts, 0 XLSX_ONLY. This independently cross-validates the PDF parser.
- Not compared: HSC & SPK (quarantined), May (no data), and the two extra `Laporan PM (actual lapangan)…MARET` workbooks (not used).

### Assets (207 distinct eligible tags vs production `asset_registry`, 257 rows)

Exact match after whitespace/case typography only:
- EXACT_PUMP: 202.
- EXACT_NON_PUMP: 2 (`701-MM-51`, `702-MM-51`). They exist with an empty `asset_type`, and PUMP is never inferred.
- NOT_FOUND: 2 (`DMI-P-201A`, `DMI-P-201B`). The registry holds `P-201A-DMI` / `P-201B-DMI`, and a curated alias exists in `historical_pm_cmon_extraction._KNOWN_ASSET_ALIASES`, but it was **not applied** (no auto-correction).
- AMBIGUOUS: 1 (`140-P-3B`: only `140-P-3A` exists, a suffix near-miss).

### Occurrences (4,707 structurally eligible vs production `condition_monitoring_reading`, 2,092 rows)

Key = registry asset code + reading date, then a comparison of the 20-field measurement fingerprint.
- ALREADY_PRESENT **1,748** (identical values).
- SAFE_NEW **2,907** (EXACT_PUMP, no production row for that asset/date, unique within the candidate set).
  - By month: 2025-10 297 · 2025-11 443 · 2025-12 257 · 2026-01 205 · 2026-02 751 · 2026-03 685 · 2026-06 269.
  - By source: 997 PDF-only (2025) · 1,910 PDF+XLSX identical (2026).
- POTENTIAL_DUPLICATE **10**: the same tag twice on one date inside one report (212-P-7A 2025-11-21 rows 150/158; OM & UTL Feb 2026 2026-02-23 for DMI-P-201A/B and 945-P-7A/B). Never auto-picked.
- CONFLICT **0**.
- NOT_IMPORTABLE **42** (asset gate).

## 4. Production data conflict found (Chief Architect decision required)

**244 existing production rows are column-shifted.**
- Which rows: exactly all 155 HSC & SPK April 2026 rows and all 89 HSC & SPK July 2026 rows.
- Provenance: each has `provenance=HISTORICAL_IMPORT`, `workflow_status=DRAFT` and `source_reference=document_field_extraction:DFE-…`.
- Cause: the earlier document-extraction import mapped the unlabelled HSC sub-values across the wrong columns.

Example: `CMONR-80F9A4B9F4F4` (100-P-6B, 2026-04-01).
- The source row has LBI DE `47|44`, LBI NDE `43|55`, LBO `45|52`/`41|65`, mechseal 69/80, suction 218, discharge 229, Status `Standby`.
- Production has `flushing_in_temp_de/nde`=47/44, `flushing_out_temp_de/nde`=43/55, `cooling_water_in_temp_*`=45/52, `cooling_water_out_temp_*`=41/65, `suction_temp`=45, `discharge_temp`=45 and **`pump_operating_state`='69'** (the mechseal DE value).

Detector: a numeric `pump_operating_state` flags exactly these 244 rows. **Not modified** (read-only phase). Correcting them needs its own MWO, a backup and approval.

Also not yet explained: 41 other April 2026 HISTORICAL_IMPORT production rows that no archive candidate matches. The 59 MANUAL/WHATSAPP rows (Jun/Aug 2026) are expected not to match.

## 5. Access history and artifacts

- The first read-only production attempt and the first `git push` were denied by the permission classifier and not retried. Both were explicitly approved at 04:55 and then succeeded. SSH was via the existing `ai5r` alias (unikom666@103.20.196.187); SSH config was not changed.
- Untracked RYZEN `TEMP/` artifacts:
  - Dry run: `ltsa_pdf_cm_archive_manifest.json/.csv`, `ltsa_pdf_cm_archive_validation.json`, `ltsa_pdf_cm_archive_occurrences.jsonl`, `ltsa_pdf_cm_archive_raw_rows.jsonl`.
  - Reconciliation: `ltsa_cm_reconcile_readonly.py`, `ltsa_cm_reconciliation.json`, `ltsa_cm_reconciliation_candidates.jsonl` (one line per candidate with its asset and occurrence class).
  - Read-only production snapshots: `prod_asset_registry_snapshot.csv`, `prod_cm_reading_snapshot.csv`.
- Regenerate the dry run on any machine with the source archive:
  `cd PRODUCTS/LTSA-BRAIN/INGESTION && python historical_cm_pdf_archive_dry_run.py --root "D:\PROJECT\Source-documents\LTSA\PM_CM_HISTORY" --years 2025 2026 --out "<repo>\TEMP"`

## 6. REMAINING_WORK

1. **Chief Architect decisions before any import:**
   - (a) the 244 column-shifted HSC production rows (§4);
   - (b) the HSC & SPK sub-value semantics (749 source rows);
   - (c) whether the curated alias `DMI-P-201A/B → P-201A/B-DMI` may be applied (27 rows);
   - (d) the `701/702-MM-51` asset type (12 rows);
   - (e) `140-P-3B` (3 rows);
   - (f) release of the AREA_SOURCE_CONFLICT (279) and DATE_CONTEXT_CONFLICT (14) rows;
   - (g) the 10 POTENTIAL_DUPLICATE rows.
2. `LTSA_HISTORICAL_CM_CONTROLLED_PRODUCTION_IMPORT` for the 2,907 SAFE_NEW rows only:
   - verified backup first;
   - re-run the read-only reconciliation immediately before writing, since production may have changed;
   - transactional batches with no overwrite;
   - post-import invariants and a final idempotency dry run, which must show 0 SAFE_NEW.
   Reuse the existing `condition_monitoring_reading_repository` insert path with `provenance=HISTORICAL_IMPORT` and a deterministic `source_reference` per source row (document SHA-256 + page + row), so re-runs are idempotent.
3. Investigate the 41 unexplained April 2026 HISTORICAL_IMPORT production rows.
4. Optionally run the Docker-backed migration tests where Docker is running.

## 7. EXACT_RESUME_INSTRUCTION

On the **laptop**:

```
git fetch origin
git switch feature/ltsa-historical-cm-pdf-parser-r1      # HEAD = this handoff commit
python -m pytest PRODUCTS/LTSA-BRAIN/INGESTION/TEST/test_historical_cm_pdf_parser.py -q
# the reference regression skips unless LTSA_PM_CM_HISTORY_ROOT points at the source archive
```

Do not repeat parser generalization or the read-only reconciliation analysis. Start at `LTSA_HISTORICAL_CM_CONTROLLED_PRODUCTION_IMPORT` once the §6 item 1 decisions are made. The candidate-level files exist only in RYZEN `TEMP/`. Either run the import gate on RYZEN, or regenerate them on the laptop: run the §5 dry-run command, refresh both production snapshots read-only, then run `ltsa_cm_reconcile_readonly.py`.
