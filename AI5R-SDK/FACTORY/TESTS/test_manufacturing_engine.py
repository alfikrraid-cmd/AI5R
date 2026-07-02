import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from manifest_loader import ManifestLoader
from MANUFACTURING.manufacturing_engine import ManufacturingEngine


def test_engine():
    loader = ManifestLoader()
    unit = loader.load("PRODUCTS/LTSA-BRAIN/product.manifest.json")

    engine = ManufacturingEngine()
    outputs = engine.manufacture(
        unit,
        "PRODUCTS/LTSA-BRAIN/RELEASE"
    )

    assert len(outputs) == 3
    print(outputs)
    print("FM-100.4 Manufacturing Engine OK")


if __name__ == "__main__":
    test_engine()
