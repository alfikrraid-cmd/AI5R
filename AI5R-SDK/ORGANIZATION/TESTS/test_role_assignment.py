import dataclasses
import sys

import pytest


def test_valid_creation():
    from ORGANIZATION.role_assignment import RoleAssignment

    assignment = RoleAssignment(
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        work_order_id="WO-001",
        priority="HIGH",
        status="ASSIGNED",
    )

    assert assignment.assignment_id == "ASSIGN-001"
    assert assignment.role_id == "ROLE-001"
    assert assignment.work_order_id == "WO-001"
    assert assignment.priority == "HIGH"
    assert assignment.status == "ASSIGNED"
    assert assignment.assigned_at is None
    assert assignment.deadline is None
    assert assignment.metadata == {}


def test_accepts_full_data():
    from ORGANIZATION.role_assignment import RoleAssignment

    assignment = RoleAssignment(
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        work_order_id="WO-001",
        priority="HIGH",
        status="ASSIGNED",
        assigned_at="2026-07-10T00:00:00+00:00",
        deadline="2026-07-11T00:00:00+00:00",
        metadata={"note": "urgent"},
    )

    assert assignment.assigned_at == "2026-07-10T00:00:00+00:00"
    assert assignment.deadline == "2026-07-11T00:00:00+00:00"
    assert assignment.metadata == {"note": "urgent"}


def test_missing_assignment_id_raises():
    from ORGANIZATION.role_assignment import RoleAssignment

    with pytest.raises(ValueError):
        RoleAssignment(
            assignment_id="",
            role_id="ROLE-001",
            work_order_id="WO-001",
            priority="HIGH",
            status="ASSIGNED",
        )


def test_missing_assignment_id_none_raises():
    from ORGANIZATION.role_assignment import RoleAssignment

    with pytest.raises(ValueError):
        RoleAssignment(
            assignment_id=None,
            role_id="ROLE-001",
            work_order_id="WO-001",
            priority="HIGH",
            status="ASSIGNED",
        )


def test_missing_role_id_raises():
    from ORGANIZATION.role_assignment import RoleAssignment

    with pytest.raises(ValueError):
        RoleAssignment(
            assignment_id="ASSIGN-001",
            role_id="",
            work_order_id="WO-001",
            priority="HIGH",
            status="ASSIGNED",
        )


def test_missing_work_order_id_raises():
    from ORGANIZATION.role_assignment import RoleAssignment

    with pytest.raises(ValueError):
        RoleAssignment(
            assignment_id="ASSIGN-001",
            role_id="ROLE-001",
            work_order_id="",
            priority="HIGH",
            status="ASSIGNED",
        )


def test_missing_priority_raises():
    from ORGANIZATION.role_assignment import RoleAssignment

    with pytest.raises(ValueError):
        RoleAssignment(
            assignment_id="ASSIGN-001",
            role_id="ROLE-001",
            work_order_id="WO-001",
            priority="",
            status="ASSIGNED",
        )


def test_missing_status_raises():
    from ORGANIZATION.role_assignment import RoleAssignment

    with pytest.raises(ValueError):
        RoleAssignment(
            assignment_id="ASSIGN-001",
            role_id="ROLE-001",
            work_order_id="WO-001",
            priority="HIGH",
            status="",
        )


def test_is_frozen():
    from ORGANIZATION.role_assignment import RoleAssignment

    assignment = RoleAssignment(
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        work_order_id="WO-001",
        priority="HIGH",
        status="ASSIGNED",
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        assignment.status = "COMPLETED"


def test_deterministic_equality_for_equivalent_data():
    from ORGANIZATION.role_assignment import RoleAssignment

    first = RoleAssignment(
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        work_order_id="WO-001",
        priority="HIGH",
        status="ASSIGNED",
        metadata={"note": "urgent"},
    )
    second = RoleAssignment(
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        work_order_id="WO-001",
        priority="HIGH",
        status="ASSIGNED",
        metadata={"note": "urgent"},
    )

    assert first == second


def test_inequality_when_fields_differ():
    from ORGANIZATION.role_assignment import RoleAssignment

    first = RoleAssignment(
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        work_order_id="WO-001",
        priority="HIGH",
        status="ASSIGNED",
    )
    second = RoleAssignment(
        assignment_id="ASSIGN-002",
        role_id="ROLE-001",
        work_order_id="WO-001",
        priority="HIGH",
        status="ASSIGNED",
    )

    assert first != second


def test_input_metadata_dict_is_defensively_copied():
    from ORGANIZATION.role_assignment import RoleAssignment

    metadata = {"note": "urgent"}
    assignment = RoleAssignment(
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        work_order_id="WO-001",
        priority="HIGH",
        status="ASSIGNED",
        metadata=metadata,
    )

    metadata["extra"] = True

    assert assignment.metadata == {"note": "urgent"}


def test_default_metadata_not_shared_between_instances():
    from ORGANIZATION.role_assignment import RoleAssignment

    first = RoleAssignment(
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        work_order_id="WO-001",
        priority="HIGH",
        status="ASSIGNED",
    )
    second = RoleAssignment(
        assignment_id="ASSIGN-002",
        role_id="ROLE-001",
        work_order_id="WO-001",
        priority="HIGH",
        status="ASSIGNED",
    )

    first.metadata["marker"] = True

    assert "marker" not in second.metadata


def test_to_dict_returns_expected_structure():
    from ORGANIZATION.role_assignment import RoleAssignment

    assignment = RoleAssignment(
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        work_order_id="WO-001",
        priority="HIGH",
        status="ASSIGNED",
        assigned_at="2026-07-10T00:00:00+00:00",
        deadline="2026-07-11T00:00:00+00:00",
        metadata={"note": "urgent"},
    )

    assert assignment.to_dict() == {
        "assignment_id": "ASSIGN-001",
        "role_id": "ROLE-001",
        "work_order_id": "WO-001",
        "priority": "HIGH",
        "status": "ASSIGNED",
        "assigned_at": "2026-07-10T00:00:00+00:00",
        "deadline": "2026-07-11T00:00:00+00:00",
        "metadata": {"note": "urgent"},
    }


def test_to_dict_mutation_does_not_affect_original():
    from ORGANIZATION.role_assignment import RoleAssignment

    assignment = RoleAssignment(
        assignment_id="ASSIGN-001",
        role_id="ROLE-001",
        work_order_id="WO-001",
        priority="HIGH",
        status="ASSIGNED",
        metadata={"note": "urgent"},
    )

    as_dict = assignment.to_dict()
    as_dict["metadata"]["note"] = "mutated"

    assert assignment.metadata == {"note": "urgent"}


def test_role_assignment_is_independent_of_manufacturing_center():
    for module_name in list(sys.modules):
        if module_name.startswith("MANUFACTURING_CENTER"):
            del sys.modules[module_name]

    import ORGANIZATION.role_assignment  # noqa: F401

    assert not any(
        module_name.startswith("MANUFACTURING_CENTER")
        for module_name in sys.modules
    )
