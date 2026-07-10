"""
MWO-004.1
Website Factory Pack

Deterministic, stateless generator that turns a Technical Architecture
dict (as produced by SolutionArchitect.plan()) into a static website
source bundle. Pure generation only: no filesystem writes, no LLM, no
reasoning, no Manufacturing Center / Organization / Runtime coupling.
"""

from __future__ import annotations

from typing import Any

DEFAULT_PRIORITY = "NORMAL"


class WebsiteFactoryPack:
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

        index_html = self._render_index_html(
            product_name, architecture_name, modules, services, apis
        )
        style_css = self._render_style_css()
        app_js = self._render_app_js(modules, services, apis)
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
            "pack": "WEBSITE",
            "architecture_name": architecture_name,
            "product_name": product_name,
            "modules": modules,
            "services": services,
            "apis": apis,
            "database": database,
            "constraints": constraints,
            "priority": priority,
            "files": ["index.html", "style.css", "app.js", "README.md"],
        }

        return {
            "index.html": index_html,
            "style.css": style_css,
            "app.js": app_js,
            "README.md": readme_md,
            "website.manifest.json": manifest,
        }

    def _render_index_html(
        self,
        product_name: str,
        architecture_name: str,
        modules: list[str],
        services: list[str],
        apis: list[str],
    ) -> str:
        modules_items = "".join(f"<li>{module}</li>" for module in modules)
        services_items = "".join(f"<li>{service}</li>" for service in services)
        apis_items = "".join(f"<li>{api}</li>" for api in apis)
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8">\n'
            f"  <title>{product_name}</title>\n"
            '  <link rel="stylesheet" href="style.css">\n'
            "</head>\n"
            "<body>\n"
            f"  <h1>{product_name}</h1>\n"
            f"  <p>Architecture: {architecture_name}</p>\n"
            "  <h2>Modules</h2>\n"
            f"  <ul>{modules_items}</ul>\n"
            "  <h2>Services</h2>\n"
            f"  <ul>{services_items}</ul>\n"
            "  <h2>APIs</h2>\n"
            f"  <ul>{apis_items}</ul>\n"
            '  <script src="app.js"></script>\n'
            "</body>\n"
            "</html>\n"
        )

    def _render_style_css(self) -> str:
        return (
            "body {\n"
            "  font-family: sans-serif;\n"
            "  margin: 0 auto;\n"
            "  max-width: 960px;\n"
            "  padding: 2rem;\n"
            "}\n"
            "h1, h2 {\n"
            "  color: #222;\n"
            "}\n"
        )

    def _render_app_js(
        self, modules: list[str], services: list[str], apis: list[str]
    ) -> str:
        return (
            "const architecture = {\n"
            f"  modules: {modules!r},\n"
            f"  services: {services!r},\n"
            f"  apis: {apis!r},\n"
            "};\n"
        )

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
            f"# {product_name}\n\n"
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
