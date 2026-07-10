import dataclasses
import sys

import pytest


def test_creates_with_required_fields_only_and_defaults_are_empty():
    from ORGANIZATION.ai_executive import AIExecutive

    executive = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
    )

    assert executive.executive_id == "EXEC-001"
    assert executive.executive_name == "Chief Finance Officer"
    assert executive.department == "FINANCE"
    assert executive.authority_level == "C-LEVEL"
    assert executive.managed_roles == ()
    assert executive.policies == ()
    assert executive.metadata == {}


def test_accepts_full_data():
    from ORGANIZATION.ai_executive import AIExecutive

    executive = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
        managed_roles=["ROLE-001", "ROLE-002"],
        policies=["POLICY-DATA-RETENTION"],
        metadata={"tier": "gold"},
    )

    assert executive.managed_roles == ("ROLE-001", "ROLE-002")
    assert executive.policies == ("POLICY-DATA-RETENTION",)
    assert executive.metadata == {"tier": "gold"}


def test_missing_executive_id_raises():
    from ORGANIZATION.ai_executive import AIExecutive

    with pytest.raises(ValueError):
        AIExecutive(
            executive_id="",
            executive_name="Chief Finance Officer",
            department="FINANCE",
            authority_level="C-LEVEL",
        )


def test_missing_executive_id_none_raises():
    from ORGANIZATION.ai_executive import AIExecutive

    with pytest.raises(ValueError):
        AIExecutive(
            executive_id=None,
            executive_name="Chief Finance Officer",
            department="FINANCE",
            authority_level="C-LEVEL",
        )


def test_missing_executive_name_raises():
    from ORGANIZATION.ai_executive import AIExecutive

    with pytest.raises(ValueError):
        AIExecutive(
            executive_id="EXEC-001",
            executive_name="",
            department="FINANCE",
            authority_level="C-LEVEL",
        )


def test_missing_department_raises():
    from ORGANIZATION.ai_executive import AIExecutive

    with pytest.raises(ValueError):
        AIExecutive(
            executive_id="EXEC-001",
            executive_name="Chief Finance Officer",
            department="",
            authority_level="C-LEVEL",
        )


def test_missing_authority_level_raises():
    from ORGANIZATION.ai_executive import AIExecutive

    with pytest.raises(ValueError):
        AIExecutive(
            executive_id="EXEC-001",
            executive_name="Chief Finance Officer",
            department="FINANCE",
            authority_level="",
        )


def test_is_frozen():
    from ORGANIZATION.ai_executive import AIExecutive

    executive = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        executive.authority_level = "VP"


def test_managed_roles_are_normalized_to_a_tuple():
    from ORGANIZATION.ai_executive import AIExecutive

    executive = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
        managed_roles=["ROLE-001"],
    )

    assert isinstance(executive.managed_roles, tuple)


def test_policies_are_normalized_to_a_tuple():
    from ORGANIZATION.ai_executive import AIExecutive

    executive = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
        policies=["POLICY-DATA-RETENTION"],
    )

    assert isinstance(executive.policies, tuple)


def test_input_managed_roles_list_is_defensively_copied():
    from ORGANIZATION.ai_executive import AIExecutive

    managed_roles = ["ROLE-001"]
    executive = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
        managed_roles=managed_roles,
    )

    managed_roles.append("ROLE-002")

    assert executive.managed_roles == ("ROLE-001",)


def test_input_policies_list_is_defensively_copied():
    from ORGANIZATION.ai_executive import AIExecutive

    policies = ["POLICY-DATA-RETENTION"]
    executive = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
        policies=policies,
    )

    policies.append("POLICY-EXTRA")

    assert executive.policies == ("POLICY-DATA-RETENTION",)


def test_input_metadata_dict_is_defensively_copied():
    from ORGANIZATION.ai_executive import AIExecutive

    metadata = {"tier": "gold"}
    executive = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
        metadata=metadata,
    )

    metadata["extra"] = True

    assert executive.metadata == {"tier": "gold"}


def test_default_collections_are_not_shared_between_instances():
    from ORGANIZATION.ai_executive import AIExecutive

    first = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
    )
    second = AIExecutive(
        executive_id="EXEC-002",
        executive_name="Chief Operating Officer",
        department="OPERATIONS",
        authority_level="C-LEVEL",
    )

    first.metadata["marker"] = True

    assert "marker" not in second.metadata


def test_deterministic_equality_for_equivalent_data():
    from ORGANIZATION.ai_executive import AIExecutive

    first = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
        managed_roles=["ROLE-001"],
        policies=["POLICY-DATA-RETENTION"],
        metadata={"tier": "gold"},
    )
    second = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
        managed_roles=["ROLE-001"],
        policies=["POLICY-DATA-RETENTION"],
        metadata={"tier": "gold"},
    )

    assert first == second


def test_inequality_when_fields_differ():
    from ORGANIZATION.ai_executive import AIExecutive

    first = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
    )
    second = AIExecutive(
        executive_id="EXEC-002",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
    )

    assert first != second


def test_to_dict_returns_expected_structure():
    from ORGANIZATION.ai_executive import AIExecutive

    executive = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
        managed_roles=["ROLE-001"],
        policies=["POLICY-DATA-RETENTION"],
        metadata={"tier": "gold"},
    )

    assert executive.to_dict() == {
        "executive_id": "EXEC-001",
        "executive_name": "Chief Finance Officer",
        "department": "FINANCE",
        "authority_level": "C-LEVEL",
        "managed_roles": ["ROLE-001"],
        "policies": ["POLICY-DATA-RETENTION"],
        "metadata": {"tier": "gold"},
    }


def test_to_dict_mutation_does_not_affect_original():
    from ORGANIZATION.ai_executive import AIExecutive

    executive = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
        managed_roles=["ROLE-001"],
        policies=["POLICY-DATA-RETENTION"],
        metadata={"tier": "gold"},
    )

    as_dict = executive.to_dict()
    as_dict["managed_roles"].append("ROLE-999")
    as_dict["policies"].append("POLICY-999")
    as_dict["metadata"]["tier"] = "platinum"

    assert executive.managed_roles == ("ROLE-001",)
    assert executive.policies == ("POLICY-DATA-RETENTION",)
    assert executive.metadata == {"tier": "gold"}


def test_receive_work_raises_not_implemented():
    from ORGANIZATION.ai_executive import AIExecutive

    executive = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
    )

    with pytest.raises(NotImplementedError):
        executive.receive_work()


def test_plan_raises_not_implemented():
    from ORGANIZATION.ai_executive import AIExecutive

    executive = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
    )

    with pytest.raises(NotImplementedError):
        executive.plan()


def test_assign_raises_not_implemented():
    from ORGANIZATION.ai_executive import AIExecutive

    executive = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
    )

    with pytest.raises(NotImplementedError):
        executive.assign()


def test_monitor_raises_not_implemented():
    from ORGANIZATION.ai_executive import AIExecutive

    executive = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
    )

    with pytest.raises(NotImplementedError):
        executive.monitor()


def test_report_raises_not_implemented():
    from ORGANIZATION.ai_executive import AIExecutive

    executive = AIExecutive(
        executive_id="EXEC-001",
        executive_name="Chief Finance Officer",
        department="FINANCE",
        authority_level="C-LEVEL",
    )

    with pytest.raises(NotImplementedError):
        executive.report()


def test_ai_executive_is_independent_of_manufacturing_center():
    for module_name in list(sys.modules):
        if module_name.startswith("MANUFACTURING_CENTER"):
            del sys.modules[module_name]

    import ORGANIZATION.ai_executive  # noqa: F401

    assert not any(
        module_name.startswith("MANUFACTURING_CENTER")
        for module_name in sys.modules
    )


def test_ai_executive_is_independent_of_organization_runtime():
    for module_name in list(sys.modules):
        if module_name.startswith("ORGANIZATION.organization_runtime"):
            del sys.modules[module_name]

    import ORGANIZATION.ai_executive  # noqa: F401

    assert not any(
        module_name.startswith("ORGANIZATION.organization_runtime")
        for module_name in sys.modules
    )
