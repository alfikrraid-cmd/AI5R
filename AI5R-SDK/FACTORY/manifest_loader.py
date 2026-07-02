"""
FM-100.2 Manifest Loader

Reads a product.manifest.json file and converts it into
a CompilationUnit for the AI5R manufacturing pipeline.
"""

import json
from pathlib import Path
from typing import Any, Dict

from IR.compilation_unit import CompilationUnit
from IR.entity_ir import EntityIR


class ManifestLoader:
    def load(self, manifest_path: str) -> CompilationUnit:
        path = Path(manifest_path)

        if not path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        with path.open("r", encoding="utf-8") as f:
            manifest: Dict[str, Any] = json.load(f)

        product = manifest.get("product", {})
        product_name = product.get("name")

        if not product_name:
            raise ValueError("Manifest missing product.name")

        unit = CompilationUnit(
            product=product_name,
            metadata={
                "product": product,
                "artifacts": manifest.get("artifacts", {}),
                "modules": manifest.get("modules", []),
            },
        )

        for module in manifest.get("modules", []):
            if module.get("enabled", True):
                entity = EntityIR(
                    name=module["name"],
                    fields=[],
                )
                unit.add_entity(entity)

        return unit
