# LTSA Historical CM — Overnight Handoff (RYZEN → Laptop)

Status: FINAL CHECKPOINT (overnight run 2026-09-23 → 2026-09-24, worker RYZEN)
Phase gate reached: `LTSA_HISTORICAL_CM_RYZEN_FINAL_CHECKPOINT_R1`: parser generalization complete, branch pushed, **read-only** production reconciliation complete. No production write of any kind.
Addendum 2026-09-24: `LTSA_HISTORICAL_CM_SAFE_IMPORT_SET_R1` fixed a hash-pinned Batch A import set of 2,907 rows (§8).
Addendum 2026-09-24 (laptop): `LTSA_HISTORICAL_CM_BATCH_A_IMPORT_EXECUTOR_R1` implemented and tested; nothing imported (§9).
Addendum 2026-09-24 (laptop): `LTSA_HISTORICAL_CM_BATCH_A_R2_FREEZE_AND_EXECUTOR_ALIGNMENT_R1`: the R1 manifest is **SUPERSEDED** by the API-Plan-corrected **R2** manifest (SHA-256 `54668aca38b285d85b204e0ebf6b45eaef4a8b94b660823c9cc8d2ef052581d8`), now the only manifest a real apply accepts (§8.7).
Addendum 2026-09-24: **Batch A R2 imported into production** (2,092 → 4,999; 2,907 inserted). **DATA IMPORT = PASS**, **APPLICATION UAT = PASS_WITH_UI_FINDINGS**. The Batch A data workstream is **CLOSED** (§10).
Next gate: `LTSA_CM_UI_REMEDIATION_R1` (§10.6). Historical: `LTSA_HISTORICAL_CM_BATCH_A_R2_PRODUCTION_DRY_RUN_R1` (§9.5). Batch A excludes every unresolved population, so it does not wait on the §6 decisions.

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
2. Batch A import (2,907 rows): implement `LTSA_HISTORICAL_CM_BATCH_A_IMPORT_EXECUTOR_R1` to the §8.6 requirements, then run it under its own approval. Batch A needs none of the item 1 decisions.
3. Investigate the 41 unexplained April 2026 HISTORICAL_IMPORT production rows (§8.4).
4. Optionally run the Docker-backed migration tests where Docker is running.

## 7. EXACT_RESUME_INSTRUCTION

On the **laptop**:

```
git fetch origin
git switch feature/ltsa-historical-cm-pdf-parser-r1      # HEAD = this handoff commit
python -m pytest PRODUCTS/LTSA-BRAIN/INGESTION/TEST/test_historical_cm_pdf_parser.py -q
# the reference regression skips unless LTSA_PM_CM_HISTORY_ROOT points at the source archive
```

Do not repeat parser generalization, reconciliation or Batch A planning. The next gate is `LTSA_HISTORICAL_CM_BATCH_A_IMPORT_EXECUTOR_R1` (§8.6). It needed the Batch A R1 manifest with SHA-256 `80542d3c94e129dc7ee82d19127a30b0c01d22f8a1c85f284231280d3e647af0` (**SUPERSEDED**, historical reference only). The executor is now implemented (§9), and the production candidate is the **R2** manifest `54668aca38b285d85b204e0ebf6b45eaef4a8b94b660823c9cc8d2ef052581d8` (§8.7).

## 8. Batch A Production Import Plan

Planned in `LTSA_HISTORICAL_CM_SAFE_IMPORT_SET_R1` (2026-09-24, read-only). Nothing was inserted.

### 8.1 Plan figures

| Field | Value |
|---|---|
| PRODUCTION_CM_BASELINE | 2,092 (read-only recheck at planning; unchanged since 05:00; last production write 2026-09-21 09:08) |
| SAFE_NEW_BATCH_A | 2,907 |
| EXPECTED_CM_AFTER_BATCH_A | 4,999 (= 2,092 + 2,907; insert only, no UPDATE/DELETE) |
| BATCH_A_2025 | 997 (PDF FORMAT_A only; no 2025 XLSX exists) |
| BATCH_A_2026 | 1,910 (PDF FORMAT_A, each row identical to its XLSX row; XLSX file + row recorded per row) |
| BATCH_A_HCC | 1,117 |
| BATCH_A_HOC | 924 |
| BATCH_A_OM_UTL | 866 |
| BATCH_A_OTHER | 0 |
| MONTHS | 2025-10=297 · 2025-11=443 · 2025-12=257 · 2026-01=205 · 2026-02=751 · 2026-03=685 · 2026-06=269 |
| ALREADY_PRESENT_NOW (at recheck) | 0 |
| MANIFEST (R1, **SUPERSEDED**) | `TEMP/ltsa_historical_cm_batch_a_import_manifest.json` (untracked) |
| MANIFEST_SHA256 (R1, **SUPERSEDED**, historical reference only) | `80542d3c94e129dc7ee82d19127a30b0c01d22f8a1c85f284231280d3e647af0` |
| MANIFEST (R2, **FROZEN_PRODUCTION_CANDIDATE**) | `TEMP/ltsa_historical_cm_batch_a_import_manifest_r2_api_plan.json` (untracked) — see §8.7 |
| MANIFEST_SHA256 (R2, **FROZEN_PRODUCTION_CANDIDATE**) | `54668aca38b285d85b204e0ebf6b45eaef4a8b94b660823c9cc8d2ef052581d8` |

Batch A entry criteria (none weakened) — a row qualifies only if all of these hold:
- extraction validation passed;
- FORMAT_A structure;
- exact PUMP match in `asset_registry` with registry code equal to the source tag;
- not already in production;
- unique asset+date across all parsed sources;
- no HSC & SPK, area-conflict or date-conflict relation (date conflict checked against the printed date and the plausible report-year date);
- tag not in {DMI-P-201A/B, 701-MM-51, 702-MM-51, 140-P-3B};
- tag reported in only one area;
- for 2026, API PLAN identical in PDF and XLSX.

The recheck excluded nothing further.

Each manifest row carries:
- `source_hash`, `source_document`, `relative_path`, `source_page`, `source_report_page`, `source_row`;
- `source_date`, `source_tag`, `tag`, `asset_code`, `reading_date`, `year`/`month`/`area`, `api_plan_snapshot`;
- canonical `measurements` (20 FORMAT_A fields + `pump_operating_state`, NULL for all rows);
- `measurement_fingerprint` (SHA-256 of the canonical measurements);
- `source_format`, `xlsx_corroboration`, and a unique `proposed_source_reference` (`ltsa_hist_cm_pdf:<hash16>:p<page>:r<row>`).

### 8.2 701 metrics (read-only, 2026-09-24)

| Metric | Definition | Value |
|---|---|---|
| P701_P1A_CM_COUNT | production CM rows with `asset_code = '701-P-1A'` (live) | 9 |
| AREA_701_PUMP_CM_COUNT | production CM rows with `asset_code LIKE '701-P-%'` (live) | 81 |
| AREA_701_INCLUDING_MM_COUNT | the previous row + `701-MM-51` (7 rows) | 88 |

### 8.3 Unresolved populations — NOT in Batch A (listed separately, none counted as coverage)

| Population | Rows | Status |
|---|---|---|
| HSC & SPK semantic quarantine (source) | 749 | SEMANTIC_MAPPING_REQUIRED — sub-value meaning undefined |
| Existing production rows column-shifted (HSC & SPK Apr + Jul 2026) | 244 | REPAIR_REQUIRED — audit `TEMP/ltsa_hsc_spk_column_shift_repair_candidates.json` (source row identified for all 244; not repaired; not historical coverage) |
| AREA_SOURCE_CONFLICT (HCC Dec 2025 under HOC) | 279 | quarantined |
| DATE_CONTEXT_CONFLICT (HOC Jan 2026, `06-Jan-25`) | 14 | quarantined |
| Asset identity: DMI-P-201A/B (alias not applied) | 27 | NOT_FOUND |
| Asset identity: 701-MM-51 / 702-MM-51 (empty asset_type) | 12 | EXACT_NON_PUMP |
| Asset identity: 140-P-3B (near-miss to 140-P-3A) | 3 | AMBIGUOUS |
| Same tag twice on one date within a report | 10 | POTENTIAL_DUPLICATE |
| Unexplained existing April 2026 HISTORICAL_IMPORT rows | 41 | 8 SOURCE_IDENTIFIED (P-201A/B-DMI, identical to OM & UTL April rows via the DMI alias; evidence only) · 33 SOURCE_NOT_IDENTIFIED (no April report row at that tag/date; all `document_field_extraction`) — audit `TEMP/ltsa_cm_unexplained_april_rows_audit.json` |

### 8.4 Artifacts (RYZEN `TEMP/`, untracked, never committed)

- `ltsa_historical_cm_batch_a_import_manifest.json` (+ `.sha256`): R1, **SUPERSEDED** by R2 (§8.7); keep it unchanged as the correction's base
- `ltsa_historical_cm_batch_a_import_manifest_r2_api_plan.json` (+ `.sha256`): R2, **FROZEN_PRODUCTION_CANDIDATE** (laptop `TEMP/`)
- `ltsa_historical_cm_batch_a_plan.json` (breakdowns + per-row exclusion log)
- `ltsa_hsc_spk_column_shift_repair_candidates.json`, `ltsa_cm_unexplained_april_rows_audit.json`
- `ltsa_cm_reconciliation.json`, `ltsa_cm_reconciliation_candidates.jsonl`, production snapshots `prod_asset_registry_snapshot.csv` / `prod_cm_reading_snapshot.csv`
- `recon_20260924_0500/` (the 05:00 reconciliation, preserved)
- Planning scripts (read-only, no DB access):

| Script | SHA-256 |
|---|---|
| `ltsa_cm_reconcile_readonly.py` | `256c533e0723db2f4ed08e53ecdf2fdca774035e92d8dee7792a81c798bad2ef` |
| `ltsa_cm_batch_a_plan_readonly.py` | `0e6d4c0a9afd559a57f127d893188869de4251161d0135505f73b586fb6b7c76` |

### 8.5 Regenerating the manifest

This section regenerates **R1** (**SUPERSEDED**, historical reference). R2 is then derived from R1 by the §8.7 correction only; regeneration alone does not produce the production candidate.

**Determinism proven on RYZEN.** The full chain was rebuilt from scratch into an empty directory (archive dry run → reconciliation → Batch A planner, using the saved production snapshots). It reproduced SHA-256 `80542d3c…47af0` byte for byte. Environment: Python 3.14.6, pdfplumber 0.11.10, openpyxl 3.1.5.

Commands (from the repo root; `<OUT>` = an empty directory):

```
cd PRODUCTS/LTSA-BRAIN/INGESTION
python historical_cm_pdf_archive_dry_run.py --root "D:\PROJECT\Source-documents\LTSA\PM_CM_HISTORY" --years 2025 2026 --out "<OUT>"
# place read-only production snapshots in <OUT> (same SELECTs as used on RYZEN):
#   prod_asset_registry_snapshot.csv : select asset_code, asset_name, asset_type, area, status from asset_registry order by asset_code;
#   prod_cm_reading_snapshot.csv     : select condition_monitoring_reading_code, asset_code, asset_type, reading_date::date as reading_date,
#       <20 FORMAT_A measurement columns>, pump_operating_state, provenance, workflow_status, source_reference,
#       source_workbook_name, source_sheet_name, source_row_number, api_plan_snapshot, deleted_at
#       from condition_monitoring_reading order by asset_code, reading_date;   (psql --csv, read-only session)
# set T = Path(r"<OUT>") in both planning scripts, then:
python <OUT>/ltsa_cm_reconcile_readonly.py
python <OUT>/ltsa_cm_batch_a_plan_readonly.py
sha256sum <OUT>/ltsa_historical_cm_batch_a_import_manifest.json   # R1 (SUPERSEDED): must equal 80542d3c…47af0
```

Conditions for an identical hash:
- the same source archive (document SHA-256s are in §3);
- the same parser commit `3af4a464`;
- the two planning scripts with the SHA-256s above;
- unchanged production (`condition_monitoring_reading` = 2,092 rows as snapshotted, and `asset_registry` = 257 rows). The manifest embeds `production_total_cm_at_planning`, and its row set depends on production. If production changes, the new hash is *expected* to differ and the plan must be reviewed again.

**BLOCKER — laptop regeneration.** The two planning scripts exist only in RYZEN `TEMP/`. This addendum commits documentation only, so a laptop cannot regenerate the manifest from git alone. Options:
- (a) copy the manifest (verify its SHA-256) or the two scripts (verify the SHA-256s above) from RYZEN to the laptop;
- (b) approve committing the two read-only planning scripts as tools in a follow-up;
- (c) run the executor gate on RYZEN.

### 8.6 Next gate: `LTSA_HISTORICAL_CM_BATCH_A_IMPORT_EXECUTOR_R1` (requirements only — NOT implemented)

The executor must:
1. accept an explicit manifest path;
2. require the expected SHA-256 as an argument, and refuse to run on a mismatch;
3. be insert-only into `condition_monitoring_reading`: no UPDATE, no DELETE, no `asset_registry` / `ltsa_pumps` mutation (`ltsa_pumps.api_plan` is never touched; the source plan goes to `api_plan_snapshot`);
4. use `proposed_source_reference` as the idempotency key (a row whose `source_reference` already exists is skipped, never updated);
5. run a preflight read-only recheck of every manifest row: asset still EXACT PUMP, and no live production row for asset+date or for the same `source_reference`. Any change aborts the run for review;
6. require a production backup taken immediately before the write, **and verified** (restorable / checksum), recording the backup path;
7. do a dry run first, which must propose exactly 2,907 inserts;
8. check the baseline: the expected count goes 2,092 → 4,999 only if the baseline is still 2,092 at write time; abort if it has changed unexpectedly;
9. write in transactional batches, rolling back any failed batch as a whole; there are no partial rows;
10. verify post-import invariants: total = baseline + inserted; no pre-existing row changed (compare the `updated_at` / fingerprint of the snapshotted rows); every manifest row present exactly once with an identical measurement fingerprint;
11. run a second dry run after the import, which must propose **0** inserts;
12. write `provenance=HISTORICAL_IMPORT` and populate source provenance (`source_reference`, and document/page/row where columns exist), reusing the existing repository insert path rather than a new SQL path.

### 8.7 R2 manifest freeze (`LTSA_HISTORICAL_CM_BATCH_A_R2_FREEZE_AND_EXECUTOR_ALIGNMENT_R1`, 2026-09-24)

| Field | Value |
|---|---|
| R1_MANIFEST_STATUS | **SUPERSEDED** |
| R1_FILENAME | `ltsa_historical_cm_batch_a_import_manifest.json` |
| R1_SHA256 | `80542d3c94e129dc7ee82d19127a30b0c01d22f8a1c85f284231280d3e647af0` |
| R2_MANIFEST_STATUS | **FROZEN_PRODUCTION_CANDIDATE** |
| R2_FILENAME | `ltsa_historical_cm_batch_a_import_manifest_r2_api_plan.json` |
| R2_SHA256 | `54668aca38b285d85b204e0ebf6b45eaef4a8b94b660823c9cc8d2ef052581d8` |
| ROWS / BASELINE / EXPECTED_INSERTS / EXPECTED_TOTAL_AFTER | 2,907 / 2,092 / 2,907 / 4,999 (unchanged from R1) |
| API_PLAN_SNAPSHOT non-NULL / NULL | 2,898 / 9 |

R2 was made from R1 by `LTSA_HISTORICAL_CM_BATCH_A_API_PLAN_CORRECTION_R1`. It applies exactly two user-confirmed interpretation rules to `api_plan_snapshot` and nothing else:
- 9 rows: `"23/61` → `23/61`. This is a source typo (a stray quote). All 9 are `110-P-12A`, HOC October and November 2025.
- 9 rows: `-` → **NULL**. All 9 are `211-P-30`, HCC February, March and June 2026.

**NULL means the API Plan is unknown / not yet known.** The UI shows it as N/A / Belum diketahui. A NULL snapshot is never filled from the master `ltsa_pumps.api_plan`, and `-` is not an API Plan value.

Everything else is unchanged from R1: row order, `proposed_source_reference`, `measurement_fingerprint`, measurements, leak true/false/null, asset/date/area, and all source evidence (`source_hash`, `source_document`, page, row, tag, date).

The raw source values stay traceable. R2's header adds `revision=R2_API_PLAN_CORRECTION`, `revision_phase`, `supersedes_manifest_sha256` (= R1) and `api_plan_correction_rules`. It also adds `api_plan_corrections`: for each of the 18 rows, the reference, asset, date, area, document, page and row, with the original and canonical value. R2 uses the same serialization as R1 (sorted keys, `indent=1`, CRLF), so a text diff of R1 → R2 removes only the 18 `api_plan_snapshot` lines.

The executor's `BATCH_A_MANIFEST_SHA256` is the R2 hash. A real apply accepts only R2. R1 and any other hash are rejected with `NOT_FROZEN_MANIFEST`, even when every other gate is satisfied. Dry runs still require `--expected-sha256` to match the file.

## 9. Batch A import executor (`LTSA_HISTORICAL_CM_BATCH_A_IMPORT_EXECUTOR_R1`)

Implemented on the laptop, 2026-09-24. **No import, no production access, no database write** in this phase. The only database used was a disposable local test container.

### 9.1 Files

All under `PRODUCTS/LTSA-BRAIN/INGESTION/`:

- `historical_cm_batch_a_import_executor.py`: the executor.
- `TEST/test_historical_cm_batch_a_import_executor.py`: 88 tests (80 + 8 added by the R2 alignment; 3 of them read the real R2 file and skip where it is absent). They use a synthetic 2,907-row manifest with the frozen header contract and an in-memory transactional store.
- `TEST/test_historical_cm_batch_a_import_executor_real_db.py`: 5 tests. They run the real generated SQL against a disposable `postgres:16-alpine` container (canonical schema + migrations + the migration 038 column), and are skipped when Docker is down.

### 9.2 How it runs (each step aborts the run on failure)

1. **Hash.** SHA-256 of the manifest's raw bytes is checked against `--expected-sha256` *before* parsing. The manifest is only read, never rewritten.
2. **Manifest validation.**
   - Header: `manifest=LTSA_HISTORICAL_CM_BATCH_A`, `row_count=2907` (= `len(rows)`), `production_total_cm_at_planning=2092`, `expected_total_cm_after=4999`, `insert_only=true`.
   - Rows: `proposed_source_reference` well-formed and unique; `asset_code+reading_date` unique; `asset_code == tag`; no excluded tag (DMI-P-201A/B, 701/702-MM-51, 140-P-3B) and no HSC_SPK area.
   - `reading_date` is an ISO calendar date, not in the future, and inside the row's `year`/`month`.
   - `measurements`: exactly the 20 FORMAT_A keys + `pump_operating_state`. Numbers are finite or null. Leak values are strictly `true`/`false`/`null`. A numeric `pump_operating_state` is rejected (the §4 column-shift signature).
   - `api_plan_snapshot` key present (text or null).
3. **Read-only preflight.** Every read runs in `BEGIN TRANSACTION READ ONLY`. It checks:
   - `api_plan_snapshot` column present;
   - baseline = current total − manifest rows already present, must be 2,092, else ABORT / REPLAN;
   - no foreign `source_reference` or reading-code collision;
   - no live row at a manifest asset+date;
   - exactly one `asset_registry` row per asset, with `asset_type = 'PUMP'`;
   - no rows with the `ltsa_hist_cm_pdf:` prefix other than this manifest's own;
   - a partial import is refused unless `--allow-resume`.
   Output: `PROPOSED_INSERTS` / `ALREADY_IMPORTED` / `UPDATES=0` / `DELETES=0`.
4. **Apply (`--mode apply` only).** Refused unless all of these hold: the manifest hash equals the frozen **R2** `54668aca38b285d85b204e0ebf6b45eaef4a8b94b660823c9cc8d2ef052581d8` (`BATCH_A_MANIFEST_SHA256`; R1 `80542d3c…47af0` is SUPERSEDED and rejected with `NOT_FROZEN_MANIFEST`); `--confirm-production-write LTSA_HISTORICAL_CM_BATCH_A` is given; `--backup-file` exists and matches `--backup-sha256`; and `--expected-inserts` equals the proposal.
   - Each batch (default 250 rows) is one script: `BEGIN` → `LOCK` → DO-block precheck (total, references, codes, occurrences, assets) → one multi-row `INSERT` → DO-block postcheck → `COMMIT`.
   - A failed batch rolls back as a whole, and the run stops with `BATCH_FAILED`, committed batch/row counts and a rollback check. No later batch runs.
5. **Post-import verification.**
   - total = baseline + 2,907;
   - every row not carrying the `ltsa_hist_cm_pdf:` prefix is unchanged (per-row md5 fingerprint);
   - every manifest row is present exactly once, field-identical;
   - a second dry run must propose **0**.

Written values: `condition_monitoring_reading_code = LTSA-CMONR-HISTPDF-<sha1(ref)[:16]>`, `condition_monitoring_schedule_code = UNSCHEDULED::<source_document>` (the existing `build_unscheduled_reference`), `asset_type='PUMP'`, `provenance='HISTORICAL_IMPORT'`, `workflow_status='FINALIZED'` (same as the existing historical XLSX importer), `source_reference`, `source_workbook_name=<source PDF>`, `source_row_number`, and `api_plan_snapshot` from the manifest row only. `created_by`/`finding` are left NULL, and no `record_change_history` row is written. The existing historical XLSX importer does the same.

**Insert-only by construction.**
- Every write script passes `_assert_insert_only`, which refuses UPDATE…SET, DELETE, ON CONFLICT, MERGE, TRUNCATE, DDL, and INSERT into any other table.
- There is exactly one write call site.
- `asset_registry` and `ltsa_pumps` are only ever read.
- The existing repository `create_*` methods were deliberately **not** reused: on the dashboard branch (2afdfe9) they fill `api_plan_snapshot` from `ltsa_pumps.api_plan`, which is the master-plan fallback this batch forbids. The transport (`DatabaseRunner`, docker-compose psql or direct connect) is reused unchanged.

### 9.3 Manifest schema assumption (verify at the production dry run)

**Resolved:** `LTSA_HISTORICAL_CM_BATCH_A_REAL_MANIFEST_ACCEPTANCE_R1` ran the executor's hash gate and parser, with no database, against the real R1 file (`80542d3c…47af0`, now SUPERSEDED): 2,907 rows accepted, schema as assumed below. R2 was accepted the same way (§8.7). The original note follows.

The real manifest is on RYZEN only (§8.5 blocker) and was **not available on the laptop**. So its SHA-256 was not verified here, and the executor was never run against it.
- Key names follow §8.1: top-level `rows`; per row `source_row`, `source_page`, `source_document`, `tag`, `asset_code`, `year`, `month`, `area`, `api_plan_snapshot`, `measurements`, `proposed_source_reference`.
- If the real file uses different key names, the executor aborts with `MANIFEST_SCHEMA_INVALID` / `MANIFEST_ROWS_INVALID`. It fails closed and never guesses.
- `measurement_fingerprint` is carried but not recomputed, because its serialization lives in the uncommitted RYZEN planning script. Instead, identity is proven by a field-level comparison with the stored row.

### 9.4 Leak alert contract (downstream UI, not implemented here)

Historical measurement values are never changed.
- `mechanical_seal_leak_de = true` OR `mechanical_seal_leak_nde = true` → **LEAK_DETECTED**.
- `false` → NO_LEAK. `null` → N/A (unknown, never shown as "no leak").
- Historical occurrence: an occurrence keeps its leak alert permanently.
- Current Condition: alert only when the **latest valid** CM occurrence has leak = true. An older leak does not raise the current alert.
- UI implementation is out of scope for the executor.

### 9.5 Production write gate

Next: `LTSA_HISTORICAL_CM_BATCH_A_R2_PRODUCTION_DRY_RUN_R1`, a separate mission.
- Bring the **R2** manifest `ltsa_historical_cm_batch_a_import_manifest_r2_api_plan.json` to the machine that runs the executor and verify `54668aca38b285d85b204e0ebf6b45eaef4a8b94b660823c9cc8d2ef052581d8`. Do not use R1.
- Then run `python historical_cm_batch_a_import_executor.py --manifest <path to R2> --expected-sha256 54668aca38b285d85b204e0ebf6b45eaef4a8b94b660823c9cc8d2ef052581d8 --mode dry-run --env-file … --compose-file … --report <out>`. It must report `PROPOSED_INSERTS=2907`, `UPDATES=0`, `DELETES=0`.

Production import only after all of these: executor review PASS, tests PASS, manifest SHA PASS, production baseline recheck PASS (2,092), fresh production backup, backup verification PASS, production dry run proposes exactly 2,907, and explicit write approval.

### 9.6 docker-exec read compatibility fix (`LTSA_HISTORICAL_CM_BATCH_A_R2_DOCKER_EXEC_READ_FIX_R1`)

The problem: on the production host, the executor connects in `DatabaseRunner`'s docker-exec mode (`docker compose … exec -T postgres psql -tAc`). psql prints the command tag of every statement in the call, so the executor's read-only reads (`BEGIN TRANSACTION READ ONLY; SELECT …`) return `BEGIN\n<result>`. Commit `547a9c4` parsed that as the result itself, so its first preflight read failed (`int('BEGIN\n2092')`). It failed closed, before any write.

The fix: `PostgresCmImportStore._read` now passes the output through `_query_result`.
- It drops exactly one leading `BEGIN` line and returns the rest unchanged.
- Empty or status-only output aborts with `READ_RESULT_EMPTY`.
- Anything else malformed (a second status line, extra lines, bad numbers or JSON) still fails in the existing `int()` / `json.loads` parsing.
- Transport failures still raise in the runner.
- The shared `DatabaseRunner`, the write path, the insert-only guard and every apply gate are unchanged.

Evidence:
- `TEST/test_historical_cm_batch_a_import_executor_docker_exec_real_db.py` runs a disposable compose project. It reproduces the failure on `547a9c4`, then runs the full dry run, apply, verification and idempotency through the docker-exec transport.
- 16 fake-runner unit tests cover the failure and pass cases.
- A read-only production probe through the real compose transport returned `BEGIN\n2092`, which parses to 2,092.

**Operational note for host execution:** `DatabaseRunner.query_scalar` does not redirect stdin, and `docker compose exec` reads it. Run the executor with stdin from `/dev/null`, never as part of a script piped to `bash -s`.

## 10. Batch A R2 closure (`LTSA_HISTORICAL_CM_BATCH_A_R2_CLOSURE_R1`, 2026-09-24)

**DATA IMPORT = PASS · APPLICATION UAT = PASS_WITH_UI_FINDINGS.** The UI findings (§10.6) do not invalidate the imported data.

### 10.1 Import identity

| Field | Value |
|---|---|
| Manifest (R2, frozen) | `ltsa_historical_cm_batch_a_import_manifest_r2_api_plan.json`, SHA-256 `54668aca38b285d85b204e0ebf6b45eaef4a8b94b660823c9cc8d2ef052581d8` (R1 `80542d3c…47af0` SUPERSEDED) |
| Executor commit | `fd18fc903ad9a1093e266cd17c09a8c7d6cc504c`, staged on the production host as a `git archive` (commit id verified; 40 files byte-identical to git blobs) |
| Transport | production-host execution: `DatabaseRunner` docker-exec (`docker compose … exec -T postgres psql`), compose project `ai5ros-prod`, database `ltsa_brain`, stdin `/dev/null` |
| Pre-import backup | `/home/unikom666/AI5R-PROD-BACKUPS/ltsa_brain_pre_histcm_batch_a_r2_20260924T134054Z.dump`: `pg_dump -Fc` of `ltsa_brain`, 667,668 bytes, SHA-256 `b6286e82368459571ec42d51e8594a4b769bd00222d07cdfd9f10493a07356dd`. `pg_restore --list` PASS. A disposable restore reproduced 2,092 / 257 / 252 with identical table fingerprints. |
| Apply | one run of `--mode apply --expected-inserts 2907 --confirm-production-write LTSA_HISTORICAL_CM_BATCH_A`: exit 0, 12/12 batches committed, no retry, no `--allow-resume` |

### 10.2 Result (verified read-only after import, and again at closure)

| Field | Value |
|---|---|
| BASELINE_CM / BATCH_A_INSERTED / FINAL_CM | 2,092 / 2,907 / 4,999 |
| Membership | 2,907 matched and field-identical to the manifest; 0 missing; 0 unexpected; 0 duplicate source references |
| Provenance / workflow | HISTORICAL_IMPORT 2,907 / FINALIZED 2,907 |
| Year | 2025 = 997 · 2026 = 1,910 |
| Area (source report) | HCC 1,117 · HOC 924 · OM_UTL 866 |
| Month | 2025-10 297 · 2025-11 443 · 2025-12 257 · 2026-01 205 · 2026-02 751 · 2026-03 685 · 2026-06 269 |
| API plan snapshot | non-NULL 2,898 · NULL 9 (all `211-P-30`) · `23/61` 217 · `"23/61` 0 · `-` 0 |
| Leak DE | true 215 · false 2,669 · NULL 23 |
| Leak NDE | true 52 · false 673 · NULL 2,182 |
| Any / both leak true | 235 / 32 |
| 701-P-1A | 9 before + 13 Batch A = 22 |
| Pre-existing rows | unchanged (fingerprint of the 2,092 non-Batch-A rows identical before and after the import) |
| asset_registry / ltsa_pumps | 257 / 252; fingerprints unchanged (`257:a0589f3b…a570`, `252:ced14b95…736d`) |
| Idempotency (dry run after import) | ALREADY_IMPORTED 2,907 · PROPOSED_INSERTS 0 · UPDATES 0 · DELETES 0 · issues 0 |

### 10.3 Confirmed correct behaviour (not defects)

- Historical API Plan comes from `api_plan_snapshot`. A NULL snapshot never falls back to `ltsa_pumps.api_plan`.
- The 9 unknown `211-P-30` API Plans are NULL (master plan `11/62` not used). The Actual Measuring Report shows an unknown plan as "—".
- DE and NDE are stored and rendered independently. A NULL leak stays NULL in the stored data.
- Batch A changed the latest valid CM of **zero** assets (0 of 253), so it added history without changing any Current Condition.
- Rows from before migration 038 carry `api_plan_snapshot` NULL. That is the expected historical-unknown state, not a Batch A defect.

### 10.4 UAT limitations

- **AUTHENTICATED_UI_CLICKTHROUGH = NOT_VERIFIED_LIVE.** No authenticated LTSA browser session was available, and production authentication was not bypassed. What UAT did cover:
  - live, read-only: health, auth-gated routes returning 401, logs (0 API errors, 0 nginx 5xx since the import);
  - database reconciliation of every sampled occurrence;
  - the deployed code (below).
- **DEPLOYED_API_IDENTITY = VERIFIED** against `7bd3236` for `cm_condition_evaluator.py`, `equipment_360_service.py` and `condition_monitoring_reading_repository.py` (byte-identical in the API container).
- **DEPLOYED_FRONTEND_IDENTITY = NOT_FULLY_VERIFIED.**
  - The served bundle is `index-BogGFLFT.js`; the local release build is `index-BKL53JLI.js`.
  - The served bundle does contain the expected strings (for example "API Plan Recorded in Source").
  - This does not by itself mean a wrong deployment. Authenticated visual verification is still required.
  - Suggested click-through: `701-P-1A`; `211-P-30` 2026-02-02; `840-P-4B` 2025-10-09.

### 10.5 Retained recovery artifacts

No cleanup is authorized. Keep:
- the backup above;
- the staging directory `/home/unikom666/AI5R-HISTCM-BATCH-A-R2` (read-only; the frozen executor, manifest and `STAGING_INVENTORY.txt`).

Both are retained until UI remediation and the authenticated live verification close.

### 10.6 Follow-up workstream `LTSA_CM_UI_REMEDIATION_R1` (open; not implemented here)

1. **NULL/NULL leak summarized as a green "No leak".**
   - Where: `ConditionMonitoringReadingDetailPanel` (`leakDetected = leakDe || leakNde`). Its DE/NDE rows correctly say "Not Recorded".
   - Required: true → leak · false → no leak · null → unknown / not recorded.
   - Seen at UAT: 321 live rows (23 Batch A).
2. **Active-leak semantics.**
   - Now: several consumers (maintenance history flag, Equipment 360, fleet analytics, seal diagnostic) use "any leak in the last 30 days".
   - Contract: the **latest valid CM occurrence** determines Current Condition. A historical leak stays visible in History, but it must not create a current active leak when a newer valid occurrence says no leak.
   - The evaluator's `current_condition` is computed but no UI consumes it.
   - UAT snapshot (not constants): latest-valid leak assets 16, currently flagged 1, mismatches 15.
3. **Leak alert visibility.** There is no explicit critical presentation. Desired: **LEAK DETECTED — DE**, **— NDE**, **— DE & NDE**, shown in red.
