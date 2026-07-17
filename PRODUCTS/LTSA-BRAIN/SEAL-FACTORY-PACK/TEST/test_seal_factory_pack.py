"""Behavioral tests for the Seal Factory Pack definition and its recipe.
Mirrors test_pump_factory_pack.py.

Run with: python -m pytest PRODUCTS/LTSA-BRAIN/SEAL-FACTORY-PACK/TEST/
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
PACK_FILE = PACK_DIR / "seal.factory-pack.json"
RECIPE_FILE = PACK_DIR / "recipe.json"


def test_seal_factory_pack_loads_and_validates():
    pack = FactoryPackLoader().load(PACK_FILE)

    assert pack.pack_code == "FP-SEAL-001"
    assert pack.product_type == "SEAL"
    assert "IDENTITY_RESOLUTION" in pack.capabilities
    assert "RELATIONSHIP_RESOLUTION" in pack.capabilities
    assert pack.recipe_path == "PRODUCTS/LTSA-BRAIN/SEAL-FACTORY-PACK/recipe.json"
    assert pack.validate() is True


def test_seal_recipe_json_exists_and_matches_the_v1_minimal_schema():
    recipe = json.loads(RECIPE_FILE.read_text())

    assert recipe["recipe_id"] == "RECIPE-SEAL-001"
    assert recipe["recipe_version"] == "1"
    assert recipe["object_type"] == "SEAL"
    assert recipe["identity_key"] == "seal_code"
    assert recipe["relationship_keys"] == ["compatible_seal_name"]
    assert recipe["stations"] == ["SealManufacturingStation"]
