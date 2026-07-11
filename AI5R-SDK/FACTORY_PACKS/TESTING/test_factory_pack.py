"""
FP-004
Test Factory Pack

Deterministic, stateless generator that turns a Technical Architecture
dict (as produced by SolutionArchitect.plan()) into a test source bundle.
Pure generation only: no filesystem writes, no LLM, no reasoning, no
Manufacturing Center / Organization / Runtime coupling.
"""

from __future__ import annotations

from typing import Any

DEFAULT_PRIORITY = "NORMAL"


class TestFactoryPack:
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

        test_api_py = self._render_test_api(architecture_name, apis)
        test_website_py = self._render_test_website(architecture_name, modules, services)
        test_smoke_py = self._render_test_smoke(product_name, architecture_name)
        readme_tests_md = self._render_readme_tests(
            product_name, architecture_name, modules, services, apis, database, constraints, priority
        )
        manifest = {
            "pack": "TESTING",
            "architecture_name": architecture_name,
            "product_name": product_name,
            "modules": modules,
            "services": services,
            "apis": apis,
            "database": database,
            "constraints": constraints,
            "priority": priority,
            "files": [
                "tests/test_api.py",
                "tests/test_website.py",
                "tests/test_smoke.py",
                "tests/README_TESTS.md",
            ],
        }

        return {
            "tests/test_api.py": test_api_py,
            "tests/test_website.py": test_website_py,
            "tests/test_smoke.py": test_smoke_py,
            "tests/README_TESTS.md": readme_tests_md,
            "test.manifest.json": manifest,
        }

    def _render_test_api(self, architecture_name: str, apis: list[str]) -> str:
        assertions = "".join(
            f'    assert "{api}" in known_apis\n' for api in apis
        )
        if not assertions:
            assertions = "    assert known_apis == []\n"
        return (
            f"# Generated API tests for {architecture_name}\n\n"
            f"KNOWN_APIS = {apis!r}\n\n\n"
            "def test_declared_apis_are_present():\n"
            "    known_apis = KNOWN_APIS\n"
            f"{assertions}"
        )

    def _render_test_website(
        self, architecture_name: str, modules: list[str], services: list[str]
    ) -> str:
        return (
            f"# Generated website tests for {architecture_name}\n\n"
            f"KNOWN_MODULES = {modules!r}\n"
            f"KNOWN_SERVICES = {services!r}\n\n\n"
            "def test_declared_modules_are_present():\n"
            "    assert KNOWN_MODULES == " + repr(modules) + "\n\n\n"
            "def test_declared_services_are_present():\n"
            "    assert KNOWN_SERVICES == " + repr(services) + "\n"
        )

    def _render_test_smoke(self, product_name: str, architecture_name: str) -> str:
        return (
            f"# Generated smoke tests for {product_name}\n\n"
            f'PRODUCT_NAME = "{product_name}"\n'
            f'ARCHITECTURE_NAME = "{architecture_name}"\n\n\n'
            "def test_product_name_is_set():\n"
            f'    assert PRODUCT_NAME == "{product_name}"\n\n\n'
            "def test_architecture_name_is_set():\n"
            f'    assert ARCHITECTURE_NAME == "{architecture_name}"\n'
        )

    def _render_readme_tests(
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
            f"# Tests for {product_name}\n\n"
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
