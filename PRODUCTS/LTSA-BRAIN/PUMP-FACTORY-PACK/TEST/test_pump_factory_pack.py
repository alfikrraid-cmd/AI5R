"""Behavioral tests for the Pump Factory Pack definition and its recipe.

`pump.factory-pack.json` is a FACTORY.PACKS.FactoryPack instance, loadable by
the existing, unmodified FactoryPackLoader. `recipe.json` is the v1 minimal
recipe format Chief Architect approved for this MWO (MWO-LTSA-050 WP-001) --
the first concrete recipe.json in the repository, since FactoryPack.recipe_path
previously pointed at no real file anywhere. Future Factory Packs (Seal,
Maintenance, Installation) may reuse and extend this shape.

Run with: python -m pytest PRODUCTS/LTSA-BRAIN/PUMP-FACTORY-PACK/TEST/
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_AI5R_SDK_PATH = Path(__file__).resolve().parents[4] / "AI5R-SDK"
if str(_AI5R_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_AI5R_SDK_PATH))

from FACTORY.PACKS.factory_pack_loader import FactoryPackLoader  # noqa: E402

PACK_DIR = Path(__file__).resolve().parents[1]
PACK_FILE = PACK_DIR / "pump.factory-pack.json"
RECIPE_FILE = PACK_DIR / "recipe.json"


def test_pump_factory_pack_loads_and_validates():
    pack = FactoryPackLoader().load(PACK_FILE)

    assert pack.pack_code == "FP-PUMP-001"
    assert pack.product_type == "PUMP"
    assert "IDENTITY_RESOLUTION" in pack.capabilities
    assert "RELATIONSHIP_RESOLUTION" in pack.capabilities
    assert pack.recipe_path == "PRODUCTS/LTSA-BRAIN/PUMP-FACTORY-PACK/recipe.json"
    assert pack.validate() is True


def test_pump_recipe_json_exists_and_matches_the_v1_minimal_schema():
    recipe = json.loads(RECIPE_FILE.read_text())

    assert recipe["recipe_id"] == "RECIPE-PUMP-001"
    assert recipe["recipe_version"] == "1"
    assert recipe["object_type"] == "PUMP"
    assert recipe["identity_key"] == "tag_number"
    assert recipe["relationship_keys"] == ["seal_type"]
    assert recipe["stations"] == ["PumpManufacturingStation"]
