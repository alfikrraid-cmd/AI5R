import sys
from datetime import date
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.company_manufacturing import manufacture_company
from API.department_manufacturing import manufacture_department
from API.maintenance_command_center import get_maintenance_command_center
from API.role_manufacturing import manufacture_role


class FakePumpGateway:
    def __init__(self, pumps):
        self._response = {"success": True, "message": "ok", "count": len(pumps), "data": pumps}

    def list_pumps(self):
        return self._response


class FakeWorkOrderGateway:
    def __init__(self, work_orders):
        self._response = {
            "success": True,
            "message": "ok",
            "count": len(work_orders),
            "data": work_orders,
        }

    def list_work_orders(self):
        return self._response


class FakeMaintenanceHistoryGateway:
    def __init__(self, records):
        self._response = {
            "success": True,
            "message": "ok",
            "count": len(records),
            "data": records,
        }

    def list_maintenance_history(self):
        return self._response


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


def test_command_center_summary_counts(tmp_path):
    _seed_organization(tmp_path)

    pump_gateway = FakePumpGateway([{"tag_number": "P-101"}, {"tag_number": "P-102"}])
    work_order_gateway = FakeWorkOrderGateway(
        [
            {"work_order_code": "WO-101", "closed_at": None, "status": "OPEN"},
            {"work_order_code": "WO-102", "closed_at": "2026-07-01T10:00:00.000Z", "status": "CLOSED"},
        ]
    )
    maintenance_history_gateway = FakeMaintenanceHistoryGateway(
        [
            {"maintenance_record_code": "MH-101", "performed_at": "2026-07-14T09:00:00.000Z"},
            {"maintenance_record_code": "MH-102", "performed_at": "2026-07-10T09:00:00.000Z"},
        ]
    )

    result = get_maintenance_command_center(
        "LTSA-BRAIN",
        root_path=tmp_path,
        today=date(2026, 7, 14),
        pump_gateway=pump_gateway,
        work_order_gateway=work_order_gateway,
        maintenance_history_gateway=maintenance_history_gateway,
    )

    assert result["summary"] == {
        "total_pumps": 2,
        "active_work_orders": 1,
        "completed_today": 1,
        "overdue_work_orders": 0,
    }


def test_command_center_recent_work_orders_and_maintenance(tmp_path):
    _seed_organization(tmp_path)

    pump_gateway = FakePumpGateway([])
    work_order_gateway = FakeWorkOrderGateway(
        [
            {
                "work_order_code": "WO-101",
                "asset_code": "P-101",
                "assigned_to": "Field Technician",
                "status": "OPEN",
                "closed_at": None,
            }
        ]
    )
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

    result = get_maintenance_command_center(
        "LTSA-BRAIN",
        root_path=tmp_path,
        today=date(2026, 7, 14),
        pump_gateway=pump_gateway,
        work_order_gateway=work_order_gateway,
        maintenance_history_gateway=maintenance_history_gateway,
    )

    assert result["recent_work_orders"] == [
        {
            "work_order_code": "WO-101",
            "pump": "P-101",
            "assigned_role": "Field Technician",
            "status": "OPEN",
        }
    ]
    assert result["recent_maintenance"] == [
        {
            "maintenance_code": "MH-101",
            "pump": "P-101",
            "completed_by": "Field Technician",
            "completed_time": "2026-07-14T09:00:00.000Z",
        }
    ]


def test_command_center_limits_recent_lists_to_five_most_recent(tmp_path):
    _seed_organization(tmp_path)

    work_orders = [
        {"work_order_code": f"WO-{i}", "closed_at": None, "status": "OPEN"} for i in range(8)
    ]
    maintenance_records = [
        {"maintenance_record_code": f"MH-{i}", "performed_at": "2026-07-14T09:00:00.000Z"}
        for i in range(8)
    ]

    result = get_maintenance_command_center(
        "LTSA-BRAIN",
        root_path=tmp_path,
        today=date(2026, 7, 14),
        pump_gateway=FakePumpGateway([]),
        work_order_gateway=FakeWorkOrderGateway(work_orders),
        maintenance_history_gateway=FakeMaintenanceHistoryGateway(maintenance_records),
    )

    assert len(result["recent_work_orders"]) == 5
    assert [wo["work_order_code"] for wo in result["recent_work_orders"]] == [
        "WO-0", "WO-1", "WO-2", "WO-3", "WO-4",
    ]
    assert len(result["recent_maintenance"]) == 5


def test_command_center_organization_summary(tmp_path):
    _seed_organization(tmp_path)
    manufacture_department(
        product_name="LTSA-BRAIN", department_name="Warehouse", root_path=tmp_path
    )
    manufacture_role(
        product_name="LTSA-BRAIN",
        role_name="Warehouse Lead",
        department_name="Warehouse",
        root_path=tmp_path,
    )

    result = get_maintenance_command_center(
        "LTSA-BRAIN",
        root_path=tmp_path,
        today=date(2026, 7, 14),
        pump_gateway=FakePumpGateway([]),
        work_order_gateway=FakeWorkOrderGateway([]),
        maintenance_history_gateway=FakeMaintenanceHistoryGateway([]),
    )

    assert result["organization_summary"] == {"departments": 2, "roles": 2}


def test_command_center_handles_empty_data(tmp_path):
    _seed_organization(tmp_path)

    result = get_maintenance_command_center(
        "LTSA-BRAIN",
        root_path=tmp_path,
        today=date(2026, 7, 14),
        pump_gateway=FakePumpGateway([]),
        work_order_gateway=FakeWorkOrderGateway([]),
        maintenance_history_gateway=FakeMaintenanceHistoryGateway([]),
    )

    assert result["summary"] == {
        "total_pumps": 0,
        "active_work_orders": 0,
        "completed_today": 0,
        "overdue_work_orders": 0,
    }
    assert result["recent_work_orders"] == []
    assert result["recent_maintenance"] == []


def test_command_center_fails_without_company(tmp_path):
    product_dir = tmp_path / "PRODUCTS" / "LTSA-BRAIN"
    product_dir.mkdir(parents=True, exist_ok=True)
    (product_dir / "product_artifact.json").write_text("{}", encoding="utf-8")

    try:
        get_maintenance_command_center(
            "LTSA-BRAIN",
            root_path=tmp_path,
            pump_gateway=FakePumpGateway([]),
            work_order_gateway=FakeWorkOrderGateway([]),
            maintenance_history_gateway=FakeMaintenanceHistoryGateway([]),
        )
    except ValueError as exc:
        assert "no Company artifact found" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
