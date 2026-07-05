import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PRODUCT.product_object import ProductObject


def test_product_object():

    product = ProductObject(
        product_code="WF",
        product_name="AI Workforce",
        category="PLATFORM_PRODUCT",
        version="1.0.0",
        description="Digital Workforce Platform",
        owner="AI5R",
        runtime="Enterprise Kernel",
    )

    assert product.object_type == "PRODUCT"
    assert product.status == "ACTIVE"
    assert product.product_code == "WF"
    assert product.product_name == "AI Workforce"
    assert product.product_id.startswith("PROD-")
