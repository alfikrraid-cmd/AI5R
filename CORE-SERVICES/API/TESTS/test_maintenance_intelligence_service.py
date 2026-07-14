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
    get_pump_history,
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
