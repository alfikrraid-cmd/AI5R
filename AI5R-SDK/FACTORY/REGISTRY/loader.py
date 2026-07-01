"""
AI5R Factory Registry Loader
FM-001.6
"""

from pathlib import Path
import json


class FactoryRegistryLoader:

    def __init__(self):
        self.registry_path = Path("AI5R-SDK/FACTORY/REGISTRY/MODULES")

    def load_module(self, module_name: str):
        clean_module = module_name.upper().replace("BP-", "")
        module_file = self.registry_path / f"{clean_module}.json"

        if not module_file.exists():
            raise FileNotFoundError(
                f"Factory registry not found for module: {clean_module}"
            )

        with module_file.open("r", encoding="utf-8") as file:
            data = json.load(file)

        self._validate(data)

        return data

    def _validate(self, data: dict):
        required_keys = [
            "module",
            "product",
            "table",
            "primary_key",
            "fields",
        ]

        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing registry key: {key}")

        if not isinstance(data["fields"], list):
            raise ValueError("Registry fields must be a list")

        if len(data["fields"]) == 0:
            raise ValueError("Registry fields cannot be empty")
