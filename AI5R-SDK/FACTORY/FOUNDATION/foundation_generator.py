from pathlib import Path

try:
    from .template_loader import TemplateLoader
    from .template_registry import TemplateRegistry
except ImportError:
    from template_loader import TemplateLoader
    from template_registry import TemplateRegistry


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
        self.registry = TemplateRegistry()

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

        registry_mode = "legacy" if legacy_mode else "standard"
        files = self.registry.get(registry_mode)

        rendered_files = {}

        for relative_path, template_name in files.items():
            rendered_path = (
                relative_path
                .replace("{{module_name}}", module_name)
                .replace("{{foundation_code}}", foundation_code)
                .replace("{{foundation_upper}}", foundation_name.upper())
            )

            rendered_files[rendered_path] = template_name

        files = rendered_files

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
