import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PRODUCT.product_object import ProductObject
from PRODUCT.product_engine import ProductEngine


def test_product_engine():

    engine = ProductEngine()

    product = ProductObject(
        product_code="WF",
        product_name="AI Workforce",
        category="PLATFORM_PRODUCT",
        version="1.0.0",
        description="Digital Workforce Platform",
        owner="AI5R",
        runtime="Enterprise Kernel",
    )

    result = engine.build(product)

    assert result["status"] == "READY"
    assert result["product"] == product
    assert result["profile"]["product_code"] == "WF"
    assert result["profile"]["runtime"] == "Enterprise Kernel"
