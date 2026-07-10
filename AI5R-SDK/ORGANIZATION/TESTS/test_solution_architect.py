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
        work_order_id="WO-200",
        objective="Design the payments platform architecture",
        priority="HIGH",
        constraints=["budget<=200000"],
        success_criteria=["latency <= 200ms"],
        requested_roles=["ROLE-BACKEND", "ROLE-DATABASE"],
    )
    defaults.update(overrides)
    return ExecutiveWorkOrder(**defaults)


def test_inherits_from_ai_executive():
    from ORGANIZATION.ai_executive import AIExecutive
    from ORGANIZATION.solution_architect import SolutionArchitect

    sa = SolutionArchitect()

    assert isinstance(sa, AIExecutive)


def test_constructor_supports_no_arguments():
    from ORGANIZATION.solution_architect import SolutionArchitect

    sa = SolutionArchitect()

    assert sa.organization_runtime is None
    assert sa.executive_id
    assert sa.executive_name
    assert sa.department
    assert sa.authority_level


def test_constructor_stores_injected_runtime():
    from ORGANIZATION.solution_architect import SolutionArchitect

    runtime = FakeOrganizationRuntime()
    sa = SolutionArchitect(organization_runtime=runtime)

    assert sa.organization_runtime is runtime


def test_receive_work_returns_the_same_work_order():
    from ORGANIZATION.solution_architect import SolutionArchitect

    sa = SolutionArchitect()
    work_order = make_work_order()

    received = sa.receive_work(work_order)

    assert received is work_order


def test_receive_work_rejects_invalid_work_order():
    from ORGANIZATION.solution_architect import SolutionArchitect

    sa = SolutionArchitect()

    with pytest.raises(ValueError):
        sa.receive_work({"work_order_id": "WO-200"})


def test_plan_is_deterministic():
    from ORGANIZATION.solution_architect import SolutionArchitect

    sa = SolutionArchitect()
    work_order = make_work_order()

    first = sa.plan(work_order)
    second = sa.plan(work_order)

    assert first == second
    assert first == {
        "architecture_name": "WO-200",
        "product_name": "WO-200",
        "modules": ["ROLE-BACKEND", "ROLE-DATABASE"],
        "services": [],
        "apis": [],
        "database": [],
        "constraints": ["budget<=200000"],
        "priority": "HIGH",
    }


def test_plan_uses_metadata_product_name_when_present():
    from ORGANIZATION.solution_architect import SolutionArchitect

    sa = SolutionArchitect()
    work_order = make_work_order(metadata={"product_name": "Payments Platform"})

    plan = sa.plan(work_order)

    assert plan["product_name"] == "Payments Platform"


def test_plan_rejects_invalid_work_order():
    from ORGANIZATION.solution_architect import SolutionArchitect

    sa = SolutionArchitect()

    with pytest.raises(ValueError):
        sa.plan(None)


def test_plan_output_shape():
    from ORGANIZATION.solution_architect import SolutionArchitect

    sa = SolutionArchitect()
    work_order = make_work_order()

    plan = sa.plan(work_order)

    assert set(plan.keys()) == {
        "architecture_name",
        "product_name",
        "modules",
        "services",
        "apis",
        "database",
        "constraints",
        "priority",
    }


def test_assign_delegates_to_injected_runtime():
    from ORGANIZATION.solution_architect import SolutionArchitect

    runtime = FakeOrganizationRuntime(assign_result="ASSIGNED")
    sa = SolutionArchitect(organization_runtime=runtime)
    work_order = make_work_order()

    result = sa.assign(work_order)

    assert result == "ASSIGNED"
    assert runtime.assign_calls == [work_order]


def test_assign_without_runtime_raises():
    from ORGANIZATION.solution_architect import SolutionArchitect

    sa = SolutionArchitect()
    work_order = make_work_order()

    with pytest.raises(ValueError):
        sa.assign(work_order)


def test_assign_rejects_invalid_work_order():
    from ORGANIZATION.solution_architect import SolutionArchitect

    runtime = FakeOrganizationRuntime()
    sa = SolutionArchitect(organization_runtime=runtime)

    with pytest.raises(ValueError):
        sa.assign({"work_order_id": "WO-200"})


def test_monitor_returns_deterministic_snapshot():
    from ORGANIZATION.solution_architect import SolutionArchitect

    sa = SolutionArchitect()

    first = sa.monitor()
    second = sa.monitor()

    assert first == second
    assert first["executive_id"] == sa.executive_id
    assert first["department"] == sa.department


def test_report_returns_deterministic_report():
    from ORGANIZATION.solution_architect import SolutionArchitect

    sa = SolutionArchitect()

    first = sa.report({"status": "SUCCESS"})
    second = sa.report({"status": "SUCCESS"})

    assert first == second
    assert first["executive_id"] == sa.executive_id
    assert first["result"] == {"status": "SUCCESS"}


def test_stateless_across_runs():
    from ORGANIZATION.solution_architect import SolutionArchitect

    sa = SolutionArchitect()
    work_order = make_work_order()

    sa.plan(work_order)
    sa.monitor()
    sa.report({"status": "SUCCESS"})

    assert sa.metadata == {}
    assert sa.plan(work_order) == sa.plan(work_order)


def test_stateless_between_independent_instances():
    from ORGANIZATION.solution_architect import SolutionArchitect

    first = SolutionArchitect(organization_runtime=FakeOrganizationRuntime())
    second = SolutionArchitect()

    first.monitor()

    assert second.organization_runtime is None


def test_solution_architect_is_independent_of_manufacturing_center():
    for module_name in list(sys.modules):
        if module_name.startswith("MANUFACTURING_CENTER"):
            del sys.modules[module_name]

    import ORGANIZATION.solution_architect  # noqa: F401

    assert not any(
        module_name.startswith("MANUFACTURING_CENTER")
        for module_name in sys.modules
    )
