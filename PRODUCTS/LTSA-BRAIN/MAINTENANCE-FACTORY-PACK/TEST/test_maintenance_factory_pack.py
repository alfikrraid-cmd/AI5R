"""Behavioral tests for the Maintenance Factory Pack definition and its
recipe. Mirrors test_pump_factory_pack.py / test_seal_factory_pack.py,
extended for Maintenance's two object types (recipe.json v1.1 shape,
reusing and extending Pump's v1 schema per its own docstring's stated
intent).

Run with: python -m pytest PRODUCTS/LTSA-BRAIN/MAINTENANCE-FACTORY-PACK/TEST/
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
PACK_FILE = PACK_DIR / "maintenance.factory-pack.json"
RECIPE_FILE = PACK_DIR / "recipe.json"


def test_maintenance_factory_pack_loads_and_validates():
    pack = FactoryPackLoader().load(PACK_FILE)

    assert pack.pack_code == "FP-MAINTENANCE-001"
    assert pack.product_type == "MAINTENANCE"
    assert "IDENTITY_RESOLUTION" in pack.capabilities
    assert "RELATIONSHIP_RESOLUTION" in pack.capabilities
    assert pack.recipe_path == "PRODUCTS/LTSA-BRAIN/MAINTENANCE-FACTORY-PACK/recipe.json"
    assert pack.validate() is True


def test_maintenance_recipe_json_exists_and_matches_the_v1_1_extended_schema():
    recipe = json.loads(RECIPE_FILE.read_text())

    assert recipe["recipe_id"] == "RECIPE-MAINTENANCE-001"
    assert recipe["recipe_version"] == "1"
    assert recipe["object_types"] == ["WORK_ORDER", "MAINTENANCE_RECORD"]
    assert recipe["identity_keys"] == {
        "WORK_ORDER": "work_order_code",
        "MAINTENANCE_RECORD": "maintenance_record_code",
    }
    assert recipe["relationship_keys"] == {
        "WORK_ORDER": ["asset_code", "asset_type"],
        "MAINTENANCE_RECORD": ["asset_code", "asset_type", "work_order_code"],
    }
    assert recipe["stations"] == ["MaintenanceManufacturingStation"]
