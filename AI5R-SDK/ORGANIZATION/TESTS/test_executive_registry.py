import sys

import pytest


def make_executive(**overrides):
    from ORGANIZATION.ai_executive import AIExecutive

    defaults = dict(
        executive_id="EXEC-CTO-001",
        executive_name="Chief Technology Officer",
        department="TECHNOLOGY",
        authority_level="C-LEVEL",
    )
    defaults.update(overrides)
    return AIExecutive(**defaults)


def test_empty_registry():
    from ORGANIZATION.executive_registry import ExecutiveRegistry

    registry = ExecutiveRegistry()

    assert registry.list_all() == []
    assert registry.get("EXEC-CTO-001") is None
    assert registry.get_by_department("TECHNOLOGY") == []


def test_register_executive():
    from ORGANIZATION.executive_registry import ExecutiveRegistry

    registry = ExecutiveRegistry()
    executive = make_executive()

    result = registry.register(executive)

    assert result is executive
    assert registry.get("EXEC-CTO-001") is executive
    assert registry.list_all() == [executive]


def test_duplicate_register_raises():
    from ORGANIZATION.executive_registry import ExecutiveRegistry

    registry = ExecutiveRegistry()
    executive = make_executive()
    registry.register(executive)

    with pytest.raises(ValueError):
        registry.register(make_executive())


def test_unregister_executive():
    from ORGANIZATION.executive_registry import ExecutiveRegistry

    registry = ExecutiveRegistry()
    executive = make_executive()
    registry.register(executive)

    registry.unregister("EXEC-CTO-001")

    assert registry.get("EXEC-CTO-001") is None
    assert registry.list_all() == []


def test_unregister_unknown_raises():
    from ORGANIZATION.executive_registry import ExecutiveRegistry

    registry = ExecutiveRegistry()

    with pytest.raises(KeyError):
        registry.unregister("EXEC-UNKNOWN-001")


def test_get_executive():
    from ORGANIZATION.executive_registry import ExecutiveRegistry

    registry = ExecutiveRegistry()
    executive = make_executive()
    registry.register(executive)

    assert registry.get("EXEC-CTO-001") is executive


def test_get_unknown_returns_none():
    from ORGANIZATION.executive_registry import ExecutiveRegistry

    registry = ExecutiveRegistry()

    assert registry.get("EXEC-UNKNOWN-001") is None


def test_list_all_deterministic():
    from ORGANIZATION.executive_registry import ExecutiveRegistry

    registry = ExecutiveRegistry()
    first = make_executive(executive_id="EXEC-CTO-001")
    second = make_executive(executive_id="EXEC-CFO-001", department="FINANCE")
    third = make_executive(executive_id="EXEC-COO-001", department="OPERATIONS")

    registry.register(first)
    registry.register(second)
    registry.register(third)

    assert registry.list_all() == [first, second, third]
    assert registry.list_all() == registry.list_all()


def test_get_by_department():
    from ORGANIZATION.executive_registry import ExecutiveRegistry

    registry = ExecutiveRegistry()
    tech_one = make_executive(executive_id="EXEC-CTO-001", department="TECHNOLOGY")
    tech_two = make_executive(executive_id="EXEC-VPE-001", department="TECHNOLOGY")
    finance_one = make_executive(executive_id="EXEC-CFO-001", department="FINANCE")

    registry.register(tech_one)
    registry.register(tech_two)
    registry.register(finance_one)

    assert registry.get_by_department("TECHNOLOGY") == [tech_one, tech_two]
    assert registry.get_by_department("FINANCE") == [finance_one]
    assert registry.get_by_department("OPERATIONS") == []


def test_stateless_instances():
    from ORGANIZATION.executive_registry import ExecutiveRegistry

    first = ExecutiveRegistry()
    second = ExecutiveRegistry()

    first.register(make_executive())

    assert first.list_all() != second.list_all()
    assert second.list_all() == []
    assert second.get("EXEC-CTO-001") is None


def test_executive_registry_is_independent_of_manufacturing_center():
    for module_name in list(sys.modules):
        if module_name.startswith("MANUFACTURING_CENTER"):
            del sys.modules[module_name]

    import ORGANIZATION.executive_registry  # noqa: F401

    assert not any(
        module_name.startswith("MANUFACTURING_CENTER")
        for module_name in sys.modules
    )
