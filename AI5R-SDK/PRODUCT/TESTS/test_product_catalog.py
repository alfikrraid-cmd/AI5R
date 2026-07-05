import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PRODUCT.product_object import ProductObject
from PRODUCT.product_engine import ProductEngine
from PRODUCT.product_catalog import ProductCatalog


def test_product_catalog():

    product = ProductObject(
        product_code="WF",
        product_name="AI Workforce",
        category="PLATFORM_PRODUCT",
        version="1.0.0",
        description="Digital Workforce Platform",
        owner="AI5R",
        runtime="Enterprise Kernel",
    )

    product_result = ProductEngine().build(product)

    catalog = ProductCatalog()

    registration = catalog.register(product_result)

    assert registration["status"] == "REGISTERED"
    assert catalog.get(product.product_id) == product_result
    assert catalog.list_all() == [product_result]
    assert catalog.list_by_category("PLATFORM_PRODUCT") == [product_result]
    assert catalog.list_by_owner("AI5R") == [product_result]
