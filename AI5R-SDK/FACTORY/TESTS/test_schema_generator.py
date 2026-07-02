import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from manifest_loader import ManifestLoader
from GENERATORS.schema_generator import SchemaGenerator


def test_schema_generator():
    manifest_path = Path("PRODUCTS/LTSA-BRAIN/product.manifest.json")
    output_path = Path("PRODUCTS/LTSA-BRAIN/RELEASE/schema.json")

    unit = ManifestLoader().load(str(manifest_path))
    schema = SchemaGenerator().generate(unit, str(output_path))

    assert output_path.exists()
    assert schema["product"] == "LTSA-BRAIN"

    entity_names = [entity["name"] for entity in schema["entities"]]
    assert "customer" in entity_names
    assert "pump" in entity_names
    assert "asset" in entity_names
    assert "inspection" in entity_names
    assert "maintenance" in entity_names

    print("FM-100.3.2 Schema Generator OK")


if __name__ == "__main__":
    test_schema_generator()
