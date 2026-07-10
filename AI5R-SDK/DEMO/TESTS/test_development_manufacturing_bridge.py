import pytest

from ORGANIZATION.executive_work_order import ExecutiveWorkOrder
from ORGANIZATION.organization_execution_result import OrganizationExecutionResult


class FakeOrganizationRuntime:
    def __init__(self, result=None):
        self.execute_calls = []
        self._result = result

    def execute(self, work_order):
        self.execute_calls.append(work_order)
        return self._result


class FakeManufacturingRuntime:
    def __init__(self, result=None):
        self.execute_calls = []
        self._result = result

    def execute(self, organization_result):
        self.execute_calls.append(organization_result)
        return self._result


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


def make_organization_result(**overrides):
    defaults = dict(
        status="COMPLETED",
        completed_roles=["ROLE-INFRA", "ROLE-PLATFORM"],
        execution_order=["ROLE-INFRA", "ROLE-PLATFORM"],
        results=["ASSIGNED"],
    )
    defaults.update(overrides)
    return OrganizationExecutionResult(**defaults)


def test_execute_rejects_invalid_work_order():
    from DEMO.development_manufacturing_bridge import DevelopmentManufacturingBridge

    bridge = DevelopmentManufacturingBridge(
        organization_runtime=FakeOrganizationRuntime(),
        manufacturing_runtime=FakeManufacturingRuntime(),
    )

    with pytest.raises(ValueError):
        bridge.execute({"work_order_id": "WO-001"})


def test_execute_raises_when_organization_runtime_missing():
    from DEMO.development_manufacturing_bridge import DevelopmentManufacturingBridge

    bridge = DevelopmentManufacturingBridge(
        organization_runtime=None,
        manufacturing_runtime=FakeManufacturingRuntime(),
    )
    work_order = make_work_order()

    with pytest.raises(ValueError):
        bridge.execute(work_order)


def test_execute_raises_when_manufacturing_runtime_missing():
    from DEMO.development_manufacturing_bridge import DevelopmentManufacturingBridge

    bridge = DevelopmentManufacturingBridge(
        organization_runtime=FakeOrganizationRuntime(),
        manufacturing_runtime=None,
    )
    work_order = make_work_order()

    with pytest.raises(ValueError):
        bridge.execute(work_order)


def test_execute_returns_manufacturing_result_on_success():
    from DEMO.development_manufacturing_bridge import DevelopmentManufacturingBridge

    organization_result = make_organization_result()
    organization_runtime = FakeOrganizationRuntime(result=organization_result)
    manufacturing_runtime = FakeManufacturingRuntime(result="MANUFACTURING-RESULT")
    bridge = DevelopmentManufacturingBridge(
        organization_runtime=organization_runtime,
        manufacturing_runtime=manufacturing_runtime,
    )
    work_order = make_work_order()

    result = bridge.execute(work_order)

    assert result == "MANUFACTURING-RESULT"
    assert organization_runtime.execute_calls == [work_order]
    assert manufacturing_runtime.execute_calls == [organization_result]


def test_execute_is_deterministic():
    from DEMO.development_manufacturing_bridge import DevelopmentManufacturingBridge

    organization_result = make_organization_result()
    bridge = DevelopmentManufacturingBridge(
        organization_runtime=FakeOrganizationRuntime(result=organization_result),
        manufacturing_runtime=FakeManufacturingRuntime(result="MANUFACTURING-RESULT"),
    )
    work_order = make_work_order()

    first = bridge.execute(work_order)
    second = bridge.execute(work_order)

    assert first == second == "MANUFACTURING-RESULT"


def test_execute_uses_injected_dependencies():
    from DEMO.development_manufacturing_bridge import DevelopmentManufacturingBridge

    organization_result_a = make_organization_result(status="COMPLETED")
    organization_result_b = make_organization_result(status="PARTIAL")

    bridge_a = DevelopmentManufacturingBridge(
        organization_runtime=FakeOrganizationRuntime(result=organization_result_a),
        manufacturing_runtime=FakeManufacturingRuntime(result="RESULT-A"),
    )
    bridge_b = DevelopmentManufacturingBridge(
        organization_runtime=FakeOrganizationRuntime(result=organization_result_b),
        manufacturing_runtime=FakeManufacturingRuntime(result="RESULT-B"),
    )
    work_order = make_work_order()

    assert bridge_a.execute(work_order) == "RESULT-A"
    assert bridge_b.execute(work_order) == "RESULT-B"


def test_execute_is_stateless_across_runs():
    from DEMO.development_manufacturing_bridge import DevelopmentManufacturingBridge

    organization_runtime = FakeOrganizationRuntime(result=make_organization_result())
    manufacturing_runtime = FakeManufacturingRuntime(result="MANUFACTURING-RESULT")
    bridge = DevelopmentManufacturingBridge(
        organization_runtime=organization_runtime,
        manufacturing_runtime=manufacturing_runtime,
    )
    work_order = make_work_order()

    bridge.execute(work_order)
    bridge.execute(work_order)
    bridge.execute(work_order)

    assert len(organization_runtime.execute_calls) == 3
    assert len(manufacturing_runtime.execute_calls) == 3
    assert bridge.execute(work_order) == bridge.execute(work_order)
