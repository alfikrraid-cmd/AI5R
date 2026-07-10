import dataclasses
import sys

import pytest


def test_creates_with_required_fields_only_and_defaults_are_empty():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    order = ExecutiveWorkOrder(
        work_order_id="WO-001",
        objective="Increase quarterly revenue",
        priority="HIGH",
    )

    assert order.work_order_id == "WO-001"
    assert order.mission_id is None
    assert order.objective == "Increase quarterly revenue"
    assert order.priority == "HIGH"
    assert order.constraints == ()
    assert order.success_criteria == ()
    assert order.requested_roles == ()
    assert order.metadata == {}


def test_accepts_full_data():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    order = ExecutiveWorkOrder(
        work_order_id="WO-001",
        mission_id="MISSION-001",
        objective="Increase quarterly revenue",
        priority="HIGH",
        constraints=["budget<=100000"],
        success_criteria=["revenue increase >= 10%"],
        requested_roles=["ROLE-001", "ROLE-002"],
        metadata={"origin": "board"},
    )

    assert order.mission_id == "MISSION-001"
    assert order.constraints == ("budget<=100000",)
    assert order.success_criteria == ("revenue increase >= 10%",)
    assert order.requested_roles == ("ROLE-001", "ROLE-002")
    assert order.metadata == {"origin": "board"}


def test_missing_work_order_id_raises():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    with pytest.raises(ValueError):
        ExecutiveWorkOrder(
            work_order_id="",
            objective="Increase quarterly revenue",
            priority="HIGH",
        )


def test_missing_work_order_id_none_raises():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    with pytest.raises(ValueError):
        ExecutiveWorkOrder(
            work_order_id=None,
            objective="Increase quarterly revenue",
            priority="HIGH",
        )


def test_missing_objective_raises():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    with pytest.raises(ValueError):
        ExecutiveWorkOrder(
            work_order_id="WO-001",
            objective="",
            priority="HIGH",
        )


def test_missing_priority_raises():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    with pytest.raises(ValueError):
        ExecutiveWorkOrder(
            work_order_id="WO-001",
            objective="Increase quarterly revenue",
            priority="",
        )


def test_is_frozen():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    order = ExecutiveWorkOrder(
        work_order_id="WO-001",
        objective="Increase quarterly revenue",
        priority="HIGH",
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        order.priority = "LOW"


def test_constraints_are_normalized_to_a_tuple():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    order = ExecutiveWorkOrder(
        work_order_id="WO-001",
        objective="Increase quarterly revenue",
        priority="HIGH",
        constraints=["budget<=100000"],
    )

    assert isinstance(order.constraints, tuple)


def test_success_criteria_are_normalized_to_a_tuple():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    order = ExecutiveWorkOrder(
        work_order_id="WO-001",
        objective="Increase quarterly revenue",
        priority="HIGH",
        success_criteria=["revenue increase >= 10%"],
    )

    assert isinstance(order.success_criteria, tuple)


def test_requested_roles_are_normalized_to_a_tuple():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    order = ExecutiveWorkOrder(
        work_order_id="WO-001",
        objective="Increase quarterly revenue",
        priority="HIGH",
        requested_roles=["ROLE-001"],
    )

    assert isinstance(order.requested_roles, tuple)


def test_input_constraints_list_is_defensively_copied():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    constraints = ["budget<=100000"]
    order = ExecutiveWorkOrder(
        work_order_id="WO-001",
        objective="Increase quarterly revenue",
        priority="HIGH",
        constraints=constraints,
    )

    constraints.append("deadline<=30d")

    assert order.constraints == ("budget<=100000",)


def test_input_success_criteria_list_is_defensively_copied():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    success_criteria = ["revenue increase >= 10%"]
    order = ExecutiveWorkOrder(
        work_order_id="WO-001",
        objective="Increase quarterly revenue",
        priority="HIGH",
        success_criteria=success_criteria,
    )

    success_criteria.append("customer churn <= 5%")

    assert order.success_criteria == ("revenue increase >= 10%",)


def test_input_requested_roles_list_is_defensively_copied():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    requested_roles = ["ROLE-001"]
    order = ExecutiveWorkOrder(
        work_order_id="WO-001",
        objective="Increase quarterly revenue",
        priority="HIGH",
        requested_roles=requested_roles,
    )

    requested_roles.append("ROLE-002")

    assert order.requested_roles == ("ROLE-001",)


def test_input_metadata_dict_is_defensively_copied():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    metadata = {"origin": "board"}
    order = ExecutiveWorkOrder(
        work_order_id="WO-001",
        objective="Increase quarterly revenue",
        priority="HIGH",
        metadata=metadata,
    )

    metadata["extra"] = True

    assert order.metadata == {"origin": "board"}


def test_default_collections_are_not_shared_between_instances():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    first = ExecutiveWorkOrder(
        work_order_id="WO-001",
        objective="Increase quarterly revenue",
        priority="HIGH",
    )
    second = ExecutiveWorkOrder(
        work_order_id="WO-002",
        objective="Reduce operating costs",
        priority="MEDIUM",
    )

    first.metadata["marker"] = True

    assert "marker" not in second.metadata


def test_deterministic_equality_for_equivalent_data():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    first = ExecutiveWorkOrder(
        work_order_id="WO-001",
        mission_id="MISSION-001",
        objective="Increase quarterly revenue",
        priority="HIGH",
        constraints=["budget<=100000"],
        success_criteria=["revenue increase >= 10%"],
        requested_roles=["ROLE-001"],
        metadata={"origin": "board"},
    )
    second = ExecutiveWorkOrder(
        work_order_id="WO-001",
        mission_id="MISSION-001",
        objective="Increase quarterly revenue",
        priority="HIGH",
        constraints=["budget<=100000"],
        success_criteria=["revenue increase >= 10%"],
        requested_roles=["ROLE-001"],
        metadata={"origin": "board"},
    )

    assert first == second


def test_inequality_when_fields_differ():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    first = ExecutiveWorkOrder(
        work_order_id="WO-001",
        objective="Increase quarterly revenue",
        priority="HIGH",
    )
    second = ExecutiveWorkOrder(
        work_order_id="WO-002",
        objective="Increase quarterly revenue",
        priority="HIGH",
    )

    assert first != second


def test_to_dict_returns_expected_structure():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    order = ExecutiveWorkOrder(
        work_order_id="WO-001",
        mission_id="MISSION-001",
        objective="Increase quarterly revenue",
        priority="HIGH",
        constraints=["budget<=100000"],
        success_criteria=["revenue increase >= 10%"],
        requested_roles=["ROLE-001"],
        metadata={"origin": "board"},
    )

    assert order.to_dict() == {
        "work_order_id": "WO-001",
        "mission_id": "MISSION-001",
        "objective": "Increase quarterly revenue",
        "priority": "HIGH",
        "constraints": ["budget<=100000"],
        "success_criteria": ["revenue increase >= 10%"],
        "requested_roles": ["ROLE-001"],
        "metadata": {"origin": "board"},
    }


def test_to_dict_mutation_does_not_affect_original():
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    order = ExecutiveWorkOrder(
        work_order_id="WO-001",
        objective="Increase quarterly revenue",
        priority="HIGH",
        constraints=["budget<=100000"],
        success_criteria=["revenue increase >= 10%"],
        requested_roles=["ROLE-001"],
        metadata={"origin": "board"},
    )

    as_dict = order.to_dict()
    as_dict["constraints"].append("deadline<=30d")
    as_dict["success_criteria"].append("customer churn <= 5%")
    as_dict["requested_roles"].append("ROLE-999")
    as_dict["metadata"]["extra"] = True

    assert order.constraints == ("budget<=100000",)
    assert order.success_criteria == ("revenue increase >= 10%",)
    assert order.requested_roles == ("ROLE-001",)
    assert order.metadata == {"origin": "board"}


def test_executive_work_order_is_independent_of_manufacturing_center():
    for module_name in list(sys.modules):
        if module_name.startswith("MANUFACTURING_CENTER"):
            del sys.modules[module_name]

    import ORGANIZATION.executive_work_order  # noqa: F401

    assert not any(
        module_name.startswith("MANUFACTURING_CENTER")
        for module_name in sys.modules
    )


def test_executive_work_order_is_independent_of_organization_runtime():
    for module_name in list(sys.modules):
        if module_name.startswith("ORGANIZATION.organization_runtime"):
            del sys.modules[module_name]

    import ORGANIZATION.executive_work_order  # noqa: F401

    assert not any(
        module_name.startswith("ORGANIZATION.organization_runtime")
        for module_name in sys.modules
    )


def test_executive_work_order_is_independent_of_ai_executive():
    for module_name in list(sys.modules):
        if module_name.startswith("ORGANIZATION.ai_executive"):
            del sys.modules[module_name]

    import ORGANIZATION.executive_work_order  # noqa: F401

    assert not any(
        module_name.startswith("ORGANIZATION.ai_executive")
        for module_name in sys.modules
    )
