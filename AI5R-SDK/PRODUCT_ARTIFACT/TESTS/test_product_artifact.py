import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PRODUCT_ENGINE import ProductSpecification
from PRODUCT_ARTIFACT import ProductArtifact


def test_product_artifact_is_created(tmp_path):
    specification = ProductSpecification(
        product_name="Digital Employee",
        domains=[
            "Identity",
            "Memory",
        ],
    )

    artifact = ProductArtifact(tmp_path)

    result = artifact.manufacture(specification)

    assert result["status"] == "PRODUCT_MANUFACTURED"
    assert result["artifact"]["status"] == "MANUFACTURED"

    product_path = (
        tmp_path /
        "PRODUCTS" /
        "DIGITAL_EMPLOYEE"
    )

    assert (
        product_path /
        "product_artifact.json"
    ).exists()
