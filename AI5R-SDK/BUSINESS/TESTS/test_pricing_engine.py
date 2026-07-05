import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BUSINESS.pricing_model import PricingModel
from BUSINESS.pricing_engine import PricingEngine


def test_pricing_engine_without_overage():

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

    result = PricingEngine().calculate(
        pricing=pricing,
        used_units=100,
    )

    assert result["status"] == "CALCULATED"
    assert result["overage_units"] == 0
    assert result["total_amount"] == 5000000


def test_pricing_engine_with_overage():

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

    result = PricingEngine().calculate(
        pricing=pricing,
        used_units=170,
    )

    assert result["status"] == "CALCULATED"
    assert result["overage_units"] == 10
    assert result["total_amount"] == 5500000
