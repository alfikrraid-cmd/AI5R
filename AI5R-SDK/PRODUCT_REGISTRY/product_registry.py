from pathlib import Path

from PRODUCT_ARTIFACT import ProductArtifact
from PRODUCT_ENGINE import ProductSpecification


class ProductRegistry:
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.artifact_manufacturer = ProductArtifact(root_path)
        self.products = {}

    def register(self, specification: ProductSpecification):
        manufactured = self.artifact_manufacturer.manufacture(specification)
        artifact = manufactured["artifact"]

        product_name = artifact["product"]

        self.products[product_name] = {
            "product": product_name,
            "version": artifact["version"],
            "status": "REGISTERED",
            "artifact_path": manufactured["artifact_path"],
            "artifact": artifact,
        }

        return self.products[product_name]

    def get(self, product_name: str):
        normalized = product_name.strip().upper().replace(" ", "_").replace("-", "_")
        return self.products.get(normalized)
