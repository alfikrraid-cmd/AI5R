import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PRODUCT_ENGINE import ProductSpecification


def test_product_specification_build():
    specification = ProductSpecification(
        product_name="Digital Employee",
        domains=[
            "Identity",
            "Memory",
            "Capability",
            "Decision",
        ],
        interfaces=[
            "REST",
            "EVENT",
        ],
    )

    result = specification.build()

    assert result["status"] == "SPECIFIED"
    assert result["product"] == "DIGITAL_EMPLOYEE"
    assert result["version"] == "1.0"
    assert len(result["domains"]) == 4
    assert result["runtime"] == "Python"
    assert len(result["canonical_pipeline"]) == 7


def test_product_specification_requires_name():
    try:
        ProductSpecification(product_name="").build()
    except ValueError as error:
        assert str(error) == "product_name is required"
    else:
        raise AssertionError("Expected ValueError")
