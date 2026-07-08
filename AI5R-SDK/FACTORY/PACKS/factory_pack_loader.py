import json
from pathlib import Path

from FACTORY.PACKS.factory_pack import FactoryPack


class FactoryPackLoader:
    def load(self, path: str | Path) -> FactoryPack:
        pack_path = Path(path)

        if not pack_path.exists():
            raise FileNotFoundError(f"Factory pack not found: {pack_path}")

        data = json.loads(pack_path.read_text())

        pack = FactoryPack(
            pack_code=data.get("pack_code"),
            pack_name=data.get("pack_name"),
            product_type=data.get("product_type"),
            capabilities=data.get("capabilities", []),
            recipe_path=data.get("recipe_path"),
            metadata=data.get("metadata", {}),
        )

        pack.validate()

        return pack
