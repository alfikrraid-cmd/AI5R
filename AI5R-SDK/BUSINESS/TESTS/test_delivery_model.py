import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BUSINESS.delivery_model import DeliveryModel


def test_delivery_model():

    delivery = DeliveryModel(
        product_code="WF",
        delivery_code="MANAGED_FULL_TIME",
        delivery_name="Managed Full Time Digital Employee",
        deployment_type="CLOUD",
        management_type="MANAGED_BY_AI5R",
        service_scope="FULL_TIME_DIGITAL_EMPLOYEE",
        support_level="STANDARD",
    )

    assert delivery.object_type == "DELIVERY_MODEL"
    assert delivery.status == "ACTIVE"
    assert delivery.product_code == "WF"
    assert delivery.management_type == "MANAGED_BY_AI5R"
    assert delivery.delivery_id.startswith("DEL-")
