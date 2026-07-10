import dataclasses
import sys

import pytest


def test_valid_construction_with_required_fields_only():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    result = OrganizationExecutionResult(status="SUCCESS")

    assert result.status == "SUCCESS"
    assert result.completed_roles == ()
    assert result.failed_roles == ()
    assert result.execution_order == ()
    assert result.results == ()
    assert result.metadata == {}


def test_accepts_full_data():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    result = OrganizationExecutionResult(
        status="SUCCESS",
        completed_roles=["ROLE-001", "ROLE-002"],
        failed_roles=["ROLE-003"],
        execution_order=["ROLE-001", "ROLE-002", "ROLE-003"],
        results=[{"role_id": "ROLE-001", "status": "SUCCESS"}],
        metadata={"duration": 3.2},
    )

    assert result.completed_roles == ("ROLE-001", "ROLE-002")
    assert result.failed_roles == ("ROLE-003",)
    assert result.execution_order == ("ROLE-001", "ROLE-002", "ROLE-003")
    assert result.results == ({"role_id": "ROLE-001", "status": "SUCCESS"},)
    assert result.metadata == {"duration": 3.2}


def test_missing_status_raises():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    with pytest.raises(ValueError):
        OrganizationExecutionResult(status=None)


def test_empty_status_raises():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    with pytest.raises(ValueError):
        OrganizationExecutionResult(status="")


def test_blank_status_raises():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    with pytest.raises(ValueError):
        OrganizationExecutionResult(status="   ")


def test_non_string_status_raises():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    with pytest.raises(ValueError):
        OrganizationExecutionResult(status=123)


def test_is_frozen():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    result = OrganizationExecutionResult(status="SUCCESS")

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = "FAILED"


def test_completed_roles_are_normalized_to_a_tuple():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    result = OrganizationExecutionResult(
        status="SUCCESS",
        completed_roles=["ROLE-001"],
    )

    assert isinstance(result.completed_roles, tuple)


def test_failed_roles_are_normalized_to_a_tuple():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    result = OrganizationExecutionResult(
        status="SUCCESS",
        failed_roles=["ROLE-001"],
    )

    assert isinstance(result.failed_roles, tuple)


def test_execution_order_is_normalized_to_a_tuple():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    result = OrganizationExecutionResult(
        status="SUCCESS",
        execution_order=["ROLE-001"],
    )

    assert isinstance(result.execution_order, tuple)


def test_results_are_normalized_to_a_tuple():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    result = OrganizationExecutionResult(
        status="SUCCESS",
        results=[{"role_id": "ROLE-001"}],
    )

    assert isinstance(result.results, tuple)


def test_input_completed_roles_list_is_defensively_copied():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    completed_roles = ["ROLE-001"]
    result = OrganizationExecutionResult(
        status="SUCCESS",
        completed_roles=completed_roles,
    )

    completed_roles.append("ROLE-002")

    assert result.completed_roles == ("ROLE-001",)


def test_input_failed_roles_list_is_defensively_copied():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    failed_roles = ["ROLE-001"]
    result = OrganizationExecutionResult(
        status="SUCCESS",
        failed_roles=failed_roles,
    )

    failed_roles.append("ROLE-002")

    assert result.failed_roles == ("ROLE-001",)


def test_input_execution_order_list_is_defensively_copied():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    execution_order = ["ROLE-001"]
    result = OrganizationExecutionResult(
        status="SUCCESS",
        execution_order=execution_order,
    )

    execution_order.append("ROLE-002")

    assert result.execution_order == ("ROLE-001",)


def test_input_results_list_is_defensively_copied():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    results = [{"role_id": "ROLE-001"}]
    result = OrganizationExecutionResult(
        status="SUCCESS",
        results=results,
    )

    results.append({"role_id": "ROLE-002"})

    assert result.results == ({"role_id": "ROLE-001"},)


def test_input_metadata_dict_is_defensively_copied():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    metadata = {"duration": 1.5}
    result = OrganizationExecutionResult(
        status="SUCCESS",
        metadata=metadata,
    )

    metadata["extra"] = True

    assert result.metadata == {"duration": 1.5}


def test_default_collections_are_not_shared_between_instances():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    first = OrganizationExecutionResult(status="SUCCESS")
    second = OrganizationExecutionResult(status="SUCCESS")

    first.metadata["marker"] = True

    assert "marker" not in second.metadata


def test_deterministic_equality_for_equivalent_data():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    first = OrganizationExecutionResult(
        status="SUCCESS",
        completed_roles=["ROLE-001"],
        failed_roles=[],
        execution_order=["ROLE-001"],
        results=[{"role_id": "ROLE-001"}],
        metadata={"duration": 1.5},
    )
    second = OrganizationExecutionResult(
        status="SUCCESS",
        completed_roles=["ROLE-001"],
        failed_roles=[],
        execution_order=["ROLE-001"],
        results=[{"role_id": "ROLE-001"}],
        metadata={"duration": 1.5},
    )

    assert first == second


def test_inequality_when_fields_differ():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    first = OrganizationExecutionResult(status="SUCCESS")
    second = OrganizationExecutionResult(status="FAILED")

    assert first != second


def test_to_dict_returns_expected_structure():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    result = OrganizationExecutionResult(
        status="SUCCESS",
        completed_roles=["ROLE-001"],
        failed_roles=["ROLE-002"],
        execution_order=["ROLE-001", "ROLE-002"],
        results=[{"role_id": "ROLE-001"}],
        metadata={"duration": 1.5},
    )

    assert result.to_dict() == {
        "status": "SUCCESS",
        "completed_roles": ["ROLE-001"],
        "failed_roles": ["ROLE-002"],
        "execution_order": ["ROLE-001", "ROLE-002"],
        "results": [{"role_id": "ROLE-001"}],
        "metadata": {"duration": 1.5},
    }


def test_to_dict_mutation_does_not_affect_original():
    from ORGANIZATION.organization_execution_result import OrganizationExecutionResult

    result = OrganizationExecutionResult(
        status="SUCCESS",
        completed_roles=["ROLE-001"],
        failed_roles=["ROLE-002"],
        execution_order=["ROLE-001", "ROLE-002"],
        results=[{"role_id": "ROLE-001"}],
        metadata={"duration": 1.5},
    )

    as_dict = result.to_dict()
    as_dict["completed_roles"].append("ROLE-999")
    as_dict["failed_roles"].append("ROLE-999")
    as_dict["execution_order"].append("ROLE-999")
    as_dict["results"].append({"role_id": "ROLE-999"})
    as_dict["metadata"]["duration"] = 99

    assert result.completed_roles == ("ROLE-001",)
    assert result.failed_roles == ("ROLE-002",)
    assert result.execution_order == ("ROLE-001", "ROLE-002")
    assert result.results == ({"role_id": "ROLE-001"},)
    assert result.metadata == {"duration": 1.5}


def test_organization_execution_result_is_independent_of_manufacturing_center():
    for module_name in list(sys.modules):
        if module_name.startswith("MANUFACTURING_CENTER"):
            del sys.modules[module_name]

    import ORGANIZATION.organization_execution_result  # noqa: F401

    assert not any(
        module_name.startswith("MANUFACTURING_CENTER")
        for module_name in sys.modules
    )


def test_organization_execution_result_is_independent_of_organization_runtime():
    for module_name in list(sys.modules):
        if module_name.startswith("ORGANIZATION.organization_runtime"):
            del sys.modules[module_name]

    import ORGANIZATION.organization_execution_result  # noqa: F401

    assert not any(
        module_name.startswith("ORGANIZATION.organization_runtime")
        for module_name in sys.modules
    )


def test_organization_execution_result_is_independent_of_ai_role():
    for module_name in list(sys.modules):
        if module_name.startswith("ORGANIZATION.ai_role"):
            del sys.modules[module_name]

    import ORGANIZATION.organization_execution_result  # noqa: F401

    assert not any(
        module_name.startswith("ORGANIZATION.ai_role")
        for module_name in sys.modules
    )


def test_organization_execution_result_is_independent_of_role_assignment():
    for module_name in list(sys.modules):
        if module_name.startswith("ORGANIZATION.role_assignment"):
            del sys.modules[module_name]

    import ORGANIZATION.organization_execution_result  # noqa: F401

    assert not any(
        module_name.startswith("ORGANIZATION.role_assignment")
        for module_name in sys.modules
    )
