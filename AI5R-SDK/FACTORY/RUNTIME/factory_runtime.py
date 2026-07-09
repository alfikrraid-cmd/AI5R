from FACTORY.EXECUTION import (
    BuildValidator,
    FactoryExecutionEngine,
    ZipExporter,
)


class FactoryRuntime:

    def __init__(
        self,
        execution_engine=None,
        validator=None,
        zip_exporter=None,
    ):
        self.execution_engine = (
            execution_engine
            or FactoryExecutionEngine()
        )

        self.validator = (
            validator
            or BuildValidator()
        )

        self.zip_exporter = (
            zip_exporter
            or ZipExporter()
        )

    def run(
        self,
        production_plan: dict,
        output_root="BUILD",
    ):

        execution = self.execution_engine.execute(
            production_plan,
            output_root=output_root,
        )

        workspace = execution.workspace["workspace"]

        validation = self.validator.validate(
            workspace=workspace,
            required_files=production_plan["artifacts"],
        )

        archive = self.zip_exporter.export(
            workspace=workspace,
        )

        return {
            "status": "FACTORY_COMPLETED",
            "execution": execution,
            "validation": validation,
            "archive": archive,
        }
