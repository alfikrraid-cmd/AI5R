import pytest

from ORGANIZATION.chief_technology_officer import ChiefTechnologyOfficer
from ORGANIZATION.executive_registry import ExecutiveRegistry
from ORGANIZATION.executive_work_order import ExecutiveWorkOrder
from ORGANIZATION.organization_execution_result import OrganizationExecutionResult


class FakeOrganizationRuntime:
    def __init__(self, assign_result=None):
        self.assign_calls = []
        self._assign_result = assign_result

    def assign(self, work_order):
        self.assign_calls.append(work_order)
        return self._assign_result if self._assign_result is not None else work_order


class FakeExecutive:
    def __init__(self, executive_id, assign_result=None):
        self.executive_id = executive_id
        self.receive_work_calls = []
        self.plan_calls = []
        self.assign_calls = []
        self._assign_result = assign_result

    def receive_work(self, work_order):
        self.receive_work_calls.append(work_order)
        return work_order

    def plan(self, work_order):
        self.plan_calls.append(work_order)
        return {"steps": list(work_order.requested_roles)}

    def assign(self, work_order):
        self.assign_calls.append(work_order)
        return self._assign_result if self._assign_result is not None else "ASSIGNED"


class FakeExecutiveRegistry:
    def __init__(self, executives=None):
        self._executives = dict(executives or {})

    def get(self, executive_id):
        return self._executives.get(executive_id)


def make_work_order(**overrides):
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


def make_cto_and_registry(assign_result=None):
    runtime = FakeOrganizationRuntime(assign_result=assign_result)
    cto = ChiefTechnologyOfficer(organization_runtime=runtime)
    registry = ExecutiveRegistry()
    registry.register(cto)
    return cto, registry, runtime


def test_run_rejects_invalid_work_order():
    from DEMO.development_organization_demo import DevelopmentOrganizationDemo

    cto, registry, _runtime = make_cto_and_registry()
    demo = DevelopmentOrganizationDemo(cto=cto, executive_registry=registry)

    with pytest.raises(ValueError):
        demo.run({"work_order_id": "WO-001"})


def test_run_raises_when_cto_missing_from_registry():
    from DEMO.development_organization_demo import DevelopmentOrganizationDemo

    cto = ChiefTechnologyOfficer(organization_runtime=FakeOrganizationRuntime())
    empty_registry = ExecutiveRegistry()
    demo = DevelopmentOrganizationDemo(cto=cto, executive_registry=empty_registry)
    work_order = make_work_order()

    with pytest.raises(ValueError):
        demo.run(work_order)


def test_run_returns_organization_execution_result_on_success():
    from DEMO.development_organization_demo import DevelopmentOrganizationDemo

    cto, registry, runtime = make_cto_and_registry(assign_result="ASSIGNED")
    demo = DevelopmentOrganizationDemo(cto=cto, executive_registry=registry)
    work_order = make_work_order()

    result = demo.run(work_order)

    assert isinstance(result, OrganizationExecutionResult)
    assert result.status == "COMPLETED"
    assert result.completed_roles == ("ROLE-INFRA", "ROLE-PLATFORM")
    assert result.execution_order == ("ROLE-INFRA", "ROLE-PLATFORM")
    assert result.results == ("ASSIGNED",)
    assert runtime.assign_calls == [work_order]


def test_run_is_deterministic():
    from DEMO.development_organization_demo import DevelopmentOrganizationDemo

    cto, registry, _runtime = make_cto_and_registry(assign_result="ASSIGNED")
    demo = DevelopmentOrganizationDemo(cto=cto, executive_registry=registry)
    work_order = make_work_order()

    first = demo.run(work_order)
    second = demo.run(work_order)

    assert first.to_dict() == second.to_dict()


def test_run_uses_injected_dependencies():
    from DEMO.development_organization_demo import DevelopmentOrganizationDemo

    fake_executive = FakeExecutive(executive_id="EXEC-FAKE-001", assign_result="FAKE-ASSIGNED")
    registry = FakeExecutiveRegistry({"EXEC-FAKE-001": fake_executive})
    demo = DevelopmentOrganizationDemo(cto=fake_executive, executive_registry=registry)
    work_order = make_work_order()

    result = demo.run(work_order)

    assert fake_executive.receive_work_calls == [work_order]
    assert fake_executive.plan_calls == [work_order]
    assert fake_executive.assign_calls == [work_order]
    assert result.results == ("FAKE-ASSIGNED",)


def test_run_is_stateless_across_runs():
    from DEMO.development_organization_demo import DevelopmentOrganizationDemo

    cto, registry, runtime = make_cto_and_registry(assign_result="ASSIGNED")
    demo = DevelopmentOrganizationDemo(cto=cto, executive_registry=registry)
    work_order = make_work_order()

    demo.run(work_order)
    demo.run(work_order)
    demo.run(work_order)

    assert len(runtime.assign_calls) == 3
    assert demo.run(work_order).to_dict() == demo.run(work_order).to_dict()
