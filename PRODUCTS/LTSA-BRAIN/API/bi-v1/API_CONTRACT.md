# LTSA Governed BI API — Contract `ltsa-bi/1.0.0`

Status: IMPLEMENTED (LTSA_POWER_BI_R1B) — not deployed to production.
Source of truth for the semantics: `LTSA_POWER_BI_R1A_SEMANTIC_DATA_CONTRACT`.

Read-only, versioned tables for a Power BI **Import** model. Power BI consumes
these governed facts; it never recreates LTSA business logic. Every rule is
delegated to the canonical LTSA contracts (`CORE-SERVICES/API/bi_dataset_service.py`):

| Rule | Canonical source |
|---|---|
| Contract area | `pump_contract_area.resolve_contract_area` (exact token) |
| Maintenance area, area code, display | `pump_area_scope.resolve_area_ma` / `normalize_area_token` / `format_area_display` |
| CM leak state, current condition | `cm_condition_evaluator.canonical_leak_state` / `is_active_leak` / `current_leak_condition` |
| Installation events | `historical_installation_evidence.combined_installation_evidence` + `current_installation_contract.valid_installation_events` |
| MTBF intervals, pump MTBF | `installation_interval_contract.installation_based_mtbf` |
| Current installation, service age | `current_installation_contract.resolve_current_installation` (installation_report only) |

## Endpoints (all `GET`, permission `bi.read`)

| Path | Table | Grain | Key / order |
|---|---|---|---|
| `/api/ltsa/bi/v1/metadata` | — | reconciliation counts | — |
| `/api/ltsa/bi/v1/assets` | DIM_ASSET | one asset_registry asset | `asset_code` |
| `/api/ltsa/bi/v1/areas` | DIM_AREA | one distinct raw area | `raw_area_key` |
| `/api/ltsa/bi/v1/cm` | FACT_CM | one live CM reading | `reading_code` |
| `/api/ltsa/bi/v1/pm` | FACT_PM | one live PM occurrence | `pm_occurrence_code` |
| `/api/ltsa/bi/v1/installations` | FACT_INSTALLATION | one governed installation / reinstallation event | `event_id`; order `asset_code,event_date,event_id` |
| `/api/ltsa/bi/v1/mtbf-intervals` | FACT_MTBF_INTERVAL | one completed interval | `interval_id`; order `asset_code,position,start_date,start_event_id` |
| `/api/ltsa/bi/v1/pump-current` | FACT_PUMP_CURRENT | one asset_registry PUMP, as of the request | `asset_code` |

DIM_DATE is generated in Power BI (`CALENDAR(metadata.min_fact_date, metadata.as_of_date)`), not served.

## Envelope

```json
{"success": true, "contract_version": "ltsa-bi/1.0.0", "table": "cm",
 "generated_at_utc": "2026-09-28T03:00:00Z", "as_of_date": "2026-09-28",
 "plant_timezone": "Asia/Jakarta", "row_count": 4999, "max_rows": 50000,
 "order_by": "reading_code", "data": [ ... ]}
```

**Bounded bulk, never truncated.** Each call returns the complete table. A
table above `max_rows` (50,000) returns HTTP 413 `BI_TABLE_LIMIT_EXCEEDED`
with no data — never the first 50,000 rows. Power BI must fail the refresh
unless `rows received == row_count`.

**Snapshots are per request.** Each call has its own `generated_at_utc` and
plant-local `as_of_date` (Asia/Jakarta). Separate calls are not
transactionally consistent; a difference between a table's `row_count` and
`/metadata` after a concurrent write is expected and must be surfaced as a
warning, not hidden (`metadata.snapshot_consistency = "PER_REQUEST"`).

## Errors

`{"success": false, "error_code": "...", "message": "...", "contract_version": "ltsa-bi/1.0.0"}`

| HTTP | error_code | When |
|---|---|---|
| 401 | `BI_UNAUTHENTICATED` | no / invalid / expired token |
| 403 | `BI_FORBIDDEN` | identity lacks `bi.read` |
| 413 | `BI_TABLE_LIMIT_EXCEEDED` | table above `max_rows` |
| 503 | `BI_SOURCE_UNAVAILABLE` | a source read failed (e.g. database or schema unavailable) |
| 500 | `BI_INTERNAL_ERROR` | anything else |

Messages never contain SQL, credentials, stack traces or internal paths.

## Field semantics

Dates are ISO `YYYY-MM-DD`. CM/PM timestamps are stored naive plant-local;
`reading_date` / `occurrence_date` are their date part and the raw value is kept
in `*_timestamp_local`. Installation dates are the canonical parser's
plant-local date with `date_precision` = `DATE_ONLY` | `TIMESTAMP`
(installation_report.report_date is TEXT; Power BI never re-parses it).

- **DIM_ASSET** — `asset_code, asset_name, asset_type (nullable), is_pump,
  asset_status, raw_area_key, raw_area, contract_area, maintenance_area,
  pump_enrichment_present, pump_type, api_plan, configured_seal_type,
  criticality, ltsa_location`. asset_registry is authoritative; ltsa_pumps is
  LEFT JOIN enrichment — missing/blank enrichment is `null`, never "Unknown";
  no asset is ever dropped. A duplicate join result fails with 503.
- **DIM_AREA** — `raw_area_key` (raw value, or `__NOT_RECORDED__`), `raw_area,
  area_code, contract_area, maintenance_area (MA1..MA4 or "Unclassified"),
  area_display, asset_count`. The two canonical mappings are exposed as they
  are, including their divergence: `OIL MOVEMENT` → contract `Unclassified` /
  maintenance `MA4`; `UTILITIES` → `Unclassified` / `MA3`. No composite
  `OM_UTL` / `MA3&4` values exist.
- **FACT_CM** — `reading_code, asset_code, reading_date,
  reading_timestamp_local, workflow_status (DRAFT kept), pump_operating_state,
  provenance, source_reference, leak_de, leak_nde, canonical_leak_state,
  leak_active, finding, technical_recommendation, api_plan_snapshot`.
  `leak_de`/`leak_nde` are the lossless tri-state `TRUE | FALSE |
  NOT_RECORDED` (NULL is never FALSE). `canonical_leak_state` ∈
  `LEAK_DE_AND_NDE, LEAK_DE, LEAK_NDE, NO_LEAK, NO_LEAK_DE_ONLY,
  NO_LEAK_NDE_ONLY, UNKNOWN`. No leak-text-conflict field in 1.0.0.
- **FACT_PM** — `pm_occurrence_code, asset_code, occurrence_date,
  occurrence_timestamp_local, status, workflow_status, provenance,
  source_reference, finding`. No compliance / plan-vs-actual semantics
  (pm_schedule has no targets).
- **FACT_INSTALLATION** — `event_id` (installation_code or
  historical_event_id), `event_source` (`INSTALLATION_REPORT` |
  `HISTORICAL_SERVICE_ACTIVITY`), `asset_code, position (DE | NDE | PUMP_LEVEL),
  event_date, date_precision, event_type (INSTALLATION |
  REINSTALLATION_REFURBISHED_SEAL), seal_type, seal_size (verbatim), seal_code,
  evidence_grade, date_correction_status, source_reference, source_document`.
  Position comes only from structured data; DE/NDE is never inferred from
  free text. Only governed historical rows are events (review queue excluded).
- **FACT_MTBF_INTERVAL** — `interval_id
  ("{asset}|{position}|{start}|{end}"), asset_code, position, start_event_id,
  end_event_id, start_date, end_date, mtbf_days, mtbf_hours (= days × 24),
  calendar_basis (CALENDAR_TIME), precision, seal_identity_transition
  (CONFIRMED_SAME | CHANGED | UNKNOWN), start/end seal type & size`.
  Completed intervals only: same pump, same structured position, consecutive
  valid installation/reinstallation events. CM leaks, findings, PM,
  inspections, work orders and configuration are never boundaries.
- **FACT_PUMP_CURRENT** — `asset_code, as_of_timestamp_utc, as_of_date,
  current_cm_reading_code, current_cm_reading_date, current_cm_workflow_status,
  current_pump_operating_state, current_leak_state, current_leak_active,
  current_installation_status, current_installation_code,
  current_installation_date, current_installation_position,
  current_installed_seal_type, current_installed_seal_size,
  current_service_age_days, current_service_age_hours,
  current_service_age_basis, current_service_age_precision,
  pump_mtbf_completed_interval_count, pump_mtbf_days_mean,
  pump_mtbf_hours_mean, pump_mtbf_latest_interval_days`.
  Current condition and current installation come from the application's own
  evaluators; current installation is installation_report-only (historical
  evidence never becomes current). **Service age is not MTBF**: DATE_ONLY
  hours = days × 24; TIMESTAMP hours are elapsed hours. A pump with no
  completed interval has count 0 and `null` means — never a zero MTBF.

## MTBF / MTTR policy

- No area- or fleet-average MTBF anywhere. By area only: pump count, pumps
  with completed MTBF, completed interval count, coverage %. Pump-level
  installation-based MTBF only in single-pump context.
- Coverage % = pumps with ≥ 1 completed interval ÷ asset_registry PUMP
  population (FACT_PUMP_CURRENT rows) — never ÷ ltsa_pumps.
- MTTR is not available (`metadata.mttr_available = false`,
  `mttr_status = "DATA NOT AVAILABLE"`): there is no governed failure start,
  repair start/end or return-to-service evidence, and a leak is not a failure.

## Metadata (`/metadata`)

`contract_version, generated_at_utc, as_of_date, plant_timezone, asset_count,
pump_count, cm_count, pm_count, installation_event_count,
installation_report_count, historical_installation_count, mtbf_interval_count,
mtbf_pump_coverage_count, mtbf_pump_population, mtbf_coverage_pct,
mtbf_excluded_same_day_count, mtbf_non_comparable_transition_count,
min_fact_date, max_fact_date, max_rows, largest_table_rows, mttr_available,
mttr_status, snapshot_consistency`. Computed from the same builders as the
tables; for reconciliation, never a KPI source.

## Authorization

- Permission `bi.read`; role `BI_READER` = `{bi.read}` only (code-defined, no
  migration). `SUPERUSER` also holds `bi.read` for verification.
  `SUPERUSER` / `TAP_ADMIN` must not be used as the Power BI identity.
- `BI_READER` is **path-confined** to `/api/ltsa/bi/` centrally in
  `dependencies.get_current_user` (`auth_service.ROLE_PATH_ALLOWLIST`), so it
  cannot reach any other route — including routes that check no permission.
- The R1 dataset is unrestricted by design (TAP management audience; no RLS).
- Unattended Power BI authentication (a non-interactive, revocable machine
  credential) is **not** part of 1.0.0 — it belongs to R1C.
