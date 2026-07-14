from MANUFACTURING import ManufacturingOrder
from MANUFACTURING.FACTORY import DigitalFactory
from MANUFACTURING.role_recipe_registration import (
    ROLE_LINE,
    ROLE_RECIPE,
    produce_role_artifact,
    register_role_manufacturing,
)
from RUNTIME import RuntimeStatus


class _FakeRequest:
    def __init__(self, payload):
        self.payload = payload


def test_produce_role_artifact_is_pure_no_filesystem_access(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    request = _FakeRequest(
        {
            "order_id": "MO-TEST-001",
            "product_name": "LTSA-BRAIN",
            "requirements": {
                "role_name": "Field Technician",
                "department_name": "Field Operations",
                "reports_to_role_name": None,
                "responsibilities": "Perform maintenance tasks",
                "goals": "Zero unplanned downtime",
                "permissions": "Read work orders",
            },
        }
    )

    result = produce_role_artifact(request)

    assert result["role_artifact"]["role"]["name"] == "Field Technician"
    assert result["role_artifact"]["relationships"]["department"] == "Field Operations"
    assert result["role_artifact"]["relationships"]["reports_to_role"] is None
    assert list(tmp_path.iterdir()) == []


def test_produce_role_artifact_requires_role_name():
    request = _FakeRequest(
        {
            "order_id": "MO-TEST-002",
            "product_name": "LTSA-BRAIN",
            "requirements": {"department_name": "Field Operations"},
        }
    )

    try:
        produce_role_artifact(request)
    except ValueError as exc:
        assert "role_name is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_produce_role_artifact_requires_department_name():
    request = _FakeRequest(
        {
            "order_id": "MO-TEST-003",
            "product_name": "LTSA-BRAIN",
            "requirements": {"role_name": "Field Technician"},
        }
    )

    try:
        produce_role_artifact(request)
    except ValueError as exc:
        assert "department_name is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_register_role_manufacturing_registers_recipe_and_line():
    factory = DigitalFactory(factory_id="DF-TEST-ROLE", factory_name="Test Factory")

    register_role_manufacturing(factory)

    assert factory.get_recipe("ROLE") == ROLE_RECIPE
    assert factory.get_line("LINE-ROLE-001") == ROLE_LINE


def test_role_manufacturing_end_to_end_via_digital_factory():
    factory = DigitalFactory(factory_id="DF-TEST-ROLE-2", factory_name="Test Factory")
    register_role_manufacturing(factory)

    order = ManufacturingOrder(
        order_id="MO-TEST-004",
        product_name="LTSA-BRAIN",
        product_type="ROLE",
        requested_by="Test",
        requirements={
            "role_name": "Field Technician",
            "department_name": "Field Operations",
        },
    )

    response = factory.manufacture_order(order)

    assert response.status == RuntimeStatus.SUCCESS
    assert response.output["role_artifact"]["role"]["name"] == "Field Technician"
