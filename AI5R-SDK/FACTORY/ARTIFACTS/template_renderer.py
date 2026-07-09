class TemplateRenderer:
    def render(
        self,
        template_text: str,
        context: dict,
    ) -> str:
        rendered = template_text

        for key, value in context.items():
            rendered = rendered.replace(
                "{{" + key + "}}",
                str(value),
            )

        return rendered
