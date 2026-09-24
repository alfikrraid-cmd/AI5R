"""LTSA_HISTORICAL_CM_BATCH_A_IMPORT_EXECUTOR_R1 -- fail-closed, manifest-driven,
INSERT-ONLY executor for the frozen LTSA Historical CM Batch A dataset
(docs/handoffs/LTSA_HISTORICAL_CM_OVERNIGHT_HANDOFF.md §8).

Order of operations -- every step aborts the run on the first failed gate:

  1. SHA-256 of the manifest file's raw bytes, BEFORE it is parsed. A mismatch
     against the required --expected-sha256 aborts. The manifest is only ever
     read; it is never regenerated, normalized, reformatted or rewritten.
  2. Manifest header + per-row schema validation (pinned Batch A constants,
     exact 21-key measurement schema, tri-state leak booleans, ISO dates,
     unique proposed_source_reference, unique asset+date).
  3. Read-only preflight against the database (every read runs inside
     SET TRANSACTION READ ONLY): api_plan_snapshot column present, baseline,
     source_reference / reading-code collisions, duplicate occurrences,
     asset identity (exactly one asset_registry row, asset_type = PUMP).
     Result: PROPOSED_INSERTS / ALREADY_IMPORTED / UPDATES=0 / DELETES=0.
  4. (apply only) Transactional batches. Each batch is ONE script:
     BEGIN -> LOCK -> DO-block precheck -> one multi-row INSERT -> DO-block
     postcheck -> COMMIT (the create_ad_hoc_batch() idiom of
     condition_monitoring_reading_repository.py). Any error aborts the batch
     transaction, so the batch rolls back as a whole, and the run stops.
  5. (apply only) Post-import invariants and a second preflight that must
     propose 0 inserts.

Write surface -- by construction, and re-asserted on every write script by
_assert_insert_only(): INSERT INTO condition_monitoring_reading only. No
UPDATE, no DELETE, no ON CONFLICT (so no UPSERT), no write to asset_registry,
ltsa_pumps or any other table. api_plan_snapshot is written from the manifest
row only -- never read from, or defaulted to, the master ltsa_pumps.api_plan.
Measurement values are written exactly as the manifest carries them:
true stays TRUE, false stays FALSE, null stays NULL.

Idempotency key: proposed_source_reference -> condition_monitoring_reading.
source_reference. A live row that already carries a manifest reference and
is identical to its manifest row is ALREADY_IMPORTED and skipped (never
updated). Anything else carrying that reference aborts the run. A partial
import (some rows present, some not) aborts unless --allow-resume is given.

Transport: DatabaseConfig/DatabaseRunner from ltsa_pump_inventory_db_upsert.py
(the same docker-compose-exec-psql / direct-connect runner every historical
ingestion CLI uses) -- no second database connection mechanism.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Protocol

from ltsa_hoc_pm_cm_upsert import build_unscheduled_reference
from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, _sql

EXECUTOR_NAME = "ltsa_historical_cm_batch_a_import_executor"
EXECUTOR_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Frozen Batch A contract (handoff §8.1). Never read from the environment.
# ---------------------------------------------------------------------------

BATCH_A_MANIFEST_NAME = "LTSA_HISTORICAL_CM_BATCH_A"
# R2 (ltsa_historical_cm_batch_a_import_manifest_r2_api_plan.json) is the only
# manifest a real apply accepts; R1 is SUPERSEDED (handoff §8.7).
BATCH_A_MANIFEST_SHA256 = "54668aca38b285d85b204e0ebf6b45eaef4a8b94b660823c9cc8d2ef052581d8"
BATCH_A_ROW_COUNT = 2907
BATCH_A_PRODUCTION_BASELINE = 2092
BATCH_A_EXPECTED_TOTAL_AFTER = 4999

SOURCE_REFERENCE_PREFIX = "ltsa_hist_cm_pdf:"
_SOURCE_REFERENCE_PATTERN = re.compile(r"^ltsa_hist_cm_pdf:[0-9a-f]{16}:p\d+:r\d+$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NUMERIC_TEXT = re.compile(r"^\s*-?\d+([.,]\d+)?\s*$")

READING_CODE_PREFIX = "LTSA-CMONR-HISTPDF-"
PROVENANCE = "HISTORICAL_IMPORT"
# Same "fully processed historical actual work" status the existing
# historical XLSX importer writes (ltsa_hoc_pm_cm_db_upsert.apply_plan).
WORKFLOW_STATUS = "FINALIZED"
REQUIRED_ASSET_TYPE = "PUMP"

# Excluded from Batch A by the Chief Architect's source decisions (handoff §6,
# §8.3). A row carrying one of these is never importable, whatever the hash.
EXCLUDED_TAGS = frozenset({"DMI-P-201A", "DMI-P-201B", "701-MM-51", "702-MM-51", "140-P-3B"})
EXCLUDED_AREAS = frozenset({"HSC_SPK"})

# The 20 FORMAT_A measurement columns + pump_operating_state (handoff §8.1).
NUMERIC_FIELDS = (
    "flushing_temp_de", "flushing_temp_nde",
    "quench_temp_de", "quench_temp_nde",
    "flushing_in_temp_de", "flushing_in_temp_nde",
    "flushing_out_temp_de", "flushing_out_temp_nde",
    "cooling_water_in_temp_de", "cooling_water_in_temp_nde",
    "cooling_water_out_temp_de", "cooling_water_out_temp_nde",
    "mechseal_temp_de", "mechseal_temp_nde",
    "water_jacket_temp_de", "water_jacket_temp_nde",
    "suction_temp", "discharge_temp",
)
LEAK_FIELDS = ("mechanical_seal_leak_de", "mechanical_seal_leak_nde")
TEXT_FIELDS = ("pump_operating_state",)
MEASUREMENT_FIELDS = NUMERIC_FIELDS + LEAK_FIELDS + TEXT_FIELDS

REQUIRED_HEADER_KEYS = (
    "manifest", "row_count", "production_total_cm_at_planning", "expected_total_cm_after", "insert_only", "rows",
)
REQUIRED_ROW_KEYS = (
    "proposed_source_reference", "source_hash", "source_document", "source_page", "source_row",
    "tag", "asset_code", "reading_date", "year", "month", "area", "api_plan_snapshot", "measurements",
)

# Column order of the one INSERT statement. api_plan_snapshot comes from the
# manifest row; nothing in this list is ever derived from another table.
INSERT_COLUMNS = (
    "condition_monitoring_reading_code", "condition_monitoring_schedule_code",
    "asset_code", "asset_type", "reading_date",
    *MEASUREMENT_FIELDS,
    "workflow_status", "provenance", "source_reference",
    "source_workbook_name", "source_row_number", "api_plan_snapshot",
)

DEFAULT_BATCH_SIZE = 250
_READ_CHUNK = 300  # keeps each read query well under a Windows command line


class ExecutorAbort(RuntimeError):
    """A fail-closed gate refused to continue. `code` is machine-readable."""

    def __init__(self, code: str, message: str, details: Any = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.details = details


class BatchFailed(ExecutorAbort):
    pass


# ---------------------------------------------------------------------------
# 1. Manifest: hash first, then parse
# ---------------------------------------------------------------------------


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_manifest_bytes_verified(path: Path, expected_sha256: str) -> tuple[bytes, str]:
    """Returns (raw bytes, actual hash). Nothing is parsed before the hash
    comparison; the file is opened read-only and never written."""
    expected = (expected_sha256 or "").strip().lower()
    if not _SHA256_PATTERN.match(expected):
        raise ExecutorAbort("EXPECTED_SHA256_INVALID", "--expected-sha256 must be 64 lowercase hex characters")
    if not path.is_file():
        raise ExecutorAbort("MANIFEST_NOT_FOUND", f"manifest not found: {path}")
    data = path.read_bytes()
    actual = sha256_bytes(data)
    if actual != expected:
        raise ExecutorAbort(
            "MANIFEST_HASH_MISMATCH",
            "manifest SHA-256 does not match the expected hash; nothing was parsed",
            {"expected": expected, "actual": actual},
        )
    return data, actual


@dataclass(frozen=True)
class ManifestRow:
    index: int
    source_reference: str
    reading_code: str
    asset_code: str
    reading_date: str
    api_plan_snapshot: str | None
    measurements: dict[str, Any]
    source_document: str
    source_row: int
    raw: dict[str, Any] = field(repr=False, compare=False)


@dataclass(frozen=True)
class Manifest:
    sha256: str
    name: str
    row_count: int
    baseline: int
    expected_total_after: int
    rows: tuple[ManifestRow, ...]


def build_reading_code(source_reference: str) -> str:
    """Deterministic, collision-checked identity derived from the idempotency
    key, with its own prefix (same convention as the V2 / HCCJUNE codes)."""
    digest = hashlib.sha1(source_reference.encode("utf-8")).hexdigest()[:16].upper()
    return f"{READING_CODE_PREFIX}{digest}"


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _validate_measurements(measurements: Any) -> list[str]:
    if not isinstance(measurements, dict):
        return ["measurements is not an object"]
    problems: list[str] = []
    keys = set(measurements)
    missing = sorted(set(MEASUREMENT_FIELDS) - keys)
    unknown = sorted(keys - set(MEASUREMENT_FIELDS))
    if missing:
        problems.append(f"missing measurement keys {missing}")
    if unknown:
        problems.append(f"unknown measurement keys {unknown}")
    for name in NUMERIC_FIELDS:
        value = measurements.get(name)
        if value is not None and not _is_number(value):
            problems.append(f"{name}={value!r} is not a finite number or null")
    for name in LEAK_FIELDS:
        value = measurements.get(name)
        # Tri-state: exactly true / false / null. "Y", 1, 0, "" are malformed.
        if value is not None and not isinstance(value, bool):
            problems.append(f"{name}={value!r} is not true/false/null")
    for name in TEXT_FIELDS:
        value = measurements.get(name)
        if value is not None and not isinstance(value, str):
            problems.append(f"{name}={value!r} is not text or null")
        elif isinstance(value, str) and _NUMERIC_TEXT.match(value):
            # A numeric operating state is the §4 column-shift signature.
            problems.append(f"{name}={value!r} is numeric (column-shift signature)")
    return problems


def _validate_reading_date(row: dict[str, Any], today: date) -> list[str]:
    value = row.get("reading_date")
    if not isinstance(value, str) or not _ISO_DATE_PATTERN.match(value):
        return [f"reading_date={value!r} is not YYYY-MM-DD"]
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return [f"reading_date={value!r} is not a calendar date"]
    problems = []
    if parsed > today:
        problems.append(f"reading_date={value} is in the future")
    if (row.get("year"), row.get("month")) != (parsed.year, parsed.month):
        problems.append(f"reading_date={value} is outside the row's report period {row.get('year')}-{row.get('month')}")
    return problems


def parse_manifest(data: bytes, sha256: str, *, today: date | None = None) -> Manifest:
    """Validates the already hash-verified bytes. Any problem aborts the whole
    manifest -- no row is dropped, repaired or defaulted."""
    today = today or date.today()
    try:
        document = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ExecutorAbort("MANIFEST_UNREADABLE", f"manifest is not UTF-8 JSON: {error}") from error
    if not isinstance(document, dict):
        raise ExecutorAbort("MANIFEST_SCHEMA_INVALID", "manifest root is not an object")

    missing = [key for key in REQUIRED_HEADER_KEYS if key not in document]
    if missing:
        raise ExecutorAbort("MANIFEST_SCHEMA_INVALID", f"manifest header missing keys {missing}")
    header_problems = []
    expected_header = {
        "manifest": BATCH_A_MANIFEST_NAME,
        "row_count": BATCH_A_ROW_COUNT,
        "production_total_cm_at_planning": BATCH_A_PRODUCTION_BASELINE,
        "expected_total_cm_after": BATCH_A_EXPECTED_TOTAL_AFTER,
    }
    for key, expected in expected_header.items():
        if document[key] != expected or isinstance(document[key], bool):
            header_problems.append(f"{key}={document[key]!r} (expected {expected!r})")
    if document["insert_only"] is not True:
        header_problems.append(f"insert_only={document['insert_only']!r} (expected true)")
    rows = document["rows"]
    if not isinstance(rows, list):
        header_problems.append("rows is not a list")
    elif len(rows) != BATCH_A_ROW_COUNT:
        header_problems.append(f"len(rows)={len(rows)} (expected {BATCH_A_ROW_COUNT})")
    if header_problems:
        raise ExecutorAbort("MANIFEST_HEADER_INVALID", "; ".join(header_problems), header_problems)

    problems: list[dict[str, Any]] = []
    parsed_rows: list[ManifestRow] = []
    seen_refs: dict[str, int] = {}
    seen_occurrences: dict[tuple[str, str], int] = {}
    for index, row in enumerate(rows):
        row_problems: list[str] = []
        if not isinstance(row, dict):
            problems.append({"index": index, "problems": ["row is not an object"]})
            continue
        missing_keys = [key for key in REQUIRED_ROW_KEYS if key not in row]
        if missing_keys:
            problems.append({"index": index, "problems": [f"missing keys {missing_keys}"]})
            continue

        ref = row["proposed_source_reference"]
        if not isinstance(ref, str) or not _SOURCE_REFERENCE_PATTERN.match(ref):
            row_problems.append(f"proposed_source_reference={ref!r} is malformed")
        elif ref in seen_refs:
            row_problems.append(f"DUPLICATE_SOURCE_REFERENCE with row {seen_refs[ref]}")
        else:
            seen_refs[ref] = index

        asset_code = row["asset_code"]
        if not isinstance(asset_code, str) or not asset_code or asset_code != asset_code.strip():
            row_problems.append(f"asset_code={asset_code!r} is invalid")
        elif row["tag"] != asset_code:
            row_problems.append(f"asset_code={asset_code!r} differs from tag={row['tag']!r}")
        if str(asset_code) in EXCLUDED_TAGS or str(row["tag"]) in EXCLUDED_TAGS:
            row_problems.append(f"asset {asset_code!r} is excluded from Batch A")
        if str(row["area"]) in EXCLUDED_AREAS:
            row_problems.append(f"area {row['area']!r} is excluded from Batch A")

        row_problems.extend(_validate_reading_date(row, today))
        row_problems.extend(_validate_measurements(row["measurements"]))

        snapshot = row["api_plan_snapshot"]
        if snapshot is not None and (not isinstance(snapshot, str) or not snapshot.strip()):
            row_problems.append(f"api_plan_snapshot={snapshot!r} must be non-empty text or null")
        if not isinstance(row["source_document"], str) or not row["source_document"]:
            row_problems.append("source_document is empty")
        if not isinstance(row["source_row"], int) or isinstance(row["source_row"], bool):
            row_problems.append(f"source_row={row['source_row']!r} is not an integer")

        if isinstance(asset_code, str) and isinstance(row["reading_date"], str):
            occurrence = (asset_code, row["reading_date"])
            if occurrence in seen_occurrences:
                row_problems.append(f"DUPLICATE_OCCURRENCE with row {seen_occurrences[occurrence]}")
            else:
                seen_occurrences[occurrence] = index

        if row_problems:
            problems.append({"index": index, "source_reference": ref, "problems": row_problems})
            continue
        parsed_rows.append(
            ManifestRow(
                index=index,
                source_reference=ref,
                reading_code=build_reading_code(ref),
                asset_code=asset_code,
                reading_date=row["reading_date"],
                api_plan_snapshot=snapshot,
                measurements={name: row["measurements"][name] for name in MEASUREMENT_FIELDS},
                source_document=row["source_document"],
                source_row=row["source_row"],
                raw=row,
            )
        )

    if problems:
        raise ExecutorAbort(
            "MANIFEST_ROWS_INVALID", f"{len(problems)} manifest row(s) failed validation", problems[:50]
        )
    codes = [row.reading_code for row in parsed_rows]
    if len(set(codes)) != len(codes):
        raise ExecutorAbort("READING_CODE_COLLISION", "two source references hash to the same reading code")
    return Manifest(
        sha256=sha256,
        name=document["manifest"],
        row_count=document["row_count"],
        baseline=document["production_total_cm_at_planning"],
        expected_total_after=document["expected_total_cm_after"],
        rows=tuple(parsed_rows),
    )


# ---------------------------------------------------------------------------
# 2. Database port + the Postgres adapter
# ---------------------------------------------------------------------------


class CmImportStore(Protocol):
    def has_column(self, table: str, column: str) -> bool: ...
    def count_total(self) -> int: ...
    def count_with_reference_prefix(self, prefix: str) -> int: ...
    def rows_by_reference_or_code(self, refs: list[str], codes: list[str]) -> list[dict[str, Any]]: ...
    def live_rows_by_occurrence(self, occurrences: list[tuple[str, str]]) -> list[dict[str, Any]]: ...
    def registry_assets(self, asset_codes: list[str]) -> list[dict[str, Any]]: ...
    def preexisting_fingerprint(self, excluded_prefix: str) -> str: ...
    def insert_batch(self, rows: list[ManifestRow], expected_total_before: int) -> None: ...


_FORBIDDEN_WRITE_PATTERNS = (
    re.compile(r"\bUPDATE\s+[\w.\"]+\s+SET\b", re.IGNORECASE),
    re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
    re.compile(r"\bON\s+CONFLICT\b", re.IGNORECASE),
    re.compile(r"\bMERGE\s+INTO\b", re.IGNORECASE),
    re.compile(r"\bTRUNCATE\b", re.IGNORECASE),
    re.compile(r"\b(ALTER|DROP|CREATE)\s+(TABLE|INDEX|TRIGGER|FUNCTION|RULE)\b", re.IGNORECASE),
    re.compile(r"\bINSERT\s+INTO\s+(?!condition_monitoring_reading\b)", re.IGNORECASE),
)


def _assert_insert_only(script: str) -> None:
    """Defense in depth: refuses to send any write script that could mutate
    an existing row or touch a table other than condition_monitoring_reading.
    String literals are blanked first so manifest text cannot trip it."""
    code_only = re.sub(r"'(?:[^']|'')*'", "''", script)
    for pattern in _FORBIDDEN_WRITE_PATTERNS:
        match = pattern.search(code_only)
        if match:
            raise ExecutorAbort("FORBIDDEN_WRITE", f"write script contains forbidden SQL: {match.group(0)!r}")


def _values_row(row: ManifestRow) -> str:
    values: list[Any] = [
        row.reading_code,
        build_unscheduled_reference(row.source_document),
        row.asset_code,
        REQUIRED_ASSET_TYPE,
        row.reading_date,
        *(row.measurements[name] for name in MEASUREMENT_FIELDS),
        WORKFLOW_STATUS,
        PROVENANCE,
        row.source_reference,
        row.source_document,
        row.source_row,
        row.api_plan_snapshot,
    ]
    rendered = [_sql(value) for value in values]
    date_index = INSERT_COLUMNS.index("reading_date")
    rendered[date_index] = f"{rendered[date_index]}::date"
    return "(" + ", ".join(rendered) + ")"


def build_batch_sql(rows: list[ManifestRow], expected_total_before: int) -> str:
    """One atomic script per batch. Any RAISE / SQL error aborts the
    transaction before COMMIT, so the whole batch rolls back."""
    if not rows:
        raise ValueError("empty batch")
    n = len(rows)
    refs_sql = ", ".join(_sql(row.source_reference) for row in rows)
    codes_sql = ", ".join(_sql(row.reading_code) for row in rows)
    occurrences_sql = ", ".join(f"({_sql(row.asset_code)}, {_sql(row.reading_date)}::date)" for row in rows)
    assets_sql = ", ".join(f"({_sql(code)})" for code in sorted({row.asset_code for row in rows}))
    values_sql = ",\n    ".join(_values_row(row) for row in rows)
    script = f"""
BEGIN;
LOCK TABLE condition_monitoring_reading IN SHARE ROW EXCLUSIVE MODE;

DO $$
DECLARE
  v_total BIGINT;
  v_bad INT;
BEGIN
  SELECT count(*) INTO v_total FROM condition_monitoring_reading;
  IF v_total <> {int(expected_total_before)} THEN
    RAISE EXCEPTION 'BASELINE_CHANGED: total % <> expected {int(expected_total_before)}', v_total;
  END IF;
  SELECT count(*) INTO v_bad FROM condition_monitoring_reading
   WHERE source_reference IN ({refs_sql}) OR condition_monitoring_reading_code IN ({codes_sql});
  IF v_bad > 0 THEN
    RAISE EXCEPTION 'SOURCE_REFERENCE_EXISTS: % row(s) already carry a batch reference/code', v_bad;
  END IF;
  SELECT count(*) INTO v_bad FROM condition_monitoring_reading r
    JOIN (VALUES {occurrences_sql}) AS m(asset_code, reading_date)
      ON r.asset_code = m.asset_code AND r.reading_date::date = m.reading_date
   WHERE r.deleted_at IS NULL;
  IF v_bad > 0 THEN
    RAISE EXCEPTION 'DUPLICATE_OCCURRENCE: % live row(s) at a batch asset/date', v_bad;
  END IF;
  SELECT count(*) INTO v_bad FROM (VALUES {assets_sql}) AS m(asset_code)
   WHERE (SELECT count(*) FROM asset_registry a
           WHERE a.asset_code = m.asset_code AND a.asset_type = {_sql(REQUIRED_ASSET_TYPE)}) <> 1
      OR (SELECT count(*) FROM asset_registry a WHERE a.asset_code = m.asset_code) <> 1;
  IF v_bad > 0 THEN
    RAISE EXCEPTION 'INVALID_ASSET: % batch asset(s) not exactly one {REQUIRED_ASSET_TYPE} registry row', v_bad;
  END IF;
END $$;

INSERT INTO condition_monitoring_reading ({", ".join(INSERT_COLUMNS)})
VALUES
    {values_sql};

DO $$
DECLARE
  v_total BIGINT;
  v_mine INT;
BEGIN
  SELECT count(*) INTO v_total FROM condition_monitoring_reading;
  SELECT count(*) INTO v_mine FROM condition_monitoring_reading WHERE source_reference IN ({refs_sql});
  IF v_mine <> {n} OR v_total <> {int(expected_total_before) + n} THEN
    RAISE EXCEPTION 'BATCH_POSTCHECK_FAILED: inserted % of {n}, total %', v_mine, v_total;
  END IF;
END $$;

COMMIT;
"""
    script = script.strip()
    _assert_insert_only(script)
    return script


def _chunks(items: list[Any], size: int) -> Iterable[list[Any]]:
    for start in range(0, len(items), size):
        yield items[start:start + size]


_READBACK_COLUMNS = (
    "condition_monitoring_reading_code, asset_code, asset_type, reading_date::date::text AS reading_date, "
    + ", ".join(MEASUREMENT_FIELDS)
    + ", provenance, workflow_status, source_reference, api_plan_snapshot, deleted_at"
)


class PostgresCmImportStore:
    """Reads run as SET TRANSACTION READ ONLY; the only write is
    insert_batch(), which sends build_batch_sql() through execute_script()."""

    def __init__(self, runner: DatabaseRunner) -> None:
        self._runner = runner

    def _read(self, sql: str) -> str:
        # Explicit read-only transaction, never committed: the runner closes
        # its connection / psql process after the call, which rolls it back.
        # Any write attempted inside it fails with SQLSTATE 25006.
        return self._runner.query_scalar(f"BEGIN TRANSACTION READ ONLY; {sql}")

    def _read_json(self, sql: str) -> list[dict[str, Any]]:
        raw = self._read(f"SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ({sql}) t;")
        return json.loads(raw or "[]")

    def has_column(self, table: str, column: str) -> bool:
        raw = self._read(
            "SELECT count(*) FROM information_schema.columns WHERE table_schema = 'public' "
            f"AND table_name = {_sql(table)} AND column_name = {_sql(column)};"
        )
        return int(raw or 0) == 1

    def count_total(self) -> int:
        return int(self._read("SELECT count(*) FROM condition_monitoring_reading;"))

    def count_with_reference_prefix(self, prefix: str) -> int:
        return int(
            self._read(
                "SELECT count(*) FROM condition_monitoring_reading "
                f"WHERE left(source_reference, {len(prefix)}) = {_sql(prefix)};"
            )
        )

    def rows_by_reference_or_code(self, refs: list[str], codes: list[str]) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for chunk in _chunks(list(zip(refs, codes)), _READ_CHUNK):
            refs_sql = ", ".join(_sql(ref) for ref, _ in chunk)
            codes_sql = ", ".join(_sql(code) for _, code in chunk)
            found.extend(
                self._read_json(
                    f"SELECT {_READBACK_COLUMNS} FROM condition_monitoring_reading "
                    f"WHERE source_reference IN ({refs_sql}) OR condition_monitoring_reading_code IN ({codes_sql})"
                )
            )
        unique = {row["condition_monitoring_reading_code"]: row for row in found}
        return list(unique.values())

    def live_rows_by_occurrence(self, occurrences: list[tuple[str, str]]) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for chunk in _chunks(occurrences, _READ_CHUNK):
            values_sql = ", ".join(f"({_sql(asset)}, {_sql(day)}::date)" for asset, day in chunk)
            found.extend(
                self._read_json(
                    f"SELECT r.condition_monitoring_reading_code, r.asset_code, r.reading_date::date::text AS reading_date, "
                    f"r.source_reference FROM condition_monitoring_reading r "
                    f"JOIN (VALUES {values_sql}) AS m(asset_code, reading_date) "
                    "ON r.asset_code = m.asset_code AND r.reading_date::date = m.reading_date "
                    "WHERE r.deleted_at IS NULL"
                )
            )
        return found

    def registry_assets(self, asset_codes: list[str]) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for chunk in _chunks(sorted(set(asset_codes)), _READ_CHUNK):
            codes_sql = ", ".join(_sql(code) for code in chunk)
            found.extend(
                self._read_json(f"SELECT asset_code, asset_type FROM asset_registry WHERE asset_code IN ({codes_sql})")
            )
        return found

    def preexisting_fingerprint(self, excluded_prefix: str) -> str:
        return self._read(
            "SELECT count(*)::text || ':' || COALESCE(md5(string_agg(md5(t::text), ',' "
            "ORDER BY t.condition_monitoring_reading_code)), '') FROM condition_monitoring_reading t "
            f"WHERE left(t.source_reference, {len(excluded_prefix)}) IS DISTINCT FROM {_sql(excluded_prefix)};"
        )

    def insert_batch(self, rows: list[ManifestRow], expected_total_before: int) -> None:
        self._runner.execute_script(build_batch_sql(rows, expected_total_before))


# ---------------------------------------------------------------------------
# 3. Preflight (read-only)
# ---------------------------------------------------------------------------


def _same_value(expected: Any, actual: Any) -> bool:
    if expected is None or actual is None:
        return expected is None and actual is None
    if isinstance(expected, bool) or isinstance(actual, bool):
        return type(expected) is type(actual) and expected == actual
    if _is_number(expected):
        try:
            return float(actual) == float(expected)
        except (TypeError, ValueError):
            return False
    return expected == actual


def row_matches_manifest(db_row: dict[str, Any], row: ManifestRow) -> list[str]:
    """Field-level comparison of a stored row with its manifest row. Returns
    the list of differing fields (empty == identical)."""
    diffs = []
    expected = {
        "condition_monitoring_reading_code": row.reading_code,
        "asset_code": row.asset_code,
        "asset_type": REQUIRED_ASSET_TYPE,
        "reading_date": row.reading_date,
        "provenance": PROVENANCE,
        "source_reference": row.source_reference,
        "api_plan_snapshot": row.api_plan_snapshot,
        "deleted_at": None,
        **row.measurements,
    }
    for name, value in expected.items():
        actual = db_row.get(name)
        if name == "reading_date" and isinstance(actual, str):
            actual = actual[:10]
        if not _same_value(value, actual):
            diffs.append(name)
    return diffs


@dataclass
class PreflightResult:
    total_now: int
    baseline_now: int
    already_imported: list[str]
    proposed: list[ManifestRow]
    issues: list[dict[str, Any]]

    def summary(self, manifest: Manifest) -> dict[str, Any]:
        return {
            "CURRENT_TOTAL_CM": self.total_now,
            "EXPECTED_BASELINE": manifest.baseline,
            "BASELINE_EXCLUDING_MANIFEST_ROWS": self.baseline_now,
            "MANIFEST_ROWS": len(manifest.rows),
            "ALREADY_IMPORTED": len(self.already_imported),
            "PROPOSED_INSERTS": len(self.proposed),
            "UPDATES": 0,
            "DELETES": 0,
            "EXPECTED_TOTAL_AFTER": manifest.expected_total_after,
            "PROJECTED_TOTAL_AFTER": self.total_now + len(self.proposed),
            "ISSUES": len(self.issues),
        }


def preflight(manifest: Manifest, store: CmImportStore, *, allow_resume: bool = False) -> PreflightResult:
    """Read-only. Collects every issue, then aborts if there is any."""
    issues: list[dict[str, Any]] = []

    if not store.has_column("condition_monitoring_reading", "api_plan_snapshot"):
        raise ExecutorAbort(
            "SCHEMA_MISSING_API_PLAN_SNAPSHOT",
            "condition_monitoring_reading.api_plan_snapshot is absent (migration 038 not applied)",
        )

    rows = list(manifest.rows)
    by_ref = {row.source_reference: row for row in rows}
    by_code = {row.reading_code: row for row in rows}

    existing = store.rows_by_reference_or_code([r.source_reference for r in rows], [r.reading_code for r in rows])
    rows_per_ref: dict[str, list[dict[str, Any]]] = {}
    for db_row in existing:
        ref = db_row.get("source_reference")
        code = db_row.get("condition_monitoring_reading_code")
        if ref in by_ref:
            rows_per_ref.setdefault(ref, []).append(db_row)
        if code in by_code and by_code[code].source_reference != ref:
            issues.append({"code": "READING_CODE_EXISTS", "reading_code": code, "existing_source_reference": ref})

    already: list[str] = []
    for ref, db_rows in rows_per_ref.items():
        if len(db_rows) != 1:
            issues.append({"code": "SOURCE_REFERENCE_EXISTS", "source_reference": ref, "rows": len(db_rows)})
            continue
        diffs = row_matches_manifest(db_rows[0], by_ref[ref])
        if diffs:
            issues.append({"code": "SOURCE_REFERENCE_EXISTS", "source_reference": ref, "differs": diffs})
        else:
            already.append(ref)
    already_set = set(already)

    live = store.live_rows_by_occurrence([(row.asset_code, row.reading_date) for row in rows])
    by_occurrence = {(row.asset_code, row.reading_date): row for row in rows}
    for db_row in live:
        manifest_row = by_occurrence.get((db_row["asset_code"], db_row["reading_date"][:10]))
        if manifest_row is None:
            continue
        own = db_row.get("source_reference") == manifest_row.source_reference and manifest_row.source_reference in already_set
        if not own:
            issues.append(
                {
                    "code": "DUPLICATE_OCCURRENCE",
                    "source_reference": manifest_row.source_reference,
                    "asset_code": manifest_row.asset_code,
                    "reading_date": manifest_row.reading_date,
                    "existing_reading_code": db_row.get("condition_monitoring_reading_code"),
                }
            )

    registry: dict[str, list[dict[str, Any]]] = {}
    for asset in store.registry_assets([row.asset_code for row in rows]):
        registry.setdefault(asset["asset_code"], []).append(asset)
    for asset_code in sorted({row.asset_code for row in rows}):
        entries = registry.get(asset_code, [])
        if len(entries) != 1 or entries[0].get("asset_type") != REQUIRED_ASSET_TYPE:
            issues.append(
                {
                    "code": "INVALID_ASSET",
                    "asset_code": asset_code,
                    "registry_rows": len(entries),
                    "asset_type": entries[0].get("asset_type") if len(entries) == 1 else None,
                }
            )

    total_now = store.count_total()
    baseline_now = total_now - len(already)
    if baseline_now != manifest.baseline:
        issues.append(
            {
                "code": "BASELINE_CHANGED",
                "expected_baseline": manifest.baseline,
                "baseline_excluding_manifest_rows": baseline_now,
                "current_total": total_now,
                "action": "ABORT / REPLAN",
            }
        )
    prefixed = store.count_with_reference_prefix(SOURCE_REFERENCE_PREFIX)
    if prefixed != len(already):
        issues.append(
            {"code": "FOREIGN_BATCH_REFERENCES", "rows_with_prefix": prefixed, "manifest_rows_present": len(already)}
        )
    if already and len(already) != len(rows) and not allow_resume:
        issues.append({"code": "PARTIAL_IMPORT_DETECTED", "already_imported": len(already), "manifest_rows": len(rows)})

    proposed = [row for row in rows if row.source_reference not in already_set]
    result = PreflightResult(total_now, baseline_now, already, proposed, issues)
    if issues:
        raise ExecutorAbort("PREFLIGHT_FAILED", f"{len(issues)} preflight issue(s)", {"issues": issues[:100], "summary": result.summary(manifest)})
    return result


# ---------------------------------------------------------------------------
# 4. Apply (transactional batches) + post-import verification
# ---------------------------------------------------------------------------


def apply(
    manifest: Manifest,
    store: CmImportStore,
    plan: PreflightResult,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    if batch_size < 1:
        raise ExecutorAbort("BATCH_SIZE_INVALID", "batch size must be >= 1")
    fingerprint_before = store.preexisting_fingerprint(SOURCE_REFERENCE_PREFIX)
    expected_total = plan.total_now
    committed_batches = 0
    committed_rows = 0
    batches = list(_chunks(plan.proposed, batch_size))
    for number, batch in enumerate(batches, 1):
        try:
            store.insert_batch(batch, expected_total)
        except Exception as error:  # the batch transaction never reached COMMIT
            try:
                total_after_failure: int | None = store.count_total()
            except Exception:  # database unreachable: report unknown, never assume
                total_after_failure = None
            raise BatchFailed(
                "BATCH_FAILED",
                f"batch {number}/{len(batches)} failed and was rolled back; run stopped",
                {
                    "failed_batch": number,
                    "batches_total": len(batches),
                    "committed_batches": committed_batches,
                    "committed_rows": committed_rows,
                    "expected_total_after_rollback": expected_total,
                    "total_after_failure": total_after_failure,
                    "rolled_back_cleanly": total_after_failure == expected_total,
                    "error": str(error)[-2000:],
                },
            ) from error
        committed_batches += 1
        committed_rows += len(batch)
        expected_total += len(batch)

    verification = verify_post_import(manifest, store, fingerprint_before)
    return {
        "batches": len(batches),
        "batch_size": batch_size,
        "committed_batches": committed_batches,
        "inserted": committed_rows,
        "verification": verification,
    }


def verify_post_import(manifest: Manifest, store: CmImportStore, fingerprint_before: str) -> dict[str, Any]:
    problems = []
    total = store.count_total()
    if total != manifest.baseline + len(manifest.rows):
        problems.append(f"total {total} <> baseline {manifest.baseline} + {len(manifest.rows)}")
    fingerprint_after = store.preexisting_fingerprint(SOURCE_REFERENCE_PREFIX)
    if fingerprint_after != fingerprint_before:
        problems.append("pre-existing rows changed")
    stored = store.rows_by_reference_or_code(
        [row.source_reference for row in manifest.rows], [row.reading_code for row in manifest.rows]
    )
    per_ref: dict[str, list[dict[str, Any]]] = {}
    for db_row in stored:
        per_ref.setdefault(db_row.get("source_reference"), []).append(db_row)
    mismatched = 0
    for row in manifest.rows:
        found = per_ref.get(row.source_reference, [])
        if len(found) != 1 or row_matches_manifest(found[0], row):
            mismatched += 1
    if mismatched:
        problems.append(f"{mismatched} manifest row(s) not present exactly once with identical values")
    second = preflight(manifest, store)
    if second.proposed:
        problems.append(f"second dry run proposes {len(second.proposed)} insert(s)")
    result = {
        "TOTAL_AFTER": total,
        "PREEXISTING_ROWS_UNCHANGED": fingerprint_after == fingerprint_before,
        "MANIFEST_ROWS_IDENTICAL": mismatched == 0,
        "SECOND_DRY_RUN_PROPOSED_INSERTS": len(second.proposed),
    }
    if problems:
        raise ExecutorAbort("POST_IMPORT_VERIFICATION_FAILED", "; ".join(problems), result)
    return result


# ---------------------------------------------------------------------------
# 5. CLI
# ---------------------------------------------------------------------------


def verify_backup(path: Path | None, expected_sha256: str | None) -> dict[str, Any]:
    if path is None or not expected_sha256:
        raise ExecutorAbort("BACKUP_REQUIRED", "apply requires --backup-file and --backup-sha256")
    if not path.is_file() or path.stat().st_size == 0:
        raise ExecutorAbort("BACKUP_MISSING", f"backup file missing or empty: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    actual = digest.hexdigest()
    if actual != expected_sha256.strip().lower():
        raise ExecutorAbort("BACKUP_HASH_MISMATCH", "backup checksum does not match", {"actual": actual})
    return {"BACKUP_PATH": str(path), "BACKUP_SHA256": actual, "BACKUP_BYTES": path.stat().st_size}


def run(args: argparse.Namespace, store: CmImportStore | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {"EXECUTOR": EXECUTOR_NAME, "VERSION": EXECUTOR_VERSION, "MODE": args.mode}
    data, actual = read_manifest_bytes_verified(args.manifest, args.expected_sha256)
    report["MANIFEST_SHA256"] = actual
    report["HASH_VERIFICATION"] = "PASS"
    manifest = parse_manifest(data, actual)
    report["MANIFEST_VALIDATION"] = "PASS"

    if args.mode == "apply":
        if actual != BATCH_A_MANIFEST_SHA256:
            raise ExecutorAbort("NOT_FROZEN_MANIFEST", "apply only runs on the frozen Batch A manifest hash")
        if args.confirm_production_write != BATCH_A_MANIFEST_NAME:
            raise ExecutorAbort(
                "WRITE_NOT_CONFIRMED", f"apply requires --confirm-production-write {BATCH_A_MANIFEST_NAME}"
            )
        report["BACKUP"] = verify_backup(args.backup_file, args.backup_sha256)

    if store is None:
        store = PostgresCmImportStore(
            DatabaseRunner(
                DatabaseConfig(
                    env_file=args.env_file, compose_file=args.compose_file, service=args.service,
                    user=args.db_user, database=args.database,
                )
            )
        )
    plan = preflight(manifest, store, allow_resume=args.allow_resume)
    report["PREFLIGHT"] = plan.summary(manifest)

    if args.mode == "apply":
        expected_inserts = args.expected_inserts
        if expected_inserts is None or expected_inserts != len(plan.proposed):
            raise ExecutorAbort(
                "PROPOSED_INSERTS_MISMATCH",
                f"--expected-inserts {expected_inserts} <> proposed {len(plan.proposed)}",
            )
        report["APPLY"] = apply(manifest, store, plan, batch_size=args.batch_size)
    report["STATUS"] = "PASS"
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LTSA Historical CM Batch A insert-only import executor")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--mode", choices=("dry-run", "apply"), default="dry-run")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--compose-file", type=Path)
    parser.add_argument("--service", default="postgres")
    parser.add_argument("--db-user", default="ai5r")
    parser.add_argument("--database", default="ltsa_brain")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--allow-resume", action="store_true")
    parser.add_argument("--expected-inserts", type=int)
    parser.add_argument("--backup-file", type=Path)
    parser.add_argument("--backup-sha256")
    parser.add_argument("--confirm-production-write")
    parser.add_argument("--report", type=Path, help="write the JSON report here (never next to the manifest)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run(args)
        exit_code = 0
    except ExecutorAbort as abort:
        report = {"EXECUTOR": EXECUTOR_NAME, "MODE": args.mode, "STATUS": "ABORTED", "ABORT_CODE": abort.code,
                  "MESSAGE": str(abort), "DETAILS": abort.details}
        exit_code = 2
    text = json.dumps(report, indent=2, default=str)
    if args.report:
        if args.report.resolve() == args.manifest.resolve():
            print("refusing to overwrite the manifest with the report", file=sys.stderr)
            return 2
        args.report.write_text(text, encoding="utf-8")
    print(text)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
