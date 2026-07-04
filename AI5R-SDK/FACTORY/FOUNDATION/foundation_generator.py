from pathlib import Path

try:
    from .template_loader import TemplateLoader
except ImportError:
    from template_loader import TemplateLoader


class FoundationGenerator:
    """
    AI5R Foundation Generator.

    Generates canonical foundation components from templates.
    Backward compatible with FG-001 manifest/root API.
    """

    def __init__(self, template_dir: str | Path | None = None):
        base_dir = Path(__file__).resolve().parent
        self.template_dir = Path(template_dir) if template_dir else base_dir / "TEMPLATES"
        self.loader = TemplateLoader(self.template_dir)

    def generate(
        self,
        foundation_name: str | None = None,
        output_dir: str | Path | None = None,
        manifest=None,
        root: str | Path | None = None,
    ):
        legacy_mode = manifest is not None

        if legacy_mode:
            foundation_name = manifest.foundation
            output_dir = Path(root) / manifest.foundation.upper()

        if foundation_name is None or output_dir is None:
            raise ValueError("foundation_name/output_dir or manifest/root is required")

        class_name = self._to_class_name(foundation_name)
        module_name = self._to_module_name(foundation_name)

        output_dir = Path(output_dir)
        tests_dir = output_dir / "TESTS"

        output_dir.mkdir(parents=True, exist_ok=True)
        tests_dir.mkdir(parents=True, exist_ok=True)

        foundation_code = getattr(manifest, "code", module_name.upper()) if manifest is not None else module_name.upper()

        context = {
            "foundation_name": foundation_name,
            "foundation_code": foundation_code,
            "class_name": class_name,
            "module_name": module_name,
        }

        if legacy_mode:
            files = {
                "__init__.py": "init.py.tpl",
                f"{module_name}_object.py": "object.py.tpl",
                f"{module_name}_registry.py": "registry.py.tpl",
                f"{module_name}_validation_engine.py": "validation.py.tpl",
                f"{module_name}_runtime.py": "runtime.py.tpl",
                f"{module_name}_manifest.py": "manifest.py.tpl",
                f"{module_name}_manufacturing_station.py": "station.py.tpl",
                f"TESTS/test_{module_name}_object.py": "test_object.py.tpl",
                f"DOCS/{foundation_code}-SPECIFICATION.md": "specification.md.tpl",
                f"DOCS/{foundation_name.upper()}-FOUNDATION-FREEZE-v1.0.md": "freeze.md.tpl",
            }
        else:
            files = {
                f"{module_name}.py": "object.py.tpl",
                f"{module_name}_registry.py": "registry.py.tpl",
                f"{module_name}_validator.py": "validation.py.tpl",
                f"{module_name}_runtime.py": "runtime.py.tpl",
                "manifest.json": "manifest.json.tpl",
                f"{module_name}_station.py": "station.py.tpl",
                f"TESTS/test_{module_name}.py": "test_object.py.tpl",
                "SPECIFICATION.md": "specification.md.tpl",
                "FREEZE.md": "freeze.md.tpl",
            }

        generated = []

        for relative_path, template_name in files.items():
            target = output_dir / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(self.loader.render(template_name, context))
            generated.append(str(target))

        if legacy_mode:
            return {
                "status": "GENERATED",
                "foundation": foundation_name.upper(),
                "output_dir": str(output_dir),
                "generated_files": generated,
            }

        return generated

    def _to_class_name(self, value: str) -> str:
        return "".join(part.capitalize() for part in value.replace("-", "_").split("_"))

    def _to_module_name(self, value: str) -> str:
        return value.replace("-", "_").lower()
