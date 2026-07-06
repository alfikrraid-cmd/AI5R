import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PRODUCT_ENGINE import ProductSpecification
from PRODUCT_REGISTRY import ProductRegistry


def test_product_registry_registers_product(tmp_path):
    specification = ProductSpecification(
        product_name="Digital Employee",
        domains=[
            "Identity",
            "Memory",
            "Capability",
        ],
    )

    registry = ProductRegistry(tmp_path)

    result = registry.register(specification)

    assert result["status"] == "REGISTERED"
    assert result["product"] == "DIGITAL_EMPLOYEE"
    assert result["version"] == "1.0"
    assert result["artifact"]["status"] == "MANUFACTURED"


def test_product_registry_gets_registered_product(tmp_path):
    specification = ProductSpecification(
        product_name="Digital Employee",
        domains=[
            "Identity",
            "Memory",
        ],
    )

    registry = ProductRegistry(tmp_path)
    registry.register(specification)

    product = registry.get("digital employee")

    assert product is not None
    assert product["product"] == "DIGITAL_EMPLOYEE"
    assert product["status"] == "REGISTERED"


def test_product_registry_returns_none_for_unknown_product(tmp_path):
    registry = ProductRegistry(tmp_path)

    result = registry.get("Unknown Product")

    assert result is None
