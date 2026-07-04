class TemplateRegistry:
    """
    Registry for AI5R foundation generation templates.
    """

    def foundation_templates(self) -> dict:
        return {
            "standard": {
                "{{module_name}}.py": "object.py.tpl",
                "{{module_name}}_registry.py": "registry.py.tpl",
                "{{module_name}}_validator.py": "validation.py.tpl",
                "{{module_name}}_runtime.py": "runtime.py.tpl",
                "manifest.json": "manifest.json.tpl",
                "{{module_name}}_station.py": "station.py.tpl",
                "TESTS/test_{{module_name}}.py": "test_object.py.tpl",
                "SPECIFICATION.md": "specification.md.tpl",
                "FREEZE.md": "freeze.md.tpl",
            },
            "legacy": {
                "__init__.py": "init.py.tpl",
                "{{module_name}}_object.py": "object.py.tpl",
                "{{module_name}}_registry.py": "registry.py.tpl",
                "{{module_name}}_validation_engine.py": "validation.py.tpl",
                "{{module_name}}_runtime.py": "runtime.py.tpl",
                "{{module_name}}_manifest.py": "manifest.py.tpl",
                "{{module_name}}_manufacturing_station.py": "station.py.tpl",
                "TESTS/test_{{module_name}}_object.py": "test_object.py.tpl",
                "DOCS/{{foundation_code}}-SPECIFICATION.md": "specification.md.tpl",
                "DOCS/{{foundation_upper}}-FOUNDATION-FREEZE-v1.0.md": "freeze.md.tpl",
            },
        }

    def get(self, mode: str) -> dict:
        templates = self.foundation_templates()

        if mode not in templates:
            raise ValueError(f"Unknown template mode: {mode}")

        return templates[mode]
