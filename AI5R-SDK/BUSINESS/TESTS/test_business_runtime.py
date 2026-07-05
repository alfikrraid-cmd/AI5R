import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BUSINESS.business_runtime import BusinessRuntime
from BUSINESS.business_model_object import BusinessModelObject
from BUSINESS.pricing_model import PricingModel


def test_business_runtime():

    runtime = BusinessRuntime()

    business_model = BusinessModelObject(
        product_code="WF",
        product_name="AI Workforce",
        target_customer="SME",
        revenue_model="SUBSCRIPTION",
        delivery_model="FULL_TIME",
        support_model="MANAGED_BY_AI5R",
        pricing_strategy="MONTHLY",
    )

    result = runtime.build_business_model(business_model)

    assert result["status"] == "CREATED"
    assert result["result"]["status"] == "READY"
    assert result["registration"]["status"] == "REGISTERED"

    assert runtime.get(business_model.business_model_id) == business_model
    assert runtime.list_by_type("BUSINESS_MODEL") == [business_model]
    assert runtime.list_by_product("WF") == [business_model]


def test_business_runtime_calculate_pricing():

    runtime = BusinessRuntime()

    pricing = PricingModel(
        product_code="WF",
        plan_code="FULL_TIME",
        plan_name="Full Time Digital Employee",
        billing_cycle="MONTHLY",
        price_amount=5000000,
        currency="IDR",
        included_units=160,
        overage_rate=50000,
    )

    result = runtime.calculate_pricing(
        pricing=pricing,
        used_units=170,
    )

    assert result["status"] == "CALCULATED"
    assert result["overage_units"] == 10
    assert result["total_amount"] == 5500000
