"""
FP-002
API Factory Pack

Deterministic, stateless generator that turns a Technical Architecture
dict (as produced by SolutionArchitect.plan()) into a technology-neutral
API source bundle. Pure generation only: no filesystem writes, no LLM,
no reasoning, no Manufacturing Center / Organization / Runtime coupling.
"""

from __future__ import annotations

import json
from typing import Any

DEFAULT_PRIORITY = "NORMAL"


class ApiFactoryPack:
    def manufacture(self, technical_architecture: Any) -> dict[str, Any]:
        if not isinstance(technical_architecture, dict):
            raise ValueError("technical_architecture must be a dict")

        architecture_name = technical_architecture.get("architecture_name")
        if not isinstance(architecture_name, str) or not architecture_name.strip():
            raise ValueError("architecture_name is required")

        product_name = technical_architecture.get("product_name")
        if not isinstance(product_name, str) or not product_name.strip():
            raise ValueError("product_name is required")

        modules = list(technical_architecture.get("modules") or [])
        services = list(technical_architecture.get("services") or [])
        apis = list(technical_architecture.get("apis") or [])
        database = list(technical_architecture.get("database") or [])
        constraints = list(technical_architecture.get("constraints") or [])
        priority = technical_architecture.get("priority") or DEFAULT_PRIORITY

        openapi_json = self._render_openapi_json(
            product_name, architecture_name, apis
        )
        routes_json = self._render_routes_json(architecture_name, apis)
        readme_md = self._render_readme(
            product_name,
            architecture_name,
            modules,
            services,
            apis,
            database,
            constraints,
            priority,
        )
        manifest = {
            "pack": "API",
            "architecture_name": architecture_name,
            "product_name": product_name,
            "modules": modules,
            "services": services,
            "apis": apis,
            "database": database,
            "constraints": constraints,
            "priority": priority,
            "files": ["openapi.json", "routes.json", "README_API.md"],
        }

        return {
            "openapi.json": openapi_json,
            "routes.json": routes_json,
            "api.manifest.json": manifest,
            "README_API.md": readme_md,
        }

    def _render_openapi_json(
        self, product_name: str, architecture_name: str, apis: list[str]
    ) -> str:
        paths = {
            api: {
                "get": {
                    "summary": f"{api} endpoint",
                    "responses": {"200": {"description": "OK"}},
                }
            }
            for api in apis
        }
        document = {
            "openapi": "3.0.3",
            "info": {
                "title": product_name,
                "version": "1.0.0",
                "description": f"API for {product_name} ({architecture_name})",
            },
            "paths": paths,
        }
        return json.dumps(document, indent=2)

    def _render_routes_json(self, architecture_name: str, apis: list[str]) -> str:
        document = {
            "architecture_name": architecture_name,
            "routes": [{"method": "GET", "path": api} for api in apis],
        }
        return json.dumps(document, indent=2)

    def _render_readme(
        self,
        product_name: str,
        architecture_name: str,
        modules: list[str],
        services: list[str],
        apis: list[str],
        database: list[str],
        constraints: list[str],
        priority: str,
    ) -> str:
        return (
            f"# {product_name} API\n\n"
            f"Architecture: {architecture_name}\n\n"
            f"Priority: {priority}\n\n"
            "## Endpoints\n\n"
            + "".join(f"- {api}\n" for api in apis)
            + "\n## Modules\n\n"
            + "".join(f"- {module}\n" for module in modules)
            + "\n## Services\n\n"
            + "".join(f"- {service}\n" for service in services)
            + "\n## Database\n\n"
            + "".join(f"- {entry}\n" for entry in database)
            + "\n## Constraints\n\n"
            + "".join(f"- {constraint}\n" for constraint in constraints)
        )
