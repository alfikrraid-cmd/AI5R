from pathlib import Path

try:
    from .template_loader import TemplateLoader
except ImportError:
    from template_loader import TemplateLoader


class ComponentGenerator:
    """
    Generates a single component from a template.
    """

    def __init__(self, loader: TemplateLoader):
        self.loader = loader

    def generate(self, template_name: str, destination: str | Path, context: dict) -> str:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)

        content = self.loader.render(template_name, context)
        destination.write_text(content)

        return str(destination)
