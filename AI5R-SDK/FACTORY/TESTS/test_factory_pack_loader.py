import json
from pathlib import Path

from FACTORY.PACKS.factory_pack_loader import FactoryPackLoader


def test_factory_pack_loader_loads_json(tmp_path):
    pack_file = tmp_path / "website.factory-pack.json"

    pack_file.write_text(
        json.dumps(
            {
                "pack_code": "FP-WEBSITE-001",
                "pack_name": "Website Factory Pack",
                "product_type": "WEBSITE",
                "capabilities": ["GENERATE_HTML", "GENERATE_COPY"],
                "recipe_path": "PRODUCTS/WEBSITE/recipe.json",
                "metadata": {
                    "version": "0.1"
                },
            }
        )
    )

    loader = FactoryPackLoader()
    pack = loader.load(pack_file)

    assert pack.pack_code == "FP-WEBSITE-001"
    assert pack.product_type == "WEBSITE"
    assert "GENERATE_HTML" in pack.capabilities
    assert pack.validate() is True
