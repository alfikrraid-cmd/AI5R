import dataclasses
import sys

import pytest


def test_valid_construction_with_required_fields_only():
    from ORGANIZATION.role_execution_result import RoleExecutionResult

    result = RoleExecutionResult(
        execution_id="EXEC-001",
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        status="SUCCESS",
    )

    assert result.execution_id == "EXEC-001"
    assert result.assignment_id == "ASSIGN-001"
    assert result.role_id == "ROLE-001"
    assert result.status == "SUCCESS"
    assert result.outputs == {}
    assert result.artifacts == ()
    assert result.metadata == {}


def test_accepts_full_data():
    from ORGANIZATION.role_execution_result import RoleExecutionResult

    result = RoleExecutionResult(
        execution_id="EXEC-001",
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        status="SUCCESS",
        outputs={"report": "generated"},
        artifacts=["report.pdf", "summary.csv"],
        metadata={"duration": 1.5},
    )

    assert result.outputs == {"report": "generated"}
    assert result.artifacts == ("report.pdf", "summary.csv")
    assert result.metadata == {"duration": 1.5}


def test_missing_execution_id_raises():
    from ORGANIZATION.role_execution_result import RoleExecutionResult

    with pytest.raises(ValueError):
        RoleExecutionResult(
            execution_id="",
            assignment_id="ASSIGN-001",
            role_id="ROLE-001",
            status="SUCCESS",
        )


def test_missing_execution_id_none_raises():
    from ORGANIZATION.role_execution_result import RoleExecutionResult

    with pytest.raises(ValueError):
        RoleExecutionResult(
            execution_id=None,
            assignment_id="ASSIGN-001",
            role_id="ROLE-001",
            status="SUCCESS",
        )


def test_missing_assignment_id_raises():
    from ORGANIZATION.role_execution_result import RoleExecutionResult

    with pytest.raises(ValueError):
        RoleExecutionResult(
            execution_id="EXEC-001",
            assignment_id="",
            role_id="ROLE-001",
            status="SUCCESS",
        )


def test_missing_role_id_raises():
    from ORGANIZATION.role_execution_result import RoleExecutionResult

    with pytest.raises(ValueError):
        RoleExecutionResult(
            execution_id="EXEC-001",
            assignment_id="ASSIGN-001",
            role_id="",
            status="SUCCESS",
        )


def test_missing_status_raises():
    from ORGANIZATION.role_execution_result import RoleExecutionResult

    with pytest.raises(ValueError):
        RoleExecutionResult(
            execution_id="EXEC-001",
            assignment_id="ASSIGN-001",
            role_id="ROLE-001",
            status="",
        )


def test_is_frozen():
    from ORGANIZATION.role_execution_result import RoleExecutionResult

    result = RoleExecutionResult(
        execution_id="EXEC-001",
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        status="SUCCESS",
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = "FAILED"


def test_artifacts_are_normalized_to_a_tuple():
    from ORGANIZATION.role_execution_result import RoleExecutionResult

    result = RoleExecutionResult(
        execution_id="EXEC-001",
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        status="SUCCESS",
        artifacts=["report.pdf"],
    )

    assert isinstance(result.artifacts, tuple)


def test_input_artifacts_list_is_defensively_copied():
    from ORGANIZATION.role_execution_result import RoleExecutionResult

    artifacts = ["report.pdf"]
    result = RoleExecutionResult(
        execution_id="EXEC-001",
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        status="SUCCESS",
        artifacts=artifacts,
    )

    artifacts.append("summary.csv")

    assert result.artifacts == ("report.pdf",)


def test_input_outputs_dict_is_defensively_copied():
    from ORGANIZATION.role_execution_result import RoleExecutionResult

    outputs = {"report": "generated"}
    result = RoleExecutionResult(
        execution_id="EXEC-001",
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        status="SUCCESS",
        outputs=outputs,
    )

    outputs["extra"] = True

    assert result.outputs == {"report": "generated"}


def test_input_metadata_dict_is_defensively_copied():
    from ORGANIZATION.role_execution_result import RoleExecutionResult

    metadata = {"duration": 1.5}
    result = RoleExecutionResult(
        execution_id="EXEC-001",
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        status="SUCCESS",
        metadata=metadata,
    )

    metadata["extra"] = True

    assert result.metadata == {"duration": 1.5}


def test_default_collections_are_not_shared_between_instances():
    from ORGANIZATION.role_execution_result import RoleExecutionResult

    first = RoleExecutionResult(
        execution_id="EXEC-001",
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        status="SUCCESS",
    )
    second = RoleExecutionResult(
        execution_id="EXEC-002",
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        status="SUCCESS",
    )

    first.metadata["marker"] = True
    first.outputs["marker"] = True

    assert "marker" not in second.metadata
    assert "marker" not in second.outputs


def test_deterministic_equality_for_equivalent_data():
    from ORGANIZATION.role_execution_result import RoleExecutionResult

    first = RoleExecutionResult(
        execution_id="EXEC-001",
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        status="SUCCESS",
        outputs={"report": "generated"},
        artifacts=["report.pdf"],
        metadata={"duration": 1.5},
    )
    second = RoleExecutionResult(
        execution_id="EXEC-001",
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        status="SUCCESS",
        outputs={"report": "generated"},
        artifacts=["report.pdf"],
        metadata={"duration": 1.5},
    )

    assert first == second


def test_inequality_when_fields_differ():
    from ORGANIZATION.role_execution_result import RoleExecutionResult

    first = RoleExecutionResult(
        execution_id="EXEC-001",
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        status="SUCCESS",
    )
    second = RoleExecutionResult(
        execution_id="EXEC-002",
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        status="SUCCESS",
    )

    assert first != second


def test_to_dict_returns_expected_structure():
    from ORGANIZATION.role_execution_result import RoleExecutionResult

    result = RoleExecutionResult(
        execution_id="EXEC-001",
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        status="SUCCESS",
        outputs={"report": "generated"},
        artifacts=["report.pdf"],
        metadata={"duration": 1.5},
    )

    assert result.to_dict() == {
        "execution_id": "EXEC-001",
        "assignment_id": "ASSIGN-001",
        "role_id": "ROLE-001",
        "status": "SUCCESS",
        "outputs": {"report": "generated"},
        "artifacts": ["report.pdf"],
        "metadata": {"duration": 1.5},
    }


def test_to_dict_mutation_does_not_affect_original():
    from ORGANIZATION.role_execution_result import RoleExecutionResult

    result = RoleExecutionResult(
        execution_id="EXEC-001",
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        status="SUCCESS",
        outputs={"report": "generated"},
        artifacts=["report.pdf"],
        metadata={"duration": 1.5},
    )

    as_dict = result.to_dict()
    as_dict["outputs"]["report"] = "mutated"
    as_dict["artifacts"].append("summary.csv")
    as_dict["metadata"]["duration"] = 99

    assert result.outputs == {"report": "generated"}
    assert result.artifacts == ("report.pdf",)
    assert result.metadata == {"duration": 1.5}


def test_role_execution_result_is_independent_of_manufacturing_center():
    for module_name in list(sys.modules):
        if module_name.startswith("MANUFACTURING_CENTER"):
            del sys.modules[module_name]

    import ORGANIZATION.role_execution_result  # noqa: F401

    assert not any(
        module_name.startswith("MANUFACTURING_CENTER")
        for module_name in sys.modules
    )
