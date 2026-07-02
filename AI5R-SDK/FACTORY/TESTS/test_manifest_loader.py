import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from manifest_loader import ManifestLoader


def test_manifest_loader():
    manifest_path = Path("PRODUCTS/LTSA-BRAIN/product.manifest.json")

    loader = ManifestLoader()
    unit = loader.load(str(manifest_path))

    assert unit.product == "LTSA-BRAIN"
    assert len(unit.entities) >= 1

    entity_names = [entity.name for entity in unit.entities]

    assert "customer" in entity_names
    assert "pump" in entity_names
    assert "asset" in entity_names
    assert "inspection" in entity_names
    assert "maintenance" in entity_names

    assert unit.metadata["product"]["display_name"] == "LTSA Brain"
    assert unit.metadata["artifacts"]["database"] is True

    print("FM-100.2 Manifest Loader OK")


if __name__ == "__main__":
    test_manifest_loader()
