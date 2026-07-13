from MANUFACTURING import ManufacturingOrder
from MANUFACTURING.FACTORY import DigitalFactory
from MANUFACTURING.department_recipe_registration import (
    DEPARTMENT_LINE,
    DEPARTMENT_RECIPE,
    produce_department_artifact,
    register_department_manufacturing,
)
from RUNTIME import RuntimeStatus


class _FakeRequest:
    def __init__(self, payload):
        self.payload = payload


def test_produce_department_artifact_is_pure_no_filesystem_access(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    request = _FakeRequest(
        {
            "order_id": "MO-TEST-001",
            "product_name": "LTSA-BRAIN",
            "requirements": {
                "department_name": "Field Operations",
                "company_name": "CV Razzan Teknik Mandiri",
                "parent_department_name": None,
                "responsibilities": "Maintenance execution",
            },
        }
    )

    result = produce_department_artifact(request)

    assert result["department_artifact"]["department"]["name"] == "Field Operations"
    assert result["department_artifact"]["relationships"]["company"] == "CV Razzan Teknik Mandiri"
    assert result["department_artifact"]["relationships"]["parent_department"] is None
    assert list(tmp_path.iterdir()) == []


def test_produce_department_artifact_requires_department_name():
    request = _FakeRequest(
        {
            "order_id": "MO-TEST-002",
            "product_name": "LTSA-BRAIN",
            "requirements": {"company_name": "CV Razzan Teknik Mandiri"},
        }
    )

    try:
        produce_department_artifact(request)
    except ValueError as exc:
        assert "department_name is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_produce_department_artifact_requires_company_name():
    request = _FakeRequest(
        {
            "order_id": "MO-TEST-003",
            "product_name": "LTSA-BRAIN",
            "requirements": {"department_name": "Field Operations"},
        }
    )

    try:
        produce_department_artifact(request)
    except ValueError as exc:
        assert "company_name is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_register_department_manufacturing_registers_recipe_and_line():
    factory = DigitalFactory(factory_id="DF-TEST-DEPT", factory_name="Test Factory")

    register_department_manufacturing(factory)

    assert factory.get_recipe("DEPARTMENT") == DEPARTMENT_RECIPE
    assert factory.get_line("LINE-DEPARTMENT-001") == DEPARTMENT_LINE


def test_department_manufacturing_end_to_end_via_digital_factory():
    factory = DigitalFactory(factory_id="DF-TEST-DEPT-2", factory_name="Test Factory")
    register_department_manufacturing(factory)

    order = ManufacturingOrder(
        order_id="MO-TEST-004",
        product_name="LTSA-BRAIN",
        product_type="DEPARTMENT",
        requested_by="Test",
        requirements={
            "department_name": "Field Operations",
            "company_name": "CV Razzan Teknik Mandiri",
        },
    )

    response = factory.manufacture_order(order)

    assert response.status == RuntimeStatus.SUCCESS
    assert response.output["department_artifact"]["department"]["name"] == "Field Operations"
