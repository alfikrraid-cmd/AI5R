import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PRODUCT_ENGINE import ProductSpecification
from PRODUCT_RELEASE import ProductReleaseManager


def test_product_release_manager_releases_product(tmp_path):
    specification = ProductSpecification(
        product_name="Digital Employee",
        domains=[
            "Identity",
            "Memory",
            "Capability",
            "Decision",
        ],
    )

    manager = ProductReleaseManager(tmp_path)
    result = manager.release(specification)

    assert result["status"] == "PRODUCT_RELEASED"
    assert result["product"] == "DIGITAL_EMPLOYEE"
    assert result["release"]["status"] == "RELEASED"

    release_file = (
        tmp_path /
        "PRODUCTS" /
        "DIGITAL_EMPLOYEE" /
        "release_manifest.json"
    )

    assert release_file.exists()

    data = json.loads(release_file.read_text())

    assert data["product"] == "DIGITAL_EMPLOYEE"
    assert data["status"] == "RELEASED"
    assert len(data["domains"]) == 4
