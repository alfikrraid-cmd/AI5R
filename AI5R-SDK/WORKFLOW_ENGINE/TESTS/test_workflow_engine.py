import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from WORKFLOW_ENGINE import ManufacturingWorkflow
from WORKFLOW_ENGINE import WorkflowEngine


def test_register_default_workflow():
    engine = WorkflowEngine()

    workflow = ManufacturingWorkflow(
        workflow_name="DEFAULT_PRODUCT_PIPELINE"
    )

    result = engine.register(workflow)

    assert result["status"] == "REGISTERED"
    assert len(result["stations"]) == 6


def test_execute_registered_workflow():
    engine = WorkflowEngine()

    engine.register(
        ManufacturingWorkflow(
            workflow_name="DEFAULT_PRODUCT_PIPELINE"
        )
    )

    result = engine.execute("DEFAULT_PRODUCT_PIPELINE")

    assert result["status"] == "COMPLETED"
    assert len(result["stations"]) == 6
    assert result["stations"][0]["status"] == "COMPLETED"


def test_unknown_workflow():
    engine = WorkflowEngine()

    result = engine.execute("UNKNOWN")

    assert result["status"] == "NOT_FOUND"


def test_invalid_workflow():
    try:
        ManufacturingWorkflow(workflow_name="").validate()
    except ValueError as error:
        assert str(error) == "workflow_name is required"
    else:
        raise AssertionError("Expected ValueError")
