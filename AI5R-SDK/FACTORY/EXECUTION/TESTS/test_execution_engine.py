from FACTORY.EXECUTION import FactoryExecutionEngine


def test_execution_engine_executes_plan():

    plan = {
        "artifacts": [
            "main.py",
            "auth.py",
            "README.md",
        ]
    }

    result = FactoryExecutionEngine().execute(plan)

    assert result.status == "EXECUTED"

    assert len(result.artifacts) == 3

    assert result.workspace["status"] == "PENDING"


def test_execution_result_has_execution_id():

    result = FactoryExecutionEngine().execute(
        {
            "artifacts":[]
        }
    )

    assert result.execution_id.startswith("EXEC-")
