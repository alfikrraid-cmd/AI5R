import sys
from datetime import date
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.company_manufacturing import manufacture_company
from API.department_manufacturing import manufacture_department
from API.maintenance_intelligence_service import (
    get_active_work_orders,
    get_assigned_role,
    get_pump_condition_monitoring_flag,
    get_pump_history,
    get_pump_last_cm,
    get_pump_last_pm,
    get_pump_spare_parts,
    get_pump_status,
    get_recent_maintenance,
    summarize_situation,
)
from API.role_manufacturing import manufacture_role


class FakePumpGateway:
    def __init__(self, pumps=None, detail_response=None):
        pumps = pumps or []
        self._list_response = {"success": True, "message": "ok", "count": len(pumps), "data": pumps}
        self._detail_response = detail_response

    def list_pumps(self):
        return self._list_response

    def get_pump(self, tag_number):
        return self._detail_response


class FakeWorkOrderGateway:
    def __init__(self, work_orders=None, detail_responses=None):
        work_orders = work_orders or []
        self._list_response = {
            "success": True,
            "message": "ok",
            "count": len(work_orders),
            "data": work_orders,
        }
        self._detail_responses = detail_responses or {}

    def list_work_orders(self):
        return self._list_response

    def get_work_order(self, work_order_code):
        return self._detail_responses.get(
            work_order_code, {"success": False, "message": "Work order not found", "data": None}
        )


class FakeMaintenanceHistoryGateway:
    def __init__(self, records=None):
        records = records or []
        self._list_response = {
            "success": True,
            "message": "ok",
            "count": len(records),
            "data": records,
        }

    def list_maintenance_history(self):
        return self._list_response


class FakePMOccurrenceGateway:
    def __init__(self, occurrences=None, success=True):
        occurrences = occurrences or []
        self._list_response = {
            "success": success,
            "message": "ok",
            "count": len(occurrences),
            "data": occurrences,
        }

    def list_pm_occurrences(self):
        return self._list_response


class FakeCMReportGateway:
    def __init__(self, records=None, success=True):
        records = records or []
        self._list_response = {
            "success": success,
            "message": "ok",
            "count": len(records),
            "data": records,
        }

    def list_cm_reports(self):
        return self._list_response


class FakeConditionMonitoringReadingGateway:
    def __init__(self, readings=None, success=True):
        readings = readings or []
        self._list_response = {
            "success": success,
            "message": "ok",
            "count": len(readings),
            "data": readings,
        }

    def list_condition_monitoring_readings(self):
        return self._list_response


class FakeSealPumpCompatibilityGateway:
    def __init__(self, records=None, success=True):
        records = records or []
        self._list_response = {
            "success": success,
            "message": "ok",
            "count": len(records),
            "data": records,
        }

    def list_seal_pump_compatibilities(self):
        return self._list_response


class FakeSealStockGateway:
    def __init__(self, records=None, success=True):
        records = records or []
        self._list_response = {
            "success": success,
            "message": "ok",
            "count": len(records),
            "data": records,
        }

    def list_seal_stocks(self):
        return self._list_response


class FakeSealGateway:
    def __init__(self, records=None, success=True):
        records = records or []
        self._list_response = {
            "success": success,
            "message": "ok",
            "count": len(records),
            "data": records,
        }

    def list_seals(self):
        return self._list_response


def _seed_organization(tmp_path, product_name="LTSA-BRAIN"):
    product_dir = tmp_path / "PRODUCTS" / product_name
    product_dir.mkdir(parents=True, exist_ok=True)
    (product_dir / "product_artifact.json").write_text("{}", encoding="utf-8")

    manufacture_company(
        product_name=product_name, company_name="CV Razzan Teknik Mandiri", root_path=tmp_path
    )
    manufacture_department(
        product_name=product_name, department_name="Field Operations", root_path=tmp_path
    )
    manufacture_role(
        product_name=product_name,
        role_name="Field Technician",
        department_name="Field Operations",
        root_path=tmp_path,
    )


def test_get_pump_status_returns_gateway_response_unchanged():
    detail_response = {"success": True, "message": "Pump detail found", "data": {"tag_number": "P-101"}}
    pump_gateway = FakePumpGateway(detail_response=detail_response)

    result = get_pump_status("P-101", pump_gateway=pump_gateway)

    assert result == detail_response


def test_get_pump_history_filters_by_pump():
    maintenance_history_gateway = FakeMaintenanceHistoryGateway(
        [
            {"maintenance_record_code": "MH-101", "asset_code": "P-101"},
            {"maintenance_record_code": "MH-102", "asset_code": "P-102"},
        ]
    )

    result = get_pump_history("P-101", maintenance_history_gateway=maintenance_history_gateway)

    assert result["tag_number"] == "P-101"
    assert result["records"] == [{"maintenance_record_code": "MH-101", "asset_code": "P-101"}]


def test_get_pump_last_pm_picks_most_recent_pm_typed_record():
    # ADR-PUMP-002 / WO-PUMP-004: only maintenance_history records whose
    # linked work_order has work_type == 'PM' qualify; among those, the
    # most recent performed_at wins. No pm_occurrence rows exist here, so
    # the work_order-sourced candidate wins by default.
    maintenance_history_gateway = FakeMaintenanceHistoryGateway(
        [
            {
                "maintenance_record_code": "MH-101",
                "asset_code": "P-101",
                "work_order_code": "WO-101",
                "performed_at": "2026-06-01T00:00:00Z",
            },
            {
                "maintenance_record_code": "MH-102",
                "asset_code": "P-101",
                "work_order_code": "WO-102",
                "performed_at": "2026-07-01T00:00:00Z",
            },
        ]
    )
    work_order_gateway = FakeWorkOrderGateway(
        [
            {"work_order_code": "WO-101", "work_type": "PM"},
            {"work_order_code": "WO-102", "work_type": "PM"},
        ]
    )
    pm_occurrence_gateway = FakePMOccurrenceGateway([])

    result = get_pump_last_pm(
        "P-101",
        maintenance_history_gateway=maintenance_history_gateway,
        work_order_gateway=work_order_gateway,
        pm_occurrence_gateway=pm_occurrence_gateway,
    )

    assert result["tag_number"] == "P-101"
    assert result["last_pm"]["source"] == "work_order"
    assert result["last_pm"]["performed_at"] == "2026-07-01T00:00:00Z"
    assert result["last_pm"]["record"]["maintenance_record_code"] == "MH-102"


def test_get_pump_last_pm_excludes_non_pm_work_types():
    maintenance_history_gateway = FakeMaintenanceHistoryGateway(
        [
            {
                "maintenance_record_code": "MH-101",
                "asset_code": "P-101",
                "work_order_code": "WO-101",
                "performed_at": "2026-07-01T00:00:00Z",
            },
        ]
    )
    work_order_gateway = FakeWorkOrderGateway(
        [{"work_order_code": "WO-101", "work_type": "CM"}]
    )
    pm_occurrence_gateway = FakePMOccurrenceGateway([])

    result = get_pump_last_pm(
        "P-101",
        maintenance_history_gateway=maintenance_history_gateway,
        work_order_gateway=work_order_gateway,
        pm_occurrence_gateway=pm_occurrence_gateway,
    )

    assert result["last_pm"] is None


def test_get_pump_last_pm_excludes_records_with_no_linked_work_order():
    maintenance_history_gateway = FakeMaintenanceHistoryGateway(
        [
            {
                "maintenance_record_code": "MH-101",
                "asset_code": "P-101",
                "work_order_code": None,
                "performed_at": "2026-07-01T00:00:00Z",
            },
        ]
    )
    work_order_gateway = FakeWorkOrderGateway([])
    pm_occurrence_gateway = FakePMOccurrenceGateway([])

    result = get_pump_last_pm(
        "P-101",
        maintenance_history_gateway=maintenance_history_gateway,
        work_order_gateway=work_order_gateway,
        pm_occurrence_gateway=pm_occurrence_gateway,
    )

    assert result["last_pm"] is None


def test_get_pump_last_pm_uses_pm_occurrence_when_more_recent():
    # ADR-PM-OCCURRENCE-001 / MWO-MAINTINT-001: pm_occurrence is the
    # canonical source for routine PM completion; it wins when more
    # recent than any work_order-linked maintenance_history candidate.
    maintenance_history_gateway = FakeMaintenanceHistoryGateway(
        [
            {
                "maintenance_record_code": "MH-101",
                "asset_code": "P-101",
                "work_order_code": "WO-101",
                "performed_at": "2026-06-01T00:00:00Z",
            },
        ]
    )
    work_order_gateway = FakeWorkOrderGateway([{"work_order_code": "WO-101", "work_type": "PM"}])
    pm_occurrence_gateway = FakePMOccurrenceGateway(
        [
            {
                "pm_occurrence_code": "PM-OCC-101",
                "asset_code": "P-101",
                "occurrence_date": "2026-07-15T00:00:00Z",
            }
        ]
    )

    result = get_pump_last_pm(
        "P-101",
        maintenance_history_gateway=maintenance_history_gateway,
        work_order_gateway=work_order_gateway,
        pm_occurrence_gateway=pm_occurrence_gateway,
    )

    assert result["last_pm"]["source"] == "pm_occurrence"
    assert result["last_pm"]["performed_at"] == "2026-07-15T00:00:00Z"
    assert result["last_pm"]["record"]["pm_occurrence_code"] == "PM-OCC-101"


def test_get_pump_last_pm_uses_work_order_when_more_recent_than_pm_occurrence():
    maintenance_history_gateway = FakeMaintenanceHistoryGateway(
        [
            {
                "maintenance_record_code": "MH-101",
                "asset_code": "P-101",
                "work_order_code": "WO-101",
                "performed_at": "2026-07-20T00:00:00Z",
            },
        ]
    )
    work_order_gateway = FakeWorkOrderGateway([{"work_order_code": "WO-101", "work_type": "PM"}])
    pm_occurrence_gateway = FakePMOccurrenceGateway(
        [
            {
                "pm_occurrence_code": "PM-OCC-101",
                "asset_code": "P-101",
                "occurrence_date": "2026-06-01T00:00:00Z",
            }
        ]
    )

    result = get_pump_last_pm(
        "P-101",
        maintenance_history_gateway=maintenance_history_gateway,
        work_order_gateway=work_order_gateway,
        pm_occurrence_gateway=pm_occurrence_gateway,
    )

    assert result["last_pm"]["source"] == "work_order"
    assert result["last_pm"]["record"]["maintenance_record_code"] == "MH-101"


def test_get_pump_last_pm_filters_pm_occurrences_by_asset_code():
    maintenance_history_gateway = FakeMaintenanceHistoryGateway([])
    work_order_gateway = FakeWorkOrderGateway([])
    pm_occurrence_gateway = FakePMOccurrenceGateway(
        [
            {
                "pm_occurrence_code": "PM-OCC-201",
                "asset_code": "P-999",
                "occurrence_date": "2026-07-15T00:00:00Z",
            }
        ]
    )

    result = get_pump_last_pm(
        "P-101",
        maintenance_history_gateway=maintenance_history_gateway,
        work_order_gateway=work_order_gateway,
        pm_occurrence_gateway=pm_occurrence_gateway,
    )

    assert result["last_pm"] is None


def test_get_pump_last_pm_succeeds_if_either_source_succeeds():
    maintenance_history_gateway = FakeMaintenanceHistoryGateway([])
    work_order_gateway = FakeWorkOrderGateway([])
    pm_occurrence_gateway = FakePMOccurrenceGateway([], success=False)

    result = get_pump_last_pm(
        "P-101",
        maintenance_history_gateway=maintenance_history_gateway,
        work_order_gateway=work_order_gateway,
        pm_occurrence_gateway=pm_occurrence_gateway,
    )

    assert result["success"] is True


def test_get_pump_last_cm_picks_most_recent_by_created_at():
    cm_report_gateway = FakeCMReportGateway(
        [
            {
                "cm_report_code": "CM-101",
                "asset_code": "P-101",
                "created_at": "2026-06-01T00:00:00Z",
            },
            {
                "cm_report_code": "CM-102",
                "asset_code": "P-101",
                "created_at": "2026-07-01T00:00:00Z",
            },
            {
                "cm_report_code": "CM-103",
                "asset_code": "P-999",
                "created_at": "2026-08-01T00:00:00Z",
            },
        ]
    )

    result = get_pump_last_cm("P-101", cm_report_gateway=cm_report_gateway)

    assert result["tag_number"] == "P-101"
    assert result["last_cm"]["cm_report_code"] == "CM-102"


def test_get_pump_last_cm_returns_none_when_no_reports():
    cm_report_gateway = FakeCMReportGateway([])

    result = get_pump_last_cm("P-101", cm_report_gateway=cm_report_gateway)

    assert result["last_cm"] is None


def test_get_pump_condition_monitoring_flag_true_when_recent_leak():
    condition_monitoring_reading_gateway = FakeConditionMonitoringReadingGateway(
        [
            {
                "condition_monitoring_reading_code": "CMON-101",
                "asset_code": "P-101",
                "reading_date": "2026-07-01T00:00:00Z",
                "mechanical_seal_leak_de": True,
                "mechanical_seal_leak_nde": False,
            }
        ]
    )

    result = get_pump_condition_monitoring_flag(
        "P-101",
        condition_monitoring_reading_gateway=condition_monitoring_reading_gateway,
        today=date(2026, 7, 10),
    )

    assert result["flagged"] is True
    assert result["window_days"] == 30
    assert result["latest_flagged_reading"]["condition_monitoring_reading_code"] == "CMON-101"


def test_get_pump_condition_monitoring_flag_false_when_no_leak():
    condition_monitoring_reading_gateway = FakeConditionMonitoringReadingGateway(
        [
            {
                "condition_monitoring_reading_code": "CMON-101",
                "asset_code": "P-101",
                "reading_date": "2026-07-01T00:00:00Z",
                "mechanical_seal_leak_de": False,
                "mechanical_seal_leak_nde": False,
            }
        ]
    )

    result = get_pump_condition_monitoring_flag(
        "P-101",
        condition_monitoring_reading_gateway=condition_monitoring_reading_gateway,
        today=date(2026, 7, 10),
    )

    assert result["flagged"] is False
    assert result["latest_flagged_reading"] is None


def test_get_pump_condition_monitoring_flag_excludes_leaks_outside_window():
    condition_monitoring_reading_gateway = FakeConditionMonitoringReadingGateway(
        [
            {
                "condition_monitoring_reading_code": "CMON-101",
                "asset_code": "P-101",
                "reading_date": "2026-01-01T00:00:00Z",
                "mechanical_seal_leak_de": True,
            }
        ]
    )

    result = get_pump_condition_monitoring_flag(
        "P-101",
        condition_monitoring_reading_gateway=condition_monitoring_reading_gateway,
        today=date(2026, 7, 10),
    )

    assert result["flagged"] is False


def test_get_pump_condition_monitoring_flag_excludes_other_assets():
    condition_monitoring_reading_gateway = FakeConditionMonitoringReadingGateway(
        [
            {
                "condition_monitoring_reading_code": "CMON-101",
                "asset_code": "P-999",
                "reading_date": "2026-07-01T00:00:00Z",
                "mechanical_seal_leak_de": True,
            }
        ]
    )

    result = get_pump_condition_monitoring_flag(
        "P-101",
        condition_monitoring_reading_gateway=condition_monitoring_reading_gateway,
        today=date(2026, 7, 10),
    )

    assert result["flagged"] is False


def test_get_pump_condition_monitoring_flag_ignores_readings_with_no_date():
    condition_monitoring_reading_gateway = FakeConditionMonitoringReadingGateway(
        [
            {
                "condition_monitoring_reading_code": "CMON-101",
                "asset_code": "P-101",
                "reading_date": None,
                "mechanical_seal_leak_de": True,
            }
        ]
    )

    result = get_pump_condition_monitoring_flag(
        "P-101",
        condition_monitoring_reading_gateway=condition_monitoring_reading_gateway,
        today=date(2026, 7, 10),
    )

    assert result["flagged"] is False


def test_get_pump_spare_parts_returns_compatible_seals_with_stock_joined():
    seal_pump_compatibility_gateway = FakeSealPumpCompatibilityGateway(
        [
            {"seal_code": "SC-001", "pump_tag_number": "641-P-5"},
            {"seal_code": "SC-002", "pump_tag_number": "305-P-2"},
        ]
    )
    seal_stock_gateway = FakeSealStockGateway(
        [{"seal_code": "SC-001", "quantity_on_hand": 4, "reorder_point": 2, "location": "Warehouse A"}]
    )
    seal_gateway = FakeSealGateway([{"seal_code": "SC-001", "seal_name": "John Crane Type 21"}])

    result = get_pump_spare_parts(
        "641-P-5",
        seal_pump_compatibility_gateway=seal_pump_compatibility_gateway,
        seal_stock_gateway=seal_stock_gateway,
        seal_gateway=seal_gateway,
    )

    assert result["tag_number"] == "641-P-5"
    assert result["spare_parts"] == [
        {
            "seal_code": "SC-001",
            "part_name": "John Crane Type 21",
            "quantity_on_hand": 4,
            "reorder_point": 2,
            "location": "Warehouse A",
        }
    ]


def test_get_pump_spare_parts_leaves_stock_fields_null_when_no_stock_row_exists():
    # A compatible seal with no seal_stock record must not be fabricated
    # as zero stock -- "unknown" and "confirmed zero" are different facts.
    seal_pump_compatibility_gateway = FakeSealPumpCompatibilityGateway(
        [{"seal_code": "SC-009", "pump_tag_number": "641-P-5"}]
    )
    seal_stock_gateway = FakeSealStockGateway([])
    seal_gateway = FakeSealGateway([{"seal_code": "SC-009", "seal_name": "Chesterton 155"}])

    result = get_pump_spare_parts(
        "641-P-5",
        seal_pump_compatibility_gateway=seal_pump_compatibility_gateway,
        seal_stock_gateway=seal_stock_gateway,
        seal_gateway=seal_gateway,
    )

    assert result["spare_parts"] == [
        {
            "seal_code": "SC-009",
            "part_name": "Chesterton 155",
            "quantity_on_hand": None,
            "reorder_point": None,
            "location": None,
        }
    ]


def test_get_pump_spare_parts_returns_empty_list_when_no_compatible_seals():
    seal_pump_compatibility_gateway = FakeSealPumpCompatibilityGateway([])
    seal_stock_gateway = FakeSealStockGateway([])
    seal_gateway = FakeSealGateway([])

    result = get_pump_spare_parts(
        "999-P-9",
        seal_pump_compatibility_gateway=seal_pump_compatibility_gateway,
        seal_stock_gateway=seal_stock_gateway,
        seal_gateway=seal_gateway,
    )

    assert result["spare_parts"] == []
    assert result["success"] is True


def test_get_pump_spare_parts_reports_failure_from_compatibility_gateway():
    seal_pump_compatibility_gateway = FakeSealPumpCompatibilityGateway([], success=False)
    seal_stock_gateway = FakeSealStockGateway([])
    seal_gateway = FakeSealGateway([])

    result = get_pump_spare_parts(
        "641-P-5",
        seal_pump_compatibility_gateway=seal_pump_compatibility_gateway,
        seal_stock_gateway=seal_stock_gateway,
        seal_gateway=seal_gateway,
    )

    assert result["success"] is False


def test_get_active_work_orders_filters_closed_and_by_pump():
    work_order_gateway = FakeWorkOrderGateway(
        [
            {"work_order_code": "WO-101", "asset_code": "P-101", "closed_at": None},
            {"work_order_code": "WO-102", "asset_code": "P-101", "closed_at": "2026-07-01T00:00:00Z"},
            {"work_order_code": "WO-103", "asset_code": "P-102", "closed_at": None},
        ]
    )

    result = get_active_work_orders("P-101", work_order_gateway=work_order_gateway)

    assert [wo["work_order_code"] for wo in result["work_orders"]] == ["WO-101"]


def test_get_active_work_orders_without_pump_returns_all_open():
    work_order_gateway = FakeWorkOrderGateway(
        [
            {"work_order_code": "WO-101", "asset_code": "P-101", "closed_at": None},
            {"work_order_code": "WO-102", "asset_code": "P-102", "closed_at": "2026-07-01T00:00:00Z"},
        ]
    )

    result = get_active_work_orders(work_order_gateway=work_order_gateway)

    assert [wo["work_order_code"] for wo in result["work_orders"]] == ["WO-101"]


def test_get_assigned_role_returns_role_artifact(tmp_path):
    _seed_organization(tmp_path)

    work_order_gateway = FakeWorkOrderGateway(
        detail_responses={
            "WO-101": {
                "success": True,
                "message": "found",
                "data": {"work_order_code": "WO-101", "assigned_to": "Field Technician"},
            }
        }
    )

    role = get_assigned_role(
        "LTSA-BRAIN", "WO-101", root_path=tmp_path, work_order_gateway=work_order_gateway
    )

    assert role["role"]["name"] == "Field Technician"


def test_get_assigned_role_returns_none_when_unassigned(tmp_path):
    _seed_organization(tmp_path)

    work_order_gateway = FakeWorkOrderGateway(
        detail_responses={
            "WO-101": {
                "success": True,
                "message": "found",
                "data": {"work_order_code": "WO-101", "assigned_to": None},
            }
        }
    )

    role = get_assigned_role(
        "LTSA-BRAIN", "WO-101", root_path=tmp_path, work_order_gateway=work_order_gateway
    )

    assert role is None


def test_get_assigned_role_returns_none_when_work_order_not_found(tmp_path):
    _seed_organization(tmp_path)

    work_order_gateway = FakeWorkOrderGateway(detail_responses={})

    role = get_assigned_role(
        "LTSA-BRAIN", "UNKNOWN", root_path=tmp_path, work_order_gateway=work_order_gateway
    )

    assert role is None


def test_get_recent_maintenance_reuses_command_center(tmp_path):
    _seed_organization(tmp_path)

    maintenance_history_gateway = FakeMaintenanceHistoryGateway(
        [
            {
                "maintenance_record_code": "MH-101",
                "asset_code": "P-101",
                "performed_by": "Field Technician",
                "performed_at": "2026-07-14T09:00:00.000Z",
            }
        ]
    )

    result = get_recent_maintenance(
        "LTSA-BRAIN",
        root_path=tmp_path,
        today=date(2026, 7, 14),
        pump_gateway=FakePumpGateway([]),
        work_order_gateway=FakeWorkOrderGateway([]),
        maintenance_history_gateway=maintenance_history_gateway,
    )

    assert result == [
        {
            "maintenance_code": "MH-101",
            "pump": "P-101",
            "completed_by": "Field Technician",
            "completed_time": "2026-07-14T09:00:00.000Z",
        }
    ]


def test_summarize_situation_reuses_command_center_output(tmp_path):
    _seed_organization(tmp_path)

    result = summarize_situation(
        "LTSA-BRAIN",
        root_path=tmp_path,
        today=date(2026, 7, 14),
        pump_gateway=FakePumpGateway([{"tag_number": "P-101"}]),
        work_order_gateway=FakeWorkOrderGateway([]),
        maintenance_history_gateway=FakeMaintenanceHistoryGateway([]),
    )

    assert result["summary"]["total_pumps"] == 1
    assert result["organization_summary"] == {"departments": 1, "roles": 1}
