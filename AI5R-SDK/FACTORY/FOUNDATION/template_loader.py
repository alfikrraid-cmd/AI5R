from pathlib import Path


class TemplateLoader:
    def __init__(self, template_dir: str | Path):
        self.template_dir = Path(template_dir)

    def load(self, template_name: str) -> str:
        path = self.template_dir / template_name

        if not path.exists():
            raise FileNotFoundError(f"Template not found: {path}")

        return path.read_text()

    def render(self, template_name: str, context: dict) -> str:
        template = self.load(template_name)

        for key, value in context.items():
            template = template.replace("{{ " + key + " }}", str(value))

        return template
