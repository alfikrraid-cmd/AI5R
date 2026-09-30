"""LTSA_POWER_BI_R1B -- governed BI dataset service (contract ltsa-bi/1.0.0).

Every business rule must come from the canonical LTSA contracts; these tests
compare the BI rows with direct calls to those contracts, check the frozen
semantics (tri-state leaks, installation_report-only Current Installation,
service age != MTBF, no zero MTBF, canonical area mappings incl. their
divergence) and the extract guarantees (no truncation, bulk reads only).
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.bi_dataset_service import (
    CONTRACT_VERSION,
    NOT_RECORDED_AREA_KEY,
    BiDatasetService,
    BiSourceUnavailable,
    BiTableLimitExceeded,
    leak_tristate,
)
from API.cm_condition_evaluator import canonical_leak_state, current_leak_condition
from API.current_installation_contract import resolve_current_installation
from API.historical_installation_evidence import combined_installation_evidence
from API.installation_interval_contract import installation_based_mtbf
from API.pump_area_scope import format_area_display, normalize_area_token, resolve_area_ma
from API.pump_contract_area import resolve_contract_area

NOW = datetime(2026, 9, 27, 5, 0, tzinfo=timezone.utc)  # 2026-09-27 12:00 WIB


class Repo:
    """Fake repository: each bulk method returns a fixed list and counts calls."""

    def __init__(self, **methods):
        self.calls = {name: 0 for name in methods}
        self._rows = methods

    def __getattr__(self, name):
        rows = self.__dict__["_rows"]
        if name not in rows:
            raise AttributeError(name)

        def method():
            self.calls[name] += 1
            value = rows[name]
            if isinstance(value, Exception):
                raise value
            return [dict(row) for row in value]

        return method


def asset(code, asset_type, area, *, enriched=True):
    return {
        "asset_code": code, "asset_name": code, "asset_type": asset_type, "asset_status": "Active", "raw_area": area,
        "pump_enrichment_present": enriched,
        "pump_type": "OH2" if enriched else None, "api_plan": "11" if enriched else None,
        "configured_seal_type": "T8B1" if enriched else None, "criticality": "A" if enriched else None,
        "ltsa_location": None,
    }


ASSETS = [
    asset("P-1", "PUMP", "HOC"),
    asset("P-2", "PUMP", "OIL MOVEMENT", enriched=False),
    asset("P-3", "PUMP", "UTILITIES"),
    asset("C-1", "LIQUID RING COMPRESSOR", "REAKTOR", enriched=False),
    asset("X-1", None, None, enriched=False),
]


def reading(code, tag, day, workflow, de, nde, **extra):
    return {
        "condition_monitoring_reading_code": code, "asset_code": tag, "reading_date": f"{day}T00:00:00",
        "created_at": f"{day}T01:00:00", "workflow_status": workflow, "deleted_at": None,
        "mechanical_seal_leak_de": de, "mechanical_seal_leak_nde": nde, "mechseal_temp_de": 50,
        "pump_operating_state": "Running", "provenance": "MANUAL", "source_reference": f"SRC:{code}",
        "finding": extra.get("finding"), "technical_recommendation": None, "api_plan_snapshot": "11",
    }


READINGS = [
    reading("CM-1", "P-1", "2026-08-01", "FINALIZED", False, False),
    reading("CM-2", "P-1", "2026-08-13", "DRAFT", True, None, finding="Mechseal bocor"),
    reading("CM-3", "P-2", "2026-07-01", "SUBMITTED", None, None),
]

PM_ROWS = [
    {"pm_occurrence_code": "PM-2", "asset_code": "P-1", "occurrence_date": "2026-05-02T00:00:00", "status": "DONE",
     "workflow_status": "FINALIZED", "provenance": "MANUAL", "source_reference": None, "finding": None},
    {"pm_occurrence_code": "PM-1", "asset_code": "P-2", "occurrence_date": "2026-05-01T00:00:00", "status": "DONE",
     "workflow_status": "DRAFT", "provenance": "HISTORICAL_IMPORT", "source_reference": "X", "finding": "ok"},
]


def report(code, tag, report_date, *, seal_location=None, source_document="doc.pdf"):
    return {
        "installation_code": code, "report_no": f"RN-{code}", "report_date": report_date, "pump_tag_number": tag,
        "seal_type": "T8B1", "seal_size": '2"', "seal_location": seal_location, "source_document_name": source_document,
        "seal_code": None, "seal_unit_id": None,
    }


REPORTS = [
    report("INSTL-A", "P-1", "2026-01-10", source_document="INSTL-A (DE).pdf"),  # "(DE)" in text only -> PUMP_LEVEL
    report("INSTL-B", "P-1", "2026-02-28T20:00:00Z"),  # TIMESTAMP -> plant date 2026-03-01
]


def hist(event_id, tag, day, *, grade="DIRECT_EVIDENCE", position="PUMP_LEVEL", event_type="INSTALLATION"):
    return {
        "historical_event_id": event_id, "pump_tag_number": tag, "event_date": day, "position": position,
        "event_type": event_type, "seal_type": "T8B1", "seal_size": '2"', "evidence_grade": grade,
        "source_filename": "Servis Activity 2024.xlsx", "source_worksheet": "Juni", "source_row": 9,
        "source_reference": f"SA:{event_id}", "date_correction_status": "NOT_REQUIRED",
    }


HISTORICAL = [
    hist("HIST-1", "P-1", "2025-06-01"),
    hist("HIST-2", "P-3", "2024-05-01"),
    hist("HIST-3", "P-3", "2025-05-01", event_type="REINSTALLATION_REFURBISHED_SEAL"),
    hist("HIST-AMB", "P-3", "2025-09-01", grade="AMBIGUOUS"),  # not governed -> never an event
]


def build(**overrides):
    repos = {
        "asset_repository": Repo(list_assets_with_pump_enrichment=overrides.pop("assets", ASSETS)),
        "cm_repository": Repo(list_all_live=overrides.pop("cm", READINGS)),
        "pm_repository": Repo(list_all_live=overrides.pop("pm", PM_ROWS)),
        "installation_report_repository": Repo(list_for_registered_pumps=overrides.pop("reports", REPORTS)),
        "historical_repository": Repo(list_governed_installation_events=overrides.pop("historical", HISTORICAL)),
        "seal_lifecycle_repository": Repo(list_all_pump_events=overrides.pop("lifecycle", [])),
    }
    service = BiDatasetService(**repos, clock=lambda: NOW, **overrides)
    return service, repos


def by(rows, key):
    return {row[key]: row for row in rows}


# -- envelope / extract guarantees -----------------------------------------------------------------------


def test_envelope_contract_fields_and_deterministic_order():
    service, _ = build()
    body = service.cm()
    assert body["success"] is True and body["contract_version"] == CONTRACT_VERSION == "ltsa-bi/1.0.0"
    assert body["table"] == "cm" and body["plant_timezone"] == "Asia/Jakarta"
    assert body["generated_at_utc"] == "2026-09-27T05:00:00Z" and body["as_of_date"] == "2026-09-27"
    assert body["row_count"] == len(body["data"]) == 3 and body["max_rows"] == 50000
    assert body["order_by"] == "reading_code"
    assert [r["reading_code"] for r in body["data"]] == ["CM-1", "CM-2", "CM-3"]
    assert [r["pm_occurrence_code"] for r in service.pm()["data"]] == ["PM-1", "PM-2"]


def test_table_above_the_limit_fails_instead_of_truncating():
    service, _ = build(max_rows=2)
    with pytest.raises(BiTableLimitExceeded) as error:
        service.cm()
    assert error.value.status_code == 413 and error.value.error_code == "BI_TABLE_LIMIT_EXCEEDED"
    assert service.pm()["row_count"] == 2  # at the limit is still complete


def test_source_failure_is_unavailable_never_partial():
    service, _ = build(pm=RuntimeError("relation does not exist"))
    with pytest.raises(BiSourceUnavailable) as error:
        service.pm()
    assert error.value.status_code == 503 and "relation" not in str(error.value)


def test_duplicate_asset_from_enrichment_join_fails_loudly():
    service, _ = build(assets=ASSETS + [asset("P-1", "PUMP", "HOC")])
    with pytest.raises(BiSourceUnavailable):
        service.assets()


def test_bulk_reads_only_no_per_pump_queries():
    many_pumps = [asset(f"P-{i:03d}", "PUMP", "HOC") for i in range(200)]
    service, repos = build(assets=many_pumps)
    assert service.pump_current()["row_count"] == 200
    for repo in repos.values():
        assert all(count <= 1 for count in repo.calls.values()), repo.calls


# -- DIM_ASSET / DIM_AREA ----------------------------------------------------------------------------------------


def test_assets_keep_every_registry_asset_with_null_enrichment():
    rows = by(build()[0].assets()["data"], "asset_code")
    assert list(rows) == ["C-1", "P-1", "P-2", "P-3", "X-1"]
    p2 = rows["P-2"]
    assert p2["is_pump"] is True and p2["pump_enrichment_present"] is False
    assert (p2["pump_type"], p2["api_plan"], p2["configured_seal_type"], p2["criticality"]) == (None, None, None, None)
    assert rows["X-1"]["asset_type"] is None and rows["X-1"]["raw_area_key"] == NOT_RECORDED_AREA_KEY
    assert rows["X-1"]["contract_area"] == "Unclassified" and rows["X-1"]["maintenance_area"] == "Unclassified"


def test_assets_apply_governed_pump_mapping_without_changing_raw_or_maintenance_area():
    assets = [asset("101-P-2A", "PUMP", "CDU"), asset("946-P-2A", "PUMP", "ITY")]
    service, _ = build(assets=assets)
    rows = by(service.assets()["data"], "asset_code")

    assert rows["101-P-2A"]["contract_area"] == "HSC & S. Pakning"
    assert rows["101-P-2A"]["raw_area"] == "CDU"
    assert rows["101-P-2A"]["maintenance_area"] == "Unclassified"
    assert rows["946-P-2A"]["contract_area"] == "Unclassified"


def test_areas_reuse_canonical_mappings_and_keep_their_divergence():
    rows = by(build()[0].areas()["data"], "raw_area_key")
    for key, row in rows.items():
        raw = row["raw_area"]
        assert row["contract_area"] == resolve_contract_area(raw)
        assert row["maintenance_area"] == (resolve_area_ma(raw) or "Unclassified")
        assert row["area_code"] == normalize_area_token(raw) and row["area_display"] == format_area_display(raw)
    assert (rows["OIL MOVEMENT"]["contract_area"], rows["OIL MOVEMENT"]["maintenance_area"]) == ("Unclassified", "MA4")
    assert (rows["UTILITIES"]["contract_area"], rows["UTILITIES"]["maintenance_area"]) == ("Unclassified", "MA3")
    assert (rows["REAKTOR"]["contract_area"], rows["REAKTOR"]["maintenance_area"]) == ("Unclassified", "Unclassified")
    assert (rows["HOC"]["contract_area"], rows["HOC"]["maintenance_area"]) == ("HOC", "MA1")
    assert rows[NOT_RECORDED_AREA_KEY]["raw_area"] is None


# -- FACT_CM / FACT_PM ---------------------------------------------------------------------------------------------


def test_leak_tristate_is_lossless():
    assert (leak_tristate(True), leak_tristate(False), leak_tristate(None)) == ("TRUE", "FALSE", "NOT_RECORDED")
    assert leak_tristate(0) == "NOT_RECORDED" and leak_tristate("") == "NOT_RECORDED"


def test_cm_rows_keep_draft_tristate_and_canonical_state():
    rows = by(build()[0].cm()["data"], "reading_code")
    assert rows["CM-2"]["workflow_status"] == "DRAFT"  # never filtered
    assert (rows["CM-2"]["leak_de"], rows["CM-2"]["leak_nde"]) == ("TRUE", "NOT_RECORDED")
    assert (rows["CM-3"]["leak_de"], rows["CM-3"]["leak_nde"]) == ("NOT_RECORDED", "NOT_RECORDED")
    for source in READINGS:
        row = rows[source["condition_monitoring_reading_code"]]
        assert row["canonical_leak_state"] == canonical_leak_state(source["mechanical_seal_leak_de"], source["mechanical_seal_leak_nde"])
    assert rows["CM-2"]["reading_date"] == "2026-08-13" and rows["CM-2"]["finding"] == "Mechseal bocor"
    assert "leak_text_conflict" not in rows["CM-2"]  # no conflict semantics in R1


def test_pm_rows_have_no_compliance_semantics():
    row = by(build()[0].pm()["data"], "pm_occurrence_code")["PM-1"]
    assert set(row) == {"pm_occurrence_code", "asset_code", "occurrence_date", "occurrence_timestamp_local", "status",
                        "workflow_status", "provenance", "source_reference", "finding"}
    assert row["occurrence_date"] == "2026-05-01" and row["workflow_status"] == "DRAFT"


# -- FACT_INSTALLATION / FACT_MTBF_INTERVAL ----------------------------------------------------------------------------


def test_installations_combine_both_sources_with_canonical_dates_and_no_position_inference():
    rows = by(build()[0].installations()["data"], "event_id")
    assert set(rows) == {"HIST-1", "INSTL-A", "INSTL-B", "HIST-2", "HIST-3"}  # HIST-AMB not governed
    assert rows["INSTL-A"]["event_source"] == "INSTALLATION_REPORT" and rows["HIST-1"]["event_source"] == "HISTORICAL_SERVICE_ACTIVITY"
    assert rows["INSTL-A"]["position"] == "PUMP_LEVEL"  # "(DE)" only in the document name -> never inferred
    assert (rows["INSTL-B"]["event_date"], rows["INSTL-B"]["date_precision"]) == ("2026-03-01", "TIMESTAMP")
    assert (rows["INSTL-A"]["event_date"], rows["INSTL-A"]["date_precision"]) == ("2026-01-10", "DATE_ONLY")
    assert rows["HIST-3"]["event_type"] == "REINSTALLATION_REFURBISHED_SEAL" and rows["HIST-1"]["evidence_grade"] == "DIRECT_EVIDENCE"
    assert rows["INSTL-A"]["evidence_grade"] is None and rows["INSTL-A"]["source_reference"] == "RN-INSTL-A"
    assert rows["HIST-1"]["source_reference"] == "SA:HIST-1"


def test_mtbf_intervals_are_exactly_the_canonical_contract_output():
    rows = build()[0].mtbf_intervals()["data"]
    expected = []
    for tag in ("P-1", "P-3"):
        combined = combined_installation_evidence(
            [r for r in REPORTS if r["pump_tag_number"] == tag], [h for h in HISTORICAL if h["pump_tag_number"] == tag]
        )
        expected += [(tag, i.previous_installation_code, i.next_installation_code, i.mtbf_days) for i in installation_based_mtbf(combined, tag).intervals]
    assert [(r["asset_code"], r["start_event_id"], r["end_event_id"], r["mtbf_days"]) for r in rows] == expected
    assert [(r["start_event_id"], r["end_event_id"], r["mtbf_days"]) for r in rows] == [
        ("HIST-1", "INSTL-A", 223), ("INSTL-A", "INSTL-B", 50), ("HIST-2", "HIST-3", 365),
    ]
    assert all(r["mtbf_hours"] == r["mtbf_days"] * 24 and r["calendar_basis"] == "CALENDAR_TIME" for r in rows)


# -- FACT_PUMP_CURRENT ---------------------------------------------------------------------------------------------------


def test_pump_current_one_row_per_registry_pump_with_canonical_state():
    body = build()[0].pump_current()
    rows = by(body["data"], "asset_code")
    assert list(rows) == ["P-1", "P-2", "P-3"]  # registry PUMPs only; compressor and untyped asset excluded
    p1 = rows["P-1"]
    # Current Installation is installation_report-only; historical evidence never becomes current.
    assert (p1["current_installation_code"], p1["current_installation_date"]) == ("INSTL-B", "2026-03-01")
    assert rows["P-3"]["current_installation_status"] == "NOT_RECORDED" and rows["P-3"]["current_installation_code"] is None
    # Service age is its own field, from Current Installation, never the MTBF mean. INSTL-B is a
    # TIMESTAMP (2026-03-01 03:00 WIB), so hours are elapsed hours; DATE_ONLY would be days x 24.
    canonical = resolve_current_installation([r for r in REPORTS if r["pump_tag_number"] == "P-1"], "P-1", now=NOW).current
    assert (p1["current_service_age_days"], p1["current_service_age_hours"]) == (
        canonical.time_since_installation_days, canonical.time_since_installation_hours) == (210, 5049)
    assert p1["current_service_age_precision"] == "TIMESTAMP"
    assert p1["current_service_age_basis"] == "CALENDAR_TIME" and p1["pump_mtbf_days_mean"] == 136.5
    assert rows["P-3"]["current_service_age_days"] is None and rows["P-3"]["pump_mtbf_days_mean"] == 365
    # Current condition = the application's own evaluator on the pump's readings (DRAFT latest selected).
    expected = current_leak_condition([r for r in READINGS if r["asset_code"] == "P-1"])
    assert (p1["current_cm_reading_code"], p1["current_leak_state"], p1["current_leak_active"]) == (expected["reading_code"], expected["state"], expected["active"])
    assert (p1["current_cm_reading_code"], p1["current_cm_workflow_status"]) == ("CM-2", "DRAFT")
    assert rows["P-2"]["current_leak_state"] == "UNKNOWN"
    assert p1["as_of_date"] == "2026-09-27" and p1["as_of_timestamp_utc"] == body["generated_at_utc"]


def test_pump_without_completed_interval_has_null_not_zero_mtbf():
    p2 = by(build()[0].pump_current()["data"], "asset_code")["P-2"]
    assert p2["pump_mtbf_completed_interval_count"] == 0
    assert (p2["pump_mtbf_days_mean"], p2["pump_mtbf_hours_mean"], p2["pump_mtbf_latest_interval_days"]) == (None, None, None)


# -- metadata ---------------------------------------------------------------------------------------------------------------


def test_metadata_reconciles_with_every_table():
    service, _ = build()
    meta = service.metadata()
    assert meta["contract_version"] == CONTRACT_VERSION and meta["mttr_available"] is False
    assert meta["mttr_status"] == "DATA NOT AVAILABLE" and meta["snapshot_consistency"] == "PER_REQUEST"
    assert meta["asset_count"] == service.assets()["row_count"] == 5
    assert meta["pump_count"] == meta["mtbf_pump_population"] == service.pump_current()["row_count"] == 3
    assert meta["cm_count"] == service.cm()["row_count"] and meta["pm_count"] == service.pm()["row_count"]
    installations = service.installations()["data"]
    assert meta["installation_event_count"] == len(installations) == 5
    assert (meta["installation_report_count"], meta["historical_installation_count"]) == (2, 3)
    intervals = service.mtbf_intervals()["data"]
    assert meta["mtbf_interval_count"] == len(intervals) == 3
    assert meta["mtbf_pump_coverage_count"] == len({r["asset_code"] for r in intervals}) == 2
    assert meta["mtbf_coverage_pct"] == round(100 * 2 / 3, 2)
    assert (meta["min_fact_date"], meta["max_fact_date"]) == ("2024-05-01", "2026-08-13")
    assert "mttr" not in " ".join(k for k in service.pump_current()["data"][0])
