"""LTSA_HISTORICAL_INSTALLATION_2024_2025_IMPORT_IMPLEMENTATION_R1 -- unit tests
for the governed historical installation manifest executor (no database: an
in-memory store implements the executor's store protocol)."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import pytest

_INGESTION_PATH = Path(__file__).resolve().parents[1]
if str(_INGESTION_PATH) not in sys.path:
    sys.path.insert(0, str(_INGESTION_PATH))

import historical_installation_manifest_executor as ex  # noqa: E402

SOURCE_2024 = "a" * 64
SOURCE_2025 = "b" * 64


def make_row(year, sheet, row_no, pump, event_date, *, position="PUMP_LEVEL", event_type="INSTALLATION",
             seal_type="T48MP", seal_size="1.7/8''", parsed=None, correction=None):
    source_hash = SOURCE_2024 if year == 2024 else SOURCE_2025
    source_fp = ex.fingerprint(source_hash, sheet, row_no)
    return {
        "historical_event_id": "HIST-INSTL-" + source_fp[:16].upper(),
        "pump_tag": pump, "asset_registry_id": pump, "event_date": event_date, "event_type": event_type,
        "position": position, "seal_type_raw": seal_type, "seal_size_raw": seal_size, "api_plan_raw": None,
        "position_source_raw": "Hanya bagian DE" if position != "PUMP_LEVEL" else None,
        "position_extraction_reason": "explicit same-row remark" if position != "PUMP_LEVEL" else "no explicit position -> PUMP_LEVEL",
        "source_year": year, "source_document": f"workbook-{year}.xlsx", "source_sheet": sheet, "source_row": row_no,
        "source_hash": source_hash, "source_tag": pump, "source_activity": "Pemasangan Seal", "source_status": "SELESAI",
        "source_remarks": None,
        "source_date_raw": f"XLSX_DATE:{parsed or event_date}",
        "parsed_source_date": parsed or event_date,
        "corrected_event_date": event_date if correction else None,
        "date_correction_status": "APPROVED" if correction else "NOT_REQUIRED",
        "date_correction_reason": correction,
        "evidence_grade": "DIRECT_EVIDENCE", "asset_resolution_status": "EXACT_ASSET_MATCH",
        "deduplication_status": "DISTINCT_EVENT", "source_reference": f"SERVICE_ACTIVITY:{year}:{sheet}:R{row_no}",
        "source_fingerprint": source_fp,
        "event_fingerprint": ex.fingerprint(pump, event_date, position, event_type),
        "mtbf_interval_eligible": True,
        "raw": {"job_document_number": None, "team": "Andi", "sleeve_condition": "Old", "gland_condition": "Old",
                "basic_seal_condition": None, "quantity": "1", "drawing_number": None, "end_user_or_location": "Workshop",
                "sp_po": None, "start_date_source": None, "failure_date_source": None, "source_area": None},
    }


def base_rows():
    return [
        make_row(2024, "Januari 2024", 9, "701-P-2", "2024-01-11", parsed="2024-11-01", correction="DAY_MONTH_SWAP"),
        make_row(2024, "Mei 2024", 10, "200-P-7A", "2024-05-07", position="DE"),
        make_row(2025, "INSTALLATION REPORT 2025", 27, "220-P-1B", "2025-07-16", event_type="REINSTALLATION_REFURBISHED_SEAL",
                 seal_type="T8B1", seal_size='3.1/2"'),
    ]


def manifest_bytes(rows, *, row_count=None, crlf=False):
    doc = {"phase": "TEST", "sources": {"2024": {"sha256": SOURCE_2024}, "2025": {"sha256": SOURCE_2025}},
           "row_count": len(rows) if row_count is None else row_count, "rows": rows}
    text = json.dumps(doc, indent=1, ensure_ascii=False, sort_keys=True)
    return (text.replace("\n", "\r\n") if crlf else text).encode("utf-8")


class FakeStore:
    def __init__(self, pumps=("701-P-2", "200-P-7A", "220-P-1B"), governed=(), migrated=True, fail_insert=False):
        self.rows: list[dict] = []
        self.pumps = set(pumps)
        self.governed = list(governed)
        self.migrated = migrated
        self.fail_insert = fail_insert
        self.insert_calls = 0

    def has_column(self, table, column):
        return self.migrated

    def count_total(self):
        return len(self.rows)

    def existing_rows(self, rows):
        keys = {k for r in rows for k in (r["source_fingerprint"], r["source_reference"], r["historical_event_id"], r["event_fingerprint"])}
        return [dict(e, activity_id=str(i)) for i, e in enumerate(self.rows)
                if keys & {e.get("source_fingerprint"), e.get("source_reference"), e.get("historical_event_id"), e.get("event_fingerprint")}]

    def pump_identity(self, pumps):
        return {p: ({"registry_rows": 1, "pump_rows": 1, "ltsa_pump_rows": 1} if p in self.pumps
                    else {"registry_rows": 0, "pump_rows": 0, "ltsa_pump_rows": 0}) for p in pumps}

    def governed_installations_on(self, pairs):
        return [g for g in self.governed if (g["pump_tag_number"], g["report_date"]) in set(pairs)]

    def insert_all(self, rows, manifest_sha256, expected_total_before):
        self.insert_calls += 1
        staged = [r.db_values(manifest_sha256) for r in rows]
        if self.fail_insert:
            raise RuntimeError("injected failure inside the transaction")
        self.rows.extend(staged)


def args_for(path, sha, rows, *, apply=False, expected_inserts=None, confirm=None):
    return argparse.Namespace(manifest=path, expected_sha256=sha, expected_rows=rows, apply=apply,
                              expected_inserts=expected_inserts, confirm_historical_installation_import=confirm,
                              env_file=None, compose_file=None, service="postgres", db_user="ai5r", database="ltsa_brain",
                              host=None, port=None, password=None, report=None)


@pytest.fixture
def manifest(tmp_path):
    data = manifest_bytes(base_rows())
    path = tmp_path / "approved.json"
    path.write_bytes(data)
    return path, ex.sha256_bytes(data)


def run(path, sha, store, *, rows=3, **kw):
    return ex.run(args_for(path, sha, rows, **kw), store, approved_manifest_sha256=sha)


# -- happy path + idempotency ------------------------------------------------------------


def test_dry_run_is_default_and_writes_nothing(manifest):
    path, sha = manifest
    store = FakeStore()
    report = run(path, sha, store)
    assert report["MODE"] == "dry-run"
    assert report["PREFLIGHT"]["PROPOSED_INSERT"] == 3 and report["PREFLIGHT"]["ALREADY_IMPORTED"] == 0
    assert store.rows == [] and store.insert_calls == 0


def test_apply_then_rerun_is_idempotent(manifest):
    path, sha = manifest
    store = FakeStore()
    first = run(path, sha, store, apply=True, expected_inserts=3, confirm=sha)
    assert first["APPLY"]["INSERTED"] == 3 and first["VERIFY"]["FIELD_IDENTICAL"] is True
    second = run(path, sha, store)
    assert second["PREFLIGHT"]["PROPOSED_INSERT"] == 0 and second["PREFLIGHT"]["ALREADY_IMPORTED"] == 3
    again = run(path, sha, store, apply=True, expected_inserts=0, confirm=sha)
    assert again["APPLY"]["INSERTED"] == 0 and len(store.rows) == 3


def test_stored_values_preserve_corrections_position_and_verbatim_seal_values(manifest):
    path, sha = manifest
    store = FakeStore()
    run(path, sha, store, apply=True, expected_inserts=3, confirm=sha)
    by_tag = {r["pump_tag_number"]: r for r in store.rows}
    swap = by_tag["701-P-2"]
    assert (swap["event_date"], swap["parsed_source_date"], swap["corrected_event_date"]) == ("2024-01-11", "2024-11-01", "2024-01-11")
    assert (swap["date_correction_status"], swap["date_correction_reason"], swap["date_status"]) == ("APPROVED", "DAY_MONTH_SWAP", "APPROVED_DAY_MONTH_SWAP")
    assert swap["seal_size"] == "1.7/8''"
    assert by_tag["200-P-7A"]["position"] == "DE" and by_tag["200-P-7A"]["position_source_raw"] == "Hanya bagian DE"
    assert by_tag["220-P-1B"]["event_type"] == "REINSTALLATION_REFURBISHED_SEAL" and by_tag["220-P-1B"]["seal_size"] == '3.1/2"'


# -- manifest integrity ------------------------------------------------------------------------


def test_wrong_sha_rejected_before_parsing(manifest):
    path, _ = manifest
    with pytest.raises(ex.ExecutorAbort) as err:
        run(path, "0" * 64, FakeStore())
    assert err.value.code == "MANIFEST_HASH_MISMATCH"


def test_crlf_rewrite_changes_hash_and_is_rejected(tmp_path, manifest):
    _, sha = manifest
    crlf = tmp_path / "crlf.json"
    crlf.write_bytes(manifest_bytes(base_rows(), crlf=True))
    with pytest.raises(ex.ExecutorAbort) as err:
        run(crlf, sha, FakeStore())
    assert err.value.code == "MANIFEST_HASH_MISMATCH"


def test_single_byte_mutation_rejected(tmp_path, manifest):
    path, sha = manifest
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0x01
    mutated = tmp_path / "mutated.json"
    mutated.write_bytes(bytes(data))
    with pytest.raises(ex.ExecutorAbort) as err:
        run(mutated, sha, FakeStore())
    assert err.value.code == "MANIFEST_HASH_MISMATCH"


def test_wrong_expected_row_count_rejected(manifest):
    path, sha = manifest
    with pytest.raises(ex.ExecutorAbort) as err:
        run(path, sha, FakeStore(), rows=88)
    assert err.value.code == "ROW_COUNT_MISMATCH"


def test_declared_row_count_must_match(tmp_path):
    data = manifest_bytes(base_rows(), row_count=4)
    path = tmp_path / "m.json"
    path.write_bytes(data)
    with pytest.raises(ex.ExecutorAbort) as err:
        run(path, ex.sha256_bytes(data), FakeStore())
    assert err.value.code == "ROW_COUNT_MISMATCH"


def _mutated_manifest(tmp_path, mutate):
    rows = base_rows()
    mutate(rows)
    data = manifest_bytes(rows)
    path = tmp_path / "m.json"
    path.write_bytes(data)
    return path, ex.sha256_bytes(data), len(rows)


@pytest.mark.parametrize("name, mutate, expected", [
    ("review row", lambda rows: rows[0].update({"review_id": "REVIEW-1", "review_reason": ["x"]}), "REVIEW_QUEUE_ROW"),
    ("ambiguous asset", lambda rows: rows[0].update({"asset_resolution_status": "AMBIGUOUS_ASSET"}), "UNRESOLVED_ASSET"),
    ("unapproved correction", lambda rows: rows[0].update({"date_correction_status": "PROPOSED"}), "UNAPPROVED_DATE_CORRECTION"),
    ("correction without approval", lambda rows: rows[0].update({"date_correction_status": "NOT_REQUIRED"}), "UNAPPROVED_DATE_CORRECTION"),
    ("unsupported position", lambda rows: rows[1].update({"position": "BOTH"}), "UNSUPPORTED_POSITION"),
    ("unsupported event type", lambda rows: rows[2].update({"event_type": "CLEANING"}), "UNSUPPORTED_EVENT_TYPE"),
    ("unsupported grade", lambda rows: rows[2].update({"evidence_grade": "AMBIGUOUS"}), "UNSUPPORTED_EVIDENCE_GRADE"),
    ("possible duplicate", lambda rows: rows[2].update({"deduplication_status": "POSSIBLE_SAME_EVENT"}), "UNRESOLVED_DEDUP"),
    ("tampered id", lambda rows: rows[2].update({"historical_event_id": "HIST-INSTL-0000000000000000"}), "HISTORICAL_EVENT_ID_MISMATCH"),
    ("tampered source hash", lambda rows: rows[2].update({"source_hash": "c" * 64}), "SOURCE_HASH_MISMATCH"),
])
def test_invalid_rows_rejected(tmp_path, name, mutate, expected):
    path, sha, n = _mutated_manifest(tmp_path, mutate)
    with pytest.raises(ex.ExecutorAbort) as err:
        run(path, sha, FakeStore(), rows=n)
    assert err.value.code == "MANIFEST_ROWS_REJECTED"
    assert expected in json.dumps(err.value.details)


def test_duplicate_source_fingerprint_rejected(tmp_path):
    def mutate(rows):
        rows.append(copy.deepcopy(rows[0]))
    path, sha, n = _mutated_manifest(tmp_path, mutate)
    with pytest.raises(ex.ExecutorAbort) as err:
        run(path, sha, FakeStore(), rows=n)
    assert "DUPLICATE_SOURCE_FINGERPRINT" in err.value.details and "DUPLICATE_HISTORICAL_EVENT_ID" in err.value.details


def test_duplicate_historical_event_id_rejected(tmp_path):
    def mutate(rows):
        rows[1]["historical_event_id"] = rows[0]["historical_event_id"]
    path, sha, n = _mutated_manifest(tmp_path, mutate)
    with pytest.raises(ex.ExecutorAbort) as err:
        run(path, sha, FakeStore(), rows=n)
    assert "DUPLICATE_HISTORICAL_EVENT_ID" in err.value.details


# -- preflight against the database --------------------------------------------------------------


def test_unknown_pump_rejected(manifest):
    path, sha = manifest
    with pytest.raises(ex.ExecutorAbort) as err:
        run(path, sha, FakeStore(pumps=("701-P-2", "200-P-7A")))
    assert err.value.code == "ASSET_RESOLUTION_FAILED"
    assert err.value.details[0]["pump_tag"] == "220-P-1B"


def test_migration_must_be_applied(manifest):
    path, sha = manifest
    with pytest.raises(ex.ExecutorAbort) as err:
        run(path, sha, FakeStore(migrated=False))
    assert err.value.code == "MIGRATION_039_NOT_APPLIED"


def test_same_pump_and_date_as_governed_installation_report_is_a_conflict(manifest):
    path, sha = manifest
    store = FakeStore(governed=[{"installation_code": "INSTL-X", "pump_tag_number": "200-P-7A", "report_date": "2024-05-07"}])
    with pytest.raises(ex.ExecutorAbort) as err:
        run(path, sha, store)
    assert err.value.code == "CONFLICTS_PRESENT"


def test_existing_row_with_different_payload_is_a_conflict(manifest):
    path, sha = manifest
    store = FakeStore()
    run(path, sha, store, apply=True, expected_inserts=3, confirm=sha)
    store.rows[0] = dict(store.rows[0], seal_size='1.7/8"')
    with pytest.raises(ex.ExecutorAbort) as err:
        run(path, sha, store)
    assert err.value.code == "CONFLICTS_PRESENT"
    assert err.value.details["CONFLICT_DETAILS"][0]["reason"] == "PAYLOAD_DIFFERS"


# -- apply guards ---------------------------------------------------------------------------------------


def test_apply_requires_confirmation(manifest):
    path, sha = manifest
    with pytest.raises(ex.ExecutorAbort) as err:
        run(path, sha, FakeStore(), apply=True, expected_inserts=3)
    assert err.value.code == "WRITE_NOT_CONFIRMED"


def test_apply_requires_expected_inserts(manifest):
    path, sha = manifest
    with pytest.raises(ex.ExecutorAbort) as err:
        run(path, sha, FakeStore(), apply=True, expected_inserts=2, confirm=sha)
    assert err.value.code == "PROPOSED_INSERTS_MISMATCH"


def test_apply_refuses_a_manifest_that_is_not_the_approved_one(manifest):
    path, sha = manifest
    with pytest.raises(ex.ExecutorAbort) as err:
        ex.run(args_for(path, sha, 3, apply=True, expected_inserts=3, confirm=sha), FakeStore())
    assert err.value.code == "NOT_APPROVED_MANIFEST"


def test_failed_transaction_imports_nothing(manifest):
    path, sha = manifest
    store = FakeStore(fail_insert=True)
    with pytest.raises(ex.ExecutorAbort) as err:
        run(path, sha, store, apply=True, expected_inserts=3, confirm=sha)
    assert err.value.code == "IMPORT_ROLLED_BACK"
    assert store.rows == []


def test_generated_sql_is_insert_only_and_atomic():
    rows = [ex.ManifestRow(r) for r in base_rows()]
    sql = ex.build_insert_sql(rows, "d" * 64, 0)
    assert sql.startswith("BEGIN;") and sql.endswith("COMMIT;")
    assert sql.count("INSERT INTO public.historical_seal_service_activity") == 1
    assert "1.7/8''''" in sql  # verbatim value, SQL-escaped
    for forbidden in ("UPDATE ", "DELETE ", "TRUNCATE"):
        assert forbidden not in sql.upper().replace("'", "")


def test_approved_constants_match_the_frozen_manifest():
    assert ex.APPROVED_MANIFEST_SHA256 == "6bae2f112a0a3d23b034b364c1ec81eef3118df063376a6f0361abcaf6fe718d"
    assert ex.APPROVED_MANIFEST_ROWS == 88
