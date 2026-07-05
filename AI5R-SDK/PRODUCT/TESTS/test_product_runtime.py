import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PRODUCT.product_object import ProductObject
from PRODUCT.product_runtime import ProductRuntime


def test_product_runtime():

    runtime = ProductRuntime()

    product = ProductObject(
        product_code="WF",
        product_name="AI Workforce",
        category="PLATFORM_PRODUCT",
        version="1.0.0",
        description="Digital Workforce Platform",
        owner="AI5R",
        runtime="Enterprise Kernel",
    )

    result = runtime.create(product)

    assert result["status"] == "CREATED"
    assert result["registration"]["status"] == "REGISTERED"
    assert result["result"]["status"] == "READY"

    stored = runtime.get(product.product_id)

    assert stored["product"] == product
    assert runtime.list_all() == [stored]
    assert runtime.list_by_category("PLATFORM_PRODUCT") == [stored]
    assert runtime.list_by_owner("AI5R") == [stored]
