import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PRODUCT.product_manifest import ProductManifest


def test_product_manifest():

    manifest = ProductManifest(
        product_code="WF",
        product_name="AI Workforce",
        version="1.0.0",
        runtime="Enterprise Kernel",
        entrypoint="WORKFORCE.digital_employee_factory",
        dependencies=[
            "KERNEL",
            "IDENTITY",
            "POSITION",
        ],
        capabilities=[
            "DIGITAL_EMPLOYEE_MANUFACTURING",
        ],
        policies=[
            "EMPLOYEE_GOVERNANCE",
        ],
        metadata={
            "owner": "AI5R",
        },
    )

    assert manifest.object_type == "PRODUCT_MANIFEST"
    assert manifest.status == "READY"
    assert manifest.product_code == "WF"
    assert manifest.entrypoint == "WORKFORCE.digital_employee_factory"
    assert "KERNEL" in manifest.dependencies
