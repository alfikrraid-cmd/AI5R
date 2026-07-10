import dataclasses
import sys

import pytest


def test_creates_with_required_fields_only_and_defaults_are_empty():
    from ORGANIZATION.ai_role import AIRole

    role = AIRole(
        role_id="ROLE-001",
        role_name="Finance Analyst",
        department="FINANCE",
    )

    assert role.role_id == "ROLE-001"
    assert role.role_name == "Finance Analyst"
    assert role.department == "FINANCE"
    assert role.capabilities == ()
    assert role.responsibilities == ()
    assert role.input_contracts == ()
    assert role.output_contracts == ()
    assert role.policies == ()
    assert role.metadata == {}


def test_accepts_full_data():
    from ORGANIZATION.ai_role import AIRole

    role = AIRole(
        role_id="ROLE-001",
        role_name="Finance Analyst",
        department="FINANCE",
        capabilities=["forecasting", "reporting"],
        responsibilities=["prepare monthly report"],
        input_contracts=["finance.transactions.v1"],
        output_contracts=["finance.report.v1"],
        policies=["POLICY-DATA-RETENTION"],
        metadata={"tier": "gold"},
    )

    assert role.capabilities == ("forecasting", "reporting")
    assert role.responsibilities == ("prepare monthly report",)
    assert role.input_contracts == ("finance.transactions.v1",)
    assert role.output_contracts == ("finance.report.v1",)
    assert role.policies == ("POLICY-DATA-RETENTION",)
    assert role.metadata == {"tier": "gold"}


def test_collections_are_normalized_to_tuples():
    from ORGANIZATION.ai_role import AIRole

    role = AIRole(
        role_id="ROLE-001",
        role_name="Finance Analyst",
        department="FINANCE",
        capabilities=["forecasting"],
    )

    assert isinstance(role.capabilities, tuple)


def test_input_lists_are_defensively_copied():
    from ORGANIZATION.ai_role import AIRole

    capabilities = ["forecasting"]
    role = AIRole(
        role_id="ROLE-001",
        role_name="Finance Analyst",
        department="FINANCE",
        capabilities=capabilities,
    )

    capabilities.append("reporting")

    assert role.capabilities == ("forecasting",)


def test_input_metadata_dict_is_defensively_copied():
    from ORGANIZATION.ai_role import AIRole

    metadata = {"tier": "gold"}
    role = AIRole(
        role_id="ROLE-001",
        role_name="Finance Analyst",
        department="FINANCE",
        metadata=metadata,
    )

    metadata["extra"] = True

    assert role.metadata == {"tier": "gold"}


def test_default_collections_are_not_shared_between_instances():
    from ORGANIZATION.ai_role import AIRole

    first = AIRole(role_id="ROLE-001", role_name="A", department="FINANCE")
    second = AIRole(role_id="ROLE-002", role_name="B", department="FINANCE")

    first.metadata["marker"] = True

    assert "marker" not in second.metadata


def test_is_immutable():
    from ORGANIZATION.ai_role import AIRole

    role = AIRole(role_id="ROLE-001", role_name="A", department="FINANCE")

    with pytest.raises(dataclasses.FrozenInstanceError):
        role.role_name = "Changed"


def test_to_dict_returns_expected_structure():
    from ORGANIZATION.ai_role import AIRole

    role = AIRole(
        role_id="ROLE-001",
        role_name="Finance Analyst",
        department="FINANCE",
        capabilities=["forecasting"],
        responsibilities=["prepare monthly report"],
        input_contracts=["finance.transactions.v1"],
        output_contracts=["finance.report.v1"],
        policies=["POLICY-DATA-RETENTION"],
        metadata={"tier": "gold"},
    )

    assert role.to_dict() == {
        "role_id": "ROLE-001",
        "role_name": "Finance Analyst",
        "department": "FINANCE",
        "capabilities": ["forecasting"],
        "responsibilities": ["prepare monthly report"],
        "input_contracts": ["finance.transactions.v1"],
        "output_contracts": ["finance.report.v1"],
        "policies": ["POLICY-DATA-RETENTION"],
        "metadata": {"tier": "gold"},
    }


def test_to_dict_mutation_does_not_affect_original():
    from ORGANIZATION.ai_role import AIRole

    role = AIRole(
        role_id="ROLE-001",
        role_name="Finance Analyst",
        department="FINANCE",
        capabilities=["forecasting"],
        metadata={"tier": "gold"},
    )

    as_dict = role.to_dict()
    as_dict["capabilities"].append("reporting")
    as_dict["metadata"]["tier"] = "mutated"

    assert role.capabilities == ("forecasting",)
    assert role.metadata == {"tier": "gold"}


def test_equality_is_deterministic_for_equivalent_data():
    from ORGANIZATION.ai_role import AIRole

    first = AIRole(
        role_id="ROLE-001",
        role_name="Finance Analyst",
        department="FINANCE",
        capabilities=["forecasting"],
    )
    second = AIRole(
        role_id="ROLE-001",
        role_name="Finance Analyst",
        department="FINANCE",
        capabilities=["forecasting"],
    )

    assert first == second


def test_inequality_when_fields_differ():
    from ORGANIZATION.ai_role import AIRole

    first = AIRole(role_id="ROLE-001", role_name="A", department="FINANCE")
    second = AIRole(role_id="ROLE-002", role_name="A", department="FINANCE")

    assert first != second


def test_raises_when_role_id_is_missing():
    from ORGANIZATION.ai_role import AIRole

    with pytest.raises(ValueError):
        AIRole(role_id="", role_name="A", department="FINANCE")


def test_raises_when_role_id_is_none():
    from ORGANIZATION.ai_role import AIRole

    with pytest.raises(ValueError):
        AIRole(role_id=None, role_name="A", department="FINANCE")


def test_raises_when_role_name_is_missing():
    from ORGANIZATION.ai_role import AIRole

    with pytest.raises(ValueError):
        AIRole(role_id="ROLE-001", role_name="", department="FINANCE")


def test_raises_when_department_is_missing():
    from ORGANIZATION.ai_role import AIRole

    with pytest.raises(ValueError):
        AIRole(role_id="ROLE-001", role_name="A", department="")


def test_ai_role_is_independent_of_manufacturing_center():
    for module_name in list(sys.modules):
        if module_name.startswith("MANUFACTURING_CENTER"):
            del sys.modules[module_name]

    import ORGANIZATION.ai_role  # noqa: F401

    assert not any(
        module_name.startswith("MANUFACTURING_CENTER")
        for module_name in sys.modules
    )
