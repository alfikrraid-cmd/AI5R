import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BUSINESS.business_model_object import BusinessModelObject
from BUSINESS.business_engine import BusinessEngine


def test_business_engine():

    engine = BusinessEngine()

    model = BusinessModelObject(
        product_code="WF",
        product_name="AI Workforce",
        target_customer="SME",
        revenue_model="SUBSCRIPTION",
        delivery_model="FULL_TIME",
        support_model="MANAGED_BY_AI5R",
        pricing_strategy="MONTHLY",
    )

    result = engine.build(model)

    assert result["status"] == "READY"
    assert result["business_model"] == model
    assert result["profile"]["product_code"] == "WF"
    assert result["profile"]["revenue_model"] == "SUBSCRIPTION"
    assert result["profile"]["support_model"] == "MANAGED_BY_AI5R"
