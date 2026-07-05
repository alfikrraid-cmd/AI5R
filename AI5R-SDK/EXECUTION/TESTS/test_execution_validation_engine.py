import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from EXECUTION.execution_engine import ExecutionEngine
from EXECUTION.execution_validation_engine import ExecutionValidationEngine


def test_execution_validation_engine():

    engine = ExecutionEngine()
    validator = ExecutionValidationEngine()

    execution = engine.create_execution(
        plan_id="PLAN-001",
        step_number=1,
        action="Inspect Pump",
        capability_code="CAP-005",
        input_data={"asset_id": "PUMP-001"},
    )

    result = validator.validate(execution)

    assert result["valid"] is True
    assert result["errors"] == []

    print("EX-005 Execution Validation Engine OK")


if __name__ == "__main__":
    test_execution_validation_engine()
