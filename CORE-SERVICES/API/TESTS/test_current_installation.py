"""LTSA_ASSET360_CURRENT_INSTALLATION_AND_SERVICE_AGE_R1 -- Current
Installation contract, pump_tag_number attribution, and calendar service
age. Rows mirror the production installation_report rows named in the
audit; "now" is always injected (never the wall clock)."""

import sys
from datetime import datetime, timezone
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

import pytest

from API.current_installation_contract import (
    NOT_RECORDED,
    PRECISION_DATE_ONLY,
    PRECISION_TIMESTAMP,
    STATUS_INSTALLED,
    STATUS_NOT_RECORDED,
    STATUS_REMOVED,
    TIME_BASIS_CALENDAR,
    plant_today,
    resolve_current_installation,
    valid_installation_events,
)
from API.equipment_timeline_service import EquipmentTimelineService
from API.installation_report_repository import InstallationReportRepository
from API.ltsa_knowledge_service import LTSAKnowledge

# 2026-09-25 10:00 WIB
NOW = datetime(2026, 9, 25, 3, 0, tzinfo=timezone.utc)


def report(code, plant_equip_no, pump_tag_number, report_date, seal_type=None, **extra):
    return {
        "installation_code": code,
        "report_no": code.replace("INSTL-", "").replace("-2026", "") + "/INSTL/TAP",
        "report_date": report_date,
        "plant_equip_no": plant_equip_no,
        "pump_tag_number": pump_tag_number,
        "seal_type": seal_type,
        "seal_code": None,
        "seal_unit_id": None,
        "seal_location": None,
        "source_document_name": f"SCAN {code[6:9]} INSTALLATION REPORT {pump_tag_number}.pdf",
        **extra,
    }


PRODUCTION_ROWS = [
    report("INSTL-024-2026", "101-P-2A", "101-P-2A", "2026-05-05", "T48LP"),
    report("INSTL-025-2026", "101-P-2A", "101-P-3B", "2026-05-05", "T48LP"),
    report("INSTL-031-2026", "140-P-26A", "140-P-26A", "2026-05-19", "T48MP"),
    report("INSTL-041-2026", "140-P-26A", "140-P-26B", "2026-06-07", "T48MP"),
    report("INSTL-036-2026", "945-P-7A", "945-P-7A", "2026-05-29", "2648-2 Tandem Seal"),
    report("INSTL-038-2026", "945-P-7A", "945-P-7B", "2026-06-05", "2648-2 Tandem"),
    report("INSTL-043-2026", "940-P-2A (NDE)", "940-P-2A", "2026-06-10", "T8B1", seal_location="NDE"),
    report("INSTL-002-2026", "212-P-25A SPARE", "212-P-25A", "2026-01-20"),
    report("INSTL-033-2026", "211-P-1A", "211-P-1A", "2026-05-22", "T8B1-RS"),
    report(
        "INSTL-003-2026", "211-P-2A", "211-P-2A", "2026-01-24", "T8B1-RS",
        source_document_name="SCAN 003 INSTALLATION REPORT 211-P-2A (DE).pdf",
    ),
    report("INSTL-022-2026", "945-P-9B", "945-P-9B", "2026-04-17", "T48MP"),
    report("INSTL-026-2026", "945-P-9B", "945-P-9B", "2026-05-07", "T48MP"),
    report("INSTL-019-2026", "220-P-3A", "220-P-3A", "2026-03-30"),
    report("INSTL-037-2026", "220-P-3A", "220-P-3A", "2026-06-02"),
]


# -- service fakes -------------------------------------------------------


class FakeGateway:
    def __init__(self, method_name, records=None):
        response = {"success": True, "data": records or []}
        setattr(self, method_name, lambda: response)


class FakeKnowledgeService:
    def __init__(self, knowledge):
        self._knowledge = knowledge
        self.cm_report_gateway = FakeGateway("list_cm_reports", [])
        self.seal_engineering_document_gateway = FakeGateway("list_seal_engineering_documents", [])

    def build(self, tag_number):
        return self._knowledge


class FakeInstallationReportRepository:
    """Behaves like list_by_pump_tag(): pump_tag_number only, and returns
    rows in a deliberately scrambled order so no test depends on row order."""

    def __init__(self, rows):
        self._rows = rows

    def list_by_pump_tag(self, pump_tag_number):
        rows = [r for r in self._rows if r.get("pump_tag_number") == pump_tag_number]
        return rows[::2] + rows[1::2]


class FakeLifecycleRepository:
    def __init__(self, events):
        self._events = events

    def list_by_pump(self, pump_tag_number):
        return [e for e in self._events if e.get("pump_tag_number") == pump_tag_number]


def knowledge_for(tag, *, configured_seal_type="T8B1"):
    return LTSAKnowledge(
        tag_number=tag,
        pump={"tag_number": tag, "seal_type": configured_seal_type, "api_plan": "23/61"},
        seal=[], inventory=[], pm_history=[], cm_history=[], breakdown_history=[],
        drawings=[], recommendation=(), pm_schedules=[],
        condition_monitoring_schedules=[], condition_monitoring_readings=[], work_orders=[],
    )


def service_for(tag, rows=PRODUCTION_ROWS, *, lifecycle_events=None, configured_seal_type="T8B1"):
    return EquipmentTimelineService(
        knowledge_service=FakeKnowledgeService(knowledge_for(tag, configured_seal_type=configured_seal_type)),
        installation_gateway=FakeGateway("list_installations", []),
        work_order_gateway=FakeGateway("list_work_orders", []),
        maintenance_history_gateway=FakeGateway("list_maintenance_history", []),
        pm_occurrence_gateway=FakeGateway("list_pm_occurrences", []),
        seal_gateway=FakeGateway("list_seals", []),
        seal_lifecycle_event_repository=(
            FakeLifecycleRepository(lifecycle_events) if lifecycle_events is not None else None
        ),
        installation_report_repository=FakeInstallationReportRepository(rows),
    )


def current_for(tag, **kwargs):
    return service_for(tag, **kwargs).build_current_installation(tag, now=NOW)


# -- attribution (pump_tag_number, never plant_equip_no) -------------------


@pytest.mark.parametrize(
    "sibling, owner, code, date",
    [
        ("101-P-2A", "101-P-3B", "INSTL-025-2026", "2026-05-05"),
        ("945-P-7A", "945-P-7B", "INSTL-038-2026", "2026-06-05"),
        ("140-P-26A", "140-P-26B", "INSTL-041-2026", "2026-06-07"),
    ],
)
def test_sibling_pump_never_consumes_another_pumps_report(sibling, owner, code, date):
    owner_current = current_for(owner).current
    assert owner_current.installation_status == STATUS_INSTALLED
    assert owner_current.source_installation_code == code
    assert owner_current.installation_date == date

    sibling_resolution = current_for(sibling)
    assert code not in [event.installation_code for event in sibling_resolution.history]
    assert sibling_resolution.current.source_installation_code != code


def test_sibling_currents_resolve_to_their_own_reports():
    assert current_for("140-P-26A").current.source_installation_code == "INSTL-031-2026"
    assert current_for("945-P-7A").current.source_installation_code == "INSTL-036-2026"
    assert current_for("101-P-2A").current.source_installation_code == "INSTL-024-2026"


@pytest.mark.parametrize(
    "pump, code",
    [("940-P-2A", "INSTL-043-2026"), ("212-P-25A", "INSTL-002-2026")],
)
def test_annotated_plant_equip_no_still_attributes_by_pump_tag_number(pump, code):
    current = current_for(pump).current
    assert current.installation_status == STATUS_INSTALLED
    assert current.source_installation_code == code


def test_legacy_gateway_path_also_attributes_by_pump_tag_number():
    service = EquipmentTimelineService(
        knowledge_service=FakeKnowledgeService(knowledge_for("101-P-3B")),
        installation_gateway=FakeGateway("list_installations", PRODUCTION_ROWS),
        work_order_gateway=FakeGateway("list_work_orders", []),
        maintenance_history_gateway=FakeGateway("list_maintenance_history", []),
        pm_occurrence_gateway=FakeGateway("list_pm_occurrences", []),
        seal_gateway=FakeGateway("list_seals", []),
    )
    assert service.build_current_installation("101-P-3B", now=NOW).current.source_installation_code == "INSTL-025-2026"
    assert service.build_current_seal("101-P-2A").installation_code == "INSTL-024-2026"


def test_current_seal_and_lifecycle_follow_the_same_attribution():
    service = service_for("140-P-26A")
    assert service.build_current_seal("140-P-26A").installation_code == "INSTL-031-2026"
    lifecycle = service.build_lifecycle("140-P-26A", today=plant_today(NOW))
    assert lifecycle.current_state.current_installation.installation_code == "INSTL-031-2026"
    assert lifecycle.current_state.elapsed_service_days == 129


# -- ordering, supersession, ties -------------------------------------------


def test_latest_installation_supersedes_earlier_one():
    resolution = current_for("945-P-9B")
    assert resolution.current.source_installation_code == "INSTL-026-2026"
    assert resolution.current.installation_date == "2026-05-07"
    assert [e.installation_code for e in resolution.history] == ["INSTL-026-2026", "INSTL-022-2026"]


def test_same_date_tie_breaks_on_installation_code_desc_regardless_of_row_order():
    rows = [
        report("INSTL-010-2026", "X", "P-TIE", "2026-05-05", "A"),
        report("INSTL-011-2026", "X", "P-TIE", "2026-05-05", "B"),
    ]
    for ordering in (rows, rows[::-1]):
        current = resolve_current_installation(ordering, "P-TIE", now=NOW).current
        assert current.source_installation_code == "INSTL-011-2026"
        assert current.installed_seal_type == "B"


def test_invalid_or_missing_dates_are_not_valid_installations():
    rows = [
        report("INSTL-001-2026", "P", "P-BAD", None, "A"),
        report("INSTL-002-2026", "P", "P-BAD", "not-a-date", "B"),
        report("INSTL-003-2026", "P", "P-BAD", "2026-02-30", "C"),
    ]
    assert resolve_current_installation(rows, "P-BAD", now=NOW).current == NOT_RECORDED


# -- no evidence (701-P-1A) ---------------------------------------------------


def test_701_p_1a_has_no_installation_and_never_falls_back_to_configured_seal():
    service = service_for("701-P-1A", configured_seal_type="T8B1")
    resolution = service.build_current_installation("701-P-1A", now=NOW)
    current = resolution.current
    assert current.installation_status == STATUS_NOT_RECORDED
    assert current.installed_seal_type is None
    assert current.installed_seal_unit is None
    assert current.installation_date is None
    assert current.time_since_installation_days is None
    assert current.time_since_installation_hours is None
    assert current.actual_operating_hours is None
    assert resolution.current_by_position == ()
    assert resolution.history == ()
    assert service.build_current_seal("701-P-1A") is None


def test_configured_seal_differs_from_installed_seal_type():
    current = current_for("211-P-1A", configured_seal_type="T8B1").current
    assert current.installed_seal_type == "T8B1-RS"


# -- installed seal identity ---------------------------------------------------


def test_installed_seal_type_without_seal_unit():
    current = current_for("211-P-1A").current
    assert current.installed_seal_type == "T8B1-RS"
    assert current.installed_seal_unit is None
    assert current.seal_code is None


def test_installation_without_seal_type_is_installed_with_type_not_recorded():
    current = current_for("220-P-3A").current
    assert current.installation_status == STATUS_INSTALLED
    assert current.installed_seal_type is None
    assert current.installation_date == "2026-06-02"


# -- positions -----------------------------------------------------------------


def test_explicit_seal_location_sets_position():
    assert current_for("940-P-2A").current.installation_position == "NDE"


def test_position_is_never_inferred_from_file_name_or_free_text():
    # 211-P-2A's "(DE)" exists only in the source file name.
    assert current_for("211-P-2A").current.installation_position is None
    assert current_for("212-P-25A").current.installation_position is None


def test_de_and_nde_installations_are_independent_currents():
    rows = [
        report("INSTL-050-2026", "P", "P-DUAL", "2026-03-01", "DE-OLD", seal_location="DE"),
        report("INSTL-051-2026", "P", "P-DUAL", "2026-04-01", "NDE-ONLY", seal_location="nde"),
        report("INSTL-052-2026", "P", "P-DUAL", "2026-05-01", "DE-NEW", seal_location="DE"),
    ]
    resolution = resolve_current_installation(rows, "P-DUAL", now=NOW)
    by_position = {c.installation_position: c.installed_seal_type for c in resolution.current_by_position}
    assert by_position == {"DE": "DE-NEW", "NDE": "NDE-ONLY"}
    assert resolution.current.installed_seal_type == "DE-NEW"


# -- service age -----------------------------------------------------------------


@pytest.mark.parametrize(
    "pump, date, seal_type, days",
    [
        ("211-P-1A", "2026-05-22", "T8B1-RS", 126),
        ("211-P-2A", "2026-01-24", "T8B1-RS", 244),
        ("945-P-9B", "2026-05-07", "T48MP", 141),
        ("140-P-26B", "2026-06-07", "T48MP", 110),
        ("101-P-3B", "2026-05-05", "T48LP", 143),
        ("220-P-3A", "2026-06-02", None, 115),
    ],
)
def test_positive_assets_date_only_service_age(pump, date, seal_type, days):
    current = current_for(pump).current
    assert current.installation_status == STATUS_INSTALLED
    assert current.installation_date == date
    assert current.installed_seal_type == seal_type
    assert current.time_since_installation_days == days
    assert current.time_since_installation_hours == days * 24
    assert current.time_basis == TIME_BASIS_CALENDAR
    assert current.time_precision == PRECISION_DATE_ONLY


def test_asia_jakarta_date_boundary_not_utc():
    rows = [report("INSTL-033-2026", "211-P-1A", "211-P-1A", "2026-05-22", "T8B1-RS")]
    # 2026-09-24 23:59:59 WIB (UTC date also 2026-09-24)
    before = datetime(2026, 9, 24, 16, 59, 59, tzinfo=timezone.utc)
    # 2026-09-25 00:00:00 WIB while UTC is still 2026-09-24
    after = datetime(2026, 9, 24, 17, 0, 0, tzinfo=timezone.utc)
    assert resolve_current_installation(rows, "211-P-1A", now=before).current.time_since_installation_days == 125
    assert resolve_current_installation(rows, "211-P-1A", now=after).current.time_since_installation_days == 126
    assert plant_today(after).isoformat() == "2026-09-25"


def test_timestamp_precision_uses_actual_elapsed_hours():
    rows = [report("INSTL-060-2026", "P", "P-TS", "2026-09-24T08:30:00+07:00", "T48MP")]
    current = resolve_current_installation(rows, "P-TS", now=NOW).current
    assert current.time_precision == PRECISION_TIMESTAMP
    assert current.time_since_installation_days == 1
    assert current.time_since_installation_hours == 25


def test_future_dated_evidence_never_yields_negative_age():
    rows = [report("INSTL-061-2026", "P", "P-FUT", "2026-10-01", "T48MP")]
    current = resolve_current_installation(rows, "P-FUT", now=NOW).current
    assert current.installation_status == STATUS_INSTALLED
    assert current.time_since_installation_days is None
    assert current.time_since_installation_hours is None


# -- counter reset / removal ----------------------------------------------------


def test_counter_does_not_reset_on_non_installation_evidence():
    # PM/CM/CMON, configuration and compatibility are not inputs to the
    # contract at all: only installation rows and lifecycle removals are.
    rows = [report("INSTL-033-2026", "211-P-1A", "211-P-1A", "2026-05-22", "T8B1-RS")]
    unrelated = [{"event_type": "INSPECTION_COMPLETED", "pump_tag_number": "211-P-1A", "event_at": "2026-09-01T00:00:00Z"}]
    current = resolve_current_installation(rows, "211-P-1A", removal_events=unrelated, now=NOW).current
    assert current.time_since_installation_days == 126


def test_counter_resets_only_on_a_new_installation():
    rows = [report("INSTL-022-2026", "945-P-9B", "945-P-9B", "2026-04-17", "T48MP")]
    assert resolve_current_installation(rows, "945-P-9B", now=NOW).current.time_since_installation_days == 161
    rows.append(report("INSTL-026-2026", "945-P-9B", "945-P-9B", "2026-05-07", "T48MP"))
    assert resolve_current_installation(rows, "945-P-9B", now=NOW).current.time_since_installation_days == 141


@pytest.mark.parametrize("event_type", ["REMOVE", "SCRAP", "RETURN_TO_STOCK"])
def test_later_lifecycle_removal_stops_the_counter(event_type):
    removal = {"event_type": event_type, "pump_tag_number": "211-P-1A", "event_at": "2026-08-01T02:00:00Z"}
    resolution = current_for("211-P-1A", lifecycle_events=[removal])
    assert resolution.current.installation_status == STATUS_REMOVED
    assert resolution.current.removed_at == "2026-08-01"
    assert resolution.current.installed_seal_type is None
    assert resolution.current.time_since_installation_days is None
    assert service_for("211-P-1A", lifecycle_events=[removal]).build_current_seal("211-P-1A") is None


def test_removal_before_a_reinstallation_does_not_stop_the_new_counter():
    removal = {"event_type": "REMOVE", "pump_tag_number": "945-P-9B", "event_at": "2026-05-01T00:00:00Z"}
    current = current_for("945-P-9B", lifecycle_events=[removal]).current
    assert current.installation_status == STATUS_INSTALLED
    assert current.source_installation_code == "INSTL-026-2026"


# -- repository query ------------------------------------------------------------


class RecordingRunner:
    def __init__(self):
        self.sql = []

    def query_scalar(self, sql):
        self.sql.append(sql)
        return "[]"


def test_repository_attributes_by_pump_tag_number_with_registry_and_deterministic_order():
    runner = RecordingRunner()
    assert InstallationReportRepository(runner).list_by_pump_tag("101-P-3B") == []
    sql = runner.sql[0]
    assert "ir.pump_tag_number = '101-P-3B'" in sql
    assert "plant_equip_no =" not in sql
    assert "asset_registry" in sql and "asset_type = 'PUMP'" in sql
    assert "ORDER BY ir.report_date DESC NULLS LAST, ir.installation_code DESC" in sql
    assert "seal_location" in sql and "seal_unit_id" in sql


def test_valid_events_are_newest_first():
    codes = [e.installation_code for e in valid_installation_events(PRODUCTION_ROWS, "220-P-3A")]
    assert codes == ["INSTL-037-2026", "INSTL-019-2026"]
