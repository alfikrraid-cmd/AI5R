import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BUSINESS.pricing_model import PricingModel


def test_pricing_model():

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

    assert pricing.object_type == "PRICING_MODEL"
    assert pricing.status == "ACTIVE"
    assert pricing.product_code == "WF"
    assert pricing.plan_code == "FULL_TIME"
    assert pricing.billing_cycle == "MONTHLY"
    assert pricing.currency == "IDR"
    assert pricing.pricing_id.startswith("PRICE-")
