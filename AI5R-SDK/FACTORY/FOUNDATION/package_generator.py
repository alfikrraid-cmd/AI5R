from pathlib import Path

try:
    from .component_generator import ComponentGenerator
except ImportError:
    from component_generator import ComponentGenerator


class PackageGenerator:
    """
    Generates a package from multiple registered templates.
    """

    def __init__(self, component_generator: ComponentGenerator):
        self.component_generator = component_generator

    def generate(self, output_dir: str | Path, files: dict, context: dict) -> list:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        generated = []

        for relative_path, template_name in files.items():
            target = output_dir / relative_path

            generated.append(
                self.component_generator.generate(
                    template_name=template_name,
                    destination=target,
                    context=context,
                )
            )

        return generated
