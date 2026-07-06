import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PRODUCT_ENGINE import ProductSpecification
from PRODUCT_FACTORY import ProductFactory


def test_product_factory_builds_product_with_domains(tmp_path):
    specification = ProductSpecification(
        product_name="Digital Employee",
        domains=[
            "Identity",
            "Memory",
            "Capability",
        ],
        interfaces=[
            "REST",
            "EVENT",
        ],
    )

    factory = ProductFactory(tmp_path)
    result = factory.build(specification)

    product_path = tmp_path / "PRODUCTS" / "DIGITAL_EMPLOYEE"

    assert result["status"] == "PRODUCT_BUILT"
    assert result["product"] == "DIGITAL_EMPLOYEE"
    assert product_path.exists()
    assert (product_path / "product_manifest.py").exists()

    assert (tmp_path / "IDENTITY").exists()
    assert (tmp_path / "MEMORY").exists()
    assert (tmp_path / "CAPABILITY").exists()

    assert len(result["domains"]) == 3
    assert result["domains"][0]["status"] == "VALID"


def test_product_factory_rejects_invalid_specification(tmp_path):
    factory = ProductFactory(tmp_path)

    try:
        factory.build(ProductSpecification(product_name=""))
    except ValueError as error:
        assert str(error) == "product_name is required"
    else:
        raise AssertionError("Expected ValueError")
