"""LTSA_HISTORICAL_CM_BATCH_A_IMPORT_EXECUTOR_R1 -- coverage for
historical_cm_batch_a_import_executor.py without any database.

The frozen Batch A manifest is never committed (and is not on every
machine), so every test builds a SYNTHETIC manifest with the exact frozen
header contract (2,907 rows, baseline 2,092, expected 4,999) and runs the
executor against FakeStore: an in-memory condition_monitoring_reading whose
insert_batch() re-applies the same gates as the SQL precheck and is
all-or-nothing per batch. The generated SQL itself is covered here
statically and against a real Postgres in
test_historical_cm_batch_a_import_executor_real_db.py.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import historical_cm_batch_a_import_executor as executor  # noqa: E402
from historical_cm_batch_a_import_executor import (  # noqa: E402
    BATCH_A_EXPECTED_TOTAL_AFTER,
    BATCH_A_PRODUCTION_BASELINE,
    BATCH_A_ROW_COUNT,
    LEAK_FIELDS,
    MEASUREMENT_FIELDS,
    NUMERIC_FIELDS,
    BatchFailed,
    ExecutorAbort,
    ManifestRow,
    _assert_insert_only,
    build_batch_sql,
    parse_manifest,
    preflight,
    read_manifest_bytes_verified,
    row_matches_manifest,
)

_TODAY = date(2026, 9, 24)
_ASSETS = [f"100-P-{i:03d}A" for i in range(202)]
_LEAK_CYCLE = (True, False, None)


# ---------------------------------------------------------------------------
# Synthetic manifest
# ---------------------------------------------------------------------------


def _measurements(i: int) -> dict:
    values: dict = {}
    for offset, name in enumerate(NUMERIC_FIELDS):
        # Every 5th value is a genuine NULL; others vary per row.
        values[name] = None if (i + offset) % 5 == 0 else round(30 + (i * 7 + offset) % 60 + 0.5 * (offset % 2), 1)
    # DE and NDE cycle at different rates -> every (DE, NDE) combination
    # of true/false/null occurs, proving the two sides stay independent.
    values["mechanical_seal_leak_de"] = _LEAK_CYCLE[i % 3]
    values["mechanical_seal_leak_nde"] = _LEAK_CYCLE[(i // 3) % 3]
    values["pump_operating_state"] = None
    return values


def _manifest_row(i: int) -> dict:
    asset = _ASSETS[i % len(_ASSETS)]
    reading_date = date(2025, 10, 1) + timedelta(days=i // len(_ASSETS))
    document = f"LAPORAN PM CM OKTOBER 2025 {i // 500}.pdf"
    source_hash = hashlib.sha256(document.encode()).hexdigest()
    page, row = 40 + (i % 500) // 25, i % 500 + 1
    return {
        "proposed_source_reference": f"ltsa_hist_cm_pdf:{source_hash[:16]}:p{page}:r{row}",
        "source_hash": source_hash,
        "source_document": document,
        "relative_path": f"2025/{document}",
        "source_page": page,
        "source_report_page": page - 1,
        "source_row": row,
        "source_date": reading_date.strftime("%d-%b-%y"),
        "source_tag": asset,
        "tag": asset,
        "asset_code": asset,
        "reading_date": reading_date.isoformat(),
        "year": reading_date.year,
        "month": reading_date.month,
        "area": "HCC",
        "api_plan_snapshot": None if i % 4 == 0 else ("11/62" if i % 2 else "23/61"),
        "measurements": _measurements(i),
        "measurement_fingerprint": "0" * 64,
        "source_format": "FORMAT_A",
        "xlsx_corroboration": None,
    }


def _manifest_document(rows: list[dict] | None = None) -> dict:
    rows = rows if rows is not None else [_manifest_row(i) for i in range(BATCH_A_ROW_COUNT)]
    return {
        "manifest": "LTSA_HISTORICAL_CM_BATCH_A",
        "row_count": BATCH_A_ROW_COUNT,
        "production_total_cm_at_planning": BATCH_A_PRODUCTION_BASELINE,
        "expected_total_cm_after": BATCH_A_EXPECTED_TOTAL_AFTER,
        "insert_only": True,
        "rows": rows,
    }


def _write(tmp_path: Path, document: dict) -> tuple[Path, str]:
    path = tmp_path / "manifest.json"
    data = json.dumps(document, indent=1).encode("utf-8")
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


def _parse(document: dict):
    data = json.dumps(document).encode("utf-8")
    return parse_manifest(data, hashlib.sha256(data).hexdigest(), today=_TODAY)


@pytest.fixture(scope="module")
def base_document() -> dict:
    return _manifest_document()


@pytest.fixture
def document(base_document) -> dict:
    return copy.deepcopy(base_document)


@pytest.fixture(scope="module")
def manifest(base_document):
    return _parse(base_document)


# ---------------------------------------------------------------------------
# FakeStore -- transactional in-memory condition_monitoring_reading
# ---------------------------------------------------------------------------


class FakeStore:
    def __init__(self, *, baseline: int = BATCH_A_PRODUCTION_BASELINE, has_snapshot_column: bool = True) -> None:
        self.rows: list[dict] = [
            {
                "condition_monitoring_reading_code": f"CMONR-EXIST{n:06d}",
                "asset_code": _ASSETS[n % len(_ASSETS)],
                "asset_type": "PUMP",
                "reading_date": (date(2024, 1, 1) + timedelta(days=n // len(_ASSETS))).isoformat(),
                "source_reference": None if n % 2 else f"document_field_extraction:DFE-{n}",
                "provenance": "MANUAL",
                "deleted_at": None,
                **{name: None for name in MEASUREMENT_FIELDS},
            }
            for n in range(baseline)
        ]
        self.registry = {asset: [{"asset_code": asset, "asset_type": "PUMP"}] for asset in _ASSETS}
        # Master API Plan exists for every pump: it must never leak into a row.
        self.ltsa_pumps = {asset: {"tag_number": asset, "api_plan": "MASTER-PLAN-53B"} for asset in _ASSETS}
        self.has_snapshot_column = has_snapshot_column
        self.fail_on_reference: str | None = None
        self.batches_attempted = 0
        self.statements: list[str] = []

    # -- reads --
    def has_column(self, table, column):
        return self.has_snapshot_column

    def count_total(self):
        return len(self.rows)

    def count_with_reference_prefix(self, prefix):
        return sum(1 for row in self.rows if (row.get("source_reference") or "").startswith(prefix))

    def rows_by_reference_or_code(self, refs, codes):
        refs, codes = set(refs), set(codes)
        return [
            copy.deepcopy(row) for row in self.rows
            if row.get("source_reference") in refs or row["condition_monitoring_reading_code"] in codes
        ]

    def live_rows_by_occurrence(self, occurrences):
        wanted = set(occurrences)
        return [
            copy.deepcopy(row) for row in self.rows
            if row["deleted_at"] is None and (row["asset_code"], row["reading_date"][:10]) in wanted
        ]

    def registry_assets(self, asset_codes):
        return [entry for code in set(asset_codes) for entry in self.registry.get(code, [])]

    def preexisting_fingerprint(self, excluded_prefix):
        kept = [row for row in self.rows if not (row.get("source_reference") or "").startswith(excluded_prefix)]
        return f"{len(kept)}:" + hashlib.md5(json.dumps(kept, sort_keys=True, default=str).encode()).hexdigest()

    # -- the one write --
    def insert_batch(self, rows: list[ManifestRow], expected_total_before: int) -> None:
        self.batches_attempted += 1
        sql = build_batch_sql(rows, expected_total_before)  # also runs _assert_insert_only
        self.statements.append(sql)
        snapshot = copy.deepcopy(self.rows)  # BEGIN
        try:
            if len(self.rows) != expected_total_before:
                raise RuntimeError("BASELINE_CHANGED")
            for row in rows:
                if self.fail_on_reference == row.source_reference:
                    raise RuntimeError("simulated failure inside the INSERT")
                self.rows.append(
                    {
                        "condition_monitoring_reading_code": row.reading_code,
                        "asset_code": row.asset_code,
                        "asset_type": "PUMP",
                        "reading_date": row.reading_date,
                        "source_reference": row.source_reference,
                        "provenance": "HISTORICAL_IMPORT",
                        "api_plan_snapshot": row.api_plan_snapshot,
                        "deleted_at": None,
                        **copy.deepcopy(row.measurements),
                    }
                )
        except Exception:
            self.rows = snapshot  # ROLLBACK
            raise


def _args(path: Path, sha: str, **overrides) -> argparse.Namespace:
    values = dict(
        manifest=path, expected_sha256=sha, mode="dry-run", env_file=None, compose_file=None, service="postgres",
        db_user="ai5r", database="ltsa_brain", batch_size=250, allow_resume=False, expected_inserts=None,
        backup_file=None, backup_sha256=None, confirm_production_write=None, report=None,
    )
    values.update(overrides)
    return argparse.Namespace(**values)


def _abort_code(excinfo) -> str:
    return excinfo.value.code


def _issue_codes(excinfo) -> set[str]:
    return {issue["code"] for issue in excinfo.value.details["issues"]}


# ---------------------------------------------------------------------------
# PASS
# ---------------------------------------------------------------------------


def test_correct_manifest_hash_passes(tmp_path, base_document):
    path, sha = _write(tmp_path, base_document)
    data, actual = read_manifest_bytes_verified(path, sha)
    assert actual == sha and data == path.read_bytes()


def test_manifest_with_2907_valid_rows_parses(manifest):
    assert len(manifest.rows) == BATCH_A_ROW_COUNT == 2907
    assert manifest.baseline == 2092 and manifest.expected_total_after == 4999
    assert len({row.source_reference for row in manifest.rows}) == 2907


def test_dry_run_proposes_2907_inserts_and_no_updates_or_deletes(tmp_path, base_document):
    path, sha = _write(tmp_path, base_document)
    store = FakeStore()
    report = executor.run(_args(path, sha), store=store)
    summary = report["PREFLIGHT"]
    assert report["STATUS"] == "PASS" and report["HASH_VERIFICATION"] == "PASS"
    assert summary["PROPOSED_INSERTS"] == 2907
    assert summary["UPDATES"] == 0 and summary["DELETES"] == 0
    assert summary["CURRENT_TOTAL_CM"] == 2092 and summary["PROJECTED_TOTAL_AFTER"] == 4999
    assert store.batches_attempted == 0 and len(store.rows) == 2092  # dry run wrote nothing


def test_manifest_file_is_never_modified(tmp_path, base_document):
    path, sha = _write(tmp_path, base_document)
    before = path.read_bytes()
    store = FakeStore()
    executor.run(_args(path, sha), store=store)
    plan = preflight(_parse(base_document), store)
    executor.apply(_parse(base_document), store, plan)
    assert path.read_bytes() == before


# ---------------------------------------------------------------------------
# FAIL CLOSED
# ---------------------------------------------------------------------------


def test_hash_mismatch_aborts_before_parsing(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_bytes(b"{ this is not json")
    with pytest.raises(ExecutorAbort) as excinfo:
        executor.run(_args(path, "0" * 64), store=FakeStore())
    # MANIFEST_UNREADABLE would mean the bytes were parsed first.
    assert _abort_code(excinfo) == "MANIFEST_HASH_MISMATCH"


def test_hash_mismatch_on_one_changed_byte(tmp_path, base_document):
    path, sha = _write(tmp_path, base_document)
    data = path.read_bytes()
    path.write_bytes(data.replace(b"11/62", b"11/61", 1))
    with pytest.raises(ExecutorAbort) as excinfo:
        read_manifest_bytes_verified(path, sha)
    assert _abort_code(excinfo) == "MANIFEST_HASH_MISMATCH"


def test_expected_hash_argument_must_be_a_sha256(tmp_path, base_document):
    path, _ = _write(tmp_path, base_document)
    with pytest.raises(ExecutorAbort) as excinfo:
        read_manifest_bytes_verified(path, "")
    assert _abort_code(excinfo) == "EXPECTED_SHA256_INVALID"


def test_baseline_changed_aborts(manifest):
    for baseline in (2091, 2093):
        with pytest.raises(ExecutorAbort) as excinfo:
            preflight(manifest, FakeStore(baseline=baseline))
        assert "BASELINE_CHANGED" in _issue_codes(excinfo)


@pytest.mark.parametrize(
    "key, value",
    [
        ("manifest", "LTSA_HISTORICAL_CM_BATCH_B"),
        ("row_count", 2906),
        ("production_total_cm_at_planning", 2093),
        ("expected_total_cm_after", 5000),
        ("insert_only", False),
    ],
)
def test_header_contract_mismatch_aborts(document, key, value):
    document[key] = value
    with pytest.raises(ExecutorAbort) as excinfo:
        _parse(document)
    assert _abort_code(excinfo) == "MANIFEST_HEADER_INVALID"


def test_row_count_must_match_rows(document):
    document["rows"].pop()
    with pytest.raises(ExecutorAbort) as excinfo:
        _parse(document)
    assert _abort_code(excinfo) == "MANIFEST_HEADER_INVALID"


def test_duplicate_proposed_source_reference_in_manifest_aborts(document):
    document["rows"][10]["proposed_source_reference"] = document["rows"][9]["proposed_source_reference"]
    with pytest.raises(ExecutorAbort) as excinfo:
        _parse(document)
    assert _abort_code(excinfo) == "MANIFEST_ROWS_INVALID"
    assert any("DUPLICATE_SOURCE_REFERENCE" in p for d in excinfo.value.details for p in d["problems"])


def test_duplicate_occurrence_inside_manifest_aborts(document):
    document["rows"][300]["reading_date"] = document["rows"][300 - len(_ASSETS)]["reading_date"]
    with pytest.raises(ExecutorAbort) as excinfo:
        _parse(document)
    assert any("DUPLICATE_OCCURRENCE" in p for d in excinfo.value.details for p in d["problems"])


def test_source_reference_already_present_with_different_row_aborts(manifest):
    store = FakeStore()
    target = manifest.rows[5]
    store.rows[0]["source_reference"] = target.source_reference  # an unrelated production row
    with pytest.raises(ExecutorAbort) as excinfo:
        preflight(manifest, store)
    assert "SOURCE_REFERENCE_EXISTS" in _issue_codes(excinfo)


def test_soft_deleted_row_with_manifest_reference_aborts(manifest):
    store = FakeStore()
    executor.apply(manifest, store, preflight(manifest, store))
    store.rows[-1]["deleted_at"] = "2026-09-24T00:00:00"
    with pytest.raises(ExecutorAbort) as excinfo:
        preflight(manifest, store)
    assert "SOURCE_REFERENCE_EXISTS" in _issue_codes(excinfo)


def test_reading_code_collision_aborts(manifest):
    store = FakeStore()
    store.rows[0]["condition_monitoring_reading_code"] = manifest.rows[7].reading_code
    with pytest.raises(ExecutorAbort) as excinfo:
        preflight(manifest, store)
    assert "READING_CODE_EXISTS" in _issue_codes(excinfo)


def test_duplicate_occurrence_in_production_aborts(manifest):
    store = FakeStore()
    target = manifest.rows[42]
    store.rows[1]["asset_code"], store.rows[1]["reading_date"] = target.asset_code, f"{target.reading_date}T00:00:00"
    with pytest.raises(ExecutorAbort) as excinfo:
        preflight(manifest, store)
    assert "DUPLICATE_OCCURRENCE" in _issue_codes(excinfo)


def test_soft_deleted_occurrence_is_not_a_duplicate(manifest):
    store = FakeStore()
    target = manifest.rows[42]
    store.rows[1].update(asset_code=target.asset_code, reading_date=target.reading_date, deleted_at="2026-01-01")
    assert len(preflight(manifest, store).proposed) == 2907


@pytest.mark.parametrize(
    "registry_entries",
    [
        [],  # asset no longer in asset_registry
        [{"asset_code": "X", "asset_type": ""}],  # exists but not PUMP (701-MM-51 shape)
        [{"asset_code": "X", "asset_type": "pump"}],  # PUMP is matched exactly, never case-folded
        [{"asset_code": "X", "asset_type": "PUMP"}, {"asset_code": "X", "asset_type": "PUMP"}],  # ambiguous
    ],
)
def test_invalid_asset_aborts(manifest, registry_entries):
    store = FakeStore()
    store.registry[_ASSETS[3]] = [{**entry, "asset_code": _ASSETS[3]} for entry in registry_entries]
    with pytest.raises(ExecutorAbort) as excinfo:
        preflight(manifest, store)
    assert "INVALID_ASSET" in _issue_codes(excinfo)


@pytest.mark.parametrize("tag", sorted(executor.EXCLUDED_TAGS))
def test_excluded_tags_abort(document, tag):
    document["rows"][0].update(tag=tag, asset_code=tag, source_tag=tag)
    with pytest.raises(ExecutorAbort) as excinfo:
        _parse(document)
    assert _abort_code(excinfo) == "MANIFEST_ROWS_INVALID"


def test_hsc_spk_area_aborts(document):
    document["rows"][0]["area"] = "HSC_SPK"
    with pytest.raises(ExecutorAbort):
        _parse(document)


def test_asset_code_must_equal_source_tag(document):
    document["rows"][0]["asset_code"] = "P-201A-DMI"  # an alias is never applied
    with pytest.raises(ExecutorAbort):
        _parse(document)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda m: m.update(flushing_in_temp_de="47|44"),  # HSC sub-cell text
        lambda m: m.update(suction_temp="218"),  # numeric text, not a number
        lambda m: m.update(discharge_temp=True),  # bool is not a number
        lambda m: m.update(mechanical_seal_leak_de="Y"),  # raw leak code, not tri-state
        lambda m: m.update(mechanical_seal_leak_nde=0),  # 0/1 is not tri-state
        lambda m: m.update(pump_operating_state="69"),  # §4 column-shift signature
        lambda m: m.update(pump_operating_state=12),
        lambda m: m.pop("mechseal_temp_nde"),  # missing key
        lambda m: m.update(stuffing_box_temp_de=10),  # key outside FORMAT_A
    ],
)
def test_malformed_measurement_aborts(document, mutate):
    mutate(document["rows"][17]["measurements"])
    with pytest.raises(ExecutorAbort) as excinfo:
        _parse(document)
    assert _abort_code(excinfo) == "MANIFEST_ROWS_INVALID"


def test_non_finite_number_aborts(document):
    document["rows"][0]["measurements"]["suction_temp"] = float("nan")
    data = json.dumps(document)  # serializes as the non-standard token NaN
    assert "NaN" in data
    with pytest.raises(ExecutorAbort):
        parse_manifest(data.encode(), hashlib.sha256(data.encode()).hexdigest(), today=_TODAY)


@pytest.mark.parametrize(
    "value",
    ["2025-02-30", "01-Oct-25", "2025/10/01", "2025-10-01T00:00:00", "", None, 20251001, "2027-01-05", "2025-11-01"],
)
def test_invalid_reading_date_aborts(document, value):
    # 2027-01-05 is in the future; 2025-11-01 is outside the row's 2025-10 report period.
    document["rows"][0]["reading_date"] = value
    with pytest.raises(ExecutorAbort) as excinfo:
        _parse(document)
    assert _abort_code(excinfo) == "MANIFEST_ROWS_INVALID"


def test_malformed_source_reference_aborts(document):
    document["rows"][0]["proposed_source_reference"] = "document_field_extraction:DFE-1"
    with pytest.raises(ExecutorAbort):
        _parse(document)


def test_missing_api_plan_snapshot_key_aborts(document):
    del document["rows"][0]["api_plan_snapshot"]
    with pytest.raises(ExecutorAbort):
        _parse(document)


def test_missing_api_plan_snapshot_column_aborts(manifest):
    with pytest.raises(ExecutorAbort) as excinfo:
        preflight(manifest, FakeStore(has_snapshot_column=False))
    assert _abort_code(excinfo) == "SCHEMA_MISSING_API_PLAN_SNAPSHOT"


def test_foreign_rows_with_batch_prefix_abort(manifest):
    store = FakeStore()
    store.rows[0]["source_reference"] = "ltsa_hist_cm_pdf:ffffffffffffffff:p1:r1"
    with pytest.raises(ExecutorAbort) as excinfo:
        preflight(manifest, store)
    assert "FOREIGN_BATCH_REFERENCES" in _issue_codes(excinfo)


# ---------------------------------------------------------------------------
# SEMANTICS
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def imported(manifest):
    store = FakeStore()
    result = executor.apply(manifest, store, preflight(manifest, store))
    by_ref = {row["source_reference"]: row for row in store.rows}
    return store, result, by_ref


def test_leak_true_false_null_are_preserved(manifest, imported):
    _, _, by_ref = imported
    seen = set()
    for row in manifest.rows:
        stored = by_ref[row.source_reference]
        for name in LEAK_FIELDS:
            expected = row.measurements[name]
            assert stored[name] is expected  # identity: True/False/None, never coerced
            seen.add(expected)
    assert seen == {True, False, None}


def test_de_and_nde_leak_are_independent(manifest, imported):
    _, _, by_ref = imported
    pairs = {
        (by_ref[r.source_reference]["mechanical_seal_leak_de"], by_ref[r.source_reference]["mechanical_seal_leak_nde"])
        for r in manifest.rows
    }
    assert pairs == {(de, nde) for de in _LEAK_CYCLE for nde in _LEAK_CYCLE}


def test_null_measurements_remain_null(manifest, imported):
    _, _, by_ref = imported
    nulls = 0
    for row in manifest.rows:
        for name in NUMERIC_FIELDS + ("pump_operating_state",):
            if row.measurements[name] is None:
                assert by_ref[row.source_reference][name] is None
                nulls += 1
    assert nulls > 2907  # NULLs are common and never filled


def test_api_plan_snapshot_preserved_without_master_fallback(manifest, imported):
    store, _, by_ref = imported
    for row in manifest.rows:
        assert by_ref[row.source_reference]["api_plan_snapshot"] == row.api_plan_snapshot
    null_rows = [r for r in manifest.rows if r.api_plan_snapshot is None]
    assert null_rows and all(by_ref[r.source_reference]["api_plan_snapshot"] is None for r in null_rows)
    assert all(pump["api_plan"] == "MASTER-PLAN-53B" for pump in store.ltsa_pumps.values())  # untouched
    assert all("ltsa_pumps" not in sql and "api_plan FROM" not in sql for sql in store.statements)


def test_sql_literals_preserve_tristate_null_and_snapshot():
    row = ManifestRow(
        index=0, source_reference="ltsa_hist_cm_pdf:0123456789abcdef:p1:r1",
        reading_code=executor.build_reading_code("ltsa_hist_cm_pdf:0123456789abcdef:p1:r1"),
        asset_code="100-P-1A", reading_date="2025-10-01", api_plan_snapshot=None,
        measurements={**{name: None for name in MEASUREMENT_FIELDS}, "mechanical_seal_leak_de": True,
                      "mechanical_seal_leak_nde": False, "suction_temp": 47.5},
        source_document="doc.pdf", source_row=1, raw={},
    )
    values = executor._values_row(row).strip("()").split(", ")
    rendered = dict(zip(executor.INSERT_COLUMNS, values))
    assert rendered["mechanical_seal_leak_de"] == "TRUE"
    assert rendered["mechanical_seal_leak_nde"] == "FALSE"
    assert rendered["suction_temp"] == "47.5"
    assert rendered["discharge_temp"] == "NULL"
    assert rendered["pump_operating_state"] == "NULL"
    assert rendered["api_plan_snapshot"] == "NULL"
    assert rendered["provenance"] == "'HISTORICAL_IMPORT'"
    assert rendered["asset_type"] == "'PUMP'"
    assert rendered["condition_monitoring_schedule_code"] == "'UNSCHEDULED::doc.pdf'"


def test_imported_rows_match_manifest_field_by_field(manifest, imported):
    _, result, by_ref = imported
    assert all(not row_matches_manifest(by_ref[r.source_reference], r) for r in manifest.rows)
    assert result["verification"]["MANIFEST_ROWS_IDENTICAL"] is True


# ---------------------------------------------------------------------------
# TRANSACTION / INSERT-ONLY
# ---------------------------------------------------------------------------


def test_failed_batch_rolls_back_and_stops_the_run(manifest):
    store = FakeStore()
    plan = preflight(manifest, store)
    store.fail_on_reference = plan.proposed[260].source_reference  # middle of batch 2 (250-row batches)
    with pytest.raises(BatchFailed) as excinfo:
        executor.apply(manifest, store, plan, batch_size=250)
    details = excinfo.value.details
    assert details["failed_batch"] == 2 and details["committed_batches"] == 1
    assert details["committed_rows"] == 250 and details["rolled_back_cleanly"] is True
    assert len(store.rows) == 2092 + 250
    assert store.batches_attempted == 2  # no batch after the failure
    batch_two = {r.source_reference for r in plan.proposed[250:500]}
    assert not any(row.get("source_reference") in batch_two for row in store.rows)


def test_partial_import_requires_explicit_resume_then_completes(manifest):
    store = FakeStore()
    plan = preflight(manifest, store)
    store.fail_on_reference = plan.proposed[260].source_reference
    with pytest.raises(BatchFailed):
        executor.apply(manifest, store, plan)
    store.fail_on_reference = None
    with pytest.raises(ExecutorAbort) as excinfo:
        preflight(manifest, store)
    assert "PARTIAL_IMPORT_DETECTED" in _issue_codes(excinfo)
    resumed = preflight(manifest, store, allow_resume=True)
    assert len(resumed.proposed) == 2907 - 250 and resumed.baseline_now == 2092
    executor.apply(manifest, store, resumed)
    assert len(store.rows) == 4999


def test_generated_batch_sql_is_insert_only_and_transactional(manifest):
    sql = build_batch_sql(list(manifest.rows[:3]), 2092)
    assert sql.startswith("BEGIN;") and sql.endswith("COMMIT;")
    assert sql.count("INSERT INTO condition_monitoring_reading") == 1
    assert "RAISE EXCEPTION 'BASELINE_CHANGED" in sql and "BATCH_POSTCHECK_FAILED" in sql
    for forbidden in (r"\bUPDATE\b", r"\bDELETE\b", r"ON\s+CONFLICT", r"\bTRUNCATE\b", "ltsa_pumps", r"INSERT INTO asset_registry"):
        assert not re.search(forbidden, sql, re.IGNORECASE), forbidden


@pytest.mark.parametrize(
    "script",
    [
        "UPDATE condition_monitoring_reading SET suction_temp = 1;",
        "DELETE FROM condition_monitoring_reading;",
        "INSERT INTO condition_monitoring_reading (a) VALUES (1) ON CONFLICT DO NOTHING;",
        "INSERT INTO asset_registry (asset_code) VALUES ('x');",
        "INSERT INTO ltsa_pumps (tag_number) VALUES ('x');",
        "update ltsa_pumps set api_plan = 'x';",
        "TRUNCATE condition_monitoring_reading;",
        "ALTER TABLE asset_registry ADD COLUMN x INT;",
    ],
)
def test_insert_only_guard_rejects_mutation(script):
    with pytest.raises(ExecutorAbort) as excinfo:
        _assert_insert_only(script)
    assert _abort_code(excinfo) == "FORBIDDEN_WRITE"


def test_insert_only_guard_ignores_text_inside_string_literals():
    _assert_insert_only("INSERT INTO condition_monitoring_reading (finding) VALUES ('UPDATE x SET y; DELETE FROM z');")


def test_executor_source_has_no_update_delete_or_asset_write_path():
    source = Path(executor.__file__).read_text(encoding="utf-8")
    code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
    patterns = [
        r"UPDATE\s+[\w.\"]+\s+SET", r"DELETE\s+FROM", r"ON\s+CONFLICT\s+DO", r"MERGE\s+INTO",
        r"INSERT\s+INTO\s+(asset_registry|ltsa_pumps)", r"_build_update",
    ]
    for pattern in patterns:
        assert not re.search(pattern, code, re.IGNORECASE), pattern
    assert code.count("self._runner.execute_script(") == 1  # the one write call site


# ---------------------------------------------------------------------------
# IDEMPOTENCY
# ---------------------------------------------------------------------------


def test_second_dry_run_after_import_proposes_zero(manifest, imported):
    store, result, _ = imported
    assert result["inserted"] == 2907 and len(store.rows) == 4999
    assert result["verification"]["SECOND_DRY_RUN_PROPOSED_INSERTS"] == 0
    assert result["verification"]["PREEXISTING_ROWS_UNCHANGED"] is True
    again = preflight(manifest, store)
    assert len(again.proposed) == 0 and len(again.already_imported) == 2907
    assert again.summary(manifest)["PROPOSED_INSERTS"] == 0 and again.baseline_now == 2092


def test_import_does_not_change_preexisting_rows(manifest):
    store = FakeStore()
    before = copy.deepcopy(store.rows)
    executor.apply(manifest, store, preflight(manifest, store))
    assert store.rows[:2092] == before


# ---------------------------------------------------------------------------
# CLI write gates
# ---------------------------------------------------------------------------


def test_apply_refuses_a_manifest_that_is_not_the_frozen_hash(tmp_path, base_document):
    path, sha = _write(tmp_path, base_document)
    with pytest.raises(ExecutorAbort) as excinfo:
        executor.run(_args(path, sha, mode="apply"), store=FakeStore())
    assert _abort_code(excinfo) == "NOT_FROZEN_MANIFEST"


R1_SUPERSEDED_SHA256 = "80542d3c94e129dc7ee82d19127a30b0c01d22f8a1c85f284231280d3e647af0"
R2_FROZEN_SHA256 = "54668aca38b285d85b204e0ebf6b45eaef4a8b94b660823c9cc8d2ef052581d8"


def _present_bytes_as(monkeypatch, reported_sha: str) -> None:
    """The synthetic file cannot have the R2 hash. Its bytes are still
    hash-verified against their own real SHA-256 first; only the hash the
    executor then compares with the frozen constant is replaced, so the
    frozen-manifest gate runs against the unpatched BATCH_A_MANIFEST_SHA256."""
    original = executor.read_manifest_bytes_verified

    def verified_then_reported(path, expected_sha256):
        data, _ = original(path, hashlib.sha256(path.read_bytes()).hexdigest())
        return data, reported_sha

    monkeypatch.setattr(executor, "read_manifest_bytes_verified", verified_then_reported)


@pytest.fixture
def frozen_synthetic(tmp_path, base_document, monkeypatch):
    path, sha = _write(tmp_path, base_document)
    _present_bytes_as(monkeypatch, R2_FROZEN_SHA256)
    backup = tmp_path / "ltsa_brain_pre_batch_a.dump"
    backup.write_bytes(b"PGDMP synthetic backup")
    return path, sha, backup, hashlib.sha256(backup.read_bytes()).hexdigest()


def test_frozen_constant_is_r2_and_not_r1():
    assert executor.BATCH_A_MANIFEST_SHA256 == R2_FROZEN_SHA256
    source = Path(executor.__file__).read_text(encoding="utf-8")
    assert R1_SUPERSEDED_SHA256 not in source


@pytest.mark.parametrize(
    "reported_sha, expected_code",
    [
        (R2_FROZEN_SHA256, "WRITE_NOT_CONFIRMED"),  # hash gate passed; next gate stops it
        (R1_SUPERSEDED_SHA256, "NOT_FROZEN_MANIFEST"),
        ("ab" * 32, "NOT_FROZEN_MANIFEST"),
    ],
)
def test_real_apply_frozen_manifest_gate(tmp_path, base_document, monkeypatch, reported_sha, expected_code):
    path, _ = _write(tmp_path, base_document)
    _present_bytes_as(monkeypatch, reported_sha)
    store = FakeStore()
    with pytest.raises(ExecutorAbort) as excinfo:
        executor.run(_args(path, reported_sha, mode="apply"), store=store)
    assert _abort_code(excinfo) == expected_code
    assert len(store.rows) == 2092 and store.batches_attempted == 0


def test_r1_is_rejected_even_with_every_other_gate_satisfied(tmp_path, base_document, monkeypatch):
    path, _ = _write(tmp_path, base_document)
    _present_bytes_as(monkeypatch, R1_SUPERSEDED_SHA256)
    backup = tmp_path / "backup.dump"
    backup.write_bytes(b"PGDMP synthetic backup")
    store = FakeStore()
    with pytest.raises(ExecutorAbort) as excinfo:
        executor.run(
            _args(path, R1_SUPERSEDED_SHA256, mode="apply", confirm_production_write="LTSA_HISTORICAL_CM_BATCH_A",
                  backup_file=backup, backup_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),
                  expected_inserts=2907),
            store=store,
        )
    assert _abort_code(excinfo) == "NOT_FROZEN_MANIFEST" and len(store.rows) == 2092


# ---------------------------------------------------------------------------
# Real R2 manifest (untracked TEMP file; skipped where it is absent)
# ---------------------------------------------------------------------------

_R2_PATH = Path(
    os.environ.get(
        "LTSA_BATCH_A_R2_MANIFEST",
        Path(__file__).resolve().parents[4] / "TEMP" / "ltsa_historical_cm_batch_a_import_manifest_r2_api_plan.json",
    )
)
_needs_r2 = pytest.mark.skipif(not _R2_PATH.is_file(), reason=f"R2 manifest not present: {_R2_PATH}")


@pytest.fixture(scope="module")
def real_r2():
    before = hashlib.sha256(_R2_PATH.read_bytes()).hexdigest()
    data, actual = read_manifest_bytes_verified(_R2_PATH, R2_FROZEN_SHA256)
    yield parse_manifest(data, actual)
    assert hashlib.sha256(_R2_PATH.read_bytes()).hexdigest() == before == R2_FROZEN_SHA256  # never modified


@_needs_r2
def test_real_r2_parses_with_null_api_plans(real_r2):
    assert len(real_r2.rows) == 2907
    nulls = [row for row in real_r2.rows if row.api_plan_snapshot is None]
    assert len(nulls) == 9 and {row.asset_code for row in nulls} == {"211-P-30"}
    snapshots = {row.api_plan_snapshot for row in real_r2.rows}
    assert '"23/61' not in snapshots and "-" not in snapshots


@_needs_r2
def test_real_r2_null_api_plan_renders_sql_null_without_master_fallback(real_r2):
    for row in real_r2.rows:
        rendered = executor._values_row(row).strip("()").rsplit(", ", 1)[-1]
        assert rendered == ("NULL" if row.api_plan_snapshot is None else executor._sql(row.api_plan_snapshot))
    for start in range(0, len(real_r2.rows), 250):
        sql = build_batch_sql(list(real_r2.rows[start:start + 250]), 2092)
        assert "ltsa_pumps" not in sql and "api_plan FROM" not in sql


@_needs_r2
def test_real_r2_passes_the_real_apply_hash_gate_without_a_database():
    store = FakeStore()
    with pytest.raises(ExecutorAbort) as excinfo:
        executor.run(_args(_R2_PATH, R2_FROZEN_SHA256, mode="apply"), store=store)
    assert _abort_code(excinfo) == "WRITE_NOT_CONFIRMED"  # the frozen-hash gate accepted R2
    assert store.batches_attempted == 0


def test_apply_requires_confirmation_and_verified_backup(frozen_synthetic):
    path, sha, backup, backup_sha = frozen_synthetic
    cases = [
        ({}, "WRITE_NOT_CONFIRMED"),
        ({"confirm_production_write": "LTSA_HISTORICAL_CM_BATCH_A"}, "BACKUP_REQUIRED"),
        ({"confirm_production_write": "LTSA_HISTORICAL_CM_BATCH_A", "backup_file": backup,
          "backup_sha256": "0" * 64}, "BACKUP_HASH_MISMATCH"),
        ({"confirm_production_write": "LTSA_HISTORICAL_CM_BATCH_A", "backup_file": backup.with_suffix(".missing"),
          "backup_sha256": backup_sha}, "BACKUP_MISSING"),
    ]
    for overrides, code in cases:
        store = FakeStore()
        with pytest.raises(ExecutorAbort) as excinfo:
            executor.run(_args(path, sha, mode="apply", **overrides), store=store)
        assert _abort_code(excinfo) == code
        assert len(store.rows) == 2092


def test_apply_requires_expected_inserts_to_match_proposal(frozen_synthetic):
    path, sha, backup, backup_sha = frozen_synthetic
    gates = dict(confirm_production_write="LTSA_HISTORICAL_CM_BATCH_A", backup_file=backup, backup_sha256=backup_sha)
    store = FakeStore()
    with pytest.raises(ExecutorAbort) as excinfo:
        executor.run(_args(path, sha, mode="apply", expected_inserts=2906, **gates), store=store)
    assert _abort_code(excinfo) == "PROPOSED_INSERTS_MISMATCH" and len(store.rows) == 2092

    report = executor.run(_args(path, sha, mode="apply", expected_inserts=2907, **gates), store=store)
    assert report["APPLY"]["inserted"] == 2907 and report["BACKUP"]["BACKUP_PATH"] == str(backup)
    assert report["APPLY"]["verification"]["TOTAL_AFTER"] == 4999


def test_main_reports_abort_with_nonzero_exit(tmp_path, capsys):
    path = tmp_path / "manifest.json"
    path.write_bytes(b"{}")
    exit_code = executor.main(["--manifest", str(path), "--expected-sha256", "0" * 64])
    output = json.loads(capsys.readouterr().out)
    assert exit_code == 2 and output["STATUS"] == "ABORTED" and output["ABORT_CODE"] == "MANIFEST_HASH_MISMATCH"


# ---------------------------------------------------------------------------
# Read-result parsing across transports (DOCKER_EXEC_READ_FIX_R1)
# ---------------------------------------------------------------------------


class _CannedRunner:
    """Returns one canned stdout (or raises) for every query_scalar call."""

    def __init__(self, output: str | None = None, error: Exception | None = None) -> None:
        self.output, self.error, self.sql = output, error, []

    def query_scalar(self, sql: str) -> str:
        self.sql.append(sql)
        if self.error is not None:
            raise self.error
        return self.output

    def execute_script(self, sql: str) -> None:  # pragma: no cover - never reached by reads
        raise AssertionError("reads must not call execute_script")


def _store(output: str | None = None, error: Exception | None = None):
    runner = _CannedRunner(output, error)
    return executor.PostgresCmImportStore(runner), runner


def test_read_nonzero_transport_failure_still_raises():
    import subprocess

    store, _ = _store(error=subprocess.CalledProcessError(1, ["docker", "compose", "exec"], stderr="boom"))
    with pytest.raises(subprocess.CalledProcessError):
        store.count_total()


@pytest.mark.parametrize("raw", ["", "\n", "BEGIN", "BEGIN\n", " BEGIN \n\n"])
def test_read_empty_result_fails(raw):
    store, _ = _store(raw)
    with pytest.raises(ExecutorAbort) as excinfo:
        store.count_total()
    assert _abort_code(excinfo) == "READ_RESULT_EMPTY"


@pytest.mark.parametrize("raw", ["BEGIN\nabc", "BEGIN\nBEGIN\n2092", "BEGIN\n2092\n1", "ROLLBACK\n2092"])
def test_read_malformed_numeric_result_fails(raw):
    store, _ = _store(raw)
    with pytest.raises(ValueError):
        store.count_total()


@pytest.mark.parametrize("raw", ['BEGIN\n[{"asset_code": "A"', "BEGIN\nnot json", 'BEGIN\n[]\n[{"x": 1}]'])
def test_read_malformed_json_result_fails(raw):
    store, _ = _store(raw)
    with pytest.raises(json.JSONDecodeError):
        store.registry_assets(["A"])


def test_read_transaction_status_plus_scalar_passes():
    store, runner = _store("BEGIN\n2092")
    assert store.count_total() == 2092
    assert runner.sql[0].startswith("BEGIN TRANSACTION READ ONLY; ")  # read-only wrapper unchanged


def test_read_transaction_status_plus_json_passes():
    payload = [{"asset_code": "100-P-1A", "asset_type": "PUMP"}, {"asset_code": "100-P-2A", "asset_type": "PUMP"}]
    store, _ = _store("BEGIN\n" + json.dumps(payload))
    assert store.registry_assets(["100-P-1A", "100-P-2A"]) == payload
    multi_line = "BEGIN\n" + json.dumps(payload, indent=1)  # a multi-line result is kept whole
    store, _ = _store(multi_line)
    assert store.registry_assets(["100-P-1A", "100-P-2A"]) == payload


def test_read_direct_connect_single_line_result_passes():
    store, _ = _store("2092")
    assert store.count_total() == 2092
    store, _ = _store('[{"asset_code": "100-P-1A", "asset_type": "PUMP"}]')
    assert store.registry_assets(["100-P-1A"]) == [{"asset_code": "100-P-1A", "asset_type": "PUMP"}]
    store, _ = _store("2092:0123abcd")
    assert store.preexisting_fingerprint(executor.SOURCE_REFERENCE_PREFIX) == "2092:0123abcd"
