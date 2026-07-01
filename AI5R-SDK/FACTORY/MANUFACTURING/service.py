"""
AI5R Manufacturing Service
FM-001.6.6 Registry-driven Manufacturing
"""

from pathlib import Path
import importlib.util
import json


ARTIFACTS = [
    "DATABASE",
    "WORKFLOWS",
    "SCHEMAS",
    "TESTS",
    "REPORTS",
]


CRUD_OPERATIONS = [
    "LIST",
    "DETAIL",
    "CREATE",
    "UPDATE",
    "DELETE",
]


def load_registry(module_name: str):
    loader_path = Path("AI5R-SDK/FACTORY/REGISTRY/loader.py")

    spec = importlib.util.spec_from_file_location(
        "factory_registry_loader",
        loader_path,
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    loader = module.FactoryRegistryLoader()
    return loader.load_module(module_name)


class ManufacturingService:

    def manufacture_module(self, module_name: str, product: str = "LTSA-BRAIN"):

        clean_module = module_name.upper().replace("BP-", "")
        registry = load_registry(clean_module)

        root = (
            Path("PRODUCTS")
            / product
            / "BUILD-PACKS"
            / f"BP-{clean_module}"
        )

        root.mkdir(parents=True, exist_ok=True)

        for artifact in ARTIFACTS:
            (root / artifact).mkdir(exist_ok=True)

        readme = root / "README.md"
        readme.write_text(
            f"# Build Pack\n\n"
            f"Product: {product}\n"
            f"Module: {registry['module']}\n"
            f"Table: {registry['table']}\n"
            f"Primary Key: {registry['primary_key']}\n",
            encoding="utf-8"
        )

        self._generate_crud_workflows(root=root, registry=registry)

        return root

    def _generate_crud_workflows(self, root: Path, registry: dict):

        product = registry["product"]
        module_name = registry["module"]
        module_slug = module_name.lower()
        table_name = registry["table"]
        primary_key = registry["primary_key"]
        fields = registry["fields"]

        workflow_dir = root / "WORKFLOWS"

        for operation in CRUD_OPERATIONS:
            workflow = {
                "name": f"WF-{product}-{module_name}-{operation}-001",
                "nodes": [
                    {
                        "parameters": {
                            "path": f"ltsa/{module_slug}/{operation.lower()}",
                            "responseMode": "responseNode",
                            "options": {}
                        },
                        "id": f"webhook-{module_slug}-{operation.lower()}",
                        "name": "Webhook",
                        "type": "n8n-nodes-base.webhook",
                        "typeVersion": 2,
                        "position": [260, 300],
                        "webhookId": f"{product.lower()}-{module_slug}-{operation.lower()}-001"
                    },
                    {
                        "parameters": {
                            "respondWith": "json",
                            "responseBody": json.dumps({
                                "success": True,
                                "product": product,
                                "module": module_name,
                                "operation": operation,
                                "table": table_name,
                                "primary_key": primary_key
                            })
                        },
                        "id": f"response-{module_slug}-{operation.lower()}",
                        "name": "Respond to Webhook",
                        "type": "n8n-nodes-base.respondToWebhook",
                        "typeVersion": 1,
                        "position": [520, 300]
                    }
                ],
                "connections": {
                    "Webhook": {
                        "main": [
                            [
                                {
                                    "node": "Respond to Webhook",
                                    "type": "main",
                                    "index": 0
                                }
                            ]
                        ]
                    }
                },
                "settings": {
                    "executionOrder": "v1",
                    "registry": {
                        "table": table_name,
                        "primary_key": primary_key,
                        "fields": fields
                    }
                }
            }

            output = workflow_dir / f"WF-{product}-{module_name}-{operation}-001.json"
            output.write_text(json.dumps(workflow, indent=2), encoding="utf-8")
