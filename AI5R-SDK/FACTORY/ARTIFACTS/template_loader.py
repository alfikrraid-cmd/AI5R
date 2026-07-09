from pathlib import Path


class TemplateLoader:

    def __init__(self, template_root: str | None = None):
        if template_root is None:
            template_root = (
                Path(__file__).parent / "TEMPLATES"
            )
        self.template_root = Path(template_root)

    def load(
        self,
        pack_name: str,
        template_name: str,
    ) -> str:

        template = (
            self.template_root
            / pack_name
            / template_name
        )

        return template.read_text(encoding="utf-8")
