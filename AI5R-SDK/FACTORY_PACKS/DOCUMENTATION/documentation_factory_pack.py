"""
FP-003
Documentation Factory Pack

Deterministic, stateless generator that turns a Technical Architecture
dict (as produced by SolutionArchitect.plan()) into a documentation
source bundle. Pure generation only: no filesystem writes, no LLM,
no reasoning, no Manufacturing Center / Organization / Runtime coupling.
"""

from __future__ import annotations

from typing import Any

DEFAULT_PRIORITY = "NORMAL"


class DocumentationFactoryPack:
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

        readme_md = self._render_readme(product_name, architecture_name, priority)
        install_md = self._render_install(product_name, database, constraints)
        system_overview_md = self._render_system_overview(
            product_name,
            architecture_name,
            modules,
            services,
            apis,
            database,
            constraints,
            priority,
        )
        changelog_md = self._render_changelog(product_name, architecture_name)
        manifest = {
            "pack": "DOCUMENTATION",
            "architecture_name": architecture_name,
            "product_name": product_name,
            "modules": modules,
            "services": services,
            "apis": apis,
            "database": database,
            "constraints": constraints,
            "priority": priority,
            "files": ["README.md", "INSTALL.md", "SYSTEM_OVERVIEW.md", "CHANGELOG.md"],
        }

        return {
            "README.md": readme_md,
            "INSTALL.md": install_md,
            "SYSTEM_OVERVIEW.md": system_overview_md,
            "CHANGELOG.md": changelog_md,
            "documentation.manifest.json": manifest,
        }

    def _render_readme(
        self, product_name: str, architecture_name: str, priority: str
    ) -> str:
        return (
            f"# {product_name}\n\n"
            f"Architecture: {architecture_name}\n\n"
            f"Priority: {priority}\n\n"
            "See SYSTEM_OVERVIEW.md for architecture details and "
            "INSTALL.md for setup instructions.\n"
        )

    def _render_install(
        self, product_name: str, database: list[str], constraints: list[str]
    ) -> str:
        return (
            f"# Installing {product_name}\n\n"
            "## Database\n\n"
            + "".join(f"- {entry}\n" for entry in database)
            + "\n## Constraints\n\n"
            + "".join(f"- {constraint}\n" for constraint in constraints)
        )

    def _render_system_overview(
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
            f"# {product_name} System Overview\n\n"
            f"Architecture: {architecture_name}\n\n"
            f"Priority: {priority}\n\n"
            "## Modules\n\n"
            + "".join(f"- {module}\n" for module in modules)
            + "\n## Services\n\n"
            + "".join(f"- {service}\n" for service in services)
            + "\n## APIs\n\n"
            + "".join(f"- {api}\n" for api in apis)
            + "\n## Database\n\n"
            + "".join(f"- {entry}\n" for entry in database)
            + "\n## Constraints\n\n"
            + "".join(f"- {constraint}\n" for constraint in constraints)
        )

    def _render_changelog(self, product_name: str, architecture_name: str) -> str:
        return (
            f"# Changelog: {product_name}\n\n"
            f"## {architecture_name}\n\n"
            "- Initial generation from technical architecture.\n"
        )
