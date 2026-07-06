from datetime import datetime, UTC
from pathlib import Path

from PRODUCT_REGISTRY import ProductRegistry
from PRODUCT_ENGINE import ProductSpecification


class ProductRuntime:
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.registry = ProductRegistry(root_path)
        self.running_products = {}

    def start(self, specification: ProductSpecification):
        registered = self.registry.register(specification)

        product = registered["product"]

        runtime_context = {
            "product": product,
            "version": registered["version"],
            "status": "RUNNING",
            "started_at": datetime.now(UTC).isoformat(),
            "domains": [
                unit["domain"]
                for unit in registered["artifact"]["assembly_units"]
            ],
            "artifact_path": registered["artifact_path"],
        }

        self.running_products[product] = runtime_context

        runtime_path = (
            Path(self.root_path) /
            "PRODUCTS" /
            product /
            "runtime_state.json"
        )

        runtime_path.write_text(
            str(runtime_context),
            encoding="utf-8",
        )

        return runtime_context

    def stop(self, product_name: str):
        normalized = (
            product_name.strip()
            .upper()
            .replace(" ", "_")
            .replace("-", "_")
        )

        runtime = self.running_products.get(normalized)

        if runtime is None:
            return None

        runtime["status"] = "STOPPED"
        runtime["stopped_at"] = datetime.now(UTC).isoformat()

        return runtime

    def status(self, product_name: str):
        normalized = (
            product_name.strip()
            .upper()
            .replace(" ", "_")
            .replace("-", "_")
        )

        return self.running_products.get(normalized)
