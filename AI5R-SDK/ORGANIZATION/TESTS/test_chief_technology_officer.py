import sys

import pytest


class FakeOrganizationRuntime:
    def __init__(self, assign_result=None):
        self.assign_calls = []
        self._assign_result = assign_result

    def assign(self, work_order):
        self.assign_calls.append(work_order)
        return self._assign_result if self._assign_result is not None else work_order


def make_work_order(**overrides):
    from ORGANIZATION.executive_work_order import ExecutiveWorkOrder

    defaults = dict(
        work_order_id="WO-001",
        objective="Modernize the deployment pipeline",
        priority="HIGH",
        constraints=["budget<=50000"],
        success_criteria=["deploy time <= 5m"],
        requested_roles=["ROLE-INFRA", "ROLE-PLATFORM"],
    )
    defaults.update(overrides)
    return ExecutiveWorkOrder(**defaults)


def test_inherits_from_ai_executive():
    from ORGANIZATION.ai_executive import AIExecutive
    from ORGANIZATION.chief_technology_officer import ChiefTechnologyOfficer

    cto = ChiefTechnologyOfficer()

    assert isinstance(cto, AIExecutive)


def test_constructor_supports_no_arguments():
    from ORGANIZATION.chief_technology_officer import ChiefTechnologyOfficer

    cto = ChiefTechnologyOfficer()

    assert cto.organization_runtime is None
    assert cto.executive_id
    assert cto.executive_name
    assert cto.department
    assert cto.authority_level


def test_constructor_stores_injected_runtime():
    from ORGANIZATION.chief_technology_officer import ChiefTechnologyOfficer

    runtime = FakeOrganizationRuntime()
    cto = ChiefTechnologyOfficer(organization_runtime=runtime)

    assert cto.organization_runtime is runtime


def test_receive_work_returns_the_same_work_order():
    from ORGANIZATION.chief_technology_officer import ChiefTechnologyOfficer

    cto = ChiefTechnologyOfficer()
    work_order = make_work_order()

    received = cto.receive_work(work_order)

    assert received is work_order


def test_receive_work_rejects_invalid_work_order():
    from ORGANIZATION.chief_technology_officer import ChiefTechnologyOfficer

    cto = ChiefTechnologyOfficer()

    with pytest.raises(ValueError):
        cto.receive_work({"work_order_id": "WO-001"})


def test_plan_is_deterministic():
    from ORGANIZATION.chief_technology_officer import ChiefTechnologyOfficer

    cto = ChiefTechnologyOfficer()
    work_order = make_work_order()

    first = cto.plan(work_order)
    second = cto.plan(work_order)

    assert first == second
    assert first == {
        "work_order_id": "WO-001",
        "mission_id": None,
        "objective": "Modernize the deployment pipeline",
        "priority": "HIGH",
        "constraints": ["budget<=50000"],
        "success_criteria": ["deploy time <= 5m"],
        "steps": ["ROLE-INFRA", "ROLE-PLATFORM"],
    }


def test_plan_rejects_invalid_work_order():
    from ORGANIZATION.chief_technology_officer import ChiefTechnologyOfficer

    cto = ChiefTechnologyOfficer()

    with pytest.raises(ValueError):
        cto.plan(None)


def test_assign_delegates_to_injected_runtime():
    from ORGANIZATION.chief_technology_officer import ChiefTechnologyOfficer

    runtime = FakeOrganizationRuntime(assign_result="ASSIGNED")
    cto = ChiefTechnologyOfficer(organization_runtime=runtime)
    work_order = make_work_order()

    result = cto.assign(work_order)

    assert result == "ASSIGNED"
    assert runtime.assign_calls == [work_order]


def test_assign_without_runtime_raises():
    from ORGANIZATION.chief_technology_officer import ChiefTechnologyOfficer

    cto = ChiefTechnologyOfficer()
    work_order = make_work_order()

    with pytest.raises(ValueError):
        cto.assign(work_order)


def test_monitor_returns_deterministic_snapshot():
    from ORGANIZATION.chief_technology_officer import ChiefTechnologyOfficer

    cto = ChiefTechnologyOfficer()

    first = cto.monitor()
    second = cto.monitor()

    assert first == second
    assert first["executive_id"] == cto.executive_id
    assert first["department"] == cto.department


def test_report_returns_deterministic_report():
    from ORGANIZATION.chief_technology_officer import ChiefTechnologyOfficer

    cto = ChiefTechnologyOfficer()

    first = cto.report({"status": "SUCCESS"})
    second = cto.report({"status": "SUCCESS"})

    assert first == second
    assert first["executive_id"] == cto.executive_id
    assert first["result"] == {"status": "SUCCESS"}


def test_stateless_across_runs():
    from ORGANIZATION.chief_technology_officer import ChiefTechnologyOfficer

    cto = ChiefTechnologyOfficer()
    work_order = make_work_order()

    cto.plan(work_order)
    cto.monitor()
    cto.report({"status": "SUCCESS"})

    assert cto.metadata == {}
    assert cto.plan(work_order) == cto.plan(work_order)


def test_stateless_between_independent_instances():
    from ORGANIZATION.chief_technology_officer import ChiefTechnologyOfficer

    first = ChiefTechnologyOfficer(organization_runtime=FakeOrganizationRuntime())
    second = ChiefTechnologyOfficer()

    first.monitor()

    assert second.organization_runtime is None


def test_chief_technology_officer_is_independent_of_manufacturing_center():
    for module_name in list(sys.modules):
        if module_name.startswith("MANUFACTURING_CENTER"):
            del sys.modules[module_name]

    import ORGANIZATION.chief_technology_officer  # noqa: F401

    assert not any(
        module_name.startswith("MANUFACTURING_CENTER")
        for module_name in sys.modules
    )
