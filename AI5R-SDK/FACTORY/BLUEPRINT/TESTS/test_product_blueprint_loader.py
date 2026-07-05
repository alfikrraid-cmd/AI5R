from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from FACTORY.BLUEPRINT import ProductBlueprintLoader


def test_loader_loads_ltsa_ai_product_blueprint():
    blueprint = ProductBlueprintLoader().load(
        REPO / "PRODUCTS/LTSA-AI/product.blueprint.json"
    )

    assert blueprint["product"]["name"] == "LTSA AI"
    assert blueprint["product"]["owner"] == "AI5R"
    assert blueprint["pipeline"][0] == "MS-001"
    assert blueprint["pipeline"][-1] == "MS-011"
    assert len(blueprint["pipeline"]) == 11


def test_loader_rejects_missing_blueprint():
    try:
        ProductBlueprintLoader().load("missing.blueprint.json")
    except FileNotFoundError as exc:
        assert "Product blueprint not found" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError")
