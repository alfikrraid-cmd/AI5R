"""
AI5R Schema Manufacturing Engine
FM-001.8
"""

import json


JSON_TYPE_MAP = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "date": "string",
    "datetime": "string"
}


class SchemaGenerator:

    def generate_json_schema(self, registry: dict) -> str:

        properties = {}
        required = []

        for field in registry["fields"]:

            properties[field["name"]] = {
                "type": JSON_TYPE_MAP.get(
                    field.get("type", "string"),
                    "string"
                )
            }

            if field.get("required", False):
                required.append(field["name"])

        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": registry["module"],
            "type": "object",
            "properties": properties,
            "required": required
        }

        return json.dumps(schema, indent=2)

    def generate_openapi(self, registry: dict) -> str:

        schema = {
            "openapi": "3.0.0",
            "info": {
                "title": registry["module"],
                "version": "1.0.0"
            },
            "components": {
                "schemas": {
                    registry["module"]: {
                        "type": "object"
                    }
                }
            }
        }

        return json.dumps(schema, indent=2)
