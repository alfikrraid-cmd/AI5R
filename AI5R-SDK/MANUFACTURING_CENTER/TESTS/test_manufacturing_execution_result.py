import dataclasses

import pytest


def test_creates_with_status_only_and_defaults_are_empty():
    from MANUFACTURING_CENTER.manufacturing_execution_result import (
        ManufacturingExecutionResult,
    )

    result = ManufacturingExecutionResult(status="COMPLETED")

    assert result.status == "COMPLETED"
    assert result.completed_nodes == ()
    assert result.failed_nodes == ()
    assert result.execution_order == ()
    assert result.metadata == {}


def test_accepts_full_data():
    from MANUFACTURING_CENTER.manufacturing_execution_result import (
        ManufacturingExecutionResult,
    )

    result = ManufacturingExecutionResult(
        status="COMPLETED",
        completed_nodes=["A", "B"],
        failed_nodes=["C"],
        execution_order=["A", "B", "C"],
        metadata={"duration": 1.5},
    )

    assert result.status == "COMPLETED"
    assert result.completed_nodes == ("A", "B")
    assert result.failed_nodes == ("C",)
    assert result.execution_order == ("A", "B", "C")
    assert result.metadata == {"duration": 1.5}


def test_collections_are_normalized_to_tuples():
    from MANUFACTURING_CENTER.manufacturing_execution_result import (
        ManufacturingExecutionResult,
    )

    result = ManufacturingExecutionResult(
        status="COMPLETED",
        completed_nodes=["A", "B"],
    )

    assert isinstance(result.completed_nodes, tuple)


def test_input_lists_are_defensively_copied():
    from MANUFACTURING_CENTER.manufacturing_execution_result import (
        ManufacturingExecutionResult,
    )

    completed = ["A", "B"]
    result = ManufacturingExecutionResult(
        status="COMPLETED",
        completed_nodes=completed,
    )

    completed.append("C")

    assert result.completed_nodes == ("A", "B")


def test_input_metadata_dict_is_defensively_copied():
    from MANUFACTURING_CENTER.manufacturing_execution_result import (
        ManufacturingExecutionResult,
    )

    metadata = {"a": 1}
    result = ManufacturingExecutionResult(status="COMPLETED", metadata=metadata)

    metadata["b"] = 2

    assert result.metadata == {"a": 1}


def test_default_collections_are_not_shared_between_instances():
    from MANUFACTURING_CENTER.manufacturing_execution_result import (
        ManufacturingExecutionResult,
    )

    first = ManufacturingExecutionResult(status="COMPLETED")
    second = ManufacturingExecutionResult(status="COMPLETED")

    first.metadata["marker"] = True

    assert "marker" not in second.metadata


def test_is_immutable():
    from MANUFACTURING_CENTER.manufacturing_execution_result import (
        ManufacturingExecutionResult,
    )

    result = ManufacturingExecutionResult(status="COMPLETED")

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = "FAILED"


def test_to_dict_returns_expected_structure():
    from MANUFACTURING_CENTER.manufacturing_execution_result import (
        ManufacturingExecutionResult,
    )

    result = ManufacturingExecutionResult(
        status="COMPLETED",
        completed_nodes=["A"],
        failed_nodes=[],
        execution_order=["A"],
        metadata={"key": "value"},
    )

    assert result.to_dict() == {
        "status": "COMPLETED",
        "completed_nodes": ["A"],
        "failed_nodes": [],
        "execution_order": ["A"],
        "metadata": {"key": "value"},
    }


def test_to_dict_is_deterministic_across_calls():
    from MANUFACTURING_CENTER.manufacturing_execution_result import (
        ManufacturingExecutionResult,
    )

    result = ManufacturingExecutionResult(
        status="COMPLETED",
        completed_nodes=["A", "B"],
    )

    assert result.to_dict() == result.to_dict()


def test_to_dict_mutation_does_not_affect_original():
    from MANUFACTURING_CENTER.manufacturing_execution_result import (
        ManufacturingExecutionResult,
    )

    result = ManufacturingExecutionResult(
        status="COMPLETED",
        completed_nodes=["A"],
        metadata={"key": "value"},
    )

    as_dict = result.to_dict()
    as_dict["completed_nodes"].append("B")
    as_dict["metadata"]["key"] = "mutated"

    assert result.completed_nodes == ("A",)
    assert result.metadata == {"key": "value"}


def test_raises_when_status_is_missing():
    from MANUFACTURING_CENTER.manufacturing_execution_result import (
        ManufacturingExecutionResult,
    )

    with pytest.raises(ValueError):
        ManufacturingExecutionResult(status="")


def test_raises_when_status_is_none():
    from MANUFACTURING_CENTER.manufacturing_execution_result import (
        ManufacturingExecutionResult,
    )

    with pytest.raises(ValueError):
        ManufacturingExecutionResult(status=None)


def test_raises_when_status_is_not_a_string():
    from MANUFACTURING_CENTER.manufacturing_execution_result import (
        ManufacturingExecutionResult,
    )

    with pytest.raises(ValueError):
        ManufacturingExecutionResult(status=123)
