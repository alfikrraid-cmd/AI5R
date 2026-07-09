from FACTORY.ARTIFACTS.artifact_generator import ArtifactGenerator
from FACTORY.EXECUTION.execution_result import ExecutionResult
from FACTORY.EXECUTION.workspace_builder import WorkspaceBuilder


class FactoryExecutionEngine:
    TEMPLATE_MAP = {
        "app/main.py": "main.py.tpl",
        "app/routers/auth.py": "auth.py.tpl",
        "app/schemas.py": "schemas.py.tpl",
        "tests/test_login.py": "test_login.py.tpl",
        "tests/test_health.py": "test_login.py.tpl",
        "README.md": "README.md.tpl",
        "requirements.txt": "requirements.txt.tpl",
        "openapi.json": "openapi.json.tpl",
    }

    def __init__(
        self,
        workspace_builder: WorkspaceBuilder | None = None,
        artifact_generator: ArtifactGenerator | None = None,
    ) -> None:
        self.workspace_builder = workspace_builder or WorkspaceBuilder()
        self.artifact_generator = artifact_generator or ArtifactGenerator()

    def execute(
        self,
        production_plan: dict,
        output_root: str = "BUILD",
    ) -> ExecutionResult:
        artifacts = production_plan.get("artifacts", [])

        workspace_result = self.workspace_builder.build(
            artifacts=artifacts,
            output_root=output_root,
        )

        materializable = [
            {
                "path": artifact,
                "template": self.TEMPLATE_MAP[artifact],
            }
            for artifact in artifacts
            if artifact in self.TEMPLATE_MAP
        ]

        generation_result = self.artifact_generator.generate(
            workspace=workspace_result["workspace"],
            pack_name="FASTAPI",
            artifacts=materializable,
            context={
                "project_name": production_plan.get("product_name", "Login API"),
            },
        )

        return ExecutionResult(
            status="EXECUTED",
            production_plan=production_plan,
            artifacts=artifacts,
            workspace=workspace_result,
            reports=[
                generation_result,
            ],
            metadata={
                "generated_artifacts": generation_result["count"],
            },
        )
