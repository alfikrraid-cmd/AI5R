import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from manifest_loader import ManifestLoader
from GENERATORS.openapi_generator import OpenAPIGenerator


def test_openapi_generator():
    manifest_path = Path("PRODUCTS/LTSA-BRAIN/product.manifest.json")
    output_path = Path("PRODUCTS/LTSA-BRAIN/RELEASE/openapi.json")

    unit = ManifestLoader().load(str(manifest_path))
    openapi = OpenAPIGenerator().generate(unit, str(output_path))

    assert output_path.exists()
    assert openapi["openapi"] == "3.0.0"
    assert openapi["info"]["title"] == "LTSA Brain API"

    assert "/customers" in openapi["paths"]
    assert "/customers/{id}" in openapi["paths"]
    assert "/pumps" in openapi["paths"]
    assert "/assets" in openapi["paths"]
    assert "/inspections" in openapi["paths"]
    assert "/maintenances" in openapi["paths"]

    assert "get" in openapi["paths"]["/pumps"]
    assert "post" in openapi["paths"]["/pumps"]
    assert "get" in openapi["paths"]["/pumps/{id}"]
    assert "put" in openapi["paths"]["/pumps/{id}"]
    assert "delete" in openapi["paths"]["/pumps/{id}"]

    print("FM-100.3.3 OpenAPI Generator OK")


if __name__ == "__main__":
    test_openapi_generator()
