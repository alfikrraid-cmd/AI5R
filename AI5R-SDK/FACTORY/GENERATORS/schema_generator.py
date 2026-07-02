"""
FM-100.3.2 Schema Generator

Generates schema.json from a CompilationUnit.
"""

import json
from pathlib import Path


class SchemaGenerator:
    def generate(self, unit, output_path: str) -> dict:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        schema = {
            "product": unit.product,
            "version": unit.metadata.get("product", {}).get("version", "1.0.0"),
            "entities": []
        }

        for entity in unit.entities:
            schema["entities"].append({
                "name": entity.name,
                "fields": [
                    {"name": "id", "type": "integer", "primary_key": True},
                    {"name": "code", "type": "string", "required": True, "unique": True},
                    {"name": "name", "type": "string", "required": True},
                    {"name": "status", "type": "string", "default": "active"},
                    {"name": "created_at", "type": "datetime"},
                    {"name": "updated_at", "type": "datetime"}
                ]
            })

        path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
        return schema
