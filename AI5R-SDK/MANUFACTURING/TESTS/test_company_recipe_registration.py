from MANUFACTURING import ManufacturingOrder
from MANUFACTURING.FACTORY import DigitalFactory
from MANUFACTURING.company_recipe_registration import (
    COMPANY_LINE,
    COMPANY_RECIPE,
    produce_company_artifact,
    register_company_manufacturing,
)
from RUNTIME import RuntimeStatus


class _FakeRequest:
    def __init__(self, payload):
        self.payload = payload


def test_produce_company_artifact_is_pure_no_filesystem_access(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    request = _FakeRequest(
        {
            "order_id": "MO-TEST-001",
            "product_name": "LTSA-BRAIN",
            "requirements": {"company_name": "CV Razzan Teknik Mandiri"},
        }
    )

    result = produce_company_artifact(request)

    assert result["company_artifact"]["company"]["name"] == "CV Razzan Teknik Mandiri"
    assert result["company_artifact"]["company"]["status"] == "ACTIVE"
    assert result["company_artifact"]["relationships"]["product"] == "LTSA-BRAIN"
    assert list(tmp_path.iterdir()) == []


def test_produce_company_artifact_requires_company_name():
    request = _FakeRequest(
        {"order_id": "MO-TEST-002", "product_name": "LTSA-BRAIN", "requirements": {}}
    )

    try:
        produce_company_artifact(request)
    except ValueError as exc:
        assert "company_name is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_register_company_manufacturing_registers_recipe_and_line():
    factory = DigitalFactory(factory_id="DF-TEST", factory_name="Test Factory")

    register_company_manufacturing(factory)

    assert factory.get_recipe("COMPANY") == COMPANY_RECIPE
    assert factory.get_line("LINE-COMPANY-001") == COMPANY_LINE


def test_company_manufacturing_end_to_end_via_digital_factory():
    factory = DigitalFactory(factory_id="DF-TEST-2", factory_name="Test Factory")
    register_company_manufacturing(factory)

    order = ManufacturingOrder(
        order_id="MO-TEST-003",
        product_name="LTSA-BRAIN",
        product_type="COMPANY",
        requested_by="Test",
        requirements={"company_name": "CV Razzan Teknik Mandiri"},
    )

    response = factory.manufacture_order(order)

    assert response.status == RuntimeStatus.SUCCESS
    assert response.output["company_artifact"]["company"]["name"] == "CV Razzan Teknik Mandiri"
