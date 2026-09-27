"""LTSA_HISTORICAL_INSTALLATION_2024_2025_IMPORT_IMPLEMENTATION_R1 -- governed,
insert-only import of APPROVED historical mechanical-seal installation evidence
(Service Activity 2024/2025) into public.historical_seal_service_activity
(migration 036 + 039).

Supersedes historical_seal_service_activity_ingestion.py (DEPRECATED) for any
governed import. Rules:

1. The input is ONLY the approved, hash-frozen manifest. Its SHA-256 is
   computed from the raw file bytes before anything is parsed; the file is
   never rewritten. Review-queue rows are rejected, never imported.
2. Every row is re-validated: evidence grade, exact asset resolution,
   dedup status, event type, position, date-correction consistency, and the
   deterministic historical_event_id / source_fingerprint / event_fingerprint
   are recomputed and must match. No fallback asset matching, no alias,
   no suffix inference, no date re-derivation.
3. Preflight is read-only and classifies each row as PROPOSED_INSERT,
   ALREADY_IMPORTED (same fingerprint, identical governed payload) or
   CONFLICT (fingerprint/reference/event collision with different content,
   or a governed installation_report on the same pump and date). Any CONFLICT
   aborts. A pump must be exactly one asset_registry PUMP row and exist in
   ltsa_pumps (the table's FK target).
4. Dry run is the default. Apply requires --apply, the frozen approved
   manifest hash, --expected-rows, --expected-inserts equal to the proposed
   count, and --confirm-historical-installation-import <manifest sha256>.
5. Apply is ONE transaction: lock, in-database precheck, one multi-row
   INSERT, in-database postcheck, COMMIT. Any failure rolls back everything;
   there is no partial import, no retry loop and no fuzzy recovery.
6. History only: nothing here reads or writes installation_report, Current
   Installation, Service Age or CM data (installation_report is only READ to
   detect a same-pump/same-date conflict).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Protocol

_INGESTION_DIR = Path(__file__).resolve().parent
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, _sql  # noqa: E402

EXECUTOR_NAME = "historical_installation_manifest_executor"
EXECUTOR_VERSION = "R1"
# The approved manifest (88 rows, UTF-8, LF) frozen by the import design gate.
APPROVED_MANIFEST_SHA256 = "6bae2f112a0a3d23b034b364c1ec81eef3118df063376a6f0361abcaf6fe718d"
APPROVED_MANIFEST_ROWS = 88

TABLE = "public.historical_seal_service_activity"
ALLOWED_GRADES = frozenset({"DIRECT_EVIDENCE", "CORROBORATED"})
ALLOWED_ASSET_STATUSES = frozenset({"EXACT_ASSET_MATCH", "CANONICAL_FORMAT_MATCH"})
ALLOWED_EVENT_TYPES = frozenset({"INSTALLATION", "REINSTALLATION_REFURBISHED_SEAL"})
ALLOWED_POSITIONS = frozenset({"DE", "NDE", "PUMP_LEVEL"})
ALLOWED_CORRECTION_STATUSES = frozenset({"NOT_REQUIRED", "APPROVED"})
APPROVED_CORRECTION_REASONS = frozenset({"DAY_MONTH_SWAP"})
REVIEW_MARKERS = ("review_id", "review_reason", "recommended_human_action", "candidate_assets")
REQUIRED_FIELDS = (
    "historical_event_id", "pump_tag", "asset_registry_id", "event_date", "event_type", "position",
    "seal_type_raw", "seal_size_raw", "api_plan_raw", "position_source_raw", "position_extraction_reason",
    "source_year", "source_document", "source_sheet", "source_row", "source_hash", "source_tag",
    "source_activity", "source_status", "source_remarks", "source_date_raw", "parsed_source_date",
    "corrected_event_date", "date_correction_status", "date_correction_reason", "evidence_grade",
    "asset_resolution_status", "deduplication_status", "source_reference", "source_fingerprint",
    "event_fingerprint", "raw",
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_READ_CHUNK = 200

# Columns written for a governed row (migration 036 + 039).
INSERT_COLUMNS = (
    "source_reference", "source_type", "source_year", "source_filename", "source_worksheet", "source_row",
    "source_job_document_number", "sp_no", "raw_tag", "pump_tag_number", "tag_match_outcome",
    "raw_job_description", "event_type", "failure_attribution", "seal_type", "seal_size", "drawing_number",
    "quantity", "shaft_sleeve_condition", "gland_plate_condition", "team_service", "end_user", "location",
    "ltsa_area", "unit_area", "api_plan", "finish_date", "event_date", "date_status", "status", "remarks",
    "historical_event_id", "source_hash", "source_fingerprint", "event_fingerprint", "position",
    "position_source_raw", "position_extraction_reason", "source_date_raw", "parsed_source_date",
    "corrected_event_date", "date_correction_status", "date_correction_reason", "evidence_grade",
    "deduplication_status", "import_manifest_sha256",
)
# Governed payload compared for idempotency (everything the manifest decides).
COMPARED_COLUMNS = tuple(c for c in INSERT_COLUMNS if c != "import_manifest_sha256")


class ExecutorAbort(RuntimeError):
    def __init__(self, code: str, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint(*parts: Any) -> str:
    return hashlib.sha256("|".join("" if p is None else str(p) for p in parts).encode("utf-8")).hexdigest()


def read_manifest_bytes_verified(path: Path, expected_sha256: str) -> tuple[bytes, str]:
    """(raw bytes, actual hash). Nothing is parsed before the hash matches;
    the file is only read, never written."""
    expected = (expected_sha256 or "").strip().lower()
    if not _SHA256.match(expected):
        raise ExecutorAbort("EXPECTED_SHA256_INVALID", "--expected-sha256 must be 64 lowercase hex characters")
    if not path.is_file():
        raise ExecutorAbort("MANIFEST_NOT_FOUND", f"manifest not found: {path}")
    data = path.read_bytes()
    actual = sha256_bytes(data)
    if actual != expected:
        raise ExecutorAbort("MANIFEST_HASH_MISMATCH", "manifest SHA-256 does not match; nothing was parsed",
                            {"expected": expected, "actual": actual})
    return data, actual


# -- 1. manifest -----------------------------------------------------------------------


@dataclass(frozen=True)
class ManifestRow:
    data: dict[str, Any]

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def db_values(self, manifest_sha256: str) -> dict[str, Any]:
        """The governed row as stored (deterministic mapping; seal values verbatim)."""
        r, raw = self.data, self.data["raw"]
        area = (raw.get("source_area") or "").split(" / ") if raw.get("source_area") else [None, None]
        ltsa_area = area[0] if len(area) == 2 and area[0] not in ("None", "-", "") else None
        unit_area = area[1] if len(area) == 2 and area[1] not in ("None", "-", "") else None
        quantity = raw.get("quantity")
        return {
            "source_reference": r["source_reference"], "source_type": "SERVICE_ACTIVITY",
            "source_year": int(r["source_year"]), "source_filename": r["source_document"],
            "source_worksheet": r["source_sheet"], "source_row": int(r["source_row"]),
            "source_job_document_number": raw.get("job_document_number"), "sp_no": raw.get("sp_po"),
            "raw_tag": r["source_tag"], "pump_tag_number": r["pump_tag"], "tag_match_outcome": r["asset_resolution_status"],
            "raw_job_description": r["source_activity"], "event_type": r["event_type"], "failure_attribution": "UNKNOWN",
            "seal_type": r["seal_type_raw"], "seal_size": r["seal_size_raw"], "drawing_number": raw.get("drawing_number"),
            "quantity": int(quantity) if quantity is not None and str(quantity).strip().isdigit() else None,
            "shaft_sleeve_condition": raw.get("sleeve_condition"), "gland_plate_condition": raw.get("gland_condition"),
            "team_service": raw.get("team"),
            "end_user": raw.get("end_user_or_location") if int(r["source_year"]) == 2024 else None,
            "location": raw.get("end_user_or_location") if int(r["source_year"]) != 2024 else None,
            "ltsa_area": ltsa_area, "unit_area": unit_area, "api_plan": r["api_plan_raw"],
            "finish_date": r["event_date"], "event_date": r["event_date"],
            "date_status": "APPROVED_DAY_MONTH_SWAP" if r["date_correction_status"] == "APPROVED" else "VALID",
            "status": r["source_status"], "remarks": r["source_remarks"],
            "historical_event_id": r["historical_event_id"], "source_hash": r["source_hash"],
            "source_fingerprint": r["source_fingerprint"], "event_fingerprint": r["event_fingerprint"],
            "position": r["position"], "position_source_raw": r["position_source_raw"],
            "position_extraction_reason": r["position_extraction_reason"], "source_date_raw": r["source_date_raw"],
            "parsed_source_date": r["parsed_source_date"], "corrected_event_date": r["corrected_event_date"],
            "date_correction_status": r["date_correction_status"], "date_correction_reason": r["date_correction_reason"],
            "evidence_grade": r["evidence_grade"], "deduplication_status": r["deduplication_status"],
            "import_manifest_sha256": manifest_sha256,
        }


@dataclass(frozen=True)
class Manifest:
    sha256: str
    rows: tuple[ManifestRow, ...]
    sources: dict[str, Any]


def _row_errors(row: dict[str, Any], sources: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if any(marker in row for marker in REVIEW_MARKERS):
        return ["REVIEW_QUEUE_ROW: review-queue rows are never importable"]
    missing = [f for f in REQUIRED_FIELDS if f not in row]
    if missing:
        return [f"MISSING_FIELDS: {missing}"]
    if row["evidence_grade"] not in ALLOWED_GRADES:
        errors.append(f"UNSUPPORTED_EVIDENCE_GRADE: {row['evidence_grade']}")
    if row["asset_resolution_status"] not in ALLOWED_ASSET_STATUSES:
        errors.append(f"UNRESOLVED_ASSET: {row['asset_resolution_status']}")
    if not row["pump_tag"] or row["pump_tag"] != row["asset_registry_id"]:
        errors.append("UNRESOLVED_ASSET: pump_tag missing or not equal to asset_registry_id")
    if row["deduplication_status"] != "DISTINCT_EVENT":
        errors.append(f"UNRESOLVED_DEDUP: {row['deduplication_status']}")
    if row["event_type"] not in ALLOWED_EVENT_TYPES:
        errors.append(f"UNSUPPORTED_EVENT_TYPE: {row['event_type']}")
    if row["position"] not in ALLOWED_POSITIONS:
        errors.append(f"UNSUPPORTED_POSITION: {row['position']}")
    elif row["position"] in ("DE", "NDE") and not row["position_source_raw"]:
        errors.append("POSITION_WITHOUT_EVIDENCE")
    for key in ("event_date", "parsed_source_date"):
        value = row[key]
        if not isinstance(value, str) or not _ISO_DATE.match(value):
            errors.append(f"INVALID_DATE: {key}={value!r}")
        else:
            try:
                date.fromisoformat(value)
            except ValueError:
                errors.append(f"INVALID_DATE: {key}={value!r}")
    status = row["date_correction_status"]
    if status not in ALLOWED_CORRECTION_STATUSES:
        errors.append(f"UNAPPROVED_DATE_CORRECTION: status={status}")
    elif status == "APPROVED":
        if row["date_correction_reason"] not in APPROVED_CORRECTION_REASONS or row["corrected_event_date"] != row["event_date"]:
            errors.append("UNAPPROVED_DATE_CORRECTION: approved correction must be DAY_MONTH_SWAP with corrected_event_date == event_date")
    elif row["corrected_event_date"] is not None or row["date_correction_reason"] is not None or row["event_date"] != row["parsed_source_date"]:
        errors.append("UNAPPROVED_DATE_CORRECTION: event_date differs from parsed_source_date without an approved correction")
    year = str(row["source_year"])
    source = sources.get(year)
    if not source or source.get("sha256") != row["source_hash"]:
        errors.append("SOURCE_HASH_MISMATCH: row source_hash does not match the manifest source for its year")
    expected_source_fp = fingerprint(row["source_hash"], row["source_sheet"], row["source_row"])
    if row["source_fingerprint"] != expected_source_fp:
        errors.append("SOURCE_FINGERPRINT_MISMATCH")
    if row["historical_event_id"] != "HIST-INSTL-" + expected_source_fp[:16].upper():
        errors.append("HISTORICAL_EVENT_ID_MISMATCH")
    if row["event_fingerprint"] != fingerprint(row["pump_tag"], row["event_date"], row["position"], row["event_type"]):
        errors.append("EVENT_FINGERPRINT_MISMATCH")
    return errors


def parse_manifest(data: bytes, sha256: str, *, expected_rows: int) -> Manifest:
    try:
        doc = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ExecutorAbort("MANIFEST_INVALID_JSON", f"manifest is not valid UTF-8 JSON: {error}") from error
    if not isinstance(doc, dict) or not isinstance(doc.get("rows"), list) or not isinstance(doc.get("sources"), dict):
        raise ExecutorAbort("MANIFEST_INVALID_SCHEMA", "manifest must be an object with 'rows' and 'sources'")
    rows = doc["rows"]
    if doc.get("row_count") != len(rows) or len(rows) != expected_rows:
        raise ExecutorAbort("ROW_COUNT_MISMATCH", "row count mismatch",
                            {"declared": doc.get("row_count"), "actual": len(rows), "expected": expected_rows})
    problems: dict[str, list[str]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            problems[f"#{index}"] = ["ROW_NOT_OBJECT"]
            continue
        errors = _row_errors(row, doc["sources"])
        if errors:
            problems[row.get("source_reference") or f"#{index}"] = errors
    for key in ("historical_event_id", "source_fingerprint", "source_reference", "event_fingerprint"):
        seen = Counter(row.get(key) for row in rows if isinstance(row, dict))
        dupes = [value for value, count in seen.items() if count > 1]
        if dupes:
            problems[f"DUPLICATE_{key.upper()}"] = [str(d) for d in dupes]
    if problems:
        raise ExecutorAbort("MANIFEST_ROWS_REJECTED", f"{len(problems)} manifest problem(s)", problems)
    return Manifest(sha256=sha256, rows=tuple(ManifestRow(r) for r in rows), sources=doc["sources"])


# -- 2. database access -------------------------------------------------------------------


class HistoricalInstallationStore(Protocol):
    def has_column(self, table: str, column: str) -> bool: ...
    def count_total(self) -> int: ...
    def existing_rows(self, rows: list[ManifestRow]) -> list[dict[str, Any]]: ...
    def pump_identity(self, pumps: list[str]) -> dict[str, dict[str, int]]: ...
    def governed_installations_on(self, pairs: list[tuple[str, str]]) -> list[dict[str, Any]]: ...
    def insert_all(self, rows: list[ManifestRow], manifest_sha256: str, expected_total_before: int) -> None: ...


_TRANSACTION_STATUS_LINE = "BEGIN"


def _query_result(raw: str) -> str:
    """docker-exec psql prints the command tag of every statement ('BEGIN\\n<result>');
    exactly one leading BEGIN line is dropped. Direct connect returns only the result."""
    lines = raw.splitlines()
    if lines and lines[0].strip() == _TRANSACTION_STATUS_LINE:
        lines = lines[1:]
    result = "\n".join(lines).strip()
    if not result:
        raise ExecutorAbort("READ_RESULT_EMPTY", f"read returned no result: {raw!r}")
    return result


def _chunks(items: list[Any], size: int) -> Iterable[list[Any]]:
    for start in range(0, len(items), size):
        yield items[start:start + size]


_READBACK = ", ".join(
    f"{c}::text AS {c}" if c in ("finish_date", "event_date", "parsed_source_date", "corrected_event_date") else c
    for c in INSERT_COLUMNS
)


def _values_sql(row: ManifestRow, manifest_sha256: str) -> str:
    values = row.db_values(manifest_sha256)
    return "(" + ", ".join(_sql(values[c]) for c in INSERT_COLUMNS) + ", now())"


def _assert_insert_only(script: str) -> None:
    lowered = re.sub(r"'(?:[^']|'')*'", "''", script).lower()
    for forbidden in ("update ", "delete ", "truncate", "drop ", "alter ", "grant ", "revoke "):
        if forbidden in lowered:
            raise ExecutorAbort("NON_INSERT_SQL", f"generated script contains '{forbidden.strip()}'")


def build_insert_sql(rows: list[ManifestRow], manifest_sha256: str, expected_total_before: int) -> str:
    if not rows:
        raise ValueError("no rows")
    n = len(rows)
    fps = ", ".join(_sql(r["source_fingerprint"]) for r in rows)
    refs = ", ".join(_sql(r["source_reference"]) for r in rows)
    ids = ", ".join(_sql(r["historical_event_id"]) for r in rows)
    efps = ", ".join(_sql(r["event_fingerprint"]) for r in rows)
    pumps = ", ".join(f"({_sql(p)})" for p in sorted({r["pump_tag"] for r in rows}))
    pairs = ", ".join(f"({_sql(r['pump_tag'])}, {_sql(r['event_date'])})" for r in rows)
    values = ",\n    ".join(_values_sql(r, manifest_sha256) for r in rows)
    script = f"""
BEGIN;
LOCK TABLE {TABLE} IN SHARE ROW EXCLUSIVE MODE;

DO $$
DECLARE v_total BIGINT; v_bad INT;
BEGIN
  SELECT count(*) INTO v_total FROM {TABLE};
  IF v_total <> {int(expected_total_before)} THEN
    RAISE EXCEPTION 'BASELINE_CHANGED: total % <> expected {int(expected_total_before)}', v_total;
  END IF;
  SELECT count(*) INTO v_bad FROM {TABLE}
   WHERE source_fingerprint IN ({fps}) OR source_reference IN ({refs})
      OR historical_event_id IN ({ids}) OR event_fingerprint IN ({efps});
  IF v_bad > 0 THEN RAISE EXCEPTION 'ALREADY_PRESENT: % row(s) collide with this batch', v_bad; END IF;
  SELECT count(*) INTO v_bad FROM (VALUES {pumps}) AS m(tag)
   WHERE (SELECT count(*) FROM asset_registry a WHERE a.asset_code = m.tag AND a.asset_type = 'PUMP') <> 1
      OR (SELECT count(*) FROM asset_registry a WHERE a.asset_code = m.tag) <> 1
      OR NOT EXISTS (SELECT 1 FROM ltsa_pumps p WHERE p.tag_number = m.tag);
  IF v_bad > 0 THEN RAISE EXCEPTION 'INVALID_ASSET: % pump(s) not exactly one registry PUMP row in ltsa_pumps', v_bad; END IF;
  SELECT count(*) INTO v_bad FROM installation_report ir
    JOIN (VALUES {pairs}) AS m(tag, day) ON ir.pump_tag_number = m.tag AND ir.report_date = m.day;
  IF v_bad > 0 THEN RAISE EXCEPTION 'GOVERNED_INSTALLATION_CONFLICT: % same pump/date installation_report row(s)', v_bad; END IF;
END $$;

INSERT INTO {TABLE} ({", ".join(INSERT_COLUMNS)}, imported_at)
VALUES
    {values};

DO $$
DECLARE v_total BIGINT; v_mine INT;
BEGIN
  SELECT count(*) INTO v_total FROM {TABLE};
  SELECT count(*) INTO v_mine FROM {TABLE} WHERE source_fingerprint IN ({fps});
  IF v_mine <> {n} OR v_total <> {int(expected_total_before) + n} THEN
    RAISE EXCEPTION 'POSTCHECK_FAILED: inserted % of {n}, total %', v_mine, v_total;
  END IF;
END $$;

COMMIT;
""".strip()
    _assert_insert_only(script)
    return script


class PostgresHistoricalInstallationStore:
    """Reads run inside READ ONLY transactions; the only write is insert_all()."""

    def __init__(self, runner: DatabaseRunner) -> None:
        self._runner = runner

    def _read(self, sql: str) -> str:
        return _query_result(self._runner.query_scalar(f"BEGIN TRANSACTION READ ONLY; {sql}"))

    def _read_json(self, sql: str) -> list[dict[str, Any]]:
        return json.loads(self._read(f"SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ({sql}) t;") or "[]")

    def has_column(self, table: str, column: str) -> bool:
        return int(self._read(
            "SELECT count(*) FROM information_schema.columns WHERE table_schema = 'public' "
            f"AND table_name = {_sql(table)} AND column_name = {_sql(column)};"
        )) == 1

    def count_total(self) -> int:
        return int(self._read(f"SELECT count(*) FROM {TABLE};"))

    def existing_rows(self, rows: list[ManifestRow]) -> list[dict[str, Any]]:
        found: dict[str, dict[str, Any]] = {}
        for chunk in _chunks(rows, _READ_CHUNK):
            fps = ", ".join(_sql(r["source_fingerprint"]) for r in chunk)
            refs = ", ".join(_sql(r["source_reference"]) for r in chunk)
            ids = ", ".join(_sql(r["historical_event_id"]) for r in chunk)
            efps = ", ".join(_sql(r["event_fingerprint"]) for r in chunk)
            for row in self._read_json(
                f"SELECT activity_id::text AS activity_id, {_READBACK} FROM {TABLE} "
                f"WHERE source_fingerprint IN ({fps}) OR source_reference IN ({refs}) "
                f"OR historical_event_id IN ({ids}) OR event_fingerprint IN ({efps})"
            ):
                found[row["activity_id"]] = row
        return list(found.values())

    def pump_identity(self, pumps: list[str]) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {}
        for chunk in _chunks(sorted(set(pumps)), _READ_CHUNK):
            tags = ", ".join(f"({_sql(p)})" for p in chunk)
            for row in self._read_json(
                f"SELECT m.tag, (SELECT count(*) FROM asset_registry a WHERE a.asset_code = m.tag) AS registry_rows, "
                f"(SELECT count(*) FROM asset_registry a WHERE a.asset_code = m.tag AND a.asset_type = 'PUMP') AS pump_rows, "
                f"(SELECT count(*) FROM ltsa_pumps p WHERE p.tag_number = m.tag) AS ltsa_pump_rows "
                f"FROM (VALUES {tags}) AS m(tag)"
            ):
                out[row["tag"]] = {k: int(row[k]) for k in ("registry_rows", "pump_rows", "ltsa_pump_rows")}
        return out

    def governed_installations_on(self, pairs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for chunk in _chunks(pairs, _READ_CHUNK):
            values = ", ".join(f"({_sql(p)}, {_sql(d)})" for p, d in chunk)
            found.extend(self._read_json(
                "SELECT ir.installation_code, ir.pump_tag_number, ir.report_date FROM installation_report ir "
                f"JOIN (VALUES {values}) AS m(tag, day) ON ir.pump_tag_number = m.tag AND ir.report_date = m.day"
            ))
        return found

    def insert_all(self, rows: list[ManifestRow], manifest_sha256: str, expected_total_before: int) -> None:
        self._runner.execute_script(build_insert_sql(rows, manifest_sha256, expected_total_before))


# -- 3. preflight ----------------------------------------------------------------------------


def _same(expected: Any, actual: Any) -> bool:
    if expected is None or actual is None:
        return expected is None and actual is None
    return str(expected) == str(actual)


def payload_differences(db_row: dict[str, Any], row: ManifestRow, manifest_sha256: str) -> list[str]:
    values = row.db_values(manifest_sha256)
    return [c for c in COMPARED_COLUMNS if not _same(values[c], db_row.get(c))]


@dataclass
class PreflightResult:
    total_before: int
    proposed: list[ManifestRow] = field(default_factory=list)
    already_imported: list[ManifestRow] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            "TOTAL_BEFORE": self.total_before,
            "PROPOSED_INSERT": len(self.proposed),
            "ALREADY_IMPORTED": len(self.already_imported),
            "CONFLICT": len(self.conflicts),
            "REJECTED": len(self.rejected),
            "CONFLICT_DETAILS": self.conflicts[:50],
            "REJECTED_DETAILS": self.rejected[:50],
        }


def preflight(manifest: Manifest, store: HistoricalInstallationStore) -> PreflightResult:
    for column in ("historical_event_id", "source_fingerprint", "position", "evidence_grade", "date_correction_status"):
        if not store.has_column("historical_seal_service_activity", column):
            raise ExecutorAbort("MIGRATION_039_NOT_APPLIED", f"historical_seal_service_activity.{column} is missing")
    result = PreflightResult(total_before=store.count_total())
    rows = list(manifest.rows)

    identity = store.pump_identity([r["pump_tag"] for r in rows])
    bad_assets = {p: v for p, v in identity.items() if v != {"registry_rows": 1, "pump_rows": 1, "ltsa_pump_rows": 1}}
    for p in {r["pump_tag"] for r in rows} - set(identity):
        bad_assets[p] = {"registry_rows": 0, "pump_rows": 0, "ltsa_pump_rows": 0}
    if bad_assets:
        result.rejected = [{"pump_tag": p, "identity": v, "reason": "UNRESOLVED_ASSET"} for p, v in sorted(bad_assets.items())]
        raise ExecutorAbort("ASSET_RESOLUTION_FAILED", f"{len(bad_assets)} pump(s) not exactly one registry PUMP in ltsa_pumps",
                            result.rejected)

    governed = {(g["pump_tag_number"], g["report_date"]): g["installation_code"]
                for g in store.governed_installations_on([(r["pump_tag"], r["event_date"]) for r in rows])}
    existing = store.existing_rows(rows)
    by_fp = {e.get("source_fingerprint"): e for e in existing if e.get("source_fingerprint")}
    for row in rows:
        key = (row["pump_tag"], row["event_date"])
        if key in governed:
            result.conflicts.append({"source_reference": row["source_reference"], "reason": "GOVERNED_INSTALLATION_SAME_PUMP_DATE",
                                     "installation_code": governed[key]})
            continue
        match = by_fp.get(row["source_fingerprint"])
        others = [e for e in existing if e is not match and (
            e.get("source_reference") == row["source_reference"] or e.get("historical_event_id") == row["historical_event_id"]
            or e.get("event_fingerprint") == row["event_fingerprint"])]
        if others:
            result.conflicts.append({"source_reference": row["source_reference"], "reason": "IDENTITY_COLLISION",
                                     "colliding_rows": [o.get("source_reference") for o in others]})
        elif match is None:
            result.proposed.append(row)
        else:
            diffs = payload_differences(match, row, manifest.sha256)
            if diffs:
                result.conflicts.append({"source_reference": row["source_reference"], "reason": "PAYLOAD_DIFFERS", "columns": diffs})
            else:
                result.already_imported.append(row)
    return result


# -- 4. apply / verify ----------------------------------------------------------------------


def apply(manifest: Manifest, store: HistoricalInstallationStore, plan: PreflightResult) -> dict[str, Any]:
    if plan.conflicts or plan.rejected:
        raise ExecutorAbort("PREFLIGHT_NOT_CLEAN", "apply refused: conflicts or rejections present", plan.summary())
    if not plan.proposed:
        return {"INSERTED": 0, "NOTE": "nothing to insert (all rows already imported)"}
    try:
        store.insert_all(plan.proposed, manifest.sha256, plan.total_before)
    except ExecutorAbort:
        raise
    except Exception as error:  # the single transaction never reached COMMIT
        raise ExecutorAbort("IMPORT_ROLLED_BACK", f"import failed and was rolled back: {error}") from error
    return {"INSERTED": len(plan.proposed)}


def verify_post_import(manifest: Manifest, store: HistoricalInstallationStore) -> dict[str, Any]:
    existing = {e["source_fingerprint"]: e for e in store.existing_rows(list(manifest.rows)) if e.get("source_fingerprint")}
    missing = [r["source_reference"] for r in manifest.rows if r["source_fingerprint"] not in existing]
    mismatched = {r["source_reference"]: d for r in manifest.rows
                  if r["source_fingerprint"] in existing
                  for d in [payload_differences(existing[r["source_fingerprint"]], r, manifest.sha256)] if d}
    if missing or mismatched:
        raise ExecutorAbort("POST_IMPORT_VERIFICATION_FAILED", "imported rows do not match the manifest",
                            {"missing": missing, "mismatched": mismatched})
    return {"VERIFIED_ROWS": len(manifest.rows), "FIELD_IDENTICAL": True, "TABLE_TOTAL": store.count_total()}


# -- 5. entry point ---------------------------------------------------------------------------


def run(args: argparse.Namespace, store: HistoricalInstallationStore | None = None, *,
        approved_manifest_sha256: str = APPROVED_MANIFEST_SHA256) -> dict[str, Any]:
    mode = "apply" if args.apply else "dry-run"
    report: dict[str, Any] = {"EXECUTOR": EXECUTOR_NAME, "VERSION": EXECUTOR_VERSION, "MODE": mode}
    data, actual = read_manifest_bytes_verified(args.manifest, args.expected_sha256)
    report["MANIFEST_SHA256"] = actual
    report["HASH_VERIFICATION"] = "PASS"
    manifest = parse_manifest(data, actual, expected_rows=args.expected_rows)
    report["MANIFEST_VALIDATION"] = "PASS"
    report["MANIFEST_ROWS"] = len(manifest.rows)

    if mode == "apply":
        if actual != approved_manifest_sha256:
            raise ExecutorAbort("NOT_APPROVED_MANIFEST", "apply only runs on the approved, frozen manifest hash")
        if args.confirm_historical_installation_import != actual:
            raise ExecutorAbort("WRITE_NOT_CONFIRMED",
                                "apply requires --confirm-historical-installation-import <manifest sha256>")

    if store is None:
        store = PostgresHistoricalInstallationStore(DatabaseRunner(DatabaseConfig(
            env_file=args.env_file, compose_file=args.compose_file, service=args.service,
            user=args.db_user, database=args.database,
            host=args.host, port=args.port or 5432, password=args.password,
        )))
    plan = preflight(manifest, store)
    report["PREFLIGHT"] = plan.summary()
    if plan.conflicts:
        raise ExecutorAbort("CONFLICTS_PRESENT", f"{len(plan.conflicts)} conflict(s); nothing written", plan.summary())

    if mode == "apply":
        if args.expected_inserts is None or args.expected_inserts != len(plan.proposed):
            raise ExecutorAbort("PROPOSED_INSERTS_MISMATCH",
                                f"--expected-inserts {args.expected_inserts} <> proposed {len(plan.proposed)}")
        report["APPLY"] = apply(manifest, store, plan)
        report["VERIFY"] = verify_post_import(manifest, store)
    report["STATUS"] = "PASS"
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Governed historical installation manifest import (dry run by default)")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-rows", type=int, required=True)
    parser.add_argument("--apply", action="store_true", help="write; default is a read-only dry run")
    parser.add_argument("--expected-inserts", type=int)
    parser.add_argument("--confirm-historical-installation-import")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--compose-file", type=Path)
    parser.add_argument("--service", default="postgres")
    parser.add_argument("--db-user", default="ai5r")
    parser.add_argument("--database", default="ltsa_brain")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--password")
    parser.add_argument("--report", type=Path, help="write the JSON report here (never over the manifest)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run(args)
        code = 0
    except ExecutorAbort as abort:
        report = {"EXECUTOR": EXECUTOR_NAME, "MODE": "apply" if args.apply else "dry-run", "STATUS": "ABORTED",
                  "ABORT_CODE": abort.code, "MESSAGE": str(abort), "DETAILS": abort.details}
        code = 2
    text = json.dumps(report, indent=2, default=str)
    if args.report:
        if args.report.resolve() == args.manifest.resolve():
            print("refusing to overwrite the manifest with the report", file=sys.stderr)
            return 2
        args.report.write_text(text, encoding="utf-8")
    print(text)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
