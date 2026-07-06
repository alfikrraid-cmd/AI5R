from datetime import datetime, UTC
from pathlib import Path
import json

from PRODUCT_ENGINE import ProductSpecification
from PRODUCT_MANUFACTURING import ProductManufacturingController


class ProductReleaseManager:
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.controller = ProductManufacturingController(root_path)

    def release(self, specification: ProductSpecification):
        manufactured = self.controller.manufacture(specification)

        product = manufactured["product"]
        product_path = self.root_path / "PRODUCTS" / product
        release_path = product_path / "release_manifest.json"

        release_manifest = {
            "product": product,
            "version": manufactured["version"],
            "status": "RELEASED",
            "released_at": datetime.now(UTC).isoformat(),
            "runtime_status": manufactured["runtime_status"],
            "domains": manufactured["domains"],
            "artifact_path": manufactured["artifact_path"],
        }

        release_path.write_text(
            json.dumps(release_manifest, indent=2),
            encoding="utf-8",
        )

        return {
            "status": "PRODUCT_RELEASED",
            "product": product,
            "version": manufactured["version"],
            "release_manifest": str(release_path),
            "release": release_manifest,
        }
