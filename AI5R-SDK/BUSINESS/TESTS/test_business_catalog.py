import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BUSINESS.business_catalog import BusinessCatalog
from BUSINESS.business_model_object import BusinessModelObject
from BUSINESS.pricing_model import PricingModel
from BUSINESS.delivery_model import DeliveryModel


def test_business_catalog():

    catalog = BusinessCatalog()

    business_model = BusinessModelObject(
        product_code="WF",
        product_name="AI Workforce",
        target_customer="SME",
        revenue_model="SUBSCRIPTION",
        delivery_model="FULL_TIME",
        support_model="MANAGED_BY_AI5R",
        pricing_strategy="MONTHLY",
    )

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

    delivery = DeliveryModel(
        product_code="WF",
        delivery_code="MANAGED_FULL_TIME",
        delivery_name="Managed Full Time Digital Employee",
        deployment_type="CLOUD",
        management_type="MANAGED_BY_AI5R",
        service_scope="FULL_TIME_DIGITAL_EMPLOYEE",
        support_level="STANDARD",
    )

    r1 = catalog.register(business_model)
    r2 = catalog.register(pricing)
    r3 = catalog.register(delivery)

    assert r1["status"] == "REGISTERED"
    assert r2["status"] == "REGISTERED"
    assert r3["status"] == "REGISTERED"

    assert catalog.get(business_model.business_model_id) == business_model
    assert len(catalog.list_all()) == 3
    assert catalog.list_by_type("PRICING_MODEL") == [pricing]
    assert catalog.list_by_product("WF") == [
        business_model,
        pricing,
        delivery,
    ]
