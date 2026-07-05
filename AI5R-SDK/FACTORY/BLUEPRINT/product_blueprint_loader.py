import json
from pathlib import Path
from typing import Any


class ProductBlueprintLoader:
    def load(self, blueprint_path: str | Path) -> dict[str, Any]:
        path = Path(blueprint_path)

        if not path.exists():
            raise FileNotFoundError(f"Product blueprint not found: {path}")

        with path.open("r", encoding="utf-8") as file:
            blueprint = json.load(file)

        if "product" not in blueprint:
            raise ValueError("Product blueprint requires product section")

        if "pipeline" not in blueprint:
            raise ValueError("Product blueprint requires pipeline section")

        if not blueprint["pipeline"]:
            raise ValueError("Product blueprint pipeline cannot be empty")

        return blueprint
