import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BUSINESS.business_model_object import BusinessModelObject


def test_business_model_object():

    model = BusinessModelObject(
        product_code="WF",
        product_name="AI Workforce",
        target_customer="SME",
        revenue_model="SUBSCRIPTION",
        delivery_model="FULL_TIME",
        support_model="MANAGED_BY_AI5R",
        pricing_strategy="MONTHLY",
    )

    assert model.object_type == "BUSINESS_MODEL"
    assert model.status == "ACTIVE"
    assert model.product_code == "WF"
    assert model.revenue_model == "SUBSCRIPTION"
    assert model.business_model_id.startswith("BM-")
