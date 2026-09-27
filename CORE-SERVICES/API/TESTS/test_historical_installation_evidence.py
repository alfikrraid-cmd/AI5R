"""LTSA_HISTORICAL_INSTALLATION_2024_2025_IMPORT_IMPLEMENTATION_R1 -- governed
historical installation evidence: adapter, MTBF read model, and the hard
isolation of Current Installation / Service Age from historical rows."""

import sys
from datetime import datetime, timezone
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.equipment_timeline_service import EquipmentTimelineService
from API.historical_installation_evidence import (
    ORIGIN_HISTORICAL_SERVICE_ACTIVITY,
    ORIGIN_INSTALLATION_REPORT,
    combined_installation_evidence,
    historical_row_to_interval_record,
    is_governed_historical_row,
)
from API.installation_interval_contract import installation_based_mtbf
from API.seal_equipment_history_service import _historical_service_activity_to_timeline
from API.TESTS.test_current_installation import FakeGateway, FakeKnowledgeService, PRODUCTION_ROWS, knowledge_for, report

NOW = datetime(2026, 9, 27, 5, 0, tzinfo=timezone.utc)  # 2026-09-27 12:00 WIB (frozen UAT day)


def hist(event_id, pump, day, *, position="PUMP_LEVEL", event_type="INSTALLATION", seal_type="T48MP",
         seal_size="2.3/8''", grade="DIRECT_EVIDENCE"):
    return {"historical_event_id": event_id, "pump_tag_number": pump, "event_date": day, "position": position,
            "event_type": event_type, "seal_type": seal_type, "seal_size": seal_size, "evidence_grade": grade,
            "source_filename": "Servis Activity 2024 (1).xlsx", "source_worksheet": "Juni 2024", "source_row": 9,
            "source_reference": f"SERVICE_ACTIVITY:2024:X:{event_id}", "raw_tag": pump}


class FakeInstallationRepo:
    def __init__(self, rows):
        self._rows = rows

    def list_by_pump_tag(self, tag):
        return [r for r in self._rows if r.get("pump_tag_number") == tag]


class FakeHistoricalRepo:
    def __init__(self, rows, fail=False):
        self._rows = rows
        self._fail = fail
        self.governed_calls = 0

    def list_by_pump(self, tag):
        return [r for r in self._rows if r.get("pump_tag_number") == tag]

    def list_governed_installation_events_by_pump(self, tag):
        self.governed_calls += 1
        if self._fail:
            raise RuntimeError("column historical_event_id does not exist")
        return [r for r in self._rows if r.get("pump_tag_number") == tag and r.get("historical_event_id")]


def service(tag, historical, *, fail=False):
    return EquipmentTimelineService(
        knowledge_service=FakeKnowledgeService(knowledge_for(tag)),
        installation_gateway=FakeGateway("list_installations", []),
        work_order_gateway=FakeGateway("list_work_orders", []),
        maintenance_history_gateway=FakeGateway("list_maintenance_history", []),
        pm_occurrence_gateway=FakeGateway("list_pm_occurrences", []),
        seal_gateway=FakeGateway("list_seals", []),
        installation_report_repository=FakeInstallationRepo(PRODUCTION_ROWS),
        historical_seal_service_activity_repository=FakeHistoricalRepo(historical, fail=fail),
    )


HIST_945 = [hist("HIST-INSTL-AAAA000000000001", "945-P-9B", "2024-06-10")]
HIST_211 = [hist("HIST-INSTL-AAAA000000000002", "211-P-1A", "2025-03-01", seal_type="T8B1-RS", seal_size='4.1/2"'),
            hist("HIST-INSTL-AAAA000000000003", "211-P-1A", "2025-11-01", seal_type="T8B1-RS", seal_size='4.1/2"')]
HIST_701 = [hist("HIST-INSTL-AAAA000000000004", "701-P-1A", "2024-08-16", seal_type="T8B1"),
            hist("HIST-INSTL-AAAA000000000005", "701-P-1A", "2025-08-16", seal_type="T8B1")]


# -- adapter -----------------------------------------------------------------------------------


def test_adapter_maps_without_pretending_to_be_an_installation_report():
    record = historical_row_to_interval_record(hist("HIST-INSTL-1", "200-P-7A", "2024-05-07", position="DE"))
    assert record["installation_code"] == "HIST-INSTL-1"
    assert record["report_date"] == "2024-05-07"
    assert record["seal_location"] == "DE"
    assert record["seal_size"] == "2.3/8''"  # verbatim
    assert record["evidence_origin"] == ORIGIN_HISTORICAL_SERVICE_ACTIVITY
    assert historical_row_to_interval_record(hist("HIST-INSTL-2", "P", "2024-05-07"))["seal_location"] is None


def test_only_governed_rows_are_admitted():
    assert is_governed_historical_row(hist("HIST-INSTL-1", "P", "2024-01-01"))
    assert not is_governed_historical_row(dict(hist("HIST-INSTL-1", "P", "2024-01-01"), historical_event_id=None))
    assert not is_governed_historical_row(hist("HIST-INSTL-1", "P", "2024-01-01", grade="AMBIGUOUS"))
    combined = combined_installation_evidence([report("INSTL-1", "P", "P", "2026-01-01")],
                                              [hist("HIST-INSTL-1", "P", "2025-01-01"), hist("HIST-INSTL-2", "P", "2025-02-01", grade=None)])
    assert [r["evidence_origin"] for r in combined] == [ORIGIN_INSTALLATION_REPORT, ORIGIN_HISTORICAL_SERVICE_ACTIVITY]


# -- MTBF read model ---------------------------------------------------------------------------------


def test_mtbf_consumes_governed_historical_evidence_through_the_frozen_contract():
    result = service("945-P-9B", HIST_945).build_installation_based_mtbf("945-P-9B")
    assert [(i.previous_installation_code, i.next_installation_code, i.mtbf_days) for i in result.intervals] == [
        ("HIST-INSTL-AAAA000000000001", "INSTL-022-2026", 676),
        ("INSTL-022-2026", "INSTL-026-2026", 20),
    ]
    # identical to calling the unchanged contract on the combined input
    direct = installation_based_mtbf(
        combined_installation_evidence([r for r in PRODUCTION_ROWS if r["pump_tag_number"] == "945-P-9B"], HIST_945), "945-P-9B")
    assert result == direct


def test_historical_seal_identity_keeps_frozen_verbatim_semantics():
    # 2.3/8'' (historical) vs 2.3/8" (report) is CHANGED under frozen R1 semantics; not silently normalized.
    interval = service("945-P-9B", HIST_945).build_installation_based_mtbf("945-P-9B").intervals[0]
    assert interval.seal_identity_status == "CHANGED"


def test_no_repository_or_missing_migration_degrades_to_installation_report_only():
    baseline = service("945-P-9B", []).build_installation_based_mtbf("945-P-9B")
    failing = service("945-P-9B", HIST_945, fail=True).build_installation_based_mtbf("945-P-9B")
    assert failing == baseline and baseline.completed_interval_count == 1


def test_ungoverned_rows_in_the_table_never_reach_mtbf():
    legacy = [dict(HIST_945[0], historical_event_id=None, evidence_grade=None)]
    assert service("945-P-9B", legacy).build_installation_based_mtbf("945-P-9B").completed_interval_count == 1


# -- hard isolation -------------------------------------------------------------------------------------


def test_current_installation_and_service_age_ignore_historical_evidence():
    for tag, historical, code, date_, days in [
        ("945-P-9B", HIST_945, "INSTL-026-2026", "2026-05-07", 143),
        ("211-P-1A", HIST_211, "INSTL-033-2026", "2026-05-22", 128),
    ]:
        with_hist = service(tag, historical)
        without = service(tag, [])
        current = with_hist.build_current_installation(tag, now=NOW).current
        assert (current.source_installation_code, current.installation_date, current.time_since_installation_days,
                current.time_since_installation_hours) == (code, date_, days, days * 24)
        assert current == without.build_current_installation(tag, now=NOW).current
        assert with_hist.build_current_seal(tag) == without.build_current_seal(tag)


def test_historical_evidence_never_creates_a_current_installation():
    svc = service("701-P-1A", HIST_701)
    assert svc.build_current_installation("701-P-1A", now=NOW).current.installation_status == "NOT_RECORDED"
    assert svc.build_current_seal("701-P-1A") is None
    # ...while the historical pair does form an MTBF interval
    assert svc.build_installation_based_mtbf("701-P-1A").completed_interval_count == 1


def test_lifecycle_current_state_ignores_historical_evidence():
    with_hist = service("211-P-1A", HIST_211).build_lifecycle("211-P-1A")
    without = service("211-P-1A", []).build_lifecycle("211-P-1A")
    assert with_hist.current_state.current_installation == without.current_state.current_installation
    assert with_hist.current_state.elapsed_service_days == without.current_state.elapsed_service_days


# -- lifecycle presentation --------------------------------------------------------------------------------


def test_historical_timeline_labels_keep_the_source_distinction():
    events = _historical_service_activity_to_timeline([
        hist("HIST-INSTL-1", "220-P-1B", "2025-07-16", event_type="INSTALLATION", seal_type="T8B1"),
        hist("HIST-INSTL-2", "220-P-1B", "2025-08-13", event_type="REINSTALLATION_REFURBISHED_SEAL", seal_type="T8B1"),
    ])
    assert [e.title for e in events] == ["Historical Service Activity (T8B1)", "Reinstallation (Refurbished Seal) (T8B1)"]
