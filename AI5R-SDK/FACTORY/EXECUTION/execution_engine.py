from FACTORY.EXECUTION.execution_result import ExecutionResult


class FactoryExecutionEngine:

    def execute(
        self,
        production_plan: dict,
    ) -> ExecutionResult:

        artifacts = production_plan.get("artifacts", [])

        return ExecutionResult(
            status="EXECUTED",
            production_plan=production_plan,
            artifacts=artifacts,
            workspace={
                "status": "PENDING",
            },
            reports=[],
        )
