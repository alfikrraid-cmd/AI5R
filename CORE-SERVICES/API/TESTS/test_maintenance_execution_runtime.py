import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.company_manufacturing import manufacture_company
from API.department_manufacturing import manufacture_department
from API.maintenance_execution_runtime import execute_maintenance
from API.role_manufacturing import manufacture_role


class FakePumpGateway:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def get_pump(self, tag_number):
        self.calls.append(tag_number)
        return self._response


class FakeWorkOrderGateway:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def create_work_order(self, payload):
        self.calls.append(payload)
        return self._response


class FakeMaintenanceHistoryGateway:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def create_maintenance_history(self, payload):
        self.calls.append(payload)
        return self._response


def _seed_role(tmp_path, product_name="LTSA-BRAIN"):
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


def test_execute_maintenance_runs_full_flow_and_returns_runtime_result(tmp_path):
    _seed_role(tmp_path)

    pump_gateway = FakePumpGateway(
        {
            "success": True,
            "message": "Pump detail found",
            "data": {"tag_number": "P-101", "pump_type": "Centrifugal"},
        }
    )
    work_order_gateway = FakeWorkOrderGateway(
        {
            "success": True,
            "message": "Work order created successfully",
            "data": {"work_order_code": "WO-101"},
        }
    )
    maintenance_history_gateway = FakeMaintenanceHistoryGateway(
        {
            "success": True,
            "message": "Maintenance history record created successfully",
            "data": {"maintenance_record_code": "MH-101"},
        }
    )

    result = execute_maintenance(
        product_name="LTSA-BRAIN",
        tag_number="P-101",
        work_order_code="WO-101",
        maintenance_record_code="MH-101",
        description="Bearing replacement",
        action_taken="Replaced bearing",
        role_name="Field Technician",
        performed_by="Field Technician",
        root_path=tmp_path,
        pump_gateway=pump_gateway,
        work_order_gateway=work_order_gateway,
        maintenance_history_gateway=maintenance_history_gateway,
    )

    assert result["success"] is True
    assert result["step"] == "COMPLETE"
    assert result["pump"]["data"]["tag_number"] == "P-101"
    assert result["role"]["role"]["name"] == "Field Technician"
    assert result["work_order"]["data"]["work_order_code"] == "WO-101"
    assert result["maintenance_history"]["data"]["maintenance_record_code"] == "MH-101"

    assert pump_gateway.calls == ["P-101"]
    assert work_order_gateway.calls[0]["asset_code"] == "P-101"
    assert work_order_gateway.calls[0]["asset_type"] == "Centrifugal"
    assert work_order_gateway.calls[0]["assigned_to"] == "Field Technician"
    assert maintenance_history_gateway.calls[0]["work_order_code"] == "WO-101"
    assert maintenance_history_gateway.calls[0]["asset_code"] == "P-101"


def test_execute_maintenance_without_role_name_skips_role_lookup(tmp_path):
    _seed_role(tmp_path)

    pump_gateway = FakePumpGateway(
        {"success": True, "message": "found", "data": {"tag_number": "P-101", "pump_type": "Centrifugal"}}
    )
    work_order_gateway = FakeWorkOrderGateway(
        {"success": True, "message": "created", "data": {"work_order_code": "WO-101"}}
    )
    maintenance_history_gateway = FakeMaintenanceHistoryGateway(
        {"success": True, "message": "created", "data": {"maintenance_record_code": "MH-101"}}
    )

    result = execute_maintenance(
        product_name="LTSA-BRAIN",
        tag_number="P-101",
        work_order_code="WO-101",
        maintenance_record_code="MH-101",
        description="Bearing replacement",
        action_taken="Replaced bearing",
        root_path=tmp_path,
        pump_gateway=pump_gateway,
        work_order_gateway=work_order_gateway,
        maintenance_history_gateway=maintenance_history_gateway,
    )

    assert result["success"] is True
    assert result["role"] is None
    assert work_order_gateway.calls[0]["assigned_to"] is None


def test_execute_maintenance_stops_when_pump_not_found(tmp_path):
    pump_gateway = FakePumpGateway(
        {"success": False, "message": "Pump not found", "data": None}
    )
    work_order_gateway = FakeWorkOrderGateway({"success": True, "message": "created", "data": {}})
    maintenance_history_gateway = FakeMaintenanceHistoryGateway(
        {"success": True, "message": "created", "data": {}}
    )

    result = execute_maintenance(
        product_name="LTSA-BRAIN",
        tag_number="UNKNOWN",
        work_order_code="WO-101",
        maintenance_record_code="MH-101",
        description="Bearing replacement",
        action_taken="Replaced bearing",
        root_path=tmp_path,
        pump_gateway=pump_gateway,
        work_order_gateway=work_order_gateway,
        maintenance_history_gateway=maintenance_history_gateway,
    )

    assert result["success"] is False
    assert result["step"] == "RETRIEVE_PUMP"
    assert result["work_order"] is None
    assert result["maintenance_history"] is None
    assert work_order_gateway.calls == []
    assert maintenance_history_gateway.calls == []


def test_execute_maintenance_stops_when_work_order_creation_fails(tmp_path):
    pump_gateway = FakePumpGateway(
        {"success": True, "message": "found", "data": {"tag_number": "P-101", "pump_type": "Centrifugal"}}
    )
    work_order_gateway = FakeWorkOrderGateway(
        {"success": False, "message": "work_order_code already exists: WO-101", "data": None}
    )
    maintenance_history_gateway = FakeMaintenanceHistoryGateway(
        {"success": True, "message": "created", "data": {}}
    )

    result = execute_maintenance(
        product_name="LTSA-BRAIN",
        tag_number="P-101",
        work_order_code="WO-101",
        maintenance_record_code="MH-101",
        description="Bearing replacement",
        action_taken="Replaced bearing",
        root_path=tmp_path,
        pump_gateway=pump_gateway,
        work_order_gateway=work_order_gateway,
        maintenance_history_gateway=maintenance_history_gateway,
    )

    assert result["success"] is False
    assert result["step"] == "CREATE_WORK_ORDER"
    assert result["maintenance_history"] is None
    assert maintenance_history_gateway.calls == []


def test_execute_maintenance_stops_when_maintenance_history_creation_fails(tmp_path):
    pump_gateway = FakePumpGateway(
        {"success": True, "message": "found", "data": {"tag_number": "P-101", "pump_type": "Centrifugal"}}
    )
    work_order_gateway = FakeWorkOrderGateway(
        {"success": True, "message": "created", "data": {"work_order_code": "WO-101"}}
    )
    maintenance_history_gateway = FakeMaintenanceHistoryGateway(
        {
            "success": False,
            "message": "maintenance_record_code already exists: MH-101",
            "data": None,
        }
    )

    result = execute_maintenance(
        product_name="LTSA-BRAIN",
        tag_number="P-101",
        work_order_code="WO-101",
        maintenance_record_code="MH-101",
        description="Bearing replacement",
        action_taken="Replaced bearing",
        root_path=tmp_path,
        pump_gateway=pump_gateway,
        work_order_gateway=work_order_gateway,
        maintenance_history_gateway=maintenance_history_gateway,
    )

    assert result["success"] is False
    assert result["step"] == "CREATE_MAINTENANCE_HISTORY"
    assert result["work_order"]["data"]["work_order_code"] == "WO-101"


def test_execute_maintenance_raises_when_role_does_not_exist(tmp_path):
    _seed_role(tmp_path)

    pump_gateway = FakePumpGateway(
        {"success": True, "message": "found", "data": {"tag_number": "P-101", "pump_type": "Centrifugal"}}
    )
    work_order_gateway = FakeWorkOrderGateway({"success": True, "message": "created", "data": {}})
    maintenance_history_gateway = FakeMaintenanceHistoryGateway(
        {"success": True, "message": "created", "data": {}}
    )

    try:
        execute_maintenance(
            product_name="LTSA-BRAIN",
            tag_number="P-101",
            work_order_code="WO-101",
            maintenance_record_code="MH-101",
            description="Bearing replacement",
            action_taken="Replaced bearing",
            role_name="Nonexistent Role",
            root_path=tmp_path,
            pump_gateway=pump_gateway,
            work_order_gateway=work_order_gateway,
            maintenance_history_gateway=maintenance_history_gateway,
        )
    except ValueError as exc:
        assert "no Role artifact found" in str(exc)
    else:
        raise AssertionError("Expected ValueError")

    assert work_order_gateway.calls == []
