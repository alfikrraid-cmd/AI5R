from FACTORY.ARTIFACTS.artifact_writer import ArtifactWriter
from FACTORY.ARTIFACTS.template_loader import TemplateLoader
from FACTORY.ARTIFACTS.template_renderer import TemplateRenderer


class ArtifactGenerator:
    def __init__(
        self,
        loader: TemplateLoader | None = None,
        renderer: TemplateRenderer | None = None,
        writer: ArtifactWriter | None = None,
    ) -> None:
        self.loader = loader or TemplateLoader()
        self.renderer = renderer or TemplateRenderer()
        self.writer = writer or ArtifactWriter()

    def generate(
        self,
        workspace: str,
        pack_name: str,
        artifacts: list[dict],
        context: dict,
    ) -> dict:
        written = []

        for artifact in artifacts:
            template_text = self.loader.load(
                pack_name,
                artifact["template"],
            )

            rendered = self.renderer.render(
                template_text,
                context,
            )

            result = self.writer.write(
                workspace=workspace,
                artifact_path=artifact["path"],
                content=rendered,
            )

            written.append(result)

        return {
            "status": "ARTIFACTS_GENERATED",
            "workspace": workspace,
            "count": len(written),
            "artifacts": written,
        }
