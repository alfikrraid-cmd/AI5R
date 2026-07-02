"""
FM-100.3.3 OpenAPI Generator

Generates openapi.json from a CompilationUnit.
"""

import json
from pathlib import Path


class OpenAPIGenerator:
    def generate(self, unit, output_path: str) -> dict:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        product_meta = unit.metadata.get("product", {})
        title = f"{product_meta.get('display_name', unit.product)} API"
        version = product_meta.get("version", "1.0.0")

        openapi = {
            "openapi": "3.0.0",
            "info": {
                "title": title,
                "version": version
            },
            "paths": {}
        }

        for entity in unit.entities:
            plural = f"{entity.name}s"
            tag = entity.name.capitalize()

            openapi["paths"][f"/{plural}"] = {
                "get": {
                    "tags": [tag],
                    "summary": f"List {plural}",
                    "responses": {
                        "200": {"description": "Successful response"}
                    }
                },
                "post": {
                    "tags": [tag],
                    "summary": f"Create {entity.name}",
                    "responses": {
                        "201": {"description": "Created"}
                    }
                }
            }

            openapi["paths"][f"/{plural}/{{id}}"] = {
                "get": {
                    "tags": [tag],
                    "summary": f"Get {entity.name} detail",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"}
                        }
                    ],
                    "responses": {
                        "200": {"description": "Successful response"},
                        "404": {"description": "Not found"}
                    }
                },
                "put": {
                    "tags": [tag],
                    "summary": f"Update {entity.name}",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"}
                        }
                    ],
                    "responses": {
                        "200": {"description": "Updated"},
                        "404": {"description": "Not found"}
                    }
                },
                "delete": {
                    "tags": [tag],
                    "summary": f"Delete {entity.name}",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"}
                        }
                    ],
                    "responses": {
                        "200": {"description": "Deleted"},
                        "404": {"description": "Not found"}
                    }
                }
            }

        path.write_text(json.dumps(openapi, indent=2), encoding="utf-8")
        return openapi
