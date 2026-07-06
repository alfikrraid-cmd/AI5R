import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PRODUCT_ENGINE import ProductSpecification
from PRODUCT_ASSEMBLY import ProductAssembly


def test_product_assembly_builds_assembled_product(tmp_path):
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

    assembly = ProductAssembly(tmp_path)
    result = assembly.assemble(specification)

    product_path = tmp_path / "PRODUCTS" / "DIGITAL_EMPLOYEE"

    assert result["status"] == "PRODUCT_ASSEMBLED"
    assert result["product"] == "DIGITAL_EMPLOYEE"
    assert product_path.exists()
    assert (product_path / "assembly_manifest.py").exists()
    assert len(result["assembly_units"]) == 4
    assert result["assembly_units"][0]["status"] == "ASSEMBLED"


def test_product_assembly_rejects_invalid_specification(tmp_path):
    assembly = ProductAssembly(tmp_path)

    try:
        assembly.assemble(ProductSpecification(product_name=""))
    except ValueError as error:
        assert str(error) == "product_name is required"
    else:
        raise AssertionError("Expected ValueError")
